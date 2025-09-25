import { BaseDAO } from '../../../shared/database/dao';
import { dbConnection } from '../../../shared/database/connection';
import { RiskAssessment, RiskAlert } from '../../../shared/database/models';

// 风险评估DAO
export class RiskAssessmentDAO extends BaseDAO<RiskAssessment> {
  constructor() {
    super('risk_assessments');
  }

  // 根据策略ID查询风险评估
  findByStrategyId(strategyId: number): RiskAssessment[] {
    const query = `
      SELECT * FROM ${this.tableName} 
      WHERE strategy_id = ? 
      ORDER BY created_at DESC
    `;
    return this.db.prepare(query).all(strategyId) as RiskAssessment[];
  }

  // 获取最新的风险评估
  findLatestByStrategyId(strategyId: number): RiskAssessment | null {
    const query = `
      SELECT * FROM ${this.tableName} 
      WHERE strategy_id = ? 
      ORDER BY created_at DESC 
      LIMIT 1
    `;
    return this.db.prepare(query).get(strategyId) as RiskAssessment || null;
  }

  // 根据风险等级查询评估
  findByRiskLevel(riskLevel: string): RiskAssessment[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.risk_level = ?
      ORDER BY ra.created_at DESC
    `;
    return this.db.prepare(query).all(riskLevel) as RiskAssessment[];
  }

  // 根据评估状态查询
  findByStatus(status: string): RiskAssessment[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.status = ?
      ORDER BY ra.created_at DESC
    `;
    return this.db.prepare(query).all(status) as RiskAssessment[];
  }

  // 获取待审批的风险评估
  findPendingAssessments(): RiskAssessment[] {
    return this.findByStatus('pending');
  }

  // 获取高风险评估
  findHighRiskAssessments(): RiskAssessment[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.risk_level = 'high' OR ra.risk_score >= 80
      ORDER BY ra.risk_score DESC, ra.created_at DESC
    `;
    return this.db.prepare(query).all() as RiskAssessment[];
  }

  // 更新评估状态
  updateStatus(id: number, status: string, reviewNotes?: string): boolean {
    const query = `
      UPDATE ${this.tableName} 
      SET status = ?, review_notes = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `;
    const result = this.db.prepare(query).run(status, reviewNotes || null, id);
    return result.changes > 0;
  }

  // 更新风险评分
  updateRiskScore(id: number, riskScore: number, riskLevel: string): boolean {
    const query = `
      UPDATE ${this.tableName} 
      SET risk_score = ?, risk_level = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `;
    const result = this.db.prepare(query).run(riskScore, riskLevel, id);
    return result.changes > 0;
  }

  // 获取风险评估统计
  getRiskAssessmentStats(): {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
    low_risk: number;
    medium_risk: number;
    high_risk: number;
    avg_risk_score: number;
    max_risk_score: number;
    min_risk_score: number;
  } | null {
    const query = `
      SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
        COUNT(CASE WHEN risk_level = 'low' THEN 1 END) as low_risk,
        COUNT(CASE WHEN risk_level = 'medium' THEN 1 END) as medium_risk,
        COUNT(CASE WHEN risk_level = 'high' THEN 1 END) as high_risk,
        AVG(risk_score) as avg_risk_score,
        MAX(risk_score) as max_risk_score,
        MIN(risk_score) as min_risk_score
      FROM ${this.tableName}
      WHERE created_at >= date('now', '-30 days')
    `;
    const result = this.db.prepare(query).get();
    return result as {
      total: number;
      pending: number;
      approved: number;
      rejected: number;
      low_risk: number;
      medium_risk: number;
      high_risk: number;
      avg_risk_score: number;
      max_risk_score: number;
      min_risk_score: number;
    } | null;
  }

  // 获取策略风险历史
  getStrategyRiskHistory(strategyId: number, days: number = 30): RiskAssessment[] {
    const query = `
      SELECT * FROM ${this.tableName}
      WHERE strategy_id = ? AND created_at >= date('now', '-${days} days')
      ORDER BY created_at ASC
    `;
    return this.db.prepare(query).all(strategyId) as RiskAssessment[];
  }

  // 批量创建风险评估
  batchCreateAssessments(assessments: Partial<RiskAssessment>[]): number {
    const query = `
      INSERT INTO ${this.tableName} (
        strategy_id, risk_score, risk_level, assessment_details, 
        recommendations, status, assessed_by
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    const stmt = this.db.prepare(query);
    const transaction = this.db.transaction((assessments: Partial<RiskAssessment>[]) => {
      let insertedCount = 0;
      for (const assessment of assessments) {
        if (assessment) {
          const result = stmt.run(
            assessment.strategy_id,
            assessment.risk_score,
            'medium', // risk_level
            JSON.stringify(assessment), // assessment_details
            assessment.recommendations,
            assessment.assessment_result || 'conditional',
            assessment.assessed_by
          );
          if (result.changes > 0) insertedCount++;
        }
      }
      return insertedCount;
    });
    
    return transaction(assessments);
  }
}

// 风险警报DAO
export class RiskAlertDAO extends BaseDAO<RiskAlert> {
  constructor() {
    super('risk_alerts');
  }

