import { systemMonitorDAO, systemConfigDAO } from '../dao/masterDAO';
import { redisCache, CacheKeyType } from '../../../shared/cache/redis';
import { zmqBus, ZMQMessage, MessageType } from '../../../shared/messaging/zeromq';
import { logger } from '../../../shared/utils/logger';
import * as os from 'os';
    // // import * as fs from 'fs'; // 暂未使用 // 暂未使用
    // // import * as path from 'path'; // 暂未使用 // 暂未使用

/**
 * 紧急控制请求接口
 */
export interface EmergencyControlRequest {
  action: 'stop' | 'pause' | 'resume' | 'restart';
  scope: 'system' | 'module' | 'strategy';
  targetId?: string | number;
  reason: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  initiatedBy: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

/**
 * 系统监控配置接口
 */
export interface MonitoringConfig {
  intervals: {
    systemHealth: number;
    performanceMetrics: number;
    moduleStatus: number;
    alertProcessing: number;
  };
  thresholds: {
    cpu: { warning: number; critical: number };
    memory: { warning: number; critical: number };
    disk: { warning: number; critical: number };
    network: { warning: number; critical: number };
  };
  alerting: {
    enabled: boolean;
    channels: string[];
    escalationRules: unknown[][];
  };
}

/**
 * 总控服务类
 */
export class MasterService {
  private isInitialized: boolean = false;
  private monitoringConfig: MonitoringConfig;
  private emergencyStopActive: boolean = false;
  private systemStartTime: Date;
  private moduleStatuses: Map<string, unknown> = new Map();
  private alertQueue: Array<Record<string, any>> = [];
  private performanceHistory: Map<string, unknown[][]> = new Map();

  constructor() {
    this.systemStartTime = new Date();
    this.monitoringConfig = this.getDefaultMonitoringConfig();
  }

  /**
   * 初始化总控服务
   */
  async initialize(): Promise<void> {
    try {
      logger.info('正在初始化总控服务...');

      // 加载配置
      await this.loadConfiguration();

      // 初始化系统状态
      await this.initializeSystemStatus();

      // 设置消息监听
      this.setupMessageListeners();

      // 启动系统监控
      this.startSystemMonitoring();

      this.isInitialized = true;
      logger.info('总控服务初始化完成');
    } catch (error) {
      logger.error('总控服务初始化失败:', error);
      throw error;
    }
  }

  /**
   * 获取默认监控配置
   */
  private getDefaultMonitoringConfig(): MonitoringConfig {
    return {
      intervals: {
        systemHealth: 30000, // 30秒
        performanceMetrics: 60000, // 1分钟
        moduleStatus: 15000, // 15秒
        alertProcessing: 5000 // 5秒
      },
      thresholds: {
        cpu: { warning: 70, critical: 90 },
        memory: { warning: 80, critical: 95 },
        disk: { warning: 85, critical: 95 },
        network: { warning: 1000, critical: 5000 }
      },
      alerting: {
        enabled: true,
        channels: ['zmq', 'log'],
        escalationRules: []
      }
    };
  }

  /**
   * 加载配置
   */
  private async loadConfiguration(): Promise<void> {
    try {
      // 从数据库加载配置
      const alertThresholds = systemConfigDAO.getConfig('system.alert_thresholds');
      if (alertThresholds) {
        this.monitoringConfig.thresholds = {
          ...this.monitoringConfig.thresholds,
          ...(alertThresholds.config_value as Record<string, any>)
        };
      }

      const healthCheckInterval = systemConfigDAO.getConfig('system.health_check_interval');
      if (healthCheckInterval) {
        this.monitoringConfig.intervals.systemHealth = healthCheckInterval.config_value as number;
      }

      // 检查紧急停止状态
      const emergencyStopConfig = systemConfigDAO.getConfig('system.emergency_stop_enabled');
      if (emergencyStopConfig) {
        this.emergencyStopActive = emergencyStopConfig.config_value as boolean;
      }

      logger.info('总控服务配置加载完成');
    } catch (error) {
      logger.error('加载总控服务配置失败:', error);
      throw error;
    }
  }

