import { Router } from 'express';
import { financeRoutes } from './routes/financeRoutes';
import { financeService, FinanceService } from './services/financeService';
import { budgetRequestDAO, fundAllocationDAO, accountDAO, financialTransactionDAO } from './dao/financeDAO';
import { redisCache, CacheKeyType } from '../../shared/cache/redis';
import { zmqBus, ZMQMessage, MessageType } from '../../shared/messaging/zeromq';
import { logger } from '../../shared/utils/logger';





/**
 * 财务模组主类
 * 负责整合财务模组的所有组件，管理模组生命周期
 */
export class FinanceModule {
  private router: Router;
  private service: FinanceService;
  private isInitialized: boolean = false;
  private healthCheckInterval?: NodeJS.Timeout;
  private budgetProcessingInterval?: NodeJS.Timeout;
  private accountMonitoringInterval?: NodeJS.Timeout;
  private cacheCleanupInterval?: NodeJS.Timeout;
  private moduleConfig: Record<string, unknown>;

  constructor() {
    this.router = Router();
    this.service = financeService;
    this.moduleConfig = {};
  }

  /**
   * 初始化财务模组
   */
  async initialize(): Promise<void> {
    try {
      logger.info('正在初始化财务模组...');

      // 1. 加载配置
      await this.loadConfiguration();

      // 2. 初始化数据访问层
      await this.initializeDAOs();

      // 3. 初始化服务层
      await this.initializeService();

      // 4. 设置路由
      this.setupRoutes();

      // 5. 启动定时任务
      this.startScheduledTasks();

      // 6. 设置消息监听
      this.setupMessageListeners();

      this.isInitialized = true;
      logger.info('财务模组初始化完成');
    } catch (error) {
      logger.error('财务模组初始化失败:', error);
      throw error;
    }
  }

  /**
   * 加载配置
   */
  private async loadConfiguration(): Promise<void> {
    try {
      // 从Redis缓存加载配置
      const cachedConfig = await redisCache.get(CacheKeyType.SYSTEM_CONFIG, 'finance_config');
      if (cachedConfig) {
        this.moduleConfig = { ...this.moduleConfig, ...(cachedConfig as Record<string, unknown>) };
      }

      // 设置默认配置
      this.moduleConfig = {
        autoApprovalThreshold: 10000, // 自动批准阈值
        maxDailyBudget: 1000000, // 每日最大预算
        riskLevelLimits: {
          low: 50000,
          medium: 100000,
          high: 200000,
          critical: 500000
        },
        accountHealthThresholds: {
          lowBalance: 1000,
          criticalBalance: 100,
          maxDailyLoss: 0.05, // 5%
          maxMonthlyLoss: 0.20 // 20%
        },
        intervals: {
          healthCheck: 30000, // 30秒
          budgetProcessing: 60000, // 1分钟
          accountMonitoring: 120000, // 2分钟
          cacheCleanup: 300000 // 5分钟
        },
        ...this.moduleConfig
      };

      logger.info('财务模组配置加载完成');
    } catch (error) {
      logger.error('加载财务模组配置失败:', error);
      throw error;
    }
  }

  /**
   * 初始化数据访问对象
   */
  private async initializeDAOs(): Promise<void> {
    try {
      // 初始化所有DAO
      await budgetRequestDAO.initialize();
      await fundAllocationDAO.initialize();
      await accountDAO.initialize();
      await financialTransactionDAO.initialize();

      logger.info('财务模组DAO初始化完成');
    } catch (error) {
      logger.error('财务模组DAO初始化失败:', error);
      throw error;
    }
  }

  /**
   * 初始化服务层
   */
  private async initializeService(): Promise<void> {
    try {
      await this.service.initialize();
      await this.service.updateConfiguration(this.moduleConfig);
      
      logger.info('财务服务初始化完成');
    } catch (error) {
      logger.error('财务服务初始化失败:', error);
      throw error;
    }
  }

  /**
   * 设置路由
   */
  private setupRoutes(): void {
    this.router.use('/finance', financeRoutes);
    logger.info('财务模组路由设置完成');
  }

