from typing import TypedDict, List


class BrickognizeExternalSite(TypedDict):
    name: str
    url: str


class BrickognizeBoundingBox(TypedDict):
    left: float
    upper: float
    right: float
    lower: float
    image_width: float
    image_height: float
    score: float


class BrickognizeItem(TypedDict):
    id: str
    name: str
    img_url: str
    external_sites: List[BrickognizeExternalSite]
    category: str
    type: str
    score: float


class BrickognizeClassificationResult(TypedDict):
    listing_id: str
    bounding_box: BrickognizeBoundingBox
    items: List[BrickognizeItem]
