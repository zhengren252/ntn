import { readFileSync } from 'fs';
import { join } from 'path';
import * as yaml from 'yaml';

/**
 * 环境配置接口
 */
export interface EnvironmentConfig {
  app: {
    name: string;
    version: string;
    environment: string;
    port: number;
    host: string;
    debug: boolean;
    logLevel: string;
  };
  database: {
    path: string;
    options: {
      verbose: boolean;
      readonly: boolean;
      fileMustExist: boolean;
    };
    backup: {
      enabled: boolean;
      interval: number;
      path: string;
      retention?: number;
    };
  };
  redis: {
    host: string;
    port: number;
    password: string | null;
    db: number;
    keyPrefix: string;
    ttl: {
      default: number;
      session: number;
      realtime: number;
      cache: number;
    };
    connectionPool: {
      min: number;
      max: number;
    };
  };
  zeromq: {
    publisher: {
      port: number;
      bind: string;
    };
    subscriber: {
      endpoints: string[];
    };
    request: {
      port: number;
      bind: string;
      timeout: number;
    };
    reply: {
      endpoints: string[];
      timeout: number;
    };
    heartbeat: {
      interval: number;
      timeout: number;
    };
  };
  security: {
    jwt: {
      secret: string;
      expiresIn: string;
      issuer: string;
    };
    bcrypt: {
      saltRounds: number;
    };
    cors: {
      origin: string[];
      credentials: boolean;
    };
    rateLimit: {
      windowMs: number;
      max: number;
    };
  };
  trading: {
    maxPositionSize: number;
    maxOrderSize: number;
    defaultStopLoss: number;
    defaultTakeProfit: number;
    maxDailyLoss: number;
    maxDrawdown: number;
    riskFreeRate: number;
  };
  risk: {
    var: {
      confidenceLevel: number;
      timeHorizon: number;
      historicalDays: number;
    };
    limits: {
      maxPositionConcentration: number;
      maxSectorExposure: number;
      maxLeverage: number;
    };
    alerts: {
      enabled: boolean;
      thresholds: {
        low: number;
        medium: number;
        high: number;
        critical: number;
      };
    };
  };
  finance: {
    baseCurrency: string;
    initialCapital: number;
    minCashReserve: number;
    maxAllocationPerStrategy: number;
    budgetApproval: {
      autoApproveLimit: number;
      requiresApproval: number;
    };
    commission: {
      rate: number;
      minimum: number;
    };
  };
  monitoring: {
    metrics: {
      enabled: boolean;
      interval: number;
      retention: number;
    };
    alerts: {
      email: {
        enabled: boolean;
      };
      webhook: {
        enabled: boolean;
        url?: string;
      };
    };
    healthCheck: {
      interval: number;
      timeout: number;
    };
  };
  logging: {
    level: string;
    format: string;
    file: {
      enabled: boolean;
      path: string;
      maxSize: string;
      maxFiles: number;
    };
    console: {
      enabled: boolean;
      colorize?: boolean;
    };
  };
  api: {
    prefix: string;
    timeout: number;
    maxRequestSize: string;
    documentation: {
      enabled: boolean;
      path: string;
    };
    versioning: {
      enabled: boolean;
      header: string;
    };
  };
}

/**
 * 配置管理类
 */
class ConfigurationManager {
  private static instance: ConfigurationManager;
  private config: EnvironmentConfig;
  private environment: string;

  private constructor() {
    this.environment = this.getCurrentEnvironment();
    this.config = this.loadConfiguration();
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): ConfigurationManager {
    if (!ConfigurationManager.instance) {
      ConfigurationManager.instance = new ConfigurationManager();
    }
    return ConfigurationManager.instance;
  }

  /**
   * 获取当前环境
   */
  private getCurrentEnvironment(): string {
    return process.env.NODE_ENV || process.env.APP_ENV || 'development';
  }

