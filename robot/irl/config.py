from pyfirmata import Arduino, util, pyfirmata
from robot.irl.motors import PCA9685, Servo
from robot.irl.distribution import Bin, DistributionModule
from typing import Dict, List, Tuple, TypedDict, NewType
import os
from robot.global_config import GlobalConfig


class DistributionModuleConfig(TypedDict):
    distance_from_camera: int
    num_bins: int
    controller_address: int


class IRLConfig(TypedDict):
    mc_path: str
    distribution_modules: List[DistributionModuleConfig]


IRLSystemInterface = Tuple[Arduino, List[DistributionModule]]


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
    }


def buildIRLSystemInterface(
    config: IRLConfig, global_config: GlobalConfig
) -> IRLSystemInterface:
    mc = Arduino(config["mc_path"])
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

    return mc, dms
