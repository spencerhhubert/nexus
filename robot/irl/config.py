from pyfirmata import util, pyfirmata
from robot.irl.our_arduino import OurArduinoMega
from robot.irl.motors import PCA9685, Servo, DCMotor
from robot.irl.distribution import Bin, DistributionModule
from robot.irl.camera import Camera, connectToCamera
from robot.irl.camera_calibration import CameraCalibration, CameraCalibrationMeasurement
from typing import Dict, List, Tuple, TypedDict, Optional
import os
import subprocess
import re
from robot.global_config import GlobalConfig
from robot.util.units import inchesToCm


class ServoMotorConfig(TypedDict):
    channel: int


class DistributionModuleConfig(TypedDict):
    distance_from_camera_center_to_door_begin_cm: int
    num_bins: int
    controller_address: int
    conveyor_door_servo: ServoMotorConfig
    bin_door_servos: List[ServoMotorConfig]


class DCMotorConfig(TypedDict):
    enable_pin: int
    input_1_pin: int
    input_2_pin: int


class MainCameraConfig(TypedDict):
    device_index: int
    width: int
    height: int
    fps: int
    calibration_measurements: List[CameraCalibrationMeasurement]


class IRLConfig(TypedDict):
    mc_path: str
    distribution_modules: List[DistributionModuleConfig]
    main_conveyor_dc_motor: DCMotorConfig
    feeder_conveyor_dc_motor: DCMotorConfig
    vibration_hopper_dc_motor: DCMotorConfig
    main_camera: MainCameraConfig


class IRLSystemInterface(TypedDict):
    arduino: OurArduinoMega
    distribution_modules: List[DistributionModule]
    main_conveyor_dc_motor: DCMotor
    feeder_conveyor_dc_motor: DCMotor
    vibration_hopper_dc_motor: DCMotor
    main_camera: Camera


def buildIRLConfig() -> IRLConfig:
    mc_path = os.getenv("MC_PATH")
    if mc_path is None:
        raise ValueError("MC_PATH environment variable must be set")

    camera_index = os.getenv("CAMERA_INDEX")
    if camera_index is None:
        raise ValueError("CAMERA_INDEX environment variable must be set")

    return {
        "mc_path": mc_path,
        "main_camera": {
            "device_index": int(camera_index),
            # "width": 1920,
            # "height": 1080,
            "width": 3840,
            "height": 2160,
            "fps": 10,
            "calibration_measurements": [
                {
                    "distance_down_from_top_of_frame_percent": 0.245,
                    "physical_distance_on_floor_across_frame_cm": inchesToCm(
                        8 + 10 / 16
                    ),
                },
                {
                    "distance_down_from_top_of_frame_percent": 0.885,
                    "physical_distance_on_floor_across_frame_cm": inchesToCm(
                        5 + 6 / 16
                    ),
                },
            ],
        },
        "distribution_modules": [
            {
                "distance_from_camera_center_to_door_begin_cm": int(
                    inchesToCm(7 + 3 / 16)
                ),
                "num_bins": 4,
                "controller_address": 0x41,
                "conveyor_door_servo": {"channel": 15},
                "bin_door_servos": [
                    {"channel": 0},
                    {"channel": 1},
                    {"channel": 2},
                    {"channel": 3},
                ],
            },
            {
                "distance_from_camera_center_to_door_begin_cm": int(
                    inchesToCm(7 + 3 / 16 + (6 + 2 / 16))
                ),
                "num_bins": 4,
                "controller_address": 0x42,
                "conveyor_door_servo": {"channel": 15},
                "bin_door_servos": [
                    {"channel": 0},
                    {"channel": 1},
                    {"channel": 2},
                    {"channel": 3},
                ],
            },
            {
                "distance_from_camera_center_to_door_begin_cm": int(
                    inchesToCm(7 + 3 / 16 + 2 * (6 + 2 / 16))
                ),
                "num_bins": 4,
                "controller_address": 0x40,
                "conveyor_door_servo": {"channel": 15},
                "bin_door_servos": [
                    {"channel": 0},
                    {"channel": 1},
                    {"channel": 2},
                    {"channel": 3},
                ],
            },
        ],
        "vibration_hopper_dc_motor": {
            "enable_pin": 3,
            "input_1_pin": 22,
            "input_2_pin": 24,
        },
        "main_conveyor_dc_motor": {
            "enable_pin": 5,
            "input_1_pin": 26,
            "input_2_pin": 28,
        },
        "feeder_conveyor_dc_motor": {
            "enable_pin": 6,
            "input_1_pin": 30,
            "input_2_pin": 32,
        },
    }


