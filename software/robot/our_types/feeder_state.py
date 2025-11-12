from enum import Enum


class FeederState(Enum):
    OBJECT_AT_END_OF_SECOND_FEEDER = "object_at_end_of_second_feeder"
    OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = "object_underneath_exit_of_first_feeder"
    NO_OBJECT_UNDERNEATH_EXIT_OF_FIRST_FEEDER = (
        "no_object_underneath_exit_of_first_feeder"
    )
    FIRST_FEEDER_EMPTY = "first_feeder_empty"
    OBJECT_ON_MAIN_CONVEYOR = "object_on_main_conveyor"
