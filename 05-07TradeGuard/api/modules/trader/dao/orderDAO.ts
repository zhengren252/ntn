import { BaseDAO } from '../../../shared/database/dao';
import { Order, OrderExecution, DatabaseResult, QueryFilter } from '../../../shared/database/models';

// 订单数据访问对象
export class OrderDAO extends BaseDAO<Order> {
  constructor() {
    super('orders');
  }

  // 根据策略ID查询订单
  public findByStrategyId(strategyId: number): Order[] {
    const filters: QueryFilter[] = [
      { field: 'strategy_id', operator: 'eq', value: strategyId }
    ];
    return this.findAll(filters) as Order[];
  }

  // 根据状态查询订单
  public findByStatus(status: string): Order[] {
    const filters: QueryFilter[] = [
      { field: 'status', operator: 'eq', value: status }
    ];
    return this.findAll(filters) as Order[];
  }

  // 根据交易品种查询订单
  public findBySymbol(symbol: string): Order[] {
    const filters: QueryFilter[] = [
      { field: 'symbol', operator: 'eq', value: symbol }
    ];
    return this.findAll(filters) as Order[];
  }

  // 查询活跃订单（待处理、已提交、部分成交）
  public findActiveOrders(): Order[] {
    const filters: QueryFilter[] = [
      { field: 'status', operator: 'in', value: ['pending', 'submitted', 'partial_filled'] }
    ];
    return this.findAll(filters) as Order[];
  }

  // 查询今日订单
  public findTodayOrders(): Order[] {
    const today = new Date().toISOString().split('T')[0];
    const filters: QueryFilter[] = [
      { field: 'created_at', operator: 'gte', value: `${today} 00:00:00` }
    ];
    return this.findAll(filters) as Order[];
  }

  // 创建订单
  public createOrder(orderData: Partial<Order>): DatabaseResult {
    // 设置默认值
    const defaultData = {
      status: 'pending' as 'pending' | 'rejected' | 'filled' | 'cancelled' | 'partial_filled' | 'submitted',
      filled_quantity: 0,
      commission: 0,
      risk_check_passed: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      ...orderData
    };
    
    return this.create(defaultData);
  }

  // 更新订单状态
  public updateStatus(id: number, status: string): DatabaseResult {
    const updateData: Partial<Order> = {
      status: status as any,
      updated_at: new Date().toISOString()
    };
    
    // 根据状态设置相应的时间戳
    switch (status) {
      case 'submitted':
        updateData.submitted_at = new Date().toISOString();
        break;
      case 'filled':
      case 'partial_filled':
        updateData.filled_at = new Date().toISOString();
        break;
      case 'cancelled':
      case 'rejected':
        updateData.cancelled_at = new Date().toISOString();
        break;
    }
    
    return this.update(id, updateData);
  }

  // 更新订单成交信息
  public updateFillInfo(id: number, filledQuantity: number, avgFillPrice: number, commission: number): DatabaseResult {
    const updateData: Partial<Order> = {
      filled_quantity: filledQuantity,
      avg_fill_price: avgFillPrice,
      commission: commission,
      updated_at: new Date().toISOString()
    };
    
    // 如果完全成交，更新状态
    const order = this.findById(id);
    if (order && filledQuantity >= order.quantity) {
      updateData.status = 'filled' as const;
      updateData.filled_at = new Date().toISOString();
    } else if (filledQuantity > 0) {
      updateData.status = 'partial_filled' as const;
    }
    
    return this.update(id, updateData);
  }

  // 批量更新订单状态
  public batchUpdateStatus(orderIds: number[], status: string): DatabaseResult {
    if (!orderIds || orderIds.length === 0) {
      return { success: false, error: '订单ID列表为空' };
    }

    const placeholders = orderIds.map(() => '?').join(', ');
    const sql = `
      UPDATE ${this.tableName} 
      SET status = ?, updated_at = CURRENT_TIMESTAMP 
      WHERE id IN (${placeholders})
    `;
    
    return this.executeCommand(sql, [status, ...orderIds]);
  }

