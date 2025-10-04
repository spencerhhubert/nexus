import os
import argparse
import time
from typing import TypedDict, TYPE_CHECKING, cast, Optional

if TYPE_CHECKING:
    from robot.logger import Logger


class GlobalConfig(TypedDict):
    debug_level: int
    auto_confirm: bool
    logger: "Logger"
    blob_storage_path: str
    run_id: str
    run_blob_dir: str
    db_path: str
    tensor_device: str
    main_camera_index: int
    yolo_model: str
    feeder_camera_yolo_weights_path: str
    main_camera_yolo_weights_path: str
    disable_main_conveyor: bool
    disable_first_vibration_hopper_motor: bool
    disable_second_vibration_hopper_motor: bool
    disable_feeder_conveyor: bool
    disable_distribution: bool
    disable_classification: bool
    capture_delay_ms: int
    camera_preview: bool
    enable_profiling: bool
    recording_enabled: bool
    max_queue_size: int
    conveyor_door_open_angle: int
    bin_door_open_angle: int
    conveyor_door_closed_angle: int
    bin_door_closed_angle: int
    conveyor_door_close_delay_ms: int
    bin_door_close_delay_ms: int
    conveyor_door_gradual_close_duration_ms: int
    min_sending_to_bin_time_ms: int
    use_prev_bin_state: Optional[str]
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
    encoder_polling_delay_ms: int
    delay_between_firmata_commands_ms: int
    classifying_timeout_ms: int
    waiting_for_object_to_center_timeout_ms: int
    waiting_for_object_to_appear_timeout_ms: int
    fs_object_at_end_of_second_feeder_timeout_ms: int
    state_machine_steps_per_second: int


def buildGlobalConfig() -> GlobalConfig:
    parser = argparse.ArgumentParser(description="Robot control system")
    parser.add_argument(
        "--auto-confirm",
        "-y",
        action="store_true",
        help="Automatically confirm all prompts",
    )
    parser.add_argument(
        "--disable",
        nargs="*",
        choices=[
            "main_conveyor",
            "vibration_hopper",
            "first_vibration_hopper",
            "second_vibration_hopper",
            "feeder_conveyor",
            "classification",
            "distribution",
        ],
        help="Disable specified systems",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable performance profiling",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Enable camera preview window",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record raw and annotated camera feeds to video files",
    )
    parser.add_argument(
        "--use_prev_bin_state",
        nargs="?",
        const="latest",
        help="Use previous bin state. Optionally specify bin state ID, defaults to most recent",
    )
    args = parser.parse_args()

    disabled_motors = args.disable or []

    run_id = f"run_{int(time.time())}"
    base_blob_path = "../.blob"
    run_blob_dir = os.path.join(base_blob_path, run_id)

    from robot.logger import Logger

    debug_level = int(os.getenv("DEBUG", "0"))
    gc: GlobalConfig = {
        "debug_level": debug_level,
        "auto_confirm": args.auto_confirm,
        "blob_storage_path": base_blob_path,
        "run_id": run_id,
        "run_blob_dir": run_blob_dir,
        "db_path": "../database.db",
        "tensor_device": "cpu",
        "main_camera_index": 0,
        "yolo_model": "yolo11n-seg",
        # "yolo_weights_path":" /Users/spencer/Downloads/checkpoints (small)/run_1757963343/weights/best.pt",
        # "yolo_weights_path": "/Users/spencer/Downloads/checkpoints (nano)/run_1757970830/weights/best.pt",
        # "yolo_weights_path": "/Users/spencer/Downloads/checkpoints (nano 414)/run_1757975149/weights/best.pt",
        # "yolo_weights_path": "/Users/spencer/Documents/GitHub/nexus2/weights/yolo11s-seg.pt",
        # "yolo_weights_path": "/Users/spencer/Downloads/run_1758315224/weights/best.pt", #nano more data
        # "yolo_weights_path": "/Users/spencer/Downloads/run_1758315429/weights/best.pt",  # small more data
        # "yolo_weights_path": "/Users/spencer/Downloads/run_1758582313/weights/best.pt",  # small, moved camera
        # "yolo_weights_path": "/Users/spencer/Downloads/run_1758827336/weights/best.pt",  # medium, new data03, 640
        # "yolo_weights_path": "/Users/spencer/Downloads/run_1758831161/weights/best.pt",  # nano, new data03, 640, 150 epochs
        # "yolo_weights_path": "/Users/spencer/Downloads/run_1758827930/weights/best.pt",  # small, new data03, 416, 100 epochs
        # "feeder_camera_yolo_weights_path": "/Users/spencer/Downloads/run_1759011892_416_small_150epochs_8batch_yolo_data_feeder_camera/weights/last.pt",
        "feeder_camera_yolo_weights_path": "/Users/spencer/Downloads/run_1759021739_640_nano_150epochs_8batch_yolo_data_feeder_camera/weights/last.pt",
        # "main_camera_yolo_weights_path": "/Users/spencer/Downloads/run_1759012309_416_small_150epochs_8batch_yolo_data_main_camera/weights/epoch100.pt",
        "main_camera_yolo_weights_path": "/Users/spencer/Downloads/run_1759016097_416_nano_150epochs_8batch_yolo_data_main_camera/weights/epoch100.pt",
        "disable_main_conveyor": "main_conveyor" in disabled_motors,
        "disable_first_vibration_hopper_motor": "vibration_hopper" in disabled_motors
        or "first_vibration_hopper" in disabled_motors,
        "disable_second_vibration_hopper_motor": "vibration_hopper" in disabled_motors
        or "second_vibration_hopper" in disabled_motors,
        "disable_feeder_conveyor": "feeder_conveyor" in disabled_motors,
        "disable_distribution": "distribution" in disabled_motors,
        "disable_classification": "classification" in disabled_motors,
        "capture_delay_ms": 300,
        "camera_preview": args.preview,
        "enable_profiling": args.profile,
        "recording_enabled": args.record,
        "max_queue_size": 8,
        "conveyor_door_open_angle": 60,
        "bin_door_open_angle": 180 - 50,
        "conveyor_door_closed_angle": 2,
        "bin_door_closed_angle": 170,
        "conveyor_door_close_delay_ms": 2500,
        "bin_door_close_delay_ms": 1000,
        "conveyor_door_gradual_close_duration_ms": 750,
        "min_sending_to_bin_time_ms": 3000,
        "use_prev_bin_state": args.use_prev_bin_state,
        "main_conveyor_speed": 150,
        "feeder_conveyor_speed": 80,
        "first_vibration_hopper_motor_speed": 172,  # first hopper that pieces enter
        # "first_vibration_hopper_motor_speed": 80,  # first hopper that pieces enter
        "second_vibration_hopper_motor_speed": 165,
        # "second_vibration_hopper_motor_speed": 80,
        "first_vibration_hopper_motor_pulse_ms": 200,
        "second_vibration_hopper_motor_pulse_ms": 400,
        "first_vibration_hopper_motor_pause_ms": 500,
        "second_vibration_hopper_motor_pause_ms": 500,
        "feeder_conveyor_pulse_ms": 1500,
        "feeder_conveyor_pause_ms": 200,
        "encoder_polling_delay_ms": 1000,
        "delay_between_firmata_commands_ms": 8,
        "classifying_timeout_ms": 5000,
        "waiting_for_object_to_center_timeout_ms": 5000,
        "waiting_for_object_to_appear_timeout_ms": 5000,
        "fs_object_at_end_of_second_feeder_timeout_ms": 4000,
        "state_machine_steps_per_second": 15,
        "logger": Logger(debug_level),
    }

    return cast(GlobalConfig, gc)
