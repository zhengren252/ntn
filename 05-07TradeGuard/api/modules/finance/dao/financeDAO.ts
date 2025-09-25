import { BaseDAO } from '../../../shared/database/dao';


/**
 * 预算申请数据访问对象
 */
export class BudgetRequestDAO extends BaseDAO<Record<string, unknown>> {
  constructor() {
    super('budget_requests');
  }

  /**
   * 初始化预算申请表
   */
  async initialize(): Promise<void> {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS budget_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        request_type TEXT NOT NULL CHECK (request_type IN ('initial', 'additional', 'emergency')),
        requested_amount REAL NOT NULL CHECK (requested_amount > 0),
        approved_amount REAL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
        priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
        justification TEXT,
        risk_assessment TEXT,
        requested_by TEXT NOT NULL,
        reviewed_by TEXT,
        approved_by TEXT,
        review_notes TEXT,
        approval_notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        reviewed_at TEXT,
        approved_at TEXT,
        expires_at TEXT,
        metadata TEXT -- JSON格式的额外信息
      )
    `;
    
    this.db.exec(createTableSQL);
    
    // 创建索引
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_budget_requests_strategy_id ON budget_requests(strategy_id)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_budget_requests_status ON budget_requests(status)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_budget_requests_created_at ON budget_requests(created_at)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_budget_requests_priority ON budget_requests(priority)');
  }

  /**
   * 根据策略ID查询预算申请
   */
  findByStrategyId(strategyId: number): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE strategy_id = ? ORDER BY created_at DESC`;
    return this.executeQuery(sql, [strategyId]);
  }

  /**
   * 根据状态查询预算申请
   */
  findByStatus(status: string): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE status = ? ORDER BY created_at DESC`;
    return this.executeQuery(sql, [status]);
  }

  /**
   * 查询待审批的预算申请
   */
  findPendingRequests(): Record<string, unknown>[] {
    return this.findByStatus('pending');
  }

  /**
   * 查询高优先级预算申请
   */
  findHighPriorityRequests(): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE priority IN ('high', 'urgent') ORDER BY created_at DESC`;
    return this.executeQuery(sql);
  }

  /**
   * 查询即将过期的预算申请
   */
  findExpiringRequests(hoursAhead: number = 24): Record<string, unknown>[] {
    const expiryThreshold = new Date();
    expiryThreshold.setHours(expiryThreshold.getHours() + hoursAhead);
    
    const sql = `
      SELECT * FROM budget_requests 
      WHERE status = 'pending' 
        AND expires_at IS NOT NULL 
        AND expires_at <= ?
      ORDER BY expires_at ASC
    `;
    
    return this.db.prepare(sql).all(expiryThreshold.toISOString()) as Record<string, unknown>[];
  }

  /**
   * 更新预算申请状态
   */
  async updateStatus(requestId: number, status: string, reviewNotes?: string, reviewedBy?: string): Promise<boolean> {
    const updateData: Record<string, unknown> = {
      status,
      reviewed_at: new Date().toISOString()
    };
    
    if (reviewNotes) updateData.review_notes = reviewNotes;
    if (reviewedBy) updateData.reviewed_by = reviewedBy;
    
    const result = await this.update(requestId, updateData);
    return (result as { success: boolean }).success;
  }

  /**
   * 批准预算申请
   */
  async approveRequest(requestId: number, approvedAmount: number, approvedBy: string, approvalNotes?: string): Promise<boolean> {
    const updateData = {
      status: 'approved',
      approved_amount: approvedAmount,
      approved_by: approvedBy,
      approved_at: new Date().toISOString(),
      approval_notes: approvalNotes || ''
    };
    
    const result = await this.update(requestId, updateData);
    return (result as { success: boolean }).success;
  }

  /**
   * 拒绝预算申请
   */
  async rejectRequest(requestId: number, rejectedBy: string, rejectionReason: string): Promise<boolean> {
    const updateData = {
      status: 'rejected',
      reviewed_by: rejectedBy,
      reviewed_at: new Date().toISOString(),
      review_notes: rejectionReason
    };
    
    const result = await this.update(requestId, updateData);
    return (result as { success: boolean }).success;
  }

  /**
   * 获取预算申请统计
   */
  getBudgetRequestStats(): {
    byStatus: Array<{
      status: string;
      count: number;
      total_requested: number;
      total_approved: number;
      avg_requested: number;
    }>;
    total: {
      total_requests: number;
      total_requested_amount: number;
      total_approved_amount: number;
    };
  } {
    const sql = `
      SELECT 
        status,
        COUNT(*) as count,
        SUM(requested_amount) as total_requested,
        SUM(approved_amount) as total_approved,
        AVG(requested_amount) as avg_requested
      FROM budget_requests 
      GROUP BY status
    `;
    
    const stats = this.db.prepare(sql).all() as Array<{
      status: string;
      count: number;
      total_requested: number;
      total_approved: number;
      avg_requested: number;
    }>;
    
    const totalStats = this.db.prepare(`
      SELECT 
        COUNT(*) as total_requests,
        SUM(requested_amount) as total_requested_amount,
        SUM(approved_amount) as total_approved_amount
      FROM budget_requests
    `).get() as {
      total_requests: number;
      total_requested_amount: number;
      total_approved_amount: number;
    };
    
    return {
      byStatus: stats,
      total: totalStats
    };
  }

  /**
   * 获取策略预算使用情况
   */
  getStrategyBudgetUsage(strategyId: number): {
    total_approved: number;
    pending_amount: number;
    total_requests: number;
    approved_requests: number;
  } | null {
    const sql = `
      SELECT 
        SUM(CASE WHEN status = 'approved' THEN approved_amount ELSE 0 END) as total_approved,
        SUM(CASE WHEN status = 'pending' THEN requested_amount ELSE 0 END) as pending_amount,
        COUNT(*) as total_requests,
        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_requests
      FROM budget_requests 
      WHERE strategy_id = ?
    `;
    
    return this.db.prepare(sql).get(strategyId) as {
      total_approved: number;
      pending_amount: number;
      total_requests: number;
      approved_requests: number;
    } | null;
  }
}

