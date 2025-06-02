import os
import argparse
from typing import TypedDict, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from robot.logger import Logger


class GlobalConfig(TypedDict):
    debug_level: int
    auto_confirm: bool
    logger: "Logger"
    blob_storage_path: str
    db_path: str
    tensor_device: str
    main_camera_index: int
    fastsam_weights: str
    trajectory_matching_max_time_gap_ms: int
    trajectory_matching_max_position_distance_px: int
    trajectory_matching_min_bbox_size_ratio: float
    trajectory_matching_max_bbox_size_ratio: float
    trajectory_matching_classification_consistency_weight: float
    trajectory_matching_spatial_weight: float
    camera_trigger_position: float
    capture_delay_ms: int


def buildGlobalConfig() -> GlobalConfig:
    parser = argparse.ArgumentParser(description="Robot control system")
    parser.add_argument("--auto-confirm", "-y", action="store_true", 
                       help="Automatically confirm all prompts")
    args = parser.parse_args()
    
    gc = {
        "debug_level": int(os.getenv("DEBUG", "0")),
        "auto_confirm": args.auto_confirm,
        "blob_storage_path": "./.blob",
        "db_path": "./database.db",
        "tensor_device": "mps",
        "main_camera_index": 0,
        "fastsam_weights": "./weights/FastSAM-s.pt",
        "trajectory_matching_max_time_gap_ms": 500,
        "trajectory_matching_max_position_distance_px": 200,
        "trajectory_matching_min_bbox_size_ratio": 0.5,
        "trajectory_matching_max_bbox_size_ratio": 2.0,
        "trajectory_matching_classification_consistency_weight": 0.7,
        "trajectory_matching_spatial_weight": 0.3,
        "camera_trigger_position": 0.25,
        "capture_delay_ms": 250
    }
    
    from robot.logger import Logger
    gc["logger"] = Logger(cast(GlobalConfig, gc))
    
    return cast(GlobalConfig, gc)
