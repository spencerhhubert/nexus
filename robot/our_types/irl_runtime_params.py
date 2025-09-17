from typing_extensions import TypedDict
from robot.global_config import GlobalConfig


class IRLSystemRuntimeParams(TypedDict):
    mainConveyorSpeed: int
    feederConveyorSpeed: int
    firstVibrationHopperMotorSpeed: int
    secondVibrationHopperMotorSpeed: int
    firstVibrationHopperMotorPulseMs: int
    secondVibrationHopperMotorPulseMs: int
    feederConveyorPulseMs: int
    firstVibrationHopperMotorPauseMs: int
    secondVibrationHopperMotorPauseMs: int
    feederConveyorPauseMs: int


def buildIRLSystemRuntimeParams(gc: GlobalConfig) -> IRLSystemRuntimeParams:
    return {
        "mainConveyorSpeed": gc["main_conveyor_speed"],
        "feederConveyorSpeed": gc["feeder_conveyor_speed"],
        "firstVibrationHopperMotorSpeed": gc["first_vibration_hopper_motor_speed"],
        "secondVibrationHopperMotorSpeed": gc["second_vibration_hopper_motor_speed"],
        "firstVibrationHopperMotorPulseMs": 1000,
        "secondVibrationHopperMotorPulseMs": 1000,
        "feederConveyorPulseMs": 1000,
        "firstVibrationHopperMotorPauseMs": 200,
        "secondVibrationHopperMotorPauseMs": 200,
        "feederConveyorPauseMs": 200,
    }