// 用户表模型
export interface User {
  id: number;
  username: string;
  password_hash: string;
  role: 'admin' | 'trader' | 'risk_manager' | 'finance_manager';
  email: string;
  phone?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 交易会话模型
export interface TradingSession {
  id: number;
  user_id: number;
  session_name: string;
  status: 'active' | 'paused' | 'stopped' | 'completed';
  start_time: string;
  end_time?: string;
  initial_capital: number;
  current_capital: number;
  max_drawdown: number;
  total_pnl: number;
  trade_count: number;
  win_rate: number;
  created_at: string;
  updated_at: string;
}

// 策略包模型
export interface StrategyPackage {
  id: number;
  session_id: number;
  package_name: string;
  strategy_type: 'momentum' | 'mean_reversion' | 'arbitrage' | 'market_making' | 'trend_following';
  parameters: string; // JSON字符串
  risk_level: 'low' | 'medium' | 'high';
  expected_return: number;
  max_position_size: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  status: 'pending' | 'approved' | 'rejected' | 'active' | 'paused';
  created_at: string;
  updated_at: string;
}

// 风险评估模型
export interface RiskAssessment {
  id: number;
  strategy_id: number;
  assessment_type: 'pre_trade' | 'real_time' | 'post_trade';
  risk_score: number;
  var_1d: number; // 1日风险价值
  var_5d: number; // 5日风险价值
  max_drawdown_limit: number;
  position_concentration: number;
  liquidity_risk: number;
  market_risk: number;
  credit_risk: number;
  operational_risk: number;
  assessment_result: 'approved' | 'rejected' | 'conditional';
  recommendations: string;
  assessed_by: number;
  created_at: string;
}

// 预算申请模型
export interface BudgetApplication {
  id: number;
  strategy_id: number;
  requested_amount: number;
  purpose: string;
  justification: string;
  risk_assessment_id?: number;
  status: 'pending' | 'approved' | 'rejected' | 'allocated';
  approved_amount?: number;
  approved_by?: number;
  approval_date?: string;
  conditions?: string;
  created_at: string;
  updated_at: string;
}

// 资金分配模型
export interface FundAllocation {
  id: number;
  budget_application_id: number;
  allocated_amount: number;
  allocation_type: 'initial' | 'additional' | 'rebalance' | 'withdrawal';
  effective_date: string;
  expiry_date?: string;
  utilization_rate: number;
  remaining_amount: number;
  allocation_status: 'active' | 'expired' | 'revoked' | 'fully_utilized';
  allocated_by: number;
  created_at: string;
  updated_at: string;
}

// 订单模型
export interface Order {
  id: number;
  strategy_id: number;
  symbol: string;
  order_type: 'market' | 'limit' | 'stop' | 'stop_limit';
  side: 'buy' | 'sell';
  quantity: number;
  price?: number;
  stop_price?: number;
  time_in_force: 'GTC' | 'IOC' | 'FOK' | 'DAY';
  status: 'pending' | 'submitted' | 'partial_filled' | 'filled' | 'cancelled' | 'rejected';
  filled_quantity: number;
  avg_fill_price?: number;
  commission: number;
  order_source: 'manual' | 'algorithm' | 'risk_management';
  parent_order_id?: number;
  risk_check_passed: boolean;
  submitted_at?: string;
  filled_at?: string;
  cancelled_at?: string;
  created_at: string;
  updated_at: string;
}

// 订单执行模型
export interface OrderExecution {
  id: number;
  order_id: number;
  execution_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  commission: number;
  execution_time: string;
  venue: string;
  liquidity_flag: 'maker' | 'taker';
  created_at: string;
}

// 持仓模型
export interface Position {
  id: number;
  strategy_id: number;
  symbol: string;
  quantity: number;
  avg_cost: number;
  market_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  position_type: 'long' | 'short';
  last_updated: string;
  created_at: string;
}

// 持仓更新模型
export interface PositionUpdate {
  id: number;
  position_id: number;
  update_type: 'trade' | 'mark_to_market' | 'corporate_action' | 'adjustment';
  quantity_change: number;
  price: number;
  pnl_impact: number;
  update_reason: string;
  updated_by: number;
  created_at: string;
}

// 风险警报模型
export interface RiskAlert {
  id: number;
  alert_type: 'position_limit' | 'loss_limit' | 'var_breach' | 'concentration' | 'liquidity' | 'market_volatility' | 'portfolio_risk';
  severity: 'low' | 'medium' | 'high' | 'critical';
  entity_type: 'strategy' | 'session' | 'portfolio' | 'system';
  entity_id: number;
  message: string;
  current_value: number;
  threshold_value: number;
  status: 'active' | 'acknowledged' | 'resolved' | 'escalated';
  triggered_at: string;
  acknowledged_at?: string;
  acknowledged_by?: number;
  resolved_at?: string;
  resolution_notes?: string;
  created_at: string;
}

// 数据库操作结果接口
export interface DatabaseResult {
  success: boolean;
  data?: Record<string, unknown>;
  error?: string;
  rowsAffected?: number;
  lastInsertId?: number;
}

// 分页查询参数
export interface PaginationParams {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// 分页查询结果
export interface PaginatedResult<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// 查询过滤器
export interface QueryFilter {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'like' | 'in' | 'between';
  value: unknown;
}

// 统计数据接口
export interface TradingStats {
  totalSessions: number;
  activeSessions: number;
  totalCapital: number;
  totalPnL: number;
  avgWinRate: number;
  totalTrades: number;
  riskAlerts: number;
}

// 实时数据接口
export interface RealTimeData {
  timestamp: string;
  symbol: string;
  price: number;
  volume: number;
  change: number;
  changePercent: number;
}

// 系统配置接口
export interface SystemConfig {
  key: string;
  value: string;
  description?: string;
  category: 'trading' | 'risk' | 'finance' | 'system';
  isActive: boolean;
  updatedAt: string;
}