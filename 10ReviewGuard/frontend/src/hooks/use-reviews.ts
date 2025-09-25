import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ReviewAPI } from '@/lib/api'
import { useReviewStore } from '@/store/review-store'
import type { ReviewDecision } from '@/store/review-store'

// 查询键常量
export const QUERY_KEYS = {
  PENDING_REVIEWS: 'pending-reviews',
  STRATEGY_DETAIL: 'strategy-detail',
  REVIEW_HISTORY: 'review-history',
  AUDIT_RULES: 'audit-rules',
  SYSTEM_STATUS: 'system-status',
  CURRENT_USER: 'current-user',
  HEALTH: 'health'
} as const

// 获取待审核策略列表
export function usePendingReviews() {
  const { filters, setLoading, setError, setPendingReviews, setPagination } = useReviewStore()
  
  return useQuery({
    queryKey: [QUERY_KEYS.PENDING_REVIEWS, filters],
    queryFn: async () => {
      setLoading(true)
      try {
        const response = await ReviewAPI.getPendingReviews(filters)
        setPendingReviews(response.data)
        if (response.page_info) {
          setPagination(response.page_info)
        }
        setError(null)
        return response
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '获取数据失败'
        setError(errorMessage)
        throw error
      } finally {
        setLoading(false)
      }
    },
    staleTime: 30000, // 30秒内数据被认为是新鲜的
    refetchInterval: 60000, // 每分钟自动刷新
  })
}

// 获取策略详情
export function useStrategyDetail(strategyId: string | null) {
  const { setLoading, setError } = useReviewStore()
  
  return useQuery({
    queryKey: [QUERY_KEYS.STRATEGY_DETAIL, strategyId],
    queryFn: async () => {
      if (!strategyId) throw new Error('Strategy ID is required')
      
      setLoading(true)
      try {
        const response = await ReviewAPI.getStrategyDetail(strategyId)
        setError(null)
        return response
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '获取策略详情失败'
        setError(errorMessage)
        throw error
      } finally {
        setLoading(false)
      }
    },
    enabled: !!strategyId, // 只有当strategyId存在时才执行查询
    staleTime: 60000, // 1分钟内数据被认为是新鲜的
  })
}

// 获取审核历史
export function useReviewHistory(params: {
  page?: number
  limit?: number
  reviewer_id?: string
  start_date?: string
  end_date?: string
} = {}) {
  const { setLoading, setError, setReviewHistory } = useReviewStore()
  
  return useQuery({
    queryKey: [QUERY_KEYS.REVIEW_HISTORY, params],
    queryFn: async () => {
      setLoading(true)
      try {
        const response = await ReviewAPI.getReviewHistory(params)
        setReviewHistory(response.data)
        setError(null)
        return response
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '获取审核历史失败'
        setError(errorMessage)
        throw error
      } finally {
        setLoading(false)
      }
    },
    staleTime: 60000,
  })
}

// 获取系统状态
export function useSystemStatus() {
  return useQuery({
    queryKey: [QUERY_KEYS.SYSTEM_STATUS],
    queryFn: () => ReviewAPI.getSystemStatus(),
    refetchInterval: 30000, // 每30秒刷新系统状态
    staleTime: 15000,
  })
}

// 获取当前用户
export function useCurrentUser() {
  const { setCurrentUser, setError } = useReviewStore()
  
  return useQuery({
    queryKey: [QUERY_KEYS.CURRENT_USER],
    queryFn: async () => {
      try {
        const user = await ReviewAPI.getCurrentUser()
        setCurrentUser(user)
        setError(null)
        return user
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '获取用户信息失败'
        setError(errorMessage)
        setCurrentUser(null)
        throw error
      }
    },
    staleTime: 300000, // 5分钟内数据被认为是新鲜的
    retry: false, // 认证失败时不重试
  })
}

// 提交审核决策
export function useSubmitReviewDecision() {
  const queryClient = useQueryClient()
  const { updateReviewStatus, addReviewDecision, setError } = useReviewStore()
  
  return useMutation({
    mutationFn: async ({
      reviewId,
      decision
    }: {
      reviewId: string
      decision: {
        decision: 'approve' | 'reject' | 'defer'
        reason?: string
        risk_adjustment?: Record<string, unknown>
      }
    }) => {
      return await ReviewAPI.submitReviewDecision(reviewId, decision)
    },
    onSuccess: (data, variables) => {
      // 更新本地状态
      const newStatus = variables.decision.decision === 'approve' ? 'approved' : 
                       variables.decision.decision === 'reject' ? 'rejected' : 'deferred'
      
      updateReviewStatus(variables.reviewId, newStatus)
      
      // 添加到审核历史
      const reviewDecision: ReviewDecision = {
        id: data.review_id,
        strategy_review_id: variables.reviewId,
        reviewer_id: 'current_user', // 实际应该从用户状态获取
        decision: variables.decision.decision,
        reason: variables.decision.reason,
        risk_adjustment: variables.decision.risk_adjustment,
        decision_time: new Date().toISOString()
      }
      addReviewDecision(reviewDecision)
      
      // 刷新相关查询
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PENDING_REVIEWS] })
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REVIEW_HISTORY] })
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SYSTEM_STATUS] })
      
      setError(null)
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : '提交审核决策失败'
      setError(errorMessage)
    }
  })
}

// 用户登录
export function useLogin() {
  const queryClient = useQueryClient()
  const { setCurrentUser, setError } = useReviewStore()
  
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      return await ReviewAPI.login(credentials)
    },
    onSuccess: (data) => {
      // 保存token
      localStorage.setItem('auth_token', data.access_token)
      
      // 设置用户信息
      setCurrentUser(data.user)
      
      // 清除错误
      setError(null)
      
      // 刷新用户相关查询
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.CURRENT_USER] })
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : '登录失败'
      setError(errorMessage)
    }
  })
}

// 获取审核规则
export function useAuditRules() {
  return useQuery({
    queryKey: [QUERY_KEYS.AUDIT_RULES],
    queryFn: ReviewAPI.getAuditRules,
    staleTime: 5 * 60 * 1000, // 5分钟
  })
}

// 用户登出
export function useLogout() {
  const queryClient = useQueryClient()
  const { setCurrentUser, reset } = useReviewStore()
  
  return useMutation({
    mutationFn: async () => {
      // 清除本地token
      localStorage.removeItem('auth_token')
    },
    onSuccess: () => {
      // 重置状态
      setCurrentUser(null)
      reset()
      
      // 清除所有查询缓存
      queryClient.clear()
    }
  })
}