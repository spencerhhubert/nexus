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
  frame_id?: string;
}

export interface StatusUpdateEvent {
  type: 'status_update';
  status: SystemStatus;
}

export interface ObservationEvent {
  type: 'observation';
  observation: any;
}

export interface TrajectoryEvent {
  type: 'trajectory';
  trajectory: any;
}

export type WebSocketEvent =
  | CameraFrameEvent
  | StatusUpdateEvent
  | ObservationEvent
  | TrajectoryEvent;
