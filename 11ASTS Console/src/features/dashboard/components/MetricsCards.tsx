'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useDashboardOverview } from '@/hooks/useApi'
import { TrendingUp, TrendingDown, Activity, CheckCircle } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  status?: 'success' | 'warning' | 'error'
  icon?: React.ReactNode
}

const MetricCard = ({ title, value, change, status, icon }: MetricCardProps) => {
  const getStatusColor = () => {
    switch (status) {
      case 'success': return 'text-green-600'
      case 'warning': return 'text-yellow-600'
      case 'error': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getChangeColor = () => {
    if (change === undefined) return ''
    return change >= 0 ? 'text-green-600' : 'text-red-600'
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className={getStatusColor()}>{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change !== undefined && (
          <div className={`flex items-center text-xs ${getChangeColor()}`}>
            {change >= 0 ? (
              <TrendingUp className="mr-1 h-3 w-3" />
            ) : (
              <TrendingDown className="mr-1 h-3 w-3" />
            )}
            {Math.abs(change)}%
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export const MetricsCards = () => {
  const { data: overview, isLoading, error } = useDashboardOverview()

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded w-1/2"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-red-600">数据加载失败</div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const overviewData = overview?.data
  
  const metrics = [
    {
      title: '总盈利',
      value: overviewData?.totalProfit ? `¥${overviewData.totalProfit.toLocaleString()}` : '¥0',
      change: overviewData?.profitChange,
      status: (overviewData?.profitChange || 0) >= 0 ? ('success' as const) : ('error' as const),
      icon: <TrendingUp className="h-4 w-4" />
    },
    {
      title: '活跃策略',
      value: overviewData?.activeStrategies || 0,
      change: overviewData?.strategiesChange,
      status: 'success' as const,
      icon: <Activity className="h-4 w-4" />
    },
    {
      title: '成功率',
      value: overviewData?.successRate ? `${overviewData.successRate}%` : '0%',
      change: overviewData?.successRateChange,
      status: (overviewData?.successRate || 0) >= 70 ? ('success' as const) : 
              (overviewData?.successRate || 0) >= 50 ? ('warning' as const) : ('error' as const),
      icon: <CheckCircle className="h-4 w-4" />
    },
    {
      title: '系统状态',
      value: overviewData?.systemStatus || '未知',
      change: 0, // systemStatusChange属性不存在，使用默认值
      status: overviewData?.systemStatus === 'running' ? ('success' as const) : ('error' as const),
      icon: <Activity className="h-4 w-4" />
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric, index) => (
        <MetricCard key={index} {...metric} />
      ))}
    </div>
  )
}