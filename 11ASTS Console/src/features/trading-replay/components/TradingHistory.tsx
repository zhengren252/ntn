'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Calendar, Search, Filter, TrendingUp, TrendingDown } from 'lucide-react'
import { useTradingHistory } from '@/hooks/useApi'
import { TradingRecord as Trade } from '@/lib/types'

interface TradingHistoryProps {
  onTradeSelect?: (trade: Trade) => void
}

export default function TradingHistory({ onTradeSelect }: TradingHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [dateRange, setDateRange] = useState('7d')

  const { data: tradesResponse, isLoading } = useTradingHistory({
    search: searchTerm,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    type: typeFilter !== 'all' ? typeFilter : undefined,
    dateRange
  })
  const trades = tradesResponse?.data || []

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
        <span>{isProfit ? '+' : ''}${pnl.toFixed(2)}</span>
      </div>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>交易历史</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>交易历史</CardTitle>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索交易记录..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="completed">已完成</SelectItem>
              <SelectItem value="pending">待处理</SelectItem>
              <SelectItem value="failed">失败</SelectItem>
              <SelectItem value="cancelled">已取消</SelectItem>
            </SelectContent>
          </Select>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="buy">买入</SelectItem>
              <SelectItem value="sell">卖出</SelectItem>
              <SelectItem value="limit">限价</SelectItem>
              <SelectItem value="market">市价</SelectItem>
            </SelectContent>
          </Select>
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="时间" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1d">今天</SelectItem>
              <SelectItem value="7d">7天</SelectItem>
              <SelectItem value="30d">30天</SelectItem>
              <SelectItem value="90d">90天</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <Table data-testid="trading-history-table">
          <TableHeader>
            <TableRow>
              <TableHead>时间</TableHead>
              <TableHead>交易对</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>数量</TableHead>
              <TableHead>价格</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>盈亏</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {trades.map((trade: Trade) => (
              <TableRow key={trade.id} className="cursor-pointer hover:bg-muted/50" data-testid="trade-row">
                <TableCell className="font-mono text-sm">
                  {new Date(trade.timestamp).toLocaleString()}
                </TableCell>
                <TableCell className="font-medium">{trade.symbol}</TableCell>
                <TableCell>{getTypeBadge(trade.type)}</TableCell>
                <TableCell>{trade.quantity}</TableCell>
                <TableCell className="font-mono">${trade.price.toFixed(4)}</TableCell>
                <TableCell>{getStatusBadge(trade.status)}</TableCell>
                <TableCell>{getProfitLoss(trade.pnl ?? trade.profit ?? 0)}</TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onTradeSelect?.(trade)}
                  >
                    详情
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {trades.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            暂无交易记录
          </div>
        )}
      </CardContent>
    </Card>
  )
}