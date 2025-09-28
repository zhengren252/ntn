import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios, { AxiosResponse, AxiosError } from 'axios'
import { useSystemStore } from '@/store'
import type {
  ApiResponse,
  Strategy,
  StrategyBacktestParams,
  AILabChatParams,
  TradingRecord,
  BudgetUpdateData,
  StrategyReviewData,
  ScenarioData,
  StressTestData,
  ImportModuleData,
  ExportModuleData,
  RehearsalReport
} from '@/lib/types'
import { 
  ModuleConfig,
  TradingHistoryParams,
  PerformanceAnalysisParams,
  ChartDataParams,
  CreateReplayData,
  CreateBudgetData,
  ExportCostReportParams,
  CreateScenarioData,
  RunScenarioParams,
  ModuleDependency,
  PerformanceData
} from '@/lib/types'

// API基础配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001'

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      // 处理认证失败
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API接口类型定义

export interface SystemStatus {
  isRunning: boolean
  modules: ModuleStatus[]
  uptime: number
  version: string
}

export interface ModuleStatus {
  name: string
  status: 'running' | 'stopped' | 'error' | 'warning'
  uptime: string
  lastUpdate: string
  metrics?: Record<string, number | string | boolean>
}

export interface MarketData {
  symbol: string
  price: number
  change: number
  volume: string
  timestamp: number
}

export interface TradingStrategy {
  id: string
  name: string
  description: string
  status: 'pending' | 'approved' | 'rejected' | 'active' | 'inactive' | 'pending_review'
  performance: {
    totalTrades: number
    successRate: number
    profit: number
    drawdown: number
  }
  createdAt: string
  updatedAt: string
  submittedAt?: string
  submittedBy?: string
  riskLevel?: 'low' | 'medium' | 'high'
  expectedReturn?: number
  maxDrawdown?: number
  parameters: Record<string, unknown>
}

export interface RiskAlert {
  id: string
  type: 'high' | 'medium' | 'low'
  title: string
  description: string
  module: string
  timestamp: string
  resolved: boolean
}

export interface DashboardOverview {
  totalProfit: number
  profitChange: number
  activeStrategies: number
  strategiesChange: number
  successRate: number
  successRateChange: number
  systemStatus: string
}

export interface DashboardChart {
  timestamps: string[]
  cumulativeProfit: number[]
  dailyProfit: number[]
}

// API端点常量
export const API_ENDPOINTS = {
  // 系统管理
  SYSTEM_STATUS: '/api/system/status',
  SYSTEM_START: '/api/system/start',
  SYSTEM_STOP: '/api/system/stop',
  SYSTEM_RESTART: '/api/system/restart',
  
  // 仪表盘数据
  DASHBOARD_OVERVIEW: '/api/dashboard/overview',
  DASHBOARD_CHART: '/api/dashboard/chart',
  
  // 模块管理
  MODULES: '/api/modules',
  MODULE_STATUS: (moduleId: string) => `/api/modules/${moduleId}/status`,
  MODULE_START: (moduleId: string) => `/api/modules/${moduleId}/start`,
  MODULE_STOP: (moduleId: string) => `/api/modules/${moduleId}/stop`,
  
  // 市场数据
  MARKET_DATA: '/api/market/data',
  MARKET_HISTORY: '/api/market/history',
  
  // 交易策略
  STRATEGIES: '/api/strategies',
  STRATEGIES_PENDING: '/api/reviews/pending', // 修正为复数形式
  STRATEGY_DETAIL: (strategyId: string) => `/api/strategies/${strategyId}`,
  STRATEGY_BACKTEST: '/api/strategies/backtest',
  STRATEGY_DEPLOY: (strategyId: string) => `/api/strategies/${strategyId}/deploy`,
  
  // 风险管理
  RISK_ALERTS: '/api/risk/alerts',
  RISK_METRICS: '/api/risk/metrics',
  RISK_SETTINGS: '/api/risk/settings',
  
  // AI服务
  AI_CHAT: '/api/ai/chat',
  AI_STRATEGY_GENERATE: '/api/ai/strategy/generate',
  AI_ANALYSIS: '/api/ai/analysis',
  
  // 审核工作流
  REVIEW_QUEUE: '/api/review/queue',
  REVIEW_APPROVE: (reviewId: string) => `/api/review/${reviewId}/approve`,
  REVIEW_REJECT: (reviewId: string) => `/api/review/${reviewId}/reject`,
  REVIEW_DECISION: (reviewId: string) => `/api/reviews/${reviewId}/decision`, // 新增统一决策端点
} as const

