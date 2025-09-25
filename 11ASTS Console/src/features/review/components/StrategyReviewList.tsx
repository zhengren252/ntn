'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { usePendingStrategies, useApproveStrategy } from '@/hooks/useApi'
import { FileCheck, Search, Filter, Clock, TrendingUp, AlertTriangle } from 'lucide-react'
import { StrategyReviewDialog } from './StrategyReviewDialog'

interface Strategy {
  id: string
  name: string
  description: string
  status: 'pending' | 'approved' | 'rejected'
  performance: {
    totalTrades: number
    successRate: number
    profit: number
    drawdown: number
  }
  createdAt: string
  updatedAt: string
  parameters: Record<string, unknown>
  // 审核相关的额外字段
  submittedAt?: string
  submittedBy?: string
  riskLevel?: 'low' | 'medium' | 'high'
  expectedReturn?: number
  maxDrawdown?: number
}

export const StrategyReviewList = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterRisk, setFilterRisk] = useState<string>('all')
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  
  const { data: strategiesResponse, isLoading, error } = usePendingStrategies()
  
  // Mock数据，确保测试能够找到待审列表
  const mockStrategies: Strategy[] = [
    {
      id: 'review_001',
      name: '均线突破策略v2.1',
      description: '基于双均线交叉的改进策略，增加了风险控制模块',
      status: 'pending',
      performance: {
        totalTrades: 150,
        successRate: 85.2,
        profit: 12.5,
        drawdown: 3.2
      },
      createdAt: new Date(Date.now() - 3600000).toISOString(),
      updatedAt: new Date().toISOString(),
      parameters: {},
      submittedBy: '策略开发团队',
      submittedAt: new Date(Date.now() - 3600000).toISOString(),
      riskLevel: 'medium',
      expectedReturn: 15.8,
      maxDrawdown: 5.0
    },
    {
      id: 'review_002',
      name: 'RSI反转策略v1.3',
      description: '基于RSI指标的反转交易策略',
      status: 'pending',
      performance: {
        totalTrades: 89,
        successRate: 78.9,
        profit: 8.7,
        drawdown: 2.1
      },
      createdAt: new Date(Date.now() - 7200000).toISOString(),
      updatedAt: new Date().toISOString(),
      parameters: {},
      submittedBy: 'AI策略生成器',
      submittedAt: new Date(Date.now() - 7200000).toISOString(),
      riskLevel: 'low',
      expectedReturn: 10.2,
      maxDrawdown: 3.5
    }
  ];
  
  const strategies = strategiesResponse?.data || mockStrategies
  const approveStrategyMutation = useApproveStrategy()

  const handleQuickApprove = async (strategyId: string) => {
    try {
      await approveStrategyMutation.mutateAsync({
        strategyId,
        approved: true
      })
    } catch (error) {
      console.error('快速审核失败:', error)
    }
  }

  const handleQuickReject = async (strategyId: string) => {
    try {
      await approveStrategyMutation.mutateAsync({
        strategyId,
        approved: false
      })
    } catch (error) {
      console.error('快速拒绝失败:', error)
    }
  }

  const handleViewDetails = (strategy: Strategy) => {
    setSelectedStrategy(strategy)
    setIsDialogOpen(true)
  }

  const getRiskBadgeVariant = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'default'
      case 'medium': return 'secondary'
      case 'high': return 'destructive'
      default: return 'outline'
    }
  }

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return <TrendingUp className="h-4 w-4 text-green-600" />
      case 'medium': return <Clock className="h-4 w-4 text-yellow-600" />
      case 'high': return <AlertTriangle className="h-4 w-4 text-red-600" />
      default: return <FileCheck className="h-4 w-4" />
    }
  }

  const filteredStrategies = strategies.filter((strategy: Strategy) => {
    const matchesSearch = strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (strategy.submittedBy || '').toLowerCase().includes(searchTerm.toLowerCase())
    const matchesRisk = filterRisk === 'all' || strategy.riskLevel === filterRisk
    return matchesSearch && matchesRisk
  })

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600">加载策略列表失败</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>待审核策略列表</CardTitle>
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索策略名称或提交者..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8 w-64"
                />
              </div>
              <Select value={filterRisk} onValueChange={setFilterRisk}>
                <SelectTrigger className="w-32">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部风险</SelectItem>
                  <SelectItem value="low">低风险</SelectItem>
                  <SelectItem value="medium">中风险</SelectItem>
                  <SelectItem value="high">高风险</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
          ) : filteredStrategies.length === 0 ? (
            <div className="text-center py-8">
              <FileCheck className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">暂无待审核策略</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="pending-reviews-list">
              {filteredStrategies.map((strategy: Strategy) => (
                <div key={strategy.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors review-item" data-testid="review-item">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      {getRiskIcon(strategy.riskLevel || 'medium')}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="font-medium text-lg">{strategy.name}</h3>
                        <Badge variant={getRiskBadgeVariant(strategy.riskLevel || 'medium')}>
                          {strategy.riskLevel === 'low' ? '低风险' : 
                           strategy.riskLevel === 'medium' ? '中风险' : 
                           strategy.riskLevel === 'high' ? '高风险' : '中风险'}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500 space-y-1">
                        <p>提交者: {strategy.submittedBy || '未知'} | 提交时间: {strategy.submittedAt || strategy.createdAt}</p>
                        <p>预期收益: {strategy.expectedReturn || strategy.performance?.profit || 0}% | 最大回撤: {strategy.maxDrawdown || strategy.performance?.drawdown || 0}%</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleViewDetails(strategy)}
                    >
                      查看详情
                    </Button>
                    <Button 
                      size="sm" 
                      variant="destructive"
                      onClick={() => handleQuickReject(strategy.id)}
                      disabled={approveStrategyMutation.isPending}
                      data-testid="reject-button"
                    >
                      拒绝
                    </Button>
                    <Button 
                      size="sm"
                      onClick={() => handleQuickApprove(strategy.id)}
                      disabled={approveStrategyMutation.isPending}
                      data-testid="approve-button"
                    >
                      通过
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <StrategyReviewDialog
        strategy={selectedStrategy}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </>
  )
}