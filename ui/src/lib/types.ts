export type SystemLifecycleStage =
  | 'initializing'
  | 'starting_hardware'
  | 'paused_by_user'
  | 'paused_by_system'
  | 'running'
  | 'stopping'
  | 'shutdown';

export type SortingState =
  | 'getting_new_object'
  | 'waiting_for_object_to_center'
  | 'trying_to_classify'
  | 'sending_item_to_bin';

export interface MotorInfo {
  motor_id: string;
  display_name: string;
  current_speed: number;
  min_speed: number;
  max_speed: number;
}

export interface SystemStatus {
  lifecycle_stage: SystemLifecycleStage;
  sorting_state: SortingState;
  objects_in_frame: number;
  conveyor_speed: number | null;
  average_speed_1s: number | null;
  average_speed_5s: number | null;
  motors: MotorInfo[];
}

export interface SetMotorSpeedRequest {
  motor_id: string;
  speed: number;
}

export interface StartSystemRequest {}

export interface StopSystemRequest {}

export interface CameraFrameEvent {
  type: 'camera_frame';
  frame_data: string;
}

export interface StatusUpdateEvent {
  type: 'status_update';
  status: SystemStatus;
}

export interface ObservationData {
  observation_id: string;
  trajectory_id: string | null;
  created_at: number;
  captured_at_ms: number;
  center_x_percent: number;
  center_y_percent: number;
  bbox_width_percent: number;
  bbox_height_percent: number;
  leading_edge_x_percent: number;
  center_x_px: number;
  center_y_px: number;
  bbox_width_px: number;
  bbox_height_px: number;
  leading_edge_x_px: number;
  full_image_path: string | null;
  masked_image_path: string | null;
  classification_file_path: string | null;
  classification_result: Record<string, any>;
}

export interface ObservationDataForWeb extends ObservationData {
  masked_image: string;
}

export interface TrajectoryData {
  trajectory_id: string;
  created_at: number;
  updated_at: number;
  observation_ids: string[];
  consensus_classification: string | null;
  lifecycle_stage: string;
  target_bin: Record<string, any> | null;
}

export interface NewObservationEvent {
  type: 'new_observation';
  observation: ObservationDataForWeb;
}

export interface TrajectoriesUpdateEvent {
  type: 'trajectories_update';
  trajectories: TrajectoryData[];
}

export interface BricklinkPartData {
  no: string;
  name: string;
  type: string;
  category_id: number;
  alternate_no: string;
  image_url: string;
  thumbnail_url: string;
  weight: string;
  dim_x: string;
  dim_y: string;
  dim_z: string;
  year_released: number;
  description: string;
  is_obsolete: boolean;
}

export type WebSocketEvent =
  | CameraFrameEvent
  | StatusUpdateEvent
  | NewObservationEvent
  | TrajectoriesUpdateEvent;
