from typing import TypedDict, Optional


class ClassificationResult(TypedDict):
    id: str
    category_id: str


class ClassificationConsensus(TypedDict):
    id: str
    category_id: str
