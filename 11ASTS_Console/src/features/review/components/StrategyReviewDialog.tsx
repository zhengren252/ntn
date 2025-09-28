'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePostReviewDecision } from '@/hooks/useApi'
import { CheckCircle, XCircle, AlertTriangle, TrendingUp, BarChart3 } from 'lucide-react'

interface Strategy {
  id: string
  name: string
  submittedAt?: string
  submittedBy?: string
  riskLevel?: 'low' | 'medium' | 'high'
  expectedReturn?: number
  maxDrawdown?: number
  status: 'pending' | 'approved' | 'rejected'
  description: string
  performance: {
    totalTrades: number
    successRate: number
    profit: number
    drawdown: number
  }
  createdAt: string
  updatedAt: string
  parameters: Record<string, unknown>
}

interface StrategyReviewDialogProps {
  strategy: Strategy | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export const StrategyReviewDialog = ({ strategy, open, onOpenChange }: StrategyReviewDialogProps) => {
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null)
  const [comment, setComment] = useState('')
  const reviewDecisionMutation = usePostReviewDecision()

  const handleSubmitReview = async () => {
    if (!strategy || !decision) return

    try {
      await reviewDecisionMutation.mutateAsync({
        reviewId: strategy.id,
        decision,
        comments: comment,
      })
      
      // 重置状态并关闭对话框
      setDecision(null)
      setComment('')
      onOpenChange(false)
    } catch (error) {
      console.error('提交审核失败:', error)
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-600 bg-green-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'high': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getRiskLabel = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return '低风险'
      case 'medium': return '中风险'
      case 'high': return '高风险'
      default: return '未知'
    }
  }

  if (!strategy) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <span>{strategy.name}</span>
            <Badge className={getRiskColor(strategy.riskLevel || 'medium')}>
              {getRiskLabel(strategy.riskLevel || 'medium')}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            提交者: {strategy.submittedBy || '未知'} | 提交时间: {strategy.submittedAt || '未知'}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">策略概览</TabsTrigger>
            <TabsTrigger value="parameters">参数配置</TabsTrigger>
            <TabsTrigger value="risk">风险分析</TabsTrigger>
            <TabsTrigger value="backtest">回测结果</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>策略描述</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 leading-relaxed">{strategy.description}</p>
              </CardContent>
            </Card>

            <div className="grid grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">预期收益率</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {strategy.expectedReturn || 0}%
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">最大回撤</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">
                    {strategy.maxDrawdown || 0}%
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="parameters" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>策略参数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(strategy.parameters).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                      <span className="font-medium">{key}:</span>
                      <span className="text-gray-600">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="risk" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5" />
                  <span>风险评估</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 border rounded">
                    <span>市场风险</span>
                    <Badge variant="secondary">中等</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded">
                    <span>流动性风险</span>
                    <Badge variant="default">低</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded">
                    <span>操作风险</span>
                    <Badge variant="destructive">高</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 border rounded">
                    <span>模型风险</span>
                    <Badge variant="secondary">中等</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="backtest" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>回测结果</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-green-50 rounded">
                    <div className="text-2xl font-bold text-green-600">15.2%</div>
                    <div className="text-sm text-gray-600">年化收益率</div>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded">
                    <div className="text-2xl font-bold text-blue-600">1.45</div>
                    <div className="text-sm text-gray-600">夏普比率</div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded">
                    <div className="text-2xl font-bold text-purple-600">68%</div>
                    <div className="text-sm text-gray-600">胜率</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="space-y-4">
          <div>
            <Label htmlFor="comment">审核意见</Label>
            <Textarea
              id="comment"
              placeholder="请输入审核意见..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="mt-2"
              rows={3}
            />
          </div>

          <div className="flex items-center space-x-4">
            <Label>审核决定:</Label>
            <div className="flex space-x-2">
              <Button
                variant={decision === 'approve' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDecision('approve')}
                className="flex items-center space-x-2"
              >
                <CheckCircle className="h-4 w-4" />
                <span>通过</span>
              </Button>
              <Button
                variant={decision === 'reject' ? 'destructive' : 'outline'}
                size="sm"
                onClick={() => setDecision('reject')}
                className="flex items-center space-x-2"
              >
                <XCircle className="h-4 w-4" />
                <span>拒绝</span>
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button 
            onClick={handleSubmitReview}
            disabled={!decision || reviewDecisionMutation.isPending}
          >
            {reviewDecisionMutation.isPending ? '提交中...' : '提交审核'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}