  /**
   * 加载配置文件
   */
  private loadConfiguration(): EnvironmentConfig {
    try {
      // 首先加载基础配置
      const baseConfigPath = join(process.cwd(), 'config', 'base.yaml');
      let baseConfig: Record<string, unknown> = {};
      
      try {
        const baseConfigFile = readFileSync(baseConfigPath, 'utf8');
        baseConfig = yaml.parse(baseConfigFile) as Record<string, unknown>;
      } catch {
        console.warn(`基础配置文件 ${baseConfigPath} 加载失败`);
      }

      // 加载环境特定配置
      const envConfigPath = join(process.cwd(), 'config', `${this.environment}.yaml`);
      let envConfig: Record<string, unknown> = {};
      
      try {
        const envConfigFile = readFileSync(envConfigPath, 'utf8');
        envConfig = yaml.parse(envConfigFile) as Record<string, unknown>;
      } catch {
        console.warn(`环境配置文件 ${envConfigPath} 加载失败，使用基础配置`);
      }

      // 合并配置，环境配置覆盖基础配置
      const mergedConfig = this.deepMerge(baseConfig, envConfig);
      
      // 处理环境变量替换
      const processedConfig = this.processEnvironmentVariables(mergedConfig);
      
      return processedConfig as unknown as EnvironmentConfig;
    } catch (error) {
      console.error('配置加载失败:', error);
      throw new Error('无法加载系统配置');
    }
  }

  /**
   * 深度合并对象
   */
  private deepMerge(target: Record<string, unknown>, source: Record<string, unknown>): Record<string, unknown> {
    const result = { ...target };
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(
          (result[key] as Record<string, unknown>) || {}, 
          source[key] as Record<string, unknown>
        );
      } else {
        result[key] = source[key];
      }
    }
    
    return result;
  }

  /**
   * 处理环境变量替换
   */
  private processEnvironmentVariables(config: Record<string, unknown>): Record<string, unknown> {
    const processValue = (value: unknown): unknown => {
      if (typeof value === 'string' && value.startsWith('${') && value.endsWith('}')) {
        const envVar = value.slice(2, -1);
        const envValue = process.env[envVar];
        if (envValue === undefined) {
          console.warn(`环境变量 ${envVar} 未设置`);
          return value;
        }
        return envValue;
      } else if (typeof value === 'object' && value !== null) {
        const result: Record<string, unknown> = Array.isArray(value) ? [] as any : {};
        for (const key in (value as Record<string, unknown>)) {
          result[key] = processValue((value as Record<string, unknown>)[key]);
        }
        return result;
      }
      return value;
    };
    
    return processValue(config) as Record<string, unknown>;
  }

  /**
   * 获取完整配置
   */
  public getConfig(): EnvironmentConfig {
    return this.config;
  }

  /**
   * 获取特定配置项
   */
  public get<T = unknown>(path: string): T {
    const keys = path.split('.');
    let current: unknown = this.config;
    
    for (const key of keys) {
      if (current && typeof current === 'object' && key in (current as Record<string, unknown>)) {
        current = (current as Record<string, unknown>)[key];
      } else {
        return undefined as T;
      }
    }
    
    return current as T;
  }

  /**
   * 获取当前环境名称
   */
  public getEnvironment(): string {
    return this.environment;
  }

  /**
   * 检查是否为开发环境
   */
  public isDevelopment(): boolean {
    return this.environment === 'development';
  }

  /**
   * 检查是否为预发布环境
   */
  public isStaging(): boolean {
    return this.environment === 'staging';
  }

  /**
   * 检查是否为生产环境
   */
  public isProduction(): boolean {
    return this.environment === 'production';
  }

  /**
   * 重新加载配置
   */
  public reload(): void {
    this.config = this.loadConfiguration();
  }

  /**
   * 验证配置完整性
   */
  public validateConfig(): boolean {
    try {
      const requiredPaths = [
        'app.name',
        'app.port',
        'database.path',
        'redis.host',
        'redis.port',
        'security.jwt.secret'
      ];
      
      for (const path of requiredPaths) {
        const value = this.get(path);
        if (value === undefined || value === null) {
          console.error(`必需的配置项 ${path} 缺失`);
          return false;
        }
      }
      
      return true;
    } catch (error) {
      console.error('配置验证失败:', error);
      return false;
    }
  }
}

// 导出配置管理器实例
export const configManager = ConfigurationManager.getInstance();

// 导出配置对象（向后兼容）
export const config = configManager.getConfig();

// 导出环境检查函数
export const isDevelopment = () => configManager.isDevelopment();
export const isStaging = () => configManager.isStaging();
export const isProduction = () => configManager.isProduction();
export const getEnvironment = () => configManager.getEnvironment();

// 在模块加载时验证配置
if (!configManager.validateConfig()) {
  console.error('配置验证失败，系统可能无法正常运行');
}

console.log(`配置管理器已初始化，当前环境: ${configManager.getEnvironment()}`);