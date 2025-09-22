import time
import uuid
from collections import Counter
from typing import Dict, Optional, Union, TypedDict, Literal
from robot.our_types.sorting import SortingState
from robot.our_types.vision_system import FeederState, MainCameraState
from robot.our_types.known_object import KnownObject
from robot.our_types.classify import ClassificationConsensus
from robot.our_types.observation import BoundingBox
from robot.our_types.bin import BinCoordinates
from robot.ai.classify import classifyPiece
from robot.util.images import cropImageToBbox
from robot.vision_system import (
    SegmentationModelManager,
    YOLO_CLASSES,
    SECOND_FEEDER_DISTANCE_THRESHOLD,
    MAIN_CONVEYOR_THRESHOLD,
)
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.encoder_manager import EncoderManager
from robot.bin_state_tracker import BinStateTracker


SECOND_FEEDER_THRESHOLD = 0.5  # 50% object coverage for second feeder

# Variables for handling objects at end of second feeder
REDUCED_PULSE_LENGTH_FACTOR = 0.5  # Halve the pulse length
REDUCED_MOTOR_SPEED_FACTOR = 0.95  # Reduce motor speed by 15%

# Type definitions
MotorType = Literal[
    "first_vibration_hopper_motor",
    "second_vibration_hopper_motor",
    "feeder_conveyor_motor",
]


# Motor states runtime variables
class MotorStateRuntimeVariables(TypedDict, total=False):
    motor_start_time: Optional[float]
    motor_type: Optional[MotorType]
    motor_running: Optional[bool]


# Timeout states runtime variables
class ClassifyingRuntimeVariables(TypedDict, total=False):
    classifying_timeout_start_ts: Optional[float]


class WaitingForObjectToAppearRuntimeVariables(TypedDict, total=False):
    waiting_for_object_to_appear_timeout_start_ts: Optional[float]


class WaitingForObjectToCenterRuntimeVariables(TypedDict, total=False):
    waiting_for_object_to_center_timeout_start_ts: Optional[float]


class FsObjectUnderneathExitOfFirstFeederRuntimeVariables(TypedDict, total=False):
    fs_object_at_end_of_second_feeder_timeout_start_ts: Optional[float]
    first_feeder_pulse_count: Optional[int]


# States with no runtime variables
class EmptyRuntimeVariables(TypedDict, total=False):
    pass


StateMachineRuntimeVariables = Dict[SortingState, Dict]

"""
STATE MACHINE OVERVIEW:

GETTING_NEW_OBJECT_FROM_FEEDER:
- Analyzes feeder camera to determine which feeder state to transition to
- Does not run motors directly, only determines next state
- CLEAN RULE HIERARCHY:
  1. Main camera: Object centered → CLASSIFYING
  2. Main camera: Object detected but not centered → WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
  3. Feeder camera: Object touching main conveyor edges → WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
  4. Objects on second feeder >SECOND_FEEDER_DISTANCE_THRESHOLD from first feeder → FS_OBJECT_AT_END_OF_SECOND_FEEDER (run second feeder)
  5. Objects on second feeder close to first + objects on first feeder → FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER (run first feeder)
  6. Objects on second feeder + empty first feeder → FS_FIRST_FEEDER_EMPTY (wait)
  7. Objects only on first feeder → FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER (run first feeder)
  8. No objects anywhere → FS_FIRST_FEEDER_EMPTY

FS_OBJECT_AT_END_OF_SECOND_FEEDER:
- Pulses second feeder motor to move objects forward
- Triggered when object >50% surrounded by second feeder AND >SECOND_FEEDER_DISTANCE_THRESHOLD from first feeder
- Represents objects in the dropzone that are far from the first feeder
- Transitions when objects move or are cleared

FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
- Pulses second feeder motor to clear objects blocking first feeder exit
- Transitions when first feeder exit is clear

FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
- Pulses first feeder motor to move objects from first to second feeder
- Triggered when: object >50% on second feeder and >SECOND_FEEDER_DISTANCE_THRESHOLD from first feeder, OR object >50% in first feeder
- Transitions when objects appear underneath first feeder exit

FS_FIRST_FEEDER_EMPTY:
- Wait state - no objects detected in first feeder
- Transitions when objects appear in first feeder

WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA:
- Wait state - object detected touching main conveyor edges in feeder camera (using edge proximity detection)
- Triggered when >50% of object pixels are within 3px of main conveyor mask edges
- Transitions when object appears under main camera

WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA:
- Wait state - object detected under main camera but not centered
- Transitions when object moves to center position

CLASSIFYING:
- Wait state - object is centered and ready for classification
- Transitions to SENDING_OBJECT_TO_BIN after classification

SENDING_OBJECT_TO_BIN:
- Wait state - object is being sorted to appropriate bin
- Transitions back to GETTING_NEW_OBJECT_FROM_FEEDER when complete
"""


