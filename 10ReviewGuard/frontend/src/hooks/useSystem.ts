import { useCallback, useEffect } from 'react'
import { useReviewStore } from '@/store/review-store'
import type { SystemStatus, AuditRule } from '@/store/review-store'

// 系统监控hook
export const useSystemMonitor = () => {
  const {
    systemStatus,
    isLoading,
    error,
    setSystemStatus,
    setLoading,
    setError,
    clearError
  } = useReviewStore()

  // 获取系统状态
  const fetchSystemStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 800))
      
      const mockStatus: SystemStatus = {
        status: Math.random() > 0.8 ? 'warning' : 'healthy',
        pending_count: Math.floor(Math.random() * 50) + 10,
        processed_today: Math.floor(Math.random() * 200) + 100,
        avg_processing_time: Math.floor(Math.random() * 300) + 120, // 秒
        system_load: Math.random() * 0.8 + 0.1, // 0.1-0.9
        last_updated: new Date().toISOString()
      }
      
      setSystemStatus(mockStatus)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取系统状态失败')
    } finally {
      setLoading(false)
    }
  }, [setSystemStatus, setLoading, setError])

  // 获取性能指标
  const getPerformanceMetrics = useCallback(() => {
    if (!systemStatus) return null
    
    return {
      efficiency: systemStatus.processed_today > 150 ? 'high' : systemStatus.processed_today > 100 ? 'medium' : 'low',
      load_status: systemStatus.system_load > 0.7 ? 'high' : systemStatus.system_load > 0.4 ? 'medium' : 'low',
      response_time: systemStatus.avg_processing_time < 180 ? 'fast' : systemStatus.avg_processing_time < 300 ? 'normal' : 'slow',
      health_score: (
        (systemStatus.status === 'healthy' ? 100 : systemStatus.status === 'warning' ? 70 : 30) +
        (systemStatus.system_load < 0.5 ? 100 : systemStatus.system_load < 0.8 ? 70 : 30) +
        (systemStatus.avg_processing_time < 180 ? 100 : systemStatus.avg_processing_time < 300 ? 70 : 30)
      ) / 3
    }
  }, [systemStatus])

  // 获取服务状态
  const getServiceStatus = useCallback(() => {
    const services = [
      {
        name: 'API Gateway',
        status: Math.random() > 0.1 ? 'running' : 'error',
        uptime: '99.9%',
        response_time: Math.floor(Math.random() * 50) + 10
      },
      {
        name: 'Review Engine',
        status: Math.random() > 0.05 ? 'running' : 'warning',
        uptime: '99.8%',
        response_time: Math.floor(Math.random() * 100) + 50
      },
      {
        name: 'Risk Calculator',
        status: Math.random() > 0.02 ? 'running' : 'error',
        uptime: '99.95%',
        response_time: Math.floor(Math.random() * 80) + 30
      },
      {
        name: 'Database',
        status: Math.random() > 0.01 ? 'running' : 'warning',
        uptime: '99.99%',
        response_time: Math.floor(Math.random() * 20) + 5
      },
      {
        name: 'Message Queue',
        status: Math.random() > 0.03 ? 'running' : 'error',
        uptime: '99.7%',
        response_time: Math.floor(Math.random() * 30) + 10
      }
    ]
    
    return services
  }, [])

  // 获取实时活动日志
  const getActivityLogs = useCallback(() => {
    const activities = [
      {
        id: 'ACT-001',
        timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
        type: 'review_approved',
        message: '策略 STR-001 审核通过',
        user: 'reviewer',
        level: 'info'
      },
      {
        id: 'ACT-002',
        timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
        type: 'review_rejected',
        message: '策略 STR-002 审核拒绝 - 风险过高',
        user: 'admin',
        level: 'warning'
      },
      {
        id: 'ACT-003',
        timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
        type: 'system_alert',
        message: '系统负载达到 75%',
        user: 'system',
        level: 'warning'
      },
      {
        id: 'ACT-004',
        timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
        type: 'rule_updated',
        message: '风险阈值规则已更新',
        user: 'admin',
        level: 'info'
      },
      {
        id: 'ACT-005',
        timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
        type: 'user_login',
        message: '用户 reviewer 登录系统',
        user: 'reviewer',
        level: 'info'
      }
    ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    
    return activities
  }, [])

  // 自动刷新系统状态
  useEffect(() => {
    fetchSystemStatus()
    
    const interval = setInterval(fetchSystemStatus, 30000) // 30秒刷新一次
    return () => clearInterval(interval)
  }, [fetchSystemStatus])

  return {
    systemStatus,
    isLoading,
    error,
    fetchSystemStatus,
    getPerformanceMetrics,
    getServiceStatus,
    getActivityLogs,
    clearError
  }
}

