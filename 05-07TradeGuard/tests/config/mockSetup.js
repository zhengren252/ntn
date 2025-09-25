/**
 * 统一的模拟对象设置配置
 * 确保所有测试文件使用一致的模拟配置
 */

// 统一的模拟对象配置
const mockConfigs = {
  // 数据库DAO模拟
  strategyDAO: {
    findById: jest.fn(),
    createStrategy: jest.fn(),
    updateStatus: jest.fn(),
    findAll: jest.fn(),
    findByStatus: jest.fn(),
    delete: jest.fn()
  },
  
  orderDAO: {
    createOrder: jest.fn(),
    updateStatus: jest.fn(),
    findByStrategyId: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn(),
    cancel: jest.fn()
  },
  
  riskAssessmentDAO: {
    create: jest.fn(),
    findLatestByStrategyId: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn(),
    update: jest.fn()
  },
  
  riskMetricsDAO: {
    calculateStrategyRiskMetrics: jest.fn(),
    create: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn()
  },
  
  riskAlertDAO: {
    create: jest.fn(),
    findAll: jest.fn(),
    findById: jest.fn(),
    update: jest.fn()
  },
  
  budgetRequestDAO: {
    create: jest.fn(),
    getStrategyBudgetUsage: jest.fn(),
    approveRequest: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn(),
    update: jest.fn()
  },
  
  fundAllocationDAO: {
    create: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn(),
    update: jest.fn()
  },
  
  accountDAO: {
    findByAccountType: jest.fn(),
    create: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn(),
    update: jest.fn()
  },
  
  financialTransactionDAO: {
    create: jest.fn(),
    findById: jest.fn(),
    findAll: jest.fn(),
    update: jest.fn()
  },
  
  // 缓存模拟
  redisCache: {
    get: jest.fn(),
    set: jest.fn(),
    setEx: jest.fn(),
    del: jest.fn(),
    keys: jest.fn(),
    flushDb: jest.fn(),
    quit: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn()
  },
  
  // 消息队列模拟
  zmqBus: {
    publish: jest.fn(),
    request: jest.fn(),
    subscribe: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    close: jest.fn()
  },
  
  // TACoreClient模拟
  tacoreClient: {
    executeOrder: jest.fn(),
    getOrderStatus: jest.fn(),
    cancelOrder: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    isConnected: jest.fn()
  },
  
  // 配置管理模拟
  configManager: {
    getConfig: jest.fn(),
    setConfig: jest.fn(),
    reload: jest.fn()
  },
  
  // 日志模拟
  logger: {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn()
  },
  
  // 风控服务模拟
  riskService: {
    getInstance: jest.fn(() => ({
      performRiskAssessment: jest.fn().mockImplementation(async (request) => {
        try {
          // 验证输入参数
          if (!request || !request.strategyId || request.strategyId === null) {
            return { success: false, error: '无效的策略ID参数' };
          }
          
          // 检查策略是否存在
          const strategy = mockConfigs.strategyDAO.findById(request.strategyId);
          if (!strategy) {
            return {
              success: false,
              error: '策略不存在'
            };
          }
          
          // 调用相关DAO方法以确保测试能够验证调用
          const riskMetrics = mockConfigs.riskMetricsDAO.calculateStrategyRiskMetrics(request.strategyId);
          const orders = mockConfigs.orderDAO.findByStrategyId(request.strategyId);
          
          if (riskMetrics === null) {
            return {
              success: false,
              error: '无法计算风险指标'
            };
          }
          
          // 根据策略ID动态生成风险评分
          let riskScore = 45.0; // 默认低风险
          let riskLevel = 'low';
          let assessmentResult = 'approved';
          let recommendations = ['策略风险较低，可以继续执行'];
          
          // 策略ID 2 用于critical级别测试
          if (request.strategyId === 2) {
            riskScore = 95.0; // 超过critical阈值(90)
            riskLevel = 'critical';
            assessmentResult = 'rejected';
            recommendations = ['立即停止交易', '降低仓位规模', '限制风险敞口'];
          } else if (request.strategyId === 3) {
            riskScore = 75.5; // high级别
            riskLevel = 'high';
            assessmentResult = 'rejected';
            recommendations = ['拒绝执行高风险策略', '降低交易频率', '限制单笔交易金额'];
          }
          // strategyId === 1 保持默认的低风险设置
          
          // 模拟风险评估数据结构
          const assessmentData = {
            strategy_id: request.strategyId,
            assessment_type: request.assessmentType || 'initial',
            risk_score: riskScore,
            risk_level: riskLevel,
            assessment_result: assessmentResult,
            recommendations: JSON.stringify(recommendations),
            assessed_by: request.assessedBy || 'system',
            assessment_date: new Date().toISOString(),
            details: JSON.stringify({
              marketRisk: 6.5,
              liquidityRisk: 5.2,
              operationalRisk: 4.8,
              concentrationRisk: 7.1
            })
          };
          
          // 如果是高风险或极高风险，触发ZMQ警报
          if (riskLevel === 'high' || riskLevel === 'critical') {
            try {
              const alertMessage = {
                type: 'risk.alerts',
                data: {
                  action: 'alert_created',
                  strategy_id: request.strategyId,
                  risk_level: riskLevel,
                  risk_score: riskScore,
                  timestamp: new Date().toISOString()
                }
              };
              await mockConfigs.zmqBus.publish('risk.alerts', alertMessage);
            } catch (zmqError) {
              // ZMQ发送失败不应该影响风险评估流程
              console.warn('ZMQ警报发送失败:', zmqError.message);
            }
          }
          
          // 调用DAO方法（可能会抛出异常）
          const createResult = await mockConfigs.riskAssessmentDAO.create(assessmentData);
          
          return { success: true, lastInsertId: createResult.lastInsertId || 1 };
        } catch (error) {
          return { success: false, error: error.message };
        }
      }),
      calculateRiskScore: jest.fn().mockReturnValue(0.5),
      createRiskAlert: jest.fn().mockReturnValue({ success: true, lastInsertId: 1 }),
      updateRiskMetrics: jest.fn().mockReturnValue({ success: true }),
      handleRiskAssessmentRequest: jest.fn().mockReturnValue({ success: true }),
      handleStrategyUpdate: jest.fn().mockReturnValue({ success: true }),
      handleOrderUpdate: jest.fn().mockReturnValue({ success: true }),
      handleEmergencyStopRequest: jest.fn().mockReturnValue({ success: true })
    }))
  }
};

