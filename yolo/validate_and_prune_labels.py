#!/usr/bin/env python3

import os
import shutil
from config import DATA_PATH
from typing import List, Tuple

def shoelace_area(points: List[Tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0

def segments_intersect(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def is_self_intersecting(points: List[Tuple[float, float]]) -> bool:
    n = len(points)
    for i in range(n):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        for j in range(i + 2, n):
            p3 = points[j]
            p4 = points[(j + 1) % n]
            if segments_intersect(p1, p2, p3, p4):
                return True
    return False


def reorder_points_around_centroid(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if len(points) < 3:
        return points

    # Compute centroid
    cx = sum(x for x, y in points) / len(points)
    cy = sum(y for x, y in points) / len(points)

    # Sort by polar angle
    import math
    def polar_angle(p):
        return math.atan2(p[1] - cy, p[0] - cx)

    sorted_points = sorted(points, key=polar_angle)

    # Ensure it's a simple polygon (may still intersect, but better chance)
    return sorted_points


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

                # Clean repeats and closing repeats
                float_coords = []
                for c in coords:
                    try:
                        coord = float(c)
                        # Clamp to [0, 1]
                        coord = max(0.0, min(1.0, coord))
                        float_coords.append(coord)
                    except ValueError:
                        file_modified = True
                        continue

                # Pair into points
                points = []
                num_coords = len(float_coords)
                if num_coords % 2 != 0:
                    print(f"Skipping object in {label_file}: odd number of coordinates")
                    file_modified = True
                    continue
                for i in range(0, num_coords, 2):
                    points.append((float_coords[i], float_coords[i + 1]))

                # Remove consecutive duplicates
                cleaned_points = []
                for pt in points:
                    if not cleaned_points or pt != cleaned_points[-1]:
                        cleaned_points.append(pt)

                # Remove closing repeat if present
                if len(cleaned_points) > 1 and cleaned_points[0] == cleaned_points[-1]:
                    cleaned_points.pop()

                # Skip if <3 points after cleaning
                if len(cleaned_points) < 3:
                    print(f"Skipping object in {label_file}: fewer than 3 points")
                    file_modified = True
                    continue

                # Check zero area
                area = shoelace_area(cleaned_points)
                if area == 0:
                    print(f"Skipping object in {label_file}: zero area (collinear points)")
                    file_modified = True
                    continue

                # Check self-intersection and attempt fix
                if is_self_intersecting(cleaned_points):
                    print(f"Attempting to fix self-intersecting polygon in {label_file}")
                    cleaned_points = reorder_points_around_centroid(cleaned_points)
                    if is_self_intersecting(cleaned_points):
                        print(f"Skipping object in {label_file}: self-intersecting polygon (unfixable)")
                        file_modified = True
                        continue
                    else:
                        print(f"Fixed self-intersection via reordering in {label_file}")
                        file_modified = True

                # Flatten and format
                cleaned_coords = []
                for x, y in cleaned_points:
                    cleaned_coords.append(f"{round(x, 6):.6f}")
                    cleaned_coords.append(f"{round(y, 6):.6f}")

                if cleaned_coords != coords:
                    file_modified = True

                new_line = f"{class_id} {' '.join(cleaned_coords)}"
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
