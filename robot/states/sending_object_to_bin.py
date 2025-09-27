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


class SendingObjectToBin(BaseState):
    def __init__(
        self,
        global_config,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
        encoder_manager: EncoderManager,
    ):
        super().__init__(global_config, vision_system, websocket_manager, irl_interface)
        self.encoder_manager = encoder_manager
        self.logger = global_config["logger"].ctx(state="SendingObjectToBin")

        self.start_ts: Optional[float] = None
        self.conveyor_start_timestamp: Optional[float] = None
        self.conveyor_door_close_start_ts: Optional[float] = None
        self.conveyor_door_closed: bool = False
        self.bin_door_close_start_ts: Optional[float] = None
        self.pending_known_object: Optional[KnownObject] = None

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()

        current_time = time.time()

        if self.start_ts is None:
            self.start_ts = current_time

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
                if not self.global_config["disable_main_conveyor"]:
                    main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
                    main_speed = self.irl_interface["runtime_params"][
                        "main_conveyor_speed"
                    ]
                    EXTRA_SPEED = 100
                    main_conveyor.setSpeed(main_speed + EXTRA_SPEED)
                    self.logger.info("SENDING_OBJECT_TO_BIN: Main conveyor started")

                # Record start timestamp for distance calculation
                self.conveyor_start_timestamp = current_time
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

            start_timestamp = self.conveyor_start_timestamp or current_time
            distance_traveled = self.encoder_manager.getDistanceTraveledSince(
                start_timestamp
            )

            self.logger.info(
                f"SENDING_OBJECT_TO_BIN: Distance traveled: {distance_traveled} cm, target distance {target_distance}"
            )

            if distance_traveled >= target_distance:
                if self.conveyor_door_close_start_ts is None:
                    # Wait conveyor_door_close_delay_ms before closing doors
                    self.conveyor_door_close_start_ts = current_time
                    self.logger.info(
                        "SENDING_OBJECT_TO_BIN: Target distance reached, starting door close delay"
                    )

                conveyor_delay = (
                    self.global_config["conveyor_door_close_delay_ms"] / 1000.0
                )

                if current_time - self.conveyor_door_close_start_ts >= conveyor_delay:
                    if not self.conveyor_door_closed:
                        # Close conveyor door gradually
                        self._closeConveyorDoorGradually(
                            bin_coords["distribution_module_idx"]
                        )
                        self.conveyor_door_closed = True
                        self.bin_door_close_start_ts = current_time
                        self.logger.info(
                            "SENDING_OBJECT_TO_BIN: Conveyor door closed, starting bin door delay"
                        )

                    bin_close_start_time = self.bin_door_close_start_ts or current_time
                    bin_delay = self.global_config["bin_door_close_delay_ms"] / 1000.0

                    if current_time - bin_close_start_time >= bin_delay:
                        # Close bin door and finish
                        self._closeBinDoor(bin_coords)
                        self.pending_known_object = None
                        self.logger.info("SENDING_OBJECT_TO_BIN: Sequence complete")
                        return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        return None

    def cleanup(self) -> None:
        if not self.global_config["disable_main_conveyor"]:
            main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
            main_speed = self.irl_interface["runtime_params"]["main_conveyor_speed"]
            main_conveyor.setSpeed(main_speed)

        self.pending_known_object = None
        self.start_ts = None
        self.conveyor_start_timestamp = None
        self.conveyor_door_close_start_ts = None
        self.conveyor_door_closed = False
        self.bin_door_close_start_ts = None

        self.logger.info(
            "CLEANUP: Reset main conveyor and cleared SENDING_OBJECT_TO_BIN state"
        )

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
