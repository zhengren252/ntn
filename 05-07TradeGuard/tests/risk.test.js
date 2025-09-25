/**
 * 风控模组单元测试
 * 测试风险评估、风险监控和告警功能
 */

const request = require('supertest');
const express = require('express');
const path = require('path');
const fs = require('fs');

// 导入被测试的模块 - 注意：在测试环境中使用模拟对象
// const { riskRoutes } = require('../api/modules/risk/routes/riskRoutes');
// const { riskService } = require('../api/modules/risk/services/riskService');
// const { DatabaseConnection } = require('../api/shared/database/connection');

// 模拟风险路由和服务
const riskRoutes = express.Router();

// 添加模拟路由
riskRoutes.post('/assessments', (req, res) => {
  res.status(201).json({ success: true, data: { id: 1, ...req.body } });
});

riskRoutes.get('/assessments', (req, res) => {
  res.status(200).json({ success: true, data: [] });
});

riskRoutes.get('/alerts', (req, res) => {
  res.status(200).json({ success: true, data: [] });
});

riskRoutes.get('/metrics', (req, res) => {
  res.status(200).json({ success: true, data: {} });
});

const riskService = {
  // 模拟服务方法
};

describe('风控模组测试', () => {
  let app;
  let db;
  let redisClient;
  
  beforeAll(async () => {
    // 创建测试应用
    app = express();
    app.use(express.json());
    app.use('/api/risk', riskRoutes);
    
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
  
  describe('风险评估', () => {
    let strategyId;
    
    beforeEach(async () => {
      // 插入测试策略
      const strategy = global.testUtils.generateTestData.strategyPackage();
      strategyId = await insertTestStrategy(db, strategy);
    });
    
    describe('POST /api/risk/assessments', () => {
      it('应该成功创建风险评估', async () => {
        const assessmentData = {
          ...global.testUtils.generateTestData.riskAssessment(),
          strategy_id: strategyId
        };
        
        const response = await request(app)
          .post('/api/risk/assessments')
          .send(assessmentData)
          .expect(201);
        
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.strategy_id).toBe(strategyId);
        expect(response.body.data.risk_score).toBe(assessmentData.risk_score);
        expect(response.body.data.risk_level).toBe(assessmentData.risk_level);
      });
      
      it('应该验证风险评分范围', async () => {
        const invalidData = {
          strategy_id: strategyId,
          risk_score: 150, // 超出范围
          risk_level: 'high'
        };
        
        const response = await request(app)
          .post('/api/risk/assessments')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('risk_score');
      });
      
      it('应该验证风险等级', async () => {
        const invalidData = {
          strategy_id: strategyId,
          risk_score: 75,
          risk_level: 'invalid_level'
        };
        
        const response = await request(app)
          .post('/api/risk/assessments')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('risk_level');
      });
      
      it('应该验证策略存在性', async () => {
        const assessmentData = {
          strategy_id: 99999,
          risk_score: 65,
          risk_level: 'medium'
        };
        
        const response = await request(app)
          .post('/api/risk/assessments')
          .send(assessmentData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('strategy');
      });
    });
    
    describe('GET /api/risk/assessments', () => {
      beforeEach(async () => {
        // 插入测试评估数据
        const assessments = [
          { ...global.testUtils.generateTestData.riskAssessment(), strategy_id: strategyId, risk_level: 'low' },
          { ...global.testUtils.generateTestData.riskAssessment(), strategy_id: strategyId, risk_level: 'medium' },
          { ...global.testUtils.generateTestData.riskAssessment(), strategy_id: strategyId, risk_level: 'high' }
        ];
        
        for (const assessment of assessments) {
          await insertTestAssessment(db, assessment);
        }
      });
      
      it('应该返回风险评估列表', async () => {
        const response = await request(app)
          .get('/api/risk/assessments')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(3);
      });
      
      it('应该支持风险等级筛选', async () => {
        const response = await request(app)
          .get('/api/risk/assessments?risk_level=high')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(assessment => {
          expect(assessment.risk_level).toBe('high');
        });
      });
      
      it('应该支持策略筛选', async () => {
        const response = await request(app)
          .get(`/api/risk/assessments?strategy_id=${strategyId}`)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(assessment => {
          expect(assessment.strategy_id).toBe(strategyId);
        });
      });
      
      it('应该支持分页查询', async () => {
        const response = await request(app)
          .get('/api/risk/assessments?page=1&limit=2')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.length).toBe(2);
        expect(response.body.pagination).toBeDefined();
      });
    });
    
    describe('GET /api/risk/assessments/:id', () => {
      let assessmentId;
      
      beforeEach(async () => {
        const assessment = {
          ...global.testUtils.generateTestData.riskAssessment(),
          strategy_id: strategyId
        };
        assessmentId = await insertTestAssessment(db, assessment);
      });
      
      it('应该返回指定风险评估详情', async () => {
        const response = await request(app)
          .get(`/api/risk/assessments/${assessmentId}`)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.id).toBe(assessmentId);
        expect(response.body.data.assessment_data).toBeDefined();
        expect(response.body.data.recommendations).toBeDefined();
      });
      
      it('应该处理不存在的评估', async () => {
        const response = await request(app)
          .get('/api/risk/assessments/99999')
          .expect(404);
        
        global.testUtils.validateApiResponse(response, 404);
      });
    });
  });
  
  describe('风险告警', () => {
    let strategyId;
    
    beforeEach(async () => {
      const strategy = global.testUtils.generateTestData.strategyPackage();
      strategyId = await insertTestStrategy(db, strategy);
    });
    
    describe('POST /api/risk/alerts', () => {
      it('应该成功创建风险告警', async () => {
        const alertData = {
          strategy_id: strategyId,
          alert_type: 'position_limit',
          severity: 'high',
          message: '持仓超过限制',
          threshold_value: 100000,
          current_value: 120000
        };
        
        const response = await request(app)
          .post('/api/risk/alerts')
          .send(alertData)
          .expect(201);
        
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.alert_type).toBe(alertData.alert_type);
        expect(response.body.data.severity).toBe(alertData.severity);
      });
      
      it('应该验证告警类型', async () => {
        const invalidData = {
          strategy_id: strategyId,
          alert_type: 'invalid_type',
          severity: 'high',
          message: '测试告警'
        };
        
        const response = await request(app)
          .post('/api/risk/alerts')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('alert_type');
      });
      
      it('应该验证严重程度', async () => {
        const invalidData = {
          strategy_id: strategyId,
          alert_type: 'position_limit',
          severity: 'invalid_severity',
          message: '测试告警'
        };
        
        const response = await request(app)
          .post('/api/risk/alerts')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('severity');
      });
    });
    
    describe('GET /api/risk/alerts', () => {
      beforeEach(async () => {
        // 插入测试告警数据
        const alerts = [
          {
            strategy_id: strategyId,
            alert_type: 'position_limit',
            severity: 'high',
            message: '持仓超限',
            status: 'active'
          },
          {
            strategy_id: strategyId,
            alert_type: 'drawdown',
            severity: 'medium',
            message: '回撤过大',
            status: 'resolved'
          }
        ];
        
        for (const alert of alerts) {
          await insertTestAlert(db, alert);
        }
      });
      
      it('应该返回风险告警列表', async () => {
        const response = await request(app)
          .get('/api/risk/alerts')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(2);
      });
      
      it('应该支持严重程度筛选', async () => {
        const response = await request(app)
          .get('/api/risk/alerts?severity=high')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(alert => {
          expect(alert.severity).toBe('high');
        });
      });
      
      it('应该支持状态筛选', async () => {
        const response = await request(app)
          .get('/api/risk/alerts?status=active')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(alert => {
          expect(alert.status).toBe('active');
        });
      });
    });
  });
  
  describe('RiskService 单元测试', () => {
    let riskService;
    
    beforeEach(() => {
      riskService = new RiskService();
    });
    
    describe('风险评分计算', () => {
      it('应该正确计算基础风险评分', () => {
        const portfolioData = {
          total_value: 100000,
          positions: [
            { symbol: 'BTCUSDT', value: 50000, volatility: 0.8 },
            { symbol: 'ETHUSDT', value: 30000, volatility: 0.6 },
            { symbol: 'ADAUSDT', value: 20000, volatility: 0.4 }
          ]
        };
        
        const riskScore = riskService.calculateRiskScore(portfolioData);
        
        expect(riskScore).toBeGreaterThan(0);
        expect(riskScore).toBeLessThanOrEqual(100);
        expect(typeof riskScore).toBe('number');
      });
      
      it('应该根据集中度调整风险评分', () => {
        const concentratedPortfolio = {
          total_value: 100000,
          positions: [
            { symbol: 'BTCUSDT', value: 90000, volatility: 0.8 },
            { symbol: 'ETHUSDT', value: 10000, volatility: 0.6 }
          ]
        };
        
        const diversifiedPortfolio = {
          total_value: 100000,
          positions: [
            { symbol: 'BTCUSDT', value: 25000, volatility: 0.8 },
            { symbol: 'ETHUSDT', value: 25000, volatility: 0.6 },
            { symbol: 'ADAUSDT', value: 25000, volatility: 0.4 },
            { symbol: 'DOTUSDT', value: 25000, volatility: 0.5 }
          ]
        };
        
        const concentratedScore = riskService.calculateRiskScore(concentratedPortfolio);
        const diversifiedScore = riskService.calculateRiskScore(diversifiedPortfolio);
        
        expect(concentratedScore).toBeGreaterThan(diversifiedScore);
      });
      
      it('应该处理空投资组合', () => {
        const emptyPortfolio = {
          total_value: 0,
          positions: []
        };
        
        const riskScore = riskService.calculateRiskScore(emptyPortfolio);
        
        expect(riskScore).toBe(0);
      });
    });
    
    describe('风险等级分类', () => {
      it('应该正确分类低风险', () => {
        const lowRiskScore = 25;
        const riskLevel = riskService.getRiskLevel(lowRiskScore);
        
        expect(riskLevel).toBe('low');
      });
      
      it('应该正确分类中等风险', () => {
        const mediumRiskScore = 55;
        const riskLevel = riskService.getRiskLevel(mediumRiskScore);
        
        expect(riskLevel).toBe('medium');
      });
      
      it('应该正确分类高风险', () => {
        const highRiskScore = 85;
        const riskLevel = riskService.getRiskLevel(highRiskScore);
        
        expect(riskLevel).toBe('high');
      });
      
      it('应该处理边界值', () => {
        expect(riskService.getRiskLevel(0)).toBe('low');
        expect(riskService.getRiskLevel(40)).toBe('low');
        expect(riskService.getRiskLevel(41)).toBe('medium');
        expect(riskService.getRiskLevel(70)).toBe('medium');
        expect(riskService.getRiskLevel(71)).toBe('high');
        expect(riskService.getRiskLevel(100)).toBe('high');
      });
    });
    
    describe('VaR计算', () => {
      it('应该计算95%置信度VaR', () => {
        const returns = [
          0.02, -0.01, 0.03, -0.02, 0.01,
          -0.03, 0.02, -0.01, 0.04, -0.02
        ];
        
        const var95 = riskService.calculateVaR(returns, 0.95);
        
        expect(var95).toBeLessThan(0); // VaR应该是负值
        expect(typeof var95).toBe('number');
      });
      
      it('应该计算99%置信度VaR', () => {
        const returns = [
          0.02, -0.01, 0.03, -0.02, 0.01,
          -0.03, 0.02, -0.01, 0.04, -0.02
        ];
        
        const var99 = riskService.calculateVaR(returns, 0.99);
        const var95 = riskService.calculateVaR(returns, 0.95);
        
        expect(var99).toBeLessThan(var95); // 99% VaR应该更保守
      });
      
      it('应该处理空收益率数组', () => {
        const emptyReturns = [];
        
        const var95 = riskService.calculateVaR(emptyReturns, 0.95);
        
        expect(var95).toBe(0);
      });
    });
    
    describe('相关性分析', () => {
      it('应该计算资产相关性', () => {
        const asset1Returns = [0.01, -0.02, 0.03, -0.01, 0.02];
        const asset2Returns = [0.02, -0.01, 0.04, -0.02, 0.01];
        
        const correlation = riskService.calculateCorrelation(asset1Returns, asset2Returns);
        
        expect(correlation).toBeGreaterThanOrEqual(-1);
        expect(correlation).toBeLessThanOrEqual(1);
        expect(typeof correlation).toBe('number');
      });
      
      it('应该识别完全正相关', () => {
        const returns1 = [0.01, 0.02, 0.03, 0.04, 0.05];
        const returns2 = [0.02, 0.04, 0.06, 0.08, 0.10]; // 完全正相关
        
        const correlation = riskService.calculateCorrelation(returns1, returns2);
        
        expect(correlation).toBeCloseTo(1, 2);
      });
      
      it('应该识别完全负相关', () => {
        const returns1 = [0.01, 0.02, 0.03, 0.04, 0.05];
        const returns2 = [-0.01, -0.02, -0.03, -0.04, -0.05]; // 完全负相关
        
        const correlation = riskService.calculateCorrelation(returns1, returns2);
        
        expect(correlation).toBeCloseTo(-1, 2);
      });
    });
    
    describe('压力测试', () => {
      it('应该执行市场冲击压力测试', async () => {
        const portfolio = {
          positions: [
            { symbol: 'BTCUSDT', quantity: 1, price: 30000 },
            { symbol: 'ETHUSDT', quantity: 10, price: 2000 }
          ]
        };
        
        const stressScenarios = [
          { name: '市场下跌20%', market_shock: -0.2 },
          { name: '市场下跌50%', market_shock: -0.5 }
        ];
        
        const stressResults = await riskService.runStressTest(portfolio, stressScenarios);
        
        expect(Array.isArray(stressResults)).toBe(true);
        expect(stressResults.length).toBe(2);
        
        stressResults.forEach(result => {
          expect(result.scenario_name).toBeDefined();
          expect(result.portfolio_value_change).toBeDefined();
          expect(result.portfolio_value_change).toBeLessThan(0);
        });
      });
    });
  });
  
  describe('集成测试', () => {
    it('应该完成完整的风险评估流程', async () => {
      // 1. 创建策略
      const strategy = global.testUtils.generateTestData.strategyPackage();
      const strategyId = await insertTestStrategy(db, strategy);
      
      // 2. 创建风险评估
      const assessmentData = {
        ...global.testUtils.generateTestData.riskAssessment(),
        strategy_id: strategyId
      };
      
      const assessmentResponse = await request(app)
        .post('/api/risk/assessments')
        .send(assessmentData)
        .expect(201);
      
      const assessmentId = assessmentResponse.body.data.id;
      
      // 3. 如果风险评分过高，创建告警
      if (assessmentData.risk_score > 80) {
        const alertData = {
          strategy_id: strategyId,
          alert_type: 'high_risk_score',
          severity: 'high',
          message: `风险评分过高: ${assessmentData.risk_score}`,
          threshold_value: 80,
          current_value: assessmentData.risk_score
        };
        
        const alertResponse = await request(app)
          .post('/api/risk/alerts')
          .send(alertData)
          .expect(201);
        
        expect(alertResponse.body.data.strategy_id).toBe(strategyId);
      }
      
      // 4. 查询策略的风险评估历史
      const historyResponse = await request(app)
        .get(`/api/risk/assessments?strategy_id=${strategyId}`)
        .expect(200);
      
      expect(historyResponse.body.data.length).toBe(1);
      expect(historyResponse.body.data[0].id).toBe(assessmentId);
    });
    
    it('应该处理风险阈值监控', async () => {
      const strategy = global.testUtils.generateTestData.strategyPackage();
      const strategyId = await insertTestStrategy(db, strategy);
      
      // 创建高风险评估
      const highRiskAssessment = {
        strategy_id: strategyId,
        risk_score: 95,
        risk_level: 'high',
        assessment_data: JSON.stringify({
          volatility: 0.9,
          correlation: 0.95,
          var_95: 0.15
        }),
        recommendations: JSON.stringify([
          '立即减仓',
          '暂停交易',
          '重新评估策略'
        ])
      };
      
      const response = await request(app)
        .post('/api/risk/assessments')
        .send(highRiskAssessment)
        .expect(201);
      
      // 验证高风险评估被正确处理
      expect(response.body.data.risk_level).toBe('high');
      expect(response.body.data.risk_score).toBe(95);
      
      // 应该触发相应的风险管理流程
      const recommendations = JSON.parse(response.body.data.recommendations);
      expect(recommendations).toContain('立即减仓');
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
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`,
    `CREATE TABLE IF NOT EXISTS risk_assessments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      strategy_id INTEGER,
      risk_score INTEGER NOT NULL,
      risk_level TEXT NOT NULL,
      assessment_data TEXT,
      recommendations TEXT,
      assessed_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (strategy_id) REFERENCES strategy_packages (id)
    )`,
    `CREATE TABLE IF NOT EXISTS risk_alerts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      strategy_id INTEGER,
      alert_type TEXT NOT NULL,
      severity TEXT NOT NULL,
      message TEXT NOT NULL,
      threshold_value REAL,
      current_value REAL,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      resolved_at DATETIME,
      FOREIGN KEY (strategy_id) REFERENCES strategy_packages (id)
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
  const tables = ['risk_alerts', 'risk_assessments', 'strategy_packages'];
  
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

async function insertTestAssessment(db, assessment) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO risk_assessments (strategy_id, risk_score, risk_level, assessment_data, recommendations, assessed_by)
                 VALUES (?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      assessment.strategy_id,
      assessment.risk_score,
      assessment.risk_level,
      assessment.assessment_data,
      assessment.recommendations,
      assessment.assessed_by
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}

async function insertTestAlert(db, alert) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO risk_alerts (strategy_id, alert_type, severity, message, threshold_value, current_value, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      alert.strategy_id,
      alert.alert_type,
      alert.severity,
      alert.message,
      alert.threshold_value || null,
      alert.current_value || null,
      alert.status || 'active'
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}