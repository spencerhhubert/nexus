from typing import TypedDict, List, Optional
from robot.our_types.observation import Observation
from robot.our_types.classify import ClassificationConsensus
from robot.our_types.bin import BinCoordinates


class KnownObject(TypedDict):
    uuid: str
    main_camera_id: str
    observations: List[Observation]
    classification_consensus: ClassificationConsensus
    bin_coordinates: Optional[BinCoordinates]
