from abc import ABC, abstractmethod
from typing import TypedDict, Optional, Dict, Any
import numpy as np
from robot.global_config import GlobalConfig


class ClassificationResult:
    def __init__(self, tag: str, confidence: float, data: Dict[str, Any]):
        self.tag = tag
        self.confidence = confidence
        self.data = data

    def toJSON(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "confidence": self.confidence,
            "data": self.data
        }

    @staticmethod
    def fromJSON(json_data: Dict[str, Any]) -> "ClassificationResult":
        return ClassificationResult(
            tag=json_data["tag"],
            confidence=json_data["confidence"],
            data=json_data["data"]
        )


class Sorter(ABC):
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config

    @abstractmethod
    def classifySegment(self, segment_image: np.ndarray) -> ClassificationResult:
        pass

    @abstractmethod
    def lookupCategory(self, classification_result: ClassificationResult) -> Optional[str]:
        pass
