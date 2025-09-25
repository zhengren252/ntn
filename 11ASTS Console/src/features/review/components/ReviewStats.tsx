'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePendingStrategies } from '@/hooks/useApi'
import { Clock, CheckCircle, XCircle, FileCheck, TrendingUp, AlertTriangle } from 'lucide-react'

interface ReviewStatsData {
  pending: number
  approved: number
  rejected: number
  efficiency: number
  avgProcessTime: string
  todayProcessed: number
}

export const ReviewStats = () => {
  const { data: strategiesResponse, isLoading } = usePendingStrategies()
  const strategies = strategiesResponse?.data || []
  
  // 模拟统计数据，实际应该从API获取
  const stats: ReviewStatsData = {
    pending: strategies.length || 8,
    approved: 24,
    rejected: 3,
    efficiency: 92,
    avgProcessTime: '2.5小时',
    todayProcessed: 27
  }

  const statCards = [
    {
      title: '待审核',
      value: stats.pending,
      description: '需要人工审核的策略',
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      trend: null
    },
    {
      title: '已通过',
      value: stats.approved,
      description: '今日已通过审核',
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      trend: '+12%'
    },
    {
      title: '已拒绝',
      value: stats.rejected,
      description: '今日已拒绝策略',
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
      trend: '-5%'
    },
    {
      title: '审核效率',
      value: `${stats.efficiency}%`,
      description: '平均审核通过率',
      icon: FileCheck,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      trend: '+2%'
    },
    {
      title: '平均处理时间',
      value: stats.avgProcessTime,
      description: '每个策略平均审核时间',
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      trend: '-15min'
    },
    {
      title: '今日处理总数',
      value: stats.todayProcessed,
      description: '今日已处理策略总数',
      icon: AlertTriangle,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
      trend: '+8'
    }
  ]

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
              <div className="h-4 w-4 bg-gray-200 rounded animate-pulse"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded w-16 mb-2 animate-pulse"></div>
              <div className="h-3 bg-gray-200 rounded w-32 animate-pulse"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {statCards.map((stat, index) => {
        const Icon = stat.icon
        return (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <Icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline space-x-2">
                <div className="text-2xl font-bold">{stat.value}</div>
                {stat.trend && (
                  <div className={`text-xs font-medium ${
                    stat.trend.startsWith('+') ? 'text-green-600' : 
                    stat.trend.startsWith('-') && stat.trend.includes('%') ? 'text-red-600' :
                    'text-blue-600'
                  }`}>
                    {stat.trend}
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}