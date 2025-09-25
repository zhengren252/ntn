import { useCallback, useEffect } from 'react'
import { useReviewStore } from '@/store/review-store'
import type { StrategyReview, ReviewDecision } from '@/store/review-store'

// 审核列表管理hook
export const useReviews = () => {
  const {
    pendingReviews,
    selectedReview,
    isLoading,
    error,
    filters,
    selectedReviewIds,
    setPendingReviews,
    setSelectedReview,
    setLoading,
    setError,
    setFilters,
    updateReviewStatus,
    updateReviewPriority,
    removeReview,
    batchUpdateReviews,
    getFilteredReviews,
    getReviewStats,
    toggleReviewSelection,
    clearSelection,
    clearError
  } = useReviewStore()

  // 获取审核列表
  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      const mockReviews: StrategyReview[] = [
        {
          id: 'REV-001',
          strategy_id: 'STR-001',
          symbol: 'BTCUSDT',
          strategy_type: 'Grid Trading',
          expected_return: 0.15,
          max_drawdown: 0.08,
          risk_level: 'medium',
          status: 'pending',
          created_at: '2024-01-15T10:30:00Z',
          updated_at: '2024-01-15T10:30:00Z',
          priority: 'high',
          tags: ['crypto', 'grid']
        },
        {
          id: 'REV-002',
          strategy_id: 'STR-002',
          symbol: 'ETHUSDT',
          strategy_type: 'DCA Strategy',
          expected_return: 0.12,
          max_drawdown: 0.05,
          risk_level: 'low',
          status: 'processing',
          created_at: '2024-01-15T11:00:00Z',
          updated_at: '2024-01-15T11:15:00Z',
          priority: 'medium',
          tags: ['crypto', 'dca']
        },
        {
          id: 'REV-003',
          strategy_id: 'STR-003',
          symbol: 'ADAUSDT',
          strategy_type: 'Momentum Trading',
          expected_return: 0.25,
          max_drawdown: 0.15,
          risk_level: 'high',
          status: 'pending',
          created_at: '2024-01-15T12:00:00Z',
          updated_at: '2024-01-15T12:00:00Z',
          priority: 'high',
          tags: ['crypto', 'momentum']
        }
      ]
      
      setPendingReviews(mockReviews)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取审核列表失败')
    } finally {
      setLoading(false)
    }
  }, [setPendingReviews, setLoading, setError])

  // 审批操作
  const approveReview = useCallback(async (reviewId: string, reason?: string) => {
    try {
      setLoading(true)
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      updateReviewStatus(reviewId, 'approved')
      
      // 添加审核决策记录
      const decision: ReviewDecision = {
        id: `DEC-${Date.now()}`,
        strategy_review_id: reviewId,
        decision: 'approve',
        reason: reason || '符合风险要求',
        reviewer_id: 'USER-001',
        decision_time: new Date().toISOString()
      }
      
      useReviewStore.getState().addReviewDecision(decision)
    } catch (err) {
      setError(err instanceof Error ? err.message : '审批失败')
    } finally {
      setLoading(false)
    }
  }, [updateReviewStatus, setLoading, setError])

  // 拒绝操作
  const rejectReview = useCallback(async (reviewId: string, reason: string) => {
    try {
      setLoading(true)
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      updateReviewStatus(reviewId, 'rejected')
      
      // 添加审核决策记录
      const decision: ReviewDecision = {
        id: `DEC-${Date.now()}`,
        strategy_review_id: reviewId,
        decision: 'reject',
        reason,
        reviewer_id: 'USER-001',
        decision_time: new Date().toISOString()
      }
      
      useReviewStore.getState().addReviewDecision(decision)
    } catch (err) {
      setError(err instanceof Error ? err.message : '拒绝失败')
    } finally {
      setLoading(false)
    }
  }, [updateReviewStatus, setLoading, setError])

  // 延期操作
  const deferReview = useCallback(async (reviewId: string, reason: string) => {
    try {
      setLoading(true)
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      updateReviewStatus(reviewId, 'deferred')
      
      // 添加审核决策记录
      const decision: ReviewDecision = {
        id: `DEC-${Date.now()}`,
        strategy_review_id: reviewId,
        decision: 'defer',
        reason,
        reviewer_id: 'USER-001',
        decision_time: new Date().toISOString()
      }
      
      useReviewStore.getState().addReviewDecision(decision)
    } catch (err) {
      setError(err instanceof Error ? err.message : '延期失败')
    } finally {
      setLoading(false)
    }
  }, [updateReviewStatus, setLoading, setError])

  // 批量操作
  const batchApprove = useCallback(async (reviewIds: string[]) => {
    try {
      setLoading(true)
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      batchUpdateReviews(reviewIds, { status: 'approved' })
      clearSelection()
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量审批失败')
    } finally {
      setLoading(false)
    }
  }, [batchUpdateReviews, clearSelection, setLoading, setError])

  // 搜索和筛选
  const searchReviews = useCallback((searchTerm: string) => {
    setFilters({ search: searchTerm, page: 1 })
  }, [setFilters])

  const filterByStatus = useCallback((status: string) => {
    setFilters({ status: status || undefined, page: 1 })
  }, [setFilters])

  const filterByRiskLevel = useCallback((riskLevel: string) => {
    setFilters({ risk_level: riskLevel || undefined, page: 1 })
  }, [setFilters])

  // 分页
  const changePage = useCallback((page: number) => {
    setFilters({ page })
  }, [setFilters])

  const changePageSize = useCallback((limit: number) => {
    setFilters({ limit, page: 1 })
  }, [setFilters])

  // 初始化数据
  useEffect(() => {
    fetchReviews()
  }, [fetchReviews])

  return {
    // 数据
    reviews: pendingReviews,
    filteredReviews: getFilteredReviews(),
    selectedReview,
    selectedReviewIds,
    stats: getReviewStats(),
    
    // 状态
    isLoading,
    error,
    filters,
    
    // 操作
    fetchReviews,
    setSelectedReview,
    approveReview,
    rejectReview,
    deferReview,
    batchApprove,
    updateReviewPriority,
    removeReview,
    
    // 选择
    toggleReviewSelection,
    clearSelection,
    
    // 搜索筛选
    searchReviews,
    filterByStatus,
    filterByRiskLevel,
    
    // 分页
    changePage,
    changePageSize,
    
    // 工具
    clearError
  }
}