// 系统状态相关hooks
export const useSystemStatus = () => {
  return useQuery<ApiResponse<SystemStatus>>({
    queryKey: ['systemStatus'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.SYSTEM_STATUS)
      return response.data
    },
    refetchInterval: 5000, // 每5秒刷新一次
  })
}

export const useSystemControl = () => {
  const queryClient = useQueryClient()
  const { addNotification } = useSystemStore()
  
  const startSystem = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(API_ENDPOINTS.SYSTEM_START)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemStatus'] })
      addNotification({
        type: 'success',
        title: '系统启动成功',
        message: '交易系统已成功启动'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '系统启动失败',
        message: error.message
      })
    }
  })
  
  const stopSystem = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post(API_ENDPOINTS.SYSTEM_STOP)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemStatus'] })
      addNotification({
        type: 'warning',
        title: '系统已停止',
        message: '交易系统已安全停止'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '系统停止失败',
        message: error.message
      })
    }
  })
  
  return { startSystem, stopSystem }
}

// 仪表盘数据相关hooks
export const useDashboardOverview = () => {
  return useQuery<ApiResponse<DashboardOverview>>({
    queryKey: ['dashboardOverview'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.DASHBOARD_OVERVIEW)
      return response.data
    },
    refetchInterval: 5000, // 每5秒刷新一次
  })
}

export const useDashboardChart = (timeRange: string) => {
  return useQuery<ApiResponse<DashboardChart>>({
    queryKey: ['dashboardChart', timeRange],
    queryFn: async () => {
      const response = await apiClient.get(`${API_ENDPOINTS.DASHBOARD_CHART}?timeRange=${timeRange}`)
      return response.data
    },
    refetchInterval: 10000, // 每10秒刷新一次
  })
}

// 市场数据相关hooks
export const useMarketData = () => {
  return useQuery<ApiResponse<MarketData[]>>({
    queryKey: ['marketData'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.MARKET_DATA)
      return response.data
    },
    refetchInterval: 2000, // 每2秒刷新一次
  })
}

// 交易策略相关hooks
export const useStrategies = () => {
  return useQuery<ApiResponse<TradingStrategy[]>>({
    queryKey: ['strategies'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.STRATEGIES)
      return response.data
    },
  })
}

export const useStrategy = (strategyId: string) => {
  return useQuery<ApiResponse<TradingStrategy>>({
    queryKey: ['strategy', strategyId],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.STRATEGY_DETAIL(strategyId))
      return response.data
    },
    enabled: !!strategyId,
  })
}

export const useStrategyBacktest = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (params: StrategyBacktestParams) => {
      const response = await apiClient.post(API_ENDPOINTS.STRATEGY_BACKTEST, params)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '回测完成',
        message: '策略回测已成功完成'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '回测失败',
        message: error.message
      })
    }
  })
}

// 风险管理相关hooks
export const useRiskAlerts = () => {
  return useQuery<ApiResponse<RiskAlert[]>>({
    queryKey: ['riskAlerts'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.RISK_ALERTS)
      return response.data
    },
    refetchInterval: 10000, // 每10秒刷新一次
  })
}

// AI服务相关hooks
export const useAIChat = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (message: string) => {
      const response = await apiClient.post(API_ENDPOINTS.AI_CHAT, { message })
      return response.data
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: 'AI对话失败',
        message: error.message
      })
    }
  })
}

// AI实验室相关hooks
export const useAiLabSession = () => {
  return useQuery<ApiResponse<{ sessionId: string; status: string; createdAt: string }>>({
    queryKey: ['aiLabSession'],
    queryFn: async () => {
      const response = await apiClient.get('/api/ai-lab/session')
      return response.data
    },
    refetchInterval: 10000
  })
}

