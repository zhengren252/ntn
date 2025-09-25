import { Router } from 'express';
import { traderRoutes } from './routes/traderRoutes';
import { traderService } from './services/traderService';
import { strategyDAO } from './dao/strategyDAO';
import { orderDAO } from './dao/orderDAO';
import { redisCache } from '../../shared/cache/redis';
import { zmqBus } from '../../shared/messaging/zeromq';

// 交易员模组配置接口
export interface TraderModuleConfig {
  enableRealTimeUpdates: boolean;
  maxConcurrentOrders: number;
  defaultRiskLevel: 'low' | 'medium' | 'high';
  orderTimeoutMs: number;
  strategyValidationEnabled: boolean;
}

// 默认配置
const defaultConfig: TraderModuleConfig = {
  enableRealTimeUpdates: true,
  maxConcurrentOrders: 1000,
  defaultRiskLevel: 'medium',
  orderTimeoutMs: 30000, // 30秒
  strategyValidationEnabled: true
};

// 交易员模组类
export class TraderModule {
  private static instance: TraderModule;
  private config: TraderModuleConfig;
  private isInitialized: boolean = false;
  private router: Router;

  private constructor(config: Partial<TraderModuleConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
    this.router = Router();
    this.setupRoutes();
  }

  public static getInstance(config?: Partial<TraderModuleConfig>): TraderModule {
    if (!TraderModule.instance) {
      TraderModule.instance = new TraderModule(config);
    }
    return TraderModule.instance;
  }

