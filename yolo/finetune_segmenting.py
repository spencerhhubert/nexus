import os
from ultralytics import YOLO
from config import build_config
from dataset_utils import split_train_val


def main():
    config = build_config()

    checkpoint_path = os.path.join(config["checkpoints_dir"], config["current_run_id"])
    last_checkpoint = os.path.join(checkpoint_path, "last.pt")
    data_yaml = os.path.join(config["data_path"], "data.yaml")

    if not os.path.exists(data_yaml):
        raise FileNotFoundError(f"Dataset configuration file not found: {data_yaml}")

    # Perform train/val split if requested
    if config["val_split"] is not None:
        print(f"Performing train/validation split with ratio: {config['val_split']}")
        split_train_val(config["data_path"], config["val_split"])
    else:
        print("No validation split requested, using existing train/val directories")

    if os.path.exists(last_checkpoint):
        print(f"Loading checkpoint from: {last_checkpoint}")
        model = YOLO(last_checkpoint, task="segment")
        resume = True
    else:
        print(f"Starting from base model: {config['yolo_base_model_path']}")
        model = YOLO(config["yolo_base_model_path"], task="segment")
        resume = False

    print(f"Training configuration:")
    print(f"  Data: {data_yaml}")
    print(f"  Epochs: {config['epochs']}")
    print(f"  Batch size: {config['batch_size']}")
    print(f"  Device: {config['device']}")
    print(f"  Validation split: {config['val_split'] or 'None'}")
    print(f"  Project dir: {checkpoint_path}")

    results = model.train(
        data=data_yaml,
        epochs=config["epochs"],
        batch=config["batch_size"],
        device=config["device"],
        project=config["checkpoints_dir"],
        name=config["current_run_id"],
        exist_ok=True,
        resume=resume,
        save=True,
        save_period=10,  # Save checkpoint every 10 epochs
        imgsz=640
    )

    print("Training completed!")
    print(f"Results saved to: {checkpoint_path}")

    best_model_path = os.path.join(checkpoint_path, "weights", "best.pt")
    if os.path.exists(best_model_path):
        print(f"Best model saved at: {best_model_path}")


if __name__ == "__main__":
    main()
