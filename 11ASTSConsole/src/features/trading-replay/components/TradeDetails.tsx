'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  TrendingUp,
  TrendingDown,
  Clock,
  DollarSign,
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { TradingRecord as Trade } from '@/lib/types'

interface TradeDetailsProps {
  trade: Trade
  isOpen: boolean
  onClose: () => void
}

export default function TradeDetails({ trade, isOpen, onClose }: TradeDetailsProps) {
  if (!trade) return null

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-600" />
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-600" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      'completed': 'default',
      'pending': 'secondary',
      'failed': 'destructive',
      'cancelled': 'outline'
    } as const
    return <Badge variant={variants[status as keyof typeof variants] || 'default'}>{status}</Badge>
  }

  const getTypeBadge = (type: string) => {
    const colors = {
      'buy': 'bg-green-100 text-green-800',
      'sell': 'bg-red-100 text-red-800',
      'limit': 'bg-blue-100 text-blue-800',
      'market': 'bg-purple-100 text-purple-800'
    } as const
    return (
      <Badge className={colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800'}>
        {type}
      </Badge>
    )
  }

  const getProfitLoss = (pnl: number) => {
    const isProfit = pnl > 0
    return (
      <div className={`flex items-center space-x-1 ${isProfit ? 'text-green-600' : 'text-red-600'}`}>
        {isProfit ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
        <span className="font-semibold">{isProfit ? '+' : ''}${pnl.toFixed(2)}</span>
      </div>
    )
  }

  const formatDateTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString()
    }
  }

  const { date, time } = formatDateTime(trade.timestamp)

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>交易详情</span>
            <Badge variant="outline">#{trade.id}</Badge>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* 基本信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">交易对</label>
                  <p className="text-lg font-semibold">{trade.symbol}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">交易类型</label>
                  <div className="mt-1">{getTypeBadge(trade.type)}</div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">状态</label>
                  <div className="flex items-center space-x-2 mt-1">
                    {getStatusIcon(trade.status)}
                    {getStatusBadge(trade.status)}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">执行时间</label>
                  <p className="text-sm">{date}</p>
                  <p className="text-sm text-muted-foreground">{time}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 交易数据 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">交易数据</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">数量</label>
                  <p className="text-lg font-mono">{trade.quantity}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">价格</label>
                  <p className="text-lg font-mono">${trade.price.toFixed(4)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">总金额</label>
                  <p className="text-lg font-mono">${(trade.quantity * trade.price).toFixed(2)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">手续费</label>
                  <p className="text-lg font-mono">${trade.fee?.toFixed(4) || '0.0000'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 盈亏分析 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center space-x-2">
                <DollarSign className="h-5 w-5" />
                <span>盈亏分析</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">盈亏金额</label>
                  <div className="mt-1">{getProfitLoss(trade.pnl)}</div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">盈亏比例</label>
                  <p className={`text-lg font-semibold ${
                    trade.pnlPercentage > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {trade.pnlPercentage > 0 ? '+' : ''}{trade.pnlPercentage?.toFixed(2) || '0.00'}%
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">持仓时间</label>
                  <p className="text-lg">{trade.holdingTime || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">风险评级</label>
                  <Badge variant={trade.riskLevel === 'high' ? 'destructive' : 
                                trade.riskLevel === 'medium' ? 'secondary' : 'default'}>
                    {trade.riskLevel || 'low'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 策略信息 */}
          {trade.strategy && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Target className="h-5 w-5" />
                  <span>策略信息</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">策略名称</label>
                    <p className="text-lg">{trade.strategy.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">策略版本</label>
                    <p className="text-lg">{trade.strategy.version}</p>
                  </div>
                  <div className="col-span-2">
                    <label className="text-sm font-medium text-muted-foreground">信号来源</label>
                    <p className="text-sm">{trade.strategy.signal}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 市场环境 */}
          {trade.marketCondition && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">市场环境</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">波动率</label>
                    <p className="text-lg">{trade.marketCondition.volatility}%</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">趋势</label>
                    <Badge variant={trade.marketCondition.trend === 'bullish' ? 'default' : 
                                  trade.marketCondition.trend === 'bearish' ? 'destructive' : 'secondary'}>
                      {trade.marketCondition.trend}
                    </Badge>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">成交量</label>
                    <p className="text-lg">{trade.marketCondition.volume}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">流动性</label>
                    <p className="text-lg">{trade.marketCondition.liquidity}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 备注 */}
          {trade.notes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">备注</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{trade.notes}</p>
              </CardContent>
            </Card>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={onClose}>
              关闭
            </Button>
            <Button variant="outline">
              导出详情
            </Button>
            <Button>
              复制策略
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}