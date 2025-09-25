'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Activity,
  Percent
} from 'lucide-react'
import { usePerformanceAnalysis } from '@/hooks/useApi'
import { PerformanceData, TradeDistribution } from '@/lib/types'

interface PerformanceAnalysisProps {
  dateRange?: string
  symbol?: string
}

export default function PerformanceAnalysis({ dateRange = '30d', symbol }: PerformanceAnalysisProps) {
  const { data: performanceResponse, isLoading } = usePerformanceAnalysis()
  const performance = performanceResponse?.data

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(8)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-24 mb-2" />
              <Skeleton className="h-3 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!performance) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">暂无性能数据</p>
        </CardContent>
      </Card>
    )
  }

  const {
    totalPnL = 0,
    totalTrades = 0,
    winRate = 0,
    avgWin = 0,
    avgLoss = 0,
    maxDrawdown = 0,
    sharpeRatio = 0,
    profitFactor = 0,
    dailyReturns = [],
    tradeDistribution = [],
    monthlyPerformance = []
  } = performance || {}

  const getChangeColor = (value: number) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600'
  }

  const getChangeIcon = (value: number) => {
    return value >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

  return (
    <div className="space-y-6">
      {/* 关键指标卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总盈亏</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getChangeColor(totalPnL)}`}>
              ${totalPnL.toFixed(2)}
            </div>
            <div className={`flex items-center text-xs ${getChangeColor(totalPnL)}`}>
              {getChangeIcon(totalPnL)}
              <span className="ml-1">
                {totalPnL >= 0 ? '+' : ''}{((totalPnL / 10000) * 100).toFixed(2)}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">胜率</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{winRate.toFixed(1)}%</div>
            <Progress value={winRate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">交易次数</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTrades}</div>
            <p className="text-xs text-muted-foreground mt-1">
              平均每日 {(totalTrades / 30).toFixed(1)} 笔
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">夏普比率</CardTitle>
            <Percent className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sharpeRatio.toFixed(2)}</div>
            <Badge variant={sharpeRatio > 1 ? 'default' : 'secondary'} className="mt-1">
              {sharpeRatio > 1 ? '优秀' : '一般'}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* 详细指标 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">平均盈利</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold text-green-600">
              ${avgWin.toFixed(2)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">平均亏损</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold text-red-600">
              ${avgLoss.toFixed(2)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">最大回撤</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold text-red-600">
              {maxDrawdown.toFixed(2)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">盈亏比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold">
              {profitFactor.toFixed(2)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 图表区域 */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* 每日收益曲线 */}
        <Card>
          <CardHeader>
            <CardTitle>每日收益曲线</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyReturns}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="return"
                  stroke="#8884d8"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 交易分布 */}
        <Card>
          <CardHeader>
            <CardTitle>交易类型分布</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={tradeDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {tradeDistribution.map((entry: TradeDistribution, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 月度表现 */}
      <Card>
        <CardHeader>
          <CardTitle>月度表现</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={monthlyPerformance}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="pnl" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}