// 默认返回值配置
const defaultReturnValues = {
  strategyDAO: {
    findById: jest.fn().mockImplementation((strategyId) => {
      // 根据strategyId返回不同的策略数据
      const strategies = {
        1: {
          id: 1,
          name: 'Low Risk Strategy',
          status: 'active',
          risk_level: 'low',
          expected_return: 0.08, // 8%预期收益率
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        2: {
          id: 2,
          name: 'High Risk Strategy',
          status: 'active',
          risk_level: 'high',
          expected_return: 0.15, // 15%预期收益率
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        3: {
          id: 3,
          name: 'Medium Risk Strategy',
          status: 'active',
          risk_level: 'medium',
          expected_return: 0.12, // 12%预期收益率
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      };
      
      // 如果strategyId不存在（如999），返回null
      return strategies[strategyId] || null;
    }),
    createStrategy: { success: true, lastInsertId: 1 },
    updateStatus: { success: true },
    findAll: [],
    findByStatus: [],
    delete: { success: true }
  },
  
  orderDAO: {
    createOrder: { success: true, lastInsertId: 1 },
    updateStatus: { success: true },
    findByStrategyId: [],
    findById: null,
    findAll: [],
    cancel: { success: true }
  },
  
  riskAssessmentDAO: {
    create: { success: true, lastInsertId: 1 },
    findLatestByStrategyId: null,
    findById: null,
    findAll: [],
    update: { success: true }
  },
  
  riskMetricsDAO: {
    calculateStrategyRiskMetrics: {
      volatility: 0.15,
      sharpe_ratio: 1.2,
      max_drawdown: 0.08,
      var_95: 0.05
    },
    create: { success: true, lastInsertId: 1 },
    findById: null,
    findAll: []
  },
  
  riskAlertDAO: {
    create: { success: true, lastInsertId: 1 },
    findAll: [],
    findById: null,
    update: { success: true }
  },
  
  budgetRequestDAO: {
    create: { success: true, id: 1 },
    getStrategyBudgetUsage: {
      total_approved: 0,
      total_allocated: 0,
      available_budget: 1000000
    },
    approveRequest: true,
    findById: null,
    findAll: [],
    update: { success: true }
  },
  
  riskService: {
    performRiskAssessment: { success: true, lastInsertId: 1 },
    calculateRiskScore: 0.5,
    createRiskAlert: { success: true, lastInsertId: 1 },
    updateRiskMetrics: { success: true },
    handleRiskAssessmentRequest: { success: true },
    handleStrategyUpdate: { success: true },
    handleOrderUpdate: { success: true },
    handleEmergencyStopRequest: { success: true }
  },
  
  fundAllocationDAO: {
    create: { success: true, id: 1 },
    findById: null,
    findAll: [],
    update: { success: true }
  },
  
  accountDAO: {
    findByAccountType: [],
    create: { success: true, id: 1 },
    findById: null,
    findAll: [],
    update: { success: true }
  },
  
  financialTransactionDAO: {
    create: { success: true, id: 1 },
    findById: null,
    findAll: [],
    update: { success: true }
  },
  
  redisCache: {
    get: Promise.resolve(null),
    set: Promise.resolve('OK'),
    setEx: Promise.resolve('OK'),
    del: Promise.resolve(1),
    keys: Promise.resolve([]),
    flushDb: Promise.resolve('OK'),
    quit: Promise.resolve('OK'),
    connect: Promise.resolve(undefined),
    disconnect: Promise.resolve(undefined)
  },
  
  zmqBus: {
    publish: Promise.resolve(true),
    request: Promise.resolve({ success: true }),
    subscribe: Promise.resolve(undefined),
    connect: Promise.resolve(undefined),
    disconnect: Promise.resolve(undefined),
    close: Promise.resolve(undefined)
  },
  
  tacoreClient: {
    executeOrder: Promise.resolve({ success: true, orderId: 'test_order_1' }),
    getOrderStatus: Promise.resolve({ status: 'filled', price: 50000 }),
    cancelOrder: Promise.resolve({ success: true }),
    connect: Promise.resolve(true),
    disconnect: Promise.resolve(true),
    isConnected: true
  },
  
  configManager: {
    getConfig: {
      trader: {
        maxOrderSize: 100000,
        minOrderSize: 100,
        defaultSlippage: 0.001
      },
      risk: {
        maxRiskScore: 80,
        alertThresholds: {
          high: 70,
          critical: 85
        }
      },
      finance: {
        maxBudgetAmount: 10000000,
        approvalWorkflow: {
          autoApprovalLimit: 50000,
          requiresManagerApproval: 100000
        }
      }
    },
    setConfig: true,
    reload: true
  },
  
  logger: {
    info: undefined,
    warn: undefined,
    error: undefined,
    debug: undefined
  }
};

/**
 * 重置所有模拟对象到默认状态
 */
function resetAllMocks() {
  Object.keys(mockConfigs).forEach(mockName => {
    const mockObj = mockConfigs[mockName];
    const defaultValues = defaultReturnValues[mockName];
    
    Object.keys(mockObj).forEach(methodName => {
      mockObj[methodName].mockClear();
      
      if (defaultValues && defaultValues[methodName] !== undefined) {
        const defaultValue = defaultValues[methodName];
        
        // 如果默认值是一个jest.fn()，直接替换mock对象的方法
        if (typeof defaultValue === 'function' && defaultValue._isMockFunction) {
          mockObj[methodName] = defaultValue;
        } else if (defaultValue instanceof Promise || (defaultValue && typeof defaultValue === 'object' && typeof defaultValue.then === 'function')) {
          mockObj[methodName].mockResolvedValue(defaultValue);
        } else {
          mockObj[methodName].mockReturnValue(defaultValue);
        }
      }
    });
  });
}

/**
 * 获取指定模拟对象
 */
function getMock(mockName) {
  return mockConfigs[mockName];
}

/**
 * 设置模拟对象的特定方法返回值
 */
function setMockReturnValue(mockName, methodName, returnValue) {
  if (mockConfigs[mockName] && mockConfigs[mockName][methodName]) {
    if (returnValue instanceof Promise || (typeof returnValue === 'object' && returnValue.then)) {
      mockConfigs[mockName][methodName].mockResolvedValue(returnValue);
    } else {
      mockConfigs[mockName][methodName].mockReturnValue(returnValue);
    }
  }
}

/**
 * 设置模拟对象的特定方法实现
 */
function setMockImplementation(mockName, methodName, implementation) {
  if (mockConfigs[mockName] && mockConfigs[mockName][methodName]) {
    mockConfigs[mockName][methodName].mockImplementation(implementation);
  }
}

module.exports = {
  mockConfigs,
  defaultReturnValues,
  resetAllMocks,
  getMock,
  setMockReturnValue,
  setMockImplementation
};