def discoverArduinoBoard() -> Optional[str]:
    try:
        result = subprocess.run(
            ["arduino-cli", "board", "list"], capture_output=True, text=True, check=True
        )

        for line in result.stdout.split("\n"):
            if "Arduino Mega" in line and "Serial Port (USB)" in line:
                parts = line.split()
                if parts:
                    return parts[0]

        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def connectToArduino(mc_path: str, gc: GlobalConfig) -> OurArduinoMega:
    logger = gc["logger"]
    auto_confirm = gc["auto_confirm"]

    DELAY_BETWEEN_FIRMATA_COMMANDS_MS = 100

    try:
        logger.info(f"Attempting to connect to Arduino at {mc_path}")
        mc = OurArduinoMega(gc, mc_path, DELAY_BETWEEN_FIRMATA_COMMANDS_MS)
        return mc
    except Exception as e:
        logger.error(f"Failed to connect to Arduino at {mc_path}: {e}")

        discovered_path = discoverArduinoBoard()
        if discovered_path is None:
            logger.error(
                f"Failed to connect to Arduino at {mc_path} and could not discover any Arduino Mega boards"
            )
            raise e

        if not auto_confirm:
            response = input(
                f"Failed to use board from environment at {mc_path}. Would you like to automatically try to use discovered board at {discovered_path}? (y/N): "
            )
            if response.lower() not in ["y", "yes"]:
                logger.warning("User declined to use discovered board")
                raise e

        logger.info(f"Attempting to connect to discovered Arduino at {discovered_path}")

        try:
            mc = OurArduinoMega(gc, discovered_path, DELAY_BETWEEN_FIRMATA_COMMANDS_MS)
            logger.info(f"Successfully connected to Arduino at {discovered_path}")
            return mc
        except Exception as discovery_error:
            logger.error(
                f"Failed to connect to discovered board at {discovered_path}: {discovery_error}"
            )
            raise e


def buildIRLSystemInterface(config: IRLConfig, gc: GlobalConfig) -> IRLSystemInterface:
    mc = connectToArduino(config["mc_path"], gc)
    logger = gc["logger"]
    if gc["debug_level"] > 0:
        it = util.Iterator(mc)
        it.start()

        def messageHandler(*args, **kwargs) -> None:
            logger.info(util.two_byte_iter_to_str(args))

        mc.add_cmd_handler(pyfirmata.STRING_DATA, messageHandler)

    dms = []
    for distribution_module_idx, dm in enumerate(config["distribution_modules"]):
        servo_controller = PCA9685(gc, mc, dm["controller_address"])
        chute_servo = Servo(gc, dm["conveyor_door_servo"]["channel"], servo_controller)
        bins = [
            Bin(gc, Servo(gc, servo_config["channel"], servo_controller), "", i)
            for i, servo_config in enumerate(dm["bin_door_servos"])
        ]
        dms.append(
            DistributionModule(
                gc,
                chute_servo,
                dm["distance_from_camera_center_to_door_begin_cm"],
                bins,
                distribution_module_idx,
            )
        )

    main_conveyor_motor = DCMotor(
        gc,
        mc,
        config["main_conveyor_dc_motor"]["enable_pin"],
        config["main_conveyor_dc_motor"]["input_1_pin"],
        config["main_conveyor_dc_motor"]["input_2_pin"],
    )

    feeder_conveyor_motor = DCMotor(
        gc,
        mc,
        config["feeder_conveyor_dc_motor"]["enable_pin"],
        config["feeder_conveyor_dc_motor"]["input_1_pin"],
        config["feeder_conveyor_dc_motor"]["input_2_pin"],
    )

    vibration_hopper_motor = DCMotor(
        gc,
        mc,
        config["vibration_hopper_dc_motor"]["enable_pin"],
        config["vibration_hopper_dc_motor"]["input_1_pin"],
        config["vibration_hopper_dc_motor"]["input_2_pin"],
    )

    camera_calibration = CameraCalibration(
        gc,
        config["main_camera"]["width"],
        config["main_camera"]["height"],
        config["main_camera"]["calibration_measurements"],
    )

    main_camera = connectToCamera(
        config["main_camera"]["device_index"],
        gc,
        config["main_camera"]["width"],
        config["main_camera"]["height"],
        config["main_camera"]["fps"],
        camera_calibration,
    )

    main_camera.tempSaveFrameWithCalibrationInfo()

    return {
        "arduino": mc,
        "distribution_modules": dms,
        "main_conveyor_dc_motor": main_conveyor_motor,
        "feeder_conveyor_dc_motor": feeder_conveyor_motor,
        "vibration_hopper_dc_motor": vibration_hopper_motor,
        "main_camera": main_camera,
    }
