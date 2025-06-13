import time


class Logger:
    def __init__(self, debug_level: int):
        self.debug_level = debug_level

    def info(self, message: str) -> None:
        if self.debug_level > 0:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"[{timestamp}] INFO: {message}")

    def warning(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{timestamp}] WARNING: {message}")

    def error(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{timestamp}] ERROR: {message}")
