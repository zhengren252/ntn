'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart as PieChartIcon,
  Calendar,
  Download,
  Filter
} from 'lucide-react'
import { useCostAnalytics } from '@/hooks/useApi'

interface CostData {
  date: string
  cost: number
  calls: number
  service: string
}

interface ServiceCost {
  name: string
  cost: number
  calls: number
  percentage: number
  color: string
}

interface TimeRange {
  label: string
  value: string
  days: number
}

const timeRanges: TimeRange[] = [
  { label: '最近7天', value: '7d', days: 7 },
  { label: '最近30天', value: '30d', days: 30 },
  { label: '最近90天', value: '90d', days: 90 },
  { label: '最近1年', value: '1y', days: 365 }
]

const COLORS = [
  '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
  '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
]

interface TooltipPayload {
  name: string;
  value: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
        <p className="font-medium">{label}</p>
        {payload.map((entry: TooltipPayload, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: ${entry.value?.toFixed(2)}
          </p>
        ))}
      </div>
    )
  }
  return null
}

interface PieTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      name: string;
      cost: number;
      percentage: number;
      calls: number;
    };
  }>;
}

const PieTooltip = ({ active, payload }: PieTooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
        <p className="font-medium">{data.name}</p>
        <p className="text-sm">成本: ${data.cost.toFixed(2)}</p>
        <p className="text-sm">占比: {data.percentage.toFixed(1)}%</p>
        <p className="text-sm">调用: {data.calls.toLocaleString()}</p>
      </div>
    )
  }
  return null
}

