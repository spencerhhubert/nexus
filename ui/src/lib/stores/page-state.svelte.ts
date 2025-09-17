import { setContext, getContext } from 'svelte';

interface CameraFrame {
  camera: 'main_camera' | 'feeder_camera';
  data: string; // base64 encoded image
  timestamp: number;
}

interface PageState {
  // System status
  lifecycleStage: string;
  loading: boolean;

  // Camera feeds
  mainCameraFrame: CameraFrame | null;
  feederCameraFrame: CameraFrame | null;

  // WebSocket connection
  wsConnected: boolean;
  wsError: string | null;
}

class PageStateStore {
  state = $state<PageState>({
    lifecycleStage: 'unknown',
    loading: false,
    mainCameraFrame: null,
    feederCameraFrame: null,
    wsConnected: false,
    wsError: null,
  });

  private ws: WebSocket | null = null;

  constructor() {
    this.connectWebSocket();
  }

  private connectWebSocket() {
    try {
      this.ws = new WebSocket('ws://localhost:8000/ws');

      this.ws.onopen = () => {
        this.state.wsConnected = true;
        this.state.wsError = null;
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
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        this.state.wsConnected = false;
        setTimeout(() => this.connectWebSocket(), 3000);
      };

      this.ws.onerror = error => {
        this.state.wsError = 'WebSocket connection error';
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      this.state.wsError = 'Failed to create WebSocket connection';
      console.error('WebSocket creation error:', error);
    }
  }

  updateLifecycleStage(stage: string) {
    this.state.lifecycleStage = stage;
  }

  setLoading(loading: boolean) {
    this.state.loading = loading;
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
