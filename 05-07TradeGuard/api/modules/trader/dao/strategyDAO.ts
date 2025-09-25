import { BaseDAO } from '../../../shared/database/dao';
import { StrategyPackage, DatabaseResult, QueryFilter } from '../../../shared/database/models';

// 策略包数据访问对象
export class StrategyDAO extends BaseDAO<StrategyPackage> {
  constructor() {
    super('strategy_packages');
  }

  // 根据会话ID查询策略包
  public findBySessionId(sessionId: number): StrategyPackage[] {
    const filters: QueryFilter[] = [
      { field: 'session_id', operator: 'eq', value: sessionId }
    ];
    return this.findAll(filters) as StrategyPackage[];
  }

  // 根据状态查询策略包
  public findByStatus(status: string): StrategyPackage[] {
    const filters: QueryFilter[] = [
      { field: 'status', operator: 'eq', value: status }
    ];
    return this.findAll(filters) as StrategyPackage[];
  }

  // 根据风险等级查询策略包
  public findByRiskLevel(riskLevel: string): StrategyPackage[] {
    const filters: QueryFilter[] = [
      { field: 'risk_level', operator: 'eq', value: riskLevel }
    ];
    return this.findAll(filters) as StrategyPackage[];
  }

  // 查询活跃的策略包
  public findActiveStrategies(): StrategyPackage[] {
    const filters: QueryFilter[] = [
      { field: 'status', operator: 'eq', value: 'active' }
    ];
    return this.findAll(filters) as StrategyPackage[];
  }

  // 查询待审批的策略包
  public findPendingStrategies(): StrategyPackage[] {
    const filters: QueryFilter[] = [
      { field: 'status', operator: 'eq', value: 'pending' }
    ];
    return this.findAll(filters) as StrategyPackage[];
  }

  // 更新策略状态
  public updateStatus(id: number, status: string): DatabaseResult {
    const updateData: Partial<StrategyPackage> = {
      status: status as any
    };
    
    return this.update(id, updateData);
  }

  // 更新策略参数
  public updateParameters(id: number, parameters: Record<string, unknown>): DatabaseResult {
    const updateData: Partial<StrategyPackage> = {
      parameters: JSON.stringify(parameters)
    };
    
    return this.update(id, updateData);
  }

  // 获取策略统计信息
  public getStrategyStats(): {
    status: string;
    risk_level: string;
    count: number;
    avg_expected_return: number;
    total_position_size: number;
  }[] {
    const sql = `
      SELECT 
        status,
        risk_level,
        COUNT(*) as count,
        AVG(expected_return) as avg_expected_return,
        SUM(max_position_size) as total_position_size
      FROM ${this.tableName}
      GROUP BY status, risk_level
      ORDER BY status, risk_level
    `;
    
    return this.executeQuery(sql) as any[];
  }

  // 获取策略性能指标
  public getPerformanceMetrics(strategyId: number): StrategyPackage | null {
    const sql = `
      SELECT 
        sp.*,
        ts.total_pnl,
        ts.win_rate,
        ts.max_drawdown,
        COUNT(o.id) as total_orders,
        SUM(CASE WHEN o.status = 'filled' THEN 1 ELSE 0 END) as filled_orders,
        AVG(o.avg_fill_price) as avg_fill_price
      FROM ${this.tableName} sp
      LEFT JOIN trading_sessions ts ON sp.session_id = ts.id
      LEFT JOIN orders o ON sp.id = o.strategy_id
      WHERE sp.id = ?
      GROUP BY sp.id
    `;
    
    return this.executeQuery(sql, [strategyId])[0] as any || null;
  }

  // 查询策略包的风险评估历史
  public getRiskAssessmentHistory(strategyId: number): Record<string, unknown>[] {
    const sql = `
      SELECT 
        ra.*,
        u.username as assessed_by_name
      FROM risk_assessments ra
      LEFT JOIN users u ON ra.assessed_by = u.id
      WHERE ra.strategy_id = ?
      ORDER BY ra.created_at DESC
    `;
    
    return this.executeQuery(sql, [strategyId]) as any[];
  }

  // 查询策略包的预算申请历史
  public getBudgetApplicationHistory(strategyId: number): Record<string, unknown>[] {
    const sql = `
      SELECT 
        ba.*,
        u1.username as applicant_name,
        u2.username as approved_by_name
      FROM budget_applications ba
      LEFT JOIN strategy_packages sp ON ba.strategy_id = sp.id
      LEFT JOIN trading_sessions ts ON sp.session_id = ts.id
      LEFT JOIN users u1 ON ts.user_id = u1.id
      LEFT JOIN users u2 ON ba.approved_by = u2.id
      WHERE ba.strategy_id = ?
      ORDER BY ba.created_at DESC
    `;
    
    return this.executeQuery(sql, [strategyId]) as any[];
  }

