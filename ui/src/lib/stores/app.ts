import { writable, derived } from 'svelte/store';
import type { SystemStatus } from '$lib/types';

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
  frame_id?: string;
  full_image_path?: string | null;
  masked_image_path?: string | null;
  classification_file_path?: string | null;
  classification_result: any;
  frame_data?: string;
}

export interface TrajectoryData {
  trajectory_id: string;
  created_at: number;
  updated_at: number;
  observation_ids: string[];
  consensus_classification: string | null;
  lifecycle_stage: string;
  target_bin: any | null;
}

interface AppState {
  systemStatus: SystemStatus | null;
  cameraFrame: string | null;
  currentFrameId: string | null;
  observations: ObservationData[];
  trajectories: TrajectoryData[];
  connectionState: {
    isOnline: boolean;
    isLoading: boolean;
    wsConnected: boolean;
  };
}

const initialState: AppState = {
  systemStatus: null,
  cameraFrame: null,
  currentFrameId: null,
  observations: [],
  trajectories: [],
  connectionState: {
    isOnline: false,
    isLoading: true,
    wsConnected: false,
  },
};

export const appStore = writable<AppState>(initialState);

export const systemStatus = derived(appStore, $store => $store.systemStatus);
export const cameraFrame = derived(appStore, $store => $store.cameraFrame);
export const currentFrameId = derived(
  appStore,
  $store => $store.currentFrameId
);
export const observations = derived(appStore, $store => $store.observations);
export const trajectories = derived(appStore, $store => $store.trajectories);
export const connectionState = derived(
  appStore,
  $store => $store.connectionState
);

export const activeTrajectories = derived(trajectories, $trajectories =>
  $trajectories.filter(
    t =>
      t.lifecycle_stage !== 'expired' && t.lifecycle_stage !== 'probably_in_bin'
  )
);

export const recentTrajectories = derived(trajectories, $trajectories =>
  [...$trajectories].sort((a, b) => b.updated_at - a.updated_at).slice(0, 10)
);

export const observationsForCurrentFrame = derived(
  [observations, currentFrameId],
  ([$observations, $currentFrameId]) =>
    $currentFrameId
      ? $observations.filter(obs => obs.frame_id === $currentFrameId)
      : []
);

export function updateSystemStatus(status: SystemStatus) {
  appStore.update(state => ({
    ...state,
    systemStatus: status,
  }));
}

export function updateCameraFrame(frameData: string, frameId?: string) {
  appStore.update(state => ({
    ...state,
    cameraFrame: frameData,
    currentFrameId: frameId || null,
  }));
}

export function updateConnectionState(
  updates: Partial<typeof initialState.connectionState>
) {
  appStore.update(state => ({
    ...state,
    connectionState: { ...state.connectionState, ...updates },
  }));
}

export function addObservation(observation: ObservationData) {
  appStore.update(state => ({
    ...state,
    observations: [...state.observations, observation],
  }));
}

export function addTrajectory(trajectory: TrajectoryData) {
  appStore.update(state => ({
    ...state,
    trajectories: [...state.trajectories, trajectory],
  }));
}

export function updateTrajectory(
  trajectoryId: string,
  updates: Partial<TrajectoryData>
) {
  appStore.update(state => ({
    ...state,
    trajectories: state.trajectories.map(t =>
      t.trajectory_id === trajectoryId ? { ...t, ...updates } : t
    ),
  }));
}

export function clearObservationsAndTrajectories() {
  appStore.update(state => ({
    ...state,
    observations: [],
    trajectories: [],
  }));
}
