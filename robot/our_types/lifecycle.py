from enum import Enum


class SystemLifecycleStage(Enum):
    INITIALIZING = "initializing"
    STARTING_HARDWARE = "starting_hardware"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    SHUTDOWN = "shutdown"