export const useAiLabChat = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ message, sessionId }: AILabChatParams) => {
      const response = await apiClient.post('/api/ai-lab/chat', { message, sessionId })
      return response.data
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: 'AI实验室对话失败',
        message: error.message
      })
    }
  })
}

// API成本管理相关hooks
export const useBudgetManager = () => {
  return useQuery<ApiResponse<{ totalBudget: number; usedBudget: number; remainingBudget: number; alerts: Array<{ type: string; message: string }> }>>({
    queryKey: ['budgetManager'],
    queryFn: async () => {
      const response = await apiClient.get('/api/budget/manager')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useUpdateBudget = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (budgetData: BudgetUpdateData) => {
      const response = await apiClient.put('/api/budget/update', budgetData)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '预算更新成功',
        message: '预算配置已成功更新'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '预算更新失败',
        message: error.message
      })
    }
  })
}

export const useCostAnalytics = () => {
  return useQuery<ApiResponse<{ totalCost: number; costByModule: Record<string, number>; trends: Array<{ date: string; cost: number }> }>>({
    queryKey: ['costAnalytics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/cost/analytics')
      return response.data
    },
    refetchInterval: 60000
  })
}

export const useCostStatistics = () => {
  return useQuery<ApiResponse<{ dailyCost: number; monthlyCost: number; averageCost: number; costBreakdown: Record<string, number> }>>({
    queryKey: ['costStatistics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/cost/statistics')
      return response.data
    },
    refetchInterval: 30000
  })
}

// 监控相关hooks
export const useModuleStatus = () => {
  return useQuery<ApiResponse<ModuleStatus[]>>({
    queryKey: ['moduleStatus'],
    queryFn: async () => {
      const response = await apiClient.get('/api/monitoring/modules')
      return response.data
    },
    refetchInterval: 5000
  })
}

export const useSystemMetrics = () => {
  return useQuery<ApiResponse<{
    cpu: {
      usage: number;
      cores: number;
      frequency: number;
      temperature: number;
    };
    memory: {
      used: number;
      total: number;
      percentage: number;
    };
    disk: {
      used: number;
      total: number;
      percentage: number;
    };
    network: {
      status: string;
      latency: number;
      downloadSpeed: number;
      uploadSpeed: number;
    };
    power?: {
      consumption: number;
      efficiency: number;
    };
    uptime: number;
  }>>({
    queryKey: ['systemMetrics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/monitoring/metrics')
      return response.data
    },
    refetchInterval: 10000
  })
}

// 审核相关hooks
export const useReviewStats = () => {
  return useQuery<ApiResponse<{ pending: number; approved: number; rejected: number; total: number }>>({
    queryKey: ['reviewStats'],
    queryFn: async () => {
      const response = await apiClient.get('/api/review/stats')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useStrategyReview = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (reviewData: StrategyReviewData) => {
      const response = await apiClient.post('/api/review/strategy', reviewData)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '策略审核完成',
        message: '策略审核已成功提交'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '策略审核失败',
        message: error.message
      })
    }
  })
}

// 风险演练相关hooks
export const useRehearsalReports = () => {
  return useQuery<ApiResponse<RehearsalReport[]>>({
    queryKey: ['rehearsalReports'],
    queryFn: async () => {
      const response = await apiClient.get('/api/risk-rehearsal/reports')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useExportReport = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ reportId, format }: { reportId: string; format: 'pdf' | 'excel' }) => {
      const response = await apiClient.post('/api/risk-rehearsal/export', { reportId, format })
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '报告导出成功',
        message: '风险演练报告已成功导出'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '报告导出失败',
        message: error.message
      })
    }
  })
}

export const useScenarioSimulation = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (scenarioData: ScenarioData) => {
      const response = await apiClient.post('/api/risk-rehearsal/scenario', scenarioData)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '场景模拟启动',
        message: '风险场景模拟已成功启动'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '场景模拟失败',
        message: error.message
      })
    }
  })
}

