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
    fastsam_weights: str
    disable_main_conveyor: bool
    disable_vibration_hopper: bool
    disable_feeder_conveyor: bool
    trajectory_matching_max_time_gap_ms: int
    trajectory_matching_max_position_distance_px: int
    trajectory_matching_min_bbox_size_ratio: float
    trajectory_matching_max_bbox_size_ratio: float
    trajectory_matching_classification_consistency_weight: float
    trajectory_matching_spatial_weight: float
    leading_edge_trigger_position: float
    camera_center_reference_position: float
    capture_delay_ms: int
    camera_preview: bool
    enable_profiling: bool
    max_worker_threads: int
    max_queue_size: int
    conveyor_door_open_angle: int
    bin_door_open_angle: int
    conveyor_door_closed_angle: int
    bin_door_closed_angle: int
    door_open_duration_ms: int
    door_delay_offset_ms: int
    delay_for_chute_fall_ms: int
    profiling_dir_path: str
    use_prev_bin_state: Optional[str]
    speed_estimation_border_threshold_percent: float
    overlapping_conveyor_door_windows_threshold_ms: int


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
        choices=["main_conveyor", "vibration_hopper", "feeder_conveyor"],
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
        "disable_main_conveyor": "main_conveyor" in disabled_motors,
        "disable_vibration_hopper": "vibration_hopper" in disabled_motors,
        "disable_feeder_conveyor": "feeder_conveyor" in disabled_motors,
        "trajectory_matching_max_time_gap_ms": 750,
        "trajectory_matching_max_position_distance_px": 1500,
        "trajectory_matching_min_bbox_size_ratio": 0.25,
        "trajectory_matching_max_bbox_size_ratio": 4.0,
        "trajectory_matching_classification_consistency_weight": 0.5,
        "trajectory_matching_spatial_weight": 0.3,
        "leading_edge_trigger_position": 0.45,
        "camera_center_reference_position": 0.5,
        "capture_delay_ms": 250,
        "camera_preview": args.preview,
        "enable_profiling": args.profile,
        "max_worker_threads": 4,
        "max_queue_size": 8,
        "conveyor_door_open_angle": 60,
        "bin_door_open_angle": 180 - 55,
        "conveyor_door_closed_angle": 2,
        "bin_door_closed_angle": 170,
        "door_open_duration_ms": 2500,
        "door_delay_offset_ms": -750,
        "delay_for_chute_fall_ms": 1000,
        "profiling_dir_path": "../profiles",
        "use_prev_bin_state": args.use_prev_bin_state,
        "speed_estimation_border_threshold_percent": 0.05,
        "overlapping_conveyor_door_windows_threshold_ms": 5000,
    }

    from robot.logger import Logger

    gc["logger"] = Logger(gc["debug_level"])

    return cast(GlobalConfig, gc)