  // 创建策略包
  public createStrategy(strategyData: Partial<StrategyPackage>): DatabaseResult {
    // 设置默认值
    const defaultData = {
      status: 'pending' as 'pending' | 'approved' | 'rejected' | 'active' | 'paused',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      ...strategyData
    };
    
    return this.create(defaultData);
  }

  // 批量更新策略状态
  public batchUpdateStatus(strategyIds: number[], status: string): DatabaseResult {
    if (!strategyIds || strategyIds.length === 0) {
      return { success: false, error: '策略ID列表为空' };
    }

    const placeholders = strategyIds.map(() => '?').join(', ');
    const sql = `
      UPDATE ${this.tableName} 
      SET status = ?, updated_at = CURRENT_TIMESTAMP 
      WHERE id IN (${placeholders})
    `;
    
    return this.executeCommand(sql, [status, ...strategyIds]);
  }

  // 查询策略包的订单统计
  public getOrderStatistics(strategyId: number): {
    total_orders: number;
    filled_orders: number;
    cancelled_orders: number;
    rejected_orders: number;
    total_quantity: number;
    total_filled_quantity: number;
    avg_price: number;
    total_commission: number;
  } {
    const sql = `
      SELECT 
        COUNT(*) as total_orders,
        SUM(CASE WHEN status = 'filled' THEN 1 ELSE 0 END) as filled_orders,
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders,
        SUM(quantity) as total_quantity,
        SUM(filled_quantity) as total_filled_quantity,
        AVG(avg_fill_price) as avg_price,
        SUM(commission) as total_commission
      FROM orders
      WHERE strategy_id = ?
    `;
    
    return this.executeQuery(sql, [strategyId])[0] as any || {
      total_orders: 0,
      filled_orders: 0,
      cancelled_orders: 0,
      rejected_orders: 0,
      total_quantity: 0,
      total_filled_quantity: 0,
      avg_price: 0,
      total_commission: 0
    };
  }

  // 查询策略包的持仓信息
  public getPositions(strategyId: number): Record<string, unknown>[] {
    const sql = `
      SELECT 
        p.*,
        (p.market_value - (p.quantity * p.avg_cost)) as unrealized_pnl_calculated
      FROM positions p
      WHERE p.strategy_id = ?
      ORDER BY p.symbol
    `;
    
    return this.executeQuery(sql, [strategyId]) as any[];
  }

  // 查询策略包的风险指标
  public getRiskMetrics(strategyId: number): Record<string, unknown> | null {
    const sql = `
      SELECT 
        sp.*,
        ra.risk_score,
        ra.var_1d,
        ra.var_5d,
        ra.max_drawdown_limit,
        ra.position_concentration,
        ra.liquidity_risk,
        ra.market_risk,
        ra.assessment_result
      FROM ${this.tableName} sp
      LEFT JOIN (
        SELECT DISTINCT strategy_id, 
               FIRST_VALUE(risk_score) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as risk_score,
               FIRST_VALUE(var_1d) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as var_1d,
               FIRST_VALUE(var_5d) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as var_5d,
               FIRST_VALUE(max_drawdown_limit) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as max_drawdown_limit,
               FIRST_VALUE(position_concentration) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as position_concentration,
               FIRST_VALUE(liquidity_risk) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as liquidity_risk,
               FIRST_VALUE(market_risk) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as market_risk,
               FIRST_VALUE(assessment_result) OVER (PARTITION BY strategy_id ORDER BY created_at DESC) as assessment_result
        FROM risk_assessments
      ) ra ON sp.id = ra.strategy_id
      WHERE sp.id = ?
    `;
    
    return this.executeQuery(sql, [strategyId])[0] as any || null;
  }

  // 软删除策略包（标记为已删除而不是物理删除）
  public softDelete(id: number): DatabaseResult {
    return this.updateStatus(id, 'deleted');
  }

  // 恢复已删除的策略包
  public restore(id: number): DatabaseResult {
    return this.updateStatus(id, 'pending');
  }
}

// 导出策略DAO实例
export const strategyDAO = new StrategyDAO();
export default StrategyDAO;