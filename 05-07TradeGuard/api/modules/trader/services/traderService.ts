import { strategyDAO } from '../dao/strategyDAO';
import { orderDAO, orderExecutionDAO } from '../dao/orderDAO';
import { redisCache, CacheKeyType } from '../../../shared/cache/redis';
import { zmqBus, MessageType, ZMQMessage } from '../../../shared/messaging/zeromq';
import { StrategyPackage, Order, DatabaseResult } from '../../../shared/database/models';
import { TACoreClient } from '../../../shared/clients/tacoreClient';
import { v4 as uuidv4 } from 'uuid';
import { createClient, RedisClientType } from 'redis';

// 策略包接收请求接口
export interface StrategyPackageRequest {
  sessionId: number;
  packageName: string;
  strategyType: 'momentum' | 'mean_reversion' | 'arbitrage' | 'market_making' | 'trend_following';
  parameters: Record<string, unknown>;
  riskLevel: 'low' | 'medium' | 'high';
  expectedReturn: number;
  maxPositionSize: number;
  stopLossPct: number;
  takeProfitPct: number;
}

// 订单创建请求接口
export interface OrderRequest {
  strategyId: number;
  symbol: string;
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  side: 'buy' | 'sell';
  quantity: number;
  price?: number;
  stopPrice?: number;
  timeInForce: 'GTC' | 'IOC' | 'FOK' | 'DAY';
  orderSource: 'manual' | 'algorithm' | 'risk_management';
}

// 风险财务申请接口
export interface RiskFinanceRequest {
  strategyId: number;
  requestType: 'risk_assessment' | 'budget_application' | 'both';
  requestedAmount?: number;
  purpose?: string;
  justification?: string;
}

// 交易员服务类
export class TraderService {
  private static instance: TraderService;
  private tacoreClient: TACoreClient;
  private redisLite: RedisClientType | null = null;

  private constructor() {
    this.tacoreClient = new TACoreClient();
    this.initializeMessageHandlers();
  }

  public static getInstance(): TraderService {
    if (!TraderService.instance) {
      TraderService.instance = new TraderService();
    }
    return TraderService.instance;
  }

  // 初始化消息处理器
  private initializeMessageHandlers(): void {
    // 监听风险评估结果（统一主题为 risk.alerts）
    zmqBus.subscribe(MessageType.RISK_ALERT, this.handleRiskAlert.bind(this));
    
    // 监听资金分配结果
    zmqBus.subscribe(MessageType.FUND_RESPONSE, this.handleFundResponse.bind(this));
    
    // 监听订单更新
    zmqBus.subscribe(MessageType.ORDER_UPDATE, this.handleOrderUpdate.bind(this));
    
    // 监听紧急停止信号
    zmqBus.subscribe(MessageType.EMERGENCY_STOP, this.handleEmergencyStop.bind(this));

    // 监听 ReviewGuard 审批通过事件
    zmqBus.subscribe(
      MessageType.REVIEWGUARD_POOL_APPROVED,
      this.handleReviewGuardPoolApproved.bind(this)
    );
  }

