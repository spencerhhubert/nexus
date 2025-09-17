export interface MotorStatus {
  speed: number;
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
}

export interface CameraFrameMessage {
  type: 'camera_frame';
  camera: 'main_camera' | 'feeder_camera';
  data: string;
}

export type WebSocketMessage = SystemStatusMessage | CameraFrameMessage;
