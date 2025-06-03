import time
import threading
from robot.global_config import GlobalConfig
from robot.bin_state_tracker import BinCoordinates

DOOR_OPEN_DURATION_MS = 500


class DoorScheduler:
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config

    def scheduleDoorAction(
        self, bin_coordinates: BinCoordinates, delay_ms: int = 0
    ) -> None:
        def executeDoorAction():
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

            self.global_config["logger"].info(f"Opening door for bin {bin_coordinates}")

            time.sleep(DOOR_OPEN_DURATION_MS / 1000.0)

            self.global_config["logger"].info(f"Closing door for bin {bin_coordinates}")

        thread = threading.Thread(target=executeDoorAction, daemon=True)
        thread.start()
