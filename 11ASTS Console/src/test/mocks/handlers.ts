import { http, HttpResponse } from 'msw'

// 模拟人工审核API的响应数据
const mockPendingReviews = [
  {
    id: '1',
    strategyName: '趋势跟踪策略 v2.1',
    submittedBy: 'AI策略优化模组',
    submittedAt: '2024-01-15T10:30:00Z',
    status: 'pending',
    priority: 'high',
    description: '基于移动平均线的趋势跟踪策略，优化了止损逻辑',
    riskLevel: 'medium',
    expectedReturn: 15.2,
    backtestResults: {
      sharpeRatio: 1.85,
      maxDrawdown: 8.5,
      winRate: 68.3
    }
  },
  {
    id: '2',
    strategyName: '均值回归策略 v1.3',
    submittedBy: 'AI策略优化模组',
    submittedAt: '2024-01-15T09:15:00Z',
    status: 'pending',
    priority: 'medium',
    description: '基于统计套利的均值回归策略',
    riskLevel: 'low',
    expectedReturn: 8.7,
    backtestResults: {
      sharpeRatio: 1.42,
      maxDrawdown: 4.2,
      winRate: 72.1
    }
  },
  {
    id: '3',
    strategyName: '动量突破策略 v3.0',
    submittedBy: 'AI策略优化模组',
    submittedAt: '2024-01-15T08:45:00Z',
    status: 'pending',
    priority: 'high',
    description: '基于价格动量的突破策略，新增了成交量确认',
    riskLevel: 'high',
    expectedReturn: 22.8,
    backtestResults: {
      sharpeRatio: 2.15,
      maxDrawdown: 12.3,
      winRate: 61.5
    }
  }
]

// API处理器
export const handlers = [
  // 获取待审核策略列表
  http.get('/api/reviews/pending', () => {
    return HttpResponse.json({
      success: true,
      data: mockPendingReviews,
      total: mockPendingReviews.length,
      timestamp: new Date().toISOString()
    })
  }),

  // 获取单个策略详情
  http.get('/api/reviews/:id', ({ params }) => {
    const { id } = params
    const review = mockPendingReviews.find(r => r.id === id)
    
    if (!review) {
      return HttpResponse.json(
        { success: false, error: 'Review not found' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: {
        ...review,
        detailedAnalysis: {
          codeQuality: 'A',
          riskAssessment: 'Medium',
          complianceCheck: 'Passed',
          performanceMetrics: {
            avgExecutionTime: '2.3ms',
            memoryUsage: '45MB',
            cpuUsage: '12%'
          }
        }
      }
    })
  }),

  // 提交审核决策 - 成功场景
  http.post('/api/reviews/:id/decision', async ({ params, request }) => {
    const { id } = params
    const body = await request.json() as { decision: 'approve' | 'reject', comments?: string }
    
    const review = mockPendingReviews.find(r => r.id === id)
    if (!review) {
      return HttpResponse.json(
        { success: false, error: 'Review not found' },
        { status: 404 }
      )
    }

    // 模拟处理时间
    await new Promise(resolve => setTimeout(resolve, 500))

    return HttpResponse.json({
      success: true,
      data: {
        reviewId: id,
        decision: body.decision,
        processedAt: new Date().toISOString(),
        status: body.decision === 'approve' ? 'approved' : 'rejected',
        message: `策略已${body.decision === 'approve' ? '批准' : '拒绝'}，正在通知相关模组`
      }
    })
  }),

  // 提交审核决策 - 失败场景 (用于测试错误处理)
  http.post('/api/reviews/error-test/decision', () => {
    return HttpResponse.json(
      { 
        success: false, 
        error: 'Internal server error',
        message: '审核提交失败，请稍后重试'
      },
      { status: 500 }
    )
  }),

  // 获取模组状态 (用于系统监控测试)
  http.get('/api/monitoring/modules', () => {
    return HttpResponse.json({
      success: true,
      data: {
        modules: [
          {
            id: 'ai-strategy-optimizer',
            name: 'AI策略优化模组',
            status: 'running',
            health: 'healthy',
            uptime: 86400,
            lastHeartbeat: new Date().toISOString()
          },
          {
            id: 'human-review',
            name: '人工审核模组',
            status: 'running',
            health: 'healthy',
            uptime: 86400,
            lastHeartbeat: new Date().toISOString()
          },
          {
            id: 'trader-module',
            name: '交易员模组',
            status: 'running',
            health: 'warning',
            uptime: 82800,
            lastHeartbeat: new Date().toISOString(),
            warnings: ['High memory usage detected']
          }
        ],
        totalModules: 3,
        runningModules: 3,
        stoppedModules: 0,
        timestamp: new Date().toISOString()
      }
    })
  }),

  // 风控演习API
  http.post('/api/risk/rehearsal/start', async ({ request }) => {
    const body = await request.json() as { scenarioId: string, parameters?: Record<string, unknown> }
    
    return HttpResponse.json({
      success: true,
      data: {
        rehearsalId: `rehearsal_${Date.now()}`,
        scenarioId: body.scenarioId,
        status: 'starting',
        startedAt: new Date().toISOString(),
        message: '风控演习已启动，正在初始化模拟环境'
      }
    })
  })
]