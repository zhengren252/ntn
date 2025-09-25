import { Router, Request, Response, NextFunction } from 'express';
import { traderService, StrategyPackageRequest, OrderRequest, RiskFinanceRequest } from '../services/traderService';
import { redisCache, CacheKeyType } from '../../../shared/cache/redis';
import { rateLimit } from 'express-rate-limit';

const router = Router();

// 速率限制配置
const createOrderLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 100, // 每分钟最多100个订单
  message: { error: '订单创建频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const strategyLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 20, // 每分钟最多20个策略操作
  message: { error: '策略操作频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const assessmentLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 10, // 每分钟最多10个风险评估请求
  message: { error: '风险评估请求频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

// 中间件：验证请求参数
const validateRequest = (requiredFields: string[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const missingFields = requiredFields.filter(field => {
      const value = req.body[field];
      return value === undefined || value === null || value === '';
    });
    
    if (missingFields.length > 0) {
      return res.status(400).json({
        success: false,
        error: `缺少必需字段: ${missingFields.join(', ')}`
      });
    }
    
    next();
  };
};

// 中间件：验证数字参数
const validateNumericParams = (numericFields: string[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const invalidFields = numericFields.filter(field => {
      const value = req.body[field];
      return value !== undefined && (isNaN(Number(value)) || Number(value) < 0);
    });
    
    if (invalidFields.length > 0) {
      return res.status(400).json({
        success: false,
        error: `无效的数字参数: ${invalidFields.join(', ')}`
      });
    }
    
    next();
  };
};

// 策略包管理路由

/**
 * @route POST /api/trader/strategy-packages
 * @desc 接收策略包
 * @access Private
 */
router.post('/strategy-packages',
  strategyLimit,
  validateRequest(['packageName', 'packageType', 'submittedBy']),
  async (req: Request, res: Response) => {
    try {
      const packageData: StrategyPackageRequest = {
        sessionId: Number(req.body.sessionId) || 1,
        packageName: req.body.packageName,
        strategyType: req.body.strategyType || 'momentum',
        parameters: req.body.parameters || {},
        riskLevel: req.body.riskLevel || 'medium',
        expectedReturn: Number(req.body.expectedReturn) || 0.1,
        maxPositionSize: Number(req.body.maxPositionSize) || 10000,
        stopLossPct: Number(req.body.stopLossPct) || 0.05,
        takeProfitPct: Number(req.body.takeProfitPct) || 0.15
      };

      const result = await traderService.receiveStrategyPackage(packageData);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: '策略包接收成功',
          data: {
            packageId: result.lastInsertId,
            receivedAt: new Date().toISOString()
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('接收策略包失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/trader/strategies
 * @desc 获取策略包列表
 * @access Private
 */
router.get('/strategies', async (req: Request, res: Response) => {
  try {
    const sessionId = req.query.sessionId ? Number(req.query.sessionId) : undefined;
    const strategies = await traderService.getStrategyPackages(sessionId);
    
    res.json({
      success: true,
      data: strategies,
      count: strategies.length
    });
  } catch (error) {
    console.error('获取策略包列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/trader/strategies/:id
 * @desc 获取策略包详情
 * @access Private
 */
router.get('/strategies/:id', async (req: Request, res: Response) => {
  try {
    const strategyId = Number(req.params.id);
    
    if (isNaN(strategyId)) {
      return res.status(400).json({
        success: false,
        error: '无效的策略ID'
      });
    }
    
    const performance = await traderService.getStrategyPerformance(strategyId);
    
    if (performance) {
      res.json({
        success: true,
        data: performance
      });
    } else {
      res.status(404).json({
        success: false,
        error: '策略不存在'
      });
    }
  } catch (error) {
    console.error('获取策略详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route POST /api/trader/strategies/:id/request
 * @desc 申请风险评估和资金
 * @access Private
 */
router.post('/strategies/:id/request',
  strategyLimit,
  validateRequest(['requestType']),
  async (req: Request, res: Response) => {
    try {
      const strategyId = Number(req.params.id);
      
      if (isNaN(strategyId)) {
        return res.status(400).json({
          success: false,
          error: '无效的策略ID'
        });
      }
      
      const request: RiskFinanceRequest = {
        strategyId,
        requestType: req.body.requestType,
        requestedAmount: req.body.requestedAmount ? Number(req.body.requestedAmount) : undefined,
        purpose: req.body.purpose,
        justification: req.body.justification
      };
      
      const result = await traderService.requestRiskAndFinance(request);
      
      if (result.success) {
        res.json({
          success: true,
          message: '申请已提交',
          data: result.data
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('申请风险评估和资金失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route POST /api/trader/risk-assessment
 * @desc 请求风险评估
 * @access Private
 */
router.post('/risk-assessment',
  assessmentLimit,
  validateRequest(['strategyId', 'assessmentType', 'requestedBy']),
  validateNumericParams(['strategyId']),
  async (req: Request, res: Response) => {
    try {
      const request = {
        strategyId: Number(req.body.strategyId),
        requestType: 'risk_assessment' as const,
        assessmentType: req.body.assessmentType,
        requestedBy: req.body.requestedBy,
        urgency: req.body.urgency || 'normal',
        additionalContext: req.body.additionalContext,
        riskParameters: req.body.riskParameters
      };

      const result = await traderService.requestRiskAssessment(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: '风险评估请求已提交',
          data: result.data
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('请求风险评估失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route POST /api/trader/fund-application
 * @desc 申请资金
 * @access Private
 */
router.post('/fund-application',
  assessmentLimit,
  validateRequest(['strategyId', 'requestedAmount', 'purpose', 'requestedBy']),
  validateNumericParams(['strategyId', 'requestedAmount']),
  async (req: Request, res: Response) => {
    try {
      const request = {
        strategyId: Number(req.body.strategyId),
        requestType: 'budget_application' as const,
        requestedAmount: Number(req.body.requestedAmount),
        purpose: req.body.purpose,
        justification: req.body.justification
      };

      const result = await traderService.requestFunding(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: '资金申请已提交',
          data: result.data
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('申请资金失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

// 订单管理路由

/**
 * @route POST /api/trader/orders
 * @desc 创建订单
 * @access Private
 */
router.post('/orders',
  createOrderLimit,
  validateRequest(['strategyId', 'symbol', 'orderType', 'side', 'quantity', 'timeInForce', 'orderSource']),
  validateNumericParams(['strategyId', 'quantity', 'price', 'stopPrice']),
  async (req: Request, res: Response) => {
    try {
      const request: OrderRequest = {
        strategyId: Number(req.body.strategyId),
        symbol: req.body.symbol,
        orderType: req.body.orderType,
        side: req.body.side,
        quantity: Number(req.body.quantity),
        price: req.body.price ? Number(req.body.price) : undefined,
        stopPrice: req.body.stopPrice ? Number(req.body.stopPrice) : undefined,
        timeInForce: req.body.timeInForce,
        orderSource: req.body.orderSource
      };
      
      const result = await traderService.createOrder(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: '订单创建成功',
          data: {
            orderId: result.orderId,
            symbol: request.symbol,
            side: request.side,
            quantity: request.quantity,
            status: result.status,
            riskCheckPassed: result.riskCheckPassed
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('创建订单失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/trader/orders
 * @desc 获取订单列表
 * @access Private
 */
router.get('/orders', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const orders = await traderService.getOrders(strategyId);
    
    res.json({
      success: true,
      data: orders,
      count: orders.length
    });
  } catch (error) {
    console.error('获取订单列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route DELETE /api/trader/orders/:id
 * @desc 取消订单
 * @access Private
 */
router.delete('/orders/:id', async (req: Request, res: Response) => {
  try {
    const orderId = Number(req.params.id);
    const reason = req.body.reason || 'User cancelled';
    
    if (isNaN(orderId)) {
      return res.status(400).json({
        success: false,
        error: '无效的订单ID'
      });
    }
    
    const result = await traderService.cancelOrder(orderId, reason);
    
    if (result.success) {
      res.json({
        success: true,
        message: '订单取消成功',
        data: {
          orderId,
          reason
        }
      });
    } else {
      res.status(400).json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('取消订单失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 实时数据路由

/**
 * @route GET /api/trader/realtime/strategies
 * @desc 获取实时策略状态
 * @access Private
 */
router.get('/realtime/strategies', async (req: Request, res: Response) => {
  try {
    const strategies = await traderService.getStrategyPackages();
    const realTimeData = [];
    
    for (const strategy of strategies) {
      // 从缓存获取实时状态
      const statusCache = await redisCache.get(CacheKeyType.STRATEGY_STATE, `status_${strategy.id}`);
      const performanceCache = await redisCache.get(CacheKeyType.STRATEGY_STATE, `performance_${strategy.id}`);
      
      realTimeData.push({
        id: strategy.id,
        packageName: strategy.package_name,
        status: strategy.status,
        riskLevel: strategy.risk_level,
        realTimeStatus: statusCache,
        performance: performanceCache,
        lastUpdate: new Date().toISOString()
      });
    }
    
    res.json({
      success: true,
      data: realTimeData,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('获取实时策略状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/trader/realtime/orders
 * @desc 获取实时订单状态
 * @access Private
 */
router.get('/realtime/orders', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const orders = await traderService.getOrders(strategyId);
    const realTimeData = [];
    
    for (const order of orders) {
      // 从缓存获取实时状态
      const orderCache = await redisCache.get(CacheKeyType.TRADING_DATA, `order_${order.id}`);
      
      realTimeData.push({
        ...order,
        realTimeData: orderCache,
        lastUpdate: new Date().toISOString()
      });
    }
    
    res.json({
      success: true,
      data: realTimeData,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('获取实时订单状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 统计和分析路由

/**
 * @route GET /api/trader/stats/overview
 * @desc 获取交易员模组概览统计
 * @access Private
 */
router.get('/stats/overview', async (req: Request, res: Response) => {
  try {
    const strategies = await traderService.getStrategyPackages();
    const orders = await traderService.getOrders();
    
    // 策略统计
    const strategyStats = {
      total: strategies.length,
      active: strategies.filter(s => s.status === 'active').length,
      pending: strategies.filter(s => s.status === 'pending').length,
      paused: strategies.filter(s => s.status === 'paused').length,
      rejected: strategies.filter(s => s.status === 'rejected').length
    };
    
    // 订单统计
    const orderStats = {
      total: orders.length,
      pending: orders.filter(o => o.status === 'pending').length,
      filled: orders.filter(o => o.status === 'filled').length,
      cancelled: orders.filter(o => o.status === 'cancelled').length,
      rejected: orders.filter(o => o.status === 'rejected').length
    };
    
    // 风险等级分布
    const riskDistribution = {
      low: strategies.filter(s => s.risk_level === 'low').length,
      medium: strategies.filter(s => s.risk_level === 'medium').length,
      high: strategies.filter(s => s.risk_level === 'high').length
    };
    
    // 今日订单
    const today = new Date().toISOString().split('T')[0];
    const todayOrders = orders.filter(o => o.created_at?.startsWith(today));
    
    res.json({
      success: true,
      data: {
        strategies: strategyStats,
        orders: orderStats,
        riskDistribution,
        todayOrders: todayOrders.length,
        lastUpdate: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('获取概览统计失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/trader/stats/performance
 * @desc 获取性能统计
 * @access Private
 */
router.get('/stats/performance', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    
    if (strategyId) {
      // 获取特定策略的性能
      const performance = await traderService.getStrategyPerformance(strategyId);
      res.json({
        success: true,
        data: performance
      });
    } else {
      // 获取所有策略的汇总性能
      const strategies = await traderService.getStrategyPackages();
      const performanceData = [];
      
      for (const strategy of strategies) {
        const performance = await traderService.getStrategyPerformance(strategy.id);
        if (performance) {
          performanceData.push({
            strategyId: strategy.id,
            packageName: strategy.package_name,
            performance
          });
        }
      }
      
      res.json({
        success: true,
        data: performanceData,
        count: performanceData.length
      });
    }
  } catch (error) {
    console.error('获取性能统计失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 健康检查路由

/**
 * @route GET /api/trader/health
 * @desc 交易员模组健康检查
 * @access Public
 */
router.get('/health', async (req: Request, res: Response) => {
  try {
    // 检查数据库连接
    const strategies = await traderService.getStrategyPackages();
    
    // 检查缓存连接
    const cacheStatus = await redisCache.ping();
    
    res.json({
      success: true,
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'connected',
        cache: cacheStatus ? 'connected' : 'disconnected',
        strategiesCount: strategies.length
      }
    });
  } catch (error) {
    console.error('健康检查失败:', error);
    res.status(503).json({
      success: false,
      status: 'unhealthy',
      error: error instanceof Error ? error.message : '未知错误',
      timestamp: new Date().toISOString()
    });
  }
});

export default router;
export { router as traderRoutes };