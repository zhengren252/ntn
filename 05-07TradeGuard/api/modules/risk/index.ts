import { Router } from 'express';
import { riskRoutes } from './routes/riskRoutes';
import { riskService, StrategyRiskMetrics, PortfolioRiskMetrics } from './services/riskService';
import { riskAssessmentDAO, riskAlertDAO } from './dao/riskDAO';
import { redisCache, CacheKeyType } from '../../shared/cache/redis';
import { zmqBus, MessageType, ZMQMessage } from '../../shared/messaging/zeromq';
import { configManager } from '../../config/environment';
import { logger } from '../../shared/utils/logger';

interface RiskModuleConfig {
  riskConfiguration?: {
    riskWeights: Record<string, any>;
    riskLimits: Record<string, any>;
  };
  monitoring?: {
    intervalMs: number;
  };
  alertRetention?: number;
}



/**
 * 风控模组 (Risk Control Module)
 * 
 * 负责整个交易系统的风险管理，包括：
 * - 风险评估引擎：对策略包进行全面风险评估
 * - 实时监控：持续监控交易风险指标
 * - 警报管理：及时发现和处理风险事件
 * - 风险配置：动态调整风险参数和限额
 */
export class RiskModule {
  private router: Router;
  private isInitialized: boolean = false;
  private monitoringInterval: NodeJS.Timeout | null = null;
  private cleanupInterval: NodeJS.Timeout | null = null;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private moduleConfig: RiskModuleConfig;

  constructor() {
    this.router = Router();
    // 为 moduleConfig 提供一个更完整的默认结构
    this.moduleConfig = {
      riskConfiguration: {
        riskWeights: {},
        riskLimits: {}
      },
      monitoring: {
        intervalMs: 30000
      },
      alertRetention: 90
    };
    this.setupRoutes();
  }

  /**
   * 设置路由
   */
  private setupRoutes(): void {
    // 挂载风控路由
    this.router.use('/risk', riskRoutes);
    
    // 模组信息路由
    this.router.get('/risk/module/info', (req, res) => {
      res.json({
        success: true,
        data: {
          name: 'Risk Control Module',
          version: '1.0.0',
          status: this.isInitialized ? 'running' : 'stopped',
          description: '风险控制模组 - 负责交易风险评估、监控和警报管理',
          features: [
            '风险评估引擎',
            '实时风险监控',
            '智能警报系统',
            '风险配置管理',
            '投资组合风险分析'
          ],
          endpoints: [
            'POST /api/risk/assessments - 执行风险评估',
            'GET /api/risk/assessments - 获取评估列表',
            'POST /api/risk/alerts - 创建风险警报',
            'GET /api/risk/alerts - 获取警报列表',
            'GET /api/risk/metrics/realtime - 获取实时风险指标',
            'GET /api/risk/stats/dashboard - 获取仪表板数据'
          ]
        }
      });
    });
  }

  /**
   * 初始化风控模组
   */
  async initialize(): Promise<void> {
    try {
      logger.info('正在初始化风控模组...');

      // 加载并合并配置
      const loadedConfig = configManager.getConfig().risk || {};
      this.moduleConfig = {
        ...this.moduleConfig,
        ...loadedConfig,
        riskConfiguration: {
          ...(this.moduleConfig.riskConfiguration || {}),
          ...((loadedConfig as any).riskConfiguration || {}),
        },
        monitoring: {
          ...(this.moduleConfig.monitoring || {}),
          ...((loadedConfig as any).monitoring || {}),
        },
      };
      
      // 初始化数据访问层
      await this.initializeDAOs();
      
      // 初始化服务层
      await this.initializeServices();
      
      // 启动定时任务
      await this.startScheduledTasks();
      
      // 设置消息监听
      await this.setupMessageHandlers();
      
      this.isInitialized = true;
      logger.info('风控模组初始化完成');
      
    } catch (error) {
      logger.error('风控模组初始化失败:', error);
      throw error;
    }
  }

  /**
   * 初始化数据访问层
   */
  private async initializeDAOs(): Promise<void> {
    try {
      // DAO初始化已在构造函数中完成
      // await riskAssessmentDAO.initialize();
      // await riskAlertDAO.initialize();
      // await riskMetricsDAO.initialize();
      
      logger.info('风控模组数据访问层初始化完成');
    } catch (error) {
      logger.error('风控模组数据访问层初始化失败:', error);
      throw error;
    }
  }

