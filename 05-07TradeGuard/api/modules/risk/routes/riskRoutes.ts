import { Router, Request, Response, NextFunction } from 'express';
import { riskService, RiskAssessmentRequest, RiskAlertRequest } from '../services/riskService';
import { riskAssessmentDAO, riskAlertDAO } from '../dao/riskDAO';
import { redisCache, CacheKeyType } from '../../../shared/cache/redis';
import rateLimit from 'express-rate-limit';

const router = Router();

// 速率限制配置
const assessmentLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 10, // 每分钟最多10次风险评估
  message: { error: '风险评估请求频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const alertLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 50, // 每分钟最多50次警报操作
  message: { error: '警报操作频率过高，请稍后再试' },
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

// 风险评估路由

/**
 * @route POST /api/risk/assessments
 * @desc 执行风险评估
 * @access Private
 */
router.post('/assessments',
  assessmentLimit,
  validateRequest(['strategyId', 'assessmentType', 'assessedBy']),
  validateNumericParams(['strategyId']),
  async (req: Request, res: Response) => {
    try {
      const request: RiskAssessmentRequest = {
        strategyId: Number(req.body.strategyId),
        assessmentType: req.body.assessmentType,
        triggerReason: req.body.triggerReason,
        assessedBy: req.body.assessedBy,
        forceReassessment: req.body.forceReassessment === true
      };

      const result = await riskService.performRiskAssessment(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: '风险评估完成',
          data: result.data
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('执行风险评估失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/risk/assessments
 * @desc 获取风险评估列表
 * @access Private
 */
router.get('/assessments', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const status = req.query.status as string;
    const riskLevel = req.query.riskLevel as string;
    
    let assessments;
    
    if (status) {
      assessments = riskAssessmentDAO.findByStatus(status);
    } else if (riskLevel) {
      assessments = riskAssessmentDAO.findByRiskLevel(riskLevel);
    } else {
      assessments = await riskService.getRiskAssessments(strategyId);
    }
    
    res.json({
      success: true,
      data: assessments,
      count: assessments.length
    });
  } catch (error) {
    console.error('获取风险评估列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/risk/assessments/:id
 * @desc 获取风险评估详情
 * @access Private
 */
router.get('/assessments/:id', async (req: Request, res: Response) => {
  try {
    const assessmentId = Number(req.params.id);
    
    if (isNaN(assessmentId)) {
      return res.status(400).json({
        success: false,
        error: '无效的评估ID'
      });
    }
    
    const assessment = riskAssessmentDAO.findById(assessmentId);
    
    if (assessment) {
      // 解析JSON字段
      const result = {
        ...assessment,
        recommendations: assessment.recommendations ? JSON.parse(assessment.recommendations) : null
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '风险评估不存在'
      });
    }
  } catch (error) {
    console.error('获取风险评估详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/risk/assessments/:id/status
 * @desc 更新风险评估状态
 * @access Private
 */
router.put('/assessments/:id/status',
  validateRequest(['status']),
  async (req: Request, res: Response) => {
    try {
      const assessmentId = Number(req.params.id);
      const { status, reviewNotes } = req.body;
      
      if (isNaN(assessmentId)) {
        return res.status(400).json({
          success: false,
          error: '无效的评估ID'
        });
      }
      
      const success = riskAssessmentDAO.updateStatus(assessmentId, status, reviewNotes);
      
      if (success) {
        res.json({
          success: true,
          message: '评估状态更新成功'
        });
      } else {
        res.status(404).json({
          success: false,
          error: '风险评估不存在或更新失败'
        });
      }
    } catch (error) {
      console.error('更新风险评估状态失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

// 风险警报路由

/**
 * @route POST /api/risk/alerts
 * @desc 创建风险警报
 * @access Private
 */
router.post('/alerts',
  alertLimit,
  validateRequest(['alertType', 'severity', 'message', 'triggeredBy']),
  async (req: Request, res: Response) => {
    try {
      const request: RiskAlertRequest = {
        strategyId: req.body.strategyId ? Number(req.body.strategyId) : undefined,
        alertType: req.body.alertType,
        severity: req.body.severity,
        message: req.body.message,
        details: req.body.details,
        triggeredBy: req.body.triggeredBy,
        autoResolve: req.body.autoResolve === true
      };
      
      const result = await riskService.createRiskAlert(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: '风险警报创建成功',
          data: {
            alertId: result.lastInsertId,
            alertType: request.alertType,
            severity: request.severity,
            timestamp: new Date().toISOString(),
            status: 'active'
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('创建风险警报失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/risk/alerts
 * @desc 获取风险警报列表
 * @access Private
 */
router.get('/alerts', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const alertType = req.query.alertType as string;
    const severity = req.query.severity as string;
    const status = req.query.status as string;
    const acknowledged = req.query.acknowledged;
    
    let alerts;
    
    if (status === 'active') {
      alerts = riskAlertDAO.findActiveAlerts();
    } else if (acknowledged === 'false') {
      alerts = riskAlertDAO.findUnacknowledgedAlerts();
    } else if (severity === 'critical') {
      alerts = riskAlertDAO.findCriticalAlerts();
    } else if (alertType) {
      alerts = riskAlertDAO.findByAlertType(alertType);
    } else if (severity) {
      alerts = riskAlertDAO.findBySeverity(severity);
    } else {
      alerts = await riskService.getRiskAlerts(strategyId);
    }
    
    res.json({
      success: true,
      data: alerts,
      count: alerts.length
    });
  } catch (error) {
    console.error('获取风险警报列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/risk/alerts/:id
 * @desc 获取风险警报详情
 * @access Private
 */
router.get('/alerts/:id', async (req: Request, res: Response) => {
  try {
    const alertId = Number(req.params.id);
    
    if (isNaN(alertId)) {
      return res.status(400).json({
        success: false,
        error: '无效的警报ID'
      });
    }
    
    const alert = riskAlertDAO.findById(alertId);
    
    if (alert) {
      // 返回警报详情
      const result = {
        ...alert
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '风险警报不存在'
      });
    }
  } catch (error) {
    console.error('获取风险警报详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/risk/alerts/:id/acknowledge
 * @desc 确认风险警报
 * @access Private
 */
router.put('/alerts/:id/acknowledge',
  validateRequest(['acknowledgedBy']),
  async (req: Request, res: Response) => {
    try {
      const alertId = Number(req.params.id);
      const { acknowledgedBy, notes } = req.body;
      
      if (isNaN(alertId)) {
        return res.status(400).json({
          success: false,
          error: '无效的警报ID'
        });
      }
      
      const result = await riskService.acknowledgeAlert(alertId, acknowledgedBy, notes);
      
      if (result.success) {
        res.json({
          success: true,
          message: '警报确认成功'
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error || '确认失败'
        });
      }
    } catch (error) {
      console.error('确认风险警报失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/risk/alerts/:id/resolve
 * @desc 解决风险警报
 * @access Private
 */
router.put('/alerts/:id/resolve',
  validateRequest(['resolvedBy', 'resolutionNotes']),
  async (req: Request, res: Response) => {
    try {
      const alertId = Number(req.params.id);
      const { resolvedBy, resolutionNotes } = req.body;
      
      if (isNaN(alertId)) {
        return res.status(400).json({
          success: false,
          error: '无效的警报ID'
        });
      }
      
      const result = await riskService.resolveAlert(alertId, resolvedBy, resolutionNotes);
      
      if (result.success) {
        res.json({
          success: true,
          message: '警报解决成功'
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error || '解决失败'
        });
      }
    } catch (error) {
      console.error('解决风险警报失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/risk/alerts/batch/acknowledge
 * @desc 批量确认风险警报
 * @access Private
 */
router.put('/alerts/batch/acknowledge',
  validateRequest(['alertIds', 'acknowledgedBy']),
  async (req: Request, res: Response) => {
    try {
      const { alertIds, acknowledgedBy } = req.body;
      
      if (!Array.isArray(alertIds) || alertIds.length === 0) {
        return res.status(400).json({
          success: false,
          error: '警报ID列表不能为空'
        });
      }
      
      const numericIds = alertIds.map(id => Number(id)).filter(id => !isNaN(id));
      
      if (numericIds.length !== alertIds.length) {
        return res.status(400).json({
          success: false,
          error: '包含无效的警报ID'
        });
      }
      
      const updatedCount = riskAlertDAO.batchAcknowledgeAlerts(numericIds, acknowledgedBy);
      
      res.json({
        success: true,
        message: `成功确认${updatedCount}个警报`,
        data: {
          updatedCount,
          totalRequested: alertIds.length
        }
      });
    } catch (error) {
      console.error('批量确认风险警报失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

// 风险指标路由

/**
 * @route GET /api/risk/metrics/realtime
 * @desc 获取实时风险指标
 * @access Private
 */
router.get('/metrics/realtime', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    
    const metrics = await riskService.getRealTimeRiskMetrics(strategyId);
    
    if (metrics) {
      res.json({
        success: true,
        data: metrics,
        timestamp: new Date().toISOString()
      });
    } else {
      res.status(404).json({
        success: false,
        error: '风险指标不存在'
      });
    }
  } catch (error) {
    console.error('获取实时风险指标失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/risk/metrics/history/:strategyId
 * @desc 获取策略风险历史
 * @access Private
 */
router.get('/metrics/history/:strategyId', async (req: Request, res: Response) => {
  try {
    const strategyId = Number(req.params.strategyId);
    const days = req.query.days ? Number(req.query.days) : 30;
    
    if (isNaN(strategyId)) {
      return res.status(400).json({
        success: false,
        error: '无效的策略ID'
      });
    }
    
    const riskHistory = riskAssessmentDAO.getStrategyRiskHistory(strategyId, days);
    const alertHistory = riskAlertDAO.getStrategyAlertHistory(strategyId, days);
    
    res.json({
      success: true,
      data: {
        strategyId,
        period: `${days}天`,
        riskAssessments: riskHistory,
        alerts: alertHistory
      }
    });
  } catch (error) {
    console.error('获取策略风险历史失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 统计和分析路由

/**
 * @route GET /api/risk/stats/overview
 * @desc 获取风控模组概览统计
 * @access Private
 */
router.get('/stats/overview', async (req: Request, res: Response) => {
  try {
    const stats = await riskService.getRiskStatistics();
    
    if (stats) {
      res.json({
        success: true,
        data: stats
      });
    } else {
      res.status(500).json({
        success: false,
        error: '获取统计数据失败'
      });
    }
  } catch (error) {
    console.error('获取风控概览统计失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/risk/stats/dashboard
 * @desc 获取风控仪表板数据
 * @access Private
 */
router.get('/stats/dashboard', async (req: Request, res: Response) => {
  try {
    // 获取活跃警报
    const activeAlerts = riskAlertDAO.findActiveAlerts();
    const unacknowledgedAlerts = riskAlertDAO.findUnacknowledgedAlerts();
    const criticalAlerts = riskAlertDAO.findCriticalAlerts();
    
    // 获取待审批评估
    const pendingAssessments = riskAssessmentDAO.findPendingAssessments();
    const highRiskAssessments = riskAssessmentDAO.findHighRiskAssessments();
    
    // 获取统计数据
    const alertStats = riskAlertDAO.getAlertStats();
    const assessmentStats = riskAssessmentDAO.getRiskAssessmentStats();
    const alertTrend = riskAlertDAO.getAlertTrend(7);
    
    // 获取实时风险指标
    const portfolioMetrics = await riskService.getRealTimeRiskMetrics();
    
    res.json({
      success: true,
      data: {
        alerts: {
          active: activeAlerts.length,
          unacknowledged: unacknowledgedAlerts.length,
          critical: criticalAlerts.length,
          recentAlerts: activeAlerts.slice(0, 10), // 最近10个活跃警报
          stats: alertStats,
          trend: alertTrend
        },
        assessments: {
          pending: pendingAssessments.length,
          highRisk: highRiskAssessments.length,
          recentAssessments: pendingAssessments.slice(0, 5), // 最近5个待审批评估
          stats: assessmentStats
        },
        portfolio: portfolioMetrics,
        lastUpdate: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('获取风控仪表板数据失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 配置管理路由

/**
 * @route GET /api/risk/config
 * @desc 获取风控配置
 * @access Private
 */
router.get('/config', async (req: Request, res: Response) => {
  try {
    // 从缓存获取配置
    const config = await redisCache.get(CacheKeyType.SYSTEM_CONFIG, 'risk_config');
    
    if (config) {
      res.json({
        success: true,
        data: config
      });
    } else {
      // 返回默认配置
      res.json({
        success: true,
        data: {
          riskWeights: {
            positionSize: 0.20,
            volatility: 0.15,
            correlation: 0.10,
            liquidity: 0.10,
            drawdown: 0.15,
            sharpeRatio: 0.10,
            orderSuccess: 0.10,
            riskAdjustedReturn: 0.10
          },
          riskLimits: {
            maxPositionSize: 1000000,
            maxDailyLoss: 50000,
            maxDrawdown: 0.20,
            maxLeverage: 3.0,
            maxConcentration: 0.30,
            volatilityThreshold: 0.25,
            correlationThreshold: 0.80
          },
          monitoringInterval: 30000,
          alertRetention: 90
        }
      });
    }
  } catch (error) {
    console.error('获取风控配置失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/risk/config
 * @desc 更新风控配置
 * @access Private
 */
router.put('/config', async (req: Request, res: Response) => {
  try {
    const { riskWeights, riskLimits, monitoringInterval, alertRetention } = req.body;
    
    // 更新服务配置
    riskService.updateRiskConfiguration(riskWeights, riskLimits);
    
    // 保存到缓存
    const config = {
      riskWeights,
      riskLimits,
      monitoringInterval,
      alertRetention,
      updatedAt: new Date().toISOString()
    };
    
    await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'risk_config', config);
    
    res.json({
      success: true,
      message: '风控配置更新成功',
      data: config
    });
  } catch (error) {
    console.error('更新风控配置失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 监控控制路由

/**
 * @route POST /api/risk/monitoring/start
 * @desc 启动实时监控
 * @access Private
 */
router.post('/monitoring/start', async (req: Request, res: Response) => {
  try {
    const intervalMs = req.body.intervalMs || 30000;
    
    riskService.startRealTimeMonitoring(intervalMs);
    
    res.json({
      success: true,
      message: '实时监控已启动',
      data: {
        intervalMs
      }
    });
  } catch (error) {
    console.error('启动实时监控失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route POST /api/risk/monitoring/stop
 * @desc 停止实时监控
 * @access Private
 */
router.post('/monitoring/stop', async (req: Request, res: Response) => {
  try {
    riskService.stopRealTimeMonitoring();
    
    res.json({
      success: true,
      message: '实时监控已停止'
    });
  } catch (error) {
    console.error('停止实时监控失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 健康检查路由

/**
 * @route GET /api/risk/health
 * @desc 风控模组健康检查
 * @access Public
 */
router.get('/health', async (req: Request, res: Response) => {
  try {
    // 检查数据库连接
    const assessments = await riskService.getRiskAssessments();
    const alerts = await riskService.getRiskAlerts();
    
    // 检查缓存连接
    const cacheStatus = await redisCache.ping();
    
    res.json({
      success: true,
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'connected',
        cache: cacheStatus ? 'connected' : 'disconnected',
        assessmentsCount: assessments.length,
        alertsCount: alerts.length
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
export { router as riskRoutes };