  // 根据策略ID查询警报
  findByStrategyId(strategyId: number): RiskAlert[] {
    const query = `
      SELECT * FROM ${this.tableName} 
      WHERE strategy_id = ? 
      ORDER BY created_at DESC
    `;
    return this.db.prepare(query).all(strategyId) as RiskAlert[];
  }

  // 根据警报类型查询
  findByAlertType(alertType: string): RiskAlert[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      LEFT JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.alert_type = ?
      ORDER BY ra.created_at DESC
    `;
    return this.db.prepare(query).all(alertType) as RiskAlert[];
  }

  // 根据严重程度查询
  findBySeverity(severity: string): RiskAlert[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      LEFT JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.severity = ?
      ORDER BY ra.created_at DESC
    `;
    return this.db.prepare(query).all(severity) as RiskAlert[];
  }

  // 获取活跃警报
  findActiveAlerts(): RiskAlert[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      LEFT JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.status = 'active'
      ORDER BY ra.severity DESC, ra.created_at DESC
    `;
    return this.db.prepare(query).all() as RiskAlert[];
  }

  // 获取未确认警报
  findUnacknowledgedAlerts(): RiskAlert[] {
    const query = `
      SELECT ra.*, sp.package_name, sp.strategy_type
      FROM ${this.tableName} ra
      LEFT JOIN strategy_packages sp ON ra.strategy_id = sp.id
      WHERE ra.acknowledged = 0
      ORDER BY ra.severity DESC, ra.created_at DESC
    `;
    return this.db.prepare(query).all() as RiskAlert[];
  }

  // 获取严重警报
  findCriticalAlerts(): RiskAlert[] {
    return this.findBySeverity('critical');
  }

  // 更新警报状态
  updateStatus(id: number, status: string): boolean {
    const query = `
      UPDATE ${this.tableName} 
      SET status = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `;
    const result = this.db.prepare(query).run(status, id);
    return result.changes > 0;
  }

  // 确认警报
  acknowledgeAlert(id: number, acknowledgedBy: string, notes?: string): boolean {
    const query = `
      UPDATE ${this.tableName} 
      SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = CURRENT_TIMESTAMP,
          resolution_notes = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `;
    const result = this.db.prepare(query).run(acknowledgedBy, notes || null, id);
    return result.changes > 0;
  }

  // 解决警报
  resolveAlert(id: number, resolvedBy: string, resolutionNotes: string): boolean {
    const query = `
      UPDATE ${this.tableName} 
      SET status = 'resolved', resolved_by = ?, resolved_at = CURRENT_TIMESTAMP,
          resolution_notes = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `;
    const result = this.db.prepare(query).run(resolvedBy, resolutionNotes, id);
    return result.changes > 0;
  }

  // 批量确认警报
  batchAcknowledgeAlerts(alertIds: number[], acknowledgedBy: string): number {
    const query = `
      UPDATE ${this.tableName} 
      SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = CURRENT_TIMESTAMP,
          updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `;
    
    const stmt = this.db.prepare(query);
    const transaction = this.db.transaction((ids: number[]) => {
      let updatedCount = 0;
      for (const id of ids) {
        const result = stmt.run(acknowledgedBy, id);
        if (result.changes > 0) updatedCount++;
      }
      return updatedCount;
    });
    
    return transaction(alertIds);
  }

  // 获取警报统计
  getAlertStats(): {
    total: number;
    active: number;
    resolved: number;
    unacknowledged: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
  } | null {
    const query = `
      SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
        COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
        COUNT(CASE WHEN acknowledged = 0 THEN 1 END) as unacknowledged,
        COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
        COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
        COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
        COUNT(CASE WHEN severity = 'low' THEN 1 END) as low
      FROM ${this.tableName}
      WHERE created_at >= date('now', '-7 days')
    `;
    const result = this.db.prepare(query).get();
    return result as {
      total: number;
      active: number;
      resolved: number;
      unacknowledged: number;
      critical: number;
      high: number;
      medium: number;
      low: number;
    } | null;
  }

  // 获取警报趋势
  getAlertTrend(days: number = 7): {
    alert_date: string;
    total_alerts: number;
    critical_alerts: number;
    high_alerts: number;
  }[] {
    const query = `
      SELECT 
        date(created_at) as alert_date,
        COUNT(*) as total_alerts,
        COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_alerts,
        COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_alerts
      FROM ${this.tableName}
      WHERE created_at >= date('now', '-${days} days')
      GROUP BY date(created_at)
      ORDER BY alert_date ASC
    `;
    const result = this.db.prepare(query).all();
    return result as {
      alert_date: string;
      total_alerts: number;
      critical_alerts: number;
      high_alerts: number;
    }[];
  }

  // 获取策略警报历史
  getStrategyAlertHistory(strategyId: number, days: number = 30): RiskAlert[] {
    const query = `
      SELECT * FROM ${this.tableName}
      WHERE strategy_id = ? AND created_at >= date('now', '-${days} days')
      ORDER BY created_at DESC
    `;
    return this.db.prepare(query).all(strategyId) as RiskAlert[];
  }

  // 清理过期警报
  cleanupExpiredAlerts(days: number = 90): number {
    const query = `
      DELETE FROM ${this.tableName}
      WHERE status = 'resolved' AND resolved_at < date('now', '-${days} days')
    `;
    const result = this.db.prepare(query).run();
    return result.changes;
  }
}

// 风险指标计算DAO
export class RiskMetricsDAO {
  private db: any;

  constructor() {
    this.db = dbConnection.getDatabase();
  }

  // 计算策略风险指标
  calculateStrategyRiskMetrics(strategyId: number): {
    strategyId: number;
    packageName: string;
    riskLevel: string;
    maxPositionSize: number;
    currentExposure: number;
    utilizationRatio: number;
    longExposure: number;
    shortExposure: number;
    unrealizedPnL: number;
    maxSinglePosition: number;
    totalOrders: number;
    orderSuccessRate: number;
    rejectionRate: number;
    avgOrderSize: number;
    calculatedAt: string;
  } | null {
    // 获取策略基本信息
    const strategyQuery = `
      SELECT * FROM strategy_packages WHERE id = ?
    `;
    const strategy = this.db.prepare(strategyQuery).get(strategyId);
    
    if (!strategy) return null;

    // 获取订单统计
    const orderStatsQuery = `
      SELECT 
        COUNT(*) as total_orders,
        COUNT(CASE WHEN status = 'filled' THEN 1 END) as filled_orders,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_orders,
        SUM(CASE WHEN status = 'filled' THEN quantity * COALESCE(avg_fill_price, price) ELSE 0 END) as total_volume,
        AVG(CASE WHEN status = 'filled' THEN quantity * COALESCE(avg_fill_price, price) ELSE NULL END) as avg_order_size
      FROM orders WHERE strategy_id = ?
    `;
    const orderStats = this.db.prepare(orderStatsQuery).get(strategyId);

    // 获取持仓统计
    const positionStatsQuery = `
      SELECT 
        COUNT(*) as total_positions,
        SUM(CASE WHEN quantity > 0 THEN quantity * current_price ELSE 0 END) as long_exposure,
        SUM(CASE WHEN quantity < 0 THEN ABS(quantity) * current_price ELSE 0 END) as short_exposure,
        SUM(unrealized_pnl) as total_unrealized_pnl,
        MAX(ABS(quantity * current_price)) as max_position_size
      FROM positions WHERE strategy_id = ?
    `;
    const positionStats = this.db.prepare(positionStatsQuery).get(strategyId);

    // 计算风险指标
    const totalExposure = (positionStats.long_exposure || 0) + (positionStats.short_exposure || 0);
    const utilizationRatio = totalExposure / strategy.max_position_size;
    const orderSuccessRate = orderStats.total_orders > 0 ? orderStats.filled_orders / orderStats.total_orders : 0;
    const rejectionRate = orderStats.total_orders > 0 ? orderStats.rejected_orders / orderStats.total_orders : 0;

    return {
      strategyId,
      packageName: strategy.package_name,
      riskLevel: strategy.risk_level,
      maxPositionSize: strategy.max_position_size,
      currentExposure: totalExposure,
      utilizationRatio,
      longExposure: positionStats.long_exposure || 0,
      shortExposure: positionStats.short_exposure || 0,
      unrealizedPnL: positionStats.total_unrealized_pnl || 0,
      maxSinglePosition: positionStats.max_position_size || 0,
      totalOrders: orderStats.total_orders || 0,
      orderSuccessRate,
      rejectionRate,
      avgOrderSize: orderStats.avg_order_size || 0,
      calculatedAt: new Date().toISOString()
    };
  }

  // 计算投资组合风险指标
  calculatePortfolioRiskMetrics(): {
    totalStrategies: number;
    totalExposure: number;
    totalUnrealizedPnL: number;
    totalMaxPositionSize: number;
    portfolioUtilization: number;
    avgUtilization: number;
    strategyMetrics: any[];
    calculatedAt: string;
    totalPortfolioValue: number;
    dailyDrawdown: number;
  } {
    // 获取所有活跃策略的风险指标
    const strategiesQuery = `
      SELECT id FROM strategy_packages WHERE status = 'active'
    `;
    const activeStrategies = this.db.prepare(strategiesQuery).all();

    let totalExposure = 0;
    let totalUnrealizedPnL = 0;
    let totalMaxPositionSize = 0;
    const strategyMetrics = [];

    for (const strategy of activeStrategies) {
      const metrics = this.calculateStrategyRiskMetrics(strategy.id);
      if (metrics) {
        strategyMetrics.push(metrics);
        totalExposure += metrics.currentExposure;
        totalUnrealizedPnL += metrics.unrealizedPnL;
        totalMaxPositionSize += metrics.maxPositionSize;
      }
    }

    // 计算投资组合级别指标
    const portfolioUtilization = totalMaxPositionSize > 0 ? totalExposure / totalMaxPositionSize : 0;
    const avgUtilization = strategyMetrics.length > 0 ? 
      strategyMetrics.reduce((sum, m) => sum + m.utilizationRatio, 0) / strategyMetrics.length : 0;
    
    const totalPortfolioValue = totalMaxPositionSize; // Using total allocated capital as proxy for portfolio value
    const dailyDrawdown = (totalUnrealizedPnL < 0 && totalPortfolioValue > 0) ? Math.abs(totalUnrealizedPnL) / totalPortfolioValue : 0;

    return {
      totalStrategies: activeStrategies.length,
      totalExposure,
      totalUnrealizedPnL,
      totalMaxPositionSize,
      portfolioUtilization,
      avgUtilization,
      strategyMetrics,
      calculatedAt: new Date().toISOString(),
      totalPortfolioValue,
      dailyDrawdown
    };
  }

  // 获取风险限额使用情况
  getRiskLimitUsage(): {
    riskLevel: string;
    strategyCount: number;
    totalLimit: number;
    totalUsage: number;
    utilizationRate: number;
  }[] {
    const query = `
      SELECT 
        sp.risk_level,
        COUNT(*) as strategy_count,
        SUM(sp.max_position_size) as total_limit,
        SUM(
          COALESCE(
            (SELECT SUM(ABS(quantity) * current_price) 
             FROM positions p WHERE p.strategy_id = sp.id), 0
          )
        ) as total_usage
      FROM strategy_packages sp
      WHERE sp.status = 'active'
      GROUP BY sp.risk_level
    `;
    
    const results = this.db.prepare(query).all();
    
    return results.map((row: Record<string, unknown>) => {
      const total_limit = row.total_limit as number;
      const total_usage = row.total_usage as number;
      return {
        riskLevel: row.risk_level as string,
        strategyCount: row.strategy_count as number,
        totalLimit: total_limit,
        totalUsage: total_usage,
        utilizationRate: total_limit > 0 ? total_usage / total_limit : 0
      }
    });
  }
}

// 导出DAO实例
export const riskAssessmentDAO = new RiskAssessmentDAO();
export const riskAlertDAO = new RiskAlertDAO();
export const riskMetricsDAO = new RiskMetricsDAO();