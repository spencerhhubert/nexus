import type {
  SystemStatus,
  SetMotorSpeedRequest,
  StartSystemRequest,
  StopSystemRequest,
  WebSocketEvent,
  NewObservationEvent,
  TrajectoriesUpdateEvent,
  BricklinkPartData,
} from './types';
import { logger } from './logger';

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
    logger.log(
      1,
      'connectWebSocket() called, current ws state:',
      this.ws?.readyState
    );
    if (this.ws?.readyState === WebSocket.OPEN) {
      logger.log(1, 'WebSocket already open, skipping connection');
      return;
    }

    const wsUrl = `${WS_BASE}/ws`;
    logger.log(1, 'Attempting to connect WebSocket to:', wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      logger.log(1, 'WebSocket connected successfully');
      if (this.reconnectInterval) {
        logger.log(1, 'Clearing reconnect interval');
        clearInterval(this.reconnectInterval);
        this.reconnectInterval = null;
      }
      // Notify listeners of connection
      const handler = this.eventHandlers.get('connect');
      if (handler) {
        handler({ type: 'connect' });
      }
    };

    this.ws.onmessage = event => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        logger.log(1, 'WebSocket message received:', data.type);
        const handler = this.eventHandlers.get(data.type);
        if (handler) {
          handler(data);
        } else {
          logger.warn(1, 'No handler for WebSocket event type:', data.type);
        }
      } catch (e) {
        logger.error(
          1,
          'Failed to parse WebSocket message:',
          e,
          'Raw data:',
          event.data
        );
      }
    };

    this.ws.onclose = event => {
      logger.log(
        1,
        'WebSocket disconnected. Code:',
        event.code,
        'Reason:',
        event.reason,
        'Clean:',
        event.wasClean
      );
      // Notify listeners of disconnect
      const handler = this.eventHandlers.get('disconnect');
      if (handler) {
        handler({ type: 'disconnect', code: event.code, reason: event.reason });
      }
      this.scheduleReconnect();
    };

    this.ws.onerror = error => {
      logger.error(1, 'WebSocket error:', error);
      logger.log(
        1,
        'WebSocket state when error occurred:',
        this.ws?.readyState
      );
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectInterval) return;

    this.reconnectInterval = setInterval(() => {
      logger.log(1, 'Attempting WebSocket reconnect...');
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
      logger.log(1, 'Checking if robot is online...');
      const response = await fetch(`${API_BASE}/api/system/start`, {
        method: 'HEAD',
      });
      logger.log(1, 'Robot is online, response status:', response.status);
      return true;
    } catch (e) {
      logger.log(1, 'Robot appears offline:', e);
      return false;
    }
  }

  async getBricklinkPart(kindId: string): Promise<BricklinkPartData | null> {
    try {
      logger.log(1, `Fetching BrickLink part info for: ${kindId}`);
      const response = await fetch(`${API_BASE}/api/bricklink/${kindId}`);

      if (!response.ok) {
        logger.error(
          1,
          `Failed to fetch BrickLink part: ${response.statusText}`
        );
        return null;
      }

      const partData: BricklinkPartData = await response.json();
      logger.log(1, `Successfully fetched BrickLink part: ${partData.name}`);
      return partData;
    } catch (e) {
      logger.error(1, 'Error fetching BrickLink part:', e);
      return null;
    }
  }
}

export const robotAPI = new RobotAPI();
