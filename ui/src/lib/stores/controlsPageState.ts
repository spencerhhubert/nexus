import { writable } from 'svelte/store';
import type {
  SystemStatus,
  ObservationDataForWeb,
  TrajectoryData,
} from '../types';
import { globalConfig } from '../config/global';

interface ControlsPageState {
  isOnline: boolean;
  isLoading: boolean;
  status: SystemStatus | null;
  cameraFrame: string | null;
  wsConnected: boolean;
  observations: ObservationDataForWeb[];
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
    addObservation: (observation: ObservationDataForWeb) =>
      update(state => {
        const config = globalConfig.get();
        const currentTime = Date.now();
        const cutoffTime = currentTime - config.observations.maxAgeMs;

        // Filter by age and remove any existing observation with the same ID
        const filteredObservations = state.observations.filter(
          obs =>
            obs.captured_at_ms >= cutoffTime &&
            obs.observation_id !== observation.observation_id
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

        // Filter new trajectories by age and count
        const newFiltered = trajectories.filter(
          traj => traj.updated_at >= cutoffTime
        );
        
        if (newFiltered.length > config.trajectories.maxCount) {
          newFiltered.splice(0, newFiltered.length - config.trajectories.maxCount);
        }

        // Check if there would be any difference
        if (state.trajectories.length === newFiltered.length) {
          let hasChanges = false;
          
          for (let i = 0; i < state.trajectories.length; i++) {
            const current = state.trajectories[i];
            const incoming = newFiltered.find(t => t.trajectory_id === current.trajectory_id);
            
            if (!incoming || 
                current.updated_at !== incoming.updated_at ||
                current.lifecycle_stage !== incoming.lifecycle_stage ||
                current.consensus_classification !== incoming.consensus_classification ||
                current.observation_ids.length !== incoming.observation_ids.length) {
              hasChanges = true;
              break;
            }
          }
          
          if (!hasChanges) {
            return state; // No changes, don't update
          }
        }

        return { ...state, trajectories: newFiltered };
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