  // 接收策略包
  public async receiveStrategyPackage(request: StrategyPackageRequest): Promise<DatabaseResult> {
    try {
      // 验证请求参数
      const validation = this.validateStrategyRequest(request);
      if (!validation.isValid) {
        return { success: false, error: validation.error };
      }

      // 创建策略包
      const strategyData: Partial<StrategyPackage> = {
        session_id: request.sessionId,
        package_name: request.packageName,
        strategy_type: request.strategyType,
        parameters: JSON.stringify(request.parameters),
        risk_level: request.riskLevel,
        expected_return: request.expectedReturn,
        max_position_size: request.maxPositionSize,
        stop_loss_pct: request.stopLossPct,
        take_profit_pct: request.takeProfitPct,
        status: 'pending'
      };

      const result = strategyDAO.createStrategy(strategyData);
      
      if (result.success && result.lastInsertId) {
        try {
          // 缓存策略信息
          await this.cacheStrategyInfo(result.lastInsertId, strategyData);
          
          // 发送策略创建通知
          await this.notifyStrategyCreated(result.lastInsertId, strategyData);
          
          console.log(`策略包已接收: ${request.packageName} (ID: ${result.lastInsertId})`);
        } catch (error) {
          console.error('策略后处理失败:', error);
          // 如果后处理失败，仍然返回成功，但记录错误
        }
      }

      return result;
    } catch (error) {
      console.error('接收策略包失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 申请风险评估
  public async requestRiskAssessment(request: RiskFinanceRequest): Promise<DatabaseResult> {
    try {
      const strategy = strategyDAO.findById(request.strategyId);
      if (!strategy) {
        return { success: false, error: '策略不存在' };
      }

      const correlationId = uuidv4();
      const riskRequest: ZMQMessage = {
        type: MessageType.RISK_ALERT,
        timestamp: new Date().toISOString(),
        source: 'trader_module',
        target: 'risk_module',
        correlationId,
        data: {
          action: 'request_assessment',
          strategyId: request.strategyId,
          strategy: strategy
        }
      };

      try {
        const response = await zmqBus.request(riskRequest);
        return { success: true, data: { correlationId, response } };
      } catch (error) {
        return { success: false, error: error instanceof Error ? error.message : '风险评估请求失败' };
      }
    } catch (error) {
      console.error('申请风险评估失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 申请资金
  public async requestFunding(request: RiskFinanceRequest): Promise<DatabaseResult> {
    try {
      const strategy = strategyDAO.findById(request.strategyId);
      if (!strategy) {
        return { success: false, error: '策略不存在' };
      }

      if (!request.requestedAmount || !request.purpose) {
        return { success: false, error: '资金申请需要提供申请金额和用途' };
      }

      const correlationId = uuidv4();
      const fundRequest: ZMQMessage = {
        type: MessageType.FUND_REQUEST,
        timestamp: new Date().toISOString(),
        source: 'trader_module',
        target: 'finance_module',
        correlationId,
        data: {
          action: 'request_budget',
          strategyId: request.strategyId,
          requestedAmount: request.requestedAmount,
          purpose: request.purpose,
          justification: request.justification,
          strategy: strategy
        }
      };

      try {
        const response = await zmqBus.request(fundRequest);
        return { success: true, data: { correlationId, response } };
      } catch (error) {
        return { success: false, error: error instanceof Error ? error.message : '资金申请失败' };
      }
    } catch (error) {
      console.error('申请资金失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 申请风险评估和资金
  public async requestRiskAndFinance(request: RiskFinanceRequest): Promise<DatabaseResult> {
    try {
      const strategy = strategyDAO.findById(request.strategyId);
      if (!strategy) {
        return { success: false, error: '策略不存在' };
      }

      const correlationId = uuidv4();
      let success = true;
      const results: Record<string, unknown>[] = [];

      let riskApproved = true; // 默认风控通过
      
      // 申请风险评估
      if (request.requestType === 'risk_assessment' || request.requestType === 'both') {
        const riskRequest: ZMQMessage = {
          type: MessageType.RISK_ALERT,
          timestamp: new Date().toISOString(),
          source: 'trader_module',
          target: 'risk_module',
          correlationId,
          data: {
            action: 'request_assessment',
            strategyId: request.strategyId,
            strategy: strategy
          }
        };

        try {
          const response = await zmqBus.request(riskRequest);
          results.push({ type: 'risk_assessment', response });
          // 检查风控是否批准
          if (response.data && response.data.approved === false) {
            riskApproved = false;
          }
        } catch (error) {
          success = false;
          riskApproved = false;
          results.push({ type: 'risk_assessment', error: error instanceof Error ? error.message : '风险评估请求失败' });
        }
      }

      // 申请资金分配（只有在风控通过时才申请）
      if ((request.requestType === 'budget_application' || request.requestType === 'both') && riskApproved) {
        if (!request.requestedAmount || !request.purpose) {
          return { success: false, error: '资金申请需要提供申请金额和用途' };
        }

        const fundRequest: ZMQMessage = {
          type: MessageType.FUND_REQUEST,
          timestamp: new Date().toISOString(),
          source: 'trader_module',
          target: 'finance_module',
          correlationId,
          data: {
            action: 'request_budget',
            strategyId: request.strategyId,
            requestedAmount: request.requestedAmount,
            purpose: request.purpose,
            justification: request.justification,
            strategy: strategy
          }
        };

        try {
          const response = await zmqBus.request(fundRequest);
          results.push({ type: 'budget_application', response });
        } catch (error) {
          success = false;
          results.push({ type: 'budget_application', error: error instanceof Error ? error.message : '资金申请失败' });
        }
      }

      // 缓存申请结果
      await redisCache.set(
        CacheKeyType.STRATEGY_STATE,
        `request_${request.strategyId}_${correlationId}`,
        { request, results, timestamp: new Date().toISOString() }
      );

      return {
        success,
        data: {
          correlationId,
          results
        }
      };
    } catch (error) {
      console.error('申请风险评估和资金失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 创建订单
  public async createOrder(request: OrderRequest): Promise<{ success: boolean; orderId?: number; status?: string; riskCheckPassed?: boolean; error?: string }> {
    try {
      // 验证策略状态
      const strategy = strategyDAO.findById(request.strategyId);
      if (!strategy) {
        return { success: false, error: '策略不存在' };
      }

      if (strategy.status !== 'active') {
        return { success: false, error: '策略未激活，无法创建订单' };
      }

      // 验证策略参数
      if (!strategy.parameters) {
        return { success: false, error: '策略参数无效' };
      }

      // 验证订单参数
      const validation = this.validateOrderRequest(request);
      if (!validation.isValid) {
        return { success: false, error: validation.error };
      }

      // 创建订单
      const orderData: Partial<Order> = {
        strategy_id: request.strategyId,
        symbol: request.symbol,
        order_type: request.orderType,
        side: request.side,
        quantity: request.quantity,
        price: request.price,
        stop_price: request.stopPrice,
        time_in_force: request.timeInForce,
        order_source: request.orderSource,
        status: 'pending'
      };

      const result = orderDAO.createOrder(orderData);
      
      if (result.success && result.lastInsertId) {
        // 进行风险检查
        const riskCheckResult = await this.performRiskCheck(result.lastInsertId, orderData);
        
        if (riskCheckResult.passed) {
          // 更新风险检查状态
          orderDAO.update(result.lastInsertId, { risk_check_passed: true });
          
          // 提交订单到交易引擎（不等待结果，异步处理）
          this.submitOrderToEngine(result.lastInsertId, orderData).catch(error => {
            console.error('异步提交订单失败:', error);
          });
        } else {
          // 风险检查失败，拒绝订单
          orderDAO.updateStatus(result.lastInsertId, 'rejected');
          return { success: false, error: `风险检查失败: ${riskCheckResult.reason}` };
        }
        
        // 缓存订单信息
        await this.cacheOrderInfo(result.lastInsertId, orderData).catch(error => {
          console.error('缓存订单信息失败:', error);
        });
        
        console.log(`订单已创建: ${request.symbol} ${request.side} ${request.quantity} (ID: ${result.lastInsertId})`);
        
        // 返回包含orderId的结果
        return {
          success: true,
          orderId: result.lastInsertId!,
          status: 'pending',
          riskCheckPassed: riskCheckResult.passed
        };
      }

      return result;
    } catch (error) {
      console.error('创建订单失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 取消订单
  public async cancelOrder(orderId: number, reason: string = 'User cancelled'): Promise<DatabaseResult> {
    try {
      const result = orderDAO.cancelOrder(orderId, reason);
      
      if (result.success) {
        // 通知交易引擎取消订单
        await this.notifyOrderCancellation(orderId, reason);
        
        // 更新缓存
        await this.updateOrderCache(orderId, { status: 'cancelled' });
        
        console.log(`订单已取消: ${orderId}, 原因: ${reason}`);
      }
      
      return result;
    } catch (error) {
      console.error('取消订单失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 获取策略包列表
  public async getStrategyPackages(sessionId?: number): Promise<StrategyPackage[]> {
    try {
      if (sessionId) {
        return strategyDAO.findBySessionId(sessionId);
      }
      return strategyDAO.findAll() as StrategyPackage[];
    } catch (error) {
      console.error('获取策略包列表失败:', error);
      return [];
    }
  }

  // 获取订单列表
  public async getOrders(strategyId?: number): Promise<Order[]> {
    try {
      if (strategyId) {
        return orderDAO.findByStrategyId(strategyId);
      }
      return orderDAO.findAll() as Order[];
    } catch (error) {
      console.error('获取订单列表失败:', error);
      return [];
    }
  }

  // 获取策略性能指标
  public async getStrategyPerformance(strategyId: number): Promise<unknown> {
    try {
      // 从缓存获取
      const cached = await redisCache.get(CacheKeyType.STRATEGY_STATE, `performance_${strategyId}`);
      if (cached) {
        return cached;
      }

      // 从数据库获取
      const performance = strategyDAO.getPerformanceMetrics(strategyId);
      const orderStats = orderDAO.getOrderStats(strategyId);
      const pnlStats = orderDAO.getPnLStats(strategyId);
      const positions = strategyDAO.getPositions(strategyId);
      const riskMetrics = strategyDAO.getRiskMetrics(strategyId);

      const result = {
        strategy: performance,
        orders: orderStats,
        pnl: pnlStats,
        positions,
        risk: riskMetrics,
        timestamp: new Date().toISOString()
      };

      // 缓存结果
      await redisCache.set(CacheKeyType.STRATEGY_STATE, `performance_${strategyId}`, result, 300); // 5分钟缓存

      return result;
    } catch (error) {
      console.error('获取策略性能指标失败:', error);
      return null;
    }
  }

  // 处理风险警报
  private async handleRiskAlert(message: ZMQMessage): Promise<void> {
    try {
      const { strategyId, alertType, severity } = message.data as Record<string, any>;
      
      console.log(`收到风险警报: 策略${strategyId}, 类型: ${alertType}, 严重程度: ${severity}`);
      
      // 根据严重程度采取行动
      if (severity === 'critical') {
        // 暂停策略
        await this.pauseStrategy(Number(strategyId), '风险警报: 严重风险');
        
        // 取消所有未完成订单
        const pendingOrders = orderDAO.findPendingOrders(Number(strategyId));
        for (const order of pendingOrders) {
          await this.cancelOrder(order.id, '风险警报: 紧急停止');
        }
      } else if (severity === 'high') {
        // 暂停新订单创建
        await this.pauseStrategy(Number(strategyId), '风险警报: 高风险');
      }
      
      // 更新缓存
      await redisCache.set(
        CacheKeyType.RISK_METRICS,
        `alert_${strategyId}`,
        message.data
      );
    } catch (error) {
      console.error('处理风险警报失败:', error);
    }
  }

  // 处理资金响应
  private async handleFundResponse(message: ZMQMessage): Promise<void> {
    try {
      const { strategyId, approved, allocatedAmount, reason } = message.data;
      
      console.log(`收到资金分配响应: 策略${strategyId}, 批准: ${approved}, 金额: ${allocatedAmount}`);
      
      if (approved) {
        // 激活策略
        strategyDAO.updateStatus(Number(strategyId), 'active');
        
        // 更新缓存
        await redisCache.set(
          CacheKeyType.STRATEGY_STATE,
          `funding_${strategyId}`,
          { approved: true, amount: allocatedAmount, timestamp: new Date().toISOString() }
        );
      } else {
        // 拒绝策略
        strategyDAO.updateStatus(Number(strategyId), 'rejected');
        
        console.log(`策略${strategyId}资金申请被拒绝: ${reason}`);
      }
    } catch (error) {
      console.error('处理资金响应失败:', error);
    }
  }

  // 处理订单更新
  private async handleOrderUpdate(message: ZMQMessage): Promise<void> {
    try {
      const { orderId, status, filledQuantity, avgFillPrice, commission } = message.data;
      
      console.log(`收到订单更新: ${orderId}, 状态: ${status}`);
      
      // 更新订单状态
      if (filledQuantity !== undefined && avgFillPrice !== undefined) {
        orderDAO.updateFillInfo(Number(orderId), Number(filledQuantity), Number(avgFillPrice), Number(commission) || 0);
      } else {
        orderDAO.updateStatus(Number(orderId), String(status));
      }
      
      // 更新缓存
      await this.updateOrderCache(Number(orderId), message.data);
      
      // 如果是成交更新，记录执行信息
      if (status === 'filled' || status === 'partial_filled') {
        await this.recordOrderExecution(Number(orderId), message.data);
      }
    } catch (error) {
      console.error('处理订单更新失败:', error);
    }
  }

  // 处理紧急停止
  private async handleEmergencyStop(message: ZMQMessage): Promise<void> {
    try {
      const { reason } = message.data;
      
      console.log(`收到紧急停止信号: ${reason}`);
      
      // 暂停所有活跃策略
      const activeStrategies = strategyDAO.findActiveStrategies();
      for (const strategy of activeStrategies) {
        await this.pauseStrategy(strategy.id, `紧急停止: ${reason}`);
      }
      
      // 取消所有未完成订单
      const pendingOrders = orderDAO.findPendingOrders();
      const orderIds = pendingOrders.map(order => order.id);
      if (orderIds.length > 0) {
        orderDAO.batchCancelOrders(orderIds);
      }
      
      console.log(`紧急停止完成: 暂停${activeStrategies.length}个策略，取消${orderIds.length}个订单`);
    } catch (error) {
      console.error('处理紧急停止失败:', error);
    }
  }

  // 验证策略请求
  private validateStrategyRequest(request: StrategyPackageRequest): { isValid: boolean; error?: string } {
    if (!request.packageName || request.packageName.trim().length === 0) {
      return { isValid: false, error: '策略包名称不能为空' };
    }
    
    if (request.expectedReturn < 0 || request.expectedReturn > 1) {
      return { isValid: false, error: '预期收益率必须在0-100%之间' };
    }
    
    if (request.maxPositionSize <= 0) {
      return { isValid: false, error: '最大持仓金额必须大于0' };
    }
    
    if (request.stopLossPct < 0 || request.stopLossPct > 1) {
      return { isValid: false, error: '止损比例必须在0-100%之间' };
    }
    
    if (request.takeProfitPct < 0 || request.takeProfitPct > 1) {
      return { isValid: false, error: '止盈比例必须在0-100%之间' };
    }
    
    return { isValid: true };
  }

  // 验证订单请求
  private validateOrderRequest(request: OrderRequest): { isValid: boolean; error?: string } {
    if (!request.symbol || request.symbol.trim().length === 0) {
      return { isValid: false, error: '交易品种不能为空' };
    }
    
    if (request.quantity <= 0) {
      return { isValid: false, error: '交易数量必须大于0' };
    }
    
    if ((request.orderType === 'limit' || request.orderType === 'stop_limit') && (!request.price || request.price <= 0)) {
      return { isValid: false, error: '限价订单必须指定有效价格' };
    }
    
    if ((request.orderType === 'stop' || request.orderType === 'stop_limit') && (!request.stopPrice || request.stopPrice <= 0)) {
      return { isValid: false, error: '止损订单必须指定有效止损价格' };
    }
    
    return { isValid: true };
  }

  // 执行风险检查
  private async performRiskCheck(orderId: number, orderData: Partial<Order>): Promise<{ passed: boolean; reason?: string }> {
    try {
      // 这里应该调用风控模组进行风险检查
      // 暂时使用简单的规则检查
      
      const strategy = strategyDAO.findById(orderData.strategy_id!);
      if (!strategy) {
        return { passed: false, reason: '策略不存在' };
      }
      
      // 检查持仓限制
      const orderValue = (orderData.quantity || 0) * (orderData.price || 0);
      if (orderValue > strategy.max_position_size) {
        return { passed: false, reason: '订单金额超过策略最大持仓限制' };
      }
      
      // 检查策略状态
      if (strategy.status !== 'active') {
        return { passed: false, reason: '策略未激活' };
      }
      
      return { passed: true };
    } catch (error) {
      console.error('风险检查失败:', error);
      return { passed: false, reason: '风险检查系统错误' };
    }
  }

  // 提交订单到交易引擎
  private async submitOrderToEngine(orderId: number, orderData: Partial<Order>): Promise<void> {
    try {
      // 调用TACoreService执行订单
      const executionRequest = {
        strategyId: orderData.strategy_id!,
        symbol: orderData.symbol!,
        orderType: orderData.order_type!,
        side: orderData.side!,
        quantity: orderData.quantity!,
        price: orderData.price,
        stopPrice: orderData.stop_price,
        timeInForce: (orderData.time_in_force as string || 'GTC') as 'GTC' | 'IOC' | 'FOK' | 'GTD',
        orderSource: (orderData.order_source as string || 'manual') as 'manual' | 'algorithm' | 'api'
      };
      
      const result = await this.tacoreClient.executeOrder(executionRequest);
      
      if (result && result.success) {
        // 根据TACoreService返回的状态更新订单
        const orderStatus = result.status || 'submitted';
        const statusDetails: Record<string, unknown> = {};
        
        if ((result as any).executedPrice) {
          statusDetails.executedPrice = (result as any).executedPrice;
        }
        if ((result as any).executedQuantity) {
          statusDetails.executedQuantity = (result as any).executedQuantity;
        }
        
        orderDAO.updateStatus(orderId, orderStatus);
        console.log(`订单状态已更新: ${orderId} -> ${orderStatus}`);
      } else {
        // TACoreService执行失败
        const errorMsg = result && result.error ? result.error : '执行失败';
        orderDAO.updateStatus(orderId, 'failed');
        console.error(`TACoreService执行失败: ${errorMsg}`);
      }
      
      // 发送订单更新通知
      const orderStatus = result.status || 'submitted';
      const action = orderStatus === 'filled' ? 'order_executed' : 'submit_order';
      
      const message: ZMQMessage = {
        type: MessageType.ORDER_UPDATE,
        timestamp: new Date().toISOString(),
        source: 'trader_module',
        target: 'trading_engine',
        data: {
          action,
          type: orderStatus === 'filled' ? 'order_executed' : 'order_submitted',
          orderId,
          orderData,
          tacoreResult: result
        }
      };
      
      await zmqBus.publish(message);
      
    } catch (error) {
      console.error('提交订单到交易引擎失败:', error);
      // 更新订单状态为失败，但不抛出异常，保留原始错误消息
      const errorMsg = error instanceof Error ? error.message : String(error);
      orderDAO.updateStatus(orderId, 'failed');
    }
  }

  // 暂停策略
  private async pauseStrategy(strategyId: number, reason: string): Promise<void> {
    strategyDAO.updateStatus(strategyId, 'paused');
    
    // 更新缓存
    await redisCache.set(
      CacheKeyType.STRATEGY_STATE,
      `status_${strategyId}`,
      { status: 'paused', reason, timestamp: new Date().toISOString() }
    );
    
    console.log(`策略已暂停: ${strategyId}, 原因: ${reason}`);
  }

  // 缓存策略信息
  private async cacheStrategyInfo(strategyId: number, strategyData: Record<string, unknown>): Promise<void> {
    await redisCache.set(
      CacheKeyType.STRATEGY_STATE,
      `info_${strategyId}`,
      { ...strategyData, id: strategyId, timestamp: new Date().toISOString() }
    );
  }

  // 缓存订单信息
  private async cacheOrderInfo(orderId: number, orderData: Record<string, unknown>): Promise<void> {
    await redisCache.set(
      CacheKeyType.TRADING_DATA,
      `order_${orderId}`,
      { ...orderData, id: orderId, timestamp: new Date().toISOString() }
    );
  }

  // 更新订单缓存
  private async updateOrderCache(orderId: number, updateData: Record<string, unknown>): Promise<void> {
    const cached = await redisCache.get(CacheKeyType.TRADING_DATA, `order_${orderId}`);
    if (cached && typeof cached === 'object') {
      const updated = { ...cached, ...updateData, updated_at: new Date().toISOString() };
      await redisCache.set(CacheKeyType.TRADING_DATA, `order_${orderId}`, updated);
    }
  }

  // 通知策略创建
  private async notifyStrategyCreated(strategyId: number, strategyData: Record<string, unknown>): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.STRATEGY_UPDATE,
      timestamp: new Date().toISOString(),
      source: 'trader_module',
      data: {
        action: 'strategy_created',
        strategyId,
        strategy: strategyData
      }
    };
    
    await zmqBus.publish(message);
  }

  // 通知订单取消
  private async notifyOrderCancellation(orderId: number, reason: string): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.ORDER_UPDATE,
      timestamp: new Date().toISOString(),
      source: 'trader_module',
      target: 'trading_engine',
      data: {
        action: 'cancel_order',
        orderId,
        reason
      }
    };
    
    await zmqBus.publish(message);
  }

  // 记录订单执行
  private async recordOrderExecution(orderId: number, executionData: Record<string, unknown>): Promise<void> {
    try {
      const order = orderDAO.findById(orderId);
      if (!order) return;
      
      const executionRecord = {
        order_id: orderId,
        execution_id: String(executionData.executionId || uuidv4()),
        symbol: order.symbol,
        side: order.side,
        quantity: Number(executionData.filledQuantity || 0),
        price: Number(executionData.avgFillPrice || 0),
        commission: Number(executionData.commission || 0),
        execution_time: new Date().toISOString(),
        venue: String(executionData.venue || 'unknown'),
        liquidity_flag: (String(executionData.liquidityFlag || 'taker') as 'maker' | 'taker')
      };
      
      orderExecutionDAO.createExecution(executionRecord);
    } catch (error) {
      console.error('记录订单执行失败:', error);
    }
  }

  /**
   * 获取轻量级 Redis 客户端（直连，无前缀）
   */
  private async getRedisLite(): Promise<RedisClientType> {
    if (!this.redisLite) {
      this.redisLite = createClient();
      // 基础错误日志
      this.redisLite.on('error', (err) => console.error('Redis Lite error:', err));
    }
    if (!this.redisLite.isOpen) {
      await this.redisLite.connect();
    }
    return this.redisLite;
  }

  /**
   * 处理 ReviewGuard 审批通过事件
   * 要求：
   * 1) 订阅 reviewguard.pool.approved
   * 2) 收到消息后，在 Redis 中写入：
   *    - processed:${strategy.id} -> { strategyId, timestamp }
   *    - system:status:trader:last_activity -> ISO 时间串
   */
  private async handleReviewGuardPoolApproved(message: ZMQMessage): Promise<void> {
    try {
      const data = (message && message.data) as Record<string, any> | undefined;
      const strategyId = data?.id ?? data?.strategyId;

      if (!strategyId) {
        console.warn('收到 reviewguard.pool.approved，但缺少策略ID，跳过处理');
        return;
      }

      const client = await this.getRedisLite();
      const processedKey = `processed:${strategyId}`;

      // 写入处理记录
      await client.set(
        processedKey,
        JSON.stringify({ strategyId, timestamp: new Date().toISOString() })
      );

      // 更新最近活动时间
      await client.set('system:status:trader:last_activity', new Date().toISOString());

      console.log(`已记录策略审核通过处理: ${processedKey}`);
    } catch (error) {
      console.error('处理 reviewguard.pool.approved 消息失败:', error);
    }
  }
}

// 导出服务实例
export const traderService = TraderService.getInstance();
export default TraderService;