export const useStressTesting = () => {
  return useQuery<ApiResponse<Array<{ id: string; name: string; status: string; progress: number; results?: Record<string, unknown> }>>>({
    queryKey: ['stressTesting'],
    queryFn: async () => {
      const response = await apiClient.get('/api/risk-rehearsal/stress-tests')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useCreateStressTest = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (testData: StressTestData) => {
      const response = await apiClient.post('/api/risk-rehearsal/stress-test/create', testData)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '压力测试创建成功',
        message: '压力测试配置已成功创建'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '压力测试创建失败',
        message: error.message
      })
    }
  })
}

export const useRunStressTest = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (testId: string) => {
      const response = await apiClient.post(`/api/risk-rehearsal/stress-test/${testId}/run`)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '压力测试运行',
        message: '压力测试已开始运行'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '压力测试运行失败',
        message: error.message
      })
    }
  })
}

export const useStressTests = () => {
  return useQuery<ApiResponse<Array<{ id: string; name: string; status: string; createdAt: string; results?: Record<string, unknown> }>>>({
    queryKey: ['stressTests'],
    queryFn: async () => {
      const response = await apiClient.get('/api/risk-rehearsal/stress-tests')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useRiskScenarios = () => {
  return useQuery<ApiResponse<Array<{ id: string; name: string; description: string; parameters: Record<string, unknown>; status: string }>>>({
    queryKey: ['riskScenarios'],
    queryFn: async () => {
      const response = await apiClient.get('/api/risk-rehearsal/scenarios')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useCreateScenario = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (scenarioData: CreateScenarioData) => {
      const response = await apiClient.post('/api/risk-rehearsal/scenarios', scenarioData)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '场景创建成功',
        message: '风险场景已成功创建'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '场景创建失败',
        message: error.message
      })
    }
  })
}

export const useRunScenario = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ scenarioId, params }: { scenarioId: string; params: RunScenarioParams }) => {
      const response = await apiClient.post(`/api/risk-rehearsal/scenarios/${scenarioId}/run`, params)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '场景运行',
        message: '风险场景已开始运行'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '场景运行失败',
        message: error.message
      })
    }
  })
}

// 交易复盘相关hooks
export const usePerformanceAnalysis = () => {
  return useQuery<ApiResponse<PerformanceData>>({
    queryKey: ['performanceAnalysis'],
    queryFn: async () => {
      const response = await apiClient.get('/api/trading-replay/performance')
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useTradingHistory = (params?: { search?: string; status?: string; type?: string; dateRange?: string }) => {
  return useQuery<ApiResponse<TradingRecord[]>>({
    queryKey: ['tradingHistory', params],
    queryFn: async () => {
      let url = '/api/trading-replay/history'
      if (params) {
        const queryParams = new URLSearchParams()
        if (params.search) queryParams.append('search', params.search)
        if (params.status) queryParams.append('status', params.status)
        if (params.type) queryParams.append('type', params.type)
        if (params.dateRange) queryParams.append('dateRange', params.dateRange)
        if (queryParams.toString()) {
          url += `?${queryParams.toString()}`
        }
      }
      const response = await apiClient.get(url)
      return response.data
    },
    refetchInterval: 30000
  })
}

export const useTradingViewChart = () => {
  return useQuery<ApiResponse<{ symbol: string; data: Array<{ time: number; open: number; high: number; low: number; close: number; volume: number }> }>>({
    queryKey: ['tradingViewChart'],
    queryFn: async () => {
      const response = await apiClient.get('/api/trading-replay/chart')
      return response.data
    },
    refetchInterval: 30000
  })
}

// 图表数据相关hooks
export const useChartData = (params?: { symbol?: string; timeframe?: string; timeRange?: string }) => {
  return useQuery<ApiResponse<{ labels: string[]; datasets: Array<{ label: string; data: number[]; borderColor: string; backgroundColor: string }> }>>({
    queryKey: ['chartData', params],
    queryFn: async () => {
      let url = '/api/chart/data'
      if (params) {
        const queryParams = new URLSearchParams()
        if (params.symbol) queryParams.append('symbol', params.symbol)
        if (params.timeframe) queryParams.append('timeframe', params.timeframe)
        if (params.timeRange) queryParams.append('timeRange', params.timeRange)
        if (queryParams.toString()) {
          url += `?${queryParams.toString()}`
        }
      }
      const response = await apiClient.get(url)
      return response.data
    },
    refetchInterval: 10000
  })
}

interface StrategyGenerationParams {
  marketType: string
  riskLevel: string
  timeframe: string
  targetReturn: number
  maxDrawdown: number
  description: string
}

export const useAIStrategyGenerate = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (params: StrategyGenerationParams) => {
      const response = await apiClient.post(API_ENDPOINTS.AI_STRATEGY_GENERATE, params)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: 'AI策略生成成功',
        message: '新的交易策略已生成，请查看详情'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: 'AI策略生成失败',
        message: error.message
      })
    }
  })
}

