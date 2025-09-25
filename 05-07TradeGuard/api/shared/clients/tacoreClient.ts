/**
 * TACoreService客户端
 * 用于与TACoreService进行ZMQ通信
 */

import * as zmq from 'zeromq';
import { logger } from '../utils/logger';
import { configManager } from '../../config/environment';

export interface OrderExecutionRequest {
  strategyId: number;
  symbol: string;
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  side: 'buy' | 'sell';
  quantity: number;
  price?: number;
  stopPrice?: number;
  timeInForce: 'GTC' | 'IOC' | 'FOK' | 'GTD';
  orderSource: 'manual' | 'algorithm' | 'api';
  metadata?: Record<string, unknown>;
}

export interface OrderExecutionResponse {
  success: boolean;
  orderId?: string;
  status?: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected' | 'failed';
  executedPrice?: number;
  executedQuantity?: number;
  executionTime?: string;
  error?: string;
  errorCode?: string;
}

export class TACoreClient {
  private socket: zmq.Request | null = null;
  private serviceUrl: string;
  private timeout: number;
  private connected: boolean = false;

  constructor() {
    this.serviceUrl = configManager.get('TACORE_SERVICE_URL') || 'tcp://localhost:5555';
    this.timeout = parseInt(configManager.get('TACORE_TIMEOUT') || '30000');
  }

  /**
   * 连接到TACoreService
   */
  async connect(): Promise<boolean> {
    try {
      this.socket = new zmq.Request({
        receiveTimeout: this.timeout,
        sendTimeout: this.timeout
      });
      
      this.socket.connect(this.serviceUrl);
      this.connected = true;
      
      logger.info(`TACoreClient connected to ${this.serviceUrl}`);
      return true;
    } catch (error) {
      logger.error('Failed to connect to TACoreService:', error);
      this.connected = false;
      return false;
    }
  }

  /**
   * 断开连接
   */
  async disconnect(): Promise<void> {
    if (this.socket) {
      this.socket.disconnect(this.serviceUrl);
      this.socket.close();
      this.socket = null;
      this.connected = false;
      logger.info('TACoreClient disconnected');
    }
  }

  /**
   * 执行订单
   */
  async executeOrder(request: OrderExecutionRequest): Promise<OrderExecutionResponse> {
    if (!this.connected || !this.socket) {
      const connectResult = await this.connect();
      if (!connectResult) {
        return {
          success: false,
          error: 'Failed to connect to TACoreService',
          errorCode: 'CONNECTION_ERROR'
        };
      }
    }

    try {
      const message = {
        method: 'execute.order',
        params: request,
        timestamp: new Date().toISOString(),
        requestId: `ORDER_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      };

      logger.info(`Sending order execution request: ${message.requestId}`);
      
      await this.socket!.send(JSON.stringify(message));
      const [response] = await this.socket!.receive();
      
      const result = JSON.parse(response.toString());
      
      if (result.success) {
        logger.info(`Order execution successful: ${result.orderId}`);
        return {
          success: true,
          orderId: result.orderId,
          status: result.status || 'filled',
          executedPrice: result.executedPrice,
          executedQuantity: result.executedQuantity,
          executionTime: result.executionTime || new Date().toISOString()
        };
      } else {
        logger.warn(`Order execution failed: ${result.error}`);
        return {
          success: false,
          error: result.error || 'Unknown error',
          errorCode: result.errorCode || 'EXECUTION_ERROR'
        };
      }
    } catch (error) {
      logger.error('Order execution error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        errorCode: 'COMMUNICATION_ERROR'
      };
    }
  }

  /**
   * 获取订单状态
   */
  async getOrderStatus(orderId: string): Promise<unknown> {
    if (!this.connected || !this.socket) {
      const connectResult = await this.connect();
      if (!connectResult) {
        throw new Error('Failed to connect to TACoreService');
      }
    }

    try {
      const message = {
        method: 'order.status',
        params: { orderId },
        timestamp: new Date().toISOString(),
        requestId: `STATUS_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      };

      await this.socket!.send(JSON.stringify(message));
      const [response] = await this.socket!.receive();
      
      return JSON.parse(response.toString());
    } catch (error) {
      logger.error('Get order status error:', error);
      throw error;
    }
  }

  /**
   * 取消订单
   */
  async cancelOrder(orderId: string): Promise<unknown> {
    if (!this.connected || !this.socket) {
      const connectResult = await this.connect();
      if (!connectResult) {
        throw new Error('Failed to connect to TACoreService');
      }
    }

    try {
      const message = {
        method: 'order.cancel',
        params: { orderId },
        timestamp: new Date().toISOString(),
        requestId: `CANCEL_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      };

      await this.socket!.send(JSON.stringify(message));
      const [response] = await this.socket!.receive();
      
      return JSON.parse(response.toString());
    } catch (error) {
      logger.error('Cancel order error:', error);
      throw error;
    }
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.connected;
  }
}

// 导出单例实例
export const tacoreClient = new TACoreClient();