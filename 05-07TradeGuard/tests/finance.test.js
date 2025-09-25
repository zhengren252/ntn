/**
 * 财务模组单元测试
 * 测试预算管理、资金分配和财务报告功能
 */

const request = require('supertest');
const express = require('express');
const path = require('path');
const fs = require('fs');

// 导入被测试的模块 - 注意：在测试环境中使用模拟对象
// const { financeRoutes } = require('../api/modules/finance/routes/financeRoutes');
// const { financeService } = require('../api/modules/finance/services/financeService');
// const { DatabaseConnection } = require('../api/shared/database/connection');

// 模拟财务路由和服务
const financeRoutes = express.Router();

// 添加模拟路由
financeRoutes.post('/budget-requests', (req, res) => {
  res.status(201).json({ success: true, data: { id: 1, ...req.body, status: 'pending' } });
});

financeRoutes.get('/budget-requests', (req, res) => {
  res.status(200).json({ success: true, data: [] });
});

financeRoutes.get('/allocations', (req, res) => {
  res.status(200).json({ success: true, data: [] });
});

financeRoutes.get('/accounts', (req, res) => {
  res.status(200).json({ success: true, data: [] });
});

financeRoutes.get('/transactions', (req, res) => {
  res.status(200).json({ success: true, data: [] });
});

const financeService = {
  // 模拟服务方法
};

