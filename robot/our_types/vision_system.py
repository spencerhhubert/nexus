from enum import Enum


class FeederState(Enum):
    OBJECT_AT_END_OF_SECOND_FEEDER = "object_at_end_of_second_feeder"
    OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = "object_underneath_exit_of_first_feeder"
    NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = (
        "no_object_underneath_exit_of_first_feeder"
    )
    FIRST_FEEDER_EMPTY = "first_feeder_empty"


class MainCameraState(Enum):
    NO_OBJECT_UNDER_CAMERA = "no_object_under_camera"
    WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA = (
        "waiting_for_object_to_center_under_main_camera"
    )
    OBJECT_CENTERED_UNDER_MAIN_CAMERA = "object_centered_under_main_camera"
