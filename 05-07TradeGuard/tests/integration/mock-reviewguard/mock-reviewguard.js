/**
 * 模拟ReviewGuard服务
 * 用于TradeGuard集成测试 - 发布策略包消息
 * 测试计划: TEST-PLAN-M0507-TRADEGUARD-V1 阶段3
 */

const redis = require('redis');
const zmq = require('zeromq');

class MockReviewGuard {
    constructor() {
        this.redisClient = null;
        this.publisher = null;
        this.isRunning = false;
        this.messageCount = 0;
        
        // 测试用的策略包模板
        this.testStrategies = {
            lowRisk: {
                id: 'strategy_low_risk_001',
                type: 'spot_trading',
                symbol: 'BTC/USDT',
                amount: 5000,
                riskLevel: 'low',
                leverage: 1,
                stopLoss: 0.02,
                takeProfit: 0.05,
                timestamp: Date.now(),
                metadata: {
                    source: 'mock_reviewguard',
                    testCase: 'INT-TG-02',
                    expectedResult: 'success'
                }
            },
            highRisk: {
                id: 'strategy_high_risk_001',
                type: 'futures_trading',
                symbol: 'DOGE/USDT',
                amount: 50000,
                riskLevel: 'high',
                leverage: 10,
                stopLoss: 0.05,
                takeProfit: 0.15,
                timestamp: Date.now(),
                metadata: {
                    source: 'mock_reviewguard',
                    testCase: 'INT-TG-03',
                    expectedResult: 'risk_rejection'
                }
            },
            invalidStrategy: {
                id: 'strategy_invalid_001',
                type: 'invalid_type',
                symbol: 'INVALID/PAIR',
                amount: -1000,
                riskLevel: 'unknown',
                timestamp: Date.now(),
                metadata: {
                    source: 'mock_reviewguard',
                    testCase: 'INT-TG-04',
                    expectedResult: 'validation_error'
                }
            }
        };
    }

    /**
     * 初始化Redis连接
     */
    async initializeRedis() {
        try {
            this.redisClient = redis.createClient({
                host: process.env.REDIS_HOST || 'localhost',
                port: process.env.REDIS_PORT || 6379
            });
            
            await this.redisClient.connect();
            console.log('✅ MockReviewGuard Redis连接成功');
        } catch (error) {
            console.error('❌ MockReviewGuard Redis连接失败:', error.message);
            throw error;
        }
    }

    /**
     * 初始化ZMQ发布者
     */
    async initializePublisher() {
        try {
            this.publisher = new zmq.Publisher();
            const port = process.env.ZMQ_PUBLISHER_PORT || 5558;
            await this.publisher.bind(`tcp://*:${port}`);
            console.log(`✅ MockReviewGuard ZMQ发布者启动成功，端口: ${port}`);
        } catch (error) {
            console.error('❌ MockReviewGuard ZMQ发布者启动失败:', error.message);
            throw error;
        }
    }

    /**
     * 发布策略包消息到reviewguard.pool.approved主题
     */
    async publishStrategyMessage(strategyType = 'lowRisk') {
        try {
            const strategy = this.testStrategies[strategyType];
            if (!strategy) {
                throw new Error(`未知的策略类型: ${strategyType}`);
            }

            // 更新时间戳
            strategy.timestamp = Date.now();
            strategy.messageId = `msg_${this.messageCount++}_${Date.now()}`;

            const message = {
                topic: 'reviewguard.pool.approved',
                data: strategy,
                timestamp: Date.now(),
                source: 'mock_reviewguard'
            };

            // 通过ZMQ发布消息
            await this.publisher.send([
                'reviewguard.pool.approved',
                JSON.stringify(message)
            ]);

            // 同时写入Redis用于验证
            const redisKey = `test:messages:${strategy.id}`;
            await this.redisClient.setEx(redisKey, 300, JSON.stringify(message)); // 5分钟过期

            console.log(`📤 发布策略消息: ${strategy.id} (${strategyType})`);
            console.log(`   主题: reviewguard.pool.approved`);
            console.log(`   金额: ${strategy.amount} USDT`);
            console.log(`   风险等级: ${strategy.riskLevel}`);
            
            return message;
        } catch (error) {
            console.error('❌ 发布策略消息失败:', error.message);
            throw error;
        }
    }

