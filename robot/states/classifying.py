import time
import uuid
from collections import Counter
from typing import Optional, Dict
from robot.states.base_state import BaseState
from robot.our_types.sorting import SortingState
from robot.our_types.known_object import KnownObject
from robot.our_types.classify import ClassificationConsensus
from robot.our_types.observation import BoundingBox
from robot.our_types.bin import BinCoordinates
from robot.ai.classify import classifyPiece
from robot.util.images import cropImageToBbox
from robot.vision_system import SegmentationModelManager
from robot.irl.config import IRLSystemInterface
from robot.websocket_manager import WebSocketManager
from robot.bin_state_tracker import BinStateTracker
from robot.states.shared_variables import SharedVariables
from robot.global_config import GlobalConfig


class Classifying(BaseState):
    def __init__(
        self,
        global_config: GlobalConfig,
        vision_system: SegmentationModelManager,
        websocket_manager: WebSocketManager,
        irl_interface: IRLSystemInterface,
        bin_state_tracker: BinStateTracker,
        shared_variables: SharedVariables,
    ):
        super().__init__(global_config, vision_system, websocket_manager, irl_interface)
        self.bin_state_tracker = bin_state_tracker
        self.shared_variables = shared_variables
        self.logger = global_config["logger"].ctx(state="Classifying")

        self.timeout_start_ts: Optional[float] = None
        self.known_objects: Dict[str, KnownObject] = {}

    def step(self) -> Optional[SortingState]:
        self._setMainConveyorToDefaultSpeed()

        current_time = time.time()

        if self.timeout_start_ts is None:
            self.timeout_start_ts = current_time

            # Set conveyor speed to zero
            if not self.global_config["disable_main_conveyor"]:
                main_conveyor = self.irl_interface["main_conveyor_dc_motor"]
                main_conveyor.setSpeed(0)
                self.logger.info("CLASSIFYING: Set main conveyor speed to zero")

            # Get the centered object ID
            centered_object_id = self.vision_system.getCurrentCenteredObjectId()

            if centered_object_id:
                # Build known object for this track ID
                frames = self.vision_system.getFramesForTrackId(centered_object_id)

                if frames:
                    # Create initial known object and send to frontend
                    object_uuid = str(uuid.uuid4())

                    # Get bounding box from current results for cropping
                    current_results = self.vision_system._getMainCameraResults()
                    cropped_image = None

                    if current_results:
                        for result in current_results:
                            if (
                                result.masks is not None
                                and hasattr(result, "boxes")
                                and result.boxes.id is not None
                            ):
                                for i, mask in enumerate(result.masks):
                                    if i < len(result.boxes.id):
                                        track_id = str(int(result.boxes.id[i].item()))
                                        if track_id == centered_object_id:
                                            bbox_tensor = result.boxes[i].xyxy[0]
                                            bbox = BoundingBox(
                                                x1=int(bbox_tensor[0].item()),
                                                y1=int(bbox_tensor[1].item()),
                                                x2=int(bbox_tensor[2].item()),
                                                y2=int(bbox_tensor[3].item()),
                                            )
                                            cropped_image = cropImageToBbox(
                                                frames[0], bbox
                                            )
                                            break

                    # Send initial known object event
                    self.logger.info(
                        f"WEBSOCKET: Sending initial known object event for UUID {object_uuid}"
                    )
                    self.websocket_manager.broadcastKnownObject(
                        uuid=object_uuid,
                        main_camera_id=centered_object_id,
                        image=cropped_image,
                    )

                    # Take up to 5 frames
                    selected_frames = frames[:5]
                    classification_results = []

                    # Classify each frame
                    for frame in selected_frames:
                        result = classifyPiece([frame], self.global_config)
                        if result:
                            classification_results.append(result)

                    # Calculate consensus
                    if classification_results:
                        id_counts = Counter([r["id"] for r in classification_results])
                        category_counts = Counter(
                            [r["category_id"] for r in classification_results]
                        )

                        most_common_id = (
                            id_counts.most_common(1)[0][0] if id_counts else ""
                        )
                        most_common_category = (
                            category_counts.most_common(1)[0][0]
                            if category_counts
                            else ""
                        )

                        consensus = ClassificationConsensus(
                            id=most_common_id, category_id=most_common_category
                        )

                        # Determine bin coordinates for this classification
                        bin_coordinates = self._determineBinCoordinates(
                            most_common_category
                        )

                        # Create and store known object
                        known_object = KnownObject(
                            uuid=object_uuid,
                            main_camera_id=centered_object_id,
                            observations=[],  # Not needed for this simplified approach
                            classification_consensus=consensus,
                            bin_coordinates=bin_coordinates,
                        )
                        self.known_objects[centered_object_id] = known_object
                        self.shared_variables.pending_known_object = known_object

                        # Send classification update
                        self.logger.info(
                            f"WEBSOCKET: Sending classification update for UUID {object_uuid}: {most_common_id} (category: {most_common_category})"
                        )
                        self.websocket_manager.broadcastKnownObject(
                            uuid=object_uuid,
                            classification_id=most_common_id,
                            bin_coordinates=bin_coordinates,
                        )

                        self.logger.info(f"CLASSIFICATION CONSENSUS: {consensus}")
                    else:
                        self.logger.warning("No valid classification results obtained")
                else:
                    self.logger.warning("No complete frames found for track ID")
            else:
                self.logger.warning("No centered object found for classification")

            # Go to sending object to bin state
            return SortingState.SENDING_OBJECT_TO_BIN

        timeout_duration = self.global_config["classifying_timeout_ms"] / 1000.0
        if current_time - self.timeout_start_ts >= timeout_duration:
            self.logger.info(
                f"TIMEOUT: CLASSIFYING timed out after {timeout_duration}s"
            )
            return SortingState.GETTING_NEW_OBJECT_FROM_FEEDER

        return None

    def cleanup(self) -> None:
        self.timeout_start_ts = None
        self.logger.info("CLEANUP: Cleared CLASSIFYING state")

    def _determineBinCoordinates(self, category_id: str) -> Optional[BinCoordinates]:
        if not category_id:
            return None

        # Use bin state tracker to find available bin for this category
        bin_coordinates = self.bin_state_tracker.findAvailableBin(category_id)
        if bin_coordinates:
            # Reserve the bin for this category
            self.bin_state_tracker.reserveBin(bin_coordinates, category_id)
            self.logger.info(
                f"BINS: Assigned category {category_id} to bin {bin_coordinates}"
            )
            return bin_coordinates
        else:
            self.logger.warning(
                f"BINS: No available bin found for category {category_id}"
            )
            return None
