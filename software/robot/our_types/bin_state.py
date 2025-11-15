from typing import Dict, Optional
from typing_extensions import TypedDict


BinContentsMap = Dict[str, Optional[str]]


class BinState(TypedDict):
    bin_contents: BinContentsMap
    timestamp: int


class PersistedBinState(TypedDict):
    id: str
    bin_contents: BinContentsMap
    created_at: int
    updated_at: int
    deleted_at: Optional[int]
