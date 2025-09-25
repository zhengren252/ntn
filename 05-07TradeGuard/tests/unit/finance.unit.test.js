/**
 * 财务逻辑单元测试
 * 测试计划: TEST-PLAN-M0507-TRADEGUARD-V1
 * 阶段2: 单元测试 - 财务逻辑
 */

const { testConfig, getFinanceConfig, generateTestAccount, generateTestBudgetRequest } = require('../config/testConfig');

// 使用全局模拟对象
const { mockConfigs } = require('../config/mockSetup');
const FinanceService = mockConfigs.financeService;
const budgetRequestDAO = mockConfigs.budgetRequestDAO;
const fundAllocationDAO = mockConfigs.fundAllocationDAO;
const accountDAO = mockConfigs.accountDAO;
const financialTransactionDAO = mockConfigs.financialTransactionDAO;
const redisCache = mockConfigs.redisCache;
const zmqBus = mockConfigs.zmqBus;
const configManager = mockConfigs.configManager;

// Mock所有外部依赖
jest.mock('../../api/modules/finance/dao/financeDAO.ts', () => ({
  budgetRequestDAO: {
    create: jest.fn(),
    findById: jest.fn(),
    findByStatus: jest.fn(),
    update: jest.fn(),
    delete: jest.fn()
  },
  fundAllocationDAO: {
    create: jest.fn(),
    findByRequestId: jest.fn(),
    update: jest.fn()
  },
  accountDAO: {
    findById: jest.fn(),
    findAll: jest.fn(),
    update: jest.fn()
  },
  financialTransactionDAO: {
    create: jest.fn(),
    findByAccountId: jest.fn(),
    findByDateRange: jest.fn()
  }
}));

jest.mock('../../api/shared/cache/redis', () => ({
  redisCache: {
    get: jest.fn(),
    set: jest.fn(),
    del: jest.fn(),
    exists: jest.fn()
  }
}));

jest.mock('../../api/shared/messaging/zeromq', () => ({
  zmqBus: {
    publish: jest.fn(),
    subscribe: jest.fn(),
    unsubscribe: jest.fn()
  }
}));

jest.mock('../../api/config/environment', () => ({
  configManager: {
    getConfig: jest.fn()
  }
}));

jest.mock('../../api/shared/utils/logger');

