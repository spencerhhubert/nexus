from enum import Enum


class SortingState(Enum):
    GETTING_NEW_OBJECT_FROM_FEEDER = "getting_new_object_from_feeder"
    WAITING_FOR_OBJECT_TO_APPEAR_UNDER_MAIN_CAMERA = (
        "waiting_for_object_to_appear_under_main_camera"
    )
    WAITING_FOR_OBJECT_TO_CENTER_UNDER_MAIN_CAMERA = (
        "waiting_for_object_to_center_under_main_camera"
    )
    CLASSIFYING = "classifying"
    SENDING_OBJECT_TO_BIN = "sending_object_to_bin"
