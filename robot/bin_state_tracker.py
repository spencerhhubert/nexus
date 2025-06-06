from typing import Dict, List, Optional, TypedDict
import time
from robot.global_config import GlobalConfig
from robot.sorting import SortingProfile
from robot.irl.distribution import DistributionModule


class BinCoordinates(TypedDict):
    distribution_module_idx: int
    bin_idx: int


class BinState(TypedDict):
    bin_contents: Dict[str, Optional[str]]
    timestamp: int


class BinStateTracker:
    def __init__(
        self,
        global_config: GlobalConfig,
        distribution_modules: List[DistributionModule],
        sorting_profile: SortingProfile,
        previous_state: Optional[BinState] = None,
    ):
        self.global_config = global_config
        self.distribution_modules = distribution_modules
        self.available_bin_coordinates = self._buildAvailableBinCoordinates()
        self.sorting_profile = sorting_profile

        self.current_state: Dict[str, Optional[str]] = {}
        for coordinates in self.available_bin_coordinates:
            key = binCoordinatesToKey(coordinates)
            self.current_state[key] = None

        if previous_state:
            self.current_state.update(previous_state["bin_contents"])

    def _buildAvailableBinCoordinates(self) -> List[BinCoordinates]:
        available_bins = []
        sorted_modules = sorted(
            enumerate(self.distribution_modules),
            key=lambda x: x[1].distance_from_camera,
        )

        for dm_idx, module in sorted_modules:
            for bin_idx in range(len(module.bins)):
                available_bins.append(
                    {"distribution_module_idx": dm_idx, "bin_idx": bin_idx}
                )

        return available_bins

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


def binCoordinatesToKey(coordinates: BinCoordinates) -> str:
    return f"{coordinates['distribution_module_idx']}_{coordinates['bin_idx']}"
