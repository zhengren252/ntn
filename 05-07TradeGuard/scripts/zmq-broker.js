/**
 * 交易执行铁三角项目 - ZeroMQ消息代理
 * 用途：作为各模组间的消息中转站，实现解耦通信
 */

const zmq = require('zeromq');
const fs = require('fs');
const path = require('path');

// 配置
const CONFIG = {
  // 前端端口 - 接收来自客户端的消息
  FRONTEND_PORT: 5555,
  // 后端端口 - 转发给后端服务
  BACKEND_PORT: 5556,
  // 发布端口 - 广播消息
  PUBLISHER_PORT: 5557,
  // 订阅端口 - 接收订阅
  SUBSCRIBER_PORT: 5558,
  // 心跳间隔 (毫秒)
  HEARTBEAT_INTERVAL: 5000,
  // 日志级别
  LOG_LEVEL: process.env.LOG_LEVEL || 'info'
};

// 日志工具
class Logger {
  constructor(level = 'info') {
    this.levels = { error: 0, warn: 1, info: 2, debug: 3 };
    this.level = this.levels[level] || 2;
  }

  log(level, message, data = null) {
    if (this.levels[level] <= this.level) {
      const timestamp = new Date().toISOString();
      const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
      
      if (data) {
        console.log(logMessage, data);
      } else {
        console.log(logMessage);
      }
    }
  }

  error(message, data) { this.log('error', message, data); }
  warn(message, data) { this.log('warn', message, data); }
  info(message, data) { this.log('info', message, data); }
  debug(message, data) { this.log('debug', message, data); }
}

// 消息统计
class MessageStats {
  constructor() {
    this.stats = {
      received: 0,
      sent: 0,
      errors: 0,
      startTime: Date.now()
    };
  }

  increment(type) {
    this.stats[type]++;
  }

  getStats() {
    const uptime = Date.now() - this.stats.startTime;
    return {
      ...this.stats,
      uptime: Math.floor(uptime / 1000),
      messagesPerSecond: this.stats.received / (uptime / 1000)
    };
  }
}

// ZeroMQ代理类
class ZMQBroker {
  constructor() {
    this.logger = new Logger(CONFIG.LOG_LEVEL);
    this.stats = new MessageStats();
    this.isRunning = false;
    this.sockets = {};
    this.connectedClients = new Set();
    this.heartbeatInterval = null;
  }

  async initialize() {
    try {
      this.logger.info('初始化ZeroMQ代理...');

      // 创建套接字
      await this.createSockets();
      
      // 设置消息处理
      this.setupMessageHandling();
      
      // 启动心跳
      this.startHeartbeat();
      
      this.isRunning = true;
      this.logger.info('ZeroMQ代理初始化完成');
      
    } catch (error) {
      this.logger.error('ZeroMQ代理初始化失败:', error);
      throw error;
    }
  }

  async createSockets() {
    // 路由器套接字 - 处理请求/响应
    this.sockets.router = new zmq.Router();
    await this.sockets.router.bind(`tcp://*:${CONFIG.FRONTEND_PORT}`);
    this.logger.info(`路由器套接字绑定到端口 ${CONFIG.FRONTEND_PORT}`);

    // 经销商套接字 - 负载均衡到后端
    this.sockets.dealer = new zmq.Dealer();
    await this.sockets.dealer.bind(`tcp://*:${CONFIG.BACKEND_PORT}`);
    this.logger.info(`经销商套接字绑定到端口 ${CONFIG.BACKEND_PORT}`);

    // 发布者套接字 - 广播消息
    this.sockets.publisher = new zmq.Publisher();
    await this.sockets.publisher.bind(`tcp://*:${CONFIG.PUBLISHER_PORT}`);
    this.logger.info(`发布者套接字绑定到端口 ${CONFIG.PUBLISHER_PORT}`);

    // 订阅者套接字 - 接收订阅消息
    this.sockets.subscriber = new zmq.Subscriber();
    await this.sockets.subscriber.bind(`tcp://*:${CONFIG.SUBSCRIBER_PORT}`);
    this.logger.info(`订阅者套接字绑定到端口 ${CONFIG.SUBSCRIBER_PORT}`);
  }

  setupMessageHandling() {
    // 处理来自前端的消息
    this.handleFrontendMessages();
    
    // 处理来自后端的消息
    this.handleBackendMessages();
    
    // 处理订阅消息
    this.handleSubscriberMessages();
  }