// 审核工作流相关hooks
export const useReviewQueue = () => {
  return useQuery<ApiResponse<Array<{ id: string; type: string; title: string; status: string; createdAt: string; priority: string }>>>({
    queryKey: ['reviewQueue'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.REVIEW_QUEUE)
      return response.data
    },
    refetchInterval: 30000, // 每30秒刷新一次
  })
}

export const useReviewActions = () => {
  const queryClient = useQueryClient()
  const { addNotification } = useSystemStore()
  
  const approveReview = useMutation({
    mutationFn: async ({ reviewId, action, comment }: { reviewId: string; action: 'approve' | 'reject' | 'request_changes'; comment?: string }) => {
      const response = await apiClient.post(`/api/review/${reviewId}/action`, { action, comment })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] })
      addNotification({
        type: 'success',
        title: '审核通过',
        message: '项目已通过审核'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '审核操作失败',
        message: error.message
      })
    }
  })
  
  const rejectReview = useMutation({
    mutationFn: async ({ reviewId, reason }: { reviewId: string; reason: string }) => {
      const response = await apiClient.post(API_ENDPOINTS.REVIEW_REJECT(reviewId), { reason })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] })
      addNotification({
        type: 'warning',
        title: '审核拒绝',
        message: '项目已被拒绝'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '审核操作失败',
        message: error.message
      })
    }
  })
  
  return { approveReview, rejectReview }
}

// 新的统一审核决策钩子
export const usePostReviewDecision = () => {
  const queryClient = useQueryClient()
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ reviewId, decision, comments }: { reviewId: string; decision: 'approve' | 'reject'; comments?: string }) => {
      const response = await apiClient.post(API_ENDPOINTS.REVIEW_DECISION(reviewId), { decision, comments })
      return response.data
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] })
      queryClient.invalidateQueries({ queryKey: ['pendingStrategies'] })
      const isApproved = variables.decision === 'approve'
      addNotification({
        type: isApproved ? 'success' : 'warning',
        title: isApproved ? '策略审核通过' : '策略审核拒绝',
        message: isApproved ? '策略已通过审核' : '策略已被拒绝'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '策略审核失败',
        message: error.message
      })
    }
  })
}

// 保持原有钩子以确保向后兼容
export const useApproveStrategy = () => {
  const postReviewDecision = usePostReviewDecision()
  
  return {
    ...postReviewDecision,
    mutateAsync: async ({ strategyId, approved }: { strategyId: string; approved: boolean }) => {
      return postReviewDecision.mutateAsync({
        reviewId: strategyId,
        decision: approved ? 'approve' : 'reject'
      })
    }
  }
}

// 待审核策略相关hooks
export const usePendingStrategies = () => {
  return useQuery<ApiResponse<Strategy[]>>({
    queryKey: ['pendingStrategies'],
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.STRATEGIES_PENDING)
      return response.data
    },
    refetchInterval: 30000, // 每30秒刷新一次
  })
}

// 导出回放数据相关hooks
export const useExportReplay = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ replayId, format, includeMetadata }: { replayId: string; format: 'json' | 'csv' | 'excel'; includeMetadata: boolean }) => {
      const response = await apiClient.post('/api/replay/export', { replayId, format, includeMetadata })
      return response.data
    },
    onSuccess: (data) => {
      addNotification({
        type: 'success',
        title: '数据导出成功',
        message: '回放数据已成功导出'
      })
      // 处理文件下载
      if (data.downloadUrl) {
        const link = document.createElement('a')
        link.href = data.downloadUrl
        link.download = data.filename || 'replay_data'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '数据导出失败',
        message: error.message || '导出过程中发生错误'
      })
    }
  })
}

