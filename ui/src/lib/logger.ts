import { config } from './stores/config';
import { get } from 'svelte/store';

export class DebugLogger {
  private getDebugLevel(): number {
    return get(config).debugLevel;
  }

  log(level: number, ...args: any[]): void {
    if (this.getDebugLevel() >= level) {
      console.log(...args);
    }
  }

  info(level: number, ...args: any[]): void {
    if (this.getDebugLevel() >= level) {
      console.info(...args);
    }
  }

  warn(level: number, ...args: any[]): void {
    if (this.getDebugLevel() >= level) {
      console.warn(...args);
    }
  }

  error(level: number, ...args: any[]): void {
    if (this.getDebugLevel() >= level) {
      console.error(...args);
    }
  }
}

export const logger = new DebugLogger();