  async handleFrontendMessages() {
    this.logger.info('开始监听前端消息...');
    
    for await (const [identity, ...frames] of this.sockets.router) {
      try {
        this.stats.increment('received');
        
        const message = this.parseMessage(frames);
        this.logger.debug('收到前端消息:', { identity: identity.toString(), message });
        
        // 记录客户端连接
        this.connectedClients.add(identity.toString());
        
        // 根据消息类型处理
        await this.routeMessage(identity, message);
        
      } catch (error) {
        this.stats.increment('errors');
        this.logger.error('处理前端消息失败:', error);
        
        // 发送错误响应
        await this.sendErrorResponse(identity, error.message);
      }
    }
  }

  async handleBackendMessages() {
    this.logger.info('开始监听后端消息...');
    
    for await (const frames of this.sockets.dealer) {
      try {
        const message = this.parseMessage(frames);
        this.logger.debug('收到后端消息:', message);
        
        // 转发给相应的前端客户端
        if (message.clientId) {
          await this.forwardToClient(message.clientId, message);
        } else {
          // 广播消息
          await this.broadcastMessage(message);
        }
        
      } catch (error) {
        this.stats.increment('errors');
        this.logger.error('处理后端消息失败:', error);
      }
    }
  }

  async handleSubscriberMessages() {
    this.logger.info('开始监听订阅消息...');
    
    // 订阅所有主题
    this.sockets.subscriber.subscribe('');
    
    for await (const [topic, ...frames] of this.sockets.subscriber) {
      try {
        const message = this.parseMessage(frames);
        this.logger.debug('收到订阅消息:', { topic: topic.toString(), message });
        
        // 转发订阅消息
        await this.forwardSubscriptionMessage(topic.toString(), message);
        
      } catch (error) {
        this.stats.increment('errors');
        this.logger.error('处理订阅消息失败:', error);
      }
    }
  }

  async routeMessage(clientId, message) {
    const { type, target, data } = message;
    
    switch (type) {
      case 'request':
        // 转发请求到后端
        await this.forwardToBackend(clientId, message);
        break;
        
      case 'subscribe':
        // 处理订阅请求
        await this.handleSubscription(clientId, data.topic);
        break;
        
      case 'unsubscribe':
        // 处理取消订阅
        await this.handleUnsubscription(clientId, data.topic);
        break;
        
      case 'heartbeat':
        // 响应心跳
        await this.sendHeartbeatResponse(clientId);
        break;
        
      default:
        throw new Error(`未知的消息类型: ${type}`);
    }
  }

  async forwardToBackend(clientId, message) {
    const forwardMessage = {
      ...message,
      clientId: clientId.toString(),
      timestamp: Date.now()
    };
    
    await this.sockets.dealer.send(this.serializeMessage(forwardMessage));
    this.stats.increment('sent');
    
    this.logger.debug('消息已转发到后端:', forwardMessage);
  }

  async forwardToClient(clientId, message) {
    try {
      await this.sockets.router.send([clientId, this.serializeMessage(message)]);
      this.stats.increment('sent');
      
      this.logger.debug('消息已转发到客户端:', { clientId, message });
    } catch (error) {
      this.logger.error('转发消息到客户端失败:', error);
      // 移除断开连接的客户端
      this.connectedClients.delete(clientId);
    }
  }

  async broadcastMessage(message) {
    const topic = message.topic || 'broadcast';
    await this.sockets.publisher.send([topic, this.serializeMessage(message)]);
    this.stats.increment('sent');
    
    this.logger.debug('广播消息:', { topic, message });
  }

  async forwardSubscriptionMessage(topic, message) {
    // 转发给所有订阅了该主题的客户端
    for (const clientId of this.connectedClients) {
      try {
        const forwardMessage = {
          type: 'subscription',
          topic,
          data: message,
          timestamp: Date.now()
        };
        
        await this.forwardToClient(clientId, forwardMessage);
      } catch (error) {
        this.logger.error(`转发订阅消息到客户端 ${clientId} 失败:`, error);
      }
    }
  }

  async handleSubscription(clientId, topic) {
    this.logger.info(`客户端 ${clientId} 订阅主题: ${topic}`);
    
    // 发送订阅确认
    const response = {
      type: 'subscription_ack',
      topic,
      status: 'success',
      timestamp: Date.now()
    };
    
    await this.forwardToClient(clientId, response);
  }

