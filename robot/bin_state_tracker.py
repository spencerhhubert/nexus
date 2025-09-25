from typing import List, Optional
import time
from robot.global_config import GlobalConfig
from robot.sorting.sorting_profile import SortingProfile
from robot.irl.distribution import DistributionModule
from robot.storage.sqlite3.operations import saveBinStateToDatabase
from robot.our_types.bin import BinCoordinates
from robot.our_types.bin_state import BinContentsMap, BinState, PersistedBinState


class BinStateTracker:
    def __init__(
        self,
        global_config: GlobalConfig,
        distribution_modules: List[DistributionModule],
        sorting_profile: SortingProfile,
        bin_state_id: Optional[str] = None,
    ):
        self.global_config = global_config
        self.distribution_modules = distribution_modules
        self.available_bin_coordinates = self._buildAvailableBinCoordinates()
        self.sorting_profile = sorting_profile
        self.misc_category_id = "misc"
        self.fallback_category_id = "fallback"
        self.current_bin_state_id: Optional[str] = None

        self.current_state: BinContentsMap = {}
        for coordinates in self.available_bin_coordinates:
            key = binCoordinatesToKey(coordinates)
            self.current_state[key] = None

        previous_state = None
        if bin_state_id:
            from robot.storage.sqlite3.operations import (
                getBinStateFromDatabase,
                getMostRecentBinState,
            )

            if bin_state_id == "latest":
                previous_state = getMostRecentBinState(global_config)
                if previous_state:
                    global_config["logger"].info(
                        f"Using most recent bin state: {previous_state['id']}"
                    )
            else:
                previous_state = getBinStateFromDatabase(global_config, bin_state_id)
                if previous_state:
                    global_config["logger"].info(f"Using bin state: {bin_state_id}")

            if not previous_state:
                global_config["logger"].info(
                    "No previous bin state found, starting fresh"
                )

        if previous_state:
            self.current_state.update(previous_state["bin_contents"])
            self.current_bin_state_id = previous_state["id"]
            self.global_config["logger"].info(
                f"Loaded previous bin state: {self.current_bin_state_id}"
            )

        # Reserve the second to last bin as misc and the last bin as fallback
        if len(self.available_bin_coordinates) >= 2:
            second_to_last_bin = self.available_bin_coordinates[-2]
            last_bin = self.available_bin_coordinates[-1]
            self._reserveBinInternal(second_to_last_bin, self.misc_category_id)
            self._reserveBinInternal(last_bin, self.fallback_category_id)
        elif len(self.available_bin_coordinates) == 1:
            # If only one bin, use it as misc
            last_bin = self.available_bin_coordinates[-1]
            self._reserveBinInternal(last_bin, self.misc_category_id)

        # Save initial state if this is a new bin state
        if not previous_state:
            self.current_bin_state_id = self.saveBinState()
            self.global_config["logger"].info(
                f"Created new bin state: {self.current_bin_state_id}"
            )

    def _buildAvailableBinCoordinates(self) -> List[BinCoordinates]:
        available_bins = []
        sorted_modules = sorted(
            enumerate(self.distribution_modules),
            key=lambda x: x[1].distance_from_camera_center_to_door_begin_cm,
        )

        for dm_idx, module in sorted_modules:
            for bin_idx in range(len(module.bins)):
                available_bins.append(
                    {"distribution_module_idx": dm_idx, "bin_idx": bin_idx}
                )

        return available_bins

    def findAvailableBin(self, category_id: str) -> Optional[BinCoordinates]:
        # First, try to find a bin that already has this category
        for coordinates in self.available_bin_coordinates:
            key = binCoordinatesToKey(coordinates)
            current_category = self.current_state.get(key)
            if current_category == category_id:
                return coordinates

        # If no existing bin found, look for an empty bin
        for coordinates in self.available_bin_coordinates:
            key = binCoordinatesToKey(coordinates)
            current_category = self.current_state.get(key)
            if current_category is None:
                return coordinates

        # If no empty bin available, fall back to fallback bin for categorized items
        if (
            category_id != self.misc_category_id
            and category_id != self.fallback_category_id
        ):
            self.global_config["logger"].info(
                f"No available bins for category '{category_id}', falling back to fallback bin"
            )

            for coordinates in self.available_bin_coordinates:
                key = binCoordinatesToKey(coordinates)
                current_category = self.current_state.get(key)
                if current_category == self.fallback_category_id:
                    return coordinates

        return None

    # Internal method to reserve bin without saving to database (used during initialization)
    def _reserveBinInternal(
        self, coordinates: BinCoordinates, category_id: str
    ) -> None:
        key = binCoordinatesToKey(coordinates)
        self.current_state[key] = category_id

    def reserveBin(self, coordinates: BinCoordinates, category_id: str) -> None:
        self._reserveBinInternal(coordinates, category_id)
        self.current_bin_state_id = self.saveBinState()

    def saveBinState(self) -> str:
        bin_state_id = saveBinStateToDatabase(self.global_config, self.current_state)
        return bin_state_id


def binCoordinatesToKey(coordinates: BinCoordinates) -> str:
    return f"{coordinates['distribution_module_idx']}_{coordinates['bin_idx']}"
