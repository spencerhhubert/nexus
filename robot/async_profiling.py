import time
import threading
import uuid
import cProfile
import pstats
import io
import os
from typing import TypedDict, Optional, List, Dict, Any
from collections import deque
from robot.global_config import GlobalConfig


class AsyncFrameProfilingRecord(TypedDict):
    frame_id: str
    thread_id: str

    # Timing milestones
    submitted_to_queue_ms: float
    processing_started_ms: float
    processing_completed_ms: float

    # Derived timings
    queue_wait_duration_ms: float
    total_processing_duration_ms: float

    # Step-by-step profiling
    segmentation_start_ms: Optional[float]
    segmentation_duration_ms: Optional[float]
    segments_found_count: int

    classification_total_duration_ms: float
    classification_calls_count: int

    observation_save_total_duration_ms: float
    observations_saved_count: int

    # Thread contention detection
    delayed_by_previous_frame: bool
    thread_was_busy_ms: Optional[float]


class AsyncProfilingAggregator:
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config
        self.completed_records: deque[AsyncFrameProfilingRecord] = deque(maxlen=100)
        self.active_records: Dict[str, AsyncFrameProfilingRecord] = {}
        self.thread_last_completion: Dict[str, float] = {}
        self.lock = threading.Lock()

    def createFrameRecord(self) -> AsyncFrameProfilingRecord:
        frame_id = str(uuid.uuid4())[:8]
        thread_id = threading.current_thread().name
        submitted_time_ms = time.time() * 1000

        # Check if this thread was busy with a previous frame
        delayed_by_previous = False
        thread_was_busy_ms = None

        with self.lock:
            if thread_id in self.thread_last_completion:
                time_since_last_completion = (
                    submitted_time_ms - self.thread_last_completion[thread_id]
                )
                if (
                    time_since_last_completion < 10
                ):  # Less than 10ms gap = likely delayed
                    delayed_by_previous = True
                    thread_was_busy_ms = time_since_last_completion

        record = AsyncFrameProfilingRecord(
            frame_id=frame_id,
            thread_id=thread_id,
            submitted_to_queue_ms=submitted_time_ms,
            processing_started_ms=0.0,
            processing_completed_ms=0.0,
            queue_wait_duration_ms=0.0,
            total_processing_duration_ms=0.0,
            segmentation_start_ms=None,
            segmentation_duration_ms=None,
            segments_found_count=0,
            classification_total_duration_ms=0.0,
            classification_calls_count=0,
            observation_save_total_duration_ms=0.0,
            observations_saved_count=0,
            delayed_by_previous_frame=delayed_by_previous,
            thread_was_busy_ms=thread_was_busy_ms,
        )

        with self.lock:
            self.active_records[frame_id] = record

        return record

    def startFrameProcessing(self, record: AsyncFrameProfilingRecord) -> None:
        processing_start_ms = time.time() * 1000
        record["processing_started_ms"] = processing_start_ms
        record["queue_wait_duration_ms"] = (
            processing_start_ms - record["submitted_to_queue_ms"]
        )

    def completeFrameProcessing(self, record: AsyncFrameProfilingRecord) -> None:
        processing_end_ms = time.time() * 1000
        record["processing_completed_ms"] = processing_end_ms
        record["total_processing_duration_ms"] = (
            processing_end_ms - record["processing_started_ms"]
        )

        thread_id = record["thread_id"]

        with self.lock:
            # Move from active to completed
            if record["frame_id"] in self.active_records:
                del self.active_records[record["frame_id"]]
            self.completed_records.append(record)

            # Track when this thread finished
            self.thread_last_completion[thread_id] = processing_end_ms

        if self.global_config.get("enable_profiling", False):
            self._printFrameReport(record)

    def _printFrameReport(self, record: AsyncFrameProfilingRecord) -> None:
        frame_id = record["frame_id"]
        thread_id = record["thread_id"]
        queue_wait = record["queue_wait_duration_ms"]
        total_time = record["total_processing_duration_ms"]
        segments = record["segments_found_count"]
        classifications = record["classification_calls_count"]

        contention_info = ""
        if record["delayed_by_previous_frame"]:
            busy_time = record["thread_was_busy_ms"] or 0
            contention_info = f" [DELAYED: thread busy {busy_time:.1f}ms ago]"

        segmentation_info = ""
        if record["segmentation_duration_ms"] is not None:
            segmentation_info = f", seg: {record['segmentation_duration_ms']:.1f}ms"

        classification_info = ""
        if record["classification_calls_count"] > 0:
            avg_classification = (
                record["classification_total_duration_ms"]
                / record["classification_calls_count"]
            )
            classification_info = f", cls: {record['classification_total_duration_ms']:.1f}ms ({classifications} calls, {avg_classification:.1f}ms avg)"

        self.global_config["logger"].info(
            f"Frame {frame_id} [{thread_id}]: queue {queue_wait:.1f}ms → process {total_time:.1f}ms "
            f"({segments} segments{segmentation_info}{classification_info}){contention_info}"
        )

    def getAggregateStats(self, last_n_frames: int = 10) -> Dict[str, Any]:
        with self.lock:
            recent_records = list(self.completed_records)[-last_n_frames:]

        if not recent_records:
            return {}

        total_frames = len(recent_records)

        # Calculate averages
        avg_queue_wait = (
            sum(r["queue_wait_duration_ms"] for r in recent_records) / total_frames
        )
        avg_processing_time = (
            sum(r["total_processing_duration_ms"] for r in recent_records)
            / total_frames
        )
        avg_segments = (
            sum(r["segments_found_count"] for r in recent_records) / total_frames
        )

        # Calculate throughput
        time_span_ms = (
            recent_records[-1]["processing_completed_ms"]
            - recent_records[0]["submitted_to_queue_ms"]
        )
        frames_per_second = (
            (total_frames / time_span_ms) * 1000 if time_span_ms > 0 else 0
        )

        # Count delayed frames
        delayed_frames = sum(
            1 for r in recent_records if r["delayed_by_previous_frame"]
        )
        contention_rate = delayed_frames / total_frames

        # Active threads
        active_threads = set(r["thread_id"] for r in recent_records)

        return {
            "frames_analyzed": total_frames,
            "avg_queue_wait_ms": avg_queue_wait,
            "avg_processing_time_ms": avg_processing_time,
            "avg_segments_per_frame": avg_segments,
            "frames_per_second": frames_per_second,
            "contention_rate": contention_rate,
            "delayed_frames": delayed_frames,
            "active_threads": len(active_threads),
            "thread_names": list(active_threads),
        }

    def printAggregateReport(self, last_n_frames: int = 10) -> None:
        stats = self.getAggregateStats(last_n_frames)

        if not stats:
            self.global_config["logger"].info("No profiling data available yet")
            return

        self.global_config["logger"].info(
            f"\n=== Async Profiling Report (last {stats['frames_analyzed']} frames) ==="
        )
        self.global_config["logger"].info(
            f"Throughput: {stats['frames_per_second']:.1f} FPS"
        )
        self.global_config["logger"].info(
            f"Avg queue wait: {stats['avg_queue_wait_ms']:.1f}ms"
        )
        self.global_config["logger"].info(
            f"Avg processing: {stats['avg_processing_time_ms']:.1f}ms"
        )
        self.global_config["logger"].info(
            f"Avg segments/frame: {stats['avg_segments_per_frame']:.1f}"
        )
        self.global_config["logger"].info(
            f"Thread contention: {stats['contention_rate']:.1%} ({stats['delayed_frames']}/{stats['frames_analyzed']} frames)"
        )
        self.global_config["logger"].info(
            f"Active threads: {stats['active_threads']} ({', '.join(stats['thread_names'])})"
        )
        self.global_config["logger"].info("=" * 50)


