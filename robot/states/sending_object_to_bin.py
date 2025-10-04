import time
from typing import Optional
from robot.states.base_state import BaseState
from robot.our_types.sorting import SortingState
from robot.our_types.known_object import KnownObject
from robot.our_types.bin import BinCoordinates
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.encoder_manager import EncoderManager
from robot.states.shared_variables import SharedVariables
from robot.global_config import GlobalConfig


DELAY_CHECK_ENCODER_MS = 100


class SendingObjectToBin(BaseState):
    def __init__(
        self,
        global_config: GlobalConfig,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
        encoder_manager: EncoderManager,
        shared_variables: SharedVariables,
    ):
        super().__init__(global_config, vision_system, websocket_manager, irl_interface)
        self.encoder_manager = encoder_manager
        self.shared_variables = shared_variables
        self.logger = global_config["logger"].ctx(state="SendingObjectToBin")
        self.sequence_complete = False

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()
        self._ensureExecutionThreadStarted()

        if self.sequence_complete:
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        return None

    def cleanup(self) -> None:
        super().cleanup()

        if not self.global_config["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            main_conveyor.setSpeed(main_speed)

        self.shared_variables.pending_known_object = None
        self.sequence_complete = False

        self.logger.info(
            "CLEANUP: Reset main conveyor and cleared SENDING_OBJECT_TO_BIN state"
        )

    def _executionLoop(self) -> None:
        if not (
            self.shared_variables.pending_known_object
            and self.shared_variables.pending_known_object["bin_coordinates"]
        ):
            self.logger.warning(
                "SENDING_OBJECT_TO_BIN: No pending known object or bin coordinates"
            )
            self.sequence_complete = True
            return

        bin_coords = self.shared_variables.pending_known_object["bin_coordinates"]
        self.logger.info(f"SENDING_OBJECT_TO_BIN: Starting for bin {bin_coords}")

        self._openDoorsForBin(bin_coords)

        if not self.global_config["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            EXTRA_SPEED = 100
            main_conveyor.setSpeed(main_speed + EXTRA_SPEED)
            self.logger.info("SENDING_OBJECT_TO_BIN: Main conveyor started")

        conveyor_start_timestamp = time.time()
        target_distance = self._getDistanceToDistributionModule(
            bin_coords["distribution_module_idx"]
        )

        while not self._stop_event.is_set():
            distance_traveled = self.encoder_manager.getDistanceTraveledSince(
                conveyor_start_timestamp
            )
            self.logger.info(
                f"SENDING_OBJECT_TO_BIN: Distance traveled: {distance_traveled} cm, target distance {target_distance}"
            )

            if distance_traveled >= target_distance:
                break

            time.sleep(DELAY_CHECK_ENCODER_MS / 1000)

        if self._stop_event.is_set():
            return

        conveyor_delay_ms = self.global_config["conveyor_door_close_delay_ms"]
        self.logger.info(
            "SENDING_OBJECT_TO_BIN: Target distance reached, starting door close delay"
        )
        time.sleep(conveyor_delay_ms / 1000.0)

        if self._stop_event.is_set():
            return

        self._closeConveyorDoorGradually(bin_coords["distribution_module_idx"])
        self.logger.info(
            "SENDING_OBJECT_TO_BIN: Conveyor door closed, starting bin door delay"
        )

        bin_delay_ms = self.global_config["bin_door_close_delay_ms"]
        time.sleep(bin_delay_ms / 1000.0)

        if self._stop_event.is_set():
            return

        self._closeBinDoor(bin_coords)
        self.shared_variables.pending_known_object = None
        self.logger.info("SENDING_OBJECT_TO_BIN: Sequence complete")

        self.sequence_complete = True

    def _getDistanceToDistributionModule(self, distribution_module_idx: int) -> float:
        if distribution_module_idx < len(self.irl_interface["distribution_modules"]):
            module = self.irl_interface["distribution_modules"][distribution_module_idx]
            return float(module.distance_from_camera_center_to_door_begin_cm)
        return 0.0

    def _openDoorsForBin(self, bin_coords: BinCoordinates) -> None:
        distribution_modules = self.irl_interface["distribution_modules"]

        if bin_coords["distribution_module_idx"] < len(distribution_modules):
            module = distribution_modules[bin_coords["distribution_module_idx"]]

            # Open conveyor door
            conveyor_open_angle = self.global_config["conveyor_door_open_angle"]
            module.servo.setAngle(conveyor_open_angle)
            self.logger.info(
                f"DOOR: Opened conveyor door for module {bin_coords['distribution_module_idx']} to {conveyor_open_angle}°"
            )

            # Open bin door
            if bin_coords["bin_idx"] < len(module.bins):
                bin_servo = module.bins[bin_coords["bin_idx"]].servo
                bin_open_angle = self.global_config["bin_door_open_angle"]
                bin_servo.setAngle(bin_open_angle)
                self.logger.info(
                    f"DOOR: Opened bin door {bin_coords['bin_idx']} in module {bin_coords['distribution_module_idx']} to {bin_open_angle}°"
                )

    def _closeConveyorDoorGradually(self, distribution_module_idx: int) -> None:
        distribution_modules = self.irl_interface["distribution_modules"]

        if distribution_module_idx < len(distribution_modules):
            module = distribution_modules[distribution_module_idx]
            # Close conveyor door gradually (2 second duration)
            conveyor_closed_angle = self.global_config["conveyor_door_closed_angle"]
            module.servo.setAngle(conveyor_closed_angle, 2000)
            self.logger.info(
                f"DOOR: Closing conveyor door gradually for module {distribution_module_idx} to {conveyor_closed_angle}°"
            )

    def _closeBinDoor(self, bin_coords: BinCoordinates) -> None:
        distribution_modules = self.irl_interface["distribution_modules"]

        if bin_coords["distribution_module_idx"] < len(distribution_modules):
            module = distribution_modules[bin_coords["distribution_module_idx"]]
            if bin_coords["bin_idx"] < len(module.bins):
                bin_servo = module.bins[bin_coords["bin_idx"]].servo
                bin_closed_angle = self.global_config["bin_door_closed_angle"]
                bin_servo.setAngle(bin_closed_angle)
                self.logger.info(
                    f"DOOR: Closed bin door {bin_coords['bin_idx']} in module {bin_coords['distribution_module_idx']} to {bin_closed_angle}°"
                )