  async handleUnsubscription(clientId, topic) {
    this.logger.info(`客户端 ${clientId} 取消订阅主题: ${topic}`);
    
    // 发送取消订阅确认
    const response = {
      type: 'unsubscription_ack',
      topic,
      status: 'success',
      timestamp: Date.now()
    };
    
    await this.forwardToClient(clientId, response);
  }

  async sendHeartbeatResponse(clientId) {
    const response = {
      type: 'heartbeat_ack',
      timestamp: Date.now(),
      stats: this.stats.getStats()
    };
    
    await this.forwardToClient(clientId, response);
  }

  async sendErrorResponse(clientId, errorMessage) {
    const response = {
      type: 'error',
      error: errorMessage,
      timestamp: Date.now()
    };
    
    try {
      await this.forwardToClient(clientId, response);
    } catch (error) {
      this.logger.error('发送错误响应失败:', error);
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      const heartbeat = {
        type: 'broker_heartbeat',
        timestamp: Date.now(),
        stats: this.stats.getStats(),
        connectedClients: this.connectedClients.size
      };
      
      // 广播心跳
      this.broadcastMessage(heartbeat).catch(error => {
        this.logger.error('发送心跳失败:', error);
      });
      
    }, CONFIG.HEARTBEAT_INTERVAL);
    
    this.logger.info(`心跳已启动，间隔: ${CONFIG.HEARTBEAT_INTERVAL}ms`);
  }

  parseMessage(frames) {
    try {
      const messageBuffer = Buffer.concat(frames);
      return JSON.parse(messageBuffer.toString());
    } catch (error) {
      throw new Error(`消息解析失败: ${error.message}`);
    }
  }

  serializeMessage(message) {
    try {
      return Buffer.from(JSON.stringify(message));
    } catch (error) {
      throw new Error(`消息序列化失败: ${error.message}`);
    }
  }

  async shutdown() {
    this.logger.info('正在关闭ZeroMQ代理...');
    
    this.isRunning = false;
    
    // 停止心跳
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    
    // 关闭所有套接字
    for (const [name, socket] of Object.entries(this.sockets)) {
      try {
        await socket.close();
        this.logger.info(`${name} 套接字已关闭`);
      } catch (error) {
        this.logger.error(`关闭 ${name} 套接字失败:`, error);
      }
    }
    
    this.logger.info('ZeroMQ代理已关闭');
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      stats: this.stats.getStats(),
      connectedClients: this.connectedClients.size,
      config: CONFIG
    };
  }
}

// 主函数
async function main() {
  const broker = new ZMQBroker();
  
  // 处理进程信号
  process.on('SIGINT', async () => {
    console.log('\n收到 SIGINT 信号，正在关闭代理...');
    await broker.shutdown();
    process.exit(0);
  });
  
  process.on('SIGTERM', async () => {
    console.log('\n收到 SIGTERM 信号，正在关闭代理...');
    await broker.shutdown();
    process.exit(0);
  });
  
  process.on('uncaughtException', (error) => {
    console.error('未捕获的异常:', error);
    broker.shutdown().then(() => process.exit(1));
  });
  
  process.on('unhandledRejection', (reason, promise) => {
    console.error('未处理的Promise拒绝:', reason);
    broker.shutdown().then(() => process.exit(1));
  });
  
  try {
    await broker.initialize();
    
    console.log('='.repeat(50));
    console.log('交易执行铁三角 ZeroMQ 消息代理已启动');
    console.log('='.repeat(50));
    console.log(`前端端口: ${CONFIG.FRONTEND_PORT}`);
    console.log(`后端端口: ${CONFIG.BACKEND_PORT}`);
    console.log(`发布端口: ${CONFIG.PUBLISHER_PORT}`);
    console.log(`订阅端口: ${CONFIG.SUBSCRIBER_PORT}`);
    console.log('='.repeat(50));
    
    // 定期输出状态
    setInterval(() => {
      const status = broker.getStatus();
      console.log(`[状态] 运行时间: ${status.stats.uptime}s, 消息: ${status.stats.received}/${status.stats.sent}, 客户端: ${status.connectedClients}`);
    }, 30000);
    
  } catch (error) {
    console.error('启动ZeroMQ代理失败:', error);
    process.exit(1);
  }
}

// 如果直接运行此文件
if (require.main === module) {
  main();
}

module.exports = ZMQBroker;