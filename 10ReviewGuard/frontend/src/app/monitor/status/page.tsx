'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useSystemStatus } from '@/hooks/use-reviews'
import { formatDate } from '@/lib/utils'
import { 
  Activity, 
  Server, 
  Cpu, 
  MemoryStick, 
  HardDrive, 
  Wifi, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  RefreshCw
} from 'lucide-react'

// 系统健康状态组件
function SystemHealthCard() {
  const { data: systemStatus, isLoading, error, refetch } = useSystemStatus()
  const [lastUpdate, setLastUpdate] = useState(new Date())

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date())
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600'
      case 'warning': return 'text-yellow-600'
      case 'error': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'warning': return <AlertTriangle className="h-5 w-5 text-yellow-600" />
      case 'error': return <AlertTriangle className="h-5 w-5 text-red-600" />
      default: return <Clock className="h-5 w-5 text-gray-600" />
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-medium">系统健康状态</CardTitle>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center space-x-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            <span>无法获取系统状态</span>
          </div>
        ) : systemStatus ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {getStatusIcon(systemStatus.status)}
                <span className={`font-medium ${getStatusColor(systemStatus.status)}`}>
                  {systemStatus.status === 'healthy' ? '系统正常' : 
                   systemStatus.status === 'warning' ? '系统警告' : '系统异常'}
                </span>
              </div>
              <Badge variant="outline">
                {formatDate(lastUpdate.toISOString())}
              </Badge>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">{systemStatus.pending_count}</div>
                <div className="text-sm text-muted-foreground">待处理任务</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{systemStatus.processed_today}</div>
                <div className="text-sm text-muted-foreground">今日已处理</div>
              </div>
            </div>
            
            <div className="text-center">
              <div className="text-lg font-semibold">{systemStatus.avg_processing_time} 分钟</div>
              <div className="text-sm text-muted-foreground">平均处理时间</div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-20">
            <div className="text-sm text-muted-foreground">加载中...</div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// 性能指标组件
function PerformanceMetrics() {
  const { data: systemStatus } = useSystemStatus()
  
  const metrics = [
    {
      name: 'CPU使用率',
      value: systemStatus ? (systemStatus.system_load * 100).toFixed(1) + '%' : 'N/A',
      icon: <Cpu className="h-5 w-5" />,
      color: systemStatus && systemStatus.system_load > 0.8 ? 'text-red-600' : 
             systemStatus && systemStatus.system_load > 0.6 ? 'text-yellow-600' : 'text-green-600'
    },
    {
      name: '内存使用',
      value: '65%', // 模拟数据
      icon: <MemoryStick className="h-5 w-5" />,
      color: 'text-green-600'
    },
    {
      name: '磁盘使用',
      value: '42%', // 模拟数据
      icon: <HardDrive className="h-5 w-5" />,
      color: 'text-green-600'
    },
    {
      name: '网络延迟',
      value: '12ms', // 模拟数据
      icon: <Wifi className="h-5 w-5" />,
      color: 'text-green-600'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{metric.name}</CardTitle>
            <div className={metric.color}>{metric.icon}</div>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${metric.color}`}>
              {metric.value}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// 服务状态组件
function ServiceStatus() {
  const services = [
    {
      name: 'ReviewGuard API',
      status: 'running',
      uptime: '99.9%',
      lastCheck: new Date().toISOString()
    },
    {
      name: 'ZeroMQ Service',
      status: 'running',
      uptime: '99.8%',
      lastCheck: new Date().toISOString()
    },
    {
      name: 'Redis Cache',
      status: 'running',
      uptime: '100%',
      lastCheck: new Date().toISOString()
    },
    {
      name: 'SQLite Database',
      status: 'running',
      uptime: '100%',
      lastCheck: new Date().toISOString()
    }
  ]

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <Badge className="bg-green-100 text-green-800">运行中</Badge>
      case 'stopped':
        return <Badge className="bg-red-100 text-red-800">已停止</Badge>
      case 'warning':
        return <Badge className="bg-yellow-100 text-yellow-800">警告</Badge>
      default:
        return <Badge variant="secondary">未知</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Server className="h-5 w-5" />
          <span>服务状态</span>
        </CardTitle>
        <CardDescription>各个服务组件的运行状态</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {services.map((service, index) => (
            <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`h-3 w-3 rounded-full ${
                  service.status === 'running' ? 'bg-green-500' : 
                  service.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                }`} />
                <div>
                  <div className="font-medium">{service.name}</div>
                  <div className="text-sm text-muted-foreground">
                    正常运行时间: {service.uptime}
                  </div>
                </div>
              </div>
              <div className="text-right">
                {getStatusBadge(service.status)}
                <div className="text-xs text-muted-foreground mt-1">
                  {formatDate(service.lastCheck)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// 实时活动日志组件
function ActivityLog() {
  const [logs] = useState([
    {
      id: '1',
      timestamp: new Date().toISOString(),
      level: 'info',
      message: '策略 BTCUSDT_001 已提交审核',
      source: 'ReviewGuard'
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 60000).toISOString(),
      level: 'success',
      message: '策略 ETHUSDT_002 审核通过',
      source: 'ReviewGuard'
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 120000).toISOString(),
      level: 'warning',
      message: '高风险策略 ADAUSDT_003 需要人工审核',
      source: 'RiskEngine'
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 180000).toISOString(),
      level: 'error',
      message: 'ZeroMQ连接临时中断，已自动重连',
      source: 'ZeroMQ'
    }
  ])

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'success': return 'text-green-600'
      case 'warning': return 'text-yellow-600'
      case 'error': return 'text-red-600'
      default: return 'text-blue-600'
    }
  }

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'success': return <CheckCircle className="h-4 w-4" />
      case 'warning': return <AlertTriangle className="h-4 w-4" />
      case 'error': return <AlertTriangle className="h-4 w-4" />
      default: return <Activity className="h-4 w-4" />
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Activity className="h-5 w-5" />
          <span>实时活动日志</span>
        </CardTitle>
        <CardDescription>系统最近的活动和事件</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-80 overflow-y-auto">
          {logs.map((log) => (
            <div key={log.id} className="flex items-start space-x-3 p-2 hover:bg-gray-50 rounded">
              <div className={getLevelColor(log.level)}>
                {getLevelIcon(log.level)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm">{log.message}</div>
                <div className="flex items-center space-x-2 text-xs text-muted-foreground mt-1">
                  <span>{log.source}</span>
                  <span>•</span>
                  <span>{formatDate(log.timestamp)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default function MonitorStatusPage() {
  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">系统监控</h1>
          <p className="text-muted-foreground">实时监控系统状态和性能指标</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="flex items-center space-x-1">
            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
            <span>实时监控</span>
          </Badge>
        </div>
      </div>

      {/* 系统健康状态 */}
      <SystemHealthCard />

      {/* 性能指标 */}
      <div>
        <h2 className="text-xl font-semibold mb-4">性能指标</h2>
        <PerformanceMetrics />
      </div>

      {/* 服务状态和活动日志 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ServiceStatus />
        <ActivityLog />
      </div>
    </div>
  )
}