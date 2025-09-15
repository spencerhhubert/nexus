#!/usr/bin/env python3

import os
import shutil
from config import DATA_PATH


def validate_and_prune_labels():
    labels_base_dir = os.path.join(DATA_PATH, "labels")
    backup_dir = os.path.join(DATA_PATH, "unpruned_labels")

    if not os.path.exists(labels_base_dir):
        print(f"Labels directory not found: {labels_base_dir}")
        return

    os.makedirs(backup_dir, exist_ok=True)

    splits = ["train", "val"]
    total_processed = 0
    total_backed_up = 0

    for split in splits:
        split_dir = os.path.join(labels_base_dir, split)

        if not os.path.exists(split_dir):
            print(f"Skipping {split} - directory not found: {split_dir}")
            continue

        backup_split_dir = os.path.join(backup_dir, split)
        os.makedirs(backup_split_dir, exist_ok=True)

        label_files = [f for f in os.listdir(split_dir) if f.endswith('.txt')]

        if not label_files:
            print(f"No label files found in {split_dir}")
            continue

        print(f"Processing {len(label_files)} {split} label files...")

        processed_count = 0
        backed_up_count = 0

        for label_file in label_files:
            label_path = os.path.join(split_dir, label_file)
            backup_path = os.path.join(backup_split_dir, label_file)

            # Backup original if not already backed up
            if not os.path.exists(backup_path):
                shutil.copy2(label_path, backup_path)
                backed_up_count += 1

            # Read and process the label file
            with open(label_path, 'r') as f:
                lines = f.readlines()

            modified_lines = []
            file_modified = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 3:
                    modified_lines.append(line)
                    continue

                # Process class ID (keep as integer)
                class_id = parts[0]

                # Process coordinates
                coords = []
                for coord_str in parts[1:]:
                    try:
                        coord = float(coord_str)

                        # Set negative values to zero
                        if coord < 0:
                            coord = 0.0
                            file_modified = True

                        # Round to 6 decimal places
                        rounded_coord = round(coord, 6)
                        if rounded_coord != coord:
                            file_modified = True

                        coords.append(f"{rounded_coord:.6f}")

                    except ValueError:
                        coords.append(coord_str)

                new_line = f"{class_id} {' '.join(coords)}"
                modified_lines.append(new_line)

            # Write back if modified
            if file_modified:
                with open(label_path, 'w') as f:
                    f.write('\n'.join(modified_lines) + '\n')
                processed_count += 1

        print(f"  Backed up {backed_up_count} {split} files")
        print(f"  Modified {processed_count} {split} files")
        total_backed_up += backed_up_count
        total_processed += processed_count

    print(f"\nTotal backed up: {total_backed_up} files to {backup_dir}")
    print(f"Total modified: {total_processed} label files")
    print("Validation and pruning complete!")


if __name__ == "__main__":
    validate_and_prune_labels()