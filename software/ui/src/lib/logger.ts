class Logger {
  log(level: number, ...args: any[]): void {
    console.log(...args);
  }

  info(...args: any[]): void {
    console.info(...args);
  }

  warn(...args: any[]): void {
    console.warn(...args);
  }

  error(level: number, ...args: any[]): void {
    console.error(...args);
  }
}

export const logger = new Logger();
