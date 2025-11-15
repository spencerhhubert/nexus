from typing import Optional, List
from robot.our_types.known_object import KnownObject


class SharedVariables:
    def __init__(self):
        self.pending_known_object: Optional[KnownObject] = None
        self.all_known_objects: List[KnownObject] = []
