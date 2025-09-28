// API Configuration
export const API_CONFIG = {
  // Base URLs
  BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  WS_BASE_URL: process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8001',
  
  // Backend Module Endpoints
  ENDPOINTS: {
    CORE_SERVICE: process.env.NEXT_PUBLIC_CORE_SERVICE_URL || 'http://localhost:8000/api/core',
    MARKET_SERVICE: process.env.NEXT_PUBLIC_MARKET_SERVICE_URL || 'http://localhost:8001/api/market',
    STRATEGY_SERVICE: process.env.NEXT_PUBLIC_STRATEGY_SERVICE_URL || 'http://localhost:8002/api/strategy',
    RISK_SERVICE: process.env.NEXT_PUBLIC_RISK_SERVICE_URL || 'http://localhost:8003/api/risk',
    AI_SERVICE: process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8004/api/ai',
    REVIEW_SERVICE: process.env.NEXT_PUBLIC_REVIEW_SERVICE_URL || 'http://localhost:8005/api/review',
  },
  
  // WebSocket Endpoints
  WEBSOCKETS: {
    MARKET_DATA: process.env.NEXT_PUBLIC_WS_MARKET_DATA || 'ws://localhost:8001/ws/market',
    SYSTEM_STATUS: process.env.NEXT_PUBLIC_WS_SYSTEM_STATUS || 'ws://localhost:8000/ws/system',
    TRADING_EVENTS: process.env.NEXT_PUBLIC_WS_TRADING_EVENTS || 'ws://localhost:8002/ws/trading',
    RISK_ALERTS: process.env.NEXT_PUBLIC_WS_RISK_ALERTS || 'ws://localhost:8003/ws/risk',
  },
  
  // Authentication
  AUTH: {
    ENABLED: process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true',
    SESSION_TIMEOUT: parseInt(process.env.NEXT_PUBLIC_SESSION_TIMEOUT || '3600000'),
  },
  
  // Development Settings
  DEV: {
    DEBUG_MODE: process.env.NEXT_PUBLIC_DEBUG_MODE === 'true',
    MOCK_DATA: process.env.NEXT_PUBLIC_MOCK_DATA === 'true',
  },
  
  // Request Configuration
  REQUEST: {
    TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
  },
  
  // WebSocket Configuration
  WEBSOCKET: {
    RECONNECT_INTERVAL: 5000,
    MAX_RECONNECT_ATTEMPTS: 10,
    HEARTBEAT_INTERVAL: 30000,
  }
}

// API Route Definitions
export const API_ROUTES = {
  // System Management
  SYSTEM: {
    STATUS: '/system/status',
    START: '/system/start',
    STOP: '/system/stop',
    RESTART: '/system/restart',
    EMERGENCY_STOP: '/system/emergency-stop',
    HEALTH: '/system/health',
    METRICS: '/system/metrics',
  },
  
  // Market Data
  MARKET: {
    REAL_TIME: '/market/realtime',
    HISTORICAL: '/market/historical',
    SYMBOLS: '/market/symbols',
    QUOTES: '/market/quotes',
    DEPTH: '/market/depth',
  },
  
  // Trading Strategies
  STRATEGY: {
    LIST: '/strategies',
    CREATE: '/strategies',
    UPDATE: '/strategies/:id',
    DELETE: '/strategies/:id',
    BACKTEST: '/strategies/:id/backtest',
    DEPLOY: '/strategies/:id/deploy',
    STOP: '/strategies/:id/stop',
  },
  
  // Risk Management
  RISK: {
    ALERTS: '/risk/alerts',
    METRICS: '/risk/metrics',
    LIMITS: '/risk/limits',
    REPORTS: '/risk/reports',
    SETTINGS: '/risk/settings',
  },
  
  // AI Services
  AI: {
    CHAT: '/ai/chat',
    STRATEGY_GENERATE: '/ai/strategy/generate',
    ANALYSIS: '/ai/analysis',
    RECOMMENDATIONS: '/ai/recommendations',
  },
  
  // Review Workflow
  REVIEW: {
    QUEUE: '/review/queue',
    APPROVE: '/review/:id/approve',
    REJECT: '/review/:id/reject',
    COMMENT: '/review/:id/comment',
    HISTORY: '/review/history',
  },
  
  // User Management
  USER: {
    PROFILE: '/user/profile',
    SETTINGS: '/user/settings',
    NOTIFICATIONS: '/user/notifications',
    ACTIVITY: '/user/activity',
  },
  
  // API Key Management
  API_KEYS: {
    LIST: '/api/v1/keys',
    CREATE: '/api/v1/keys',
    GET: '/api/v1/keys/:id',
    UPDATE: '/api/v1/keys/:id',
    DELETE: '/api/v1/keys/:id',
    TEST: '/api/v1/keys/:id/test',
    HEALTH: '/api/v1/keys/health',
  }
}

// Helper function to build full URL
export const buildApiUrl = (service: keyof typeof API_CONFIG.ENDPOINTS, route: string): string => {
  const baseUrl = API_CONFIG.ENDPOINTS[service]
  return `${baseUrl}${route}`
}

// Helper function to build WebSocket URL
export const buildWsUrl = (endpoint: keyof typeof API_CONFIG.WEBSOCKETS): string => {
  return API_CONFIG.WEBSOCKETS[endpoint]
}

// Helper function to replace route parameters
export const replaceRouteParams = (route: string, params: Record<string, string | number>): string => {
  let result = route
  Object.entries(params).forEach(([key, value]) => {
    result = result.replace(`:${key}`, String(value))
  })
  return result
}