  /**
   * 初始化系统状态
   */
  private async initializeSystemStatus(): Promise<void> {
    try {
      // 记录系统启动事件
      systemMonitorDAO.recordSystemEvent({
        event_type: 'system_startup',
        event_category: 'system',
        severity: 'info',
        source_module: 'master',
        title: '系统启动',
        description: '总控模组启动，开始系统监控',
        event_data: {
          startTime: this.systemStartTime.toISOString(),
          nodeVersion: process.version,
          platform: os.platform(),
          arch: os.arch()
        }
      });

      // 初始化模组状态
      const modules = ['trader', 'risk', 'finance', 'master'];
      for (const module of modules) {
        this.moduleStatuses.set(module, {
          name: module,
          status: 'initializing',
          lastHeartbeat: new Date(),
          errorCount: 0
        });
      }

      // 缓存系统信息
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'system_info', {
        startTime: this.systemStartTime.toISOString(),
        version: '1.0.0',
        environment: 'development',
        nodeVersion: process.version,
        platform: os.platform(),
        arch: os.arch()
      }, 3600);

      logger.info('系统状态初始化完成');
    } catch (error) {
      logger.error('初始化系统状态失败:', error);
      throw error;
    }
  }

  /**
   * 设置消息监听
   */
  private setupMessageListeners(): void {
    try {
      // 监听模组心跳
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, async (message: ZMQMessage) => {
        try {
          await this.handleModuleHeartbeat(message.data);
        } catch (error) {
          logger.error('处理模组心跳失败:', error);
        }
      });

      // 监听紧急控制请求
      zmqBus.subscribe(MessageType.EMERGENCY_STOP, async (message: ZMQMessage) => {
        try {
          await this.handleEmergencyControlRequest(message.data as EmergencyControlRequest);
        } catch (error) {
          logger.error('处理紧急控制请求失败:', error);
        }
      });

      // 监听系统警报
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, async (message: ZMQMessage) => {
        try {
          await this.handleSystemAlert(message.data);
        } catch (error) {
          logger.error('处理系统警报失败:', error);
        }
      });

      // 监听配置更新请求
      zmqBus.subscribe(MessageType.SYSTEM_STATUS, async (message: ZMQMessage) => {
        try {
          await this.handleConfigUpdateRequest(message.data);
        } catch (error) {
          logger.error('处理配置更新请求失败:', error);
        }
      });

