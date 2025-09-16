from robot.our_types import SystemLifecycleStage


class API:
    def __init__(self, controller):
        self.controller = controller

    def get_lifecycle_stage(self) -> SystemLifecycleStage:
        return self.controller.lifecycle_stage

    def pause(self):
        self.controller.pause()

    def resume(self):
        self.controller.resume()
