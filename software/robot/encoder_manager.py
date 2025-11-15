import time
import threading
from collections import deque
from typing import List, Tuple, Optional
from robot.global_config import GlobalConfig
from robot.irl.encoder import Encoder

HISTORY_CUTOFF_SECONDS = 40
SPEED_WINDOW_1S_SAMPLES = 10
SPEED_WINDOW_5S_SAMPLES = 50
ENCODER_RESPONSE_WAIT_MS = 100


class EncoderManager:
    def __init__(self, gc: GlobalConfig, encoder: Encoder):
        self.gc = gc
        self.encoder = encoder
        self.data_lock = threading.Lock()

        self.position_history: List[Tuple[float, int, float]] = []
        self.speed_1s_window = deque(maxlen=SPEED_WINDOW_1S_SAMPLES)
        self.speed_5s_window = deque(maxlen=SPEED_WINDOW_5S_SAMPLES)

        self.last_position = 0
        self.last_position_time = time.time()
        self.current_speed_cm_per_s = 0.0

        self.running = True
        self.update_thread = threading.Thread(target=self._updateLoop, daemon=True)
        self.update_thread.start()

        self.gc["logger"].info("EncoderManager initialized")

    def _updateLoop(self) -> None:
        time.sleep(0.5)
        self.gc["logger"].info("EncoderManager update thread started")

        while self.running:
            try:
                self.encoder.requestLivePosition()
                time.sleep(ENCODER_RESPONSE_WAIT_MS / 1000.0)

                current_time = time.time()
                current_position = self.encoder.getCachedPosition()

                with self.data_lock:
                    self._updateSpeedCalculation(current_time, current_position)
                    self._updatePositionHistory(current_time, current_position)
                    self._cleanupOldData(current_time)

                time.sleep(self.gc["encoder_polling_delay_ms"] / 1000.0)
            except Exception as e:
                self.gc["logger"].error(f"EncoderManager update error: {e}")
                time.sleep(0.1)

    def _updateSpeedCalculation(
        self, current_time: float, current_position: int
    ) -> None:
        if self.last_position_time > 0:
            time_diff = current_time - self.last_position_time
            position_diff = abs(current_position - self.last_position)

            if time_diff > 0:
                distance_cm = (
                    position_diff / self.encoder.getPulsesPerRevolution()
                ) * self.encoder.getWheelCircumferenceCm()
                speed_cm_per_s = distance_cm / time_diff

                self.current_speed_cm_per_s = speed_cm_per_s
                self.speed_1s_window.append(speed_cm_per_s)
                self.speed_5s_window.append(speed_cm_per_s)

        self.last_position = current_position
        self.last_position_time = current_time

    def _updatePositionHistory(
        self, current_time: float, current_position: int
    ) -> None:
        distance_cm = (
            current_position / self.encoder.getPulsesPerRevolution()
        ) * self.encoder.getWheelCircumferenceCm()
        self.position_history.append((current_time, current_position, distance_cm))

    def _cleanupOldData(self, current_time: float) -> None:
        cutoff_time = current_time - HISTORY_CUTOFF_SECONDS
        self.position_history = [
            (t, pos, dist) for t, pos, dist in self.position_history if t > cutoff_time
        ]

    def getDistanceTraveledSince(self, timestamp: float) -> float:
        with self.data_lock:
            if not self.position_history:
                return 0.0

            start_distance = None
            for t, pos, dist in self.position_history:
                if t >= timestamp:
                    start_distance = dist
                    break

            if start_distance is None:
                return 0.0

            current_distance = self.position_history[-1][2]
            return start_distance - current_distance

    def getCurrentSpeedCmPerS(self) -> float:
        with self.data_lock:
            return self.current_speed_cm_per_s

    def getAverageSpeed1s(self) -> float:
        # Note: caller must hold data_lock
        try:
            if not self.speed_1s_window:
                return 0.0
            return sum(self.speed_1s_window) / len(self.speed_1s_window)
        except Exception as e:
            self.gc["logger"].error(f"getAverageSpeed1s error: {e}")
            return 0.0

    def getAverageSpeed5s(self) -> float:
        # Note: caller must hold data_lock
        try:
            if not self.speed_5s_window:
                return 0.0
            return sum(self.speed_5s_window) / len(self.speed_5s_window)
        except Exception as e:
            self.gc["logger"].error(f"getAverageSpeed5s error: {e}")
            return 0.0

    def getStatus(self) -> dict:
        with self.data_lock:
            return {
                "current_speed_cm_per_s": self.current_speed_cm_per_s,
                "average_speed_1s_cm_per_s": self.getAverageSpeed1s(),
                "average_speed_5s_cm_per_s": self.getAverageSpeed5s(),
                "position_history_count": len(self.position_history),
            }

    def stop(self) -> None:
        self.running = False
