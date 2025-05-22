import os
from typing import TypedDict

class GlobalConfig(TypedDict):
    debug_level: int

def buildGlobalConfig() -> GlobalConfig:
    return {
        "debug_level": int(os.getenv("DEBUG", "0"))
    }