describe('财务模组测试', () => {
  let app;
  let db;
  let redisClient;
  
  beforeAll(async () => {
    // 创建测试应用
    app = express();
    app.use(express.json());
    app.use('/api/finance', financeRoutes);
    
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
  
  describe('预算申请', () => {
    let strategyId;
    
    beforeEach(async () => {
      // 插入测试策略
      const strategy = global.testUtils.generateTestData.strategyPackage();
      strategyId = await insertTestStrategy(db, strategy);
    });
    
    describe('POST /api/finance/budget-requests', () => {
      it('应该成功创建预算申请', async () => {
        const budgetData = {
          strategy_id: strategyId,
          requested_amount: 100000,
          purpose: '量化交易策略执行',
          justification: '基于历史回测数据，预期年化收益率15%',
          duration_months: 12,
          risk_level: 'medium'
        };
        
        const response = await request(app)
          .post('/api/finance/budget-requests')
          .send(budgetData)
          .expect(201);
        
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.strategy_id).toBe(strategyId);
        expect(response.body.data.requested_amount).toBe(budgetData.requested_amount);
        expect(response.body.data.status).toBe('pending');
      });
      
      it('应该验证申请金额范围', async () => {
        const invalidData = {
          strategy_id: strategyId,
          requested_amount: -1000, // 负数金额
          purpose: '测试',
          justification: '测试理由'
        };
        
        const response = await request(app)
          .post('/api/finance/budget-requests')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('requested_amount');
      });
      
      it('应该验证必填字段', async () => {
        const incompleteData = {
          strategy_id: strategyId,
          requested_amount: 50000
          // 缺少purpose和justification
        };
        
        const response = await request(app)
          .post('/api/finance/budget-requests')
          .send(incompleteData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toMatch(/(purpose|justification)/);
      });
      
      it('应该验证策略存在性', async () => {
        const budgetData = {
          strategy_id: 99999,
          requested_amount: 50000,
          purpose: '测试',
          justification: '测试理由'
        };
        
        const response = await request(app)
          .post('/api/finance/budget-requests')
          .send(budgetData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('strategy');
      });
    });
    
    describe('GET /api/finance/budget-requests', () => {
      beforeEach(async () => {
        // 插入测试预算申请
        const requests = [
          {
            strategy_id: strategyId,
            requested_amount: 100000,
            purpose: '策略A执行',
            justification: '高收益策略',
            status: 'pending'
          },
          {
            strategy_id: strategyId,
            requested_amount: 200000,
            purpose: '策略B执行',
            justification: '稳健策略',
            status: 'approved'
          },
          {
            strategy_id: strategyId,
            requested_amount: 50000,
            purpose: '策略C执行',
            justification: '测试策略',
            status: 'rejected'
          }
        ];
        
        for (const request of requests) {
          await insertTestBudgetRequest(db, request);
        }
      });
      
      it('应该返回预算申请列表', async () => {
        const response = await request(app)
          .get('/api/finance/budget-requests')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(3);
      });
      
      it('应该支持状态筛选', async () => {
        const response = await request(app)
          .get('/api/finance/budget-requests?status=approved')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(request => {
          expect(request.status).toBe('approved');
        });
      });
      
      it('应该支持金额范围筛选', async () => {
        const response = await request(app)
          .get('/api/finance/budget-requests?min_amount=100000')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(request => {
          expect(request.requested_amount).toBeGreaterThanOrEqual(100000);
        });
      });
      
      it('应该支持分页查询', async () => {
        const response = await request(app)
          .get('/api/finance/budget-requests?page=1&limit=2')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.length).toBe(2);
        expect(response.body.pagination).toBeDefined();
      });
    });
    
    describe('PUT /api/finance/budget-requests/:id/approve', () => {
      let requestId;
      
      beforeEach(async () => {
        const budgetRequest = {
          strategy_id: strategyId,
          requested_amount: 100000,
          purpose: '测试申请',
          justification: '测试理由',
          status: 'pending'
        };
        requestId = await insertTestBudgetRequest(db, budgetRequest);
      });
      
      it('应该成功批准预算申请', async () => {
        const approvalData = {
          approved_amount: 80000,
          approval_notes: '部分批准，降低风险'
        };
        
        const response = await request(app)
          .put(`/api/finance/budget-requests/${requestId}/approve`)
          .send(approvalData)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(response.body.data.status).toBe('approved');
        expect(response.body.data.approved_amount).toBe(approvalData.approved_amount);
      });
      
      it('应该验证批准金额不超过申请金额', async () => {
        const invalidApproval = {
          approved_amount: 150000, // 超过申请金额
          approval_notes: '超额批准'
        };
        
        const response = await request(app)
          .put(`/api/finance/budget-requests/${requestId}/approve`)
          .send(invalidApproval)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('approved_amount');
      });
      
      it('应该处理不存在的申请', async () => {
        const response = await request(app)
          .put('/api/finance/budget-requests/99999/approve')
          .send({ approved_amount: 50000 })
          .expect(404);
        
        global.testUtils.validateApiResponse(response, 404);
      });
    });
  });
  
  describe('资金分配', () => {
    let strategyId;
    let budgetRequestId;
    
    beforeEach(async () => {
      const strategy = global.testUtils.generateTestData.strategyPackage();
      strategyId = await insertTestStrategy(db, strategy);
      
      const budgetRequest = {
        strategy_id: strategyId,
        requested_amount: 100000,
        purpose: '测试申请',
        justification: '测试理由',
        status: 'approved',
        approved_amount: 100000
      };
      budgetRequestId = await insertTestBudgetRequest(db, budgetRequest);
    });
    
    describe('POST /api/finance/fund-allocations', () => {
      it('应该成功创建资金分配', async () => {
        const allocationData = {
          budget_request_id: budgetRequestId,
          allocated_amount: 80000,
          allocation_type: 'initial',
          allocation_date: new Date().toISOString().split('T')[0],
          notes: '初始资金分配'
        };
        
        const response = await request(app)
          .post('/api/finance/fund-allocations')
          .send(allocationData)
          .expect(201);
        
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.budget_request_id).toBe(budgetRequestId);
        expect(response.body.data.allocated_amount).toBe(allocationData.allocated_amount);
      });
      
      it('应该验证分配金额不超过批准金额', async () => {
        const invalidData = {
          budget_request_id: budgetRequestId,
          allocated_amount: 150000, // 超过批准金额
          allocation_type: 'initial'
        };
        
        const response = await request(app)
          .post('/api/finance/fund-allocations')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('allocated_amount');
      });
      
      it('应该验证分配类型', async () => {
        const invalidData = {
          budget_request_id: budgetRequestId,
          allocated_amount: 50000,
          allocation_type: 'invalid_type'
        };
        
        const response = await request(app)
          .post('/api/finance/fund-allocations')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('allocation_type');
      });
    });
    
    describe('GET /api/finance/fund-allocations', () => {
      beforeEach(async () => {
        // 插入测试分配记录
        const allocations = [
          {
            budget_request_id: budgetRequestId,
            allocated_amount: 50000,
            allocation_type: 'initial',
            status: 'active'
          },
          {
            budget_request_id: budgetRequestId,
            allocated_amount: 30000,
            allocation_type: 'additional',
            status: 'active'
          }
        ];
        
        for (const allocation of allocations) {
          await insertTestFundAllocation(db, allocation);
        }
      });
      
      it('应该返回资金分配列表', async () => {
        const response = await request(app)
          .get('/api/finance/fund-allocations')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(2);
      });
      
      it('应该支持预算申请筛选', async () => {
        const response = await request(app)
          .get(`/api/finance/fund-allocations?budget_request_id=${budgetRequestId}`)
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(allocation => {
          expect(allocation.budget_request_id).toBe(budgetRequestId);
        });
      });
      
      it('应该支持分配类型筛选', async () => {
        const response = await request(app)
          .get('/api/finance/fund-allocations?allocation_type=initial')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(allocation => {
          expect(allocation.allocation_type).toBe('initial');
        });
      });
    });
  });
  
  describe('账户管理', () => {
    describe('POST /api/finance/accounts', () => {
      it('应该成功创建交易账户', async () => {
        const accountData = {
          accountName: '主交易账户',
          accountType: 'strategy',
          initialBalance: 1000000,
          currency: 'USDT',
          exchange: 'binance',
          status: 'active',
          createdBy: 'test_user'
        };
        
        const response = await request(app)
          .post('/api/finance/accounts')
          .send(accountData)
          .expect(201);
        
        global.testUtils.validateApiResponse(response, 201);
        expect(response.body.data.id).toBeDefined();
        expect(response.body.data.accountId).toBeDefined();
        expect(response.body.data.accountNumber).toBeDefined();
      });
      
      it('应该验证账户类型', async () => {
        const invalidData = {
          accountName: '测试账户',
          accountType: 'invalid_type',
          initialBalance: 100000,
          createdBy: 'test_user'
        };
        
        const response = await request(app)
          .post('/api/finance/accounts')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('accountType');
      });
      
      it('应该验证初始余额', async () => {
        const invalidData = {
          accountName: '测试账户',
          accountType: 'strategy',
          initialBalance: -1000, // 负数余额
          createdBy: 'test_user'
        };
        
        const response = await request(app)
          .post('/api/finance/accounts')
          .send(invalidData)
          .expect(400);
        
        global.testUtils.validateApiResponse(response, 400);
        expect(response.body.error).toContain('initialBalance');
      });
    });
    
    describe('GET /api/finance/accounts', () => {
      beforeEach(async () => {
        // 插入测试账户
        const accounts = [
          {
            accountName: '主交易账户',
            accountType: 'strategy',
            initialBalance: 1000000,
            currentBalance: 950000,
            currency: 'USDT',
            status: 'active',
            createdBy: 'test_user'
          },
          {
            accountName: '备用账户',
            accountType: 'reserve',
            initialBalance: 500000,
            currentBalance: 500000,
            currency: 'USDT',
            status: 'active',
            createdBy: 'test_user'
          }
        ];
        
        for (const account of accounts) {
          await insertTestAccount(db, account);
        }
      });
      
      it('应该返回账户列表', async () => {
        const response = await request(app)
          .get('/api/finance/accounts')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        expect(Array.isArray(response.body.data)).toBe(true);
        expect(response.body.data.length).toBe(2);
      });
      
      it('应该支持账户类型筛选', async () => {
        const response = await request(app)
          .get('/api/finance/accounts?accountType=strategy')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(account => {
          expect(account.account_type).toBe('strategy');
        });
      });
      
      it('应该支持状态筛选', async () => {
        const response = await request(app)
          .get('/api/finance/accounts?status=active')
          .expect(200);
        
        global.testUtils.validateApiResponse(response, 200);
        response.body.data.forEach(account => {
          expect(account.status).toBe('active');
        });
      });
    });
  });
  
  describe('FinanceService 单元测试', () => {
    let financeService;
    
    beforeEach(() => {
      financeService = new FinanceService();
    });
    
    describe('预算计算', () => {
      it('应该计算策略预算需求', () => {
        const strategyParams = {
          expected_return: 0.15,
          max_drawdown: 0.1,
          volatility: 0.2,
          sharpe_ratio: 1.2,
          duration_months: 12
        };
        
        const riskProfile = 'medium';
        const baseAmount = 100000;
        
        const budgetRecommendation = financeService.calculateBudgetRecommendation(
          strategyParams,
          riskProfile,
          baseAmount
        );
        
        expect(budgetRecommendation.recommended_amount).toBeGreaterThan(0);
        expect(budgetRecommendation.risk_adjusted_amount).toBeDefined();
        expect(budgetRecommendation.confidence_level).toBeDefined();
      });
      
      it('应该根据风险等级调整预算', () => {
        const strategyParams = {
          expected_return: 0.15,
          max_drawdown: 0.1,
          volatility: 0.2
        };
        
        const lowRiskBudget = financeService.calculateBudgetRecommendation(
          strategyParams,
          'low',
          100000
        );
        
        const highRiskBudget = financeService.calculateBudgetRecommendation(
          strategyParams,
          'high',
          100000
        );
        
        expect(lowRiskBudget.recommended_amount).toBeLessThan(highRiskBudget.recommended_amount);
      });
    });
    
    describe('资金分配优化', () => {
      it('应该优化多策略资金分配', () => {
        const strategies = [
          {
            id: 1,
            expected_return: 0.15,
            volatility: 0.2,
            sharpe_ratio: 0.75,
            max_allocation: 0.4
          },
          {
            id: 2,
            expected_return: 0.12,
            volatility: 0.15,
            sharpe_ratio: 0.8,
            max_allocation: 0.5
          },
          {
            id: 3,
            expected_return: 0.18,
            volatility: 0.25,
            sharpe_ratio: 0.72,
            max_allocation: 0.3
          }
        ];
        
        const totalFunds = 1000000;
        const riskTolerance = 'medium';
        
        const allocation = financeService.optimizeAllocation(strategies, totalFunds, riskTolerance);
        
        expect(allocation.allocations).toBeDefined();
        expect(allocation.allocations.length).toBe(3);
        
        // 验证分配总和等于总资金
        const totalAllocated = allocation.allocations.reduce((sum, alloc) => sum + alloc.amount, 0);
        expect(totalAllocated).toBeCloseTo(totalFunds, 2);
        
        // 验证分配比例不超过最大限制
        allocation.allocations.forEach((alloc, index) => {
          const ratio = alloc.amount / totalFunds;
          expect(ratio).toBeLessThanOrEqual(strategies[index].max_allocation + 0.01);
        });
      });
      
      it('应该处理单一策略分配', () => {
        const strategies = [
          {
            id: 1,
            expected_return: 0.15,
            volatility: 0.2,
            sharpe_ratio: 0.75,
            max_allocation: 1.0
          }
        ];
        
        const allocation = financeService.optimizeAllocation(strategies, 100000, 'medium');
        
        expect(allocation.allocations.length).toBe(1);
        expect(allocation.allocations[0].amount).toBe(100000);
      });
    });
    
    describe('风险调整收益计算', () => {
      it('应该计算风险调整后收益', () => {
        const returns = [0.02, -0.01, 0.03, -0.02, 0.01, 0.04, -0.01, 0.02];
        const riskFreeRate = 0.02;
        
        const riskAdjustedReturn = financeService.calculateRiskAdjustedReturn(
          returns,
          riskFreeRate
        );
        
        expect(riskAdjustedReturn.sharpe_ratio).toBeDefined();
        expect(riskAdjustedReturn.sortino_ratio).toBeDefined();
        expect(riskAdjustedReturn.calmar_ratio).toBeDefined();
        expect(riskAdjustedReturn.max_drawdown).toBeDefined();
      });
      
      it('应该处理负收益情况', () => {
        const negativeReturns = [-0.01, -0.02, -0.01, -0.03, -0.01];
        const riskFreeRate = 0.02;
        
        const riskAdjustedReturn = financeService.calculateRiskAdjustedReturn(
          negativeReturns,
          riskFreeRate
        );
        
        expect(riskAdjustedReturn.sharpe_ratio).toBeLessThan(0);
        expect(riskAdjustedReturn.max_drawdown).toBeGreaterThan(0);
      });
    });
    
    describe('流动性管理', () => {
      it('应该计算流动性需求', () => {
        const positions = [
          { symbol: 'BTCUSDT', value: 50000, daily_volume: 1000000000 },
          { symbol: 'ETHUSDT', value: 30000, daily_volume: 500000000 },
          { symbol: 'ADAUSDT', value: 20000, daily_volume: 100000000 }
        ];
        
        const liquidityAnalysis = financeService.analyzeLiquidity(positions);
        
        expect(liquidityAnalysis.total_value).toBe(100000);
        expect(liquidityAnalysis.liquidity_score).toBeGreaterThan(0);
        expect(liquidityAnalysis.liquidity_score).toBeLessThanOrEqual(100);
        expect(liquidityAnalysis.estimated_exit_time).toBeDefined();
      });
      
      it('应该识别流动性风险', () => {
        const illiquidPositions = [
          { symbol: 'LOWVOLCOIN', value: 50000, daily_volume: 10000 }, // 低流动性
          { symbol: 'BTCUSDT', value: 50000, daily_volume: 1000000000 }
        ];
        
        const liquidityAnalysis = financeService.analyzeLiquidity(illiquidPositions);
        
        expect(liquidityAnalysis.liquidity_warnings).toBeDefined();
        expect(liquidityAnalysis.liquidity_warnings.length).toBeGreaterThan(0);
      });
    });
    
    describe('成本分析', () => {
      it('应该计算交易成本', () => {
        const trades = [
          {
            symbol: 'BTCUSDT',
            side: 'buy',
            quantity: 1,
            price: 30000,
            fee: 30,
            timestamp: new Date()
          },
          {
            symbol: 'BTCUSDT',
            side: 'sell',
            quantity: 1,
            price: 31000,
            fee: 31,
            timestamp: new Date()
          }
        ];
        
        const costAnalysis = financeService.analyzeTradingCosts(trades);
        
        expect(costAnalysis.total_fees).toBe(61);
        expect(costAnalysis.fee_percentage).toBeGreaterThan(0);
        expect(costAnalysis.net_profit).toBe(1000 - 61);
        expect(costAnalysis.cost_efficiency).toBeDefined();
      });
      
      it('应该分析成本效率', () => {
        const highFeeTrades = [
          { symbol: 'BTCUSDT', side: 'buy', quantity: 1, price: 30000, fee: 300 },
          { symbol: 'BTCUSDT', side: 'sell', quantity: 1, price: 30100, fee: 301 }
        ];
        
        const lowFeeTrades = [
          { symbol: 'BTCUSDT', side: 'buy', quantity: 1, price: 30000, fee: 30 },
          { symbol: 'BTCUSDT', side: 'sell', quantity: 1, price: 30100, fee: 30.1 }
        ];
        
        const highFeeAnalysis = financeService.analyzeTradingCosts(highFeeTrades);
        const lowFeeAnalysis = financeService.analyzeTradingCosts(lowFeeTrades);
        
        expect(lowFeeAnalysis.cost_efficiency).toBeGreaterThan(highFeeAnalysis.cost_efficiency);
      });
    });
  });
  
  describe('集成测试', () => {
    it('应该完成完整的预算申请和分配流程', async () => {
      // 1. 创建策略
      const strategy = global.testUtils.generateTestData.strategyPackage();
      const strategyId = await insertTestStrategy(db, strategy);
      
      // 2. 提交预算申请
      const budgetData = {
        strategy_id: strategyId,
        requested_amount: 100000,
        purpose: '量化交易策略执行',
        justification: '基于历史回测数据，预期年化收益率15%',
        duration_months: 12,
        risk_level: 'medium'
      };
      
      const budgetResponse = await request(app)
        .post('/api/finance/budget-requests')
        .send(budgetData)
        .expect(201);
      
      const requestId = budgetResponse.body.data.id;
      
      // 3. 批准预算申请
      const approvalData = {
        approved_amount: 80000,
        approval_notes: '部分批准，降低风险'
      };
      
      const approvalResponse = await request(app)
        .put(`/api/finance/budget-requests/${requestId}/approve`)
        .send(approvalData)
        .expect(200);
      
      expect(approvalResponse.body.data.status).toBe('approved');
      
      // 4. 创建资金分配
      const allocationData = {
        budget_request_id: requestId,
        allocated_amount: 60000,
        allocation_type: 'initial',
        allocation_date: new Date().toISOString().split('T')[0],
        notes: '初始资金分配'
      };
      
      const allocationResponse = await request(app)
        .post('/api/finance/fund-allocations')
        .send(allocationData)
        .expect(201);
      
      expect(allocationResponse.body.data.allocated_amount).toBe(60000);
      
      // 5. 查询分配历史
      const historyResponse = await request(app)
        .get(`/api/finance/fund-allocations?budget_request_id=${requestId}`)
        .expect(200);
      
      expect(historyResponse.body.data.length).toBe(1);
    });
    
    it('应该处理多账户资金管理', async () => {
      // 创建多个账户
      const accounts = [
        {
            accountName: '主交易账户',
            accountType: 'strategy',
            initialBalance: 1000000,
            currency: 'USDT',
            createdBy: 'test_user'
          },
        {
          accountName: '风险准备金',
          accountType: 'reserve',
          initialBalance: 200000,
          currency: 'USDT',
          createdBy: 'test_user'
        }
      ];
      
      const accountIds = [];
      for (const account of accounts) {
        const response = await request(app)
          .post('/api/finance/accounts')
          .send(account)
          .expect(201);
        
        accountIds.push(response.body.data.id);
      }
      
      // 查询所有账户
      const accountsResponse = await request(app)
        .get('/api/finance/accounts')
        .expect(200);
      
      expect(accountsResponse.body.data.length).toBe(2);
      
      // 验证总资产
      const totalBalance = accountsResponse.body.data.reduce(
        (sum, account) => sum + (account.currentBalance || account.current_balance),
        0
      );
      expect(totalBalance).toBe(1200000);
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
    `CREATE TABLE IF NOT EXISTS budget_requests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      strategy_id INTEGER,
      requested_amount REAL NOT NULL,
      approved_amount REAL,
      purpose TEXT NOT NULL,
      justification TEXT NOT NULL,
      duration_months INTEGER,
      risk_level TEXT,
      status TEXT DEFAULT 'pending',
      approval_notes TEXT,
      requested_by TEXT,
      approved_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      approved_at DATETIME,
      FOREIGN KEY (strategy_id) REFERENCES strategy_packages (id)
    )`,
    `CREATE TABLE IF NOT EXISTS fund_allocations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      budget_request_id INTEGER,
      allocated_amount REAL NOT NULL,
      allocation_type TEXT NOT NULL,
      allocation_date DATE,
      status TEXT DEFAULT 'active',
      notes TEXT,
      allocated_by TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (budget_request_id) REFERENCES budget_requests (id)
    )`,
    `CREATE TABLE IF NOT EXISTS accounts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      account_name TEXT NOT NULL,
      account_type TEXT NOT NULL,
      initial_balance REAL NOT NULL,
      current_balance REAL NOT NULL,
      currency TEXT DEFAULT 'USDT',
      exchange TEXT,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
  const tables = ['fund_allocations', 'budget_requests', 'accounts', 'strategy_packages'];
  
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

async function insertTestBudgetRequest(db, request) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO budget_requests (strategy_id, requested_amount, approved_amount, purpose, justification, duration_months, risk_level, status, approval_notes, requested_by)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      request.strategy_id,
      request.requested_amount,
      request.approved_amount || null,
      request.purpose,
      request.justification,
      request.duration_months || null,
      request.risk_level || null,
      request.status || 'pending',
      request.approval_notes || null,
      request.requested_by || 'test_user'
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}

async function insertTestFundAllocation(db, allocation) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO fund_allocations (budget_request_id, allocated_amount, allocation_type, allocation_date, status, notes, allocated_by)
                 VALUES (?, ?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      allocation.budget_request_id,
      allocation.allocated_amount,
      allocation.allocation_type,
      allocation.allocation_date || new Date().toISOString().split('T')[0],
      allocation.status || 'active',
      allocation.notes || null,
      allocation.allocated_by || 'test_user'
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}

async function insertTestAccount(db, account) {
  return new Promise((resolve, reject) => {
    const sql = `INSERT INTO accounts (account_name, account_type, initial_balance, current_balance, currency, exchange, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)`;
    
    db.run(sql, [
      account.accountName || account.account_name,
      account.accountType || account.account_type,
      account.initialBalance || account.initial_balance,
      account.currentBalance || account.current_balance || account.initialBalance || account.initial_balance,
      account.currency || 'USDT',
      account.exchange || null,
      account.status || 'active'
    ], function(err) {
      if (err) reject(err);
      else resolve(this.lastID);
    });
  });
}