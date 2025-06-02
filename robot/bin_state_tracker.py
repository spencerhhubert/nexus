from typing import Dict, List, Optional, TypedDict
import time
from robot.global_config import GlobalConfig
from robot.sorting import SortingProfile


class BinCoordinates(TypedDict):
    distribution_module_idx: int
    bin_idx: int


class BinState(TypedDict):
    bin_contents: Dict[str, Optional[str]]
    timestamp: int


class BinStateTracker:
    def __init__(self, global_config: GlobalConfig, available_bin_coordinates: List[BinCoordinates],
                 sorting_profile: SortingProfile, previous_state: Optional[BinState] = None):
        self.global_config = global_config
        self.available_bin_coordinates = available_bin_coordinates
        self.sorting_profile = sorting_profile

        self.current_state: Dict[str, Optional[str]] = {}
        for coordinates in available_bin_coordinates:
            key = binCoordinatesToKey(coordinates)
            self.current_state[key] = None

        if previous_state:
            self.current_state.update(previous_state['bin_contents'])

    def findAvailableBin(self, category_id: str) -> Optional[BinCoordinates]:
        for coordinates in self.available_bin_coordinates:
            key = binCoordinatesToKey(coordinates)
            current_category = self.current_state.get(key)
            if current_category is None:
                return coordinates
        return None

    def reserveBin(self, coordinates: BinCoordinates, category_id: str) -> None:
        key = binCoordinatesToKey(coordinates)
        self.current_state[key] = category_id

    def getCurrentState(self) -> BinState:
        return {
            'bin_contents': self.current_state.copy(),
            'timestamp': int(time.time() * 1000)
        }


def binCoordinatesToKey(coordinates: BinCoordinates) -> str:
    return f"{coordinates['distribution_module_idx']}_{coordinates['bin_idx']}"