/**
 * 资金分配数据访问对象
 */
export class FundAllocationDAO extends BaseDAO<Record<string, unknown>> {
  constructor() {
    super('fund_allocations');
  }

  /**
   * 初始化资金分配表
   */
  async initialize(): Promise<void> {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS fund_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER NOT NULL,
        allocation_type TEXT NOT NULL CHECK (allocation_type IN ('initial', 'rebalance', 'emergency', 'profit_reinvest')),
        allocated_amount REAL NOT NULL CHECK (allocated_amount > 0),
        available_amount REAL NOT NULL DEFAULT 0,
        used_amount REAL NOT NULL DEFAULT 0,
        reserved_amount REAL NOT NULL DEFAULT 0,
        allocation_ratio REAL CHECK (allocation_ratio >= 0 AND allocation_ratio <= 1),
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'expired', 'recalled')),
        risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
        allocated_by TEXT NOT NULL,
        allocation_reason TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        expires_at TEXT,
        last_updated TEXT NOT NULL DEFAULT (datetime('now')),
        metadata TEXT -- JSON格式的分配详情
      )
    `;
    
    this.db.exec(createTableSQL);
    
    // 创建索引
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_fund_allocations_strategy_id ON fund_allocations(strategy_id)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_fund_allocations_status ON fund_allocations(status)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_fund_allocations_created_at ON fund_allocations(created_at)');
  }

  /**
   * 根据策略ID查询资金分配
   */
  findByStrategyId(strategyId: number): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE strategy_id = ? ORDER BY created_at DESC`;
    return this.executeQuery(sql, [strategyId]);
  }

  /**
   * 查询活跃的资金分配
   */
  findActiveAllocations(): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE status = 'active' ORDER BY created_at DESC`;
    return this.executeQuery(sql);
  }

  /**
   * 查询策略的活跃分配
   */
  findActiveAllocationsByStrategy(strategyId: number): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE strategy_id = ? AND status = 'active' ORDER BY created_at DESC`;
    return this.executeQuery(sql, [strategyId]);
  }

  /**
   * 更新资金使用情况
   */
  async updateFundUsage(allocationId: number, usedAmount: number, reservedAmount?: number): Promise<boolean> {
    const allocation = this.findById(allocationId);
    if (!allocation) return false;
    
    const allocatedAmount = (allocation as { allocated_amount: number }).allocated_amount;
    const currentReservedAmount = (allocation as { reserved_amount: number }).reserved_amount;
    
    const updateData: Record<string, unknown> = {
      used_amount: usedAmount,
      available_amount: allocatedAmount - usedAmount - (reservedAmount || currentReservedAmount),
      last_updated: new Date().toISOString()
    };
    
    if (reservedAmount !== undefined) {
      updateData.reserved_amount = reservedAmount;
      updateData.available_amount = allocatedAmount - usedAmount - reservedAmount;
    }
    
    const result = await this.update(allocationId, updateData);
    return (result as { success: boolean }).success;
  }

  /**
   * 冻结资金分配
   */
  async freezeAllocation(allocationId: number, reason: string): Promise<boolean> {
    const result = await this.update(allocationId, {
      status: 'frozen',
      allocation_reason: reason,
      last_updated: new Date().toISOString()
    });
    return (result as { success: boolean }).success;
  }

  /**
   * 解冻资金分配
   */
  async unfreezeAllocation(allocationId: number): Promise<boolean> {
    const result = await this.update(allocationId, {
      status: 'active',
      last_updated: new Date().toISOString()
    });
    return (result as { success: boolean }).success;
  }

  /**
   * 获取总资金分配统计
   */
  getTotalAllocationStats(): {
    total_allocated: number;
    total_available: number;
    total_used: number;
    total_reserved: number;
    total_allocations: number;
    active_allocations: number;
  } {
    const sql = `
      SELECT 
        SUM(allocated_amount) as total_allocated,
        SUM(available_amount) as total_available,
        SUM(used_amount) as total_used,
        SUM(reserved_amount) as total_reserved,
        COUNT(*) as total_allocations,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_allocations
      FROM fund_allocations
    `;
    
    return this.db.prepare(sql).get() as {
      total_allocated: number;
      total_available: number;
      total_used: number;
      total_reserved: number;
      total_allocations: number;
      active_allocations: number;
    };
  }

  /**
   * 获取策略资金分配统计
   */
  getStrategyAllocationStats(strategyId: number): {
    total_allocated: number;
    total_available: number;
    total_used: number;
    total_reserved: number;
    total_allocations: number;
    avg_allocation_ratio: number;
  } {
    const sql = `
      SELECT 
        SUM(allocated_amount) as total_allocated,
        SUM(available_amount) as total_available,
        SUM(used_amount) as total_used,
        SUM(reserved_amount) as total_reserved,
        COUNT(*) as total_allocations,
        AVG(allocation_ratio) as avg_allocation_ratio
      FROM fund_allocations 
      WHERE strategy_id = ?
    `;
    
    return this.db.prepare(sql).get(strategyId) as {
      total_allocated: number;
      total_available: number;
      total_used: number;
      total_reserved: number;
      total_allocations: number;
      avg_allocation_ratio: number;
    };
  }

  /**
   * 获取资金使用率排行
   */
  getFundUtilizationRanking(limit: number = 10): {
    strategy_id: number;
    total_allocated: number;
    total_used: number;
    utilization_rate: number;
  }[] {
    const sql = `
      SELECT 
        strategy_id,
        SUM(allocated_amount) as total_allocated,
        SUM(used_amount) as total_used,
        ROUND(SUM(used_amount) * 100.0 / SUM(allocated_amount), 2) as utilization_rate
      FROM fund_allocations 
      WHERE status = 'active' AND allocated_amount > 0
      GROUP BY strategy_id
      ORDER BY utilization_rate DESC
      LIMIT ?
    `;
    
    return this.db.prepare(sql).all(limit) as {
      strategy_id: number;
      total_allocated: number;
      total_used: number;
      utilization_rate: number;
    }[];
  }
}