  /**
   * 启动定时任务
   */
  private startScheduledTasks(): void {
    const intervals = this.moduleConfig.intervals as Record<string, number>;

    // 健康检查任务
    this.healthCheckInterval = setInterval(async () => {
      try {
        await this.performHealthCheck();
      } catch (error) {
        logger.error('财务模组健康检查失败:', error);
      }
    }, Number(intervals.healthCheck));

    // 预算处理任务
    this.budgetProcessingInterval = setInterval(async () => {
      try {
        await this.processPendingBudgets();
      } catch (error) {
        logger.error('处理待审批预算失败:', error);
      }
    }, Number(intervals.budgetProcessing));

    // 账户监控任务
    this.accountMonitoringInterval = setInterval(async () => {
      try {
        await this.monitorAccountHealth();
      } catch (error) {
        logger.error('账户健康监控失败:', error);
      }
    }, Number(intervals.accountMonitoring));

    // 缓存清理任务
    this.cacheCleanupInterval = setInterval(async () => {
      try {
        await this.cleanupExpiredCache();
      } catch (error) {
        logger.error('缓存清理失败:', error);
      }
    }, Number(intervals.cacheCleanup));

    logger.info('财务模组定时任务启动完成');
  }

  /**
   * 设置消息监听
   */
  private setupMessageListeners(): void {
    try {
      // 监听预算申请消息
      zmqBus.subscribe(MessageType.BUDGET_REQUEST, async (message: ZMQMessage) => {
        try {
          logger.info('收到预算申请消息:', message as unknown as Record<string, unknown>);
          const result = await this.service.processBudgetRequest(message.data as any);
          
          // 发送响应消息
          const responseMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              type: 'budget_response',
              requestId: (message as any).requestId,
              strategyId: (message.data as Record<string, unknown>)?.strategyId,
              result
            }
          };
          await zmqBus.publish(responseMessage);
        } catch (error) {
          logger.error('处理预算申请消息失败:', error);
          
          // 发送错误响应
          const errorMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              requestId: (message as any).requestId,
              strategyId: (message.data as Record<string, unknown>)?.strategyId,
              result: {
                success: false,
                error: error instanceof Error ? error.message : '处理预算申请失败'
              }
            }
          };
          await zmqBus.publish(errorMessage);
        }
      });

      // 监听资金分配请求
      zmqBus.subscribe(MessageType.FUND_ALLOCATION_REQUEST, async (message: ZMQMessage) => {
        try {
          logger.info('收到资金分配请求:', message as unknown as Record<string, unknown>);
          const result = await this.service.createFundAllocation(message.data as any);
          
          // 发送响应消息
          const responseMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              requestId: (message as any).requestId,
              strategyId: (message.data as Record<string, unknown>)?.strategyId,
              result
            }
          };
          await zmqBus.publish(responseMessage);
        } catch (error) {
          logger.error('处理资金分配请求失败:', error);
          
          // 发送错误响应
          const errorMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              requestId: (message as any).requestId,
              strategyId: (message.data as Record<string, unknown>)?.strategyId,
              result: {
                success: false,
                error: error instanceof Error ? error.message : '处理资金分配请求失败'
              }
            }
          };
          await zmqBus.publish(errorMessage);
        }
      });

      // 监听风险检查结果
      zmqBus.subscribe(MessageType.RISK_ASSESSMENT_RESULT, async (message: ZMQMessage) => {
        try {
          logger.info('收到风险检查结果:', message as unknown as Record<string, unknown>);
          await this.handleRiskAssessmentResult(message.data as Record<string, unknown>);
        } catch (error) {
          logger.error('处理风险检查结果失败:', error);
        }
      });

      // 监听紧急停止信号
      zmqBus.subscribe(MessageType.EMERGENCY_STOP, async (message: ZMQMessage) => {
        try {
          logger.warn('收到紧急停止信号:', message as unknown as Record<string, unknown>);
          await this.handleEmergencyStop(message.data as Record<string, unknown>);
        } catch (error) {
          logger.error('处理紧急停止信号失败:', error);
        }
      });

      // 监听系统恢复信号
      zmqBus.subscribe(MessageType.SYSTEM_RECOVERY, async (message: ZMQMessage) => {
        try {
          logger.info('收到系统恢复信号:', message as unknown as Record<string, unknown>);
          await this.handleSystemRecovery(message.data as Record<string, unknown>);
        } catch (error) {
          logger.error('处理系统恢复信号失败:', error);
        }
      });

      logger.info('财务模组消息监听设置完成');
    } catch (error) {
      logger.error('设置财务模组消息监听失败:', error);
      throw error;
    }
  }

  /**
   * 执行健康检查
   */
  private async performHealthCheck(): Promise<void> {
    try {
      const healthResult = await this.service.performAccountHealthCheck();
      
      // 缓存健康检查结果
      await redisCache.set(
        CacheKeyType.SYSTEM_CONFIG,
        'finance_health_check',
        {
          ...(healthResult as Record<string, unknown>),
          timestamp: new Date().toISOString()
        }, 
        300 // 5分钟过期
      );

      // 如果发现问题，发送警报
      const healthData = healthResult as Record<string, unknown>;
      if (Number(healthData.issuesFound) > 0) {
        const alertMessage: ZMQMessage = {
          type: MessageType.SYSTEM_STATUS,
          timestamp: new Date().toISOString(),
          source: 'finance_module',
          data: {
            type: 'account_health_issue',
            severity: Number(healthData.criticalIssues) > 0 ? 'critical' : 'warning',
            data: healthResult
          }
        };
        await zmqBus.publish(alertMessage);
      }
    } catch (error) {
      logger.error('财务模组健康检查失败:', error);
    }
  }

  /**
   * 处理待审批预算
   */
  private async processPendingBudgets(): Promise<void> {
    try {
      const pendingRequests = budgetRequestDAO.findPendingRequests();
      const autoApprovalThreshold = Number(this.moduleConfig.autoApprovalThreshold);

      for (const request of pendingRequests) {
        // 检查是否可以自动批准
        if (Number(request.requested_amount) <= autoApprovalThreshold && 
            request.priority === 'low') {
          
          const result = await this.service.approveBudgetRequest(
            Number(request.id),
            Number(request.requested_amount),
            'system_auto_approval',
            '自动批准 - 金额低于阈值'
          );

          if (result.success) {
            logger.info(`自动批准预算申请 ${request.id}`);
          }
        }

        // 检查是否过期
        if (request.expires_at && new Date(String(request.expires_at)) < new Date()) {
          await this.service.rejectBudgetRequest(
            Number(request.id),
            'system_auto_reject',
            '申请已过期'
          );
          logger.info(`自动拒绝过期预算申请 ${request.id}`);
        }
      }
    } catch (error) {
      logger.error('处理待审批预算失败:', error);
    }
  }

  /**
   * 监控账户健康状态
   */
  private async monitorAccountHealth(): Promise<void> {
    try {
      const thresholds = this.moduleConfig.accountHealthThresholds as Record<string, number>;
      
      // 检查低余额账户
      const lowBalanceAccounts = accountDAO.findLowBalanceAccounts(Number(thresholds.lowBalance));
      
      for (const account of lowBalanceAccounts) {
        if (Number(account.balance) <= Number(thresholds.criticalBalance)) {
          // 发送紧急警报
          const criticalAlertMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              type: 'critical_low_balance',
              severity: 'critical',
              accountId: account.id,
              accountName: account.account_name,
              balance: account.balance,
              threshold: thresholds.criticalBalance
            }
          };
          await zmqBus.publish(criticalAlertMessage);
        } else {
          // 发送警告
          const warningMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              type: 'low_balance_warning',
              severity: 'warning',
              accountId: account.id,
              accountName: account.account_name,
              balance: account.balance,
              threshold: thresholds.lowBalance
            }
          };
          await zmqBus.publish(warningMessage);
        }
      }

      // 检查账户日损失
      const accounts = accountDAO.findActiveAccounts();
      for (const account of accounts) {
        // 获取当日交易记录 - 暂时使用模拟数据
        const dailyTransactions: any[] = [];

        const dailyLoss = dailyTransactions
          .filter(t => t.transaction_type === 'loss')
          .reduce((sum, t) => sum + Number(t.amount), 0);

        const lossRatio = dailyLoss / Number(account.balance);
        
        if (lossRatio > Number(thresholds.maxDailyLoss)) {
          const alertMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'finance_module',
            data: {
              type: 'excessive_daily_loss',
              severity: 'high',
              accountId: account.id,
              accountName: account.account_name,
              dailyLoss,
              lossRatio,
              threshold: thresholds.maxDailyLoss,
              timestamp: new Date().toISOString()
            }
          };
          await zmqBus.publish(alertMessage);
        }
      }
    } catch (error) {
      logger.error('监控账户健康状态失败:', error);
    }
  }

  /**
   * 清理过期缓存
   */
  private async cleanupExpiredCache(): Promise<void> {
    try {
      // 获取缓存键列表 - 暂时跳过
      const keys: string[] = [];
      let cleanedCount = 0;

      for (const key of keys) {
        const ttl = await redisCache.ttl(CacheKeyType.SYSTEM_CONFIG, key);
        if (ttl === -1) { // 没有过期时间的key
          // 检查是否是临时数据
          if (key.includes(':temp:') || key.includes(':cache:')) {
            await redisCache.delete(CacheKeyType.SYSTEM_CONFIG, key);
            cleanedCount++;
          }
        }
      }

      if (cleanedCount > 0) {
        logger.info(`清理了 ${cleanedCount} 个过期缓存项`);
      }
    } catch (error) {
      logger.error('清理过期缓存失败:', error);
    }
  }

  /**
   * 处理风险评估结果
   */
  private async handleRiskAssessmentResult(data: Record<string, unknown>): Promise<void> {
    try {
      const { strategyId, riskLevel, riskScore, recommendations } = data;
      
      // 更新策略风险等级缓存
      await redisCache.set(
        CacheKeyType.SYSTEM_CONFIG,
        `finance:strategy:${strategyId}:risk`,
        { riskLevel, riskScore, timestamp: new Date().toISOString() },
        3600
      );

      // 根据风险等级调整资金分配限额
      const riskLimits = this.moduleConfig.riskLevelLimits as Record<string, number>;
      const maxAllocation = riskLimits[riskLevel as string] || riskLimits.medium;

      // 检查现有分配是否超出限额
      const activeAllocations = fundAllocationDAO.findActiveAllocationsByStrategy(Number(strategyId));
      const totalAllocated = activeAllocations.reduce((sum, alloc) => sum + Number(alloc.allocated_amount), 0);

      if (totalAllocated > maxAllocation) {
        // 发送风险警报
        const riskAlertMessage: ZMQMessage = {
          type: MessageType.SYSTEM_STATUS,
          timestamp: new Date().toISOString(),
          source: 'finance_module',
          data: {
            type: 'allocation_exceeds_risk_limit',
            severity: 'critical',
            strategyId,
            riskLevel,
            totalAllocated,
            maxAllocation,
            recommendations,
            timestamp: new Date().toISOString()
          }
        };
        await zmqBus.publish(riskAlertMessage);
      }
    } catch (error) {
      logger.error('处理风险评估结果失败:', error);
    }
  }

  /**
   * 处理紧急停止信号
   */
  private async handleEmergencyStop(data: Record<string, unknown>): Promise<void> {
    try {
      logger.warn('执行财务模组紧急停止程序');
      
      const { reason, strategyId, severity } = data;

      if (strategyId) {
        // 冻结特定策略的所有资金分配
        const allocations = fundAllocationDAO.findActiveAllocationsByStrategy(Number(strategyId));
        for (const allocation of allocations) {
          fundAllocationDAO.freezeAllocation(Number(allocation.id), `紧急停止: ${reason}`);
        }
        
        logger.info(`已冻结策略 ${strategyId} 的所有资金分配`);
      } else {
        // 冻结所有活跃的资金分配
        const allocations = fundAllocationDAO.findActiveAllocations();
        for (const allocation of allocations) {
          fundAllocationDAO.freezeAllocation(Number(allocation.id), `系统紧急停止: ${reason}`);
        }
        
        logger.info('已冻结所有活跃的资金分配');
      }

      // 暂停预算申请处理
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'finance_emergency_stop', {
        reason,
        severity,
        timestamp: new Date().toISOString()
      }, 3600);

      // 发送确认消息
      const emergencyResponseMessage: ZMQMessage = {
        type: MessageType.EMERGENCY_STOP,
        timestamp: new Date().toISOString(),
        source: 'finance_module',
        data: {
          type: 'emergency_stop_executed',
          strategyId,
          reason
        }
      };
      await zmqBus.publish(emergencyResponseMessage);
    } catch (error) {
      logger.error('处理紧急停止信号失败:', error);
    }
  }

  /**
   * 处理系统恢复信号
   */
  private async handleSystemRecovery(data: Record<string, unknown>): Promise<void> {
    try {
      logger.info('执行财务模组系统恢复程序');
      
      const { reason, strategyId } = data;

      // 清除紧急停止状态
      await redisCache.delete(CacheKeyType.SYSTEM_CONFIG, 'finance_emergency_stop');

      if (strategyId) {
        // 解冻特定策略的资金分配
        const allocations = fundAllocationDAO.findByStrategyId(Number(strategyId))
          .filter((alloc: Record<string, unknown>) => alloc.status === 'frozen');
        
        for (const allocation of allocations) {
          fundAllocationDAO.unfreezeAllocation(Number(allocation.id));
        }
        
        logger.info(`已解冻策略 ${strategyId} 的资金分配`);
      } else {
        // 解冻所有冻结的资金分配
        const allAllocations = fundAllocationDAO.findAll();
        const frozenAllocations = Array.isArray(allAllocations) 
          ? allAllocations.filter((alloc: Record<string, unknown>) => alloc.status === 'frozen')
          : [];
        
        for (const allocation of frozenAllocations) {
          fundAllocationDAO.unfreezeAllocation(Number(allocation.id));
        }
        
        logger.info('已解冻所有冻结的资金分配');
      }

      // 发送确认消息
      const recoveryResponseMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'finance_module',
        data: {
          type: 'system_recovery_executed',
          strategyId,
          reason
        }
      };
      await zmqBus.publish(recoveryResponseMessage);
    } catch (error) {
      logger.error('处理系统恢复信号失败:', error);
    }
  }

  /**
   * 更新模组配置
   */
  async updateConfiguration(newConfig: Record<string, unknown>): Promise<void> {
    try {
      this.moduleConfig = { ...this.moduleConfig, ...newConfig };
      
      // 更新服务配置
      await this.service.updateConfiguration(this.moduleConfig);
      
      // 缓存新配置
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'finance_config', this.moduleConfig, 3600);
      
      logger.info('财务模组配置更新完成');
    } catch (error) {
      logger.error('更新财务模组配置失败:', error);
      throw error;
    }
  }

  /**
   * 获取模组状态
   */
  getStatus(): Record<string, unknown> {
    return {
      initialized: this.isInitialized,
      configuration: this.moduleConfig,
      tasks: {
        healthCheck: !!this.healthCheckInterval,
        budgetProcessing: !!this.budgetProcessingInterval,
        accountMonitoring: !!this.accountMonitoringInterval,
        cacheCleanup: !!this.cacheCleanupInterval
      },
      timestamp: new Date().toISOString()
    };
  }

  /**
   * 获取模组统计信息
   */
  async getStatistics(): Promise<Record<string, unknown>> {
    try {
      const stats = await this.service.getFinancialStatistics();
      const healthResult = await this.service.performAccountHealthCheck();
      
      return {
        ...(stats as Record<string, unknown>),
        accountHealth: healthResult,
        moduleStatus: this.getStatus(),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('获取财务模组统计信息失败:', error);
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
      logger.info('正在关闭财务模组...');

      // 清理定时任务
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
      }
      if (this.budgetProcessingInterval) {
        clearInterval(this.budgetProcessingInterval);
      }
      if (this.accountMonitoringInterval) {
        clearInterval(this.accountMonitoringInterval);
      }
      if (this.cacheCleanupInterval) {
        clearInterval(this.cacheCleanupInterval);
      }

      // 处理待处理的预算申请
      const pendingRequests = budgetRequestDAO.findPendingRequests();
      for (const request of pendingRequests) {
        await this.service.rejectBudgetRequest(
          Number(request.id),
          'system_shutdown',
          '系统关闭，申请被自动拒绝'
        );
      }

      // 冻结所有活跃的资金分配
      const activeAllocations = fundAllocationDAO.findActiveAllocations();
      for (const allocation of activeAllocations) {
        fundAllocationDAO.freezeAllocation(Number(allocation.id), '系统关闭');
      }

      this.isInitialized = false;
      logger.info('财务模组关闭完成');
    } catch (error) {
      logger.error('关闭财务模组失败:', error);
      throw error;
    }
  }
}

// 创建财务模组实例
export const financeModule = new FinanceModule();

// 导出类型和接口
export * from './services/financeService';
export * from './dao/financeDAO';
export * from './routes/financeRoutes';

// 默认导出
export default financeModule;