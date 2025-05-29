import os
import argparse
from typing import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from robot.logger import Logger


class GlobalConfig(TypedDict):
    debug_level: int
    auto_confirm: bool
    logger: "Logger"


def buildGlobalConfig() -> GlobalConfig:
    parser = argparse.ArgumentParser(description="Robot control system")
    parser.add_argument("--auto-confirm", "-y", action="store_true", 
                       help="Automatically confirm all prompts")
    args = parser.parse_args()
    
    gc = {
        "debug_level": int(os.getenv("DEBUG", "0")),
        "auto_confirm": args.auto_confirm
    }
    
    from robot.logger import Logger
    gc["logger"] = Logger(gc)
    
    return gc
