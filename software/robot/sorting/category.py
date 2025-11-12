from typing import Optional
from robot.global_config import GlobalConfig


class Category:
    def __init__(
        self,
        global_config: GlobalConfig,
        category_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.global_config = global_config
        self.category_id = category_id
        self.name = name
        self.description = description
