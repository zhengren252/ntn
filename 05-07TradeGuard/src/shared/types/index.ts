// 交易执行铁三角 - 共享类型定义

// 环境类型
export type Environment = 'development' | 'staging' | 'production';

// 用户角色
export type UserRole = 'admin' | 'trader' | 'risk_manager' | 'finance_manager';

// 用户接口
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// 交易会话状态
export type SessionStatus = 'active' | 'paused' | 'stopped' | 'completed';

// 交易会话接口
export interface TradingSession {
  id: string;
  userId: string;
  status: SessionStatus;
  startTime: string;
  endTime?: string;
  configuration: Record<string, unknown>;
  totalPnl: number;
  createdAt: string;
}

// 策略包状态
export type StrategyPackageStatus = 
  | 'pending' 
  | 'risk_assessment' 
  | 'budget_approval' 
  | 'executing' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

// 策略包接口
export interface StrategyPackage {
  id: string;
  sessionId: string;
  strategyId: string;
  symbol: string;
  amount: number;
  parameters: Record<string, unknown>;
  priority: number; // 1-10
  status: StrategyPackageStatus;
  createdAt: string;
  updatedAt: string;
}

// 风险评估状态
export type RiskAssessmentStatus = 'pending' | 'approved' | 'rejected' | 'requires_review';

// 风险评估接口
export interface RiskAssessment {
  id: string;
  packageId: string;
  assessorId: string;
  riskScore: number; // 1.0-10.0
  riskFactors: string[];
  recommendations: string[];
  status: RiskAssessmentStatus;
  assessedAt: string;
}

// 预算申请状态
export type BudgetApplicationStatus = 'pending' | 'approved' | 'rejected' | 'partial_approved';

// 预算申请接口
export interface BudgetApplication {
  id: string;
  packageId: string;
  applicantId: string;
  requestedAmount: number;
  approvedAmount: number;
  riskScore?: number;
  status: BudgetApplicationStatus;
  conditions?: string[];
  appliedAt: string;
  approvedAt?: string;
}

// 订单类型
export type OrderType = 'market' | 'limit' | 'twap' | 'vwap';
export type OrderSide = 'buy' | 'sell';
export type OrderStatus = 'pending' | 'partial_filled' | 'filled' | 'cancelled' | 'failed';

// 订单接口
export interface Order {
  id: string;
  packageId: string;
  symbol: string;
  orderType: OrderType;
  side: OrderSide;
  quantity: number;
  price?: number;
  executedQuantity: number;
  averagePrice: number;
  status: OrderStatus;
  createdAt: string;
  executedAt?: string;
}

// 持仓接口
export interface Position {
  id: string;
  sessionId: string;
  symbol: string;
  quantity: number;
  averagePrice: number;
  unrealizedPnl: number;
  lastUpdated: string;
}

// 风险警报严重程度
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'active' | 'acknowledged' | 'resolved';

// 风险警报接口
export interface RiskAlert {
  id: string;
  alertType: string;
  severity: AlertSeverity;
  message: string;
  affectedSymbols?: string[];
  sourceModule?: string;
  status: AlertStatus;
  createdAt: string;
  resolvedAt?: string;
}

// ZeroMQ消息接口
export interface ZMQMessage {
  type: string;
  payload: unknown;
  timestamp: string;
  source: string;
  target?: string;
  correlationId?: string;
}

// API响应接口
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

// 分页接口
export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// 系统状态接口
export interface SystemStatus {
  trader: {
    status: 'online' | 'offline' | 'error';
    activeOrders: number;
    totalPositions: number;
    lastUpdate: string;
  };
  risk: {
    status: 'online' | 'offline' | 'error';
    activeAlerts: number;
    riskLevel: AlertSeverity;
    lastUpdate: string;
  };
  finance: {
    status: 'online' | 'offline' | 'error';
    totalBalance: number;
    availableBalance: number;
    allocatedFunds: number;
    lastUpdate: string;
  };
  masterControl: {
    status: 'online' | 'offline' | 'error';
    mode: 'normal' | 'defensive' | 'emergency';
    lastUpdate: string;
  };
}

// 配置接口
export interface AppConfig {
  app: {
    name: string;
    version: string;
    environment: Environment;
    debug: boolean;
  };
  server: {
    port: number;
    host: string;
  };
  database: {
    type: string;
    filename: string;
  };
  redis: {
    host: string;
    port: number;
    db: number;
    keyPrefix: string;
  };
  zeromq: {
    trader: { pub_port: number; rep_port: number };
    risk: { pub_port: number; rep_port: number };
    finance: { pub_port: number; rep_port: number };
    master_control: { pub_port: number; rep_port: number };
  };
}