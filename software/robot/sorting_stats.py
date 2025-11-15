from typing import List, Optional
from robot.our_types.known_object import KnownObject

MAX_GAP_BETWEEN_KNOWN_OBJECTS_SECONDS = 120


def calculate_sorting_stats(
    all_known_objects: List[KnownObject],
) -> tuple[int, Optional[float]]:
    total_known_objects = len(all_known_objects)

    if total_known_objects < 2:
        return total_known_objects, None

    sorted_known_objects = sorted(all_known_objects, key=lambda obj: obj["created_at"])

    time_diffs = []
    for i in range(1, len(sorted_known_objects)):
        prev_time = sorted_known_objects[i - 1]["created_at"]
        curr_time = sorted_known_objects[i]["created_at"]
        diff = curr_time - prev_time

        if diff <= MAX_GAP_BETWEEN_KNOWN_OBJECTS_SECONDS:
            time_diffs.append(diff)

    if not time_diffs:
        return total_known_objects, None

    average_time_between_known_objects = sum(time_diffs) / len(time_diffs)
    return total_known_objects, average_time_between_known_objects