/**
 * 账户管理数据访问对象
 */
export class AccountDAO extends BaseDAO<Record<string, unknown>> {
  constructor() {
    super('accounts');
  }

  /**
   * 初始化账户表
   */
  async initialize(): Promise<void> {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_type TEXT NOT NULL CHECK (account_type IN ('master', 'strategy', 'reserve', 'profit')),
        account_name TEXT NOT NULL,
        account_number TEXT UNIQUE,
        balance REAL NOT NULL DEFAULT 0,
        available_balance REAL NOT NULL DEFAULT 0,
        frozen_balance REAL NOT NULL DEFAULT 0,
        currency TEXT NOT NULL DEFAULT 'USD',
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'closed', 'suspended')),
        risk_level TEXT NOT NULL DEFAULT 'medium' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
        daily_limit REAL DEFAULT 0,
        monthly_limit REAL DEFAULT 0,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_transaction_at TEXT,
        last_health_check TEXT,
        metadata TEXT -- JSON格式的账户详情
      )
    `;
    
    this.db.exec(createTableSQL);
    
    // 创建索引
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_accounts_number ON accounts(account_number)');
  }

  /**
   * 根据账户类型查询
   */
  findByAccountType(accountType: string): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE account_type = ? ORDER BY created_at DESC`;
    return this.executeQuery(sql, [accountType]);
  }

  /**
   * 根据账户号查询
   */
  findByAccountNumber(accountNumber: string): Record<string, unknown> | null {
    const sql = `SELECT * FROM ${this.tableName} WHERE account_number = ? LIMIT 1`;
    const results = this.executeQuery(sql, [accountNumber]);
    return results.length > 0 ? results[0] : null;
  }

  /**
   * 查询活跃账户
   */
  findActiveAccounts(): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE status = 'active' ORDER BY balance DESC`;
    return this.executeQuery(sql);
  }

  /**
   * 查询低余额账户
   */
  findLowBalanceAccounts(threshold: number = 1000): Record<string, unknown>[] {
    const sql = `
      SELECT * FROM accounts 
      WHERE status = 'active' AND available_balance < ?
      ORDER BY available_balance ASC
    `;
    
    return this.db.prepare(sql).all(threshold) as Record<string, unknown>[];
  }

  /**
   * 更新账户余额
   */
  async updateBalance(accountId: number, newBalance: number, frozenAmount?: number): Promise<boolean> {
    const updateData: Record<string, unknown> = {
      balance: newBalance,
      last_transaction_at: new Date().toISOString()
    };
    
    if (frozenAmount !== undefined) {
      updateData.frozen_balance = frozenAmount;
      updateData.available_balance = newBalance - frozenAmount;
    } else {
      const account = this.findById(accountId);
      if (account) {
        const frozenBalance = (account as { frozen_balance: number }).frozen_balance;
        updateData.available_balance = newBalance - frozenBalance;
      }
    }
    
    const result = await this.update(accountId, updateData);
    return (result as { success: boolean }).success;
  }

  /**
   * 冻结账户资金
   */
  async freezeFunds(accountId: number, amount: number): Promise<boolean> {
    const account = this.findById(accountId);
    if (!account) {
      return false;
    }
    
    const availableBalance = (account as { available_balance: number }).available_balance;
    const frozenBalance = (account as { frozen_balance: number }).frozen_balance;
    
    if (availableBalance < amount) {
      return false;
    }
    
    const result = await this.update(accountId, {
      frozen_balance: frozenBalance + amount,
      available_balance: availableBalance - amount,
      last_transaction_at: new Date().toISOString()
    });
    return (result as { success: boolean }).success;
  }

  /**
   * 解冻账户资金
   */
  async unfreezeFunds(accountId: number, amount: number): Promise<boolean> {
    const account = this.findById(accountId);
    if (!account) {
      return false;
    }
    
    const availableBalance = (account as { available_balance: number }).available_balance;
    const frozenBalance = (account as { frozen_balance: number }).frozen_balance;
    
    if (frozenBalance < amount) {
      return false;
    }
    
    const result = await this.update(accountId, {
      frozen_balance: frozenBalance - amount,
      available_balance: availableBalance + amount,
      last_transaction_at: new Date().toISOString()
    });
    return (result as { success: boolean }).success;
  }

  /**
   * 更新账户状态
   */
  async updateAccountStatus(accountId: number, status: string, reason?: string): Promise<boolean> {
    const updateData: Record<string, unknown> = {
      status,
      last_health_check: new Date().toISOString()
    };
    
    if (reason) {
      const account = this.findById(accountId);
      if (account) {
        const accountMetadata = (account as { metadata?: string }).metadata;
        const metadata = accountMetadata ? JSON.parse(accountMetadata) : {};
        metadata.statusChangeReason = reason;
        metadata.statusChangeTime = new Date().toISOString();
        updateData.metadata = JSON.stringify(metadata);
      }
    }
    
    const result = await this.update(accountId, updateData);
    return (result as { success: boolean }).success;
  }

  /**
   * 获取账户健康状态
   */
  getAccountHealthStatus(): Record<string, unknown>[] {
    const sql = `
      SELECT 
        id,
        account_name,
        account_type,
        balance,
        available_balance,
        frozen_balance,
        status,
        risk_level,
        CASE 
          WHEN available_balance < 1000 THEN 'low_balance'
          WHEN frozen_balance > balance * 0.8 THEN 'high_frozen'
          WHEN status != 'active' THEN 'inactive'
          ELSE 'healthy'
        END as health_status
      FROM accounts
      ORDER BY 
        CASE health_status
          WHEN 'low_balance' THEN 1
          WHEN 'high_frozen' THEN 2
          WHEN 'inactive' THEN 3
          ELSE 4
        END,
        available_balance ASC
    `;
    
    return this.db.prepare(sql).all() as Record<string, unknown>[];
  }

  /**
   * 获取账户统计信息
   */
  getAccountStats(): {
    byType: {
      account_type: string;
      count: number;
      total_balance: number;
      total_available: number;
      total_frozen: number;
      avg_balance: number;
    }[];
    total: {
      total_accounts: number;
      total_balance: number;
      total_available: number;
      total_frozen: number;
    };
  } {
    const sql = `
      SELECT 
        account_type,
        COUNT(*) as count,
        SUM(balance) as total_balance,
        SUM(available_balance) as total_available,
        SUM(frozen_balance) as total_frozen,
        AVG(balance) as avg_balance
      FROM accounts 
      WHERE status = 'active'
      GROUP BY account_type
    `;
    
    const byType = this.db.prepare(sql).all() as {
      account_type: string;
      count: number;
      total_balance: number;
      total_available: number;
      total_frozen: number;
      avg_balance: number;
    }[];
    
    const totalStats = this.db.prepare(`
      SELECT 
        COUNT(*) as total_accounts,
        SUM(balance) as total_balance,
        SUM(available_balance) as total_available,
        SUM(frozen_balance) as total_frozen
      FROM accounts 
      WHERE status = 'active'
    `).get() as {
      total_accounts: number;
      total_balance: number;
      total_available: number;
      total_frozen: number;
    };
    
    return {
      byType,
      total: totalStats
    };
  }
}

/**
 * 财务交易记录数据访问对象
 */
export class FinancialTransactionDAO extends BaseDAO<Record<string, unknown>> {
  constructor() {
    super('financial_transactions');
  }

  /**
   * 初始化财务交易表
   */
  async initialize(): Promise<void> {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS financial_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('allocation', 'withdrawal', 'transfer', 'fee', 'profit', 'loss')),
        from_account_id INTEGER,
        to_account_id INTEGER,
        strategy_id INTEGER,
        amount REAL NOT NULL CHECK (amount != 0),
        currency TEXT NOT NULL DEFAULT 'USD',
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
        reference_id TEXT,
        description TEXT,
        created_by TEXT NOT NULL,
        approved_by TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT,
        metadata TEXT -- JSON格式的交易详情
      )
    `;
    
    this.db.exec(createTableSQL);
    
    // 创建索引
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_financial_transactions_type ON financial_transactions(transaction_type)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_financial_transactions_status ON financial_transactions(status)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_financial_transactions_created_at ON financial_transactions(created_at)');
    this.db.exec('CREATE INDEX IF NOT EXISTS idx_financial_transactions_strategy_id ON financial_transactions(strategy_id)');
  }

  /**
   * 根据策略ID查询交易记录
   */
  findByStrategyId(strategyId: number): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE strategy_id = ? ORDER BY created_at DESC`;
    return this.executeQuery(sql, [strategyId]);
  }

  /**
   * 根据账户ID查询交易记录
   */
  findByAccountId(accountId: number): Record<string, unknown>[] {
    const sql = `
      SELECT * FROM financial_transactions 
      WHERE from_account_id = ? OR to_account_id = ?
      ORDER BY created_at DESC
    `;
    
    return this.db.prepare(sql).all(accountId, accountId) as Record<string, unknown>[];
  }

  /**
   * 根据交易类型查询
   */
  findByTransactionType(transactionType: string): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE transaction_type = ? ORDER BY created_at DESC`;
    return this.executeQuery(sql, [transactionType]) as Record<string, unknown>[];
  }

  /**
   * 查询待处理交易
   */
  findPendingTransactions(): Record<string, unknown>[] {
    const sql = `SELECT * FROM ${this.tableName} WHERE status = 'pending' ORDER BY created_at ASC`;
    return this.executeQuery(sql);
  }

  /**
   * 获取交易统计
   */
  getTransactionStats(days: number = 30): {
    transaction_type: string;
    status: string;
    count: number;
    total_amount: number;
    avg_amount: number;
  }[] {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    const sql = `
      SELECT 
        transaction_type,
        status,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        AVG(amount) as avg_amount
      FROM financial_transactions 
      WHERE created_at >= ?
      GROUP BY transaction_type, status
    `;
    
    return this.db.prepare(sql).all(startDate.toISOString()) as {
      transaction_type: string;
      status: string;
      count: number;
      total_amount: number;
      avg_amount: number;
    }[];
  }

  /**
   * 获取策略财务摘要
   */
  getStrategyFinancialSummary(strategyId: number): {
    total_allocated: number;
    total_profit: number;
    total_loss: number;
    total_fees: number;
    total_transactions: number;
  } | null {
    const sql = `
      SELECT 
        SUM(CASE WHEN transaction_type = 'allocation' AND status = 'completed' THEN amount ELSE 0 END) as total_allocated,
        SUM(CASE WHEN transaction_type = 'profit' AND status = 'completed' THEN amount ELSE 0 END) as total_profit,
        SUM(CASE WHEN transaction_type = 'loss' AND status = 'completed' THEN ABS(amount) ELSE 0 END) as total_loss,
        SUM(CASE WHEN transaction_type = 'fee' AND status = 'completed' THEN amount ELSE 0 END) as total_fees,
        COUNT(*) as total_transactions
      FROM financial_transactions 
      WHERE strategy_id = ?
    `;
    
    return this.db.prepare(sql).get(strategyId) as {
      total_allocated: number;
      total_profit: number;
      total_loss: number;
      total_fees: number;
      total_transactions: number;
    } | null;
  }
}

// 导出DAO实例
export const budgetRequestDAO = new BudgetRequestDAO();
export const fundAllocationDAO = new FundAllocationDAO();
export const accountDAO = new AccountDAO();
export const financialTransactionDAO = new FinancialTransactionDAO();