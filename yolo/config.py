import argparse
import os
import time
from typing import TypedDict, Optional


class Config(TypedDict):
    yolo_base_model_path: str
    yolo_model: str
    checkpoints_dir: str
    current_run_id: str
    data_path: str
    epochs: int
    batch_size: int
    device: str
    val_split: Optional[float]


def build_config() -> Config:
    parser = argparse.ArgumentParser(description="YOLO segmentation fine-tuning")
    parser.add_argument(
        "--checkpoint_run_id",
        type=str,
        help="Resume training from existing checkpoint run ID",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=20,
        help="Batch size for training",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for training (cpu, cuda, mps, etc.)",
    )
    parser.add_argument(
        "--val_split",
        type=float,
        help="Validation split ratio (e.g., 0.2 for 20%% validation). If not provided, no splitting is performed.",
    )

    args = parser.parse_args()

    repo_dir = "/Users/spencer/Documents/GitHub/nexus2"

    checkpoints_dir = f"{repo_dir}/yolo/checkpoints"

    if args.checkpoint_run_id:
        current_run_id = args.checkpoint_run_id
        print(f"Resuming training from checkpoint run: {current_run_id}")
    else:
        timestamp = int(time.time())
        current_run_id = f"run_{timestamp}"
        print(f"Starting new training run: {current_run_id}")

    os.makedirs(os.path.join(checkpoints_dir, current_run_id), exist_ok=True)

    return {
        "yolo_base_model_path": f"{repo_dir}/weights/yolo11s-seg.pt",
        "yolo_model": "yolo11s-seg",
        "checkpoints_dir": checkpoints_dir,
        "current_run_id": current_run_id,
        # Data should be structured as:
        # {repo_dir}/yolo/data/
        # ├── images/
        # │   ├── train/
        # │   │   ├── image001.jpg
        # │   │   ├── image002.jpg
        # │   │   └── ...
        # │   └── val/
        # │       ├── image101.jpg
        # │       ├── image102.jpg
        # │       └── ...
        # ├── labels/
        # │   ├── train/
        # │   │   ├── image001.txt  # Same filename as corresponding image
        # │   │   ├── image002.txt
        # │   │   └── ...
        # │   └── val/
        # │       ├── image101.txt
        # │       ├── image102.txt
        # │       └── ...
        # └── data.yaml (dataset configuration file)
        #
        # Each .txt label file contains one line per object:
        # class_id x1 y1 x2 y2 x3 y3 ... xn yn
        # Where (x1,y1), (x2,y2), ..., (xn,yn) are normalized polygon coordinates
        # for segmentation masks. For bounding boxes only: class_id x_center y_center width height
        "data_path": f"{repo_dir}/yolo/data",
        "epochs": args.epochs,
        "batch_size": args.batch,
        "device": args.device,
        "val_split": args.val_split,
    }


# Class mapping for visualization
CLASS_NAMES = {
    0: "object",
    1: "first_feeder",
    2: "second_feeder",
    3: "main_conveyor",
    4: "feeder_conveyor"
}
