import { Router, Request, Response } from 'express';
import { financeService, BudgetRequest, FundAllocationRequest } from '../services/financeService';
import { budgetRequestDAO, fundAllocationDAO, accountDAO, financialTransactionDAO } from '../dao/financeDAO';
import { redisCache } from '../../../shared/cache/redis';
import rateLimit from 'express-rate-limit';

const router = Router();

// 速率限制配置
const budgetLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 5, // 每分钟最多5次预算申请
  message: { error: '预算申请频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const allocationLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 10, // 每分钟最多10次资金分配操作
  message: { error: '资金分配操作频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

const approvalLimit = rateLimit({
  windowMs: 60 * 1000, // 1分钟
  max: 20, // 每分钟最多20次审批操作
  message: { error: '审批操作频率过高，请稍后再试' },
  standardHeaders: true,
  legacyHeaders: false
});

// 中间件：验证请求参数
const validateRequest = (requiredFields: string[]) => {
  return (req: Request, res: Response, next: () => void) => {
    const missingFields = requiredFields.filter(field => {
      const value = req.body[field];
      return value === undefined || value === null || value === '';
    });
    
    if (missingFields.length > 0) {
      return res.status(400).json({
        success: false,
        error: `缺少必需字段: ${missingFields.join(', ')}`
      });
    }
    
    next();
  };
};

// 中间件：验证数字参数
const validateNumericParams = (numericFields: string[]) => {
  return (req: Request, res: Response, next: () => void) => {
    const invalidFields = numericFields.filter(field => {
      const value = req.body[field];
      return value !== undefined && (isNaN(Number(value)) || Number(value) <= 0);
    });
    
    if (invalidFields.length > 0) {
      return res.status(400).json({
        success: false,
        error: `无效的数字参数: ${invalidFields.join(', ')}`
      });
    }
    
    next();
  };
};

// 预算管理路由

/**
 * @route POST /api/finance/budget/requests
 * @desc 提交预算申请
 * @access Private
 */
router.post('/budget/requests',
  budgetLimit,
  validateRequest(['strategyId', 'requestType', 'requestedAmount', 'justification', 'requestedBy']),
  validateNumericParams(['strategyId', 'requestedAmount']),
  async (req: Request, res: Response) => {
    try {
      const request: BudgetRequest = {
        strategyId: Number(req.body.strategyId),
        requestType: req.body.requestType,
        requestedAmount: Number(req.body.requestedAmount),
        priority: req.body.priority || 'normal',
        justification: req.body.justification,
        riskAssessment: req.body.riskAssessment,
        requestedBy: req.body.requestedBy,
        expiresIn: req.body.expiresIn ? Number(req.body.expiresIn) : undefined,
        metadata: req.body.metadata
      };

      const result = await financeService.processBudgetRequest(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: result.message,
          data: {
            requestId: result.requestId,
            status: result.status,
            approvedAmount: result.approvedAmount
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('提交预算申请失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/finance/budget/requests
 * @desc 获取预算申请列表
 * @access Private
 */
router.get('/budget/requests', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const status = req.query.status as string;
    const priority = req.query.priority as string;
    
    let requests;
    
    if (status === 'pending') {
      requests = budgetRequestDAO.findPendingRequests();
    } else if (priority === 'high') {
      requests = budgetRequestDAO.findHighPriorityRequests();
    } else if (status) {
      requests = budgetRequestDAO.findByStatus(status);
    } else {
      requests = await financeService.getBudgetRequests(strategyId);
    }
    
    res.json({
      success: true,
      data: requests,
      count: requests.length
    });
  } catch (error) {
    console.error('获取预算申请列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/budget/requests/:id
 * @desc 获取预算申请详情
 * @access Private
 */
router.get('/budget/requests/:id', async (req: Request, res: Response) => {
  try {
    const requestId = Number(req.params.id);
    
    if (isNaN(requestId)) {
      return res.status(400).json({
        success: false,
        error: '无效的申请ID'
      });
    }
    
    const request = budgetRequestDAO.findById(requestId);
    
    if (request) {
      // 解析JSON字段
      const result = {
        ...request,
        metadata: request.metadata ? JSON.parse(String(request.metadata)) : null
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '预算申请不存在'
      });
    }
  } catch (error) {
    console.error('获取预算申请详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/finance/budget/requests/:id/approve
 * @desc 批准预算申请
 * @access Private
 */
router.put('/budget/requests/:id/approve',
  approvalLimit,
  validateRequest(['approvedAmount', 'approvedBy']),
  validateNumericParams(['approvedAmount']),
  async (req: Request, res: Response) => {
    try {
      const requestId = Number(req.params.id);
      const { approvedAmount, approvedBy, notes } = req.body;
      
      if (isNaN(requestId)) {
        return res.status(400).json({
          success: false,
          error: '无效的申请ID'
        });
      }
      
      const result = await financeService.approveBudgetRequest(
        requestId,
        Number(approvedAmount),
        approvedBy,
        notes
      );
      
      if (result.success) {
        res.json({
          success: true,
          message: result.message,
          data: {
            approvedAmount: result.approvedAmount,
            allocationResult: result.allocationResult
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('批准预算申请失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/finance/budget/requests/:id/reject
 * @desc 拒绝预算申请
 * @access Private
 */
router.put('/budget/requests/:id/reject',
  approvalLimit,
  validateRequest(['rejectedBy', 'reason']),
  async (req: Request, res: Response) => {
    try {
      const requestId = Number(req.params.id);
      const { rejectedBy, reason } = req.body;
      
      if (isNaN(requestId)) {
        return res.status(400).json({
          success: false,
          error: '无效的申请ID'
        });
      }
      
      const result = await financeService.rejectBudgetRequest(requestId, rejectedBy, reason);
      
      if (result.success) {
        res.json({
          success: true,
          message: result.message
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('拒绝预算申请失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

// 资金分配路由

/**
 * @route POST /api/finance/allocations
 * @desc 创建资金分配
 * @access Private
 */
router.post('/allocations',
  allocationLimit,
  validateRequest(['strategyId', 'allocationType', 'requestedAmount', 'riskLevel', 'allocatedBy', 'reason']),
  validateNumericParams(['strategyId', 'requestedAmount']),
  async (req: Request, res: Response) => {
    try {
      const request: FundAllocationRequest = {
        strategyId: Number(req.body.strategyId),
        allocationType: req.body.allocationType,
        requestedAmount: Number(req.body.requestedAmount),
        allocationRatio: req.body.allocationRatio ? Number(req.body.allocationRatio) : undefined,
        riskLevel: req.body.riskLevel,
        allocatedBy: req.body.allocatedBy,
        reason: req.body.reason,
        expiresIn: req.body.expiresIn ? Number(req.body.expiresIn) : undefined,
        metadata: req.body.metadata
      };

      const result = await financeService.createFundAllocation(request);
      
      if (result.success) {
        res.status(201).json({
          success: true,
          message: result.message,
          data: {
            allocationId: result.allocationId,
            allocatedAmount: result.allocatedAmount,
            allocationRatio: result.allocationRatio,
            allocationConditions: result.allocationConditions,
            effectiveDate: result.effectiveDate,
            expiryDate: result.expiryDate
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: result.error
        });
      }
    } catch (error) {
      console.error('创建资金分配失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/finance/allocations
 * @desc 获取资金分配列表
 * @access Private
 */
router.get('/allocations', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const status = req.query.status as string;
    
    let allocations;
    
    if (strategyId && status === 'active') {
      allocations = fundAllocationDAO.findActiveAllocationsByStrategy(strategyId);
    } else if (status === 'active') {
      allocations = fundAllocationDAO.findActiveAllocations();
    } else {
      allocations = await financeService.getFundAllocations(strategyId);
    }
    
    res.json({
      success: true,
      data: allocations,
      count: allocations.length
    });
  } catch (error) {
    console.error('获取资金分配列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/allocations/:id
 * @desc 获取资金分配详情
 * @access Private
 */
router.get('/allocations/:id', async (req: Request, res: Response) => {
  try {
    const allocationId = Number(req.params.id);
    
    if (isNaN(allocationId)) {
      return res.status(400).json({
        success: false,
        error: '无效的分配ID'
      });
    }
    
    const allocation = fundAllocationDAO.findById(allocationId);
    
    if (allocation) {
      // 解析JSON字段
      const result = {
        ...allocation,
        metadata: allocation.metadata ? JSON.parse(String(allocation.metadata)) : null
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '资金分配不存在'
      });
    }
  } catch (error) {
    console.error('获取资金分配详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/finance/allocations/:id/usage
 * @desc 更新资金使用情况
 * @access Private
 */
router.put('/allocations/:id/usage',
  validateRequest(['usedAmount']),
  validateNumericParams(['usedAmount']),
  async (req: Request, res: Response) => {
    try {
      const allocationId = Number(req.params.id);
      const { usedAmount, reservedAmount } = req.body;
      
      if (isNaN(allocationId)) {
        return res.status(400).json({
          success: false,
          error: '无效的分配ID'
        });
      }
      
      const success = fundAllocationDAO.updateFundUsage(
        allocationId,
        Number(usedAmount),
        reservedAmount ? Number(reservedAmount) : undefined
      );
      
      if (success) {
        res.json({
          success: true,
          message: '资金使用情况更新成功'
        });
      } else {
        res.status(404).json({
          success: false,
          error: '资金分配不存在或更新失败'
        });
      }
    } catch (error) {
      console.error('更新资金使用情况失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/finance/allocations/:id/freeze
 * @desc 冻结资金分配
 * @access Private
 */
router.put('/allocations/:id/freeze',
  validateRequest(['reason']),
  async (req: Request, res: Response) => {
    try {
      const allocationId = Number(req.params.id);
      const { reason } = req.body;
      
      if (isNaN(allocationId)) {
        return res.status(400).json({
          success: false,
          error: '无效的分配ID'
        });
      }
      
      const success = fundAllocationDAO.freezeAllocation(allocationId, reason);
      
      if (success) {
        res.json({
          success: true,
          message: '资金分配已冻结'
        });
      } else {
        res.status(404).json({
          success: false,
          error: '资金分配不存在或冻结失败'
        });
      }
    } catch (error) {
      console.error('冻结资金分配失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/finance/allocations/:id/unfreeze
 * @desc 解冻资金分配
 * @access Private
 */
router.put('/allocations/:id/unfreeze', async (req: Request, res: Response) => {
  try {
    const allocationId = Number(req.params.id);
    
    if (isNaN(allocationId)) {
      return res.status(400).json({
        success: false,
        error: '无效的分配ID'
      });
    }
    
    const success = fundAllocationDAO.unfreezeAllocation(allocationId);
    
    if (success) {
      res.json({
        success: true,
        message: '资金分配已解冻'
      });
    } else {
      res.status(404).json({
        success: false,
        error: '资金分配不存在或解冻失败'
      });
    }
  } catch (error) {
    console.error('解冻资金分配失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 账户管理路由

/**
 * @route POST /api/finance/accounts
 * @desc 创建账户
 * @access Private
 */
router.post('/accounts',
  validateRequest(['accountType', 'accountName', 'initialBalance', 'createdBy']),
  validateNumericParams(['initialBalance']),
  async (req: Request, res: Response) => {
    try {
      const accountData = {
        account_type: req.body.accountType,
        account_name: req.body.accountName,
        account_number: req.body.accountNumber || `ACC_${Date.now()}`,
        balance: Number(req.body.initialBalance),
        available_balance: Number(req.body.initialBalance),
        currency: req.body.currency || 'USD',
        risk_level: req.body.riskLevel || 'medium',
        daily_limit: req.body.dailyLimit || 0,
        monthly_limit: req.body.monthlyLimit || 0,
        created_by: req.body.createdBy,
        metadata: req.body.metadata ? JSON.stringify(req.body.metadata) : null
      };

      const result = accountDAO.create(accountData);
      const accountId = result.success ? (result as unknown as Record<string, unknown>).id : null;
      
      if (accountId) {
        res.status(201).json({
          success: true,
          message: '账户创建成功',
          data: {
            accountId,
            accountNumber: accountData.account_number
          }
        });
      } else {
        res.status(400).json({
          success: false,
          error: '账户创建失败'
        });
      }
    } catch (error) {
      console.error('创建账户失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route GET /api/finance/accounts
 * @desc 获取账户列表
 * @access Private
 */
router.get('/accounts', async (req: Request, res: Response) => {
  try {
    const accountType = req.query.accountType as string;
    const status = req.query.status as string;
    const lowBalance = req.query.lowBalance === 'true';
    
    let accounts;
    
    if (lowBalance) {
      const threshold = req.query.threshold ? Number(req.query.threshold) : 1000;
      accounts = accountDAO.findLowBalanceAccounts(threshold);
    } else if (status === 'active') {
      accounts = accountDAO.findActiveAccounts();
    } else if (accountType) {
      accounts = accountDAO.findByAccountType(accountType);
    } else {
      accounts = accountDAO.findAll();
    }
    
    res.json({
      success: true,
      data: accounts,
      count: accounts.length
    });
  } catch (error) {
    console.error('获取账户列表失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/account-status
 * @desc 获取账户状态概览
 * @access Private
 */
router.get('/account-status', async (req: Request, res: Response) => {
  try {
    // 获取账户状态概览
    // 获取账户状态概览 - 暂时返回模拟数据
    const statusResult = {
      success: true,
      totalBalance: 1000000,
      availableBalance: 800000,
      allocatedFunds: 150000,
      frozenFunds: 50000,
      totalPnL: 25000,
      dailyPnL: 1500,
      accountHealth: 'good',
      riskExposure: 0.15,
      utilizationRate: 0.2
    };
    
    if (statusResult.success) {
      res.json({
        success: true,
        data: {
          totalBalance: statusResult.totalBalance,
          availableBalance: statusResult.availableBalance,
          allocatedFunds: statusResult.allocatedFunds,
          frozenFunds: statusResult.frozenFunds,
          totalPnL: statusResult.totalPnL,
          dailyPnL: statusResult.dailyPnL,
          accountHealth: statusResult.accountHealth,
          riskExposure: statusResult.riskExposure,
          utilizationRate: statusResult.utilizationRate
        }
      });
    } else {
      res.status(400).json({
        success: false,
        error: '获取账户状态失败'
      });
    }
  } catch (error) {
    console.error('获取账户状态失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/accounts/:id
 * @desc 获取账户详情
 * @access Private
 */
router.get('/accounts/:id', async (req: Request, res: Response) => {
  try {
    const accountId = Number(req.params.id);
    
    if (isNaN(accountId)) {
      return res.status(400).json({
        success: false,
        error: '无效的账户ID'
      });
    }
    
    const account = accountDAO.findById(accountId);
    
    if (account) {
      // 解析JSON字段
      const result = {
        ...account,
        metadata: account.metadata ? JSON.parse(String(account.metadata)) : null
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '账户不存在'
      });
    }
  } catch (error) {
    console.error('获取账户详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route PUT /api/finance/accounts/:id/balance
 * @desc 更新账户余额
 * @access Private
 */
router.put('/accounts/:id/balance',
  validateRequest(['newBalance']),
  validateNumericParams(['newBalance']),
  async (req: Request, res: Response) => {
    try {
      const accountId = Number(req.params.id);
      const { newBalance, frozenAmount } = req.body;
      
      if (isNaN(accountId)) {
        return res.status(400).json({
          success: false,
          error: '无效的账户ID'
        });
      }
      
      const success = accountDAO.updateBalance(
        accountId,
        Number(newBalance),
        frozenAmount ? Number(frozenAmount) : undefined
      );
      
      if (success) {
        res.json({
          success: true,
          message: '账户余额更新成功'
        });
      } else {
        res.status(404).json({
          success: false,
          error: '账户不存在或更新失败'
        });
      }
    } catch (error) {
      console.error('更新账户余额失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/finance/accounts/:id/freeze
 * @desc 冻结账户资金
 * @access Private
 */
router.put('/accounts/:id/freeze',
  validateRequest(['amount']),
  validateNumericParams(['amount']),
  async (req: Request, res: Response) => {
    try {
      const accountId = Number(req.params.id);
      const { amount } = req.body;
      
      if (isNaN(accountId)) {
        return res.status(400).json({
          success: false,
          error: '无效的账户ID'
        });
      }
      
      const success = accountDAO.freezeFunds(accountId, Number(amount));
      
      if (success) {
        res.json({
          success: true,
          message: '资金冻结成功'
        });
      } else {
        res.status(400).json({
          success: false,
          error: '账户不存在或可用余额不足'
        });
      }
    } catch (error) {
      console.error('冻结账户资金失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

/**
 * @route PUT /api/finance/accounts/:id/unfreeze
 * @desc 解冻账户资金
 * @access Private
 */
router.put('/accounts/:id/unfreeze',
  validateRequest(['amount']),
  validateNumericParams(['amount']),
  async (req: Request, res: Response) => {
    try {
      const accountId = Number(req.params.id);
      const { amount } = req.body;
      
      if (isNaN(accountId)) {
        return res.status(400).json({
          success: false,
          error: '无效的账户ID'
        });
      }
      
      const success = accountDAO.unfreezeFunds(accountId, Number(amount));
      
      if (success) {
        res.json({
          success: true,
          message: '资金解冻成功'
        });
      } else {
        res.status(400).json({
          success: false,
          error: '账户不存在或冻结余额不足'
        });
      }
    } catch (error) {
      console.error('解冻账户资金失败:', error);
      res.status(500).json({
        success: false,
        error: '服务器内部错误'
      });
    }
  }
);

// 财务交易路由

/**
 * @route GET /api/finance/transactions
 * @desc 获取财务交易记录
 * @access Private
 */
router.get('/transactions', async (req: Request, res: Response) => {
  try {
    const strategyId = req.query.strategyId ? Number(req.query.strategyId) : undefined;
    const accountId = req.query.accountId ? Number(req.query.accountId) : undefined;
    const transactionType = req.query.transactionType as string;
    const status = req.query.status as string;
    
    let transactions;
    
    if (status === 'pending') {
      transactions = financialTransactionDAO.findPendingTransactions();
    } else if (transactionType) {
      transactions = financialTransactionDAO.findByTransactionType(transactionType);
    } else if (accountId) {
      transactions = financialTransactionDAO.findByAccountId(accountId);
    } else if (strategyId) {
      transactions = financialTransactionDAO.findByStrategyId(strategyId);
    } else {
      transactions = financialTransactionDAO.findAll();
    }
    
    res.json({
      success: true,
      data: transactions,
      count: transactions.length
    });
  } catch (error) {
    console.error('获取财务交易记录失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/transactions/:id
 * @desc 获取财务交易详情
 * @access Private
 */
router.get('/transactions/:id', async (req: Request, res: Response) => {
  try {
    const transactionId = Number(req.params.id);
    
    if (isNaN(transactionId)) {
      return res.status(400).json({
        success: false,
        error: '无效的交易ID'
      });
    }
    
    const transaction = financialTransactionDAO.findById(transactionId);
    
    if (transaction) {
      // 解析JSON字段
      const result = {
        ...transaction,
        metadata: transaction.metadata ? JSON.parse(String(transaction.metadata)) : null
      };
      
      res.json({
        success: true,
        data: result
      });
    } else {
      res.status(404).json({
        success: false,
        error: '财务交易不存在'
      });
    }
  } catch (error) {
    console.error('获取财务交易详情失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 统计和分析路由

/**
 * @route GET /api/finance/stats/overview
 * @desc 获取财务模组概览统计
 * @access Private
 */
router.get('/stats/overview', async (req: Request, res: Response) => {
  try {
    const stats = await financeService.getFinancialStatistics();
    
    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    console.error('获取财务概览统计失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/stats/dashboard
 * @desc 获取财务仪表板数据
 * @access Private
 */
router.get('/stats/dashboard', async (req: Request, res: Response) => {
  try {
    // 获取待审批预算申请
    const pendingBudgets = budgetRequestDAO.findPendingRequests();
    const highPriorityBudgets = budgetRequestDAO.findHighPriorityRequests();
    
    // 获取活跃资金分配
    const activeAllocations = fundAllocationDAO.findActiveAllocations();
    const allocationStats = fundAllocationDAO.getTotalAllocationStats();
    
    // 获取账户健康状态
    const accountHealth = await financeService.performAccountHealthCheck();
    
    // 获取低余额账户
    const lowBalanceAccounts = accountDAO.findLowBalanceAccounts(1000);
    
    // 获取待处理交易
    const pendingTransactions = financialTransactionDAO.findPendingTransactions();
    
    // 获取统计数据
    const budgetStats = budgetRequestDAO.getBudgetRequestStats();
    const accountStats = accountDAO.getAccountStats();
    const transactionStats = financialTransactionDAO.getTransactionStats(7);
    
    res.json({
      success: true,
      data: {
        budget: {
          pending: pendingBudgets.length,
          highPriority: highPriorityBudgets.length,
          recentRequests: pendingBudgets.slice(0, 10),
          stats: budgetStats
        },
        allocation: {
          active: activeAllocations.length,
          totalStats: allocationStats,
          utilizationRanking: fundAllocationDAO.getFundUtilizationRanking(5)
        },
        accounts: {
          health: accountHealth,
          lowBalance: lowBalanceAccounts.length,
          lowBalanceAccounts: lowBalanceAccounts.slice(0, 5),
          stats: accountStats
        },
        transactions: {
          pending: pendingTransactions.length,
          recentTransactions: pendingTransactions.slice(0, 10),
          stats: transactionStats
        },
        lastUpdate: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('获取财务仪表板数据失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

/**
 * @route GET /api/finance/stats/strategy/:strategyId
 * @desc 获取策略财务摘要
 * @access Private
 */
router.get('/stats/strategy/:strategyId', async (req: Request, res: Response) => {
  try {
    const strategyId = Number(req.params.strategyId);
    
    if (isNaN(strategyId)) {
      return res.status(400).json({
        success: false,
        error: '无效的策略ID'
      });
    }
    
    const budgetUsage = budgetRequestDAO.getStrategyBudgetUsage(strategyId);
    const allocationStats = fundAllocationDAO.getStrategyAllocationStats(strategyId);
    const financialSummary = financialTransactionDAO.getStrategyFinancialSummary(strategyId);
    
    res.json({
      success: true,
      data: {
        strategyId,
        budget: budgetUsage,
        allocation: allocationStats,
        financial: financialSummary,
        lastUpdate: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('获取策略财务摘要失败:', error);
    res.status(500).json({
      success: false,
      error: '服务器内部错误'
    });
  }
});

// 健康检查路由

/**
 * @route GET /api/finance/health
 * @desc 财务模组健康检查
 * @access Public
 */
router.get('/health', async (req: Request, res: Response) => {
  try {
    // 检查数据库连接
    const budgets = await financeService.getBudgetRequests();
    const allocations = await financeService.getFundAllocations();
    
    // 检查缓存连接
    const cacheStatus = await redisCache.ping();
    
    // 执行账户健康检查
    const accountHealth = await financeService.performAccountHealthCheck();
    
    res.json({
      success: true,
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'connected',
        cache: cacheStatus ? 'connected' : 'disconnected',
        budgetRequestsCount: budgets.length,
        allocationsCount: allocations.length,
        accountHealth: {
          totalAccounts: (accountHealth as any).totalAccounts,
          healthyAccounts: (accountHealth as any).healthyAccounts,
          issuesFound: (accountHealth as any).issuesFound
        }
      }
    });
  } catch (error) {
    console.error('健康检查失败:', error);
    res.status(503).json({
      success: false,
      status: 'unhealthy',
      error: error instanceof Error ? error.message : '未知错误',
      timestamp: new Date().toISOString()
    });
  }
});

export default router;
export { router as financeRoutes };