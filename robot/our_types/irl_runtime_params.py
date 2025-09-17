from typing_extensions import TypedDict
from robot.global_config import GlobalConfig


class IRLSystemRuntimeParams(TypedDict):
    main_conveyor_speed: int
    feeder_conveyor_speed: int
    first_vibration_hopper_motor_speed: int
    second_vibration_hopper_motor_speed: int
    first_vibration_hopper_motor_pulse_ms: int
    second_vibration_hopper_motor_pulse_ms: int
    feeder_conveyor_pulse_ms: int
    first_vibration_hopper_motor_pause_ms: int
    second_vibration_hopper_motor_pause_ms: int
    feeder_conveyor_pause_ms: int
    first_vibration_hopper_motor_use_hard_stop: bool
    second_vibration_hopper_motor_use_hard_stop: bool


def buildIRLSystemRuntimeParams(gc: GlobalConfig) -> IRLSystemRuntimeParams:
    return {
        "main_conveyor_speed": gc["main_conveyor_speed"],
        "feeder_conveyor_speed": gc["feeder_conveyor_speed"],
        "first_vibration_hopper_motor_speed": gc["first_vibration_hopper_motor_speed"],
        "second_vibration_hopper_motor_speed": gc[
            "second_vibration_hopper_motor_speed"
        ],
        "first_vibration_hopper_motor_pulse_ms": gc[
            "first_vibration_hopper_motor_pulse_ms"
        ],
        "second_vibration_hopper_motor_pulse_ms": gc[
            "second_vibration_hopper_motor_pulse_ms"
        ],
        "feeder_conveyor_pulse_ms": gc["feeder_conveyor_pulse_ms"],
        "first_vibration_hopper_motor_pause_ms": gc[
            "first_vibration_hopper_motor_pause_ms"
        ],
        "second_vibration_hopper_motor_pause_ms": gc[
            "second_vibration_hopper_motor_pause_ms"
        ],
        "feeder_conveyor_pause_ms": gc["feeder_conveyor_pause_ms"],
        "first_vibration_hopper_motor_use_hard_stop": gc[
            "first_vibration_hopper_motor_use_hard_stop"
        ],
        "second_vibration_hopper_motor_use_hard_stop": gc[
            "second_vibration_hopper_motor_use_hard_stop"
        ],
    }
