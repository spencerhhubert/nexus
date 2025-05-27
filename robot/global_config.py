import os
import argparse
from typing import TypedDict


class GlobalConfig(TypedDict):
    debug_level: int
    auto_confirm: bool


def buildGlobalConfig() -> GlobalConfig:
    parser = argparse.ArgumentParser(description="Robot control system")
    parser.add_argument("--auto-confirm", "-y", action="store_true", 
                       help="Automatically confirm all prompts")
    args = parser.parse_args()
    
    return {
        "debug_level": int(os.getenv("DEBUG", "0")),
        "auto_confirm": args.auto_confirm
    }
