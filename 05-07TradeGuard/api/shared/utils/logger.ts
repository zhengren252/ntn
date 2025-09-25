import * as fs from 'fs';
import * as path from 'path';

// 日志级别枚举
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

// 日志配置接口
interface LoggerConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableFile: boolean;
  logDir: string;
  maxFileSize: number; // MB
  maxFiles: number;
}

// 默认配置
const defaultConfig: LoggerConfig = {
  level: process.env.NODE_ENV === 'production' ? LogLevel.INFO : LogLevel.DEBUG,
  enableConsole: true,
  enableFile: true,
  logDir: path.join(process.cwd(), 'logs'),
  maxFileSize: 10, // 10MB
  maxFiles: 5
};

/**
 * 日志记录器类
 */
class Logger {
  private config: LoggerConfig;
  private logStream: fs.WriteStream | null = null;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
    this.initializeFileLogging();
  }

  /**
   * 初始化文件日志
   */
  private initializeFileLogging(): void {
    if (!this.config.enableFile) return;

    try {
      // 确保日志目录存在
      if (!fs.existsSync(this.config.logDir)) {
        fs.mkdirSync(this.config.logDir, { recursive: true });
      }

      // 创建日志文件流
      const logFile = path.join(this.config.logDir, `app-${new Date().toISOString().split('T')[0]}.log`);
      this.logStream = fs.createWriteStream(logFile, { flags: 'a' });
    } catch (error) {
      console.error('Failed to initialize file logging:', error);
    }
  }

  /**
   * 格式化日志消息
   */
  private formatMessage(level: string, message: string, meta?: Record<string, unknown>): string {
    const timestamp = new Date().toISOString();
    const metaStr = meta ? ` ${JSON.stringify(meta)}` : '';
    return `[${timestamp}] [${level}] ${message}${metaStr}`;
  }

  /**
   * 写入日志
   */
  private writeLog(level: LogLevel, levelName: string, message: string, meta?: Record<string, unknown>): void {
    if (level < this.config.level) return;

    const formattedMessage = this.formatMessage(levelName, message, meta);

    // 控制台输出
    if (this.config.enableConsole) {
      switch (level) {
        case LogLevel.DEBUG:
          console.debug(formattedMessage);
          break;
        case LogLevel.INFO:
          console.info(formattedMessage);
          break;
        case LogLevel.WARN:
          console.warn(formattedMessage);
          break;
        case LogLevel.ERROR:
          console.error(formattedMessage);
          break;
      }
    }

    // 文件输出
    if (this.config.enableFile && this.logStream) {
      this.logStream.write(formattedMessage + '\n');
    }
  }

  /**
   * DEBUG级别日志
   */
  debug(message: string, meta?: Record<string, unknown>): void {
    this.writeLog(LogLevel.DEBUG, 'DEBUG', message, meta);
  }

  /**
   * INFO级别日志
   */
  info(message: string, meta?: Record<string, unknown>): void {
    this.writeLog(LogLevel.INFO, 'INFO', message, meta);
  }

  /**
   * WARN级别日志
   */
  warn(message: string, meta?: Record<string, unknown>): void {
    this.writeLog(LogLevel.WARN, 'WARN', message, meta);
  }

  /**
   * ERROR级别日志
   */
  error(message: string, meta?: Record<string, unknown>): void {
    this.writeLog(LogLevel.ERROR, 'ERROR', message, meta);
  }

  /**
   * 关闭日志流
   */
  close(): void {
    if (this.logStream) {
      this.logStream.end();
      this.logStream = null;
    }
  }
}

// 导出默认日志实例
export const logger = new Logger();

// 导出Logger类供自定义使用
export { Logger };

// 进程退出时关闭日志流
process.on('exit', () => {
  logger.close();
});

process.on('SIGINT', () => {
  logger.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  logger.close();
  process.exit(0);
});