from pyfirmata import ArduinoMega, util, pyfirmata
from robot.irl.motors import PCA9685, Servo, DCMotor
from robot.irl.distribution import Bin, DistributionModule
from typing import Dict, List, Tuple, TypedDict, NewType
import os
from robot.global_config import GlobalConfig


class DistributionModuleConfig(TypedDict):
    distance_from_camera: int
    num_bins: int
    controller_address: int

class DCMotorConfig(TypedDict):
    enable_pin: int
    input_1_pin: int
    input_2_pin: int


class IRLConfig(TypedDict):
    mc_path: str
    distribution_modules: List[DistributionModuleConfig]
    main_conveyor_dc_motor: DCMotorConfig
    feeder_conveyor_dc_motor: DCMotorConfig
    vibration_hopper_dc_motor: DCMotorConfig


class IRLSystemInterface(TypedDict):
    arduino: ArduinoMega
    distribution_modules: List[DistributionModule]
    main_conveyor_dc_motor: DCMotor
    feeder_conveyor_dc_motor: DCMotor
    vibration_hopper_dc_motor: DCMotor


def buildIRLConfig() -> IRLConfig:
    mc_path = os.getenv("MC_PATH")
    if mc_path is None:
        raise ValueError("MC_PATH environment variable must be set")

    return {
        "mc_path": mc_path,
        "distribution_modules": [
            {
                "distance_from_camera": 45,
                "num_bins": 4,
                "controller_address": 0x41,
            },
            {
                "distance_from_camera": 45 + 17,
                "num_bins": 4,
                "controller_address": 0x42,
            },
        ],
        "main_conveyor_dc_motor": {
            "enable_pin": 3,
            "input_1_pin": 22,
            "input_2_pin": 24,
        },
        "feeder_conveyor_dc_motor": {
            "enable_pin": 5,
            "input_1_pin": 26,
            "input_2_pin": 28,
        },
        "vibration_hopper_dc_motor": {
            "enable_pin": 6,
            "input_1_pin": 30,
            "input_2_pin": 32,
        }
    }


def buildIRLSystemInterface(
    config: IRLConfig, global_config: GlobalConfig
) -> IRLSystemInterface:
    mc = ArduinoMega(config["mc_path"])
    debug_level = global_config["debug_level"]
    if debug_level > 0:
        it = util.Iterator(mc)
        it.start()

        def messageHandler(*args, **kwargs) -> None:
            print(util.two_byte_iter_to_str(args))

        mc.add_cmd_handler(pyfirmata.STRING_DATA, messageHandler)

    dms = []
    for dm in config["distribution_modules"]:
        servo_controller = PCA9685(mc, dm["controller_address"])
        chute_servo = Servo(15, servo_controller)
        bins = [Bin(Servo(i, servo_controller), "") for i in range(dm["num_bins"])]
        dms.append(DistributionModule(chute_servo, dm["distance_from_camera"], bins))

    main_conveyor_motor = DCMotor(
        mc,
        config["main_conveyor_dc_motor"]["enable_pin"],
        config["main_conveyor_dc_motor"]["input_1_pin"],
        config["main_conveyor_dc_motor"]["input_2_pin"]
    )

    feeder_conveyor_motor = DCMotor(
        mc,
        config["feeder_conveyor_dc_motor"]["enable_pin"],
        config["feeder_conveyor_dc_motor"]["input_1_pin"],
        config["feeder_conveyor_dc_motor"]["input_2_pin"]
    )

    vibration_hopper_motor = DCMotor(
        mc,
        config["vibration_hopper_dc_motor"]["enable_pin"],
        config["vibration_hopper_dc_motor"]["input_1_pin"],
        config["vibration_hopper_dc_motor"]["input_2_pin"]
    )

    return {
        "arduino": mc,
        "distribution_modules": dms,
        "main_conveyor_dc_motor": main_conveyor_motor,
        "feeder_conveyor_dc_motor": feeder_conveyor_motor,
        "vibration_hopper_dc_motor": vibration_hopper_motor
    }
