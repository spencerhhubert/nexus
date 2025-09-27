import time
from typing import Any, Dict


class Logger:
    def __init__(self, debug_level: int):
        self.debug_level = debug_level
        self.context: Dict[str, Any] = {}

    def ctx(self, **kwargs) -> "Logger":
        new_logger = Logger(self.debug_level)
        new_logger.context = {**self.context, **kwargs}
        return new_logger

    def _format_context(self) -> str:
        if not self.context:
            return ""
        context_parts = [f"{k}={v}" for k, v in self.context.items()]
        return f" [{', '.join(context_parts)}]"

    def info(self, message: str) -> None:
        if self.debug_level > 0:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            context = self._format_context()
            print(f"[{timestamp}] INFO{context}: {message}")

    def warning(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        context = self._format_context()
        print(f"[{timestamp}] WARNING{context}: {message}")

    def error(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        context = self._format_context()
        print(f"[{timestamp}] ERROR{context}: {message}")
