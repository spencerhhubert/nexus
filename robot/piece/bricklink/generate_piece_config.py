import os
from typing import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from robot.logger import Logger


class PieceGenerationConfig(TypedDict):
    ldraw_parts_list_path: str
    database_path: str
    debug_level: int
    logger: "Logger"


def buildPieceGenerationConfig() -> PieceGenerationConfig:
    debug_level = int(os.getenv("DEBUG", "0"))

    from robot.logger import Logger

    logger = Logger(debug_level)

    return {
        "ldraw_parts_list_path": "../ldraw/parts.lst",
        "database_path": "../database.db",
        "debug_level": debug_level,
        "logger": logger,
    }
