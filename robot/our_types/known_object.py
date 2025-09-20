from typing import TypedDict, List
from robot.our_types.observation import Observation
from robot.our_types.classify import ClassificationConsensus


class KnownObject(TypedDict):
    main_camera_id: str
    observations: List[Observation]
    classification_consensus: ClassificationConsensus
