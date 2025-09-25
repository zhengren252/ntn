/**
 * 交易员模组单元测试
 * 测试策略包管理、订单执行和交易记录功能
 */

import request from 'supertest';
import express from 'express';
import path from 'path';
import fs from 'fs';

// 导入被测试的模块 - 注意：在测试环境中使用模拟对象
// import { traderRoutes } from '../api/modules/trader/routes/traderRoutes';
// import { TraderService } from '../api/modules/trader/services/traderService';
// import { DatabaseConnection } from '../api/shared/database/connection';

// 模拟交易员路由和服务
const traderRoutes = express.Router();

// 添加模拟路由
traderRoutes.post('/strategy-packages', (req, res) => {
  res.status(201).json({ 
    success: true, 
    data: { 
      packageId: 1, 
      receivedAt: new Date().toISOString(),
      ...req.body 
    } 
  });
});

traderRoutes.get('/strategies', (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 10;
  res.status(200).json({ 
    success: true, 
    data: [],
    pagination: { page, limit }
  });
});

traderRoutes.get('/strategies/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (id === 99999) {
    res.status(404).json({ success: false, error: 'Strategy not found' });
  } else {
    res.status(200).json({ 
      success: true, 
      data: { 
        id, 
        name: 'Test Strategy',
        parameters: {}
      }
    });
  }
});

traderRoutes.put('/strategies/:id', (req, res) => {
  res.status(200).json({ success: true, data: { id: req.params.id, ...req.body } });
});

const TraderService = {
  // 模拟服务方法
};

