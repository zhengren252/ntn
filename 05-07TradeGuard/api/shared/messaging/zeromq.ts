import * as zmq from 'zeromq';
import { readFileSync } from 'fs';
import { join } from 'path';
import yaml from 'yaml';
import { EventEmitter } from 'events';

// ZeroMQ配置接口
interface ZeroMQConfig {
  zeromq: {
    publisher: {
      port: number;
      bind: string;
    };
    subscriber: {
      endpoints: string[];
    };
    request: {
      port: number;
      bind: string;
      timeout: number;
    };
    reply: {
      endpoints: string[];
      timeout: number;
    };
  };
}

// 消息类型枚举
export enum MessageType {
  TRADING_SIGNAL = 'trading_signal',
  RISK_ALERT = 'risk.alerts',
  FUND_REQUEST = 'fund_request',
  FUND_RESPONSE = 'fund_response',
  ORDER_UPDATE = 'order_update',
  POSITION_UPDATE = 'position_update',
  MARKET_DATA = 'market_data',
  SYSTEM_STATUS = 'system_status',
  STRATEGY_UPDATE = 'strategy_update',
  EMERGENCY_STOP = 'emergency_stop',
  BUDGET_REQUEST = 'budget.request',
  FUND_ALLOCATION_REQUEST = 'fund.allocation.request',
  RISK_ASSESSMENT_RESULT = 'risk.assessment.result',
  SYSTEM_RECOVERY = 'system.recovery',
  REVIEWGUARD_POOL_APPROVED = 'reviewguard.pool.approved'
}

// 消息接口
export interface ZMQMessage {
  type: MessageType;
  timestamp: string;
  source: string;
  target?: string;
  data: Record<string, unknown>;
  correlationId?: string;
}

// ZeroMQ消息总线类
class ZeroMQBus extends EventEmitter {
  private static instance: ZeroMQBus;
  private config: ZeroMQConfig;
  private publisher: zmq.Publisher | null = null;
  private subscriber: zmq.Subscriber | null = null;
  private router: zmq.Router | null = null;
  private dealer: zmq.Dealer | null = null;
  private isInitialized: boolean = false;
  private pendingRequests: Map<string, { resolve: (value: ZMQMessage) => void; reject: (reason?: unknown) => void; timeout: NodeJS.Timeout }> = new Map();

  private constructor() {
    super();
    this.loadConfig();
  }

  // 单例模式获取实例
  public static getInstance(): ZeroMQBus {
    if (!ZeroMQBus.instance) {
      ZeroMQBus.instance = new ZeroMQBus();
    }
    return ZeroMQBus.instance;
  }

  // 加载配置文件
  private loadConfig(): void {
    const env = process.env.APP_ENV || 'development';
    const configPath = join(process.cwd(), 'config', `${env}.yaml`);
    
    try {
      const configFile = readFileSync(configPath, 'utf8');
      this.config = yaml.parse(configFile) as ZeroMQConfig;
    } catch {
      console.warn(`ZeroMQ配置文件 ${configPath} 加载失败，使用默认配置`);
      this.config = {
        zeromq: {
          publisher: {
            port: 5555,
            bind: 'tcp://*:5555'
          },
          subscriber: {
            endpoints: ['tcp://localhost:5555']
          },
          request: {
            port: 5556,
            bind: 'tcp://*:5556',
            timeout: 5000
          },
          reply: {
            endpoints: ['tcp://localhost:5556'],
            timeout: 5000
          }
        }
      };
    }
  }

