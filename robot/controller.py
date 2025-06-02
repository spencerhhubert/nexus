import time
import numpy as np
import uuid
from typing import List, Optional, Dict, Any
from enum import Enum
from robot.global_config import GlobalConfig
from robot.irl.config import IRLSystemInterface, DistributionModuleConfig
from robot.ai import segmentFrame, classifySegment
from robot.storage.sqlite3.migrations import initializeDatabase
from robot.storage.sqlite3.operations import saveObservationToDatabase
from robot.storage.blob import saveBlobImage, ensureBlobStorageExists
from robot.trajectories import Observation, ObjectTrajectory, createObservation, createTrajectory, findMatchingTrajectory, TrajectoryLifecycleStage
from robot.sorting import Category, SortingProfile
from robot.bin_state_tracker import BinStateTracker, BinCoordinates, BinState
from robot.door_scheduler import DoorScheduler
from robot.conveyor_speed_tracker import estimateConveyorSpeed


class SystemLifecycleStage(Enum):
    INITIALIZING = "initializing"
    STARTING_HARDWARE = "starting_hardware"
    RUNNING = "running"
    STOPPING = "stopping"
    SHUTDOWN = "shutdown"


class SortingController:
    def __init__(self, global_config: GlobalConfig, irl_system: IRLSystemInterface, 
                 distribution_module_configs: List[DistributionModuleConfig]):
        self.global_config = global_config
        self.irl_system = irl_system
        self.distribution_module_configs = distribution_module_configs
        self.lifecycle_stage = SystemLifecycleStage.INITIALIZING
        

        self.sorting_profile: Optional[SortingProfile] = None
        self.bin_state_tracker: Optional[BinStateTracker] = None
        self.door_scheduler: Optional[DoorScheduler] = None
        
        self.active_trajectories: List[ObjectTrajectory] = []
        self.completed_trajectories: List[ObjectTrajectory] = []

    def initialize(self) -> None:
        self.global_config['logger'].info("Initializing sorting controller...")
        
        ensureBlobStorageExists(self.global_config)
        initializeDatabase(self.global_config)
        

        
        default_category = Category(self.global_config, "default", "Default Category")
        self.sorting_profile = SortingProfile(self.global_config, "hardcoded_profile", {})
        
        available_bins = self._buildAvailableBinCoordinates()
        self.bin_state_tracker = BinStateTracker(self.global_config, available_bins, self.sorting_profile)
        self.door_scheduler = DoorScheduler(self.global_config)
        
        self.lifecycle_stage = SystemLifecycleStage.STARTING_HARDWARE

    def _buildAvailableBinCoordinates(self) -> List[BinCoordinates]:
        available_bins = []
        sorted_configs = sorted(self.distribution_module_configs, key=lambda x: x['distance_from_camera'])
        
        for dm_idx, config in enumerate(sorted_configs):
            for bin_idx in range(config['num_bins']):
                available_bins.append({
                    'distribution_module_idx': dm_idx,
                    'bin_idx': bin_idx
                })
        
        return available_bins

    def startHardware(self) -> None:
        self.global_config['logger'].info("Starting hardware systems...")
        
        self.irl_system['main_conveyor_dc_motor'].setSpeed(50)
        self.irl_system['feeder_conveyor_dc_motor'].setSpeed(100)
        self.irl_system['vibration_hopper_dc_motor'].setSpeed(65)
        
        self.lifecycle_stage = SystemLifecycleStage.RUNNING

    def run(self) -> None:
        self.global_config['logger'].info("Starting main control loop...")
        
        while self.lifecycle_stage == SystemLifecycleStage.RUNNING:
            try:
                self._processFrame()
                self._processTriggerActions()
                self._cleanupCompletedTrajectories()
                
                time.sleep(self.global_config['capture_delay_ms'] / 1000.0)
                
            except KeyboardInterrupt:
                self.global_config['logger'].info("Interrupt received, stopping...")
                self.lifecycle_stage = SystemLifecycleStage.STOPPING
                break
            except Exception as e:
                self.global_config['logger'].error(f"Error in main loop: {e}")

    def _processFrame(self) -> None:
        frame = self.irl_system['main_camera'].captureFrame()
        if frame is None:
            return
        
        segments = segmentFrame(frame, self.global_config)
        
        for segment in segments:
            masked_image = self._maskSegment(frame, segment)
            if masked_image is None:
                continue
                
            classification_result = self._classifySegment(masked_image)
            
            center_x, center_y, bbox_width, bbox_height = self._calculateNormalizedBounds(frame, segment)
            
            observation = self._assignToTrajectory(center_x, center_y, bbox_width, bbox_height, classification_result)
            
            self._saveObservationData(frame, masked_image, observation)

    def _maskSegment(self, full_frame: np.ndarray, segment) -> Optional[np.ndarray]:
        y_min, y_max, x_min, x_max = segment.bbox
        
        if y_min >= y_max or x_min >= x_max:
            return None
        
        y_min = max(0, y_min)
        y_max = min(full_frame.shape[0] - 1, y_max)
        x_min = max(0, x_min)
        x_max = min(full_frame.shape[1] - 1, x_max)
        
        cropped_image = full_frame[y_min:y_max+1, x_min:x_max+1]
        
        mask_np = segment.mask.cpu().numpy()
        cropped_mask = mask_np[y_min:y_max+1, x_min:x_max+1]
        masked_image = cropped_image.copy()
        masked_image[~cropped_mask] = 0
        
        return masked_image
    
    def _classifySegment(self, masked_image: np.ndarray) -> Dict[str, Any]:
        return classifySegment(masked_image, self.global_config)
    
    def _calculateNormalizedBounds(self, full_frame: np.ndarray, segment) -> tuple[float, float, float, float]:
        y_min, y_max, x_min, x_max = segment.bbox
        
        center_x = (x_min + x_max) / 2.0 / full_frame.shape[1]
        center_y = (y_min + y_max) / 2.0 / full_frame.shape[0]
        bbox_width = (x_max - x_min) / full_frame.shape[1]
        bbox_height = (y_max - y_min) / full_frame.shape[0]
        
        return center_x, center_y, bbox_width, bbox_height
    
    def _assignToTrajectory(self, center_x: float, center_y: float, bbox_width: float, 
                           bbox_height: float, classification_result: Dict[str, Any]) -> Observation:
        matching_trajectory = findMatchingTrajectory(self.global_config, 
                                                   self._createTempObservation(center_x, center_y, bbox_width, bbox_height, classification_result),
                                                   self.active_trajectories)
        
        if matching_trajectory is None:
            observation = createObservation(self.global_config, None, center_x, center_y, 
                                          bbox_width, bbox_height, "", "", classification_result)
            new_trajectory = createTrajectory(self.global_config, observation)
            self.active_trajectories.append(new_trajectory)
            return observation
        else:
            observation = createObservation(self.global_config, matching_trajectory.trajectory_id, 
                                          center_x, center_y, bbox_width, bbox_height, 
                                          "", "", classification_result)
            matching_trajectory.addObservation(observation)
            return observation
    
    def _saveObservationData(self, full_frame: np.ndarray, masked_image: np.ndarray, observation: Observation) -> None:
        full_image_path = saveBlobImage(self.global_config, full_frame, "full")
        masked_image_path = saveBlobImage(self.global_config, masked_image, "masked")
        
        observation['full_image_path'] = full_image_path
        observation['masked_image_path'] = masked_image_path
        
        assert observation['observation_id'] is not None, "Observation must have ID before saving"
        assert observation['trajectory_id'] is not None, "Observation must have trajectory ID before saving"
        
        saveObservationToDatabase(self.global_config, observation['observation_id'], observation['trajectory_id'],
                                 observation['timestamp_ms'], observation['center_x'], observation['center_y'],
                                 observation['bbox_width'], observation['bbox_height'], observation['full_image_path'],
                                 observation['masked_image_path'], observation['classification_result'])

    def _createTempObservation(self, center_x: float, center_y: float, bbox_width: float, 
                              bbox_height: float, classification_result: Dict[str, Any]) -> Observation:
        timestamp_ms = int(time.time() * 1000)
        return Observation(
            observation_id=None,
            trajectory_id=None, 
            timestamp_ms=timestamp_ms,
            center_x=center_x,
            center_y=center_y,
            bbox_width=bbox_width,
            bbox_height=bbox_height,
            full_image_path="",
            masked_image_path="",
            classification_result=classification_result
        )

    def _processTriggerActions(self) -> None:
        for trajectory in self.active_trajectories:
            if trajectory.lifecycle_stage != TrajectoryLifecycleStage.UNDER_CAMERA:
                continue
                
            if trajectory.shouldTriggerAction(self.global_config):
                item_id = trajectory.getConsensusClassification()
                target_bin = self._getTargetBin(item_id)
                
                if target_bin and self.door_scheduler is not None and self.bin_state_tracker is not None:
                    delay_ms = self._calculateDoorDelay(trajectory, target_bin)
                    self.door_scheduler.scheduleDoorAction(target_bin, delay_ms)
                    self.bin_state_tracker.reserveBin(target_bin, "default")
                    trajectory.lifecycle_stage = TrajectoryLifecycleStage.IN_TRANSIT
                    
                    self.global_config['logger'].info(f"Scheduled action for trajectory {trajectory.trajectory_id} -> bin {target_bin} with delay {delay_ms}ms")

    def _calculateDoorDelay(self, trajectory: ObjectTrajectory, target_bin: BinCoordinates) -> int:
        conveyor_speed = estimateConveyorSpeed(self.active_trajectories, self.completed_trajectories)
        if conveyor_speed is None:
            return 1000
        
        # Calculate distance from current position to target bin
        # For now, use a simple estimate based on distribution module distance
        if target_bin['distribution_module_idx'] < len(self.distribution_module_configs):
            target_distance = self.distribution_module_configs[target_bin['distribution_module_idx']]['distance_from_camera']
            travel_time_ms = int((target_distance / conveyor_speed) * 1000) if conveyor_speed > 0 else 1000
            return max(0, travel_time_ms)
        
        return 1000

    def _getTargetBin(self, item_id: str) -> Optional[BinCoordinates]:
        if self.bin_state_tracker is None:
            return None
        return self.bin_state_tracker.findAvailableBin("default")



    def _cleanupCompletedTrajectories(self) -> None:
        completed = [t for t in self.active_trajectories 
                    if t.lifecycle_stage == TrajectoryLifecycleStage.DOORS_CLOSED]
        
        self.completed_trajectories.extend(completed)
        
        # Keep only recent completed trajectories for speed estimation
        max_completed = 50
        if len(self.completed_trajectories) > max_completed:
            self.completed_trajectories = self.completed_trajectories[-max_completed:]
        
        self.active_trajectories = [t for t in self.active_trajectories 
                                   if t.lifecycle_stage != TrajectoryLifecycleStage.DOORS_CLOSED]

    def stop(self) -> None:
        self.global_config['logger'].info("Stopping sorting controller...")
        self.lifecycle_stage = SystemLifecycleStage.STOPPING
        
        self.irl_system['main_conveyor_dc_motor'].setSpeed(0)
        self.irl_system['feeder_conveyor_dc_motor'].setSpeed(0)
        self.irl_system['vibration_hopper_dc_motor'].setSpeed(0)
        
        self.irl_system['arduino'].flush()
        self.irl_system['arduino'].close()
        self.irl_system['main_camera'].release()
        
        self.lifecycle_stage = SystemLifecycleStage.SHUTDOWN


def createSortingController(global_config: GlobalConfig, irl_system: IRLSystemInterface,
                           distribution_module_configs: List[DistributionModuleConfig]) -> SortingController:
    return SortingController(global_config, irl_system, distribution_module_configs)