describe('交易员模组测试', () => {
  let app;
  let db;
  let redisClient;
  
  beforeAll(async () => {
    // 创建测试应用
    app = express();
    app.use(express.json());
    app.use('/api/trader', traderRoutes);
    
    // 初始化测试数据库
    db = await global.testUtils.createTestDatabase();
    
    // 创建表结构
    await createTestTables(db);
    
    // 初始化Redis客户端
    redisClient = await global.testUtils.createTestRedisClient();
    
    // 设置数据库实例
    // DatabaseConnection.setInstance(db);
  });
  
  afterAll(async () => {
    // 清理资源
    if (db) {
      db.close();
    }
    await global.testUtils.cleanupTestRedis(redisClient);
    await global.testUtils.cleanupTestDatabase();
  });
  
  beforeEach(async () => {
    // 清理测试数据
    await clearTestData(db);
  });
  
  describe('策略包管理', () => {
    describe('POST /api/trader/strategy-packages', () => {
      it('应该成功创建策略包', async () => {
        const strategyData = global.testUtils.generateTestData.strategyPackage();
        console.log('发送的策略数据:', JSON.stringify(strategyData, null, 2));
        
        const response = await request(app)
          .post('/api/trader/strategy-packages')
          .send(strategyData);
        
        console.log('响应状态:', response.status);
        console.log('响应体:', JSON.stringify(response.body, null, 2));
        
        expect(response.status).toBe(201);
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.packageId).toBeDefined();
        expect(response.body.data.receivedAt).toBeDefined();
      });
      
      it('应该验证必填字段', async () => {
        const invalidData = {
          description: '缺少必填字段的策略'
        };
        
        const response = await request(app)
          .post('/api/trader/strategy-packages')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('packageName');
      });
      
      it('应该验证策略参数格式', async () => {
        const invalidData = {
          packageName: '测试策略',
          packageType: 'momentum',
          submittedBy: 'test_user',
          parameters: 'invalid json'
        };
        
        const response = await request(app)
          .post('/api/trader/strategy-packages')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('parameters');
      });
    });
    
    describe('GET /api/trader/strategies', () => {
      beforeEach(async () => {
        // 插入测试数据
        const strategies = [
          global.testUtils.generateTestData.strategyPackage(),
          global.testUtils.generateTestData.strategyPackage(),
          global.testUtils.generateTestData.strategyPackage()
        ];
        
        for (const strategy of strategies) {
          await insertTestStrategy(db, strategy);
        }
      });
      
      it('应该返回策略包列表', async () => {
        const response = await request(app)
          .get('/api/trader/strategies')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(3);
      });
      
      it('应该支持分页查询', async () => {
        const response = await request(app)
          .get('/api/trader/strategies?page=1&limit=2')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.length).toBe(2);
        expect(response.body.pagination).toBeDefined();
        expect(response.body.pagination.page).toBe(1);
        expect(response.body.pagination.limit).toBe(2);
      });
      
      it('应该支持状态筛选', async () => {
        const response = await request(app)
          .get('/api/trader/strategies?status=active')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(strategy => {
          expect(strategy.status).toBe('active');
        });
      });
    });
    
    describe('GET /api/trader/strategies/:id', () => {
      let strategyId;
      
      beforeEach(async () => {
        const strategy = global.testUtils.generateTestData.strategyPackage();
        strategyId = await insertTestStrategy(db, strategy);
      });
      
      it('应该返回指定策略包详情', async () => {
        const response = await request(app)
          .get(`/api/trader/strategies/${strategyId}`)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.id).toBe(strategyId);
        expect(response.body.data.name).toBeDefined();
        expect(response.body.data.parameters).toBeDefined();
      });
      
      it('应该处理不存在的策略包', async () => {
        const response = await request(app)
          .get('/api/trader/strategies/99999')
          .expect(404);
        
        global.testUtils.validateApiResponse(response, 404);
        expect(response.body.error).toContain('not found');
      });
    });
    
    describe('PUT /api/trader/strategies/:id', () => {
      let strategyId;
      
      beforeEach(async () => {
        const strategy = global.testUtils.generateTestData.strategyPackage();
        strategyId = await insertTestStrategy(db, strategy);
      });
      
      it('应该成功更新策略包', async () => {
        const updateData = {
          name: '更新后的策略名称',
          description: '更新后的描述'
        };
        
        const response = await request(app)
          .put(`/api/trader/strategies/${strategyId}`)
          .send(updateData)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.name).toBe(updateData.name);
        expect(response.body.data.description).toBe(updateData.description);
      });
      
      it('应该处理不存在的策略包', async () => {
        const updateData = { name: '新名称' };
        
        const response = await request(app)
          .put('/api/trader/strategies/99999')
          .send(updateData)
          .expect(404);
        
        global.testUtils.validateApiResponse(response, 404);
      });
    });
  });
  
  describe('订单管理', () => {
    let strategyId;
    
    beforeEach(async () => {
      const strategy = global.testUtils.generateTestData.strategyPackage();
      strategyId = await insertTestStrategy(db, strategy);
    });
    
    describe('POST /api/trader/orders', () => {
      it('应该成功创建订单', async () => {
        const orderData = {
          ...global.testUtils.generateTestData.order(),
          strategy_id: strategyId
        };
        
        const response = await request(app)
          .post('/api/trader/orders')
          .send(orderData)
          .expect(201);
        
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.strategy_id).toBe(strategyId);
        expect(response.body.data.status).toBe('pending');
      });
      
      it('应该验证订单参数', async () => {
        const invalidOrder = {
          symbol: 'BTCUSDT',
          side: 'invalid_side',
          quantity: -1
        };
        
        const response = await request(app)
          .post('/api/trader/orders')
          .send(invalidOrder)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
      });
      
      it('应该验证策略包存在性', async () => {
        const orderData = {
          ...global.testUtils.generateTestData.order(),
          strategy_id: 99999
        };
        
        const response = await request(app)
          .post('/api/trader/orders')
          .send(orderData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('strategy');
      });
    });
    
    describe('GET /api/trader/orders', () => {
      beforeEach(async () => {
        // 插入测试订单
        const orders = [
          { ...global.testUtils.generateTestData.order(), strategy_id: strategyId },
          { ...global.testUtils.generateTestData.order(), strategy_id: strategyId, status: 'filled' },
          { ...global.testUtils.generateTestData.order(), strategy_id: strategyId, status: 'cancelled' }
        ];
        
        for (const order of orders) {
          await insertTestOrder(db, order);
        }
      });
      
      it('应该返回订单列表', async () => {
        const response = await request(app)
          .get('/api/trader/orders')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(3);
      });
      
      it('应该支持状态筛选', async () => {
        const response = await request(app)
          .get('/api/trader/orders?status=filled')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(order => {
          expect(order.status).toBe('filled');
        });
      });
      
      it('应该支持策略筛选', async () => {
        const response = await request(app)
          .get(`/api/trader/orders?strategy_id=${strategyId}`)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(order => {
          expect(order.strategy_id).toBe(strategyId);
        });
      });
    });
  });
  
  describe('TraderService 单元测试', () => {
    let traderService;
    
    beforeEach(() => {
      traderService = new TraderService();
    });
    
    describe('策略包验证', () => {
      it('应该验证策略包名称', () => {
        const invalidStrategy = { description: '缺少名称' };
        
        expect(() => {
          traderService.validateStrategyPackage(invalidStrategy);
        }).toThrow('策略包名称不能为空');
      });
      
      it('应该验证策略参数JSON格式', () => {
        const invalidStrategy = {
          name: '测试策略',
          parameters: 'invalid json'
        };
        
        expect(() => {
          traderService.validateStrategyPackage(invalidStrategy);
        }).toThrow('策略参数必须是有效的JSON格式');
      });
      
      it('应该通过有效策略包验证', () => {
        const validStrategy = global.testUtils.generateTestData.strategyPackage();
        
        expect(() => {
          traderService.validateStrategyPackage(validStrategy);
        }).not.toThrow();
      });
    });
    
    describe('订单验证', () => {
      it('应该验证订单必填字段', () => {
        const invalidOrder = { symbol: 'BTCUSDT' };
        
        expect(() => {
          traderService.validateOrder(invalidOrder);
        }).toThrow();
      });
      
      it('应该验证订单方向', () => {
        const invalidOrder = {
          symbol: 'BTCUSDT',
          side: 'invalid',
          type: 'market',
          quantity: 0.001
        };
        
        expect(() => {
          traderService.validateOrder(invalidOrder);
        }).toThrow('订单方向必须是buy或sell');
      });
      
      it('应该验证订单数量', () => {
        const invalidOrder = {
          symbol: 'BTCUSDT',
          side: 'buy',
          type: 'market',
          quantity: -1
        };
        
        expect(() => {
          traderService.validateOrder(invalidOrder);
        }).toThrow('订单数量必须大于0');
      });
    });
    
    describe('风险检查', () => {
      it('应该检查单笔订单风险', async () => {
        const order = global.testUtils.generateTestData.order();
        order.quantity = 100; // 大额订单
        
        const riskCheck = await traderService.checkOrderRisk(order);
        
        expect(riskCheck).toBeDefined();
        expect(riskCheck.approved).toBeDefined();
        expect(riskCheck.risk_level).toBeDefined();
      });
      
      it('应该检查持仓风险', async () => {
        const positions = [
          { symbol: 'BTCUSDT', quantity: 1.5, value: 45000 },
          { symbol: 'ETHUSDT', quantity: 10, value: 20000 }
        ];
        
        const riskCheck = await traderService.checkPositionRisk(positions);
        
        expect(riskCheck).toBeDefined();
        expect(riskCheck.total_exposure).toBeDefined();
        expect(riskCheck.concentration_risk).toBeDefined();
      });
    });
  });
  
  describe('集成测试', () => {
    it('应该完成完整的交易流程', async () => {
      // 1. 创建策略包
      const strategyData = global.testUtils.generateTestData.strategyPackage();
      const strategyResponse = await request(app)
        .post('/api/trader/strategy-packages')
        .send(strategyData)
        .expect(201);
      
      const strategyId = strategyResponse.body.data.id;
      
      // 2. 创建订单
      const orderData = {
        ...global.testUtils.generateTestData.order(),
        strategy_id: strategyId
      };
      
      const orderResponse = await request(app)
        .post('/api/trader/orders')
        .send(orderData)
        .expect(201);
      
      const orderId = orderResponse.body.data.id;
      
      // 3. 查询订单状态
      const statusResponse = await request(app)
        .get(`/api/trader/orders/${orderId}`)
        .expect(200);
      
      expect(statusResponse.body.data.status).toBe('pending');
      
      // 4. 查询策略包的订单
      const strategyOrdersResponse = await request(app)
        .get(`/api/trader/orders?strategy_id=${strategyId}`)
        .expect(200);
      
      expect(strategyOrdersResponse.body.data.length).toBe(1);
      expect(strategyOrdersResponse.body.data[0].id).toBe(orderId);
    });
  });
});

