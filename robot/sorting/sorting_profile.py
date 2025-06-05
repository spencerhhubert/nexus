from typing import Dict, Optional
from robot.global_config import GlobalConfig
from robot.sorting.category import Category


class SortingProfile:
    def __init__(
        self,
        global_config: GlobalConfig,
        profile_name: str,
        item_id_to_category_mapping: Dict[str, Category],
    ):
        self.global_config = global_config
        self.profile_name = profile_name
        self.item_id_to_category_mapping = item_id_to_category_mapping
