import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

// 策略审核数据类型
export interface StrategyReview {
  id: string
  strategy_id: string
  symbol: string
  strategy_type: string
  expected_return: number
  max_drawdown: number
  risk_level: 'low' | 'medium' | 'high'
  status: 'pending' | 'processing' | 'approved' | 'rejected' | 'deferred'
  created_at: string
  updated_at: string
  reviewer_id?: string
  priority?: 'low' | 'medium' | 'high'
  tags?: string[]
}

// 策略详情数据类型
export interface StrategyDetail extends StrategyReview {
  description?: string
  risk_analysis: {
    volatility_score: number
    liquidity_score: number
    correlation_score: number
    overall_risk: number
  }
  historical_performance: {
    total_return: number
    sharpe_ratio: number
    max_drawdown_period: string
    win_rate: number
  }
  market_conditions: {
    volatility: number
    trend: string
    liquidity: number
  }
}

// 审核规则数据类型
export interface AuditRule {
  id: string
  name: string
  description: string
  rule_type: 'risk_threshold' | 'auto_approve' | 'auto_reject' | 'require_senior'
  conditions: Record<string, unknown>
  actions: Record<string, unknown>
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// 系统状态数据类型
export interface SystemStatus {
  status: 'healthy' | 'warning' | 'error'
  pending_count: number
  processed_today: number
  avg_processing_time: number
  system_load: number
  last_updated: string
}

// 审核决策数据类型
export interface ReviewDecision {
  id: string
  strategy_review_id: string
  reviewer_id: string
  decision: 'approve' | 'reject' | 'defer'
  reason?: string
  risk_adjustment?: Record<string, unknown>
  decision_time: string
}

// 用户数据类型
export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'reviewer' | 'analyst' | 'readonly'
  status: 'active' | 'inactive'
  created_at: string
  last_login: string
}

// 分页信息类型
export interface PaginationInfo {
  current_page: number
  total_pages: number
  has_next: boolean
  total: number
}

// 审核状态管理
interface ReviewState {
  // 数据状态
  pendingReviews: StrategyReview[]
  selectedReview: StrategyReview | null
  strategyDetail: StrategyDetail | null
  reviewHistory: ReviewDecision[]
  auditRules: AuditRule[]
  systemStatus: SystemStatus | null
  currentUser: User | null
  pagination: PaginationInfo | null
  
  // 加载状态
  isLoading: boolean
  isSubmitting: boolean
  error: string | null
  
  // 筛选状态
  filters: {
    risk_level?: string
    status?: string
    search?: string
    date_range?: [string, string]
    page: number
    limit: number
  }
  
  // UI状态
  selectedReviewIds: string[]
  isQuickReviewOpen: boolean
  quickReviewData: {
    reviewId: string
    decision?: 'approve' | 'reject' | 'defer'
    reason?: string
  } | null
  
  // Actions - 数据设置
  setPendingReviews: (reviews: StrategyReview[]) => void
  setSelectedReview: (review: StrategyReview | null) => void
  setStrategyDetail: (detail: StrategyDetail | null) => void
  setReviewHistory: (history: ReviewDecision[]) => void
  setAuditRules: (rules: AuditRule[]) => void
  setSystemStatus: (status: SystemStatus | null) => void
  setCurrentUser: (user: User | null) => void
  setPagination: (pagination: PaginationInfo) => void
  
  // Actions - 状态管理
  setLoading: (loading: boolean) => void
  setSubmitting: (submitting: boolean) => void
  setError: (error: string | null) => void
  setFilters: (filters: Partial<ReviewState['filters']>) => void
  
  // Actions - UI状态
  setSelectedReviewIds: (ids: string[]) => void
  toggleReviewSelection: (id: string) => void
  clearSelection: () => void
  setQuickReviewOpen: (open: boolean) => void
  setQuickReviewData: (data: ReviewState['quickReviewData']) => void
  
  // Actions - 业务操作
  updateReviewStatus: (reviewId: string, status: StrategyReview['status']) => void
  updateReviewPriority: (reviewId: string, priority: 'low' | 'medium' | 'high') => void
  addReviewDecision: (decision: ReviewDecision) => void
  removeReview: (reviewId: string) => void
  batchUpdateReviews: (reviewIds: string[], updates: Partial<StrategyReview>) => void
  
  // Actions - 规则管理
  addAuditRule: (rule: AuditRule) => void
  updateAuditRule: (ruleId: string, updates: Partial<AuditRule>) => void
  removeAuditRule: (ruleId: string) => void
  toggleRuleActive: (ruleId: string) => void
  
  // Actions - 工具方法
  getReviewById: (id: string) => StrategyReview | undefined
  getReviewsByStatus: (status: StrategyReview['status']) => StrategyReview[]
  getReviewsByRiskLevel: (riskLevel: StrategyReview['risk_level']) => StrategyReview[]
  getFilteredReviews: () => StrategyReview[]
  getReviewStats: () => {
    total: number
    pending: number
    approved: number
    rejected: number
    deferred: number
    high_risk: number
  }
  
  // Actions - 重置和清理
  clearError: () => void
  clearCache: () => void
  reset: () => void
}

const initialState = {
  pendingReviews: [],
  selectedReview: null,
  strategyDetail: null,
  reviewHistory: [],
  auditRules: [],
  systemStatus: null,
  currentUser: null,
  pagination: null,
  isLoading: false,
  isSubmitting: false,
  error: null,
  filters: {
    page: 1,
    limit: 20
  },
  selectedReviewIds: [],
  isQuickReviewOpen: false,
  quickReviewData: null
}

