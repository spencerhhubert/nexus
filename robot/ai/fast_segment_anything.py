from fastsam import FastSAM, FastSAMPrompt  # type: ignore
import time
import torch
from PIL import Image
import numpy as np
import os
import cv2
from scipy import ndimage
from typing import List, Dict, Any, Tuple, cast

from robot.global_config import GlobalConfig

# Parameters
FILTERING_PARAMS = {
    "background_threshold": 0.20,
    "border_region_ratio": 0.1,
    "border_overlap_threshold": 0.25,
    "nested_threshold": 0.9,
    "merge_distance_px": 64 * 2,
    "multi_mask_expansion_px": 50,
    "filter_disjoint_segments": True,
    "disjoint_separation_threshold_px": 4,
}

FASTSAM_CONFIG = {"retina_masks": True, "imgsz": 512, "conf": 0.3, "iou": 0.8}


def filterMasks(
    masks: List[torch.Tensor], image_height: int, image_width: int
) -> List[torch.Tensor]:
    filtered_masks = []

    for mask in masks:
        mask = mask.bool()
        mask_area = mask.sum().item()
        total_pixels = image_height * image_width

        if mask_area / total_pixels > FILTERING_PARAMS["background_threshold"]:
            continue

        border_width = int(image_width * FILTERING_PARAMS["border_region_ratio"])
        border_height = int(image_height * FILTERING_PARAMS["border_region_ratio"])

        border_mask = torch.zeros_like(mask, dtype=torch.bool)
        border_mask[:border_height, :] = True
        border_mask[-border_height:, :] = True
        border_mask[:, :border_width] = True
        border_mask[:, -border_width:] = True

        border_overlap = (mask & border_mask).sum().item()
        border_overlap_ratio = border_overlap / mask_area if mask_area > 0 else 0

        if border_overlap_ratio > FILTERING_PARAMS["border_overlap_threshold"]:
            continue

        filtered_masks.append(mask)

    return filtered_masks


def removeNestedSegments(masks: List[torch.Tensor]) -> List[torch.Tensor]:
    filtered_masks = []

    for i, mask_a in enumerate(masks):
        is_nested = False
        for j, mask_b in enumerate(masks):
            if i != j:
                overlap = (mask_a & mask_b).sum().item()
                mask_a_area = mask_a.sum().item()

                if (
                    mask_a_area > 0
                    and overlap / mask_a_area > FILTERING_PARAMS["nested_threshold"]
                ):
                    is_nested = True
                    break

        if not is_nested:
            filtered_masks.append(mask_a)

    return filtered_masks


def mergeCloseSegments(masks: List[torch.Tensor]) -> List[torch.Tensor]:
    if len(masks) == 0:
        return masks

    merged_groups = []
    used_indices = set()

    for i, mask_a in enumerate(masks):
        if i in used_indices:
            continue

        current_group = [i]
        mask_a_np = mask_a.cpu().numpy()
        coords_a = np.where(mask_a_np)

        if len(coords_a[0]) == 0:
            continue

        y_min_a, y_max_a = coords_a[0].min(), coords_a[0].max()
        x_min_a, x_max_a = coords_a[1].min(), coords_a[1].max()

        for j, mask_b in enumerate(masks):
            if j <= i or j in used_indices:
                continue

            mask_b_np = mask_b.cpu().numpy()
            coords_b = np.where(mask_b_np)

            if len(coords_b[0]) == 0:
                continue

            y_min_b, y_max_b = coords_b[0].min(), coords_b[0].max()
            x_min_b, x_max_b = coords_b[1].min(), coords_b[1].max()

            dx = max(0, max(x_min_a, x_min_b) - min(x_max_a, x_max_b))
            dy = max(0, max(y_min_a, y_min_b) - min(y_max_a, y_max_b))
            distance = (dx * dx + dy * dy) ** 0.5

            if distance <= FILTERING_PARAMS["merge_distance_px"]:
                current_group.append(j)

        for idx in current_group:
            used_indices.add(idx)
        merged_groups.append(current_group)

    merged_masks = []
    for group in merged_groups:
        if len(group) == 1:
            merged_masks.append(masks[group[0]])
        else:
            combined_mask = masks[group[0]].clone()
            for idx in group[1:]:
                combined_mask = combined_mask | masks[idx]
            merged_masks.append(combined_mask)

    return merged_masks


