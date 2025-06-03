from robot.global_config import GlobalConfig


class Logger:
    def __init__(self, gc: GlobalConfig):
        self.gc = gc
        self.debug_level = gc["debug_level"]

    def info(self, message: str) -> None:
        if self.debug_level > 0:
            print(f"INFO: {message}")

    def warning(self, message: str) -> None:
        print(f"WARNING: {message}")

    def error(self, message: str) -> None:
        print(f"ERROR: {message}")
