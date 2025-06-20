import os
import numpy as np
import cv2
from PIL import Image
import json
from robot.global_config import GlobalConfig
from robot.storage.sqlite3.operations import saveObservationToDatabase


def ensureBlobStorageExists(global_config: GlobalConfig) -> None:
    run_blob_dir = global_config["run_blob_dir"]
    os.makedirs(run_blob_dir, exist_ok=True)


def saveTrajectory(global_config: GlobalConfig, trajectory) -> None:
    ensureBlobStorageExists(global_config)

    trajectory_dir = os.path.join(
        global_config["run_blob_dir"],
        f"traj_{trajectory.observations[0].captured_at_ms}_{trajectory.trajectory_id}",
    )
    os.makedirs(trajectory_dir, exist_ok=True)

    for observation in trajectory.observations:
        if observation.full_image_path is None:
            observation_dir = os.path.join(
                trajectory_dir,
                f"obs_{observation.captured_at_ms}_{observation.observation_id}",
            )
            os.makedirs(observation_dir, exist_ok=True)

            full_path = os.path.join(observation_dir, "full.jpg")
            rgb_full = cv2.cvtColor(observation.full_frame, cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb_full).save(full_path)

            masked_path = os.path.join(observation_dir, "masked.jpg")
            rgb_masked = cv2.cvtColor(observation.masked_image, cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb_masked).save(masked_path)

            classification_path = os.path.join(observation_dir, "classification.json")
            with open(classification_path, "w") as f:
                json.dump(observation.classification_result.toJSON(), f, indent=2)

            observation_json_path = os.path.join(observation_dir, "observation.json")
            with open(observation_json_path, "w") as f:
                json.dump(observation.toJSON(), f, indent=2)

            observation.full_image_path = full_path
            observation.masked_image_path = masked_path
            observation.classification_file_path = classification_path

            saveObservationToDatabase(global_config, observation)

    trajectory_path = os.path.join(trajectory_dir, "trajectory.json")
    with open(trajectory_path, "w") as f:
        json.dump(trajectory.toJSON(), f, indent=2)
