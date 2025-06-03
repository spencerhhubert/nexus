from typing import List, Optional
from robot.trajectories import ObjectTrajectory

NUM_TRAJECTORIES_TO_ESTIMATE_WITH = 10
MIN_OBSERVATIONS_TO_ESTIMATE_VELOCITY = 4


def estimateConveyorSpeed(
    active_trajectories: List[ObjectTrajectory],
    completed_trajectories: List[ObjectTrajectory],
) -> Optional[float]:
    all_trajectories = active_trajectories + completed_trajectories

    # Filter trajectories with enough observations
    valid_trajectories = [
        t
        for t in all_trajectories
        if len(t.observations) >= MIN_OBSERVATIONS_TO_ESTIMATE_VELOCITY
    ]

    recent_trajectories = valid_trajectories[-NUM_TRAJECTORIES_TO_ESTIMATE_WITH:]

    if not recent_trajectories:
        return None

    trajectory_speeds = []

    for trajectory in recent_trajectories:
        speed = _calculateTrajectorySpeed(trajectory)
        if speed is not None:
            trajectory_speeds.append(speed)

    if not trajectory_speeds:
        return None

    return sum(trajectory_speeds) / len(trajectory_speeds)


def _calculateTrajectorySpeed(trajectory: ObjectTrajectory) -> Optional[float]:
    if len(trajectory.observations) < 2:
        return None

    total_distance = 0.0
    total_time = 0.0

    for i in range(1, len(trajectory.observations)):
        obs_prev = trajectory.observations[i - 1]
        obs_curr = trajectory.observations[i]

        time_delta = obs_curr["timestamp_ms"] - obs_prev["timestamp_ms"]
        if time_delta <= 0:
            continue

        dx = obs_curr["center_x"] - obs_prev["center_x"]
        dy = obs_curr["center_y"] - obs_prev["center_y"]
        distance = (dx * dx + dy * dy) ** 0.5

        total_distance += distance
        total_time += time_delta

    if total_time <= 0:
        return None

    return total_distance / total_time
