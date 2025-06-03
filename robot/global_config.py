import os
import argparse
import time
from typing import TypedDict, TYPE_CHECKING, cast

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
    camera_trigger_position: float
    capture_delay_ms: int
    enable_profiling: bool


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
    args = parser.parse_args()

    disabled_motors = args.disable or []

    run_id = f"run_{int(time.time())}"
    base_blob_path = "./.blob"
    run_blob_dir = os.path.join(base_blob_path, run_id)

    gc = {
        "debug_level": int(os.getenv("DEBUG", "0")),
        "auto_confirm": args.auto_confirm,
        "blob_storage_path": base_blob_path,
        "run_id": run_id,
        "run_blob_dir": run_blob_dir,
        "db_path": "./database.db",
        "tensor_device": "mps",
        "main_camera_index": 0,
        "fastsam_weights": "./weights/FastSAM-s.pt",
        "disable_main_conveyor": "main_conveyor" in disabled_motors,
        "disable_vibration_hopper": "vibration_hopper" in disabled_motors,
        "disable_feeder_conveyor": "feeder_conveyor" in disabled_motors,
        "trajectory_matching_max_time_gap_ms": 500,
        "trajectory_matching_max_position_distance_px": 200,
        "trajectory_matching_min_bbox_size_ratio": 0.5,
        "trajectory_matching_max_bbox_size_ratio": 2.0,
        "trajectory_matching_classification_consistency_weight": 0.7,
        "trajectory_matching_spatial_weight": 0.3,
        "camera_trigger_position": 0.15,
        "capture_delay_ms": 1,
        "enable_profiling": args.profile,
    }

    from robot.logger import Logger

    gc["logger"] = Logger(cast(GlobalConfig, gc))

    return cast(GlobalConfig, gc)
