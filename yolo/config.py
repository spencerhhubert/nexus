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
    img_size: int


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
        default="cuda",
        help="Device for training (cpu, cuda, mps, etc.)",
    )
    parser.add_argument(
        "--val_split",
        type=float,
        help="Validation split ratio (e.g., 0.2 for 20%% validation). If not provided, no splitting is performed.",
    )
    parser.add_argument(
        "--model_size",
        type=str,
        choices=["nano", "small", "medium"],
        default="small",
        help="Model size: nano, small, or medium",
    )
    parser.add_argument(
        "--img_size",
        type=int,
        default=416,
        help="Image size for training",
    )
    parser.add_argument(
        "--data_path",
        type=str,
        default="yolo/data",
        help="Data path relative to repo directory",
    )

    args = parser.parse_args()

    repo_dir = "/Users/spencer/Documents/GitHub/nexus2"

    checkpoints_dir = f"{repo_dir}/yolo/checkpoints"

    model_size_map = {
        "nano": ("yolo11n-seg.pt", "yolo11n-seg"),
        "small": ("yolo11s-seg.pt", "yolo11s-seg"),
        "medium": ("yolo11m-seg.pt", "yolo11m-seg")
    }

    model_file, model_name = model_size_map[args.model_size]

    if args.checkpoint_run_id:
        current_run_id = args.checkpoint_run_id
        print(f"Resuming training from checkpoint run: {current_run_id}")
    else:
        timestamp = int(time.time())
        data_path_clean = args.data_path.replace("/", "_")
        current_run_id = f"run_{timestamp}_{args.img_size}_{args.model_size}_{args.epochs}epochs_{args.batch}batch_{data_path_clean}"
        print(f"Starting new training run: {current_run_id}")

    os.makedirs(os.path.join(checkpoints_dir, current_run_id), exist_ok=True)

    return {
        "yolo_base_model_path": f"{repo_dir}/weights/{model_file}",
        "yolo_model": model_name,
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
        "data_path": f"{repo_dir}/{args.data_path}",
        "epochs": args.epochs,
        "batch_size": args.batch,
        "device": args.device,
        "val_split": args.val_split,
        "img_size": args.img_size,
    }


# Class mapping for visualization
CLASS_NAMES = {
    0: "object",
    1: "first_feeder",
    2: "second_feeder",
    3: "main_conveyor",
    4: "feeder_conveyor"
}