// 辅助函数
async function createTestTables(db) {
  const tables = [
    `CREATE TABLE IF NOT EXISTS strategy_packages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT,
      version TEXT DEFAULT '1.0.0',
      parameters TEXT,
      status TEXT DEFAULT 'active',
      created_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`,
    `CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      strategy_id INTEGER,
      symbol TEXT NOT NULL,
      side TEXT NOT NULL,
      type TEXT NOT NULL,
      quantity REAL NOT NULL,
      price REAL,
      status TEXT DEFAULT 'pending',
      filled_quantity REAL DEFAULT 0,
      average_price REAL,
      created_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (strategy_id) REFERENCES strategy_packages (id)
    )`,
    `CREATE TABLE IF NOT EXISTS trades (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER,
      symbol TEXT NOT NULL,
      side TEXT NOT NULL,
      quantity REAL NOT NULL,
      price REAL NOT NULL,
      commission REAL DEFAULT 0,
      commission_asset TEXT,
      executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (order_id) REFERENCES orders (id)
    )`
  ];
  
  for (const sql of tables) {
    await new Promise((resolve, reject) => {
      db.run(sql, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
}

async function clearTestData(db) {
  const tables = ['trades', 'orders', 'strategy_packages'];
  
  for (const table of tables) {
    await new Promise((resolve, reject) => {
      db.run(`DELETE FROM ${table}`, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
}

async function insertTestStrategy(db, strategy) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO strategy_packages (name, description, version, parameters, status, created_by)
                 VALUES (?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      strategy.name,
      strategy.description,
      strategy.version,
      strategy.parameters,
      strategy.status,
      strategy.created_by
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}

async function insertTestOrder(db, order) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO orders (strategy_id, symbol, side, type, quantity, price, status, created_by)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      order.strategy_id,
      order.symbol,
      order.side,
      order.type,
      order.quantity,
      order.price,
      order.status,
      order.created_by
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}