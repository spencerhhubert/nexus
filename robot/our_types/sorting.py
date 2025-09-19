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
    # fs states are basically substates of GETTING_NEW_OBJECT_FROM_FEEDER
    # stands for Feeder State
    FS_OBJECT_AT_END_OF_2ND_FEEDER = "fs_object_at_end_of_2nd_feeder"
    FS_OBJECT_UNDERNEATH_EXIT_OF_1ST_FEEDER = "fs_object_underneath_exit_of_1st_feeder"
    FS_NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = (
        "fs_no_object_underneath_exit_of_first_feeder"
    )
    FS_FIRST_FEEDER_EMPTY = "fs_first_feeder_empty"