// 审核详情hook
export const useReviewDetail = (reviewId?: string) => {
  const {
    strategyDetail,
    isLoading,
    error,
    setStrategyDetail,
    setLoading,
    setError,
    getReviewById
  } = useReviewStore()

  // 获取审核详情
  const fetchReviewDetail = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 800))
      
      const review = getReviewById(id)
      if (!review) {
        throw new Error('审核记录不存在')
      }
      
      const mockDetail = {
        ...review,
        description: '基于网格交易策略的自动化交易系统，适用于震荡市场环境',
        risk_analysis: {
          volatility_score: 0.65,
          liquidity_score: 0.85,
          correlation_score: 0.45,
          overall_risk: 0.62
        },
        historical_performance: {
          total_return: 0.15,
          sharpe_ratio: 1.25,
          max_drawdown_period: '2023-11-15 to 2023-11-22',
          win_rate: 0.68
        },
        market_conditions: {
          volatility: 0.45,
          trend: 'sideways',
          liquidity: 0.85
        }
      }
      
      setStrategyDetail(mockDetail)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取详情失败')
    } finally {
      setLoading(false)
    }
  }, [setStrategyDetail, setLoading, setError, getReviewById])

  // 自动获取详情
  useEffect(() => {
    if (reviewId) {
      fetchReviewDetail(reviewId)
    }
  }, [reviewId, fetchReviewDetail])

  return {
    detail: strategyDetail,
    isLoading,
    error,
    fetchReviewDetail,
    clearError: () => setError(null)
  }
}