def groupOverlappingMasks(masks: List[torch.Tensor]) -> List[List[Dict[str, Any]]]:
    # Group masks that have overlapping or nearby bounding boxes
    if len(masks) == 0:
        return []

    mask_data = []
    for i, mask in enumerate(masks):
        mask_np = mask.cpu().numpy()
        coords = np.where(mask_np)
        if len(coords[0]) > 0:
            y_min, y_max = coords[0].min(), coords[0].max()
            x_min, x_max = coords[1].min(), coords[1].max()
            mask_data.append(
                {"mask": mask, "bbox": (y_min, y_max, x_min, x_max), "index": i}
            )

    groups = []
    used_indices = set()

    for i, data_a in enumerate(mask_data):
        if i in used_indices:
            continue

        current_group = [data_a]
        current_indices = [i]
        y_min_a, y_max_a, x_min_a, x_max_a = data_a["bbox"]

        for j, data_b in enumerate(mask_data):
            if j <= i or j in used_indices:
                continue

            y_min_b, y_max_b, x_min_b, x_max_b = data_b["bbox"]

            # Check if bounding boxes overlap or are close
            overlap_x = not (x_max_a < x_min_b or x_max_b < x_min_a)
            overlap_y = not (y_max_a < y_min_b or y_max_b < y_min_a)

            if overlap_x and overlap_y:
                current_group.append(data_b)
                current_indices.append(j)

        for idx in current_indices:
            used_indices.add(idx)
        groups.append(current_group)

    return groups


def countConnectedComponents(mask: torch.Tensor) -> int:
    # Count separate clumps of pixels using connected components analysis
    mask_np = mask.cpu().numpy().astype(np.uint8)
    result = cast(Tuple[np.ndarray, int], ndimage.label(mask_np))
    num_components = result[1]
    return int(num_components)


def filterDisjointSegments(masks: List[torch.Tensor]) -> List[torch.Tensor]:
    # Filter out segments that have multiple disconnected clumps separated by large distances
    # This helps reduce instances where we segment a bunch of features of an object, but not the entire object
    if not FILTERING_PARAMS["filter_disjoint_segments"]:
        return masks

    filtered_masks = []
    separation_threshold = FILTERING_PARAMS["disjoint_separation_threshold_px"]

    for mask in masks:
        mask_np = mask.cpu().numpy().astype(np.uint8)
        result = cast(Tuple[np.ndarray, int], ndimage.label(mask_np))
        labeled_mask, num_components = result

        if num_components <= 1:
            # Single component or no components, keep it
            filtered_masks.append(mask)
            continue

        # Find centroids of each component
        component_centroids = []
        for component_id in range(1, num_components + 1):
            component_pixels = np.where(labeled_mask == component_id)
            if len(component_pixels[0]) > 0:
                centroid_y = np.mean(component_pixels[0])
                centroid_x = np.mean(component_pixels[1])
                component_centroids.append((centroid_x, centroid_y))

        # Check if any pair of components is separated by more than threshold
        is_disjoint = False
        for i in range(len(component_centroids)):
            for j in range(i + 1, len(component_centroids)):
                cx1, cy1 = component_centroids[i]
                cx2, cy2 = component_centroids[j]
                distance = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5

                if distance > separation_threshold:
                    is_disjoint = True
                    break
            if is_disjoint:
                break

        if not is_disjoint:
            filtered_masks.append(mask)

    return filtered_masks