  // 初始化ZeroMQ套接字
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      console.log('ZeroMQ总线已初始化');
      return;
    }

    try {
      await this.initializePublisher();
      await this.initializeSubscriber();
      await this.initializeRouter();
      await this.initializeDealer();
      
      this.isInitialized = true;
      console.log('ZeroMQ消息总线初始化完成');
    } catch (error) {
      console.error('ZeroMQ初始化失败:', error);
      throw error;
    }
  }

  // 初始化发布者
  private async initializePublisher(): Promise<void> {
    this.publisher = new zmq.Publisher();
    await this.publisher.bind(this.config.zeromq.publisher.bind);
    console.log(`Publisher绑定到: ${this.config.zeromq.publisher.bind}`);
  }

  // 初始化订阅者
  private async initializeSubscriber(): Promise<void> {
    this.subscriber = new zmq.Subscriber();
    
    // 连接到所有发布端点
    for (const endpoint of this.config.zeromq.subscriber.endpoints) {
      this.subscriber.connect(endpoint);
      console.log(`Subscriber连接到: ${endpoint}`);
    }

    // 订阅所有消息类型
    for (const messageType of Object.values(MessageType)) {
      this.subscriber.subscribe(messageType);
    }

    // 启动消息接收循环
    this.startSubscriberLoop();
  }

  // 初始化路由器(服务端)
  private async initializeRouter(): Promise<void> {
    this.router = new zmq.Router();
    await this.router.bind(this.config.zeromq.request.bind);
    console.log(`Router绑定到: ${this.config.zeromq.request.bind}`);
    
    // 启动请求处理循环
    this.startRouterLoop();
  }

  // 初始化经销商(客户端)
  private async initializeDealer(): Promise<void> {
    this.dealer = new zmq.Dealer();
    
    // 连接到所有回复端点
    for (const endpoint of this.config.zeromq.reply.endpoints) {
      this.dealer.connect(endpoint);
      console.log(`Dealer连接到: ${endpoint}`);
    }

    // 启动回复接收循环
    this.startDealerLoop();
  }

  // 发布消息
  public async publish(message: ZMQMessage): Promise<boolean> {
    if (!this.publisher || !this.isInitialized) {
      console.error('Publisher未初始化');
      return false;
    }

    try {
      const serializedMessage = JSON.stringify({
        ...message,
        timestamp: message.timestamp || new Date().toISOString()
      });

      await this.publisher.send([message.type, serializedMessage]);
      console.log(`消息已发布: ${message.type}`);
      return true;
    } catch (error) {
      console.error('发布消息失败:', error);
      return false;
    }
  }

  // 订阅消息
  public subscribe(messageType: MessageType, callback: (message: ZMQMessage) => void): void {
    this.on(messageType, callback);
  }

  // 取消订阅
  public unsubscribe(messageType: MessageType, callback?: (message: ZMQMessage) => void): void {
    if (callback) {
      this.off(messageType, callback);
    } else {
      this.removeAllListeners(messageType);
    }
  }

  // 发送请求
  public async request(message: ZMQMessage): Promise<ZMQMessage> {
    if (!this.dealer || !this.isInitialized) {
      throw new Error('Dealer未初始化');
    }

    return new Promise((resolve, reject) => {
      const correlationId = message.correlationId || this.generateCorrelationId();
      const requestMessage = {
        ...message,
        correlationId,
        timestamp: message.timestamp || new Date().toISOString()
      };

      // 设置超时
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(correlationId);
        reject(new Error('请求超时'));
      }, this.config.zeromq.request.timeout);

      // 存储待处理请求
      this.pendingRequests.set(correlationId, { resolve, reject, timeout });

      // 发送请求
      this.dealer!.send([JSON.stringify(requestMessage)])
        .catch(error => {
          this.pendingRequests.delete(correlationId);
          clearTimeout(timeout);
          reject(error);
        });
    });
  }

  // 注册请求处理器
  public onRequest(messageType: MessageType, handler: (message: ZMQMessage) => Promise<string>): void {
    this.on(`request:${messageType}`, async (clientId: string, message: ZMQMessage) => {
      try {
        const result = await handler(message);
        const response: ZMQMessage = {
          type: message.type,
          timestamp: new Date().toISOString(),
          source: 'server',
          target: message.source,
          data: { result },
          correlationId: message.correlationId
        };

        if (this.router) {
          await this.router.send([clientId, JSON.stringify(response)]);
        }
      } catch (error) {
        const errorResponse: ZMQMessage = {
          type: message.type,
          timestamp: new Date().toISOString(),
          source: 'server',
          target: message.source,
          data: { error: error instanceof Error ? error.message : '未知错误' },
          correlationId: message.correlationId
        };

        if (this.router) {
          await this.router.send([clientId, JSON.stringify(errorResponse)]);
        }
      }
    });
  }

  // 启动订阅者消息循环
  private async startSubscriberLoop(): Promise<void> {
    if (!this.subscriber) return;

    for await (const [topic, message] of this.subscriber) {
      try {
        const messageType = topic.toString() as MessageType;
        const parsedMessage = JSON.parse(message.toString()) as ZMQMessage;
        
        // 触发事件
        this.emit(messageType, parsedMessage);
        this.emit('message', parsedMessage);
      } catch (error) {
        console.error('处理订阅消息失败:', error);
      }
    }
  }

  // 启动路由器消息循环
  private async startRouterLoop(): Promise<void> {
    if (!this.router) return;

    for await (const [clientId, message] of this.router) {
      try {
        const parsedMessage = JSON.parse(message.toString()) as ZMQMessage;
        
        // 触发请求事件
        this.emit(`request:${parsedMessage.type}`, clientId.toString(), parsedMessage);
      } catch (error) {
        console.error('处理路由器消息失败:', error);
      }
    }
  }

  // 启动经销商消息循环
  private async startDealerLoop(): Promise<void> {
    if (!this.dealer) return;

    for await (const [message] of this.dealer) {
      try {
        const parsedMessage = JSON.parse(message.toString()) as ZMQMessage;
        
        if (parsedMessage.correlationId) {
          const pendingRequest = this.pendingRequests.get(parsedMessage.correlationId);
          if (pendingRequest) {
            clearTimeout(pendingRequest.timeout);
            this.pendingRequests.delete(parsedMessage.correlationId);
            pendingRequest.resolve(parsedMessage);
          }
        }
      } catch (error) {
        console.error('处理经销商消息失败:', error);
      }
    }
  }

  // 生成关联ID
  private generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // 广播紧急停止信号
  public async emergencyStop(reason: string): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.EMERGENCY_STOP,
      timestamp: new Date().toISOString(),
      source: 'system',
      data: { reason }
    };

    await this.publish(message);
    console.log(`紧急停止信号已发送: ${reason}`);
  }

  // 发送系统状态更新
  public async updateSystemStatus(status: unknown): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.SYSTEM_STATUS,
      timestamp: new Date().toISOString(),
      source: 'system',
      data: { status }
    };

    await this.publish(message);
  }

  // 获取统计信息
  public getStats(): unknown {
    return {
      isInitialized: this.isInitialized,
      pendingRequests: this.pendingRequests.size,
      listenerCount: this.eventNames().reduce((total, event) => {
        return total + this.listenerCount(event);
      }, 0)
    };
  }

  // 关闭所有连接
  public async close(): Promise<void> {
    console.log('正在关闭ZeroMQ连接...');

    // 清理待处理请求
    for (const [, request] of this.pendingRequests) {
      clearTimeout(request.timeout);
      request.reject(new Error('连接已关闭'));
    }
    this.pendingRequests.clear();

    // 关闭套接字
    if (this.publisher) {
      this.publisher.close();
    }
    if (this.subscriber) {
      this.subscriber.close();
    }
    if (this.router) {
      this.router.close();
    }
    if (this.dealer) {
      this.dealer.close();
    }

    this.isInitialized = false;
    console.log('ZeroMQ连接已关闭');
  }
}

// 导出单例实例
export const zmqBus = ZeroMQBus.getInstance();
export default ZeroMQBus;