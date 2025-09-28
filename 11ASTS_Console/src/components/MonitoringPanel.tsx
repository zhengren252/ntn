import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Clock,
  DollarSign,
  BarChart3,
  Zap,
  Server,
  Wifi,
  WifiOff
} from 'lucide-react'
import { useSystemStatus, useMarketData, useRiskAlerts } from '@/hooks/useApi'
import { useWebSocket } from '@/hooks/useWebSocket'
import { cn } from '@/lib/utils'

interface MonitoringPanelProps {
  className?: string
}

export const MonitoringPanel: React.FC<MonitoringPanelProps> = ({ className }) => {
  // API数据获取
  const { data: systemStatus, isLoading: systemLoading } = useSystemStatus()
  const { data: marketData, isLoading: marketLoading } = useMarketData()
  const { data: riskAlerts, isLoading: alertsLoading } = useRiskAlerts()
  
  // WebSocket连接
  const { 
    isConnected: wsConnected, 
    data: wsData, 
    connectionState 
  } = useWebSocket({
    url: 'ws://localhost:8001/ws/monitoring',
    reconnectInterval: 3000,
    maxReconnectAttempts: 5
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
      case 'active':
        return 'text-green-500'
      case 'warning':
        return 'text-yellow-500'
      case 'error':
      case 'stopped':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'error':
      case 'stopped':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 2
    }).format(value)
  }

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* WebSocket连接状态 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold">实时连接状态</CardTitle>
            <div className="flex items-center space-x-2">
              {wsConnected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500" />
                  <Badge variant="outline" className="text-green-600 border-green-200">
                    已连接
                  </Badge>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-red-500" />
                  <Badge variant="outline" className="text-red-600 border-red-200">
                    {connectionState === 'connecting' ? '连接中...' : '连接断开'}
                  </Badge>
                </>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      <Tabs defaultValue="system" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="system">系统状态</TabsTrigger>
          <TabsTrigger value="market">市场数据</TabsTrigger>
          <TabsTrigger value="trading">交易执行</TabsTrigger>
          <TabsTrigger value="risk">风险监控</TabsTrigger>
        </TabsList>

        {/* 系统状态面板 */}
        <TabsContent value="system" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* 系统总览 */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">系统状态</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center space-x-2">
                  {systemLoading ? (
                    <div className="animate-pulse flex space-x-2">
                      <div className="rounded-full bg-gray-200 h-4 w-4"></div>
                      <div className="h-4 bg-gray-200 rounded w-16"></div>
                    </div>
                  ) : (
                    <>
                      {getStatusIcon(systemStatus?.data?.isRunning ? 'running' : 'stopped')}
                      <span className={cn(
                        'text-sm font-medium',
                        getStatusColor(systemStatus?.data?.isRunning ? 'running' : 'stopped')
                      )}>
                        {systemStatus?.data?.isRunning ? '运行中' : '已停止'}
                      </span>
                    </>
                  )}
                </div>
                {systemStatus?.data && (
                  <div className="mt-2 text-xs text-gray-500">
                    运行时间: {Math.floor(systemStatus.data.uptime / 3600)}小时
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 模块状态 */}
            <Card className="md:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">模块状态</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {systemStatus?.data?.modules?.map((module, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded-lg bg-gray-50">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(module.status)}
                        <span className="text-sm font-medium">{module.name}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge 
                          variant={module.status === 'running' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {module.status}
                        </Badge>
                        <span className="text-xs text-gray-500">{module.uptime}</span>
                      </div>
                    </div>
                  )) || (
                    <div className="text-sm text-gray-500 text-center py-4">
                      暂无模块数据
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 系统性能指标 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center">
                <Activity className="h-5 w-5 mr-2" />
                系统性能
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>CPU使用率</span>
                    <span>65%</span>
                  </div>
                  <Progress value={65} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>内存使用率</span>
                    <span>42%</span>
                  </div>
                  <Progress value={42} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>网络延迟</span>
                    <span>12ms</span>
                  </div>
                  <Progress value={12} className="h-2" />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 市场数据面板 */}
        <TabsContent value="market" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {marketData?.data?.map((item, index) => (
              <Card key={index}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{item.symbol}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    <div className="text-2xl font-bold">
                      {formatCurrency(item.price)}
                    </div>
                    <div className={cn(
                      'flex items-center text-sm',
                      item.change >= 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {item.change >= 0 ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {formatPercentage(item.change)}
                    </div>
                    <div className="text-xs text-gray-500">
                      成交量: {item.volume}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )) || (
              <div className="col-span-full text-center py-8 text-gray-500">
                {marketLoading ? '加载中...' : '暂无市场数据'}
              </div>
            )}
          </div>
        </TabsContent>

        {/* 交易执行面板 */}
        <TabsContent value="trading" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <DollarSign className="h-4 w-4 mr-2" />
                  今日收益
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">+¥12,345</div>
                <div className="text-sm text-gray-500">+2.34%</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <BarChart3 className="h-4 w-4 mr-2" />
                  交易次数
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">156</div>
                <div className="text-sm text-gray-500">成功率: 78%</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center">
                  <Zap className="h-4 w-4 mr-2" />
                  执行延迟
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">23ms</div>
                <div className="text-sm text-gray-500">平均延迟</div>
              </CardContent>
            </Card>
          </div>

          {/* 最近交易 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg font-semibold">最近交易</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((_, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                    <div className="flex items-center space-x-3">
                      <Badge variant="outline" className="text-green-600 border-green-200">
                        买入
                      </Badge>
                      <span className="font-medium">AAPL</span>
                      <span className="text-sm text-gray-500">100股</span>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">¥150.25</div>
                      <div className="text-xs text-gray-500">14:32:15</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 风险监控面板 */}
        <TabsContent value="risk" className="space-y-4">
          {/* 风险警报 */}
          <div className="space-y-3">
            {riskAlerts?.data?.map((alert, index) => (
              <Alert key={index} className={cn(
                alert.type === 'high' && 'border-red-200 bg-red-50',
                alert.type === 'medium' && 'border-yellow-200 bg-yellow-50',
                alert.type === 'low' && 'border-blue-200 bg-blue-50'
              )}>
                <AlertTriangle className={cn(
                  'h-4 w-4',
                  alert.type === 'high' && 'text-red-500',
                  alert.type === 'medium' && 'text-yellow-500',
                  alert.type === 'low' && 'text-blue-500'
                )} />
                <AlertTitle className="flex items-center justify-between">
                  <span>{alert.title}</span>
                  <Badge variant={alert.type === 'high' ? 'destructive' : 'secondary'}>
                    {alert.type}
                  </Badge>
                </AlertTitle>
                <AlertDescription>
                  <div className="mt-1">{alert.description}</div>
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                    <span>模块: {alert.module}</span>
                    <span>{new Date(alert.timestamp).toLocaleString()}</span>
                  </div>
                </AlertDescription>
              </Alert>
            )) || (
              <div className="text-center py-8 text-gray-500">
                {alertsLoading ? '加载中...' : '暂无风险警报'}
              </div>
            )}
          </div>

          {/* 风险指标 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg font-semibold">风险指标</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>最大回撤</span>
                      <span className="text-red-600">-5.2%</span>
                    </div>
                    <Progress value={52} className="h-2" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>夏普比率</span>
                      <span className="text-green-600">1.85</span>
                    </div>
                    <Progress value={85} className="h-2" />
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>波动率</span>
                      <span className="text-yellow-600">12.3%</span>
                    </div>
                    <Progress value={23} className="h-2" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>风险敞口</span>
                      <span className="text-blue-600">68%</span>
                    </div>
                    <Progress value={68} className="h-2" />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default MonitoringPanel