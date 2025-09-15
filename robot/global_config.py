import os
import argparse
import time
from typing import TypedDict, TYPE_CHECKING, cast, Optional

if TYPE_CHECKING:
    from robot.logger import Logger


class FeederTimeoutsConfig(TypedDict):
    conveyor_run_for_timeout_ms: int
    first_vibration_hopper_motor_timeout_ms: int
    second_vibration_hopper_motor_timeout_ms: int
    timeout_between_feeder_steps_ms: int


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
    fastsam_weights: str
    yolo_11s_weights: str
    disable_main_conveyor: bool
    disable_first_vibration_hopper_motor: bool
    disable_second_vibration_hopper_motor: bool
    disable_feeder_conveyor: bool
    disable_distribution: bool
    disable_classification: bool
    trajectory_matching_max_time_gap_ms: int
    trajectory_matching_max_position_distance_px: int
    trajectory_matching_min_bbox_size_ratio: float
    trajectory_matching_max_bbox_size_ratio: float
    trajectory_matching_classification_consistency_weight: float
    trajectory_matching_spatial_weight: float
    capture_delay_ms: int
    camera_preview: bool
    enable_profiling: bool
    max_worker_threads: int
    max_queue_size: int
    conveyor_door_open_angle: int
    bin_door_open_angle: int
    conveyor_door_closed_angle: int
    bin_door_closed_angle: int
    conveyor_door_close_delay_ms: int
    bin_door_close_delay_ms: int
    conveyor_door_gradual_close_duration_ms: int
    min_sending_to_bin_time_ms: int
    profiling_dir_path: str
    use_prev_bin_state: Optional[str]
    main_conveyor_speed: int
    feeder_conveyor_speed: int
    first_vibration_hopper_motor_speed: int
    second_vibration_hopper_motor_speed: int
    object_center_threshold_percent: float
    getting_new_object_timeout_ms: int
    classification_timeout_ms: int
    encoder_polling_delay_ms: int
    delay_between_firmata_commands_ms: int
    waiting_for_object_to_center_timeout_ms: int
    waiting_for_object_to_appear_timeout_ms: int
    max_trajectory_age: int
    min_number_observations_for_centering: int
    feeder_timeouts: FeederTimeoutsConfig
    websocket_broadcast_fps: int
    websocket_status_update_interval_s: float


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

    gc = {
        "debug_level": int(os.getenv("DEBUG", "0")),
        "auto_confirm": args.auto_confirm,
        "blob_storage_path": base_blob_path,
        "run_id": run_id,
        "run_blob_dir": run_blob_dir,
        "db_path": "../database.db",
        "tensor_device": "cpu",
        "main_camera_index": 0,
        "fastsam_weights": "../weights/FastSAM-s.pt",
        "yolo_11s_weights": "/Users/spencer/Documents/GitHub/nexus2/weights/yolo11s.pt",
        "disable_main_conveyor": "main_conveyor" in disabled_motors,
        "disable_first_vibration_hopper_motor": "vibration_hopper" in disabled_motors
        or "first_vibration_hopper" in disabled_motors,
        "disable_second_vibration_hopper_motor": "vibration_hopper" in disabled_motors
        or "second_vibration_hopper" in disabled_motors,
        "disable_feeder_conveyor": "feeder_conveyor" in disabled_motors,
        "disable_distribution": "distribution" in disabled_motors,
        "disable_classification": "classification" in disabled_motors,
        "trajectory_matching_max_time_gap_ms": 4000,
        "trajectory_matching_max_position_distance_px": 3000,
        "trajectory_matching_min_bbox_size_ratio": 0.15,
        "trajectory_matching_max_bbox_size_ratio": 6.0,
        "trajectory_matching_classification_consistency_weight": 0.5,
        "trajectory_matching_spatial_weight": 0.5,
        "capture_delay_ms": 300,
        "camera_preview": args.preview,
        "enable_profiling": args.profile,
        "max_worker_threads": 4,
        "max_queue_size": 8,
        "conveyor_door_open_angle": 60,
        "bin_door_open_angle": 180 - 50,
        "conveyor_door_closed_angle": 2,
        "bin_door_closed_angle": 170,
        "conveyor_door_close_delay_ms": 2500,
        "bin_door_close_delay_ms": 1000,
        "conveyor_door_gradual_close_duration_ms": 750,
        "min_sending_to_bin_time_ms": 3000,
        "profiling_dir_path": "../profiles",
        "use_prev_bin_state": args.use_prev_bin_state,
        "main_conveyor_speed": 150,
        "feeder_conveyor_speed": 140,
        # "feeder_conveyor_speed": 0,
        # "first_vibration_hopper_motor_speed": 0,
        "first_vibration_hopper_motor_speed": 149,
        "second_vibration_hopper_motor_speed": 140,
        "object_center_threshold_percent": 0.25,
        "getting_new_object_timeout_ms": 360 * 1000,
        "classification_timeout_ms": 10 * 1000,
        "encoder_polling_delay_ms": 1000,
        "delay_between_firmata_commands_ms": 10,
        "waiting_for_object_to_center_timeout_ms": 7500,
        "waiting_for_object_to_appear_timeout_ms": 10000,
        "max_trajectory_age": 10000,
        "min_number_observations_for_centering": 2,
        "feeder_timeouts": {
            "conveyor_run_for_timeout_ms": 400,
            "first_vibration_hopper_motor_timeout_ms": 1200,
            "second_vibration_hopper_motor_timeout_ms": 200,
            "timeout_between_feeder_steps_ms": 1000,
        },
        "websocket_broadcast_fps": 30,
        "websocket_status_update_interval_s": 0.2,
    }

    from robot.logger import Logger

    gc["logger"] = Logger(gc["debug_level"])

    return cast(GlobalConfig, gc)