def processSegmentGroups(
    segment_groups: List[List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    # Process each group of segments
    # If multiple masks in overlapping bounding boxes, assume model failed to identify complete object
    # and is seeing features of a single object instead of the whole thing
    processed_groups = []

    for group in segment_groups:
        masks = [data["mask"] for data in group]

        if len(masks) > 1:
            # Multiple masks with overlapping bounding boxes - treat as incomplete object detection
            # Don't mask pixels and expand bounding box to capture full object
            combined_mask = masks[0].clone()
            for mask in masks[1:]:
                combined_mask = combined_mask | mask

            # Count connected components in combined mask
            component_count = countConnectedComponents(combined_mask)

            # Get combined bounding box and expand it
            mask_np = combined_mask.cpu().numpy()
            coords = np.where(mask_np)

            if len(coords[0]) > 0:
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                expansion = FILTERING_PARAMS["multi_mask_expansion_px"]
                y_min = max(0, y_min - expansion)
                y_max = min(mask_np.shape[0] - 1, y_max + expansion)
                x_min = max(0, x_min - expansion)
                x_max = min(mask_np.shape[1] - 1, x_max + expansion)

                processed_groups.append(
                    {
                        "bbox": (y_min, y_max, x_min, x_max),
                        "apply_mask": False,
                        "mask": combined_mask,
                        "mask_count": len(masks),
                        "component_count": component_count,
                    }
                )
        else:
            # Single mask - check for multiple connected components
            mask = masks[0]
            component_count = countConnectedComponents(mask)

            mask_np = mask.cpu().numpy()
            coords = np.where(mask_np)

            if len(coords[0]) > 0:
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()

                # If single mask has multiple disconnected clumps, treat like multi-mask case
                if component_count > 1:
                    expansion = FILTERING_PARAMS["multi_mask_expansion_px"]
                    y_min = max(0, y_min - expansion)
                    y_max = min(mask_np.shape[0] - 1, y_max + expansion)
                    x_min = max(0, x_min - expansion)
                    x_max = min(mask_np.shape[1] - 1, x_max + expansion)

                    processed_groups.append(
                        {
                            "bbox": (y_min, y_max, x_min, x_max),
                            "apply_mask": False,
                            "mask": mask,
                            "mask_count": 1,
                            "component_count": component_count,
                        }
                    )
                else:
                    processed_groups.append(
                        {
                            "bbox": (y_min, y_max, x_min, x_max),
                            "apply_mask": True,
                            "mask": mask,
                            "mask_count": 1,
                            "component_count": component_count,
                        }
                    )

    return processed_groups


def postProcessMasks(
    masks: torch.Tensor, image_height: int, image_width: int
) -> List[Dict[str, Any]]:
    if len(masks) == 0:
        return []

    # Convert tensor to list of individual masks
    mask_list = [masks[i] for i in range(masks.shape[0])]

    # Step 1: Filter background and border masks
    filtered = filterMasks(mask_list, image_height, image_width)
    if len(filtered) == 0:
        return []

    # Step 2: Remove nested segments
    nested_filtered = removeNestedSegments(filtered)
    if len(nested_filtered) == 0:
        return []

    # Step 3: Merge close segments
    merged = mergeCloseSegments(nested_filtered)
    if len(merged) == 0:
        return []

    # Step 4: Filter disjoint segments
    disjoint_filtered = filterDisjointSegments(merged)
    if len(disjoint_filtered) == 0:
        return []

    # Step 5: Group overlapping masks and process multi-mask cases
    segment_groups = groupOverlappingMasks(disjoint_filtered)
    processed = processSegmentGroups(segment_groups)

    return processed


def _segmentFrame(
    frame: np.ndarray, model: FastSAM, global_config: GlobalConfig
) -> List[Dict[str, Any]]:
    device = global_config["tensor_device"]

    everything_results = model(frame, device=device, **FASTSAM_CONFIG)
    prompt_process = FastSAMPrompt(frame, everything_results, device=device)
    ann = prompt_process.everything_prompt()

    processed_groups: List[Dict[str, Any]] = []
    if len(ann) > 0:
        ann_tensor = torch.stack(ann) if isinstance(ann, list) else ann
        image_height, image_width = ann_tensor.shape[1], ann_tensor.shape[2]
        processed_groups = postProcessMasks(ann_tensor, image_height, image_width)

    return processed_groups
