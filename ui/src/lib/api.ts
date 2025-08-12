import type {
  SystemStatus,
  SetMotorSpeedRequest,
  StartSystemRequest,
  StopSystemRequest,
  WebSocketEvent,
} from './types';

const API_BASE = 'http://localhost:8080';
const WS_BASE = 'ws://localhost:8080/api';

class RobotAPI {
  private ws: WebSocket | null = null;
  private reconnectInterval: number | null = null;
  private eventHandlers: Map<string, (data: any) => void> = new Map();

  async setMotorSpeed(request: SetMotorSpeedRequest): Promise<void> {
    const response = await fetch(`${API_BASE}/api/motors/set_speed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  async startSystem(): Promise<void> {
    const response = await fetch(`${API_BASE}/api/system/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  async stopSystem(): Promise<void> {
    const response = await fetch(`${API_BASE}/api/system/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  connectWebSocket(): void {
    console.log(
      'connectWebSocket() called, current ws state:',
      this.ws?.readyState
    );
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already open, skipping connection');
      return;
    }

    const wsUrl = `${WS_BASE}/ws`;
    console.log('Attempting to connect WebSocket to:', wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected successfully');
      if (this.reconnectInterval) {
        console.log('Clearing reconnect interval');
        clearInterval(this.reconnectInterval);
        this.reconnectInterval = null;
      }
    };

    this.ws.onmessage = event => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        console.log('WebSocket message received:', data.type);
        const handler = this.eventHandlers.get(data.type);
        if (handler) {
          handler(data);
        } else {
          console.warn('No handler for WebSocket event type:', data.type);
        }
      } catch (e) {
        console.error(
          'Failed to parse WebSocket message:',
          e,
          'Raw data:',
          event.data
        );
      }
    };

    this.ws.onclose = event => {
      console.log(
        'WebSocket disconnected. Code:',
        event.code,
        'Reason:',
        event.reason,
        'Clean:',
        event.wasClean
      );
      this.scheduleReconnect();
    };

    this.ws.onerror = error => {
      console.error('WebSocket error:', error);
      console.log('WebSocket state when error occurred:', this.ws?.readyState);
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectInterval) return;

    this.reconnectInterval = setInterval(() => {
      console.log('Attempting WebSocket reconnect...');
      this.connectWebSocket();
    }, 3000);
  }

  on(eventType: string, handler: (data: any) => void): void {
    this.eventHandlers.set(eventType, handler);
  }

  disconnect(): void {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.eventHandlers.clear();
  }

  async isOnline(): Promise<boolean> {
    try {
      console.log('Checking if robot is online...');
      const response = await fetch(`${API_BASE}/api/system/start`, {
        method: 'HEAD',
      });
      console.log('Robot is online, response status:', response.status);
      return true;
    } catch (e) {
      console.log('Robot appears offline:', e);
      return false;
    }
  }
}

export const robotAPI = new RobotAPI();