  // 获取订单统计信息
  public getOrderStats(strategyId?: number): {
    status: string;
    order_type: string;
    side: string;
    count: number;
    total_quantity: number;
    total_filled_quantity: number;
    avg_price: number;
    total_commission: number;
  }[] {
    let sql = `
      SELECT 
        status,
        order_type,
        side,
        COUNT(*) as count,
        SUM(quantity) as total_quantity,
        SUM(filled_quantity) as total_filled_quantity,
        AVG(avg_fill_price) as avg_price,
        SUM(commission) as total_commission
      FROM ${this.tableName}
    `;
    
    const params: any[] = [];
    if (strategyId) {
      sql += ' WHERE strategy_id = ?';
      params.push(strategyId);
    }
    
    sql += ' GROUP BY status, order_type, side ORDER BY status, order_type, side';
    
    return this.executeQuery(sql, params) as any[];
  }

  // 获取交易对统计
  public getSymbolStats(): {
    symbol: string;
    order_count: number;
    buy_quantity: number;
    sell_quantity: number;
    total_filled: number;
    avg_price: number;
    total_commission: number;
  }[] {
    const sql = `
      SELECT 
        symbol,
        COUNT(*) as order_count,
        SUM(CASE WHEN side = 'buy' THEN quantity ELSE 0 END) as buy_quantity,
        SUM(CASE WHEN side = 'sell' THEN quantity ELSE 0 END) as sell_quantity,
        SUM(filled_quantity) as total_filled,
        AVG(avg_fill_price) as avg_price,
        SUM(commission) as total_commission
      FROM ${this.tableName}
      WHERE status IN ('filled', 'partial_filled')
      GROUP BY symbol
      ORDER BY order_count DESC
    `;
    
    return this.executeQuery(sql) as any[];
  }

  // 获取订单执行详情
  public getOrderExecutions(orderId: number): OrderExecution[] {
    const sql = `
      SELECT * FROM order_executions 
      WHERE order_id = ? 
      ORDER BY execution_time DESC
    `;
    
    return this.executeQuery(sql, [orderId]) as any[];
  }

  // 查询订单的风险检查结果
  public getRiskCheckResult(orderId: number): Record<string, unknown> | null {
    const sql = `
      SELECT 
        o.*,
        ra.risk_score,
        ra.assessment_result,
        ra.recommendations
      FROM ${this.tableName} o
      LEFT JOIN risk_assessments ra ON o.strategy_id = ra.strategy_id
      WHERE o.id = ?
      ORDER BY ra.created_at DESC
      LIMIT 1
    `;
    
    return this.executeQuery(sql, [orderId])[0] as any || null;
  }

  // 查询未完成的订单
  public findPendingOrders(strategyId?: number): Order[] {
    const filters: QueryFilter[] = [
      { field: 'status', operator: 'in', value: ['pending', 'submitted', 'partial_filled'] }
    ];
    
    if (strategyId) {
      filters.push({ field: 'strategy_id', operator: 'eq', value: strategyId });
    }
    
    return this.findAll(filters) as Order[];
  }

  // 查询超时订单
  public findTimeoutOrders(timeoutMinutes: number = 30): Order[] {
    const timeoutTime = new Date(Date.now() - timeoutMinutes * 60 * 1000).toISOString();
    const sql = `
      SELECT * FROM ${this.tableName}
      WHERE status IN ('pending', 'submitted') 
      AND created_at < ?
      ORDER BY created_at ASC
    `;
    
    return this.executeQuery(sql, [timeoutTime]) as Order[];
  }

  // 获取订单盈亏统计
  public getPnLStats(strategyId?: number): {
    realized_pnl: number;
    filled_orders: number;
    total_commission: number;
  } {
    let sql = `
      SELECT 
        SUM(CASE 
          WHEN o.side = 'buy' AND o.status = 'filled' 
          THEN -1 * (o.filled_quantity * o.avg_fill_price + o.commission)
          WHEN o.side = 'sell' AND o.status = 'filled' 
          THEN (o.filled_quantity * o.avg_fill_price - o.commission)
          ELSE 0 
        END) as realized_pnl,
        COUNT(CASE WHEN o.status = 'filled' THEN 1 END) as filled_orders,
        SUM(o.commission) as total_commission
      FROM ${this.tableName} o
    `;
    
    const params: any[] = [];
    if (strategyId) {
      sql += ' WHERE o.strategy_id = ?';
      params.push(strategyId);
    }
    
    return this.executeQuery(sql, params)[0] as any || {
      realized_pnl: 0,
      filled_orders: 0,
      total_commission: 0
    };
  }

