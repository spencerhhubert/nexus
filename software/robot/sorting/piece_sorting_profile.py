from typing import TypedDict, Optional, Dict
from robot.sorting.sorting_profile import SortingProfile
from robot.global_config import GlobalConfig


class Kind(TypedDict):
    kind_id: str
    name: Optional[str]
    description: Optional[str]


class Color(TypedDict):
    color_id: str
    name: Optional[str]
    hex_code: Optional[str]


class Piece(TypedDict):
    item_id: str
    kind_id: str
    color_id: str


class PieceSortingProfile(SortingProfile):
    def __init__(
        self,
        global_config: GlobalConfig,
        profile_name: str,
        item_id_to_category_id_mapping: Dict[str, str],
        description: Optional[str] = None,
        kinds: Optional[Dict[str, Kind]] = None,
        colors: Optional[Dict[str, Color]] = None,
        pieces: Optional[Dict[str, Piece]] = None,
    ):
        super().__init__(global_config, profile_name, description)
        self.item_id_to_category_id_mapping = item_id_to_category_id_mapping
        self.kinds = kinds or {}
        self.colors = colors or {}
        self.pieces = pieces or {}

    def getCategoryId(self, item_id: str) -> Optional[str]:
        return self.item_id_to_category_id_mapping.get(item_id)

    def addItemMapping(self, item_id: str, category_id: str) -> None:
        self.item_id_to_category_id_mapping[item_id] = category_id

    def getKind(self, kind_id: str) -> Optional[Kind]:
        return self.kinds.get(kind_id)

    def getColor(self, color_id: str) -> Optional[Color]:
        return self.colors.get(color_id)

    def getPiece(self, item_id: str) -> Optional[Piece]:
        return self.pieces.get(item_id)

    def addKind(self, kind: Kind) -> None:
        self.kinds[kind["kind_id"]] = kind

    def addColor(self, color: Color) -> None:
        self.colors[color["color_id"]] = color

    def addPiece(self, piece: Piece) -> None:
        self.pieces[piece["item_id"]] = piece
