// 配置管理工具
import { AppConfig, Environment } from '../types';

// 默认配置
const defaultConfig: Partial<AppConfig> = {
  app: {
    name: 'TradeGuard',
    version: '1.0.0',
    environment: 'development',
    debug: true
  },
  server: {
    port: 3000,
    host: 'localhost'
  },
  database: {
    type: 'sqlite',
    filename: 'tradeguard.db'
  },
  redis: {
    host: 'localhost',
    port: 6379,
    db: 0,
    keyPrefix: 'tradeguard:'
  },
  zeromq: {
    trader: { pub_port: 5555, rep_port: 5556 },
    risk: { pub_port: 5557, rep_port: 5558 },
    finance: { pub_port: 5559, rep_port: 5560 },
    master_control: { pub_port: 5561, rep_port: 5562 }
  }
};

// 环境特定配置
const environmentConfigs: Record<Environment, Partial<AppConfig>> = {
  development: {
    app: {
      name: 'TradeGuard',
      version: '1.0.0',
      environment: 'development',
      debug: true
    },
    server: {
      port: 3001,
      host: 'localhost'
    },
    database: {
      type: 'sqlite',
      filename: 'dev.db'
    },
    redis: {
      host: 'localhost',
      port: 6379,
      db: 0,
      keyPrefix: 'tradeguard:dev:'
    },
    zeromq: {
      trader: { pub_port: 15555, rep_port: 15556 },
      risk: { pub_port: 15557, rep_port: 15558 },
      finance: { pub_port: 15559, rep_port: 15560 },
      master_control: { pub_port: 15561, rep_port: 15562 }
    }
  },
  staging: {
    app: {
      name: 'TradeGuard',
      version: '1.0.0',
      environment: 'staging',
      debug: false
    },
    server: {
      port: 3002,
      host: 'localhost'
    },
    database: {
      type: 'sqlite',
      filename: 'staging.db'
    },
    redis: {
      host: 'localhost',
      port: 6379,
      db: 2,
      keyPrefix: 'tradeguard:staging:'
    },
    zeromq: {
      trader: { pub_port: 35555, rep_port: 35556 },
      risk: { pub_port: 35557, rep_port: 35558 },
      finance: { pub_port: 35559, rep_port: 35560 },
      master_control: { pub_port: 35561, rep_port: 35562 }
    }
  },
  production: {
    app: {
      name: 'TradeGuard',
      version: '1.0.0',
      environment: 'production',
      debug: false
    },
    server: {
      port: 3000,
      host: '0.0.0.0'
    },
    database: {
      type: 'sqlite',
      filename: 'prod.db'
    },
    redis: {
      host: 'localhost',
      port: 6379,
      db: 1,
      keyPrefix: 'tradeguard:prod:'
    },
    zeromq: {
      trader: { pub_port: 25555, rep_port: 25556 },
      risk: { pub_port: 25557, rep_port: 25558 },
      finance: { pub_port: 25559, rep_port: 25560 },
      master_control: { pub_port: 25561, rep_port: 25562 }
    }
  }
};

/**
 * 获取当前环境
 */
export function getCurrentEnvironment(): Environment {
  const env = process.env.APP_ENV || process.env.NODE_ENV || 'development';
  if (env === 'production' || env === 'staging' || env === 'development') {
    return env as Environment;
  }
  return 'development';
}

/**
 * 深度合并对象
 */
function deepMerge(target: Record<string, unknown>, source: Record<string, unknown>): Record<string, unknown> {
  const result = { ...target };
  
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = deepMerge(
        (target[key] as Record<string, unknown>) || {}, 
        source[key] as Record<string, unknown>
      );
    } else {
      result[key] = source[key];
    }
  }
  
  return result;
}

/**
 * 加载配置
 */
export function loadConfig(): AppConfig {
  const environment = getCurrentEnvironment();
  const envConfig = environmentConfigs[environment] || {};
  
  // 合并默认配置和环境特定配置
  const config = deepMerge(defaultConfig, envConfig) as unknown as AppConfig;
  
  // 从环境变量中覆盖配置
  if (process.env.PORT) {
    config.server.port = parseInt(process.env.PORT, 10);
  }
  
  if (process.env.REDIS_HOST) {
    config.redis.host = process.env.REDIS_HOST;
  }
  
  if (process.env.REDIS_PORT) {
    config.redis.port = parseInt(process.env.REDIS_PORT, 10);
  }
  
  if (process.env.DATABASE_URL) {
    // 解析数据库URL
    const dbUrl = process.env.DATABASE_URL;
    if (dbUrl.startsWith('sqlite:')) {
      config.database.filename = dbUrl.replace('sqlite:', '');
    }
  }
  
  if (process.env.ZMQ_BASE_PORT) {
    const basePort = parseInt(process.env.ZMQ_BASE_PORT, 10);
    config.zeromq = {
      trader: { pub_port: basePort, rep_port: basePort + 1 },
      risk: { pub_port: basePort + 2, rep_port: basePort + 3 },
      finance: { pub_port: basePort + 4, rep_port: basePort + 5 },
      master_control: { pub_port: basePort + 6, rep_port: basePort + 7 }
    };
  }
  
  return config;
}

/**
 * 验证配置
 */
export function validateConfig(config: AppConfig): boolean {
  try {
    // 验证必需的配置项
    if (!config.app?.name || !config.app?.version) {
      throw new Error('App name and version are required');
    }
    
    if (!config.server?.port || config.server.port < 1 || config.server.port > 65535) {
      throw new Error('Valid server port is required');
    }
    
    if (!config.database?.filename) {
      throw new Error('Database filename is required');
    }
    
    if (!config.redis?.host || !config.redis?.port) {
      throw new Error('Redis host and port are required');
    }
    
    // 验证ZeroMQ端口配置
    const zmqPorts = Object.values(config.zeromq).flatMap(module => 
      [module.pub_port, module.rep_port]
    );
    
    const uniquePorts = new Set(zmqPorts);
    if (uniquePorts.size !== zmqPorts.length) {
      throw new Error('ZeroMQ ports must be unique');
    }
    
    return true;
  } catch (error) {
    console.error('Configuration validation failed:', error);
    return false;
  }
}

/**
 * 获取配置实例（单例）
 */
let configInstance: AppConfig | null = null;

export function getConfig(): AppConfig {
  if (!configInstance) {
    configInstance = loadConfig();
    
    if (!validateConfig(configInstance)) {
      throw new Error('Invalid configuration');
    }
    
    console.log(`Configuration loaded for environment: ${configInstance.app.environment}`);
  }
  
  return configInstance;
}

/**
 * 重新加载配置
 */
export function reloadConfig(): AppConfig {
  configInstance = null;
  return getConfig();
}

/**
 * 检查是否为开发环境
 */
export function isDevelopment(): boolean {
  return getCurrentEnvironment() === 'development';
}

/**
 * 检查是否为生产环境
 */
export function isProduction(): boolean {
  return getCurrentEnvironment() === 'production';
}

/**
 * 检查是否为staging环境
 */
export function isStaging(): boolean {
  return getCurrentEnvironment() === 'staging';
}