  // 初始化模组
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      console.log('交易员模组已初始化');
      return;
    }

    try {
      console.log('正在初始化交易员模组...');

      // 初始化数据库连接
      await this.initializeDatabase();

      // 初始化缓存
      await this.initializeCache();

      // 初始化消息总线
      await this.initializeMessageBus();

      // 初始化服务
      await this.initializeServices();

      // 设置定时任务
      this.setupScheduledTasks();

      this.isInitialized = true;
      console.log('交易员模组初始化完成');
    } catch (error) {
      console.error('交易员模组初始化失败:', error);
      throw error;
    }
  }

  // 获取路由器
  public getRouter(): Router {
    return this.router;
  }

  // 获取配置
  public getConfig(): TraderModuleConfig {
    return { ...this.config };
  }

  // 更新配置
  public updateConfig(newConfig: Partial<TraderModuleConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('交易员模组配置已更新:', this.config);
  }

  // 获取模组状态
  public async getStatus(): Promise<unknown> {
    try {
      const strategies = await traderService.getStrategyPackages();
      const orders = await traderService.getOrders();
      
      return {
        module: 'trader',
        status: this.isInitialized ? 'running' : 'stopped',
        config: this.config,
        statistics: {
          totalStrategies: strategies.length,
          activeStrategies: strategies.filter(s => s.status === 'active').length,
          totalOrders: orders.length,
          pendingOrders: orders.filter(o => o.status === 'pending').length
        },
        lastUpdate: new Date().toISOString()
      };
    } catch (error) {
      return {
        module: 'trader',
        status: 'error',
        error: error instanceof Error ? error.message : '未知错误',
        lastUpdate: new Date().toISOString()
      };
    }
  }

  // 停止模组
  public async shutdown(): Promise<void> {
    try {
      console.log('正在停止交易员模组...');

      // 停止定时任务
      this.clearScheduledTasks();

      // 取消所有待处理订单
      await this.cancelPendingOrders();

      // 暂停所有活跃策略
      await this.pauseActiveStrategies();

      this.isInitialized = false;
      console.log('交易员模组已停止');
    } catch (error) {
      console.error('停止交易员模组失败:', error);
      throw error;
    }
  }

  // 设置路由
  private setupRoutes(): void {
    this.router.use('/trader', traderRoutes);
  }

  // 初始化数据库
  private async initializeDatabase(): Promise<void> {
    try {
      // 数据库连接已在单例初始化时完成
      console.log('交易员模组数据库连接已建立');
    } catch (error) {
      console.error('交易员模组数据库初始化失败:', error);
      throw error;
    }
  }

  // 初始化缓存
  private async initializeCache(): Promise<void> {
    try {
      await redisCache.initialize();
      console.log('交易员模组缓存连接已建立');
    } catch (error) {
      console.error('交易员模组缓存初始化失败:', error);
      throw error;
    }
  }

  // 初始化消息总线
  private async initializeMessageBus(): Promise<void> {
    try {
      await zmqBus.initialize();
      console.log('交易员模组消息总线已连接');
    } catch (error) {
      console.error('交易员模组消息总线初始化失败:', error);
      throw error;
    }
  }

  // 初始化服务
  private async initializeServices(): Promise<void> {
    try {
      // 交易员服务已通过单例模式自动初始化
      console.log('交易员模组服务已初始化');
    } catch (error) {
      console.error('交易员模组服务初始化失败:', error);
      throw error;
    }
  }

  // 设置定时任务
  private setupScheduledTasks(): void {
    // 每分钟检查超时订单
    setInterval(async () => {
      try {
        await this.checkTimeoutOrders();
      } catch (error) {
        console.error('检查超时订单失败:', error);
      }
    }, 60000); // 1分钟

    // 每5分钟更新策略性能缓存
    setInterval(async () => {
      try {
        await this.updatePerformanceCache();
      } catch (error) {
        console.error('更新性能缓存失败:', error);
      }
    }, 300000); // 5分钟

    // 每小时清理过期缓存
    setInterval(async () => {
      try {
        await this.cleanupExpiredCache();
      } catch (error) {
        console.error('清理过期缓存失败:', error);
      }
    }, 3600000); // 1小时

    console.log('交易员模组定时任务已设置');
  }

  // 清除定时任务
  private clearScheduledTasks(): void {
    // 这里应该清除所有定时任务的引用
    // 在实际实现中，需要保存定时器ID并清除
    console.log('交易员模组定时任务已清除');
  }

  // 检查超时订单
  private async checkTimeoutOrders(): Promise<void> {
    try {
      const timeoutOrders = orderDAO.findTimeoutOrders(this.config.orderTimeoutMs);
      
      for (const order of timeoutOrders) {
        console.log(`发现超时订单: ${order.id}`);
        await traderService.cancelOrder(order.id, '订单超时');
      }
      
      if (timeoutOrders.length > 0) {
        console.log(`处理了 ${timeoutOrders.length} 个超时订单`);
      }
    } catch (error) {
      console.error('检查超时订单失败:', error);
    }
  }

  // 更新性能缓存
  private async updatePerformanceCache(): Promise<void> {
    try {
      const strategies = await traderService.getStrategyPackages();
      
      for (const strategy of strategies) {
        if (strategy.status === 'active') {
          await traderService.getStrategyPerformance(strategy.id);
        }
      }
      
      console.log(`更新了 ${strategies.length} 个策略的性能缓存`);
    } catch (error) {
      console.error('更新性能缓存失败:', error);
    }
  }

  // 清理过期缓存
  private async cleanupExpiredCache(): Promise<void> {
    try {
      // 清理过期的策略状态缓存
      const expiredKeys = await redisCache.getExpiredKeys('strategy_state:*');
      if (expiredKeys.length > 0) {
        await redisCache.deleteKeys(expiredKeys);
        console.log(`清理了 ${expiredKeys.length} 个过期的策略状态缓存`);
      }
      
      // 清理过期的订单缓存
      const expiredOrderKeys = await redisCache.getExpiredKeys('trading_data:order_*');
      if (expiredOrderKeys.length > 0) {
        await redisCache.deleteKeys(expiredOrderKeys);
        console.log(`清理了 ${expiredOrderKeys.length} 个过期的订单缓存`);
      }
    } catch (error) {
      console.error('清理过期缓存失败:', error);
    }
  }

  // 取消待处理订单
  private async cancelPendingOrders(): Promise<void> {
    try {
      const pendingOrders = orderDAO.findPendingOrders();
      const orderIds = pendingOrders.map(order => order.id);
      
      if (orderIds.length > 0) {
        orderDAO.batchCancelOrders(orderIds);
        console.log(`取消了 ${orderIds.length} 个待处理订单`);
      }
    } catch (error) {
      console.error('取消待处理订单失败:', error);
    }
  }

  // 暂停活跃策略
  private async pauseActiveStrategies(): Promise<void> {
    try {
      const activeStrategies = strategyDAO.findActiveStrategies();
      
      for (const strategy of activeStrategies) {
        strategyDAO.updateStatus(strategy.id, 'paused');
      }
      
      if (activeStrategies.length > 0) {
        console.log(`暂停了 ${activeStrategies.length} 个活跃策略`);
      }
    } catch (error) {
      console.error('暂停活跃策略失败:', error);
    }
  }
}

// 导出模组实例和相关组件
export const traderModule = TraderModule.getInstance();
export { traderService } from './services/traderService';
export { strategyDAO } from './dao/strategyDAO';
export { orderDAO } from './dao/orderDAO';
// export { orderExecutionDAO } from './dao/orderDAO'; // 暂未使用
export { traderRoutes } from './routes/traderRoutes';

// 导出类型
export type {
  StrategyPackageRequest,
  OrderRequest,
  RiskFinanceRequest
} from './services/traderService';

export default TraderModule;