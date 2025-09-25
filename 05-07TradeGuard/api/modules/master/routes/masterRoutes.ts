import { Router, Request, Response, NextFunction } from 'express';
import { masterService, EmergencyControlRequest } from '../services/masterService';
import { systemMonitorDAO, systemConfigDAO } from '../dao/masterDAO';
import { redisCache, CacheKeyType } from '../../../shared/cache/redis';
import rateLimit from 'express-rate-limit';

const router = Router();

// 速率限制配置
const emergencyLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 3, // 每分钟最多3次紧急控制操作
  message: { error: '紧急控制操作频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const configLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 10, // 每分钟最多10次配置操作
  message: { error: '配置操作频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const monitoringLimit = rateLimit({
  windowMs: 10 * 1000, // 10秒
  max: 30, // 每10秒最多30次监控查询
  message: { error: '监控查询频率过高，请稍后再试' },
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

// 中间件：验证紧急控制权限
const validateEmergencyAccess = (req: Request, res: Response, next: NextFunction) => {
  // 这里可以添加权限验证逻辑
  // 例如：检查用户角色、API密钥等
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({
      success: false,
      error: '缺少授权信息'
    });
  }
  
  // 简单的权限检查示例
  // 实际应用中应该有更严格的权限验证
  next();
};

// 系统监控路由

/**
 * @route GET /api/master/overview
 * @desc 获取系统概览
 * @access Private
 */
router.get('/overview', monitoringLimit, async (req: Request, res: Response) => {
  try {
    const overview = await masterService.getSystemOverview();
    
    res.json({
      success: true,
      data: overview
    });
  } catch (error) {
    console.error('获取系统概览失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/health
 * @desc 获取系统健康状态
 * @access Private
 */
router.get('/health', async (req: Request, res: Response) => {
  try {
    // 尝试从缓存获取健康数据
    const cachedHealth = await redisCache.get(CacheKeyType.SYSTEM_CONFIG, 'health');
    
    if (cachedHealth) {
      res.json({
        success: true,
        data: cachedHealth,
        cached: true
      });
    } else {
      // 如果缓存中没有，执行健康检查
      const healthData = await masterService.getSystemOverview();
      
      res.json({
        success: true,
        data: (healthData as any).health,
        cached: false
      });
    }
  } catch (error) {
    console.error('获取系统健康状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/modules
 * @desc 获取模组状态列表
 * @access Private
 */
router.get('/modules', monitoringLimit, async (req: Request, res: Response) => {
  try {
    const status = req.query.status as string;
    
    let modules;
    if (status === 'unhealthy') {
      modules = systemMonitorDAO.getUnhealthyModules();
    } else {
      modules = systemMonitorDAO.getAllModuleStatus();
    }
    
    res.json({
      success: true,
      data: modules,
      count: modules.length
    });
  } catch (error) {
    console.error('获取模组状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/modules/:moduleName
 * @desc 获取特定模组状态
 * @access Private
 */
router.get('/modules/:moduleName', async (req: Request, res: Response) => {
  try {
    const moduleName = req.params.moduleName;
    const module = systemMonitorDAO.getModuleStatus(moduleName);
    
    if (module) {
      // 解析JSON字段
      const result = {
        ...module,
        metadata: (module as any).metadata ? JSON.parse((module as any).metadata) : null
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '模组不存在'
      });
    }
  } catch (error) {
    console.error('获取模组状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/metrics
 * @desc 获取性能指标
 * @access Private
 */
router.get('/metrics', monitoringLimit, async (req: Request, res: Response) => {
  try {
    const moduleName = req.query.moduleName as string;
    const metricType = req.query.metricType as string;
    const hours = req.query.hours ? Number(req.query.hours) : 24;
    
    if (hours > 168) { // 最多7天
      return res.status(400).json({
        success: false,
        error: '时间范围不能超过7天'
      });
    }
    
    const metrics = systemMonitorDAO.getPerformanceMetrics(moduleName, metricType, hours);
    
    res.json({
      success: true,
      data: metrics,
      count: metrics.length,
      timeRange: `${hours} hours`
    });
  } catch (error) {
    console.error('获取性能指标失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/metrics/stats/:moduleName/:metricName
 * @desc 获取性能指标统计
 * @access Private
 */
router.get('/metrics/stats/:moduleName/:metricName', async (req: Request, res: Response) => {
  try {
    const { moduleName, metricName } = req.params;
    const hours = req.query.hours ? Number(req.query.hours) : 24;
    
    const stats = systemMonitorDAO.getPerformanceStats(moduleName, metricName, hours);
    
    if (stats) {
      res.json({
        success: true,
        data: stats
      });
    } else {
      res.status(404).json({
        success: false,
        error: '未找到指标统计数据'
      });
    }
  } catch (error) {
    console.error('获取性能指标统计失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 事件和警报路由

/**
 * @route GET /api/master/events
 * @desc 获取系统事件列表
 * @access Private
 */
router.get('/events', monitoringLimit, async (req: Request, res: Response) => {
  try {
    const filters = {
      eventType: req.query.eventType as string,
      severity: req.query.severity as string,
      sourceModule: req.query.sourceModule as string,
      resolved: req.query.resolved ? req.query.resolved === 'true' : undefined,
      hours: req.query.hours ? Number(req.query.hours) : undefined
    };
    
    const limit = req.query.limit ? Number(req.query.limit) : 100;
    
    if (limit > 500) {
      return res.status(400).json({
        success: false,
        error: '限制数量不能超过500'
      });
    }
    
    const events = systemMonitorDAO.getSystemEvents(filters, limit);
    
    res.json({
      success: true,
      data: events,
      count: events.length,
      filters
    });
  } catch (error) {
    console.error('获取系统事件失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/master/events/:eventId/resolve
 * @desc 解决系统事件
 * @access Private
 */
router.put('/events/:eventId/resolve',
  validateRequest(['resolvedBy']),
  async (req: Request, res: Response) => {
    try {
      const eventId = Number(req.params.eventId);
      const { resolvedBy } = req.body;
      
      if (isNaN(eventId)) {
        return res.status(400).json({
          success: false,
          error: '无效的事件ID'
        });
      }
      
      const success = systemMonitorDAO.resolveSystemEvent(eventId, resolvedBy);
      
      if (success) {
        res.json({
          success: true,
          message: '事件已解决'
        });
      } else {
        res.status(404).json({
          success: false,
          error: '事件不存在或已解决'
        });
      }
    } catch (error) {
      console.error('解决系统事件失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/master/events/stats
 * @desc 获取事件统计
 * @access Private
 */
router.get('/events/stats', async (req: Request, res: Response) => {
  try {
    const hours = req.query.hours ? Number(req.query.hours) : 24;
    
    if (hours > 168) {
      return res.status(400).json({
        success: false,
        error: '时间范围不能超过7天'
      });
    }
    
    const stats = systemMonitorDAO.getEventStatistics(hours);
    
    res.json({
      success: true,
      data: stats,
      timeRange: `${hours} hours`
    });
  } catch (error) {
    console.error('获取事件统计失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 紧急控制路由

/**
 * @route POST /api/master/emergency/control
 * @desc 执行紧急控制操作
 * @access Private
 */
router.post('/emergency/control',
  emergencyLimit,
  validateEmergencyAccess,
  validateRequest(['action', 'scope', 'reason', 'severity', 'initiatedBy']),
  async (req: Request, res: Response) => {
    try {
      const request: EmergencyControlRequest = {
        action: req.body.action,
        scope: req.body.scope,
        targetId: req.body.targetId,
        reason: req.body.reason,
        severity: req.body.severity,
        initiatedBy: req.body.initiatedBy,
        metadata: req.body.metadata
      };

      // 验证参数
      if (!['stop', 'pause', 'resume', 'restart'].includes(request.action)) {
        return res.status(400).json({
          success: false,
          error: '无效的控制动作'
        });
      }

      if (!['system', 'module', 'strategy'].includes(request.scope)) {
        return res.status(400).json({
          success: false,
          error: '无效的控制范围'
        });
      }

      if (!['low', 'medium', 'high', 'critical'].includes(request.severity)) {
        return res.status(400).json({
          success: false,
          error: '无效的严重程度'
        });
      }

      if ((request.scope === 'module' || request.scope === 'strategy') && !request.targetId) {
        return res.status(400).json({
          success: false,
          error: '指定模组或策略时必须提供目标ID'
        });
      }

      const result = await masterService.handleEmergencyControlRequest(request);
      
      if (result.success) {
        res.status(200).json({
          success: true,
          message: result.message,
          data: {
            eventId: result.eventId,
            timestamp: result.timestamp
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error || result.message
        });
      }
    } catch (error) {
      console.error('执行紧急控制操作失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/master/emergency/status
 * @desc 获取紧急状态
 * @access Private
 */
router.get('/emergency/status', async (req: Request, res: Response) => {
  try {
    // 从缓存获取紧急停止状态
    const emergencyStatus = await redisCache.get(CacheKeyType.SYSTEM_CONFIG, 'emergency_stop');
    
    // 从配置获取紧急停止开关
    const emergencyConfig = systemConfigDAO.getConfig('system.emergency_stop_enabled');
    
    res.json({
      success: true,
      data: {
        emergencyStopActive: emergencyConfig?.config_value || false,
        emergencyStatus: emergencyStatus || null,
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('获取紧急状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 配置管理路由

/**
 * @route GET /api/master/config
 * @desc 获取系统配置
 * @access Private
 */
router.get('/config', async (req: Request, res: Response) => {
  try {
    const category = req.query.category as string;
    const configs = systemConfigDAO.getAllConfigs(category);
    
    // 过滤敏感配置
    const filteredConfigs = configs.map(config => {
      if (config.is_sensitive) {
        return {
          ...config,
          config_value: '***HIDDEN***'
        };
      }
      return config;
    });
    
    res.json({
      success: true,
      data: filteredConfigs,
      count: filteredConfigs.length
    });
  } catch (error) {
    console.error('获取系统配置失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/config/:key
 * @desc 获取特定配置项
 * @access Private
 */
router.get('/config/:key', async (req: Request, res: Response) => {
  try {
    const key = req.params.key;
    const config = systemConfigDAO.getConfig(key);
    
    if (config) {
      // 检查是否为敏感配置
      if (config.is_sensitive) {
        config.config_value = '***HIDDEN***';
      }
      
      res.json({
        success: true,
        data: config
      });
    } else {
      res.status(404).json({
        success: false,
        error: '配置项不存在'
      });
    }
  } catch (error) {
    console.error('获取配置项失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/master/config/:key
 * @desc 更新配置项
 * @access Private
 */
router.put('/config/:key',
  configLimit,
  validateRequest(['value', 'updatedBy']),
  async (req: Request, res: Response) => {
    try {
      const key = req.params.key;
      const { value, updatedBy, reason } = req.body;
      
      const success = systemConfigDAO.updateConfig(key, value, updatedBy, reason);
      
      if (success) {
        // 通知配置更新
        await masterService.updateConfiguration({ [key]: value });
        
        res.json({
          success: true,
          message: '配置更新成功'
        });
      } else {
        res.status(400).json({
          success: false,
          error: '配置更新失败，请检查配置项是否存在或是否为只读'
        });
      }
    } catch (error) {
      console.error('更新配置项失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/master/config/:key/history
 * @desc 获取配置变更历史
 * @access Private
 */
router.get('/config/:key/history', async (req: Request, res: Response) => {
  try {
    const key = req.params.key;
    const limit = req.query.limit ? Number(req.query.limit) : 50;
    
    if (limit > 200) {
      return res.status(400).json({
        success: false,
        error: '限制数量不能超过200'
      });
    }
    
    const history = systemConfigDAO.getConfigHistory(key, limit);
    
    res.json({
      success: true,
      data: history,
      count: history.length
    });
  } catch (error) {
    console.error('获取配置变更历史失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 仪表板和统计路由

/**
 * @route GET /api/master/dashboard
 * @desc 获取总控仪表板数据
 * @access Private
 */
router.get('/dashboard', monitoringLimit, async (req: Request, res: Response) => {
  try {
    // 获取系统概览
    const overview = await masterService.getSystemOverview();
    
    // 获取最新性能指标
    const latestMetrics = await redisCache.get(CacheKeyType.SYSTEM_CONFIG, 'metrics');
    
    // 获取异常模组
    const unhealthyModules = systemMonitorDAO.getUnhealthyModules();
    
    // 获取未解决的事件
    const unresolvedEvents = systemMonitorDAO.getSystemEvents({ resolved: false }, 20);
    
    // 获取事件统计
    const eventStats = systemMonitorDAO.getEventStatistics(24);
    
    res.json({
      success: true,
      data: {
        overview: {
          health: (overview as any).health,
          emergencyStop: (overview as any).emergencyStop,
          uptime: (overview as any).uptime
        },
        modules: {
          total: (overview as any).modules.length,
          healthy: (overview as any).modules.filter((m: any) => m.status === 'healthy').length,
          unhealthy: unhealthyModules.length,
          unhealthyList: unhealthyModules.slice(0, 5)
        },
        metrics: latestMetrics || null,
        events: {
          unresolved: unresolvedEvents.length,
          recentUnresolved: unresolvedEvents.slice(0, 10),
          statistics: eventStats
        },
        lastUpdate: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('获取仪表板数据失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/master/status
 * @desc 获取总控服务状态
 * @access Private
 */
router.get('/status', async (req: Request, res: Response) => {
  try {
    const status = masterService.getStatus();
    
    res.json({
      success: true,
      data: status
    });
  } catch (error) {
    console.error('获取服务状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 维护操作路由

/**
 * @route POST /api/master/maintenance/cleanup
 * @desc 执行数据清理
 * @access Private
 */
router.post('/maintenance/cleanup',
  validateEmergencyAccess,
  async (req: Request, res: Response) => {
    try {
      const retentionDays = req.body.retentionDays || 30;
      
      if (retentionDays < 1 || retentionDays > 365) {
        return res.status(400).json({
          success: false,
          error: '保留天数必须在1-365之间'
        });
      }
      
      const cleanedCount = systemMonitorDAO.cleanupOldData(retentionDays);
      
      // 记录维护事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'maintenance',
        event_category: 'system',
        severity: 'info',
        source_module: 'master',
        title: '数据清理完成',
        description: `清理了 ${cleanedCount} 条过期数据`,
        event_data: { retentionDays, cleanedCount },
        user_id: req.body.initiatedBy || 'system'
      });
      
      res.json({
        success: true,
        message: '数据清理完成',
        data: {
          cleanedCount,
          retentionDays
        }
      });
    } catch (error) {
      console.error('执行数据清理失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

// 健康检查路由

/**
 * @route GET /api/master/healthcheck
 * @desc 总控模组健康检查
 * @access Public
 */
router.get('/healthcheck', async (req: Request, res: Response) => {
  try {
    // 检查服务状态
    const serviceStatus = masterService.getStatus();
    
    // 检查数据库连接
    const modules = systemMonitorDAO.getAllModuleStatus();
    
    // 检查缓存连接
    const cacheStatus = await redisCache.ping();
    
    res.json({
      success: true,
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        service: (serviceStatus as any).initialized ? 'healthy' : 'unhealthy',
        database: 'connected',
        cache: cacheStatus ? 'connected' : 'disconnected',
        emergencyStop: (serviceStatus as any).emergencyStopActive,
        uptime: (serviceStatus as any).uptime,
        moduleCount: modules.length
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
export { router as masterRoutes };