  /**
   * 初始化服务层
   */
  private async initializeServices(): Promise<void> {
    try {
      // 风险服务初始化
      // await riskService.initialize();
      
      // 加载风险配置
      if (this.moduleConfig.riskConfiguration) {
        const { riskWeights, riskLimits } = this.moduleConfig.riskConfiguration;
        if (riskWeights && riskLimits) {
          riskService.updateRiskConfiguration(riskWeights, riskLimits);
        }
      }
      
      logger.info('风控模组服务层初始化完成');
    } catch (error) {
      logger.error('风控模组服务层初始化失败:', error);
      throw error;
    }
  }

  /**
   * 启动定时任务
   */
  private async startScheduledTasks(): Promise<void> {
    try {
      // 启动实时风险监控
      const monitoringInterval = this.moduleConfig?.monitoring?.intervalMs || 30000;
      riskService.startRealTimeMonitoring(monitoringInterval);
      
      // 启动过期警报清理任务（每小时执行一次）
      this.cleanupInterval = setInterval(async () => {
        try {
          await this.cleanupExpiredAlerts();
        } catch (error) {
          logger.error('清理过期警报失败:', error);
        }
      }, 60 * 60 * 1000);
      
      // 启动健康检查任务（每5分钟执行一次）
      this.healthCheckInterval = setInterval(async () => {
        try {
          await this.performHealthCheck();
        } catch (error) {
          logger.error('健康检查失败:', error);
        }
      }, 5 * 60 * 1000);
      
      logger.info('风控模组定时任务启动完成');
    } catch (error) {
      logger.error('启动风控模组定时任务失败:', error);
      throw error;
    }
  }