    /**
     * 启动自动消息发布（用于持续测试）
     */
    startAutoPublishing(interval = 30000) {
        if (this.isRunning) {
            console.log('⚠️ 自动发布已在运行中');
            return;
        }

        this.isRunning = true;
        console.log(`🚀 启动自动消息发布，间隔: ${interval}ms`);

        const publishCycle = async () => {
            if (!this.isRunning) return;

            try {
                // 轮流发布不同类型的策略
                const strategies = ['lowRisk', 'highRisk'];
                const strategyType = strategies[this.messageCount % strategies.length];
                
                await this.publishStrategyMessage(strategyType);
                
                // 每10条消息发布一次无效策略用于测试错误处理
                if (this.messageCount % 10 === 0) {
                    setTimeout(() => {
                        this.publishStrategyMessage('invalidStrategy').catch(console.error);
                    }, 5000);
                }
            } catch (error) {
                console.error('❌ 自动发布消息失败:', error.message);
            }

            if (this.isRunning) {
                setTimeout(publishCycle, interval);
            }
        };

        publishCycle();
    }

    /**
     * 停止自动发布
     */
    stopAutoPublishing() {
        this.isRunning = false;
        console.log('⏹️ 停止自动消息发布');
    }

    /**
     * 获取发布统计信息
     */
    async getStats() {
        try {
            const stats = {
                messageCount: this.messageCount,
                isRunning: this.isRunning,
                timestamp: Date.now(),
                redisConnected: this.redisClient?.isReady || false,
                publisherActive: this.publisher !== null
            };

            // 写入Redis用于监控
            await this.redisClient?.setEx('test:mock_reviewguard:stats', 60, JSON.stringify(stats));
            
            return stats;
        } catch (error) {
            console.error('❌ 获取统计信息失败:', error.message);
            return null;
        }
    }

    /**
     * 启动MockReviewGuard服务
     */
    async start() {
        try {
            console.log('🚀 启动MockReviewGuard服务...');
            
            await this.initializeRedis();
            await this.initializePublisher();
            
            // 等待一段时间确保其他服务启动
            console.log('⏳ 等待其他服务启动...');
            await new Promise(resolve => setTimeout(resolve, 10000));
            
            // 发布初始测试消息
            console.log('📤 发布初始测试消息...');
            await this.publishStrategyMessage('lowRisk');
            
            // 启动自动发布
            this.startAutoPublishing(30000); // 每30秒发布一次
            
            console.log('✅ MockReviewGuard服务启动完成');
            
            // 定期输出统计信息
            setInterval(async () => {
                const stats = await this.getStats();
                if (stats) {
                    console.log(`📊 统计信息: 已发布 ${stats.messageCount} 条消息`);
                }
            }, 60000); // 每分钟输出一次
            
        } catch (error) {
            console.error('❌ MockReviewGuard启动失败:', error.message);
            process.exit(1);
        }
    }

    /**
     * 停止服务
     */
    async stop() {
        try {
            console.log('⏹️ 停止MockReviewGuard服务...');
            
            this.stopAutoPublishing();
            
            if (this.publisher) {
                await this.publisher.close();
                this.publisher = null;
            }
            
            if (this.redisClient) {
                await this.redisClient.quit();
                this.redisClient = null;
            }
            
            console.log('✅ MockReviewGuard服务已停止');
        } catch (error) {
            console.error('❌ 停止服务时出错:', error.message);
        }
    }
}

// 启动服务
const mockReviewGuard = new MockReviewGuard();

// 处理进程退出
process.on('SIGINT', async () => {
    console.log('\n收到SIGINT信号，正在停止服务...');
    await mockReviewGuard.stop();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n收到SIGTERM信号，正在停止服务...');
    await mockReviewGuard.stop();
    process.exit(0);
});

// 启动服务
mockReviewGuard.start().catch(error => {
    console.error('❌ 服务启动失败:', error.message);
    process.exit(1);
});

module.exports = MockReviewGuard;