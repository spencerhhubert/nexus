import { writable } from 'svelte/store';
import type { SystemStatus } from '../types';

interface ControlsPageState {
  isOnline: boolean;
  isLoading: boolean;
  status: SystemStatus | null;
  cameraFrame: string | null;
  wsConnected: boolean;
}

const initialState: ControlsPageState = {
  isOnline: false,
  isLoading: true,
  status: null,
  cameraFrame: null,
  wsConnected: false,
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
    reset: () =>
      update(state => ({
        ...state,
        isOnline: false,
        status: null,
        cameraFrame: null,
      })),
  };
}

export const controlsPageState = createControlsPageStateStore();
