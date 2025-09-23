export interface MotorStatus {
  speed: number;
}

export interface EncoderStatus {
  current_speed_cm_per_s: number;
  average_speed_1s_cm_per_s: number;
  average_speed_5s_cm_per_s: number;
  position_history_count: number;
}

export interface SystemStatusMessage {
  type: 'system_status';
  lifecycle_stage: string;
  sorting_state: string;
  motors: {
    main_conveyor: MotorStatus;
    feeder_conveyor: MotorStatus;
    first_vibration_hopper: MotorStatus;
    second_vibration_hopper: MotorStatus;
  };
  encoder?: EncoderStatus;
}

export interface CameraFrameMessage {
  type: 'camera_frame';
  camera: 'main_camera' | 'feeder_camera';
  data: string;
}

export interface BinCoordinates {
  distribution_module_idx: number;
  bin_idx: number;
}

export interface KnownObject {
  uuid: string;
  main_camera_id?: string;
  image?: string;
  classification_id?: string;
  bin_coordinates?: BinCoordinates;
}

export interface KnownObjectMessage {
  type: 'known_object_update';
  uuid: string;
  main_camera_id?: string;
  image?: string;
  classification_id?: string;
  bin_coordinates?: BinCoordinates;
}

export type WebSocketMessage =
  | SystemStatusMessage
  | CameraFrameMessage
  | KnownObjectMessage;
