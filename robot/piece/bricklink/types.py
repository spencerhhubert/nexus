from typing import TypedDict, List, Optional, Union
from enum import Enum
from robot.our_types import BricklinkPartData


class GENERATE_PIECE_KIND_FAILED_REASON(Enum):
    COULD_NOT_FIND_PRIMARY_ID = "could_not_find_primary_id"
    COULD_NOT_GET_PART_INFO = "could_not_get_part_info"
    SCRAPING_ERROR = "scraping_error"
    API_ERROR = "api_error"


class BricklinkApiMeta(TypedDict):
    description: str
    message: str
    code: int


class BricklinkPartResponse(TypedDict):
    meta: BricklinkApiMeta
    data: BricklinkPartData


class BricklinkCategoryData(TypedDict):
    category_id: int
    category_name: str
    parent_id: int


class BricklinkCategoriesResponse(TypedDict):
    meta: BricklinkApiMeta
    data: List[BricklinkCategoryData]


class BricklinkColorData(TypedDict):
    color_id: int
    color_name: str
    color_code: str
    color_type: str


class BricklinkColorsResponse(TypedDict):
    meta: BricklinkApiMeta
    data: List[BricklinkColorData]


class BricklinkSearchResultItem(TypedDict):
    strItemNo: str
    strItemName: str
    strItemType: str
    strCategoryName: str


class BricklinkSearchResultTypeList(TypedDict):
    items: List[BricklinkSearchResultItem]


class BricklinkSearchResult(TypedDict):
    typeList: List[BricklinkSearchResultTypeList]


class BricklinkSearchResponse(TypedDict):
    result: BricklinkSearchResult