// 审核规则管理hook
export const useAuditRules = () => {
  const {
    auditRules,
    isLoading,
    error,
    setAuditRules,
    setLoading,
    setError,
    addAuditRule,
    updateAuditRule,
    removeAuditRule,
    toggleRuleActive,
    clearError
  } = useReviewStore()

  // 获取规则列表
  const fetchRules = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 600))
      
      const mockRules: AuditRule[] = [
        {
          id: 'RULE-001',
          name: '高风险策略自动拒绝',
          description: '当策略风险等级为高且最大回撤超过20%时自动拒绝',
          rule_type: 'auto_reject',
          conditions: {
            risk_level: 'high',
            max_drawdown: { operator: '>', value: 0.2 }
          },
          actions: {
            status: 'rejected',
            reason: '风险过高，超出可接受范围'
          },
          priority: 1,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-15T10:00:00Z'
        },
        {
          id: 'RULE-002',
          name: '低风险策略自动通过',
          description: '当策略风险等级为低且预期收益合理时自动通过',
          rule_type: 'auto_approve',
          conditions: {
            risk_level: 'low',
            expected_return: { operator: '<=', value: 0.15 },
            max_drawdown: { operator: '<=', value: 0.05 }
          },
          actions: {
            status: 'approved',
            reason: '低风险策略，符合自动审批条件'
          },
          priority: 2,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-10T15:30:00Z'
        },
        {
          id: 'RULE-003',
          name: '高收益策略需要高级审核',
          description: '当预期收益超过30%时需要高级审核员审核',
          rule_type: 'require_senior',
          conditions: {
            expected_return: { operator: '>', value: 0.3 }
          },
          actions: {
            assign_to: 'senior_reviewer',
            priority: 'high'
          },
          priority: 3,
          is_active: true,
          created_at: '2024-01-05T00:00:00Z',
          updated_at: '2024-01-12T09:15:00Z'
        },
        {
          id: 'RULE-004',
          name: '风险阈值检查',
          description: '检查策略是否符合风险阈值要求',
          rule_type: 'risk_threshold',
          conditions: {
            max_drawdown: { operator: '>', value: 0.15 },
            volatility: { operator: '>', value: 0.25 }
          },
          actions: {
            flag: 'high_risk',
            require_review: true
          },
          priority: 4,
          is_active: false,
          created_at: '2024-01-08T00:00:00Z',
          updated_at: '2024-01-14T14:20:00Z'
        }
      ]
      
      setAuditRules(mockRules)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取规则列表失败')
    } finally {
      setLoading(false)
    }
  }, [setAuditRules, setLoading, setError])

  // 创建新规则
  const createRule = useCallback(async (ruleData: Omit<AuditRule, 'id' | 'created_at' | 'updated_at'>) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      const newRule: AuditRule = {
        ...ruleData,
        id: `RULE-${Date.now()}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      addAuditRule(newRule)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建规则失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [addAuditRule, setLoading, setError])

  // 更新规则
  const updateRule = useCallback(async (ruleId: string, updates: Partial<AuditRule>) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 800))
      
      updateAuditRule(ruleId, updates)
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新规则失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [updateAuditRule, setLoading, setError])

  // 删除规则
  const deleteRule = useCallback(async (ruleId: string) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 600))
      
      removeAuditRule(ruleId)
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除规则失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [removeAuditRule, setLoading, setError])

  // 切换规则状态
  const toggleRule = useCallback(async (ruleId: string) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 400))
      
      toggleRuleActive(ruleId)
    } catch (err) {
      setError(err instanceof Error ? err.message : '切换规则状态失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [toggleRuleActive, setLoading, setError])

  // 获取规则统计
  const getRuleStats = useCallback(() => {
    return {
      total: auditRules.length,
      active: auditRules.filter(rule => rule.is_active).length,
      inactive: auditRules.filter(rule => !rule.is_active).length,
      by_type: {
        auto_approve: auditRules.filter(rule => rule.rule_type === 'auto_approve').length,
        auto_reject: auditRules.filter(rule => rule.rule_type === 'auto_reject').length,
        risk_threshold: auditRules.filter(rule => rule.rule_type === 'risk_threshold').length,
        require_senior: auditRules.filter(rule => rule.rule_type === 'require_senior').length
      }
    }
  }, [auditRules])

  // 验证规则配置
  const validateRule = useCallback((rule: Partial<AuditRule>): string[] => {
    const errors: string[] = []
    
    if (!rule.name?.trim()) {
      errors.push('规则名称不能为空')
    }
    
    if (!rule.description?.trim()) {
      errors.push('规则描述不能为空')
    }
    
    if (!rule.rule_type) {
      errors.push('请选择规则类型')
    }
    
    if (!rule.conditions || Object.keys(rule.conditions).length === 0) {
      errors.push('请配置规则条件')
    }
    
    if (!rule.actions || Object.keys(rule.actions).length === 0) {
      errors.push('请配置规则动作')
    }
    
    if (rule.priority !== undefined && (rule.priority < 1 || rule.priority > 100)) {
      errors.push('优先级必须在1-100之间')
    }
    
    return errors
  }, [])

  // 初始化数据
  useEffect(() => {
    fetchRules()
  }, [fetchRules])

  return {
    rules: auditRules,
    isLoading,
    error,
    fetchRules,
    createRule,
    updateRule,
    deleteRule,
    toggleRule,
    getRuleStats,
    validateRule,
    clearError
  }
}