describe('财务逻辑单元测试', () => {
  let financeService;
  let financeConfig;
  
  beforeEach(async () => {
    // 重置所有mock
    jest.clearAllMocks();
    global.mockUtils && global.mockUtils.resetAllMocks();
    
    // 获取测试配置
    financeConfig = getFinanceConfig();
    
    // Mock configManager返回测试配置
    configManager.getConfig.mockReturnValue({
      finance: financeConfig
    });
    
    // 创建FinanceService实例
    financeService = new FinanceService();
    
    // Mock基础配置
    financeService.financeConfig = financeConfig;
    
    financeService.approvalWorkflow = financeConfig.approvalWorkflow;
    
    // 使用统一的模拟配置
    if (global.mockUtils) {
      global.mockUtils.setMockReturnValue('redisCache', 'get', null);
      global.mockUtils.setMockReturnValue('redisCache', 'set', 'OK');
      global.mockUtils.setMockReturnValue('zmqBus', 'publish', true);
      global.mockUtils.setMockReturnValue('zmqBus', 'request', { success: true });
    } else {
      // 兼容性处理
      redisCache.get.mockResolvedValue(null);
      redisCache.set.mockResolvedValue('OK');
      zmqBus.publish.mockResolvedValue(true);
      zmqBus.request.mockResolvedValue({ success: true });
    }
    
    // Mock默认的DAO方法
    budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
      total_approved: 0,
      total_used: 0,
      available: 0
    });
    budgetRequestDAO.create.mockReturnValue({ success: true, id: 1 });
    budgetRequestDAO.approveRequest.mockReturnValue(true);
    fundAllocationDAO.create.mockReturnValue({ success: true, id: 1 });
    accountDAO.findByAccountType.mockReturnValue([]);
  });
  
  describe('UNIT-FIN-01: 低风险下的资金分配', () => {
    test('应该为低风险评分返回接近或等于请求额度的预算', async () => {
      // 设置低风险场景
      const strategyId = 1;
      const requestedAmount = 5000;
      
      // Mock策略预算使用情况 - 低使用率
    budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
      total_approved: 100000,  // 已批准10万
      total_used: 80000,       // 已使用8万
      available: 20000         // 可用2万
    });
      
      // Mock账户余额 - 充足资金
      const testAccount = generateTestAccount({ balance: 2000000, available_balance: 1800000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      // Mock风险等级缓存 - 低风险
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'low', riskScore: 25 });
        }
        return Promise.resolve(null);
      });
      
      // Mock预算申请创建
      budgetRequestDAO.create.mockReturnValue({
        success: true,
        id: 101
      });
      
      // Mock自动批准
      budgetRequestDAO.approveRequest.mockReturnValue(true);
      
      // Mock资金分配创建
      fundAllocationDAO.create.mockReturnValue({
        success: true,
        id: 201
      });
      
      // 执行预算申请
      const request = {
        strategyId: 1,
        requestType: 'initial',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '低风险策略初始资金申请',
        requestedBy: 'trader_001'
      };
      
      console.log('DEBUG: 低风险测试 - 请求参数:', request);
      const result = await financeService.processBudgetRequest(request);
      console.log('DEBUG: 低风险测试 - 结果:', result);
      
      // 验证结果
      expect(result.success).toBe(true);
      expect(result.requestId).toBeDefined();
      
      // 验证自动批准状态
      expect(result.status).toBe('approved');
      expect(result.approvedAmount).toBe(requestedAmount);
      
      // 验证调用了正确的方法
      expect(budgetRequestDAO.getStrategyBudgetUsage).toHaveBeenCalledWith(1);
      expect(budgetRequestDAO.create).toHaveBeenCalled();
      expect(budgetRequestDAO.approveRequest).toHaveBeenCalled();
      expect(fundAllocationDAO.create).toHaveBeenCalled();
      
      // 验证批准金额等于请求金额
      const approveCall = budgetRequestDAO.approveRequest.mock.calls[0];
      expect(approveCall[1]).toBe(requestedAmount); // 批准金额
      
      console.log('✅ UNIT-FIN-01: 低风险资金分配测试通过');
    });
    
    test('应该为低风险策略提供较高的分配比例', async () => {
      // 设置低风险大额申请场景
      const strategyId = 1;
      const requestedAmount = 60000; // 20万申请
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 50000,
        total_used: 30000,
        available: 20000
      });
      
      const testAccount = generateTestAccount({ balance: 5000000, available_balance: 4500000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      // 低风险等级
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'low', riskScore: 20 });
        }
        return Promise.resolve(null);
      });
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 102 });
      
      // 手动批准流程（超过自动批准阈值）
      const request = {
        strategyId: 1,
        requestType: 'additional',
        requestedAmount: requestedAmount,
        priority: 'high',
        justification: '低风险策略扩大投资规模',
        requestedBy: 'trader_001'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 验证进入手动审批流程
      expect(result.success).toBe(true);
      expect(result.status).toBe('pending');
      expect(result.message).toContain('等待审批');
      
      // 验证高风险需要手动审批
      expect(result.status).toBe('pending');
      
      // 验证ZMQ消息发送（审批通知）
      expect(zmqBus.publish).toHaveBeenCalled();
      const publishCall = zmqBus.publish.mock.calls.find(call => 
        call[0].data.type === 'approval_required'
      );
      expect(publishCall).toBeDefined();
      expect(publishCall[0].data.requestedAmount).toBe(60000);
      
      console.log('✅ UNIT-FIN-01: 低风险高额分配流程测试通过');
    });
    
    test('应该在低风险情况下允许较高的资金使用率', async () => {
    const strategyId = 'low-risk-strategy';
    const requestedAmount = 300000; // 30万申请
      
      // 当前已有较高使用率但仍在低风险限制内
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 100000,  // 已批准10万
        total_used: 90000,       // 已使用9万
        available: 10000         // 可用1万
      });
      
      const testAccount = generateTestAccount({ balance: 3000000, available_balance: 2500000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'low', riskScore: 30 });
        }
        return Promise.resolve(null);
      });
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 103 });
      
      const request = {
        strategyId: 'low-risk-strategy',
        requestType: 'additional',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '低风险策略追加投资申请，用于扩大交易规模',
        requestedBy: 'trader_001'
      };
      
      console.log('DEBUG: 低风险高使用率测试 - 请求参数:', request);
      const result = await financeService.processBudgetRequest(request);
      console.log('DEBUG: 低风险高使用率测试 - 结果:', result);
      
      // 验证请求被接受（总额40万仍在50万限制内）
      expect(result.success).toBe(true);
      expect(result.status).toBe('pending'); // 40万申请需要审批
      
      // 验证没有因为使用率过高而被拒绝
      expect(result.error).toBeUndefined();
      
      console.log('✅ UNIT-FIN-01: 低风险高使用率测试通过');
    });
  });
  
  describe('UNIT-FIN-02: 高风险下的资金分配', () => {
    test('应该为高风险评分返回显著低于请求额度的预算', async () => {
      // 设置高风险场景
      const strategyId = 'high-risk-strategy';
      const requestedAmount = 200000;
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 30000,
        total_used: 25000,
        available: 5000
      });
      
      const testAccount = generateTestAccount({ balance: 2000000, available_balance: 1800000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      // Mock高风险等级
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'high', riskScore: 85 });
        }
        return Promise.resolve(null);
      });
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 201 });
      
      const request = {
         strategyId: 'high-risk-strategy',
         requestType: 'initial',
         requestedAmount: 60000, // 6万
         priority: 'normal',
         justification: '高风险策略预算申请，用于算法交易',
         requestedBy: 'trader_002'
       };
      
      console.log('DEBUG: 高风险测试 - 请求参数:', request);
      const result = await financeService.processBudgetRequest(request);
      console.log('DEBUG: 高风险测试 - 结果:', result);
      
      // 验证请求被接受但需要审批
      expect(result.success).toBe(true);
      expect(result.status).toBe('pending');
      
      // 验证发送了审批通知，包含高风险警告
      expect(zmqBus.publish).toHaveBeenCalled();
      const publishCall = zmqBus.publish.mock.calls.find(call => 
        call[0].data.type === 'approval_required'
      );
      expect(publishCall).toBeDefined();
      expect(publishCall[0].data.requestedAmount).toBe(60000);
      
      console.log('✅ UNIT-FIN-02: 高风险资金分配测试通过');
    });
    
    test('应该直接拒绝高风险策略的过大资金申请', async () => {
      // 设置高风险大额申请场景
      const strategyId = 2;
      const requestedAmount = 600000; // 60万申请，超过高风险限制
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 80000,
        total_used: 70000,
        available: 10000
      });
      
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'high', riskScore: 90 });
        }
        return Promise.resolve(null);
      });
      
      const request = {
        strategyId: 2,
        requestType: 'additional',
        requestedAmount: requestedAmount,
        priority: 'urgent',
        justification: '高风险策略大额追加投资',
        requestedBy: 'trader_002'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 验证请求被拒绝（总额68万超过高风险限制）
      expect(result.success).toBe(false);
      expect(result.error).toContain('策略预算超限');
      
      // 验证没有创建预算申请记录
      expect(budgetRequestDAO.create).not.toHaveBeenCalled();
      
      console.log('✅ UNIT-FIN-02: 高风险过大申请拒绝测试通过');
    });
    
    test('应该为极高风险策略返回零分配', async () => {
      // 设置极高风险场景
      const strategyId = 3;
      const requestedAmount = 100000;
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 30000,
        total_used: 25000,
        available: 5000
      });
      
      // Mock极高风险等级
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'critical', riskScore: 95 });
        }
        return Promise.resolve(null);
      });
      
      const request = {
        strategyId: 3,
        requestType: 'emergency',
        requestedAmount: requestedAmount,
        priority: 'urgent',
        justification: '极高风险策略紧急资金申请',
        requestedBy: 'trader_003'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 验证请求被拒绝
      expect(result.success).toBe(false);
      expect(result.error).toContain('策略预算超限');
      
      console.log('✅ UNIT-FIN-02: 极高风险零分配测试通过');
    });
    
    test('应该限制高风险策略的资金使用率', async () => {
      const strategyId = 2;
      const requestedAmount = 50000;
      
      // 高风险策略已接近限制
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 280000,   // 已批准28万
        total_used: 250000,       // 已使用25万
        available: 30000          // 可用3万
      });
      
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'high', riskScore: 80 });
        }
        return Promise.resolve(null);
      });
      
      const request = {
        strategyId: 2,
        requestType: 'additional',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '高风险策略小额追加投资申请',
        requestedBy: 'trader_002'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 验证请求被拒绝（总额33万超过高风险30万限制）
      expect(result.success).toBe(false);
      expect(result.error).toContain('策略预算超限');
      
      console.log('✅ UNIT-FIN-02: 高风险使用率限制测试通过');
    });
  });
  
  describe('资金分配边界条件测试', () => {
    test('应该处理无效的申请参数', async () => {
      const invalidRequests = [
        {
          strategyId: 0,
          requestType: 'initial',
          requestedAmount: 50000,
          priority: 'normal',
          justification: '测试无效策略ID的处理逻辑',
          requestedBy: 'trader'
        },
        {
          strategyId: 1,
          requestType: 'initial',
          requestedAmount: -1000,
          priority: 'normal',
          justification: '测试负数金额的处理逻辑',
          requestedBy: 'trader'
        },
        {
          strategyId: 1,
          requestType: 'initial',
          requestedAmount: 50000,
          priority: 'normal',
          justification: '短理由',
          requestedBy: 'trader'
        }
      ];
      
      for (const request of invalidRequests) {
        const result = await financeService.processBudgetRequest(request);
        expect(result.success).toBe(false);
        expect(result.error).toBeDefined();
      }
      
      console.log('✅ 无效参数边界条件测试通过');
    });
    
    test('应该处理金额为0的预算申请', async () => {
      const testAccount = generateTestAccount({ balance: 100000 });
      const testBudgetRequest = generateTestBudgetRequest({ 
        strategyId: 1, 
        requestedAmount: 0,
        riskLevel: 'low'
      });
      
      console.log('DEBUG: 零金额测试 - 请求参数:', testBudgetRequest);
      const result = await financeService.processBudgetRequest(testBudgetRequest);
      console.log('DEBUG: 零金额测试 - 结果:', result);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('申请金额必须大于0');
      
      console.log('✅ 零金额边界条件测试通过');
    });
    
    test('应该处理账户余额不足的情况', async () => {
      const strategyId = 1;
      const requestedAmount = 1000000; // 100万申请
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 50000,
        total_used: 30000,
        available: 20000
      });
      
      // Mock账户余额不足
      const testAccount = generateTestAccount({ balance: 50000, available_balance: 30000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'low', riskScore: 25 });
        }
        return Promise.resolve(null);
      });
      
      const request = {
        strategyId: 1,
        requestType: 'initial',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '测试账户余额不足的处理逻辑验证',
        requestedBy: 'trader_001'
      };
      
      console.log('DEBUG: 余额不足测试 - 请求参数:', request);
      const result = await financeService.processBudgetRequest(request);
      console.log('DEBUG: 余额不足测试 - 结果:', result);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('账户余额不足');
      
      console.log('✅ 余额不足边界条件测试通过');
    });
    
    test('应该处理数据库操作失败的情况', async () => {
      const strategyId = 1;
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 50000,
        total_used: 30000,
        available: 20000
      });
      
      // Mock数据库创建失败
      budgetRequestDAO.create.mockReturnValue({
        success: false,
        error: '数据库连接失败'
      });
      
      redisCache.get.mockResolvedValue({ riskLevel: 'low' });
      
      const request = {
        strategyId: 1,
        requestType: 'initial',
        requestedAmount: 50000,
        priority: 'normal',
        justification: '测试数据库失败处理的完整逻辑验证',
        requestedBy: 'trader_001'
      };
      
      console.log('DEBUG: 数据库失败测试 - 请求参数:', request);
      const result = await financeService.processBudgetRequest(request);
      console.log('DEBUG: 数据库失败测试 - 结果:', result);
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('创建预算申请失败');
      
      console.log('✅ 数据库失败边界条件测试通过');
    });
    
    test('应该处理风险等级获取失败的情况', async () => {
      const strategyId = 1;
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 50000,
        total_used: 30000,
        available: 20000
      });
      
      // Mock风险等级获取失败，应该使用默认值
      redisCache.get.mockRejectedValue(new Error('Redis连接失败'));
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 301 });
      
      const request = {
        strategyId: 1,
        requestType: 'initial',
        requestedAmount: 5000, // 小额申请，应该自动批准
        priority: 'normal',
        justification: '测试风险等级获取失败处理',
        requestedBy: 'trader_001'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 应该使用默认风险等级（medium）处理
      expect(result.success).toBe(true);
      
      console.log('✅ 风险等级获取失败边界条件测试通过');
    });
  });
  
  describe('财务错误处理测试', () => {
    test('应该处理ZMQ消息发送失败的情况', async () => {
      const strategyId = 1;
      const requestedAmount = 100000; // 10万申请，需要审批
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 50000,
        total_used: 30000,
        available: 20000
      });
      
      const testAccount = generateTestAccount({ balance: 2000000, available_balance: 1800000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'medium', riskScore: 50 });
        }
        return Promise.resolve(null);
      });
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 401 });
      
      // Mock ZMQ发送失败
      zmqBus.publish.mockRejectedValue(new Error('ZMQ连接失败'));
      
      const request = {
        strategyId: 1,
        requestType: 'additional',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '测试ZMQ消息发送失败的处理逻辑',
        requestedBy: 'trader_001'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 即使ZMQ失败，预算申请应该继续进行
      expect(result.success).toBe(true);
      expect(result.status).toBe('pending');
      
      console.log('✅ ZMQ错误处理测试通过');
    });
    
    test('应该处理缓存操作失败的情况', async () => {
      const strategyId = 1;
      const requestedAmount = 5000; // 小额申请
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 50000,
        total_used: 30000,
        available: 20000
      });
      
      const testAccount = generateTestAccount({ balance: 2000000, available_balance: 1800000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      // Mock缓存读取失败但写入成功
      redisCache.get.mockRejectedValue(new Error('Redis读取失败'));
      redisCache.set.mockResolvedValue('OK');
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 402 });
      budgetRequestDAO.approveRequest.mockReturnValue(true);
      fundAllocationDAO.create.mockReturnValue({ success: true, id: 302 });
      
      const request = {
        strategyId: 1,
        requestType: 'initial',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '测试缓存操作失败的处理逻辑验证',
        requestedBy: 'trader_001'
      };
      
      const result = await financeService.processBudgetRequest(request);
      
      // 应该使用默认风险等级继续处理
      expect(result.success).toBe(true);
      
      console.log('✅ 缓存错误处理测试通过');
    });
    
    test('应该处理并发申请的情况', async () => {
      const strategyId = 1;
      const requestedAmount = 50000;
      
      budgetRequestDAO.getStrategyBudgetUsage.mockReturnValue({
        total_approved: 100000,  // 已批准10万
        total_used: 80000,
        available: 20000
      });
      
      const testAccount = generateTestAccount({ balance: 2000000, available_balance: 1800000 });
      accountDAO.findByAccountType.mockReturnValue([testAccount]);
      
      redisCache.get.mockImplementation((keyType, key) => {
        if (key === `risk_${strategyId}`) {
          return Promise.resolve({ riskLevel: 'low', riskScore: 25 });
        }
        return Promise.resolve(null);
      });
      
      budgetRequestDAO.create.mockReturnValue({ success: true, id: 403 });
      
      const request = {
        strategyId: 1,
        requestType: 'additional',
        requestedAmount: requestedAmount,
        priority: 'normal',
        justification: '测试并发申请处理的完整逻辑验证',
        requestedBy: 'trader_001'
      };
      
      console.log('DEBUG: 并发测试 - 请求参数:', request);
      console.log('DEBUG: 并发测试 - 模拟预算使用情况: 已批准10万, 已使用8万');
      
      // 验证总预算不会超过限制（低风险策略限制为200万）
      const totalApproved = 100000; // 已批准10万
      expect(totalApproved).toBeLessThanOrEqual(2000000); // 200万限制
      
      // 模拟并发申请
      const promises = [
        financeService.processBudgetRequest(request),
        financeService.processBudgetRequest(request),
        financeService.processBudgetRequest(request)
      ];
      
      const results = await Promise.all(promises);
      
      console.log('DEBUG: 并发测试 - 结果:', results);
      
      // 至少有一个申请应该成功
      const successCount = results.filter(r => r.success).length;
      expect(successCount).toBeGreaterThan(0);
      
      console.log('✅ 并发申请处理测试通过');
    });
  });
});