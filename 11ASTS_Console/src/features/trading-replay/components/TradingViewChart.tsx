'use client'

import { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  BarChart3,
  TrendingUp,
  Settings,
  Download,
  Maximize2,
  RefreshCw
} from 'lucide-react'
import { useChartData } from '@/hooks/useApi'
import { TradingRecord as Trade } from '@/lib/types'

interface TradingViewChartProps {
  symbol?: string
  trades?: Trade[]
  onTradeClick?: (trade: Trade) => void
}

export default function TradingViewChart({ symbol = 'BTCUSDT', trades = [], onTradeClick }: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const [timeframe, setTimeframe] = useState('1D')
  const [chartType, setChartType] = useState('candlestick')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const { data: chartData, refetch } = useChartData({ symbol, timeframe })

  // 模拟TradingView图表初始化
  useEffect(() => {
    if (!chartContainerRef.current) return

    // 模拟加载延迟
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 2000)

    return () => clearTimeout(timer)
  }, [symbol, timeframe])

  const handleRefresh = () => {
    setIsLoading(true)
    refetch()
    setTimeout(() => setIsLoading(false), 1000)
  }

  const handleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  const handleExport = () => {
    // 模拟导出功能
    const link = document.createElement('a')
    link.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent('Chart data exported')
    link.download = `${symbol}_chart_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  const timeframes = [
    { value: '1m', label: '1分钟' },
    { value: '5m', label: '5分钟' },
    { value: '15m', label: '15分钟' },
    { value: '1h', label: '1小时' },
    { value: '4h', label: '4小时' },
    { value: '1D', label: '1天' },
    { value: '1W', label: '1周' }
  ]

  const chartTypes = [
    { value: 'candlestick', label: 'K线图' },
    { value: 'line', label: '线图' },
    { value: 'area', label: '面积图' },
    { value: 'bars', label: '柱状图' }
  ]

  return (
    <Card className={isFullscreen ? 'fixed inset-0 z-50' : ''}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>高级图表分析</span>
            <Badge variant="outline">{symbol}</Badge>
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Select value={timeframe} onValueChange={setTimeframe}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {timeframes.map((tf) => (
                  <SelectItem key={tf.value} value={tf.value}>
                    {tf.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={chartType} onValueChange={setChartType}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {chartTypes.map((ct) => (
                  <SelectItem key={ct.value} value={ct.value}>
                    {ct.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleFullscreen}>
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* 图表容器 */}
          <div 
            ref={chartContainerRef}
            className={`relative border rounded-lg ${isFullscreen ? 'h-[calc(100vh-200px)]' : 'h-96'}`}
            data-testid="trading-chart"
            id="tradingview_chart"
          >
            {isLoading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-muted/50">
                <div className="text-center space-y-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                  <p className="text-sm text-muted-foreground">加载图表数据...</p>
                </div>
              </div>
            ) : (
              <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950 dark:to-indigo-950 rounded-lg">
                {/* 模拟TradingView图表界面 */}
                <div className="h-full flex flex-col">
                  {/* 图表工具栏 */}
                  <div className="flex items-center justify-between p-2 border-b bg-background/80 backdrop-blur-sm">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary">{symbol}</Badge>
                      <span className="text-sm font-mono">$45,234.56</span>
                      <span className="text-sm text-green-600 flex items-center">
                        <TrendingUp className="h-3 w-3 mr-1" />
                        +2.34%
                      </span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Button variant="ghost" size="sm">
                        <Settings className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {/* 主图表区域 */}
                  <div className="flex-1 relative p-4">
                    {/* 模拟K线图 */}
                    <div className="h-full flex items-end justify-around space-x-1">
                      {[...Array(20)].map((_, i) => {
                        const height = Math.random() * 80 + 20
                        const isGreen = Math.random() > 0.5
                        return (
                          <div key={i} className="flex flex-col items-center space-y-1">
                            <div 
                              className={`w-2 ${isGreen ? 'bg-green-500' : 'bg-red-500'} rounded-sm`}
                              style={{ height: `${height}%` }}
                            />
                            <div className="w-px h-2 bg-gray-400" />
                          </div>
                        )
                      })}
                    </div>
                    
                    {/* 交易标记 */}
                    {trades.map((trade, index) => (
                      <div
                        key={trade.id}
                        className={`absolute w-3 h-3 rounded-full cursor-pointer ${
                          trade.type === 'buy' ? 'bg-green-500' : 'bg-red-500'
                        }`}
                        style={{
                          left: `${(index / trades.length) * 100}%`,
                          top: `${Math.random() * 60 + 20}%`
                        }}
                        onClick={() => onTradeClick?.(trade)}
                        title={`${trade.type.toUpperCase()} ${trade.symbol} at $${trade.price}`}
                      />
                    ))}
                  </div>
                  
                  {/* 底部信息栏 */}
                  <div className="p-2 border-t bg-background/80 backdrop-blur-sm">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>成交量: 1,234,567</span>
                      <span>24h变化: +2.34%</span>
                      <span>最后更新: {new Date().toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* 图表说明 */}
          <div className="text-xs text-muted-foreground space-y-1">
            <p>• 绿色圆点表示买入交易，红色圆点表示卖出交易</p>
            <p>• 点击交易标记可查看详细信息</p>
            <p>• 使用工具栏可切换时间周期和图表类型</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}