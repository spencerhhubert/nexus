from typing import TypedDict, Optional


class TickProfilingRecord(TypedDict):
    tick_start_time_ms: float
    tick_end_time_ms: float
    total_tick_duration_ms: float

    frame_capture_start_ms: Optional[float]
    frame_capture_duration_ms: Optional[float]

    segmentation_start_ms: Optional[float]
    segmentation_duration_ms: Optional[float]
    segments_found_count: int

    classification_total_duration_ms: float
    classification_calls_count: int

    trigger_actions_start_ms: Optional[float]
    trigger_actions_duration_ms: Optional[float]

    cleanup_start_ms: Optional[float]
    cleanup_duration_ms: Optional[float]

    observation_save_total_duration_ms: float
    observations_saved_count: int


def createTickProfilingRecord(start_time_ms: float) -> TickProfilingRecord:
    return TickProfilingRecord(
        tick_start_time_ms=start_time_ms,
        tick_end_time_ms=0.0,
        total_tick_duration_ms=0.0,
        frame_capture_start_ms=None,
        frame_capture_duration_ms=None,
        segmentation_start_ms=None,
        segmentation_duration_ms=None,
        segments_found_count=0,
        classification_total_duration_ms=0.0,
        classification_calls_count=0,
        trigger_actions_start_ms=None,
        trigger_actions_duration_ms=None,
        cleanup_start_ms=None,
        cleanup_duration_ms=None,
        observation_save_total_duration_ms=0.0,
        observations_saved_count=0,
    )


def finalizeTickProfilingRecord(
    record: TickProfilingRecord, end_time_ms: float
) -> None:
    record["tick_end_time_ms"] = end_time_ms
    record["total_tick_duration_ms"] = end_time_ms - record["tick_start_time_ms"]


def printTickProfilingReport(record: TickProfilingRecord) -> None:
    print(f"\n=== Tick Profiling Report ===")
    print(f"Total tick duration: {record['total_tick_duration_ms']:.2f}ms")

    if record["frame_capture_duration_ms"] is not None:
        print(f"Frame capture: {record['frame_capture_duration_ms']:.2f}ms")

    if record["segmentation_duration_ms"] is not None:
        print(
            f"Segmentation: {record['segmentation_duration_ms']:.2f}ms ({record['segments_found_count']} segments)"
        )

    if record["classification_calls_count"] > 0:
        avg_classification_ms = (
            record["classification_total_duration_ms"]
            / record["classification_calls_count"]
        )
        print(
            f"Classification: {record['classification_total_duration_ms']:.2f}ms total ({record['classification_calls_count']} calls, {avg_classification_ms:.2f}ms avg)"
        )

    if record["observation_save_total_duration_ms"] > 0:
        avg_save_ms = record["observation_save_total_duration_ms"] / max(
            1, record["observations_saved_count"]
        )
        print(
            f"Observation saves: {record['observation_save_total_duration_ms']:.2f}ms total ({record['observations_saved_count']} saves, {avg_save_ms:.2f}ms avg)"
        )

    if record["trigger_actions_duration_ms"] is not None:
        print(f"Trigger actions: {record['trigger_actions_duration_ms']:.2f}ms")

    if record["cleanup_duration_ms"] is not None:
        print(f"Cleanup: {record['cleanup_duration_ms']:.2f}ms")

    print(f"==============================\n")
