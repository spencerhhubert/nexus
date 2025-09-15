import os
import argparse
import random
import cv2
import numpy as np
from config import DATA_PATH, CLASS_NAMES


def visualize_dataset(data_path: str = DATA_PATH, num_samples: int = 5, split: str = "train"):
    images_dir = os.path.join(data_path, "images", split)
    labels_dir = os.path.join(data_path, "labels", split)

    if not os.path.exists(images_dir):
        print(f"Images directory not found: {images_dir}")
        return

    if not os.path.exists(labels_dir):
        print(f"Labels directory not found: {labels_dir}")
        return

    image_files = [f for f in os.listdir(images_dir)
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if not image_files:
        print(f"No image files found in {images_dir}")
        return

    print(f"Found {len(image_files)} images in {split} set")

    sample_files = random.sample(image_files, min(num_samples, len(image_files)))

    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
        (128, 0, 128),  # Purple
        (255, 165, 0),  # Orange
        (255, 192, 203), # Pink
        (128, 128, 128), # Gray
    ]

    for i, image_file in enumerate(sample_files):
        print(f"\nVisualizing sample {i+1}/{len(sample_files)}: {image_file}")

        image_path = os.path.join(images_dir, image_file)
        label_file = os.path.splitext(image_file)[0] + '.txt'
        label_path = os.path.join(labels_dir, label_file)

        if not os.path.exists(label_path):
            print(f"  Warning: Label file not found: {label_path}")
            continue

        img = cv2.imread(image_path)
        if img is None:
            print(f"  Error: Could not load image: {image_path}")
            continue

        height, width = img.shape[:2]
        overlay = img.copy()

        with open(label_path, 'r') as f:
            lines = f.readlines()

        print(f"  Label file: {label_file}")
        print(f"  Number of objects: {len(lines)}")

        for j, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) < 7:
                print(f"    Object {j+1}: Invalid format - {len(parts)} parts")
                continue

            class_id = int(parts[0])
            coords = [float(x) for x in parts[1:]]
            num_points = len(coords) // 2
            class_name = CLASS_NAMES.get(class_id, f"unknown_{class_id}")
            print(f"    Object {j+1}: class={class_id} ({class_name}), points={num_points}")

            points = []
            for k in range(0, len(coords), 2):
                x = int(coords[k] * width)
                y = int(coords[k+1] * height)
                points.append([x, y])

            if len(points) >= 3:
                points_array = np.array(points, dtype=np.int32)
                color = colors[class_id % len(colors)]

                cv2.fillPoly(overlay, [points_array], color)
                cv2.polylines(img, [points_array], True, color, 2)

                # Add class label
                if len(points) > 0:
                    label_pos = tuple(points[0])
                    cv2.putText(img, f"{class_name}", label_pos,
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        alpha = 0.4
        result = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

        visualized_dir = os.path.join(data_path, "visualized")
        os.makedirs(visualized_dir, exist_ok=True)

        output_path = os.path.join(visualized_dir, f"{os.path.splitext(image_file)[0]}_visualized.jpg")
        cv2.imwrite(output_path, result)
        print(f"  ✓ Visualization saved: {output_path}")


def inspect_label_format(data_path: str = DATA_PATH, split: str = "train"):
    labels_dir = os.path.join(data_path, "labels", split)

    if not os.path.exists(labels_dir):
        print(f"Labels directory not found: {labels_dir}")
        return

    label_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]

    if not label_files:
        print(f"No label files found in {labels_dir}")
        return

    print(f"Inspecting label format in {split} set...")
    print(f"Found {len(label_files)} label files")

    # Check first few files for format issues
    for i, label_file in enumerate(label_files[:3]):
        label_path = os.path.join(labels_dir, label_file)
        print(f"\n--- {label_file} ---")

        with open(label_path, 'r') as f:
            lines = f.readlines()

        for j, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            print(f"  Line {j+1}: {len(parts)} parts")
            print(f"    Raw: {line}")

            if len(parts) >= 1:
                try:
                    class_id = int(parts[0])
                    coords = [float(x) for x in parts[1:]]
                    num_points = len(coords) // 2

                    print(f"    Class: {class_id} ({CLASS_NAMES.get(class_id, 'unknown')})")
                    print(f"    Coordinates: {num_points} points")

                    # Check coordinate ranges
                    x_coords = coords[::2]
                    y_coords = coords[1::2]

                    if x_coords and y_coords:
                        x_range = f"{min(x_coords):.3f} to {max(x_coords):.3f}"
                        y_range = f"{min(y_coords):.3f} to {max(y_coords):.3f}"
                        print(f"    X range: {x_range}")
                        print(f"    Y range: {y_range}")

                        # Check if coordinates are normalized (0-1)
                        if any(x < 0 or x > 1 for x in x_coords + y_coords):
                            print(f"    ⚠️  WARNING: Coordinates not normalized!")

                except (ValueError, IndexError) as e:
                    print(f"    ✗ Parse error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Visualize YOLO segmentation dataset")
    parser.add_argument(
        "--data_path",
        type=str,
        default=DATA_PATH,
        help="Path to dataset directory"
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=["train", "val"],
        default="train",
        help="Dataset split to visualize"
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=5,
        help="Number of samples to visualize"
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Only inspect label format without visualization"
    )

    args = parser.parse_args()

    print(f"Dataset path: {args.data_path}")
    print(f"Split: {args.split}")
    print(f"Class mapping: {CLASS_NAMES}")

    if args.inspect:
        inspect_label_format(args.data_path, args.split)
    else:
        # First inspect, then visualize
        inspect_label_format(args.data_path, args.split)
        print("\n" + "="*50)
        visualize_dataset(args.data_path, args.num_samples, args.split)


if __name__ == "__main__":
    main()