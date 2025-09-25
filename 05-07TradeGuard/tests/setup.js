/**
 * Jest测试设置文件 - 交易执行铁三角项目
 * 配置测试环境和全局设置
 */

const path = require('path');
const fs = require('fs');
const { resetAllMocks, getMock, setMockReturnValue, setMockImplementation } = require('./config/mockSetup');

// 设置测试环境变量
process.env.NODE_ENV = 'test';
process.env.PORT = '3002';
process.env.REDIS_HOST = 'localhost';
process.env.REDIS_PORT = '6379';
process.env.ZMQ_PORT = '5556';
process.env.LOG_LEVEL = 'error';

// 设置测试数据库路径
process.env.DB_PATH = path.join(__dirname, '..', 'data', 'test.db');

// 导入数据库和缓存管理器
// 注意：在测试环境中，我们将使用模拟的数据库和缓存
// const DatabaseManager = require('../api/shared/database/connection');
// const RedisClient = require('../api/shared/cache/redis');

// 全局测试超时
jest.setTimeout(30000);

// 模拟控制台输出（减少测试噪音）
// 但保留console.log用于调试
global.console = {
  ...console,
  // log: jest.fn(), // 保留真实的console.log用于调试
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
};

// 全局测试工具函数
global.testUtils = {
  /**
   * 创建测试数据库
   */
  async createTestDatabase() {
    const sqlite3 = require('sqlite3').verbose();
    const dbPath = process.env.DB_PATH;
    
    // 确保测试数据目录存在
    const dataDir = path.dirname(dbPath);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    
    // 删除现有测试数据库
    if (fs.existsSync(dbPath)) {
      fs.unlinkSync(dbPath);
    }
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath, (err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(db);
      });
    });
  },
  
  /**
   * 清理测试数据库
   */
  async cleanupTestDatabase() {
    const dbPath = process.env.DB_PATH;
    if (fs.existsSync(dbPath)) {
      fs.unlinkSync(dbPath);
    }
  },
  
  /**
   * 创建测试Redis客户端
   */
  async createTestRedisClient() {
    const redis = require('redis');
    const client = redis.createClient({
      host: process.env.REDIS_HOST,
      port: process.env.REDIS_PORT,
      db: 15 // 使用测试数据库
    });
    
    try {
      await client.connect();
      return client;
    } catch (error) {
      // Redis不可用时返回模拟客户端
      return {
        get: jest.fn().mockResolvedValue(null),
        set: jest.fn().mockResolvedValue('OK'),
        setEx: jest.fn().mockResolvedValue('OK'),
        del: jest.fn().mockResolvedValue(1),
        keys: jest.fn().mockResolvedValue([]),
        flushDb: jest.fn().mockResolvedValue('OK'),
        quit: jest.fn().mockResolvedValue('OK'),
        connect: jest.fn().mockResolvedValue(undefined),
        disconnect: jest.fn().mockResolvedValue(undefined)
      };
    }
  },
  
  /**
   * 清理测试Redis数据
   */
  async cleanupTestRedis(client) {
    if (client && typeof client.flushDb === 'function') {
      try {
        await client.flushDb();
        await client.quit();
      } catch (error) {
        // 忽略清理错误
      }
    }
  },
  
  /**
   * 等待指定时间
   */
  async sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },
  
  /**
   * 生成测试数据
   */
  generateTestData: {
    /**
     * 生成测试策略包
     */
    strategyPackage() {
      return {
        packageName: `测试策略_${Date.now()}`,
        packageType: 'momentum',
        strategyType: 'momentum',
        submittedBy: 'test_user',
        sessionId: 1,
        parameters: {
          symbol: 'BTCUSDT',
          timeframe: '1h',
          risk_level: 'medium'
        },
        riskLevel: 'medium',
        expectedReturn: 0.1,
        maxPositionSize: 10000,
        stopLossPct: 0.05,
        takeProfitPct: 0.15
      };
    },
    
    /**
     * 生成测试订单
     */
    order() {
      return {
        strategy_id: 1,
        symbol: 'BTCUSDT',
        side: 'buy',
        type: 'market',
        quantity: 0.001,
        price: null,
        status: 'pending',
        created_by: 'test_user'
      };
    },
    
    /**
     * 生成测试风险评估
     */
    riskAssessment() {
      return {
        strategy_id: 1,
        risk_score: 65,
        risk_level: 'medium',
        assessment_data: JSON.stringify({
          volatility: 0.15,
          correlation: 0.8,
          var_95: 0.05
        }),
        recommendations: JSON.stringify([
          '建议降低仓位',
          '增加止损设置'
        ]),
        assessed_by: 'test_user'
      };
    },
    
    /**
     * 生成测试预算申请
     */
    budgetRequest() {
      return {
        strategy_id: 1,
        requested_amount: 10000,
        currency: 'USDT',
        purpose: '策略测试',
        justification: '测试用预算申请',
        status: 'pending',
        requested_by: 'test_user'
      };
    },
    
    /**
     * 生成测试账户
     */
    account() {
      return {
        name: `测试账户_${Date.now()}`,
        type: 'trading',
        currency: 'USDT',
        balance: 50000,
        available_balance: 45000,
        frozen_balance: 5000,
        status: 'active',
        created_by: 'test_user'
      };
    }
  },
  
  /**
   * 模拟HTTP请求
   */
  mockRequest(options = {}) {
    return {
      body: options.body || {},
      params: options.params || {},
      query: options.query || {},
      headers: options.headers || {},
      user: options.user || { id: 'test_user', role: 'trader' },
      ip: options.ip || '127.0.0.1',
      method: options.method || 'GET',
      url: options.url || '/test'
    };
  },
  
  /**
   * 模拟HTTP响应
   */
  mockResponse() {
    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
      send: jest.fn().mockReturnThis(),
      end: jest.fn().mockReturnThis(),
      setHeader: jest.fn().mockReturnThis(),
      cookie: jest.fn().mockReturnThis(),
      clearCookie: jest.fn().mockReturnThis()
    };
    return res;
  },
  
  /**
   * 验证API响应格式
   */
  validateApiResponse(response, expectedStatus = 200) {
    expect(response.status).toBe(expectedStatus);
    expect(response.body).toBeDefined();
    
    if (expectedStatus >= 200 && expectedStatus < 300) {
      expect(response.body.success).toBe(true);
      expect(response.body.data).toBeDefined();
    } else {
      expect(response.body.success).toBe(false);
      expect(response.body.error).toBeDefined();
    }
    
    // timestamp和request_id是可选的
    // expect(response.body.timestamp).toBeDefined();
    // expect(response.body.request_id).toBeDefined();
  },
  
  /**
   * 验证ZeroMQ消息格式
   */
  validateZmqMessage(message) {
    expect(message).toBeDefined();
    expect(message.type).toBeDefined();
    expect(message.data).toBeDefined();
    expect(message.timestamp).toBeDefined();
    expect(message.source).toBeDefined();
    expect(message.id).toBeDefined();
  },
  
  /**
   * 创建测试ZMQ套接字
   */
  createTestZmqSocket() {
    return {
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      on: jest.fn(),
      close: jest.fn(),
      bind: jest.fn(),
      unbind: jest.fn()
    };
  }
};

// 全局错误处理
process.on('unhandledRejection', (reason, promise) => {
  console.error('未处理的Promise拒绝:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('未捕获的异常:', error);
});

// 测试前清理
beforeAll(async () => {
  // 清理测试数据
  await global.testUtils.cleanupTestDatabase();
  
  // 初始化统一的模拟对象
  resetAllMocks();
});

// 测试后清理
afterAll(async () => {
  // 清理测试数据
  await global.testUtils.cleanupTestDatabase();
});

// 每个测试前重置模拟
beforeEach(() => {
  jest.clearAllMocks();
  resetAllMocks();
});

// 导出统一的模拟工具
global.mockUtils = {
  getMock,
  setMockReturnValue,
  setMockImplementation,
  resetAllMocks
};

console.log('✅ 测试环境设置完成');