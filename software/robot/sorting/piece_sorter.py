from typing import TypedDict, Optional, Dict, Any, cast
import numpy as np
from robot.sorting.sorter import Sorter, ClassificationResult
from robot.sorting.piece_sorting_profile import PieceSortingProfile
from robot.ai.classify import brickognizeClassifySegment
from robot.ai.brickognize_types import BrickognizeClassificationResult
from robot.global_config import GlobalConfig


class PieceClassificationResult(TypedDict):
    item_id: Optional[str]
    kind_id: Optional[str]
    color_id: Optional[str]
    confidence: float
    brickognize_data: Dict[str, Any]


class PieceSorter(Sorter):
    def __init__(
        self, global_config: GlobalConfig, sorting_profile: PieceSortingProfile
    ):
        super().__init__(global_config)
        self.sorting_profile = sorting_profile

    def classifySegment(self, segment_image: np.ndarray) -> ClassificationResult:
        brickognize_result = brickognizeClassifySegment(
            segment_image, self.global_config
        )
        piece_result = self._convertBrickognizeResult(brickognize_result)

        return ClassificationResult(
            tag="piece_classification",
            confidence=piece_result["confidence"],
            data=cast(Dict[str, Any], piece_result),
        )

    def lookupCategory(
        self, classification_result: ClassificationResult
    ) -> Optional[str]:
        if classification_result.tag != "piece_classification":
            return None

        piece_data = classification_result.data
        item_id = piece_data.get("item_id")

        if item_id:
            return self.sorting_profile.getCategoryId(item_id)

        return None

    def _convertBrickognizeResult(
        self, brickognize_result: BrickognizeClassificationResult
    ) -> PieceClassificationResult:
        item_id = None
        confidence = 0.0

        if brickognize_result.get("items"):
            best_item = brickognize_result["items"][0]
            item_id = best_item.get("id")
            confidence = best_item.get("score", 0.0)

        return PieceClassificationResult(
            item_id=item_id,
            kind_id=None,
            color_id=None,
            confidence=confidence,
            brickognize_data=cast(Dict[str, Any], brickognize_result),
        )
