import os
import random
import shutil


def split_train_val(data_path: str, val_split: float):
    train_images_dir = os.path.join(data_path, "images", "train")
    val_images_dir = os.path.join(data_path, "images", "val")
    train_labels_dir = os.path.join(data_path, "labels", "train")
    val_labels_dir = os.path.join(data_path, "labels", "val")

    os.makedirs(val_images_dir, exist_ok=True)
    os.makedirs(val_labels_dir, exist_ok=True)

    if not os.path.exists(train_images_dir):
        print(f"Training images directory not found: {train_images_dir}")
        return

    image_files = [f for f in os.listdir(train_images_dir)
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if not image_files:
        print("No image files found in training directory")
        return

    num_val = int(len(image_files) * val_split)
    if num_val == 0:
        print(f"Validation split {val_split} too small, no files to move")
        return

    random.seed(42)
    val_files = random.sample(image_files, num_val)

    print(f"Splitting {len(image_files)} files: {len(image_files) - num_val} train, {num_val} validation")

    moved_images = 0
    moved_labels = 0

    for filename in val_files:
        src_image = os.path.join(train_images_dir, filename)
        dst_image = os.path.join(val_images_dir, filename)

        if os.path.exists(src_image):
            shutil.move(src_image, dst_image)
            moved_images += 1

        label_filename = os.path.splitext(filename)[0] + '.txt'
        src_label = os.path.join(train_labels_dir, label_filename)
        dst_label = os.path.join(val_labels_dir, label_filename)

        if os.path.exists(src_label):
            shutil.move(src_label, dst_label)
            moved_labels += 1

    print(f"Moved {moved_images} images and {moved_labels} labels to validation set")


def copy_labeler_data():
    source_dir = "/Users/spencer/Documents/GitHub/nexus2/yolo/labeler/data"
    dest_images_train = "/Users/spencer/Documents/GitHub/nexus2/yolo/data/images/train"
    dest_labels_train = "/Users/spencer/Documents/GitHub/nexus2/yolo/data/labels/train"

    os.makedirs(dest_images_train, exist_ok=True)
    os.makedirs(dest_labels_train, exist_ok=True)

    if not os.path.exists(source_dir):
        print(f"Source directory not found: {source_dir}")
        print("Make sure you've saved some frames from the labeler first!")
        return

    files = os.listdir(source_dir)
    image_files = [f for f in files if f.endswith('.jpg')]
    label_files = [f for f in files if f.endswith('.txt')]

    print(f"Found {len(image_files)} images and {len(label_files)} labels in labeler output")

    copied_images = 0
    copied_labels = 0

    for img_file in image_files:
        src = os.path.join(source_dir, img_file)
        dst = os.path.join(dest_images_train, img_file)

        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied_images += 1
        else:
            print(f"Skipping existing image: {img_file}")

    for lbl_file in label_files:
        src = os.path.join(source_dir, lbl_file)
        dst = os.path.join(dest_labels_train, lbl_file)

        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied_labels += 1
        else:
            print(f"Skipping existing label: {lbl_file}")

    print(f"Copied {copied_images} new images and {copied_labels} new labels to training set")
    print(f"Training images: {dest_images_train}")
    print(f"Training labels: {dest_labels_train}")