from robot.our_types import SystemLifecycleStage
from robot.our_types.irl_runtime_params import IRLSystemRuntimeParams


class API:
    def __init__(self, controller):
        self.controller = controller

    def get_lifecycle_stage(self) -> SystemLifecycleStage:
        return self.controller.lifecycle_stage

    def pause(self):
        self.controller.pause()

    def resume(self):
        self.controller.resume()

    def getIRLRuntimeParams(self) -> IRLSystemRuntimeParams:
        return self.controller.irl_interface["runtimeParams"]

    def updateIRLRuntimeParams(self, params: IRLSystemRuntimeParams):
        self.controller.irl_interface["runtimeParams"] = params
