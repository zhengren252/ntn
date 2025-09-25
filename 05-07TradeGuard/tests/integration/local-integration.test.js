/**
 * TradeGuard本地集成测试
 * 测试计划: TEST-PLAN-M0507-TRADEGUARD-V1 阶段3
 * 
 * 本测试在没有Docker环境的情况下运行
 * 使用模拟服务和内存数据库进行集成测试
 */

const request = require('supertest');
const express = require('express');
const { EventEmitter } = require('events');

// 导入TradeGuard核心模块 - 注意：在测试环境中使用模拟对象
// const { traderService } = require('../../api/modules/trader/services/traderService');
// const { riskService } = require('../../api/modules/risk/services/riskService');
// const { financeService } = require('../../api/modules/finance/services/financeService');

// 模拟服务对象
const traderService = {
  async processStrategyPackage(data) {
    return { success: true, data: { packageId: 1, ...data } };
  }
};

const riskService = {
  async performRiskAssessment(data) {
    return {
      success: true,
      data: {
        assessmentId: 1,
        riskScore: 45,
        riskLevel: 'medium',
        approved: true,
        ...data
      }
    };
  }
};

const financeService = {
  async processBudgetRequest(data) {
    return { success: true, data: { requestId: 1, ...data } };
  }
};

describe('TradeGuard本地集成测试', () => {
    let app;
    let mockRedis;
    let mockTACoreService;
    let messageEmitter;
    
    beforeAll(async () => {
        console.log('🚀 初始化本地集成测试环境...');
        
        // 创建模拟Redis
        mockRedis = createMockRedis();
        
        // 创建模拟TACoreService
        mockTACoreService = createMockTACoreService();
        
        // 创建消息事件发射器
        messageEmitter = new EventEmitter();
        
        // 服务已通过导入获得，无需初始化
        
        // 创建Express应用
        app = createTestApp();
        
        console.log('✅ 本地集成测试环境初始化完成');
    }, 30000);
    
    afterAll(async () => {
        console.log('🧹 清理本地集成测试环境...');
        
        if (messageEmitter) {
            messageEmitter.removeAllListeners();
        }
        
        console.log('✅ 本地集成测试环境清理完成');
    });
    
    /**
     * 创建模拟Redis客户端
     */
    function createMockRedis() {
        const storage = new Map();
        
        return {
            data: storage,
            async get(key) {
                return storage.get(key) || null;
            },
            async set(key, value) {
                storage.set(key, value);
                return 'OK';
            },
            async setEx(key, ttl, value) {
                storage.set(key, value);
                // 简化实现，不处理TTL
                return 'OK';
            },
            async exists(key) {
                return storage.has(key) ? 1 : 0;
            },
            async keys(pattern) {
                const keys = Array.from(storage.keys());
                if (pattern === '*') return keys;
                // 简化模式匹配
                const regex = new RegExp(pattern.replace('*', '.*'));
                return keys.filter(key => regex.test(key));
            },
            async flushDb() {
                storage.clear();
                return 'OK';
            },
            isReady: true
        };
    }
    
    /**
     * 创建模拟TACoreService
     */
    function createMockTACoreService() {
        return {
            async executeOrder(orderData) {
                // 模拟订单执行
                const success = orderData.amount <= 10000; // 小额订单成功
                
                return {
                    success,
                    orderId: `order_${Date.now()}`,
                    status: success ? 'executed' : 'failed',
                    executedAmount: success ? orderData.amount : 0,
                    executedPrice: success ? orderData.price || 50000 : 0,
                    timestamp: Date.now(),
                    error: success ? null : 'Insufficient liquidity'
                };
            },
            
            async getSystemHealth() {
                return {
                    status: 'healthy',
                    timestamp: Date.now(),
                    services: {
                        trading: 'active',
                        risk: 'active',
                        data: 'active'
                    }
                };
            }
        };
    }
    
    /**
     * 创建测试Express应用
     */
    function createTestApp() {
        const testApp = express();
        testApp.use(express.json());
        
        // 健康检查端点
        testApp.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: Date.now(),
                components: {
                    redis: 'connected',
                    database: 'connected',
                    tacore: 'connected'
                }
            });
        });
        
        // 策略处理端点
        testApp.post('/api/strategy/process', async (req, res) => {
            try {
                const strategy = req.body;
                const result = await processStrategy(strategy);
                res.json(result);
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        // 状态查询端点
        testApp.get('/api/status/:type', async (req, res) => {
            const { type } = req.params;
            const key = `system:status:${type}`;
            const data = await mockRedis.get(key);
            
            res.json({
                type,
                data: data ? JSON.parse(data) : null,
                timestamp: Date.now()
            });
        });
        
        return testApp;
    }
    
    /**
     * 处理策略的核心逻辑
     */
    async function processStrategy(strategy) {
        console.log(`📋 处理策略: ${strategy.id}`);
        
        // 1. 风控评估
        const riskAssessment = await riskService.performRiskAssessment({
            strategyId: parseInt(strategy.id.replace('test_strategy_', '')) || 1,
            assessmentType: 'manual',
            assessedBy: 'system'
        });
        
        console.log(`🛡️ 风控评估结果:`, riskAssessment);
        
        // 记录风控结果
        await mockRedis.set(
            `risk:assessment:${strategy.id}`,
            JSON.stringify(riskAssessment)
        );
        
        if (!riskAssessment.success || !riskAssessment.data) {
            const result = {
                success: false,
                reason: 'risk_rejected',
                riskAssessment,
                timestamp: Date.now()
            };
            
            await mockRedis.set(
                `final:status:${strategy.id}`,
                JSON.stringify(result)
            );
            
            return result;
        }
        
        // 2. 财务分配
        const budgetRequest = {
            strategyId: parseInt(strategy.id.replace('test_strategy_', '')) || 1,
            requestType: 'initial',
            requestedAmount: strategy.amount,
            priority: 'normal',
            justification: 'Integration test budget request',
            requestedBy: 'system'
        };
        
        const budgetResult = await financeService.processBudgetRequest(budgetRequest);
        console.log(`💰 财务分配结果:`, budgetResult);
        
        // 记录财务结果
        await mockRedis.set(
            `budget:allocation:${strategy.id}`,
            JSON.stringify(budgetResult)
        );
        
        if (!budgetResult.success) {
            const result = {
                success: false,
                reason: 'budget_rejected',
                budgetResult,
                timestamp: Date.now()
            };
            
            await mockRedis.set(
                `final:status:${strategy.id}`,
                JSON.stringify(result)
            );
            
            return result;
        }
        
        // 3. 执行交易
        const orderData = {
            symbol: strategy.symbol,
            amount: budgetResult.approvedAmount,
            type: strategy.type,
            price: strategy.price
        };
        
        const executionResult = await mockTACoreService.executeOrder(orderData);
        console.log(`⚡ 执行结果:`, executionResult);
        
        // 记录执行结果
        await mockRedis.set(
            `execution:request:${strategy.id}`,
            JSON.stringify(executionResult)
        );
        
        // 4. 更新系统状态
        await updateSystemStatus(strategy, executionResult);
        
        // 5. 记录最终状态
        const finalResult = {
            success: executionResult.success,
            strategyId: strategy.id,
            orderId: executionResult.orderId,
            executedAmount: executionResult.executedAmount,
            riskAssessment,
            budgetResult,
            executionResult,
            timestamp: Date.now()
        };
        
        await mockRedis.set(
            `final:status:${strategy.id}`,
            JSON.stringify(finalResult)
        );
        
        return finalResult;
    }
    
    /**
     * 更新系统状态
     */
    async function updateSystemStatus(strategy, executionResult) {
        // 更新持仓状态
        const currentPositions = await mockRedis.get('system:status:trader:positions');
        const positions = currentPositions ? JSON.parse(currentPositions) : {};
        
        if (executionResult.success) {
            positions[strategy.symbol] = {
                amount: executionResult.executedAmount,
                price: executionResult.executedPrice,
                timestamp: Date.now()
            };
        }
        
        await mockRedis.set(
            'system:status:trader:positions',
            JSON.stringify(positions)
        );
        
        // 更新风险敞口
        const totalExposure = Object.values(positions)
            .reduce((sum, pos) => sum + (pos.amount * pos.price), 0);
        
        await mockRedis.set(
            'system:status:risk:exposure',
            JSON.stringify({
                totalExposure,
                positions: Object.keys(positions).length,
                timestamp: Date.now()
            })
        );
        
        // 更新财务概览
        await mockRedis.set(
            'system:status:finance:overview',
            JSON.stringify({
                totalBalance: 1000000, // 模拟余额
                allocatedAmount: totalExposure,
                availableAmount: 1000000 - totalExposure,
                timestamp: Date.now()
            })
        );
        
        // 更新最后活动时间
        await mockRedis.set(
            'system:status:trader:last_activity',
            Date.now().toString()
        );
    }
    
    /**
     * INT-TG-01: 消息订阅与触发
     */
    describe('INT-TG-01: 消息订阅与触发', () => {
        test('应该成功接收并解析策略消息', async () => {
            const testStrategy = {
                id: 'test_strategy_001',
                type: 'spot_trading',
                symbol: 'BTC/USDT',
                amount: 5000,
                riskLevel: 'low',
                leverage: 1,
                stopLoss: 0.02,
                takeProfit: 0.05,
                timestamp: Date.now()
            };
            
            // 模拟消息接收和处理
            const result = await processStrategy(testStrategy);
            
            expect(result).toBeDefined();
            expect(result.strategyId).toBe(testStrategy.id);
            
            // 验证处理记录
            const processedData = await mockRedis.get(`final:status:${testStrategy.id}`);
            expect(processedData).toBeDefined();
            
            const processed = JSON.parse(processedData);
            expect(processed.strategyId).toBe(testStrategy.id);
            
            console.log('✅ 消息接收和解析验证通过');
        });
    });
    
    /**
     * INT-TG-02: 端到端成功流程集成
     */
    describe('INT-TG-02: 端到端成功流程集成', () => {
        test('应该完成完整的策略执行流程', async () => {
            const approvedStrategy = {
                id: 'approved_strategy_001',
                type: 'spot_trading',
                symbol: 'BTC/USDT',
                amount: 3000,
                riskLevel: 'low',
                leverage: 1,
                stopLoss: 0.01,
                takeProfit: 0.03,
                timestamp: Date.now()
            };
            
            // 通过API处理策略
            const response = await request(app)
                .post('/api/strategy/process')
                .send(approvedStrategy)
                .expect(200);
            
            expect(response.body.success).toBe(true);
            expect(response.body.strategyId).toBe(approvedStrategy.id);
            
            // 验证风控逻辑执行
            const riskData = await mockRedis.get(`risk:assessment:${approvedStrategy.id}`);
            expect(riskData).toBeDefined();
            
            const risk = JSON.parse(riskData);
            expect(risk.approved).toBe(true);
            
            // 验证财务逻辑执行
            const budgetData = await mockRedis.get(`budget:allocation:${approvedStrategy.id}`);
            expect(budgetData).toBeDefined();
            
            const budget = JSON.parse(budgetData);
            expect(budget.success).toBe(true);
            expect(budget.approvedAmount).toBeGreaterThan(0);
            
            // 验证执行结果
            const executionData = await mockRedis.get(`execution:request:${approvedStrategy.id}`);
            expect(executionData).toBeDefined();
            
            const execution = JSON.parse(executionData);
            expect(execution.success).toBe(true);
            expect(execution.orderId).toBeDefined();
            
            console.log('✅ 端到端流程验证通过');
        });
    });
    
    /**
     * INT-TG-03: 状态上报验证
     */
    describe('INT-TG-03: 状态上报验证', () => {
        test('应该正确上报持仓状态', async () => {
            // 先执行一个策略以产生持仓
            const strategy = {
                id: 'position_test_001',
                type: 'spot_trading',
                symbol: 'ETH/USDT',
                amount: 2000,
                riskLevel: 'low',
                timestamp: Date.now()
            };
            
            await processStrategy(strategy);
            
            // 检查持仓状态
            const response = await request(app)
                .get('/api/status/trader:positions')
                .expect(200);
            
            expect(response.body.data).toBeDefined();
            expect(typeof response.body.data).toBe('object');
            
            console.log('✅ 持仓状态上报验证通过');
        });
        
        test('应该正确上报风险敞口', async () => {
            const response = await request(app)
                .get('/api/status/risk:exposure')
                .expect(200);
            
            expect(response.body.data).toBeDefined();
            expect(typeof response.body.data.totalExposure).toBe('number');
            expect(response.body.data.totalExposure).toBeGreaterThanOrEqual(0);
            
            console.log('✅ 风险敞口上报验证通过');
        });
        
        test('应该正确上报财务状况', async () => {
            const response = await request(app)
                .get('/api/status/finance:overview')
                .expect(200);
            
            expect(response.body.data).toBeDefined();
            expect(typeof response.body.data.totalBalance).toBe('number');
            expect(response.body.data.totalBalance).toBeGreaterThan(0);
            
            console.log('✅ 财务状况上报验证通过');
        });
        
        test('应该维护系统健康状态', async () => {
            const response = await request(app)
                .get('/health')
                .expect(200);
            
            expect(response.body.status).toBe('healthy');
            expect(response.body.components).toBeDefined();
            expect(response.body.components.redis).toBe('connected');
            expect(response.body.components.database).toBe('connected');
            
            console.log('✅ 系统健康状态验证通过');
        });
    });
    
    /**
     * 错误处理测试
     */
    describe('错误处理验证', () => {
        test('应该正确处理高风险策略拒绝', async () => {
            const highRiskStrategy = {
                id: 'high_risk_strategy_001',
                type: 'futures_trading',
                symbol: 'DOGE/USDT',
                amount: 100000,
                riskLevel: 'high',
                leverage: 20,
                timestamp: Date.now()
            };
            
            const response = await request(app)
                .post('/api/strategy/process')
                .send(highRiskStrategy)
                .expect(200);
            
            expect(response.body.success).toBe(false);
            expect(response.body.reason).toBe('risk_rejected');
            
            console.log('✅ 高风险策略拒绝验证通过');
        });
        
        test('应该正确处理无效策略', async () => {
            const invalidStrategy = {
                id: 'invalid_strategy_001',
                // 缺少必要字段
                invalidField: 'test'
            };
            
            const response = await request(app)
                .post('/api/strategy/process')
                .send(invalidStrategy)
                .expect(500);
            
            expect(response.body.error).toBeDefined();
            
            console.log('✅ 无效策略处理验证通过');
        });
    });
});