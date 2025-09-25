import { Router } from 'express';
import { masterService } from './services/masterService';
import { systemMonitorDAO, systemConfigDAO } from './dao/masterDAO';
import { masterRoutes } from './routes/masterRoutes';
import { redisCache, CacheKeyType } from '../../shared/cache/redis';
import { zmqBus, ZMQMessage, MessageType } from '../../shared/messaging/zeromq';
import { logger } from '../../shared/utils/logger';

/**
 * 总控模组 (Master Control Module)
 * 
 * 负责系统的全局监控、紧急控制、配置管理和系统协调
 * 核心功能：
 * - 系统健康监控和性能指标收集
 * - 紧急控制和故障恢复
 * - 系统配置管理和变更控制
 * - 模组状态监控和协调
 * - 事件管理和警报处理
 */
class MasterModule {
  private router: Router;
  private initialized: boolean = false;
  private startTime: Date;
  private monitoringInterval?: NodeJS.Timeout;
  private healthCheckInterval?: NodeJS.Timeout;
  private alertProcessingInterval?: NodeJS.Timeout;
  private performanceCollectionInterval?: NodeJS.Timeout;
  private emergencyStopActive: boolean = false;
  private moduleStatus: Map<string, unknown> = new Map();
  private alertQueue: unknown[][] = [];
  private config: Record<string, unknown> = {};

  constructor() {
    this.router = Router();
    this.startTime = new Date();
    this.setupRoutes();
  }

  /**
   * 设置路由
   */
  private setupRoutes(): void {
    this.router.use('/', masterRoutes);
  }

  /**
   * 初始化总控模组
   */
  async initialize(): Promise<void> {
    try {
      logger.info('正在初始化总控模组...');

      // 1. 加载系统配置
      await this.loadConfiguration();

      // 2. 初始化数据访问对象
      await this.initializeDAOs();

      // 3. 初始化服务
      await this.initializeServices();

      // 4. 启动定时任务
      this.startScheduledTasks();

      // 5. 设置消息监听
      this.setupMessageListeners();

      // 6. 记录初始化事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'system',
        event_category: 'lifecycle',
        severity: 'info',
        source_module: 'master',
        title: '总控模组启动',
        description: '总控模组已成功初始化并开始运行',
        event_data: {
          startTime: this.startTime.toISOString(),
          version: '1.0.0'
        },
        user_id: 'system'
      });