export const useReviewStore = create<ReviewState>()(devtools(
  persist(
    (set, get) => ({
      ...initialState,
      
      // 数据设置
      setPendingReviews: (reviews) => set({ pendingReviews: reviews }),
      setSelectedReview: (review) => set({ selectedReview: review }),
      setStrategyDetail: (detail) => set({ strategyDetail: detail }),
      setReviewHistory: (history) => set({ reviewHistory: history }),
      setAuditRules: (rules) => set({ auditRules: rules }),
      setSystemStatus: (status) => set({ systemStatus: status }),
      setCurrentUser: (user) => set({ currentUser: user }),
      setPagination: (pagination) => set({ pagination }),
      
      // 状态管理
      setLoading: (loading) => set({ isLoading: loading }),
      setSubmitting: (submitting) => set({ isSubmitting: submitting }),
      setError: (error) => set({ error }),
      setFilters: (newFilters) => set((state) => ({
        filters: { ...state.filters, ...newFilters }
      })),
      
      // UI状态
      setSelectedReviewIds: (ids) => set({ selectedReviewIds: ids }),
      toggleReviewSelection: (id) => set((state) => ({
        selectedReviewIds: state.selectedReviewIds.includes(id)
          ? state.selectedReviewIds.filter(reviewId => reviewId !== id)
          : [...state.selectedReviewIds, id]
      })),
      clearSelection: () => set({ selectedReviewIds: [] }),
      setQuickReviewOpen: (open) => set({ isQuickReviewOpen: open }),
      setQuickReviewData: (data) => set({ quickReviewData: data }),
      
      // 业务操作
      updateReviewStatus: (reviewId, status) => set((state) => ({
        pendingReviews: state.pendingReviews.map(review =>
          review.id === reviewId ? { ...review, status, updated_at: new Date().toISOString() } : review
        ),
        selectedReview: state.selectedReview?.id === reviewId
          ? { ...state.selectedReview, status, updated_at: new Date().toISOString() }
          : state.selectedReview
      })),
      
      updateReviewPriority: (reviewId, priority) => set((state) => ({
        pendingReviews: state.pendingReviews.map(review =>
          review.id === reviewId ? { ...review, priority, updated_at: new Date().toISOString() } : review
        )
      })),
      
      addReviewDecision: (decision) => set((state) => ({
        reviewHistory: [decision, ...state.reviewHistory]
      })),
      
      removeReview: (reviewId) => set((state) => ({
        pendingReviews: state.pendingReviews.filter(review => review.id !== reviewId),
        selectedReviewIds: state.selectedReviewIds.filter(id => id !== reviewId)
      })),
      
      batchUpdateReviews: (reviewIds, updates) => set((state) => ({
        pendingReviews: state.pendingReviews.map(review =>
          reviewIds.includes(review.id) 
            ? { ...review, ...updates, updated_at: new Date().toISOString() }
            : review
        )
      })),
      
      // 规则管理
      addAuditRule: (rule) => set((state) => ({
        auditRules: [...state.auditRules, rule]
      })),
      
      updateAuditRule: (ruleId, updates) => set((state) => ({
        auditRules: state.auditRules.map(rule =>
          rule.id === ruleId ? { ...rule, ...updates, updated_at: new Date().toISOString() } : rule
        )
      })),
      
      removeAuditRule: (ruleId) => set((state) => ({
        auditRules: state.auditRules.filter(rule => rule.id !== ruleId)
      })),
      
      toggleRuleActive: (ruleId) => set((state) => ({
        auditRules: state.auditRules.map(rule =>
          rule.id === ruleId ? { ...rule, is_active: !rule.is_active } : rule
        )
      })),
      
      // 工具方法
      getReviewById: (id) => {
        const state = get()
        return state.pendingReviews.find(review => review.id === id)
      },
      
      getReviewsByStatus: (status) => {
        const state = get()
        return state.pendingReviews.filter(review => review.status === status)
      },
      
      getReviewsByRiskLevel: (riskLevel) => {
        const state = get()
        return state.pendingReviews.filter(review => review.risk_level === riskLevel)
      },
      
      getFilteredReviews: () => {
        const state = get()
        const { filters } = state
        let filtered = [...state.pendingReviews]
        
        if (filters.risk_level) {
          filtered = filtered.filter(review => review.risk_level === filters.risk_level)
        }
        
        if (filters.status) {
          filtered = filtered.filter(review => review.status === filters.status)
        }
        
        if (filters.search) {
          const searchLower = filters.search.toLowerCase()
          filtered = filtered.filter(review => 
            review.symbol.toLowerCase().includes(searchLower) ||
            review.strategy_type.toLowerCase().includes(searchLower) ||
            review.id.toLowerCase().includes(searchLower)
          )
        }
        
        return filtered
      },
      
      getReviewStats: () => {
        const state = get()
        const reviews = state.pendingReviews
        
        return {
          total: reviews.length,
          pending: reviews.filter(r => r.status === 'pending').length,
          approved: reviews.filter(r => r.status === 'approved').length,
          rejected: reviews.filter(r => r.status === 'rejected').length,
          deferred: reviews.filter(r => r.status === 'deferred').length,
          high_risk: reviews.filter(r => r.risk_level === 'high').length
        }
      },
      
      // 重置和清理
      clearError: () => set({ error: null }),
      clearCache: () => set({
        pendingReviews: [],
        reviewHistory: [],
        auditRules: [],
        systemStatus: null,
        pagination: null
      }),
      reset: () => set(initialState)
    }),
    {
      name: 'review-store',
      partialize: (state) => ({
        currentUser: state.currentUser,
        filters: state.filters,
        selectedReviewIds: state.selectedReviewIds
      })
    }
  ),
  {
    name: 'review-store'
  }
))