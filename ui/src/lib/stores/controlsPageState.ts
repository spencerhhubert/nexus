import { writable } from 'svelte/store';
import type { SystemStatus, ObservationData, TrajectoryData } from '../types';
import { globalConfig } from '../config/global';

interface ControlsPageState {
  isOnline: boolean;
  isLoading: boolean;
  status: SystemStatus | null;
  cameraFrame: string | null;
  wsConnected: boolean;
  observations: ObservationData[];
  trajectories: TrajectoryData[];
}

const initialState: ControlsPageState = {
  isOnline: false,
  isLoading: true,
  status: null,
  cameraFrame: null,
  wsConnected: false,
  observations: [],
  trajectories: [],
};

function createControlsPageStateStore() {
  const { subscribe, update, set } = writable<ControlsPageState>(initialState);

  return {
    subscribe,
    set,
    update,
    setOnline: (online: boolean) =>
      update(state => ({ ...state, isOnline: online })),
    setLoading: (loading: boolean) =>
      update(state => ({ ...state, isLoading: loading })),
    setStatus: (status: SystemStatus | null) =>
      update(state => ({ ...state, status })),
    setCameraFrame: (frame: string | null) =>
      update(state => ({ ...state, cameraFrame: frame })),
    setWsConnected: (connected: boolean) =>
      update(state => ({ ...state, wsConnected: connected })),
    addObservation: (observation: ObservationData) =>
      update(state => {
        const config = globalConfig.get();
        const currentTime = Date.now();
        const cutoffTime = currentTime - config.observations.maxAgeMs;

        const filteredObservations = state.observations.filter(
          obs => obs.captured_at_ms >= cutoffTime
        );

        const updatedObservations = [...filteredObservations, observation];
        if (updatedObservations.length > config.observations.maxCount) {
          updatedObservations.splice(
            0,
            updatedObservations.length - config.observations.maxCount
          );
        }

        return { ...state, observations: updatedObservations };
      }),
    setTrajectories: (trajectories: TrajectoryData[]) =>
      update(state => {
        const config = globalConfig.get();
        const currentTime = Date.now();
        const cutoffTime = currentTime - config.trajectories.maxAgeMs;

        const filteredTrajectories = trajectories.filter(
          traj => traj.updated_at >= cutoffTime
        );

        if (filteredTrajectories.length > config.trajectories.maxCount) {
          filteredTrajectories.splice(
            0,
            filteredTrajectories.length - config.trajectories.maxCount
          );
        }

        return { ...state, trajectories: filteredTrajectories };
      }),
    reset: () =>
      update(state => ({
        ...state,
        isOnline: false,
        status: null,
        cameraFrame: null,
        observations: [],
        trajectories: [],
      })),
  };
}

export const controlsPageState = createControlsPageStateStore();
