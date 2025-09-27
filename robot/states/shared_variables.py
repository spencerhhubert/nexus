from typing import Optional
from robot.our_types.known_object import KnownObject


class SharedVariables:
    def __init__(self):
        self.pending_known_object: Optional[KnownObject] = None
