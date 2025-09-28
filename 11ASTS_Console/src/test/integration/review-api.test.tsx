import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
import { describe, it, expect, beforeEach } from 'vitest'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { api } from '@/lib/api'

// 创建测试用的QueryClient包装器
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchInterval: false,
      },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

// 模拟useQuery hook用于测试
function useReviewsQuery() {
  return {
    data: null,
    isLoading: true,
    error: null,
    refetch: () => Promise.resolve()
  }
}

describe('人工审核中心 API 集成测试', () => {
  beforeEach(() => {
    // 每个测试前重置状态
  })

  describe('INT-FE-API-01: 获取待审列表', () => {
    it('应该正确请求并处理待审策略列表数据', async () => {
      // 直接测试API调用
      const response = await fetch('/api/reviews/pending')
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data.success).toBe(true)
      expect(data.data).toHaveLength(3)
      expect(data.data[0]).toMatchObject({
        id: '1',
        strategyName: '趋势跟踪策略 v2.1',
        submittedBy: 'AI策略优化模组',
        status: 'pending',
        priority: 'high'
      })
    })

    it('应该包含正确的策略详细信息', async () => {
      const response = await fetch('/api/reviews/pending')
      const data = await response.json()

      const firstStrategy = data.data[0]
      expect(firstStrategy).toHaveProperty('backtestResults')
      expect(firstStrategy.backtestResults).toMatchObject({
        sharpeRatio: expect.any(Number),
        maxDrawdown: expect.any(Number),
        winRate: expect.any(Number)
      })
    })

    it('应该返回正确的数据结构', async () => {
      const response = await fetch('/api/reviews/pending')
      const data = await response.json()

      expect(data).toHaveProperty('success', true)
      expect(data).toHaveProperty('data')
      expect(data).toHaveProperty('total')
      expect(data).toHaveProperty('timestamp')
      expect(data.total).toBe(data.data.length)
    })
  })

  describe('INT-FE-API-02: 提交审核决策 (失败场景)', () => {
    it('应该正确处理API调用失败并显示错误提示', async () => {
      // 首先添加一个专门的错误处理器
      server.use(
        http.post('/api/reviews/*/decision', () => {
          return HttpResponse.json(
            { 
              success: false, 
              error: 'Internal server error',
              message: '审核提交失败，请稍后重试'
            },
            { status: 500 }
          )
        })
      )

      // 测试失败场景
      const response = await fetch('/api/reviews/1/decision', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          decision: 'approve',
          comments: '测试失败场景'
        })
      })

      expect(response.ok).toBe(false)
      expect(response.status).toBe(500)

      const data = await response.json()
      expect(data.success).toBe(false)
      expect(data.error).toBe('Internal server error')
      expect(data.message).toBe('审核提交失败，请稍后重试')
    })

  })

  describe('审核决策提交 (成功场景)', () => {
    it('应该正确处理成功的审核决策提交', async () => {
      const response = await fetch('/api/reviews/1/decision', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          decision: 'approve',
          comments: '策略表现良好，批准上线'
        })
      })

      expect(response.ok).toBe(true)
      const data = await response.json()
      
      expect(data.success).toBe(true)
      expect(data.data).toMatchObject({
        reviewId: '1',
        decision: 'approve',
        status: 'approved'
      })
      expect(data.data.message).toContain('策略已批准')
    })

    it('应该正确处理拒绝决策', async () => {
      const response = await fetch('/api/reviews/2/decision', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          decision: 'reject',
          comments: '风险过高，需要进一步优化'
        })
      })

      expect(response.ok).toBe(true)
      const data = await response.json()
      
      expect(data.success).toBe(true)
      expect(data.data).toMatchObject({
        reviewId: '2',
        decision: 'reject',
        status: 'rejected'
      })
      expect(data.data.message).toContain('策略已拒绝')
    })
  })

  describe('策略详情API测试', () => {
    it('应该正确获取单个策略的详细信息', async () => {
      const response = await fetch('/api/reviews/1')
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data.success).toBe(true)
      expect(data.data).toHaveProperty('detailedAnalysis')
      expect(data.data.detailedAnalysis).toMatchObject({
        codeQuality: 'A',
        riskAssessment: 'Medium',
        complianceCheck: 'Passed',
        performanceMetrics: expect.any(Object)
      })
    })

    it('应该正确处理不存在的策略ID', async () => {
      const response = await fetch('/api/reviews/999')
      const data = await response.json()

      expect(response.ok).toBe(false)
      expect(response.status).toBe(404)
      expect(data.success).toBe(false)
      expect(data.error).toBe('Review not found')
    })
  })

  describe('系统监控API测试', () => {
    it('应该正确获取模组状态信息', async () => {
      const response = await fetch('/api/monitoring/modules')
      const data = await response.json()

      expect(response.ok).toBe(true)
      expect(data.success).toBe(true)
      expect(data.data.modules).toHaveLength(3)
      expect(data.data).toMatchObject({
        totalModules: 3,
        runningModules: 3,
        stoppedModules: 0
      })
    })

    it('应该包含模组健康状态信息', async () => {
      const response = await fetch('/api/monitoring/modules')
      const data = await response.json()

      const modules = data.data.modules
      expect(modules[0]).toMatchObject({
        id: 'ai-strategy-optimizer',
        name: 'AI策略优化模组',
        status: 'running',
        health: 'healthy'
      })

      // 检查警告状态的模组
      const warningModule = modules.find(m => m.health === 'warning')
      expect(warningModule).toBeDefined()
      expect(warningModule.warnings).toBeInstanceOf(Array)
    })
  })

  describe('风控演习API测试', () => {
    it('应该正确启动风控演习', async () => {
      const response = await fetch('/api/risk/rehearsal/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scenarioId: 'market_crash_519',
          parameters: {
            severity: 'high',
            duration: 60
          }
        })
      })

      expect(response.ok).toBe(true)
      const data = await response.json()
      
      expect(data.success).toBe(true)
      expect(data.data).toMatchObject({
        rehearsalId: expect.stringMatching(/^rehearsal_\d+$/),
        scenarioId: 'market_crash_519',
        status: 'starting'
      })
      expect(data.data.message).toContain('风控演习已启动')
    })
  })
})