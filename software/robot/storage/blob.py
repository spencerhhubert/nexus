import os
from robot.global_config import GlobalConfig


def ensureBlobStorageExists(global_config: GlobalConfig) -> None:
    run_blob_dir = global_config["run_blob_dir"]
    os.makedirs(run_blob_dir, exist_ok=True)