class SortingStateMachine:
    def __init__(
        self,
        vision_system: SegmentationModelManager,
        irl_interface: IRLSystemInterface,
        websocket_manager: WebSocketManager,
        encoder_manager: EncoderManager,
        bin_state_tracker: BinStateTracker,
    ):
        self.vision_system = vision_system
        self.irl_interface = irl_interface
        self.websocket_manager = websocket_manager
        self.encoder_manager = encoder_manager
        self.bin_state_tracker = bin_state_tracker
        self.current_state = SortingState.GETTING_NEW_OBJECT_FROM_FEEDER
        self.logger = vision_system.logger

        # Initialize runtime variables for all states
        self.runtime_variables: StateMachineRuntimeVariables = {}
        for state in SortingState:
            self.runtime_variables[state] = {}

        # Known objects for classification
        self.known_objects: Dict[str, KnownObject] = {}

        # Pending object being sent to bin
        self.pending_known_object: Optional[KnownObject] = None

    def step(self):
        # Execute current state's action and get next state
        next_state = None
        if self.current_state == SortingState.GETTING_NEW_OBJECT_FROM_FEEDER:
            next_state = self._runGettingNewObjectFromFeeder()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
        ):
            next_state = self._runWaitingForObjectToAppearUnderMainCamera()
        elif (
            self.current_state
            == SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            next_state = self._runWaitingForObjectToCenterUnderMainCamera()
        elif self.current_state == SortingState.CLASSIFYING:
            next_state = self._runClassifying()
        elif self.current_state == SortingState.SENDING_OBJECT_TO_BIN:
            next_state = self._runSendingObjectToBin()
        elif self.current_state == SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER:
            next_state = self._runFsObjectAtEndOfSecondFeeder()
        elif (
            self.current_state == SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        ):
            next_state = self._runFsObjectUnderneathExitOfFirstFeeder()
        elif (
            self.current_state
            == SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        ):
            next_state = self._runFsNoObjectUnderneathExitOfFirstFeeder()
        elif self.current_state == SortingState.FS_FIRST_FEEDER_EMPTY:
            next_state = self._runFsFirstFeederEmpty()

        # Transition if needed
        if next_state and next_state != self.current_state:
            self.logger.info(
                f"STATE TRANSITION: {self.current_state.value} -> {next_state.value}"
            )
            self.cleanupRuntimeVariables(self.current_state)
            self.setMotorsToDefaultSpeed()
            self.current_state = next_state
        time.sleep(0.02)

    def _runGettingNewObjectFromFeeder(self) -> SortingState:
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runWaitingForObjectToAppearUnderMainCamera(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "waiting_for_object_to_appear_timeout_start_ts" not in state_vars:
            state_vars["waiting_for_object_to_appear_timeout_start_ts"] = current_time

        start_time = state_vars["waiting_for_object_to_appear_timeout_start_ts"]
        timeout_duration = gc["waiting_for_object_to_appear_timeout_ms"] / 1000.0
        if current_time - start_time >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: {self.current_state.value} timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runWaitingForObjectToCenterUnderMainCamera(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "waiting_for_object_to_center_timeout_start_ts" not in state_vars:
            state_vars["waiting_for_object_to_center_timeout_start_ts"] = current_time

        start_time = state_vars["waiting_for_object_to_center_timeout_start_ts"]
        timeout_duration = gc["waiting_for_object_to_center_timeout_ms"] / 1000.0
        if current_time - start_time >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: {self.current_state.value} timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runClassifying(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "classifying_timeout_start_ts" not in state_vars:
            state_vars["classifying_timeout_start_ts"] = current_time

            # Set conveyor speed to zero
            if not gc["disable_main_conveyor"]:
                main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
                main_conveyor.setSpeed(0)
                self.logger.info("CLASSIFYING: Set main conveyor speed to zero")

            # Get the centered object ID
            centered_object_id = self.vision_system.getCurrentCenteredObjectId()

            if centered_object_id:
                # Build known object for this track ID
                frames = self.vision_system.getFramesForTrackId(centered_object_id)

                if frames:
                    # Create initial known object and send to frontend
                    object_uuid = str(uuid.uuid4())

                    # Get bounding box from current results for cropping
                    current_results = self.vision_system._getMainCameraResults()
                    cropped_image = None

                    if current_results:
                        for result in current_results:
                            if (
                                result.masks is not None
                                and hasattr(result, "boxes")
                                and result.boxes.id is not None
                            ):
                                for i, mask in enumerate(result.masks):
                                    if i < len(result.boxes.id):
                                        track_id = str(int(result.boxes.id[i].item()))
                                        if track_id == centered_object_id:
                                            bbox_tensor = result.boxes[i].xyxy[0]
                                            bbox = BoundingBox(
                                                x1=int(bbox_tensor[0].item()),
                                                y1=int(bbox_tensor[1].item()),
                                                x2=int(bbox_tensor[2].item()),
                                                y2=int(bbox_tensor[3].item()),
                                            )
                                            cropped_image = cropImageToBbox(
                                                frames[0], bbox
                                            )
                                            break

                    # Send initial known object event
                    self.logger.info(
                        f"WEBSOCKET: Sending initial known object event for UUID {object_uuid}"
                    )
                    self.websocket_manager.broadcastKnownObject(
                        uuid=object_uuid,
                        main_camera_id=centered_object_id,
                        image=cropped_image,
                    )

                    # Take up to 5 frames
                    selected_frames = frames[:5]
                    classification_results = []

                    # Classify each frame
                    for frame in selected_frames:
                        result = classifyPiece([frame], gc)
                        if result:
                            classification_results.append(result)

                    # Calculate consensus
                    if classification_results:
                        id_counts = Counter([r["id"] for r in classification_results])
                        category_counts = Counter(
                            [r["category_id"] for r in classification_results]
                        )

                        most_common_id = (
                            id_counts.most_common(1)[0][0] if id_counts else ""
                        )
                        most_common_category = (
                            category_counts.most_common(1)[0][0]
                            if category_counts
                            else ""
                        )

                        consensus = ClassificationConsensus(
                            id=most_common_id, category_id=most_common_category
                        )

                        # Determine bin coordinates for this classification
                        bin_coordinates = self._determineBinCoordinates(
                            most_common_category
                        )

                        # Create and store known object
                        known_object = KnownObject(
                            uuid=object_uuid,
                            main_camera_id=centered_object_id,
                            observations=[],  # Not needed for this simplified approach
                            classification_consensus=consensus,
                            bin_coordinates=bin_coordinates,
                        )
                        self.known_objects[centered_object_id] = known_object
                        self.pending_known_object = known_object

                        # Send classification update
                        self.logger.info(
                            f"WEBSOCKET: Sending classification update for UUID {object_uuid}: {most_common_id} (category: {most_common_category})"
                        )
                        self.websocket_manager.broadcastKnownObject(
                            uuid=object_uuid,
                            classification_id=most_common_id,
                            bin_coordinates=bin_coordinates,
                        )

                        self.logger.info(f"CLASSIFICATION CONSENSUS: {consensus}")
                    else:
                        self.logger.warning("No valid classification results obtained")
                else:
                    self.logger.warning("No complete frames found for track ID")
            else:
                self.logger.warning("No centered object found for classification")

            # Go to sending object to bin state
            return SortingState.SENDING_OBJECT_TO_BIN

        start_time = state_vars["classifying_timeout_start_ts"]
        timeout_duration = gc["classifying_timeout_ms"] / 1000.0
        if current_time - start_time >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: {self.current_state.value} timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        return self.current_state

    def _runSendingObjectToBin(self) -> SortingState:
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        gc = self.vision_system.global_config

        if "sending_object_to_bin_start_ts" not in state_vars:
            state_vars["sending_object_to_bin_start_ts"] = current_time

            if (
                self.pending_known_object
                and self.pending_known_object["bin_coordinates"]
            ):
                bin_coords = self.pending_known_object["bin_coordinates"]
                self.logger.info(
                    f"SENDING_OBJECT_TO_BIN: Starting for bin {bin_coords}"
                )

                # Open doors for the target bin
                self._openDoorsForBin(bin_coords)

                # Turn on main conveyor only
                if not gc["disable_main_conveyor"]:
                    main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
                    main_speed = self.irl_interface["runtime_params"][
                        "main_conveyor_speed"
                    ]
                    main_conveyor.setSpeed(main_speed)
                    self.logger.info("SENDING_OBJECT_TO_BIN: Main conveyor started")

                # Record start timestamp for distance calculation
                state_vars["conveyor_start_timestamp"] = current_time
            else:
                self.logger.warning(
                    "SENDING_OBJECT_TO_BIN: No pending known object or bin coordinates"
                )
                return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        # Check if we have traveled the required distance
        if self.pending_known_object and self.pending_known_object["bin_coordinates"]:
            bin_coords = self.pending_known_object["bin_coordinates"]
            target_distance = self._getDistanceToDistributionModule(
                bin_coords["distribution_module_idx"]
            )

            start_timestamp = state_vars.get("conveyor_start_timestamp", current_time)
            distance_traveled = self.encoder_manager.getDistanceTraveledSince(
                start_timestamp
            )

            self.logger.info(
                f"SENDING_OBJECT_TO_BIN: Distance traveled: {distance_traveled} cm, target distance {target_distance}"
            )

            if distance_traveled >= target_distance:
                if "conveyor_door_close_start_ts" not in state_vars:
                    # Wait conveyor_door_close_delay_ms before closing doors
                    state_vars["conveyor_door_close_start_ts"] = current_time
                    self.logger.info(
                        "SENDING_OBJECT_TO_BIN: Target distance reached, starting door close delay"
                    )

                close_start_time = state_vars["conveyor_door_close_start_ts"]
                conveyor_delay = gc["conveyor_door_close_delay_ms"] / 1000.0

                if current_time - close_start_time >= conveyor_delay:
                    if "conveyor_door_closed" not in state_vars:
                        # Close conveyor door gradually
                        self._closeConveyorDoorGradually(
                            bin_coords["distribution_module_idx"]
                        )
                        state_vars["conveyor_door_closed"] = True
                        state_vars["bin_door_close_start_ts"] = current_time
                        self.logger.info(
                            "SENDING_OBJECT_TO_BIN: Conveyor door closed, starting bin door delay"
                        )

                    bin_close_start_time = state_vars.get(
                        "bin_door_close_start_ts", current_time
                    )
                    bin_delay = gc["bin_door_close_delay_ms"] / 1000.0

                    if current_time - bin_close_start_time >= bin_delay:
                        # Close bin door and finish
                        self._closeBinDoor(bin_coords)
                        self.pending_known_object = None
                        self.logger.info("SENDING_OBJECT_TO_BIN: Sequence complete")
                        return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        return self.current_state

    def _runFsObjectAtEndOfSecondFeeder(self) -> SortingState:
        self._startMotorPulseIfNeeded(
            "second_vibration_hopper_motor", use_reduced_settings=True
        )
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runFsObjectUnderneathExitOfFirstFeeder(self) -> SortingState:
        gc = self.vision_system.global_config
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()

        # Initialize timeout tracking on first entry
        if "fs_object_at_end_of_second_feeder_timeout_start_ts" not in state_vars:
            state_vars["fs_object_at_end_of_second_feeder_timeout_start_ts"] = (
                current_time
            )
            state_vars["first_feeder_pulse_count"] = 0
            self.logger.info(
                "FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER: Starting timeout tracking"
            )

        # Check if timeout has expired
        timeout_start = state_vars["fs_object_at_end_of_second_feeder_timeout_start_ts"]
        timeout_duration = gc["fs_object_at_end_of_second_feeder_timeout_ms"] / 1000.0
        pulse_count = state_vars.get("first_feeder_pulse_count", 0)

        if current_time - timeout_start >= timeout_duration and pulse_count < 2:
            self.logger.info(
                f"FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER: Timeout expired, pulsing first feeder (count: {pulse_count + 1}/2)"
            )
            self._startMotorPulseIfNeeded("first_vibration_hopper_motor")
            state_vars["first_feeder_pulse_count"] = pulse_count + 1
            state_vars["fs_object_at_end_of_second_feeder_timeout_start_ts"] = (
                current_time  # Reset timeout
            )
        else:
            self._startMotorPulseIfNeeded("second_vibration_hopper_motor")

        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runFsNoObjectUnderneathExitOfFirstFeeder(self) -> SortingState:
        self._startMotorPulseIfNeeded("first_vibration_hopper_motor")
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _runFsFirstFeederEmpty(self) -> SortingState:
        next_state = self._determineNextStateFromFrameAnalysis()
        return next_state or self.current_state

    def _startMotorPulseIfNeeded(
        self, motor_type: MotorType, use_reduced_settings: bool = False
    ):
        state_vars = self.runtime_variables[self.current_state]
        current_time = time.time()
        runtime_params = self.irl_interface["runtime_params"]

        # Check if motor is already running
        if (
            state_vars.get("motor_running")
            and state_vars.get("motor_type") == motor_type
        ):
            # Check if pulse duration has elapsed
            if motor_type == "first_vibration_hopper_motor":
                pulse_duration = (
                    runtime_params["first_vibration_hopper_motor_pulse_ms"] / 1000.0
                )
            elif motor_type == "second_vibration_hopper_motor":
                pulse_duration = (
                    runtime_params["second_vibration_hopper_motor_pulse_ms"] / 1000.0
                )
                if use_reduced_settings:
                    pulse_duration *= REDUCED_PULSE_LENGTH_FACTOR
            else:  # feeder_conveyor_motor
                pulse_duration = runtime_params["feeder_conveyor_pulse_ms"] / 1000.0

            start_time = state_vars.get("motor_start_time") or 0.0
            if current_time - start_time >= pulse_duration:
                # Stop pulse and start backstop
                self._stopMotorPulse(motor_type)
                state_vars["motor_running"] = False
                state_vars["motor_start_time"] = current_time  # Start pause timer
            return

        # Check if we're in pause period
        if not state_vars.get("motor_running") and state_vars.get("motor_start_time"):
            if motor_type == "first_vibration_hopper_motor":
                pause_duration = (
                    runtime_params["first_vibration_hopper_motor_pause_ms"] / 1000.0
                )
            elif motor_type == "second_vibration_hopper_motor":
                pause_duration = (
                    runtime_params["second_vibration_hopper_motor_pause_ms"] / 1000.0
                )
            else:  # feeder_conveyor_motor
                pause_duration = runtime_params["feeder_conveyor_pause_ms"] / 1000.0

            start_time = state_vars.get("motor_start_time") or 0.0
            if current_time - start_time < pause_duration:
                return  # Still pausing

        # Start new pulse
        if not state_vars.get("motor_running"):
            self._startMotorPulse(motor_type, use_reduced_settings)
            state_vars["motor_running"] = True
            state_vars["motor_type"] = motor_type
            state_vars["motor_start_time"] = current_time

    def _startMotorPulse(
        self, motor_type: MotorType, use_reduced_settings: bool = False
    ):
        runtime_params = self.irl_interface["runtime_params"]

        if motor_type == "first_vibration_hopper_motor":
            speed = runtime_params["first_vibration_hopper_motor_speed"]
            motor = self.irl_interface["first_vibration_hopper_motor"]
            self.logger.info(f"MOTOR: Starting first feeder motor at speed {speed}")
        elif motor_type == "second_vibration_hopper_motor":
            speed = runtime_params["second_vibration_hopper_motor_speed"]
            if use_reduced_settings:
                speed = int(speed * REDUCED_MOTOR_SPEED_FACTOR)
            motor = self.irl_interface["second_vibration_hopper_motor"]
            speed_info = f" (reduced)" if use_reduced_settings else ""
            self.logger.info(
                f"MOTOR: Starting second feeder motor at speed {speed}{speed_info}"
            )
        elif motor_type == "feeder_conveyor_motor":
            speed = runtime_params["feeder_conveyor_speed"]
            motor = self.irl_interface["feeder_conveyor_dc_motor"]
            self.logger.info(f"MOTOR: Starting feeder conveyor motor at speed {speed}")
        else:
            self.logger.error(f"Unknown motor type: {motor_type}")
            return

        motor.setSpeed(speed)

    def _stopMotorPulse(self, motor_type: MotorType):
        runtime_params = self.irl_interface["runtime_params"]

        if motor_type == "first_vibration_hopper_motor":
            speed = runtime_params["first_vibration_hopper_motor_speed"]
            motor = self.irl_interface["first_vibration_hopper_motor"]
        elif motor_type == "second_vibration_hopper_motor":
            speed = runtime_params["second_vibration_hopper_motor_speed"]
            motor = self.irl_interface["second_vibration_hopper_motor"]
        elif motor_type == "feeder_conveyor_motor":
            speed = runtime_params["feeder_conveyor_speed"]
            motor = self.irl_interface["feeder_conveyor_dc_motor"]
        else:
            self.logger.error(f"Unknown motor type: {motor_type}")
            return

        self.logger.info(f"MOTOR: Backstopping {motor_type} motor after pulse")
        motor.backstop(speed)

    def _determineFeederState(self) -> Optional[SortingState]:
        feeder_state = self.vision_system.determineFeederState()

        self.logger.info(f"FEEDER ANALYSIS: Feeder state = {feeder_state}")

        if feeder_state is None:
            return None

        # Map FeederState to SortingState
        if feeder_state == FeederState.OBJECT_AT_END_OF_SECOND_FEEDER:
            return SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER
        elif feeder_state == FeederState.OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
            return SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        elif feeder_state == FeederState.NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
            return SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
        elif feeder_state == FeederState.FIRST_FEEDER_EMPTY:
            return SortingState.FS_FIRST_FEEDER_EMPTY
        elif feeder_state == FeederState.OBJECT_ON_MAIN_CONVEYOR:
            return SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA
        else:
            self.logger.error(f"Unknown feeder state: {feeder_state}")
            return None

    def _determineNextStateFromFrameAnalysis(self) -> Optional[SortingState]:
        # Check main camera first for higher priority states
        main_camera_state = self.vision_system.determineMainCameraState()

        # Map MainCameraState to SortingState
        if main_camera_state == MainCameraState.OBJECT_CENTERED_UNDER_MAIN_CAMERA:
            return SortingState.CLASSIFYING
        elif (
            main_camera_state
            == MainCameraState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA
        ):
            return SortingState.WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA

        # Check feeder camera for objects on main conveyor (in feeder view)
        if self.vision_system.hasObjectOnMainConveyorInFeederView():
            # note: going to need to add a threshold wait in this state while the object goes from camera to camera
            return SortingState.WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA

        # Check feeder states in priority order
        feeder_state = self._determineFeederState()
        if feeder_state:
            if feeder_state == SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER:
                return SortingState.FS_OBJECT_AT_END_OF_SECOND_FEEDER
            elif feeder_state == SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER:
                return SortingState.FS_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            elif (
                feeder_state
                == SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            ):
                return SortingState.FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER
            elif feeder_state == SortingState.FS_FIRST_FEEDER_EMPTY:
                return SortingState.FS_FIRST_FEEDER_EMPTY

        return None

    def cleanupRuntimeVariables(self, state: SortingState):
        self.runtime_variables[state] = {}

    def setMotorsToDefaultSpeed(self):
        gc = self.vision_system.global_config

        # Stop vibration motors with backstop
        if not gc["disable_first_vibration_hopper_motor"]:
            first_motor = self.irl_interface["first_vibration_hopper_motor"]
            first_speed = self.irl_interface["runtime_params"][
                "first_vibration_hopper_motor_speed"
            ]
            first_motor.backstop(first_speed)

        if not gc["disable_second_vibration_hopper_motor"]:
            second_motor = self.irl_interface["second_vibration_hopper_motor"]
            second_speed = self.irl_interface["runtime_params"][
                "second_vibration_hopper_motor_speed"
            ]
            second_motor.backstop(second_speed)

        # Set main conveyor to default speed
        if not gc["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            main_conveyor.setSpeed(main_speed)

    def _determineBinCoordinates(self, category_id: str) -> Optional[BinCoordinates]:
        if not category_id:
            return None

        # Use bin state tracker to find available bin for this category
        bin_coordinates = self.bin_state_tracker.findAvailableBin(category_id)
        if bin_coordinates:
            # Reserve the bin for this category
            self.bin_state_tracker.reserveBin(bin_coordinates, category_id)
            self.logger.info(
                f"BINS: Assigned category {category_id} to bin {bin_coordinates}"
            )
            return bin_coordinates
        else:
            self.logger.warning(
                f"BINS: No available bin found for category {category_id}"
            )
            return None

    def _getDistanceToDistributionModule(self, distribution_module_idx: int) -> float:
        if distribution_module_idx < len(self.irl_interface["distribution_modules"]):
            module = self.irl_interface["distribution_modules"][distribution_module_idx]
            return float(module.distance_from_camera_center_to_door_begin_cm)
        return 0.0

    def _openDoorsForBin(self, bin_coords: BinCoordinates) -> None:
        distribution_modules = self.irl_interface["distribution_modules"]
        gc = self.vision_system.global_config

        if bin_coords["distribution_module_idx"] < len(distribution_modules):
            module = distribution_modules[bin_coords["distribution_module_idx"]]

            # Open conveyor door
            conveyor_open_angle = gc["conveyor_door_open_angle"]
            module.servo.setAngle(conveyor_open_angle)
            self.logger.info(
                f"DOOR: Opened conveyor door for module {bin_coords['distribution_module_idx']} to {conveyor_open_angle}°"
            )

            # Open bin door
            if bin_coords["bin_idx"] < len(module.bins):
                bin_servo = module.bins[bin_coords["bin_idx"]].servo
                bin_open_angle = gc["bin_door_open_angle"]
                bin_servo.setAngle(bin_open_angle)
                self.logger.info(
                    f"DOOR: Opened bin door {bin_coords['bin_idx']} in module {bin_coords['distribution_module_idx']} to {bin_open_angle}°"
                )

    def _closeConveyorDoorGradually(self, distribution_module_idx: int) -> None:
        distribution_modules = self.irl_interface["distribution_modules"]
        gc = self.vision_system.global_config

        if distribution_module_idx < len(distribution_modules):
            module = distribution_modules[distribution_module_idx]
            # Close conveyor door gradually (2 second duration)
            conveyor_closed_angle = gc["conveyor_door_closed_angle"]
            module.servo.setAngle(conveyor_closed_angle, 2000)
            self.logger.info(
                f"DOOR: Closing conveyor door gradually for module {distribution_module_idx} to {conveyor_closed_angle}°"
            )

    def _closeBinDoor(self, bin_coords: BinCoordinates) -> None:
        distribution_modules = self.irl_interface["distribution_modules"]
        gc = self.vision_system.global_config

        if bin_coords["distribution_module_idx"] < len(distribution_modules):
            module = distribution_modules[bin_coords["distribution_module_idx"]]
            if bin_coords["bin_idx"] < len(module.bins):
                bin_servo = module.bins[bin_coords["bin_idx"]].servo
                bin_closed_angle = gc["bin_door_closed_angle"]
                bin_servo.setAngle(bin_closed_angle)
                self.logger.info(
                    f"DOOR: Closed bin door {bin_coords['bin_idx']} in module {bin_coords['distribution_module_idx']} to {bin_closed_angle}°"
                )
