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
