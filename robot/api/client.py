import time
from robot.our_types import SystemLifecycleStage
from robot.our_types.irl_runtime_params import IRLSystemRuntimeParams
from robot.our_types.bin_state import BinState


class API:
    def __init__(self, controller):
        self.controller = controller

    def get_lifecycle_stage(self) -> SystemLifecycleStage:
        return self.controller.lifecycle_stage

    def pause(self):
        self.controller.pause()

    def resume(self):
        self.controller.resume()

    def run(self):
        self.controller.run()

    def getIRLRuntimeParams(self) -> IRLSystemRuntimeParams:
        return self.controller.irl_interface["runtime_params"]

    def updateIRLRuntimeParams(self, params: IRLSystemRuntimeParams):
        self.controller.irl_interface["runtime_params"] = params

    def getBinState(self) -> BinState:
        return {
            "bin_contents": self.controller.bin_state_tracker.current_state,
            "timestamp": int(time.time() * 1000),
        }

    def updateBinCategory(self, coordinates: dict, category_id: str | None) -> None:
        from robot.our_types.bin import BinCoordinates

        bin_coords: BinCoordinates = {
            "distribution_module_idx": coordinates["distribution_module_idx"],
            "bin_idx": coordinates["bin_idx"],
        }
        self.controller.bin_state_tracker.updateBinCategory(bin_coords, category_id)

    def setMiscBin(self, coordinates: dict) -> None:
        from robot.our_types.bin import BinCoordinates

        bin_coords: BinCoordinates = {
            "distribution_module_idx": coordinates["distribution_module_idx"],
            "bin_idx": coordinates["bin_idx"],
        }
        self.controller.bin_state_tracker.setMiscBin(bin_coords)

    def setFallbackBin(self, coordinates: dict) -> None:
        from robot.our_types.bin import BinCoordinates

        bin_coords: BinCoordinates = {
            "distribution_module_idx": coordinates["distribution_module_idx"],
            "bin_idx": coordinates["bin_idx"],
        }
        self.controller.bin_state_tracker.setFallbackBin(bin_coords)
