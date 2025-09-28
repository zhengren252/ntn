'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Users, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Bot,
  BarChart3,
  Shield,
  Zap
} from 'lucide-react'
import { useSystemStore } from '@/store'
import { cn } from '@/lib/utils'
import MonitoringPanel from '@/components/MonitoringPanel'
import ReviewWorkflow from '@/components/ReviewWorkflow'
import AIInterface from '@/components/AIInterface'

// 模拟实时数据
const mockMarketData = {
  btc: { price: 43250.50, change: 2.34, volume: '1.2B' },
  eth: { price: 2580.75, change: -1.23, volume: '890M' },
  bnb: { price: 315.20, change: 0.89, volume: '245M' }
}

const mockSystemStatus = {
  modules: [
    { name: 'API工厂', status: 'running', uptime: '99.9%' },
    { name: '扫描器', status: 'running', uptime: '98.7%' },
    { name: '策略优化', status: 'warning', uptime: '95.2%' },
    { name: '交易员', status: 'running', uptime: '99.5%' },
    { name: '风控', status: 'running', uptime: '100%' },
    { name: 'MMS', status: 'stopped', uptime: '0%' }
  ],
  totalTrades: 1247,
  successRate: 94.2,
  totalProfit: 15420.50
}

export default function Home() {
  const { isSystemRunning, notifications, addNotification } = useSystemStore()
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-600'
      case 'warning': return 'text-yellow-600'
      case 'stopped': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <CheckCircle className="h-4 w-4" />
      case 'warning': return <AlertTriangle className="h-4 w-4" />
      case 'stopped': return <XCircle className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  return (
    <main id="main-content" role="main" className="layout main-content p-6 space-y-6 w-full max-w-full overflow-x-hidden [&_button]:min-h-[44px] [&_button]:min-w-[44px]" data-testid="main-content">
      <div className="container mx-auto px-4 main-container content" data-testid="dashboard-root">
        {/* 系统状态头部 */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">ASTS 智能交易控制台</h1>
            <p className="text-gray-600 mt-1">
              系统时间: {currentTime.toLocaleString('zh-CN')}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <Badge 
              variant={isSystemRunning ? "default" : "destructive"}
              className="px-3 py-1"
              data-testid="system-status-badge"
            >
              {isSystemRunning ? '系统运行中' : '系统已停止'}
            </Badge>
            <Button 
              variant={isSystemRunning ? "destructive" : "default"}
              onClick={() => {
                // 这里会连接到实际的系统控制API
                addNotification({
                  type: isSystemRunning ? 'warning' : 'success',
                  title: isSystemRunning ? '系统停止' : '系统启动',
                  message: isSystemRunning ? '交易系统已停止运行' : '交易系统已启动运行'
                })
              }}
              data-testid="system-control-btn"
            >
              {isSystemRunning ? '停止系统' : '启动系统'}
            </Button>
          </div>
        </div>

        {/* 主要内容区域 */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview" data-testid="tab-overview">总览</TabsTrigger>
            <TabsTrigger value="monitoring" data-testid="tab-monitoring">实时监控</TabsTrigger>
            <TabsTrigger value="review" data-testid="tab-review">人工审核</TabsTrigger>
            <TabsTrigger value="ai-lab" data-testid="tab-ai-lab">AI实验室</TabsTrigger>
            <TabsTrigger value="risk" data-testid="tab-risk">风控中心</TabsTrigger>
          </TabsList>

          {/* 总览页面 */}
          <TabsContent value="overview" className="space-y-6">
            {/* 主图表区域（最小侵入：为E2E提供可伸展的首个图表元素） */}
            <div
              className="chart w-full min-h-[360px] md:min-h-[420px] bg-muted rounded"
              data-testid="primary-chart"
              aria-label="Overview Primary Chart"
            >
              <svg role="img" aria-label="Overview Chart" className="w-full h-full block" />
            </div>

            {/* 关键指标卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card data-testid="card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">总交易次数</CardTitle>
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold" data-testid="metric-total-trades">{mockSystemStatus.totalTrades}</div>
                  <p className="text-xs text-muted-foreground">+12% 较昨日</p>
                </CardContent>
              </Card>

              <Card data-testid="card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">成功率</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold" data-testid="metric-success-rate">{mockSystemStatus.successRate}%</div>
                  <p className="text-xs text-muted-foreground">+2.1% 较昨日</p>
                </CardContent>
              </Card>

              <Card data-testid="card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">总收益</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold" data-testid="metric-total-profit">${mockSystemStatus.totalProfit}</div>
                  <p className="text-xs text-muted-foreground">+8.2% 较昨日</p>
                </CardContent>
              </Card>

              <Card data-testid="card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">活跃模块</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold" data-testid="metric-active-modules">
                    {mockSystemStatus.modules.filter(m => m.status === 'running').length}/
                    {mockSystemStatus.modules.length}
                  </div>
                  <p className="text-xs text-muted-foreground">系统模块状态</p>
                </CardContent>
              </Card>
            </div>

            {/* 市场数据和系统状态 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 市场数据 */}
              <Card>
                <CardHeader>
                  <CardTitle>实时市场数据</CardTitle>
                  <CardDescription>主要加密货币价格动态</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {Object.entries(mockMarketData).map(([symbol, data]) => (
                    <div key={symbol} className="flex items-center justify-between" data-testid={`market-row-${symbol}`}>
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                          <span className="text-sm font-bold text-orange-600">
                            {symbol.toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium">${data.price.toLocaleString()}</p>
                          <p className="text-sm text-gray-500">Vol: {data.volume}</p>
                        </div>
                      </div>
                      <div className={cn(
                        "flex items-center space-x-1",
                        data.change >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {data.change >= 0 ? 
                          <TrendingUp className="h-4 w-4" /> : 
                          <TrendingDown className="h-4 w-4" />
                        }
                        <span className="font-medium">
                          {data.change >= 0 ? '+' : ''}{data.change}%
                        </span>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* 系统模块状态 */}
              <Card>
                <CardHeader>
                  <CardTitle>系统模块状态</CardTitle>
                  <CardDescription>各核心模块运行状态监控</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {mockSystemStatus.modules.map((module, index) => (
                    <div key={index} className="flex items-center justify-between" data-testid={`module-row-${index}`}>
                      <div className="flex items-center space-x-3">
                        <div className={cn("flex items-center", getStatusColor(module.status))}>
                          {getStatusIcon(module.status)}
                        </div>
                        <div>
                          <p className="font-medium">{module.name}</p>
                          <p className="text-sm text-gray-500">运行时间: {module.uptime}</p>
                        </div>
                      </div>
                      <Badge 
                        variant={module.status === 'running' ? 'default' : 
                                module.status === 'warning' ? 'secondary' : 'destructive'}
                      >
                        {module.status === 'running' ? '运行中' :
                         module.status === 'warning' ? '警告' : '已停止'}
                      </Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* 实时监控页面 */}
          <TabsContent value="monitoring">
            <MonitoringPanel />
          </TabsContent>

          {/* 人工审核页面 */}
          <TabsContent value="review">
            <ReviewWorkflow />
          </TabsContent>

          {/* AI实验室页面 */}
          <TabsContent value="ai-lab">
            <AIInterface />
          </TabsContent>

          {/* 风控中心页面 */}
          <TabsContent value="risk">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>风控中心</span>
                </CardTitle>
                <CardDescription>
                  风险监控、预警系统、风控策略管理
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">风控中心开发中...</p>
                  <p className="text-sm text-gray-400 mt-2">
                    将包含风险评估、预警系统、风控策略配置
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  )
}