  // 查询大额订单
  public findLargeOrders(minAmount: number): Order[] {
    const sql = `
      SELECT * FROM ${this.tableName}
      WHERE (quantity * COALESCE(price, avg_fill_price, 0)) >= ?
      ORDER BY (quantity * COALESCE(price, avg_fill_price, 0)) DESC
    `;
    
    return this.executeQuery(sql, [minAmount]) as Order[];
  }

  // 查询订单历史（包含相关信息）
  public getOrderHistory(strategyId: number, limit: number = 100): Record<string, unknown>[] {
    const sql = `
      SELECT 
        o.*,
        sp.package_name,
        sp.strategy_type,
        ts.session_name
      FROM ${this.tableName} o
      LEFT JOIN strategy_packages sp ON o.strategy_id = sp.id
      LEFT JOIN trading_sessions ts ON sp.session_id = ts.id
      WHERE o.strategy_id = ?
      ORDER BY o.created_at DESC
      LIMIT ?
    `;
    
    return this.executeQuery(sql, [strategyId, limit]) as any[];
  }

  // 取消订单
  public cancelOrder(id: number, reason: string = 'User cancelled'): DatabaseResult {
    const order = this.findById(id);
    if (!order) {
      return { success: false, error: '订单不存在' };
    }
    
    if (!['pending', 'submitted', 'partial_filled'].includes(order.status)) {
      return { success: false, error: '订单状态不允许取消' };
    }
    
    return this.updateStatus(id, 'cancelled');
  }

  // 批量取消订单
  public batchCancelOrders(orderIds: number[]): DatabaseResult {
    if (!orderIds || orderIds.length === 0) {
      return { success: false, error: '订单ID列表为空' };
    }

    const placeholders = orderIds.map(() => '?').join(', ');
    const sql = `
      UPDATE ${this.tableName} 
      SET status = 'cancelled', 
          cancelled_at = CURRENT_TIMESTAMP,
          updated_at = CURRENT_TIMESTAMP 
      WHERE id IN (${placeholders})
      AND status IN ('pending', 'submitted', 'partial_filled')
    `;
    
    return this.executeCommand(sql, orderIds);
  }
}

// 订单执行数据访问对象
export class OrderExecutionDAO extends BaseDAO<OrderExecution> {
  constructor() {
    super('order_executions');
  }

  // 根据订单ID查询执行记录
  public findByOrderId(orderId: number): OrderExecution[] {
    const filters: QueryFilter[] = [
      { field: 'order_id', operator: 'eq', value: orderId }
    ];
    return this.findAll(filters) as OrderExecution[];
  }

  // 创建执行记录
  public createExecution(executionData: Partial<OrderExecution>): DatabaseResult {
    const defaultData = {
      created_at: new Date().toISOString(),
      ...executionData
    };
    
    return this.create(defaultData);
  }

  // 获取执行统计
  public getExecutionStats(): {
    venue: string;
    liquidity_flag: string;
    execution_count: number;
    total_quantity: number;
    avg_price: number;
    total_commission: number;
  }[] {
    const sql = `
      SELECT 
        venue,
        liquidity_flag,
        COUNT(*) as execution_count,
        SUM(quantity) as total_quantity,
        AVG(price) as avg_price,
        SUM(commission) as total_commission
      FROM ${this.tableName}
      GROUP BY venue, liquidity_flag
      ORDER BY execution_count DESC
    `;
    
    return this.executeQuery(sql) as any[];
  }
}

// 导出DAO实例
export const orderDAO = new OrderDAO();
export const orderExecutionDAO = new OrderExecutionDAO();
export default OrderDAO;