import time
import queue
import threading
from pyfirmata import ArduinoMega
from typing import List
from robot.global_config import GlobalConfig


class OurArduinoMega(ArduinoMega):
    def __init__(self, gc: GlobalConfig, port: str, command_delay_ms: int):
        super().__init__(port)
        self.gc = gc
        self.command_delay_ms = command_delay_ms / 1000.0
        self.command_queue = queue.Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._processCommands, daemon=True)
        self.worker_thread.start()

    def sysex(self, command: int, data: List[int]) -> None:
        if self.running:
            self.command_queue.put((command, data))
            queue_size = self.command_queue.qsize()
            if queue_size > 10:
                self.gc["logger"].warning(
                    f"Firmata command queue size is large: {queue_size} commands pending"
                )

    def _processCommands(self) -> None:
        while self.running:
            try:
                command, data = self.command_queue.get(timeout=1.0)
                self.gc["logger"].info(f"Sending command {command} with data {data}")
                self.send_sysex(command, data)
                time.sleep(self.command_delay_ms)
                self.command_queue.task_done()
            except queue.Empty:
                continue

    def flush(self) -> None:
        self.command_queue.join()

    def close(self) -> None:
        self.running = False
        self.flush()
        super().exit()
