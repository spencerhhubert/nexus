import threading
import time
from typing import Any, Optional, Dict, Tuple, List
from collections import deque


class ThreadSafeState:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._observation_queue: deque = deque()

    def set(self, key: str, value: Any) -> bool:
        if self._lock.acquire(blocking=False):
            try:
                self._data[key] = value
                self._timestamps[key] = time.time()
                return True
            finally:
                self._lock.release()
        return False

    def get(self, key: str) -> Optional[Any]:
        if self._lock.acquire(blocking=False):
            try:
                return self._data.get(key)
            finally:
                self._lock.release()
        return None

    def getWithTimestamp(self, key: str) -> Tuple[Optional[Any], Optional[float]]:
        if self._lock.acquire(blocking=False):
            try:
                value = self._data.get(key)
                timestamp = self._timestamps.get(key)
                return value, timestamp
            finally:
                self._lock.release()
        return None, None

    def hasNewData(self, key: str, since_timestamp: float) -> bool:
        if self._lock.acquire(blocking=False):
            try:
                current_timestamp = self._timestamps.get(key, 0)
                return current_timestamp > since_timestamp
            finally:
                self._lock.release()
        return False

    def setBlocking(self, key: str, value: Any, timeout: float = 1.0) -> bool:
        if self._lock.acquire(blocking=True, timeout=timeout):
            try:
                self._data[key] = value
                self._timestamps[key] = time.time()
                return True
            finally:
                self._lock.release()
        return False

    def getBlocking(self, key: str, timeout: float = 1.0) -> Optional[Any]:
        if self._lock.acquire(blocking=True, timeout=timeout):
            try:
                return self._data.get(key)
            finally:
                self._lock.release()
        return None

    def clear(self, key: str) -> bool:
        if self._lock.acquire(blocking=False):
            try:
                self._data.pop(key, None)
                self._timestamps.pop(key, None)
                return True
            finally:
                self._lock.release()
        return False

    def keys(self) -> list[str]:
        if self._lock.acquire(blocking=False):
            try:
                return list(self._data.keys())
            finally:
                self._lock.release()
        return []

    def enqueueObservation(self, observation) -> bool:
        if self._lock.acquire(blocking=False):
            try:
                self._observation_queue.append(observation)
                return True
            finally:
                self._lock.release()
        return False

    def dequeueObservations(self) -> List[Any]:
        if self._lock.acquire(blocking=False):
            try:
                observations = list(self._observation_queue)
                self._observation_queue.clear()
                return observations
            finally:
                self._lock.release()
        return []
