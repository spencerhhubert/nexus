from abc import ABC, abstractmethod
from typing import Optional
from robot.global_config import GlobalConfig


class SortingProfile(ABC):
    def __init__(
        self,
        global_config: GlobalConfig,
        profile_name: str,
        description: Optional[str] = None,
    ):
        self.global_config = global_config
        self.profile_name = profile_name
        self.description = description

    @abstractmethod
    def getCategoryId(self, item_id: str) -> Optional[str]:
        pass