// 模块管理相关hooks
export const useUpdateModuleConfig = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ moduleId, config }: { moduleId: string; config: ModuleConfig }) => {
      const response = await apiClient.put(`/api/modules/${moduleId}/config`, config)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '配置更新成功',
        message: '模块配置已成功更新'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '配置更新失败',
        message: error.message || '更新配置时发生错误'
      })
    }
  })
}

export const useModuleDependencies = (moduleId: string | null) => {
  return useQuery<ApiResponse<ModuleDependency[]>>({
    queryKey: ['moduleDependencies', moduleId],
    queryFn: async () => {
      if (!moduleId) return { data: [] }
      const response = await apiClient.get(`/api/modules/${moduleId}/dependencies`)
      return response.data
    },
    enabled: !!moduleId
  })
}

export const useInstallDependency = () => {
  const queryClient = useQueryClient()
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ moduleId, dependency }: { moduleId: string | null; dependency: { name: string; version: string } }) => {
      if (!moduleId) throw new Error('Module ID is required')
      const response = await apiClient.post(`/api/modules/${moduleId}/dependencies`, dependency)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['moduleDependencies', variables.moduleId] })
      addNotification({
        type: 'success',
        title: '依赖安装成功',
        message: '依赖包已成功安装'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '依赖安装失败',
        message: error.message || '安装依赖时发生错误'
      })
    }
  })
}

export const useRemoveDependency = () => {
  const queryClient = useQueryClient()
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async ({ moduleId, dependencyId }: { moduleId: string | null; dependencyId: string }) => {
      if (!moduleId) throw new Error('Module ID is required')
      const response = await apiClient.delete(`/api/modules/${moduleId}/dependencies/${dependencyId}`)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['moduleDependencies', variables.moduleId] })
      addNotification({
        type: 'success',
        title: '依赖移除成功',
        message: '依赖包已成功移除'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '依赖移除失败',
        message: error.message || '移除依赖时发生错误'
      })
    }
  })
}

export const useModuleTemplates = () => {
  return useQuery({
    queryKey: ['moduleTemplates'],
    queryFn: async () => {
      const response = await apiClient.get('/api/modules/templates')
      return response.data
    }
  })
}

export const useImportModule = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (data: ImportModuleData) => {
      const response = await apiClient.post('/api/modules/import', data)
      return response.data
    },
    onSuccess: () => {
      addNotification({
        type: 'success',
        title: '模块导入成功',
        message: '模块已成功导入'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '模块导入失败',
        message: error.message || '导入模块时发生错误'
      })
    }
  })
}

export const useExportModule = () => {
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (data: ExportModuleData) => {
      const response = await apiClient.post('/api/modules/export', data)
      return response.data
    },
    onSuccess: (data) => {
      addNotification({
        type: 'success',
        title: '模块导出成功',
        message: '模块已成功导出'
      })
      // 处理文件下载
      if (data.downloadUrl) {
        const link = document.createElement('a')
        link.href = data.downloadUrl
        link.download = data.filename || 'module_export'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '模块导出失败',
        message: error.message || '导出模块时发生错误'
      })
    }
  })
}

export const useRestartModule = () => {
  const queryClient = useQueryClient()
  const { addNotification } = useSystemStore()
  
  return useMutation({
    mutationFn: async (moduleId: string) => {
      const response = await apiClient.post(`/api/modules/${moduleId}/restart`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moduleStatus'] })
      queryClient.invalidateQueries({ queryKey: ['systemStatus'] })
      addNotification({
        type: 'success',
        title: '模块重启成功',
        message: '模块已成功重启'
      })
    },
    onError: (error: AxiosError) => {
      addNotification({
        type: 'error',
        title: '模块重启失败',
        message: error.message || '重启模块时发生错误'
      })
    }
  })
}

// 导出axios实例供其他地方使用
export { apiClient }
