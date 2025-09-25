/**
 * 测试配置加载器
 * 为所有测试提供统一的配置管理
 */

const path = require('path');
const fs = require('fs');
const yaml = require('js-yaml');

/**
 * 测试配置类
 */
class TestConfig {
  constructor() {
    this.config = null;
    this.loadConfig();
  }

  /**
   * 加载测试配置
   */
  loadConfig() {
    try {
      // 加载基础配置
      const baseConfigPath = path.join(__dirname, '../../config/base.yaml');
      const baseConfig = yaml.load(fs.readFileSync(baseConfigPath, 'utf8'));
      
      // 加载测试专用配置
      const testConfigPath = path.join(__dirname, '../../config/test.yaml');
      const testConfig = yaml.load(fs.readFileSync(testConfigPath, 'utf8'));
      
      // 合并配置（测试配置覆盖基础配置）
      this.config = this.mergeDeep(baseConfig, testConfig);
      
      // 设置环境变量
      this.setEnvironmentVariables();
      
    } catch (error) {
      console.error('加载测试配置失败:', error);
      throw error;
    }
  }

  /**
   * 深度合并对象
   */
  mergeDeep(target, source) {
    const result = { ...target };
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.mergeDeep(result[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }
    
    return result;
  }

  /**
   * 设置环境变量
   */
  setEnvironmentVariables() {
    // 基础环境变量
    process.env.NODE_ENV = 'test';
    process.env.APP_ENV = 'test';
    
    // 数据库配置
    process.env.DB_PATH = this.config.database.path;
    
    // Redis配置
    process.env.REDIS_HOST = this.config.redis.host;
    process.env.REDIS_PORT = this.config.redis.port.toString();
    process.env.REDIS_DB = this.config.redis.db.toString();
    
    // ZMQ配置
    process.env.ZMQ_PUB_PORT = this.config.zeromq.publisher.port.toString();
    process.env.ZMQ_REQ_PORT = this.config.zeromq.request.port.toString();
    
    // API配置
    process.env.PORT = this.config.test.ports.api.toString();
    
    // 日志配置
    process.env.LOG_LEVEL = this.config.logging.level;
  }

  /**
   * 获取配置值
   */
  get(path, defaultValue = null) {
    const keys = path.split('.');
    let current = this.config;
    
    for (const key of keys) {
      if (current && typeof current === 'object' && key in current) {
        current = current[key];
      } else {
        return defaultValue;
      }
    }
    
    return current;
  }

  /**
   * 获取完整配置
   */
  getAll() {
    return this.config;
  }

  /**
   * 获取风控配置
   */
  getRiskConfig() {
    return this.config.risk;
  }

  /**
   * 获取财务配置
   */
  getFinanceConfig() {
    return this.config.finance;
  }

  /**
   * 获取交易员配置
   */
  getTraderConfig() {
    return this.config.trader;
  }

  /**
   * 获取交易配置
   */
  getTradingConfig() {
    return this.config.trading;
  }

  /**
   * 获取数据库配置
   */
  getDatabaseConfig() {
    return this.config.database;
  }

  /**
   * 获取Redis配置
   */
  getRedisConfig() {
    return this.config.redis;
  }

  /**
   * 获取ZMQ配置
   */
  getZmqConfig() {
    return this.config.zeromq;
  }

  /**
   * 获取测试专用配置
   */
  getTestConfig() {
    return this.config.test;
  }

  /**
   * 检查是否为测试环境
   */
  isTestEnvironment() {
    return this.config.app.environment === 'test';
  }

  /**
   * 获取风险阈值
   */
  getRiskThresholds() {
    return this.config.risk.thresholds;
  }

  /**
   * 获取财务限制配置
   */
  getFinanceLimits() {
    return this.config.finance.riskBasedLimits;
  }

  /**
   * 获取预算配置
   */
  getBudgetConfig() {
    return this.config.finance.budget;
  }

  /**
   * 获取审批工作流配置
   */
  getApprovalWorkflowConfig() {
    return this.config.finance.approvalWorkflow;
  }

  /**
   * 生成测试用的策略数据
   */
  generateTestStrategy(options = {}) {
    // 如果传入的是字符串，则作为风险等级处理
    const riskLevel = typeof options === 'string' ? options : (options.riskLevel || 'low');
    
    const baseStrategy = {
      id: Math.floor(Math.random() * 1000) + 1,
      package_name: `测试策略_${riskLevel}_${Date.now()}`,
      strategy_type: riskLevel === 'high' ? 'arbitrage' : 'momentum',
      risk_level: riskLevel,
      status: 'active',
      created_by: 'test_user',
      expected_return: riskLevel === 'high' ? 0.15 : (riskLevel === 'medium' ? 0.08 : 0.05)
    };

    // 根据风险等级设置不同的参数
    let strategyData;
    switch (riskLevel) {
      case 'low':
        strategyData = {
          ...baseStrategy,
          max_position_size: 10000,
          parameters: JSON.stringify({
            symbol: 'BTCUSDT',
            timeframe: '1h',
            volatility_threshold: 0.05
          })
        };
        break;
      case 'medium':
        strategyData = {
          ...baseStrategy,
          max_position_size: 50000,
          parameters: JSON.stringify({
            symbol: 'ETHUSDT',
            timeframe: '30m',
            volatility_threshold: 0.15
          })
        };
        break;
      case 'high':
        strategyData = {
          ...baseStrategy,
          max_position_size: 100000,
          parameters: JSON.stringify({
            symbol: 'ALTCOIN/USDT',
            timeframe: '5m',
            leverage: 3,
            volatility_threshold: 0.35
          })
        };
        break;
      default:
        strategyData = baseStrategy;
    }
    
    // 如果传入的是对象，则合并覆盖属性
    if (typeof options === 'object' && options !== null) {
      return { ...strategyData, ...options };
    }
    
    return strategyData;
  }

  /**
   * 生成测试用的风险指标数据
   */
  generateTestRiskMetrics(riskLevel = 'low') {
    switch (riskLevel) {
      case 'low':
        return {
          utilizationRatio: 0.25,
          unrealizedPnL: 500,
          maxSinglePosition: 5000,
          orderSuccessRate: 0.95,
          totalExposure: 25000,
          availableBalance: 75000
        };
      case 'medium':
        return {
          utilizationRatio: 0.55,
          unrealizedPnL: -1500,
          maxSinglePosition: 25000,
          orderSuccessRate: 0.85,
          totalExposure: 55000,
          availableBalance: 45000
        };
      case 'high':
        return {
          utilizationRatio: 0.75,  // 0.8分 * 0.15权重 = 12分
          unrealizedPnL: -15000,   // 适中回撤确保drawdown评分约0.75 (11.25分)
          maxSinglePosition: 100000,
          orderSuccessRate: 0.75,  // 0.25分 * 0.10权重 = 2.5分
          totalExposure: 75000,
          availableBalance: 25000
        };
      case 'critical':
        return {
          utilizationRatio: 0.99,   // 接近100%利用率
          unrealizedPnL: -500000,  // 极大亏损确保最高drawdown评分
          maxSinglePosition: 1000000,
          orderSuccessRate: 0.01,  // 极低成功率(1%)
          totalExposure: 990000,
          availableBalance: 10000
        };
      default:
        return this.generateTestRiskMetrics('low');
    }
  }

  /**
   * 生成测试用的账户数据
   */
  generateTestAccount(overrides = {}) {
    const defaults = {
      id: 1,
      account_name: 'Test Trading Account',
      account_type: 'trading',
      balance: 1000000,
      available_balance: 800000,
      frozen_balance: 200000,
      currency: 'USD',
      status: 'active',
      created_at: new Date('2024-01-01').toISOString(),
      updated_at: new Date().toISOString()
    };
    return { ...defaults, ...overrides };
  }

  /**
   * 生成测试用的预算申请数据
   */
  generateTestBudgetRequest(overrides = {}) {
    return {
      id: 1,
      strategy_id: 1,
      requested_amount: 50000,
      request_type: 'initial',
      priority: 'normal',
      status: 'pending',
      requested_by: 'strategy_manager',
      justification: 'Test budget request',
      created_at: new Date().toISOString(),
      ...overrides
    };
  }

  /**
   * 生成测试用的订单数据
   */
  generateTestOrder(overrides = {}) {
    const defaults = {
      id: 1,
      strategy_id: 1,
      symbol: 'BTCUSDT',
      order_type: 'market',
      side: 'buy',
      quantity: 0.001,
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    return { ...defaults, ...overrides };
  }
}

// 创建单例实例
const testConfig = new TestConfig();

// 导出配置实例和工厂函数
module.exports = {
  testConfig,
  TestConfig,
  
  // 便捷访问函数
  getConfig: (path, defaultValue) => testConfig.get(path, defaultValue),
  getRiskConfig: () => testConfig.getRiskConfig(),
  getFinanceConfig: () => testConfig.getFinanceConfig(),
  getTraderConfig: () => testConfig.getTraderConfig(),
  getTradingConfig: () => testConfig.getTradingConfig(),
  getDatabaseConfig: () => testConfig.getDatabaseConfig(),
  getRedisConfig: () => testConfig.getRedisConfig(),
  getZmqConfig: () => testConfig.getZmqConfig(),
  getTestConfig: () => testConfig.getTestConfig(),
  
  // 测试数据生成函数
  generateTestStrategy: (riskLevel) => testConfig.generateTestStrategy(riskLevel),
  generateTestRiskMetrics: (riskLevel) => testConfig.generateTestRiskMetrics(riskLevel),
  generateTestAccount: (overrides) => testConfig.generateTestAccount(overrides),
  generateTestOrder: (overrides) => testConfig.generateTestOrder(overrides),
  generateTestBudgetRequest: (overrides) => testConfig.generateTestBudgetRequest(overrides)
};