      this.initialized = true;
      logger.info('总控模组初始化完成');

    } catch (error) {
      logger.error('总控模组初始化失败:', error);
      throw error;
    }
  }

  /**
   * 加载系统配置
   */
  private async loadConfiguration(): Promise<void> {
    try {
      // 获取所有系统配置
      const configs = systemConfigDAO.getAllConfigs('system');
      
      // 转换为配置对象
      this.config = configs.reduce((acc, config) => {
        acc[(config as any).config_key] = (config as any).config_value;
        return acc;
      }, {} as Record<string, unknown>);

      // 设置默认配置
      const defaultConfigs = {
        'system.monitoring_interval': 30000, // 30秒
        'system.health_check_interval': 60000, // 1分钟
        'system.alert_processing_interval': 10000, // 10秒
        'system.performance_collection_interval': 60000, // 1分钟
        'system.emergency_stop_enabled': false,
        'system.max_alert_queue_size': 1000,
        'system.data_retention_days': 30,
        'system.auto_recovery_enabled': true,
        'system.notification_enabled': true
      };

      // 插入缺失的默认配置
      for (const [key, value] of Object.entries(defaultConfigs)) {
        if (!(key in this.config)) {
          // systemConfigDAO.createConfig({
          //   config_key: key,
          //   config_value: value,
          //   config_type: typeof value,
          //   category: 'system',
          //   description: `系统默认配置: ${key}`,
          //   is_sensitive: false,
          //   is_readonly: false,
          //   created_by: 'system'
          // });
          this.config[key] = value;
        }
      }

      logger.info('系统配置加载完成');
    } catch (error) {
      logger.error('加载系统配置失败:', error);
      throw error;
    }
  }

  /**
   * 初始化数据访问对象
   */
  private async initializeDAOs(): Promise<void> {
    try {
      await systemMonitorDAO.initialize();
      await systemConfigDAO.initialize();
      logger.info('数据访问对象初始化完成');
    } catch (error) {
      logger.error('数据访问对象初始化失败:', error);
      throw error;
    }
  }

  /**
   * 初始化服务
   */
  private async initializeServices(): Promise<void> {
    try {
      await masterService.initialize();
      logger.info('总控服务初始化完成');
    } catch (error) {
      logger.error('总控服务初始化失败:', error);
      throw error;
    }
  }

  /**
   * 启动定时任务
   */
  private startScheduledTasks(): void {
    try {
      // 系统监控任务
      this.monitoringInterval = setInterval(
        () => this.performSystemMonitoring(),
        (this.config['system.monitoring_interval'] as number) || 30000
      );

      // 健康检查任务
      this.healthCheckInterval = setInterval(
        () => this.performHealthCheck(),
        (this.config['system.health_check_interval'] as number) || 60000
      );

      // 警报处理任务
      this.alertProcessingInterval = setInterval(
        () => this.processAlertQueue(),
        (this.config['system.alert_processing_interval'] as number) || 10000
      );

      // 性能指标收集任务
      this.performanceCollectionInterval = setInterval(
        () => this.collectPerformanceMetrics(),
        (this.config['system.performance_collection_interval'] as number) || 60000
      );

      logger.info('定时任务启动完成');
    } catch (error) {
      logger.error('启动定时任务失败:', error);
      throw error;
    }
  }

  /**
   * 设置消息监听
   */
  private setupMessageListeners(): void {
    try {
      // 监听模组状态更新
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, (data) => {
        this.handleModuleStatusUpdate(data as unknown as Record<string, unknown>);
      });

      // 监听系统事件
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, (data) => {
        this.handleSystemEvent(data as unknown as Record<string, unknown>);
      });

      // 监听紧急停止信号
      zmqBus.subscribe(MessageType.EMERGENCY_STOP, (data) => {
        this.handleEmergencyStop(data as unknown as Record<string, unknown>);
      });

      // 监听系统恢复信号
      zmqBus.subscribe(MessageType.SYSTEM_RECOVERY, (data) => {
        this.handleSystemRecovery(data as unknown as Record<string, unknown>);
      });

      // 监听配置变更
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, (data) => {
        this.handleConfigUpdate(data as unknown as Record<string, unknown>);
      });

      // 监听健康检查请求
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, (data) => {
        this.handleHealthCheckRequest(data as unknown as Record<string, unknown>);
      });

      logger.info('消息监听设置完成');
    } catch (error) {
      logger.error('设置消息监听失败:', error);
      throw error;
    }
  }

  /**
   * 执行系统监控
   */
  private async performSystemMonitoring(): Promise<void> {
    try {
      // 检查模组状态
      const modules = systemMonitorDAO.getAllModuleStatus();
      
      for (const module of modules) {
        // 检查模组是否超时
        const lastUpdate = new Date(module.last_update as string);
        const now = new Date();
        const timeDiff = now.getTime() - lastUpdate.getTime();
        
        if (timeDiff > 300000) { // 5分钟超时
          // 创建超时警报
          this.addAlert({
            type: 'module_timeout',
            severity: 'high',
            module: module.module_name,
            message: `模组 ${module.module_name} 超过5分钟未更新状态`,
            timestamp: now.toISOString()
          });
        }
      }

      // 检查系统资源使用情况
      const metrics = await masterService.getPerformanceMetrics() as any;
      
      // CPU使用率警报
      if (metrics.cpu > 80) {
        this.addAlert({
          type: 'high_cpu',
          severity: 'medium',
          message: `CPU使用率过高: ${metrics.cpu}%`,
          timestamp: new Date().toISOString()
        });
      }

      // 内存使用率警报
      if (metrics.memory > 85) {
        this.addAlert({
          type: 'high_memory',
          severity: 'medium',
          message: `内存使用率过高: ${metrics.memory}%`,
          timestamp: new Date().toISOString()
        });
      }

      // 更新缓存中的监控数据
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'monitoring', {
           modules: modules.length,
           alerts: this.alertQueue.length,
           timestamp: new Date().toISOString()
         }, 300);

    } catch (error) {
      logger.error('系统监控执行失败:', error);
    }
  }

  /**
   * 执行健康检查
   */
  private async performHealthCheck(): Promise<void> {
    try {
      const healthData = await masterService.getSystemOverview() as any;
      
      // 更新健康状态缓存
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'health', healthData.health, 120);
      
      // 检查系统健康评分
      if (healthData.health.score < 70) {
        this.addAlert({
          type: 'system_health',
          severity: 'high',
          message: `系统健康评分过低: ${healthData.health.score}`,
          timestamp: new Date().toISOString()
        });
      }

      // 记录健康检查事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'monitoring',
        event_category: 'health_check',
        severity: 'info',
        source_module: 'master',
        title: '系统健康检查',
        description: `健康评分: ${(healthData as any).health.score}`,
        event_data: (healthData as any).health,
        user_id: 'system'
      });

    } catch (error) {
      logger.error('健康检查执行失败:', error);
    }
  }

  /**
   * 处理警报队列
   */
  private async processAlertQueue(): Promise<void> {
    try {
      if (this.alertQueue.length === 0) return;

      // 处理队列中的警报
      const alertsToProcess = this.alertQueue.splice(0, 10); // 每次处理10个
      
      for (const alert of alertsToProcess) {
        // 记录警报事件
        systemMonitorDAO.recordSystemEvent({
          event_type: 'alert',
          event_category: (alert as any).type,
          severity: (alert as any).severity,
          source_module: (alert as any).module || 'master',
          title: `系统警报: ${(alert as any).type}`,
          description: (alert as any).message,
          event_data: alert as any as Record<string, unknown>,
          user_id: 'system'
        });

        // 发布警报通知
        if (this.config['system.notification_enabled']) {
          const alertMessage: ZMQMessage = {
            type: MessageType.SYSTEM_STATUS,
            timestamp: new Date().toISOString(),
            source: 'master_module',
            data: {
              type: 'alert_created',
              alert: alert
            }
          };
          await zmqBus.publish(alertMessage);
        }
      }

      logger.info(`处理了 ${alertsToProcess.length} 个警报`);

    } catch (error) {
      logger.error('处理警报队列失败:', error);
    }
  }

  /**
   * 收集性能指标
   */
  private async collectPerformanceMetrics(): Promise<void> {
    try {
      const metrics = await masterService.getPerformanceMetrics();
      
      // 记录性能指标
      systemMonitorDAO.recordPerformanceMetric({
        module_name: 'master',
        metric_name: 'cpu_usage',
        metric_value: (metrics as any).cpu,
        metric_unit: 'percent',
        metadata: JSON.stringify({ timestamp: new Date().toISOString() })
      });

      systemMonitorDAO.recordPerformanceMetric({
        module_name: 'master',
        metric_name: 'memory_usage',
        metric_value: (metrics as any).memory,
        metric_unit: 'percent',
        metadata: JSON.stringify({ timestamp: new Date().toISOString() })
      });

      // 更新缓存中的性能指标
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'metrics', metrics, 300);

    } catch (error) {
      logger.error('收集性能指标失败:', error);
    }
  }

  /**
   * 添加警报到队列
   */
  private addAlert(alert: unknown): void {
    if (this.alertQueue.length >= ((this.config['system.max_alert_queue_size'] as number) || 1000)) {
      // 队列满时移除最旧的警报
      this.alertQueue.shift();
    }
    
    this.alertQueue.push({
      ...(alert as any),
      id: Date.now() + Math.random(),
      createdAt: new Date().toISOString()
    });
  }

  /**
   * 处理模组状态更新
   */
  private handleModuleStatusUpdate(data: Record<string, unknown>): void {
    try {
      const { moduleName, status, metadata } = data;
      
      // 更新模组状态
      systemMonitorDAO.updateModuleStatus({
        moduleName: moduleName as string,
        status: status as string,
        metadata: metadata as Record<string, unknown>
      } as Record<string, unknown>);
      
      // 更新内存中的状态
      this.moduleStatus.set(moduleName as string, {
        status,
        metadata,
        lastUpdate: new Date().toISOString()
      });

      logger.debug(`模组状态更新: ${moduleName} -> ${status}`);
    } catch (error) {
      logger.error('处理模组状态更新失败:', error);
    }
  }

  /**
   * 处理系统事件
   */
  private handleSystemEvent(data: Record<string, unknown>): void {
    try {
      // 记录系统事件
      systemMonitorDAO.recordSystemEvent(data as any);
      
      // 根据事件严重程度创建警报
      if (data.severity === 'high' || data.severity === 'critical') {
        this.addAlert({
          type: 'system_event',
          severity: data.severity,
          module: data.source_module,
          message: data.description,
          timestamp: new Date().toISOString()
        });
      }

      logger.info(`系统事件: ${data.title}`);
    } catch (error) {
      logger.error('处理系统事件失败:', error);
    }
  }

  /**
   * 处理紧急停止
   */
  private async handleEmergencyStop(data: Record<string, unknown>): Promise<void> {
    try {
      this.emergencyStopActive = true;
      
      // 更新配置
      systemConfigDAO.updateConfig(
        'system.emergency_stop_enabled',
        true as any,
        (data.initiatedBy as string) || 'system',
        (data.reason as string) || '紧急停止'
      );

      // 更新缓存
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'emergency_stop', {
        active: true,
        reason: data.reason,
        initiatedBy: data.initiatedBy,
        timestamp: new Date().toISOString()
      }, 3600);

      // 记录紧急停止事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'emergency',
        event_category: 'stop',
        severity: 'critical',
        source_module: 'master',
        title: '系统紧急停止',
        description: data.reason || '系统进入紧急停止状态',
        event_data: data,
        user_id: data.initiatedBy || 'system'
      });

      // 通知所有模组
      const emergencyMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          type: 'emergency_stop',
          active: true,
          reason: data.reason
        }
      };
      await zmqBus.publish(emergencyMessage);

      logger.warn('系统进入紧急停止状态', { reason: data.reason as string });
    } catch (error) {
      logger.error('处理紧急停止失败:', error);
    }
  }

  /**
   * 处理系统恢复
   */
  private async handleSystemRecovery(data: Record<string, unknown>): Promise<void> {
    try {
      this.emergencyStopActive = false;
      
      // 更新配置
      systemConfigDAO.updateConfig(
        'system.emergency_stop_enabled',
        false as any,
        (data.initiatedBy as string) || 'system',
        (data.reason as string) || '系统恢复'
      );

      // 清除缓存中的紧急停止状态
      await redisCache.delete(CacheKeyType.SYSTEM_CONFIG, 'emergency_stop');

      // 记录系统恢复事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'recovery',
        event_category: 'system',
        severity: 'info',
        source_module: 'master',
        title: '系统恢复正常',
        description: (data.reason as string) || '系统已从紧急停止状态恢复',
        event_data: data as Record<string, unknown>,
        user_id: (data.initiatedBy as string) || 'system'
      });

      // 通知所有模组
      const recoveryMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          type: 'system_recovery',
          active: false,
          reason: data.reason
        }
      };
      await zmqBus.publish(recoveryMessage);

      logger.info('系统已恢复正常', { reason: data.reason as string });
    } catch (error) {
      logger.error('处理系统恢复失败:', error);
    }
  }

  /**
   * 处理配置更新
   */
  private handleConfigUpdate(data: Record<string, unknown>): void {
    try {
      const { key, value } = data;
      
      // 更新内存中的配置
      this.config[key as string] = value;
      
      // 如果是监控相关配置，重启相关任务
      if ((key as string).startsWith('system.monitoring') || (key as string).startsWith('system.health')) {
        this.restartScheduledTasks();
      }

      logger.info(`配置更新: ${key} = ${value}`);
    } catch (error) {
      logger.error('处理配置更新失败:', error);
    }
  }

  /**
   * 处理健康检查请求
   */
  private async handleHealthCheckRequest(data: Record<string, unknown>): Promise<void> {
    try {
      const healthData = await masterService.getSystemOverview();
      
      // 发送健康检查响应
      const healthMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          type: 'health_response',
          requestId: data.requestId,
          health: (healthData as any).health
        }
      };
      await zmqBus.publish(healthMessage);

    } catch (error) {
      logger.error('处理健康检查请求失败:', error);
    }
  }

  /**
   * 重启定时任务
   */
  private restartScheduledTasks(): void {
    try {
      // 清除现有任务
      if (this.monitoringInterval) clearInterval(this.monitoringInterval);
      if (this.healthCheckInterval) clearInterval(this.healthCheckInterval);
      if (this.alertProcessingInterval) clearInterval(this.alertProcessingInterval);
      if (this.performanceCollectionInterval) clearInterval(this.performanceCollectionInterval);

      // 重新启动任务
      this.startScheduledTasks();
      
      logger.info('定时任务已重启');
    } catch (error) {
      logger.error('重启定时任务失败:', error);
    }
  }

  /**
   * 更新配置
   */
  async updateConfiguration(newConfig: Record<string, unknown>): Promise<void> {
    try {
      for (const [key, value] of Object.entries(newConfig)) {
        this.config[key] = value;
      }
      
      // 发布配置更新通知
      const configMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          type: 'config_updated',
          config: newConfig
        }
      };
      await zmqBus.publish(configMessage);
      
      logger.info('配置更新完成');
    } catch (error) {
      logger.error('更新配置失败:', error);
      throw error;
    }
  }

  /**
   * 获取模组状态
   */
  getStatus(): unknown {
    return {
      initialized: this.initialized,
      startTime: this.startTime.toISOString(),
      uptime: Date.now() - this.startTime.getTime(),
      emergencyStopActive: this.emergencyStopActive,
      moduleCount: this.moduleStatus.size,
      alertQueueSize: this.alertQueue.length,
      config: this.config
    };
  }

  /**
   * 获取统计信息
   */
  getStatistics(): unknown {
    const modules = systemMonitorDAO.getAllModuleStatus();
    const events = systemMonitorDAO.getSystemEvents({}, 100);
    
    return {
      modules: {
        total: modules.length,
        healthy: modules.filter(m => m.status === 'healthy').length,
        unhealthy: modules.filter(m => m.status !== 'healthy').length
      },
      events: {
        total: events.length,
        critical: events.filter(e => e.severity === 'critical').length,
        high: events.filter(e => e.severity === 'high').length,
        unresolved: events.filter(e => !e.resolved_at).length
      },
      alerts: {
        queueSize: this.alertQueue.length,
        processed: 0 // 这里可以添加已处理警报的计数
      },
      uptime: Date.now() - this.startTime.getTime()
    };
  }

  /**
   * 获取路由器
   */
  getRouter(): Router {
    return this.router;
  }

  /**
   * 优雅关闭
   */
  async shutdown(): Promise<void> {
    try {
      logger.info('正在关闭总控模组...');

      // 清除定时任务
      if (this.monitoringInterval) clearInterval(this.monitoringInterval);
      if (this.healthCheckInterval) clearInterval(this.healthCheckInterval);
      if (this.alertProcessingInterval) clearInterval(this.alertProcessingInterval);
      if (this.performanceCollectionInterval) clearInterval(this.performanceCollectionInterval);

      // 处理剩余的警报
      if (this.alertQueue.length > 0) {
        await this.processAlertQueue();
      }

      // 记录关闭事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'system',
        event_category: 'lifecycle',
        severity: 'info',
        source_module: 'master',
        title: '总控模组关闭',
        description: '总控模组正在优雅关闭',
        event_data: {
          uptime: Date.now() - this.startTime.getTime(),
          processedAlerts: this.alertQueue.length
        },
        user_id: 'system'
      });

      this.initialized = false;
      logger.info('总控模组已关闭');

    } catch (error) {
      logger.error('关闭总控模组失败:', error);
      throw error;
    }
  }
}

// 创建总控模组实例
const masterModule = new MasterModule();

export default masterModule;
export { MasterModule };