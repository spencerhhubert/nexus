import argparse
import os
import time
from typing import TypedDict
from ultralytics import YOLO


class Config(TypedDict):
    yolo_base_model_path: str
    yolo_model: str
    checkpoints_dir: str
    current_run_id: str
    data_path: str
    epochs: int
    batch_size: int
    device: str


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
        default=16,
        help="Batch size for training",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for training (cpu, cuda, mps, etc.)",
    )

    args = parser.parse_args()

    checkpoints_dir = "/Users/spencer/Documents/GitHub/nexus2/yolo/checkpoints"

    if args.checkpoint_run_id:
        current_run_id = args.checkpoint_run_id
        print(f"Resuming training from checkpoint run: {current_run_id}")
    else:
        current_run_id = f"run_{int(time.time())}"
        print(f"Starting new training run: {current_run_id}")

    os.makedirs(os.path.join(checkpoints_dir, current_run_id), exist_ok=True)

    return {
        "yolo_base_model_path": "/Users/spencer/Documents/GitHub/nexus2/weights/yolo11n-seg.pt",
        "yolo_model": "yolo11n-seg",
        "checkpoints_dir": checkpoints_dir,
        "current_run_id": current_run_id,
        # Data should be structured as:
        # /Users/spencer/Documents/GitHub/nexus2/yolo/data/
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
        "data_path": "/Users/spencer/Documents/GitHub/nexus2/yolo/data",
        "epochs": args.epochs,
        "batch_size": args.batch,
        "device": args.device,
    }


def main():
    config = build_config()

    checkpoint_path = os.path.join(config["checkpoints_dir"], config["current_run_id"])
    last_checkpoint = os.path.join(checkpoint_path, "last.pt")
    data_yaml = os.path.join(config["data_path"], "data.yaml")

    if not os.path.exists(data_yaml):
        raise FileNotFoundError(f"Dataset configuration file not found: {data_yaml}")

    if os.path.exists(last_checkpoint):
        print(f"Loading checkpoint from: {last_checkpoint}")
        model = YOLO(last_checkpoint)
        resume = True
    else:
        print(f"Starting from base model: {config['yolo_base_model_path']}")
        model = YOLO(config["yolo_base_model_path"])
        resume = False

    print(f"Training configuration:")
    print(f"  Data: {data_yaml}")
    print(f"  Epochs: {config['epochs']}")
    print(f"  Batch size: {config['batch_size']}")
    print(f"  Device: {config['device']}")
    print(f"  Project dir: {checkpoint_path}")

    results = model.train(
        data=data_yaml,
        epochs=config["epochs"],
        batch=config["batch_size"],
        device=config["device"],
        project=config["checkpoints_dir"],
        name=config["current_run_id"],
        resume=resume,
        save=True,
        save_period=10,  # Save checkpoint every 10 epochs
    )

    print("Training completed!")
    print(f"Results saved to: {checkpoint_path}")

    best_model_path = os.path.join(checkpoint_path, "weights", "best.pt")
    if os.path.exists(best_model_path):
        print(f"Best model saved at: {best_model_path}")


if __name__ == "__main__":
    main()