      logger.info('总控服务消息监听设置完成');
    } catch (error) {
      logger.error('设置总控服务消息监听失败:', error);
      throw error;
    }
  }

  /**
   * 启动系统监控
   */
  private startSystemMonitoring(): void {
    // 系统健康检查
    setInterval(async () => {
      try {
        await this.performSystemHealthCheck();
      } catch (error) {
        logger.error('系统健康检查失败:', error);
      }
    }, this.monitoringConfig.intervals.systemHealth);

    // 性能指标收集
    setInterval(async () => {
      try {
        await this.collectPerformanceMetrics();
      } catch (error) {
        logger.error('收集性能指标失败:', error);
      }
    }, this.monitoringConfig.intervals.performanceMetrics);

    // 模组状态检查
    setInterval(async () => {
      try {
        await this.checkModuleStatuses();
      } catch (error) {
        logger.error('检查模组状态失败:', error);
      }
    }, this.monitoringConfig.intervals.moduleStatus);

    // 警报处理
    setInterval(async () => {
      try {
        await this.processAlertQueue();
      } catch (error) {
        logger.error('处理警报队列失败:', error);
      }
    }, this.monitoringConfig.intervals.alertProcessing);

    logger.info('系统监控启动完成');
  }

  /**
   * 执行系统健康检查
   */
  private async performSystemHealthCheck(): Promise<unknown> {
    try {
      const healthData: Record<string, unknown> = {
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        system: {
          platform: os.platform(),
          arch: os.arch(),
          nodeVersion: process.version,
          totalMemory: os.totalmem(),
          freeMemory: os.freemem(),
          loadAverage: os.loadavg(),
          cpuCount: os.cpus().length
        },
        process: {
          pid: process.pid,
          memoryUsage: process.memoryUsage(),
          cpuUsage: process.cpuUsage()
        },
        modules: Array.from(this.moduleStatuses.values()),
        emergencyStop: this.emergencyStopActive
      };

      // 计算健康评分
      const healthScore = this.calculateHealthScore(healthData);
      healthData.healthScore = healthScore;

      // 缓存健康数据
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'health', healthData, 60);

      // 如果健康评分过低，发送警报
      if (healthScore < 70) {
        await this.createAlert({
          type: 'system_health_degraded',
          severity: healthScore < 50 ? 'critical' : 'warning',
          title: '系统健康状况恶化',
          description: `系统健康评分: ${healthScore}`,
          data: healthData
        });
      }

      return healthData;
    } catch (error) {
      logger.error('执行系统健康检查失败:', error);
      throw error;
    }
  }

  /**
   * 计算健康评分
   */
  private calculateHealthScore(healthData: Record<string, unknown>): number {
    let score = 100;
    const thresholds = this.monitoringConfig.thresholds;

    // CPU使用率评分
    const cpuUsage = ((healthData as any).system.loadAverage[0] / (healthData as any).system.cpuCount) * 100;
    if (cpuUsage > thresholds.cpu.critical) {
      score -= 30;
    } else if (cpuUsage > thresholds.cpu.warning) {
      score -= 15;
    }

    // 内存使用率评分
    const memoryUsage = (((healthData as any).system.totalMemory - (healthData as any).system.freeMemory) / (healthData as any).system.totalMemory) * 100;
    if (memoryUsage > thresholds.memory.critical) {
      score -= 25;
    } else if (memoryUsage > thresholds.memory.warning) {
      score -= 10;
    }

    // 模组状态评分
    const unhealthyModules = (healthData as any).modules.filter((m: Record<string, unknown>) => m.status !== 'healthy').length;
    score -= unhealthyModules * 10;

    // 紧急停止状态
    if (this.emergencyStopActive) {
      score -= 20;
    }

    return Math.max(0, Math.min(100, score));
  }

  /**
   * 收集性能指标
   */
  private async collectPerformanceMetrics(): Promise<void> {
    try {
      const metrics = {
        timestamp: new Date().toISOString(),
        cpu: {
          usage: (os.loadavg()[0] / os.cpus().length) * 100,
          loadAverage: os.loadavg()
        },
        memory: {
          total: os.totalmem(),
          free: os.freemem(),
          used: os.totalmem() - os.freemem(),
          usage: ((os.totalmem() - os.freemem()) / os.totalmem()) * 100
        },
        process: {
          memoryUsage: process.memoryUsage(),
          cpuUsage: process.cpuUsage(),
          uptime: process.uptime()
        }
      };

      // 记录性能指标到数据库
      systemMonitorDAO.recordPerformanceMetric({
        module_name: 'system',
        metric_type: 'resource',
        metric_name: 'cpu_usage',
        metric_value: metrics.cpu.usage,
        unit: 'percent',
        threshold_warning: this.monitoringConfig.thresholds.cpu.warning,
        threshold_critical: this.monitoringConfig.thresholds.cpu.critical
      });

      systemMonitorDAO.recordPerformanceMetric({
        module_name: 'system',
        metric_type: 'resource',
        metric_name: 'memory_usage',
        metric_value: metrics.memory.usage,
        unit: 'percent',
        threshold_warning: this.monitoringConfig.thresholds.memory.warning,
        threshold_critical: this.monitoringConfig.thresholds.memory.critical
      });

      // 缓存最新指标
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'metrics', metrics, 300);

      // 检查阈值并创建警报
      await this.checkMetricThresholds(metrics);

    } catch (error) {
      logger.error('收集性能指标失败:', error);
    }
  }

  /**
   * 检查指标阈值
   */
  private async checkMetricThresholds(metrics: unknown): Promise<void> {
    const thresholds = this.monitoringConfig.thresholds;

    // 检查CPU使用率
    if ((metrics as any).cpu.usage > thresholds.cpu.critical) {
      await this.createAlert({
        type: 'high_cpu_usage',
        severity: 'critical',
        title: 'CPU使用率过高',
        description: `CPU使用率: ${(metrics as any).cpu.usage.toFixed(2)}%`,
        data: { cpuUsage: (metrics as any).cpu.usage, threshold: thresholds.cpu.critical }
      });
    } else if ((metrics as any).cpu.usage > thresholds.cpu.warning) {
      await this.createAlert({
        type: 'high_cpu_usage',
        severity: 'warning',
        title: 'CPU使用率警告',
        description: `CPU使用率: ${(metrics as any).cpu.usage.toFixed(2)}%`,
        data: { cpuUsage: (metrics as any).cpu.usage, threshold: thresholds.cpu.warning }
      });
    }

    // 检查内存使用率
    if ((metrics as any).memory.usage > thresholds.memory.critical) {
      await this.createAlert({
        type: 'high_memory_usage',
        severity: 'critical',
        title: '内存使用率过高',
        description: `内存使用率: ${(metrics as any).memory.usage.toFixed(2)}%`,
        data: { memoryUsage: (metrics as any).memory.usage, threshold: thresholds.memory.critical }
      });
    } else if ((metrics as any).memory.usage > thresholds.memory.warning) {
      await this.createAlert({
        type: 'high_memory_usage',
        severity: 'warning',
        title: '内存使用率警告',
        description: `内存使用率: ${(metrics as any).memory.usage.toFixed(2)}%`,
        data: { memoryUsage: (metrics as any).memory.usage, threshold: thresholds.memory.warning }
      });
    }
  }

  /**
   * 检查模组状态
   */
  private async checkModuleStatuses(): Promise<void> {
    try {
      const currentTime = new Date();
      const heartbeatTimeout = 60000; // 1分钟超时

      for (const [moduleName, moduleStatus] of this.moduleStatuses) {
        const timeSinceHeartbeat = currentTime.getTime() - (moduleStatus as any).lastHeartbeat.getTime();
        
        if (timeSinceHeartbeat > heartbeatTimeout) {
          // 模组心跳超时
          (moduleStatus as any).status = 'offline';
          (moduleStatus as any).errorCount++;

          await this.createAlert({
            type: 'module_heartbeat_timeout',
            severity: 'critical',
            title: '模组心跳超时',
            description: `模组 ${moduleName} 心跳超时`,
            data: { moduleName, timeSinceHeartbeat }
          });

          // 更新数据库中的模组状态
          systemMonitorDAO.updateModuleStatus({
            module_name: moduleName,
            status: 'offline',
            error_count: (moduleStatus as any).errorCount,
            last_heartbeat: (moduleStatus as any).lastHeartbeat.toISOString()
          });
        }
      }
    } catch (error) {
      logger.error('检查模组状态失败:', error);
    }
  }

  /**
   * 处理模组心跳
   */
  private async handleModuleHeartbeat(data: Record<string, unknown>): Promise<void> {
    try {
      const { moduleName, status, metrics, errorCount } = data;
      
      // 更新模组状态
      this.moduleStatuses.set(moduleName as string, {
        name: moduleName as string,
        status: status || 'healthy',
        lastHeartbeat: new Date(),
        errorCount: errorCount || 0,
        metrics: metrics || {}
      });

      // 更新数据库
      systemMonitorDAO.updateModuleStatus({
        module_name: moduleName,
        status: status || 'healthy',
        cpu_usage: (metrics as any)?.cpu || 0,
        memory_usage: (metrics as any)?.memory || 0,
        error_count: errorCount || 0,
        last_heartbeat: new Date().toISOString(),
        metadata: metrics ? JSON.stringify(metrics) : null
      });

      // 如果模组状态异常，创建警报
      if (status && status !== 'healthy') {
        await this.createAlert({
          type: 'module_status_change',
          severity: status === 'critical' ? 'critical' : 'warning',
          title: '模组状态变更',
          description: `模组 ${moduleName} 状态变更为 ${status}`,
          data: { moduleName, status, metrics }
        });
      }
    } catch (error) {
      logger.error('处理模组心跳失败:', error);
    }
  }

  /**
   * 处理紧急控制请求
   */
  async handleEmergencyControlRequest(request: EmergencyControlRequest): Promise<Record<string, unknown>> {
    try {
      logger.warn('收到紧急控制请求:', request);

      // 记录紧急控制事件
      const eventId = systemMonitorDAO.recordSystemEvent({
        event_type: 'emergency_control',
        event_category: 'control',
        severity: request.severity,
        source_module: 'master',
        title: `紧急控制: ${request.action}`,
        description: `${request.reason}`,
        event_data: { ...request } as Record<string, unknown>,
        user_id: request.initiatedBy
      });

      let result: Record<string, unknown> = {
        success: false,
        message: '',
        eventId
      };

      switch (request.action) {
        case 'stop':
          result = await this.executeEmergencyStop(request);
          break;
        case 'pause':
          result = await this.executeEmergencyPause(request);
          break;
        case 'resume':
          result = await this.executeEmergencyResume(request);
          break;
        case 'restart':
          result = await this.executeEmergencyRestart(request);
          break;
        default:
          result.message = `未知的紧急控制动作: ${request.action}`;
      }

      // 发送响应消息
      const responseMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          requestId: request.targetId,
          action: request.action,
          result
        }
      };
      await zmqBus.publish(responseMessage);

      return result;
    } catch (error) {
      logger.error('处理紧急控制请求失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '处理紧急控制请求失败'
      };
    }
  }

  /**
   * 执行紧急停止
   */
  private async executeEmergencyStop(request: EmergencyControlRequest): Promise<Record<string, unknown>> {
    try {
      this.emergencyStopActive = true;
      
      // 更新配置
      systemConfigDAO.updateConfig(
        'system.emergency_stop_enabled',
        { enabled: true } as Record<string, unknown>,
        request.initiatedBy,
        request.reason
      );

      // 发送紧急停止信号给所有模组
      const stopMessage: ZMQMessage = {
        type: MessageType.EMERGENCY_STOP,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          reason: request.reason,
          severity: request.severity,
          strategyId: request.scope === 'strategy' ? request.targetId : undefined,
          moduleId: request.scope === 'module' ? request.targetId : undefined
        }
      };
      await zmqBus.publish(stopMessage);

      // 缓存紧急停止状态
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'emergency_stop', {
        active: true,
        reason: request.reason,
        initiatedBy: request.initiatedBy,
        timestamp: new Date().toISOString()
      }, 3600);

      logger.warn('紧急停止已激活');
      
      return {
        success: true,
        message: '紧急停止已激活',
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('执行紧急停止失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '执行紧急停止失败'
      };
    }
  }

  /**
   * 执行紧急暂停
   */
  private async executeEmergencyPause(request: EmergencyControlRequest): Promise<Record<string, unknown>> {
    try {
      // 发送暂停信号
      const pauseMessage: ZMQMessage = {
        type: MessageType.EMERGENCY_STOP,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          reason: request.reason,
          severity: request.severity,
          strategyId: request.scope === 'strategy' ? request.targetId : undefined,
          moduleId: request.scope === 'module' ? request.targetId : undefined
        }
      };
      await zmqBus.publish(pauseMessage);

      return {
        success: true,
        message: '紧急暂停已执行',
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('执行紧急暂停失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '执行紧急暂停失败'
      };
    }
  }

  /**
   * 执行紧急恢复
   */
  private async executeEmergencyResume(request: EmergencyControlRequest): Promise<Record<string, unknown>> {
    try {
      this.emergencyStopActive = false;
      
      // 更新配置
      systemConfigDAO.updateConfig(
        'system.emergency_stop_enabled',
        { enabled: false } as Record<string, unknown>,
        request.initiatedBy,
        request.reason
      );

      // 发送恢复信号
      const recoveryMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          reason: request.reason,
          strategyId: request.scope === 'strategy' ? request.targetId : undefined,
          moduleId: request.scope === 'module' ? request.targetId : undefined
        }
      };
      await zmqBus.publish(recoveryMessage);

      // 清除紧急停止状态
      await redisCache.delete(CacheKeyType.SYSTEM_CONFIG, 'emergency_stop');

      logger.info('系统恢复已执行');
      
      return {
        success: true,
        message: '系统恢复已执行',
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('执行系统恢复失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '执行系统恢复失败'
      };
    }
  }

  /**
   * 执行紧急重启
   */
  private async executeEmergencyRestart(request: EmergencyControlRequest): Promise<Record<string, unknown>> {
    try {
      // 发送重启信号
      const restartMessage: ZMQMessage = {
        type: MessageType.EMERGENCY_STOP,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          reason: request.reason,
          severity: request.severity,
          strategyId: request.scope === 'strategy' ? request.targetId : undefined,
          moduleId: request.scope === 'module' ? request.targetId : undefined
        }
      };
      await zmqBus.publish(restartMessage);

      return {
        success: true,
        message: '紧急重启已执行',
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('执行紧急重启失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '执行紧急重启失败'
      };
    }
  }

  /**
   * 处理系统警报
   */
  private async handleSystemAlert(alertData: Record<string, unknown>): Promise<void> {
    try {
      // 添加到警报队列
      this.alertQueue.push({
        ...alertData,
        receivedAt: new Date().toISOString(),
        processed: false
      });

      // 如果是紧急警报，立即处理
      if (alertData.severity === 'critical') {
        await this.processAlert(alertData);
      }
    } catch (error) {
      logger.error('处理系统警报失败:', error);
    }
  }

  /**
   * 处理配置更新请求
   */
  private async handleConfigUpdateRequest(data: Record<string, unknown>): Promise<void> {
    try {
      const { configKey, configValue, updatedBy, reason } = data;
      
      const success = systemConfigDAO.updateConfig(configKey as string, configValue as Record<string, unknown>, updatedBy as string, reason as string);
      
      if (success) {
        // 重新加载配置
        await this.loadConfiguration();
        
        // 发送配置更新通知
        const configMessage: ZMQMessage = {
          type: MessageType.SYSTEM_STATUS,
          timestamp: new Date().toISOString(),
          source: 'master_module',
          data: {
            configKey: configKey as string,
            configValue,
            updatedBy: updatedBy as string
          }
        };
        await zmqBus.publish(configMessage);
        
        logger.info(`配置 ${configKey} 已更新`);
      } else {
        logger.error(`配置 ${configKey} 更新失败`);
      }
    } catch (error) {
      logger.error('处理配置更新请求失败:', error);
    }
  }

  /**
   * 创建警报
   */
  private async createAlert(alertData: Record<string, unknown>): Promise<void> {
    try {
      // 记录到数据库
      const eventId = systemMonitorDAO.recordSystemEvent({
        event_type: alertData.type,
        event_category: 'alert',
        severity: alertData.severity,
        source_module: 'master',
        title: alertData.title,
        description: alertData.description,
        event_data: alertData.data
      });

      // 发送警报消息
      const alertMessage: ZMQMessage = {
        type: MessageType.SYSTEM_STATUS,
        timestamp: new Date().toISOString(),
        source: 'master_module',
        data: {
          ...alertData,
          eventId
        }
      };
      await zmqBus.publish(alertMessage);

      // 添加到警报队列
      this.alertQueue.push({
        ...alertData,
        eventId,
        createdAt: new Date().toISOString(),
        processed: false
      });
    } catch (error) {
      logger.error('创建警报失败:', error);
    }
  }

  /**
   * 处理警报队列
   */
  private async processAlertQueue(): Promise<void> {
    try {
      const unprocessedAlerts = this.alertQueue.filter(alert => !(alert as any).processed);
      
      for (const alert of unprocessedAlerts) {
        await this.processAlert(alert);
        (alert as any).processed = true;
      }

      // 清理已处理的警报
      this.alertQueue = this.alertQueue.filter(alert => !(alert as any).processed);
    } catch (error) {
      logger.error('处理警报队列失败:', error);
    }
  }

  /**
   * 处理单个警报
   */
  private async processAlert(alert: Record<string, any>): Promise<void> {
    try {
      // 根据警报类型和严重程度执行相应操作
      if (alert.severity === 'critical') {
        // 紧急警报处理逻辑
        logger.error(`紧急警报: ${alert.title} - ${alert.description}`);
        
        // 可以在这里添加自动响应逻辑
        // 例如：自动重启模组、发送通知等
      } else {
        logger.warn(`警报: ${alert.title} - ${alert.description}`);
      }
    } catch (error) {
      logger.error('处理警报失败:', error);
    }
  }

  /**
   * 获取系统概览
   */
  async getSystemOverview(): Promise<unknown> {
    try {
      const healthData = await this.performSystemHealthCheck();
      const moduleStatuses = systemMonitorDAO.getAllModuleStatus();
      const recentEvents = systemMonitorDAO.getSystemEvents({ hours: 24 }, 50);
      const eventStats = systemMonitorDAO.getEventStatistics(24);
      
      return {
        health: healthData,
        modules: moduleStatuses,
        events: {
          recent: recentEvents,
          statistics: eventStats
        },
        emergencyStop: this.emergencyStopActive,
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('获取系统概览失败:', error);
      throw error;
    }
  }

  /**
   * 获取性能指标
   */
  async getPerformanceMetrics(moduleName?: string, hours: number = 24): Promise<unknown> {
    try {
      return systemMonitorDAO.getPerformanceMetrics(moduleName, undefined, hours);
    } catch (error) {
      logger.error('获取性能指标失败:', error);
      throw error;
    }
  }

  /**
   * 更新配置
   */
  async updateConfiguration(newConfig: Record<string, unknown>): Promise<void> {
    try {
      this.monitoringConfig = { ...this.monitoringConfig, ...newConfig };
      
      // 缓存新配置
      await redisCache.set(CacheKeyType.SYSTEM_CONFIG, 'config', this.monitoringConfig, 3600);
      
      logger.info('总控服务配置更新完成');
    } catch (error) {
      logger.error('更新总控服务配置失败:', error);
      throw error;
    }
  }

  /**
   * 获取服务状态
   */
  getStatus(): unknown {
    return {
      initialized: this.isInitialized,
      emergencyStopActive: this.emergencyStopActive,
      systemStartTime: this.systemStartTime.toISOString(),
      uptime: process.uptime(),
      moduleCount: this.moduleStatuses.size,
      alertQueueSize: this.alertQueue.length,
      configuration: this.monitoringConfig,
      timestamp: new Date().toISOString()
    };
  }
}

// 创建总控服务实例
export const masterService = new MasterService();

// 默认导出
export default masterService;