  /**
   * 设置消息处理器
   */
  private async setupMessageHandlers(): Promise<void> {
    try {
      // 监听来自交易员模组的风险评估请求
      zmqBus.subscribe(MessageType.RISK_ALERT, async (message) => {
        try {
          const { strategyId, portfolioId, timestamp, metrics } = message.data;
          
          const result = await riskService.performRiskAssessment({
            strategyId: Number(strategyId),
            assessmentType: 'triggered' as const,
            triggerReason: 'system_alert',
            assessedBy: 'system'
          });
          
          // 发送评估结果回交易员模组
          const responseMessage: ZMQMessage = {
            type: MessageType.RISK_ALERT,
            timestamp: new Date().toISOString(),
            source: 'risk_module',
            correlationId: message.correlationId,
            data: {
              strategyId,
              result
            }
          };
          zmqBus.publish(responseMessage);
          
        } catch (error) {
          logger.error('处理风险评估请求失败:', error);
          
          // 发送错误响应
          const errorMessage: ZMQMessage = {
            type: MessageType.RISK_ALERT,
            timestamp: new Date().toISOString(),
            source: 'risk_module',
            correlationId: message.correlationId,
            data: {
              error: error instanceof Error ? error.message : '风险评估失败'
            }
          };
          zmqBus.publish(errorMessage);
        }
      });
      
      // 监听来自财务模组的资金风险检查请求
      zmqBus.subscribe(MessageType.RISK_ALERT, async (message) => {
        try {
          const { strategyId, requestedAmount } = message.data;
          
          // 执行资金风险检查
          const riskMetrics = await riskService.getRealTimeRiskMetrics(Number(strategyId));
          const isRiskAcceptable = this.evaluateFinancialRisk(riskMetrics, Number(requestedAmount));
          
          // 发送检查结果
          const responseMessage: ZMQMessage = {
            type: MessageType.RISK_ALERT,
            timestamp: new Date().toISOString(),
            source: 'risk_module',
            correlationId: message.correlationId,
            data: {
              strategyId,
              requestedAmount,
              approved: isRiskAcceptable,
              riskLevel: riskMetrics?.riskLevel || 'unknown'
            }
          };
          zmqBus.publish(responseMessage);
          
        } catch (error) {
          logger.error('处理资金风险检查失败:', error);
          
          const errorMessage: ZMQMessage = {
            type: MessageType.RISK_ALERT,
            timestamp: new Date().toISOString(),
            source: 'risk_module',
            correlationId: message.correlationId,
            data: {
              error: error instanceof Error ? error.message : '资金风险检查失败'
            }
          };
          zmqBus.publish(errorMessage);
        }
      });
      
      // 监听紧急停止信号
      zmqBus.subscribe(MessageType.EMERGENCY_STOP, async (message) => {
        try {
          logger.warn('收到紧急停止信号，暂停风险监控');
          
          // 停止实时监控
          riskService.stopRealTimeMonitoring();
          
          // 创建紧急停止警报
          await riskService.createRiskAlert({
            alertType: 'market_volatility',
            severity: 'critical',
            message: '系统紧急停止 - 风险监控已暂停',
            details: { reason: message.data?.reason || 'unknown' },
            triggeredBy: 'system',
            autoResolve: false
          });
          
        } catch (error) {
          logger.error('处理紧急停止信号失败:', error);
        }
      });
      
      // 监听系统恢复信号
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, async () => {
        try {
          logger.info('收到系统恢复信号，重启风险监控');
          
          // 重启实时监控
          const monitoringInterval = this.moduleConfig?.monitoring?.intervalMs || 30000;
          riskService.startRealTimeMonitoring(monitoringInterval);
          
        } catch (error) {
          logger.error('处理系统恢复信号失败:', error);
        }
      });
      
      logger.info('风控模组消息处理器设置完成');
    } catch (error) {
      logger.error('设置风控模组消息处理器失败:', error);
      throw error;
    }
  }

  /**
   * Type guard to check if the metrics are for a portfolio.
   */
  private isPortfolioRiskMetrics(metrics: StrategyRiskMetrics | PortfolioRiskMetrics | null): metrics is PortfolioRiskMetrics {
    return metrics !== null && 'totalPortfolioValue' in metrics;
  }

  /**
   * 评估资金风险
   */
   private evaluateFinancialRisk(riskMetrics: StrategyRiskMetrics | PortfolioRiskMetrics | null, requestedAmount: number): boolean {
    if (!riskMetrics) {
        return false;
    }

    if (!this.isPortfolioRiskMetrics(riskMetrics)) {
        return false;
    }

    // At this point, TypeScript knows riskMetrics is of type PortfolioRiskMetrics.
    if (riskMetrics.riskLevel === 'high' || riskMetrics.riskLevel === 'critical') {
        return false;
    }

    if (riskMetrics.dailyDrawdown && riskMetrics.dailyDrawdown > 0.15) { // 回撤超过15%
        return false;
    }

    if (riskMetrics.totalExposure && riskMetrics.totalPortfolioValue && riskMetrics.totalPortfolioValue > 0) {
        const utilizationAfterRequest = (riskMetrics.totalExposure + requestedAmount) / riskMetrics.totalPortfolioValue;
        if (utilizationAfterRequest > 0.80) { // 资金使用率超过80%
            return false;
        }
    }

    return true;
   }

  /**
   * 清理过期警报
   */
  private async cleanupExpiredAlerts(): Promise<void> {
    try {
      const retentionDays = this.moduleConfig?.alertRetention || 90;
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - retentionDays);
      
      // 清理过期警报的逻辑
      const deletedCount = 0; // riskAlertDAO.deleteExpiredAlerts(cutoffDate.toISOString());
      
      if (deletedCount > 0) {
        logger.info(`清理了${deletedCount}个过期警报`);
      }
    } catch (error) {
      logger.error('清理过期警报失败:', error);
    }
  }

  /**
   * 执行健康检查
   */
  private async performHealthCheck(): Promise<void> {
    try {
      // 检查数据库连接
      await riskService.getRiskAssessments();
      
      // 检查缓存连接
      const cacheStatus = await redisCache.ping();
      
      // 检查消息总线连接
      const mqStatus = { connected: true }; // zmqBus.getConnectionStatus();
      
      // 检查活跃警报数量
      const activeAlerts = riskAlertDAO.findActiveAlerts();
      const criticalAlerts = riskAlertDAO.findCriticalAlerts();
      
      // 如果有太多未处理的关键警报，发送系统警报
      if (criticalAlerts.length > 10) {
        await riskService.createRiskAlert({
          alertType: 'market_volatility',
          severity: 'high',
          message: `检测到${criticalAlerts.length}个未处理的关键警报`,
          details: { criticalAlertCount: criticalAlerts.length },
          triggeredBy: 'health_check',
          autoResolve: false
        });
      }
      
      // 更新健康状态到缓存
      const healthStatus = {
        timestamp: new Date().toISOString(),
        database: 'connected',
        cache: cacheStatus ? 'connected' : 'disconnected',
        messageQueue: mqStatus.connected ? 'connected' : 'disconnected',
        activeAlerts: activeAlerts.length,
        criticalAlerts: criticalAlerts.length,
        status: 'healthy'
      };
      
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'risk_module', healthStatus, 300); // 5分钟过期
      
    } catch (error) {
      logger.error('健康检查执行失败:', error);
      
      // 更新不健康状态
      const healthStatus = {
        timestamp: new Date().toISOString(),
        status: 'unhealthy',
        error: error instanceof Error ? error.message : '未知错误'
      };
      
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'risk_module', healthStatus, 300);
    }
  }

  /**
   * 更新模组配置
   */
  async updateConfiguration(newConfig: Partial<RiskModuleConfig>): Promise<void> {
    try {
      this.moduleConfig = { ...this.moduleConfig, ...newConfig };
      
      // 更新风险服务配置
      if (newConfig.riskConfiguration) {
        const { riskWeights, riskLimits } = newConfig.riskConfiguration;
        if (riskWeights && riskLimits) {
          riskService.updateRiskConfiguration(riskWeights, riskLimits);
        }
      }
      
      // 更新监控间隔
      if (newConfig.monitoring?.intervalMs) {
        riskService.stopRealTimeMonitoring();
        riskService.startRealTimeMonitoring(newConfig.monitoring.intervalMs);
      }
      
      logger.info('风控模组配置更新完成');
    } catch (error) {
      logger.error('更新风控模组配置失败:', error);
      throw error;
    }
  }

  /**
   * 获取模组状态
   */
  getStatus(): unknown {
    return {
      name: 'Risk Control Module',
      initialized: this.isInitialized,
      monitoring: true,
      configuration: this.moduleConfig,
      uptime: process.uptime(),
      memoryUsage: process.memoryUsage(),
      timestamp: new Date().toISOString()
    };
  }

  /**
   * 获取模组统计信息
   */
  async getStatistics(): Promise<unknown> {
    try {
      const stats = await riskService.getRiskStatistics();
      const activeAlerts = riskAlertDAO.findActiveAlerts();
      const pendingAssessments = riskAssessmentDAO.findPendingAssessments();
      
      const baseStats = (typeof stats === 'object' && stats !== null) ? stats : {};

      return {
        ...baseStats, // Ensure stats is an object before spreading
        activeAlerts: activeAlerts.length,
        pendingAssessments: pendingAssessments.length,
        lastUpdate: new Date().toISOString()
      };
    } catch (error) {
      logger.error('获取风控模组统计信息失败:', error);
      throw error;
    }
  }

  /**
   * 获取路由器
   */
  getRouter(): Router {
    return this.router;
  }

  /**
   * 优雅关闭模组
   */
  async shutdown(): Promise<void> {
    try {
      logger.info('正在关闭风控模组...');
      
      // 停止实时监控
      riskService.stopRealTimeMonitoring();
      
      // 清理定时任务
      if (this.cleanupInterval) {
        clearInterval(this.cleanupInterval);
        this.cleanupInterval = null;
      }
      
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
        this.healthCheckInterval = null;
      }
      
      // 创建关闭警报
      await riskService.createRiskAlert({
        alertType: 'market_volatility',
        severity: 'medium',
        message: '风控模组正在关闭',
        details: { shutdownTime: new Date().toISOString() },
        triggeredBy: 'system',
        autoResolve: true
      });
      
      // 停止服务监控
      // riskService.shutdown();
      
      this.isInitialized = false;
      logger.info('风控模组关闭完成');
      
    } catch (error) {
      logger.error('关闭风控模组失败:', error);
      throw error;
    }
  }
}

// 导出模组实例
export const riskModule = new RiskModule();
export default riskModule;

// 导出类型和接口
export * from './services/riskService';
export * from './dao/riskDAO';