export const CostAnalytics = () => {
  const [timeRange, setTimeRange] = useState('30d')
  const [chartType, setChartType] = useState<'line' | 'bar' | 'area'>('line')
  const { data: analyticsData, isLoading } = useCostAnalytics()

  // 模拟分析数据
  const mockData = {
    dailyCosts: [
      { date: '01-01', cost: 45.23, calls: 4523 },
      { date: '01-02', cost: 52.18, calls: 5218 },
      { date: '01-03', cost: 38.94, calls: 3894 },
      { date: '01-04', cost: 61.75, calls: 6175 },
      { date: '01-05', cost: 49.32, calls: 4932 },
      { date: '01-06', cost: 55.67, calls: 5567 },
      { date: '01-07', cost: 42.89, calls: 4289 },
      { date: '01-08', cost: 58.14, calls: 5814 },
      { date: '01-09', cost: 47.26, calls: 4726 },
      { date: '01-10', cost: 53.91, calls: 5391 },
      { date: '01-11', cost: 44.78, calls: 4478 },
      { date: '01-12', cost: 59.83, calls: 5983 },
      { date: '01-13', cost: 41.65, calls: 4165 },
      { date: '01-14', cost: 56.42, calls: 5642 },
      { date: '01-15', cost: 48.97, calls: 4897 }
    ],
    serviceCosts: [
      { name: '币安API', cost: 456.78, calls: 45623, percentage: 36.6, color: COLORS[0] },
      { name: 'OpenAI GPT-4', cost: 324.12, calls: 8934, percentage: 26.0, color: COLORS[1] },
      { name: '火币API', cost: 198.45, calls: 32145, percentage: 15.9, color: COLORS[2] },
      { name: '数据存储', cost: 156.23, calls: 0, percentage: 12.5, color: COLORS[3] },
      { name: '其他服务', cost: 111.92, calls: 39145, percentage: 9.0, color: COLORS[4] }
    ],
    hourlyPattern: [
      { hour: '00:00', cost: 12.34 },
      { hour: '02:00', cost: 8.67 },
      { hour: '04:00', cost: 6.23 },
      { hour: '06:00', cost: 15.89 },
      { hour: '08:00', cost: 28.45 },
      { hour: '10:00', cost: 35.67 },
      { hour: '12:00', cost: 42.18 },
      { hour: '14:00', cost: 38.94 },
      { hour: '16:00', cost: 31.76 },
      { hour: '18:00', cost: 25.43 },
      { hour: '20:00', cost: 19.87 },
      { hour: '22:00', cost: 16.52 }
    ],
    costByCategory: [
      { category: 'API调用', cost: 856.34, percentage: 68.6 },
      { category: 'AI服务', cost: 234.12, percentage: 18.8 },
      { category: '数据存储', cost: 98.76, percentage: 7.9 },
      { category: '基础设施', cost: 58.28, percentage: 4.7 }
    ]
  }

  // 将API数据转换为组件期望的格式，如果没有API数据则使用模拟数据
  const data = analyticsData?.data ? {
    dailyCosts: analyticsData.data.trends || [],
    serviceCosts: mockData.serviceCosts, // API暂时没有提供服务成本数据
    hourlyPattern: mockData.hourlyPattern, // API暂时没有提供小时模式数据
    costByCategory: mockData.costByCategory // API暂时没有提供分类数据
  } : mockData

  const getTotalCost = () => {
    return data.dailyCosts.reduce((sum, item) => sum + item.cost, 0)
  }

  const getAverageCost = () => {
    return getTotalCost() / data.dailyCosts.length
  }

  const getCostTrend = () => {
    const recent = data.dailyCosts.slice(-7)
    const previous = data.dailyCosts.slice(-14, -7)
    const recentAvg = recent.reduce((sum, item) => sum + item.cost, 0) / recent.length
    const previousAvg = previous.reduce((sum, item) => sum + item.cost, 0) / previous.length
    return ((recentAvg - previousAvg) / previousAvg) * 100
  }

  const renderChart = () => {
    const commonProps = {
      data: data.dailyCosts,
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    }

    switch (chartType) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="cost" fill="#3B82F6" />
          </BarChart>
        )
      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Area 
              type="monotone" 
              dataKey="cost" 
              stroke="#3B82F6" 
              fill="#3B82F6" 
              fillOpacity={0.3}
            />
          </AreaChart>
        )
      default:
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Line 
              type="monotone" 
              dataKey="cost" 
              stroke="#3B82F6" 
              strokeWidth={2}
              dot={{ fill: '#3B82F6' }}
            />
          </LineChart>
        )
    }
  }

  const exportData = () => {
    // 这里应该实现数据导出功能
    console.log('Exporting cost analytics data...')
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-gray-200 rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardContent className="p-6">
            <div className="h-64 bg-gray-200 rounded animate-pulse" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 分析概览 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总成本</CardTitle>
            <BarChart3 className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${getTotalCost().toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              {timeRanges.find(r => r.value === timeRange)?.label}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">日均成本</CardTitle>
            <Calendar className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${getAverageCost().toFixed(2)}</div>
            <div className={`flex items-center space-x-1 text-xs ${
              getCostTrend() >= 0 ? 'text-red-600' : 'text-green-600'
            }`}>
              {getCostTrend() >= 0 ? 
                <TrendingUp className="h-3 w-3" /> : 
                <TrendingDown className="h-3 w-3" />
              }
              <span>{Math.abs(getCostTrend()).toFixed(1)}%</span>
              <span className="text-gray-500">较上周</span>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">最高单日</CardTitle>
            <TrendingUp className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${Math.max(...data.dailyCosts.map(d => d.cost)).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              峰值成本
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 成本趋势图表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>成本趋势分析</CardTitle>
            <div className="flex items-center space-x-2">
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {timeRanges.map((range) => (
                    <SelectItem key={range.value} value={range.value}>
                      {range.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={chartType} onValueChange={(value: 'line' | 'bar' | 'area') => setChartType(value)}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="line">线图</SelectItem>
                  <SelectItem value="bar">柱图</SelectItem>
                  <SelectItem value="area">面积图</SelectItem>
                </SelectContent>
              </Select>
              
              <Button variant="outline" size="sm" onClick={exportData}>
                <Download className="h-4 w-4 mr-2" />
                导出
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              {renderChart()}
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* 详细分析 */}
      <Tabs defaultValue="services" className="space-y-4">
        <TabsList>
          <TabsTrigger value="services">服务分布</TabsTrigger>
          <TabsTrigger value="hourly">时段分析</TabsTrigger>
          <TabsTrigger value="category">类别分析</TabsTrigger>
        </TabsList>
        
        <TabsContent value="services" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <PieChartIcon className="h-4 w-4" />
                  <span>服务成本分布</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.serviceCosts}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        dataKey="cost"
                        label={({ name, percentage }) => `${name} ${percentage.toFixed(1)}%`}
                      >
                        {data.serviceCosts.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>服务详情</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.serviceCosts.map((service, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded border">
                      <div className="flex items-center space-x-3">
                        <div 
                          className="w-3 h-3 rounded-full" 
                          style={{ backgroundColor: service.color }}
                        />
                        <div>
                          <p className="font-medium text-sm">{service.name}</p>
                          <p className="text-xs text-gray-500">
                            {service.calls > 0 ? `${service.calls.toLocaleString()} 调用` : '存储服务'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold">${service.cost.toFixed(2)}</p>
                        <Badge variant="outline">{service.percentage.toFixed(1)}%</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="hourly" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>24小时成本模式</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.hourlyPattern}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="cost" fill="#10B981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="category" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>成本类别分析</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.costByCategory.map((category, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{category.category}</span>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold">${category.cost.toFixed(2)}</span>
                        <Badge variant="outline">{category.percentage.toFixed(1)}%</Badge>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${category.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}