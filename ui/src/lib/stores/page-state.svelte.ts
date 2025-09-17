import { setContext, getContext } from 'svelte';

interface CameraFrame {
  camera: 'main_camera' | 'feeder_camera';
  data: string; // base64 encoded image
  timestamp: number;
}

interface PageState {
  // System status
  lifecycleStage: string;
  sortingState: string;
  motors: {
    main_conveyor: { speed: number };
    feeder_conveyor: { speed: number };
    first_vibration_hopper: { speed: number };
    second_vibration_hopper: { speed: number };
  };

  // Camera feeds
  mainCameraFrame: CameraFrame | null;
  feederCameraFrame: CameraFrame | null;

  // WebSocket connection
  wsConnected: boolean;
  wsError: string | null;
  reconnecting: boolean;
}

class PageStateStore {
  state = $state<PageState>({
    lifecycleStage: 'unknown',
    sortingState: 'unknown',
    motors: {
      main_conveyor: { speed: 0 },
      feeder_conveyor: { speed: 0 },
      first_vibration_hopper: { speed: 0 },
      second_vibration_hopper: { speed: 0 },
    },
    mainCameraFrame: null,
    feederCameraFrame: null,
    wsConnected: false,
    wsError: null,
    reconnecting: false,
  });

  private ws: WebSocket | null = null;

  constructor() {
    this.connectWebSocket();
  }

  private connectWebSocket() {
    this.state.reconnecting = true;

    try {
      this.ws = new WebSocket('ws://localhost:8000/ws');

      this.ws.onopen = () => {
        this.state.wsConnected = true;
        this.state.wsError = null;
        this.state.reconnecting = false;
      };

      this.ws.onmessage = event => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'camera_frame') {
            const frame: CameraFrame = {
              camera: message.camera,
              data: message.data,
              timestamp: Date.now(),
            };

            if (message.camera === 'main_camera') {
              this.state.mainCameraFrame = frame;
            } else if (message.camera === 'feeder_camera') {
              this.state.feederCameraFrame = frame;
            }
          } else if (message.type === 'system_status') {
            this.state.lifecycleStage = message.lifecycle_stage;
            this.state.sortingState = message.sorting_state;
            this.state.motors = message.motors;
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        this.state.wsConnected = false;
        this.state.reconnecting = true;
        setTimeout(() => this.connectWebSocket(), 3000);
      };

      this.ws.onerror = error => {
        this.state.wsError = 'WebSocket connection error';
        this.state.reconnecting = false;
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      this.state.wsError = 'Failed to create WebSocket connection';
      this.state.reconnecting = false;
      console.error('WebSocket creation error:', error);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

const PAGE_STATE_KEY = 'page-state';

export function createPageState() {
  const store = new PageStateStore();
  setContext(PAGE_STATE_KEY, store);
  return store;
}

export function getPageState(): PageStateStore {
  const store = getContext<PageStateStore>(PAGE_STATE_KEY);
  if (!store) {
    throw new Error(
      'Page state not found. Make sure createPageState() is called in a parent component.'
    );
  }
  return store;
}