# Global instance
_profiling_aggregator: Optional[AsyncProfilingAggregator] = None


def initializeAsyncProfiling(global_config: GlobalConfig) -> None:
    global _profiling_aggregator
    _profiling_aggregator = AsyncProfilingAggregator(global_config)


def createFrameProfilingRecord() -> Optional[AsyncFrameProfilingRecord]:
    if _profiling_aggregator is None:
        return None
    return _profiling_aggregator.createFrameRecord()


def startFrameProcessing(record: Optional[AsyncFrameProfilingRecord]) -> None:
    if _profiling_aggregator is None or record is None:
        return
    _profiling_aggregator.startFrameProcessing(record)


def completeFrameProcessing(record: Optional[AsyncFrameProfilingRecord]) -> None:
    if _profiling_aggregator is None or record is None:
        return
    _profiling_aggregator.completeFrameProcessing(record)


def printAggregateProfilingReport(last_n_frames: int = 10) -> None:
    if _profiling_aggregator is None:
        return
    _profiling_aggregator.printAggregateReport(last_n_frames)


def getProfilingStats(last_n_frames: int = 10) -> Dict[str, Any]:
    if _profiling_aggregator is None:
        return {}
    return _profiling_aggregator.getAggregateStats(last_n_frames)


def saveProfilingResults(
    global_config: GlobalConfig, profiler: cProfile.Profile
) -> None:
    global_config["logger"].info("Saving profiling results...")

    profiles_dir = global_config["profiling_dir_path"]
    os.makedirs(profiles_dir, exist_ok=True)

    profile_file = os.path.join(profiles_dir, f"profile_{global_config['run_id']}.prof")
    profiler.dump_stats(profile_file)

    # Log top time-consuming functions
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 functions

    global_config["logger"].info(f"Profiling results saved to {profile_file}")
    global_config["logger"].info("Top time-consuming functions:")
    for line in s.getvalue().split("\n")[:25]:  # Log first 25 lines
        if line.strip():
            global_config["logger"].info(line)
