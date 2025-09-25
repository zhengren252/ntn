'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useStrategyDetail, useSubmitReviewDecision } from '@/hooks/use-reviews'
import { formatDate, formatPercentage, getRiskLevelColor, getStatusColor } from '@/lib/utils'
import { ArrowLeft, CheckCircle, XCircle, Clock, TrendingUp, BarChart3 } from 'lucide-react'
import Link from 'next/link'

// 审核决策组件
function ReviewDecisionPanel({ strategyId }: { strategyId: string }) {
  const [decision, setDecision] = useState<'approve' | 'reject' | 'defer'>('approve')
  const [reason, setReason] = useState('')
  const [riskAdjustment, setRiskAdjustment] = useState({
    position_size_limit: 1.0,
    stop_loss_adjustment: 0,
    take_profit_adjustment: 0
  })
  const submitDecision = useSubmitReviewDecision()
  
  const handleSubmit = async () => {
    try {
      await submitDecision.mutateAsync({
        reviewId: strategyId,
        decision: {
          decision,
          reason,
          risk_adjustment: decision === 'approve' ? riskAdjustment : undefined
        }
      })
    } catch (error) {
      console.error('提交审核决策失败:', error)
    }
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>审核决策</CardTitle>
        <CardDescription>请仔细评估策略风险后做出决策</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 决策选择 */}
        <div>
          <label className="text-sm font-medium mb-3 block">审核决策</label>
          <div className="flex space-x-3">
            <Button
              variant={decision === 'approve' ? 'default' : 'outline'}
              onClick={() => setDecision('approve')}
              className="flex items-center space-x-2"
            >
              <CheckCircle className="h-4 w-4" />
              <span>批准</span>
            </Button>
            <Button
              variant={decision === 'reject' ? 'default' : 'outline'}
              onClick={() => setDecision('reject')}
              className="flex items-center space-x-2"
            >
              <XCircle className="h-4 w-4" />
              <span>拒绝</span>
            </Button>
            <Button
              variant={decision === 'defer' ? 'default' : 'outline'}
              onClick={() => setDecision('defer')}
              className="flex items-center space-x-2"
            >
              <Clock className="h-4 w-4" />
              <span>暂缓</span>
            </Button>
          </div>
        </div>
        
        {/* 审核理由 */}
        <div>
          <label className="text-sm font-medium mb-2 block">审核理由</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full px-3 py-2 border rounded-md text-sm"
            rows={4}
            placeholder="请详细说明审核理由..."
          />
        </div>
        
        {/* 风险调整参数 (仅批准时显示) */}
        {decision === 'approve' && (
          <div>
            <label className="text-sm font-medium mb-3 block">风险调整参数</label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-muted-foreground">仓位限制</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={riskAdjustment.position_size_limit}
                  onChange={(e) => setRiskAdjustment(prev => ({
                    ...prev,
                    position_size_limit: parseFloat(e.target.value)
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">止损调整 (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={riskAdjustment.stop_loss_adjustment}
                  onChange={(e) => setRiskAdjustment(prev => ({
                    ...prev,
                    stop_loss_adjustment: parseFloat(e.target.value)
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">止盈调整 (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={riskAdjustment.take_profit_adjustment}
                  onChange={(e) => setRiskAdjustment(prev => ({
                    ...prev,
                    take_profit_adjustment: parseFloat(e.target.value)
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
            </div>
          </div>
        )}
        
        {/* 提交按钮 */}
        <div className="flex justify-end space-x-2">
          <Button variant="outline" asChild>
            <Link href="/reviews/pending">取消</Link>
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={submitDecision.isPending || !reason.trim()}
          >
            {submitDecision.isPending ? '提交中...' : '提交决策'}
          </Button>
        </div>
        
        {submitDecision.isError && (
          <div className="text-sm text-red-600">
            提交失败，请重试
          </div>
        )}
        
        {submitDecision.isSuccess && (
          <div className="text-sm text-green-600">
            审核决策已提交成功
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function StrategyDetailPage() {
  const params = useParams()
  const strategyId = params.id as string
  const { data: strategyDetail, isLoading, error } = useStrategyDetail(strategyId)
  
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-medium">加载中...</div>
          <div className="text-sm text-muted-foreground mt-2">正在获取策略详情</div>
        </div>
      </div>
    )
  }
  
  if (error || !strategyDetail) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-medium text-red-600">加载失败</div>
          <div className="text-sm text-muted-foreground mt-2">
            {error instanceof Error ? error.message : '无法获取策略详情'}
          </div>
          <Button className="mt-4" asChild>
            <Link href="/reviews/pending">返回列表</Link>
          </Button>
        </div>
      </div>
    )
  }
  
  const { strategy_info, risk_analysis, historical_performance, market_conditions } = strategyDetail
  
  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" size="sm" asChild>
            <Link href="/reviews/pending">
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回列表
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">策略详情</h1>
            <p className="text-muted-foreground">策略ID: {strategy_info.strategy_id}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Badge className={getRiskLevelColor(strategy_info.risk_level)}>
            {strategy_info.risk_level} 风险
          </Badge>
          <Badge className={getStatusColor(strategy_info.status)}>
            {strategy_info.status}
          </Badge>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：策略信息和风险分析 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 策略基本信息 */}
          <Card>
            <CardHeader>
              <CardTitle>策略基本信息</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">交易对</div>
                  <div className="font-medium">{strategy_info.symbol}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">策略类型</div>
                  <div className="font-medium">{strategy_info.strategy_type}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">预期收益</div>
                  <div className="font-medium text-green-600">
                    {formatPercentage(strategy_info.expected_return)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">最大回撤</div>
                  <div className="font-medium text-red-600">
                    {formatPercentage(strategy_info.max_drawdown)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">提交时间</div>
                  <div className="font-medium">{formatDate(strategy_info.created_at)}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">更新时间</div>
                  <div className="font-medium">{formatDate(strategy_info.updated_at)}</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* 风险分析 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5" />
                <span>风险分析</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {(risk_analysis.volatility_score * 100).toFixed(1)}
                  </div>
                  <div className="text-sm text-muted-foreground">波动性评分</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {(risk_analysis.liquidity_score * 100).toFixed(1)}
                  </div>
                  <div className="text-sm text-muted-foreground">流动性评分</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {(risk_analysis.correlation_risk * 100).toFixed(1)}
                  </div>
                  <div className="text-sm text-muted-foreground">相关性风险</div>
                </div>
              </div>
              
              {risk_analysis.detailed_metrics && (
                <div className="mt-6">
                  <h4 className="font-medium mb-3">详细指标</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {Object.entries(risk_analysis.detailed_metrics).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-muted-foreground">{key}:</span>
                        <span className="font-medium">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* 历史表现 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5" />
                <span>历史表现</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {historical_performance.length > 0 ? (
                <div className="space-y-2">
                  {historical_performance.slice(0, 10).map((perf, index) => (
                    <div key={index} className="flex items-center justify-between py-2 border-b last:border-b-0">
                      <div className="text-sm text-muted-foreground">
                        {formatDate(perf.date)}
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className={`text-sm font-medium ${
                          perf.return >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {perf.return >= 0 ? '+' : ''}{formatPercentage(perf.return)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          回撤: {formatPercentage(perf.drawdown)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  暂无历史表现数据
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* 市场环境 */}
          <Card>
            <CardHeader>
              <CardTitle>市场环境分析</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-lg font-semibold">
                    {(market_conditions.volatility * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-muted-foreground">市场波动率</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold">{market_conditions.trend}</div>
                  <div className="text-sm text-muted-foreground">市场趋势</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold">{market_conditions.liquidity}</div>
                  <div className="text-sm text-muted-foreground">市场流动性</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        
        {/* 右侧：审核决策面板 */}
        <div className="lg:col-span-1">
          {strategy_info.status === 'pending' && (
            <ReviewDecisionPanel strategyId={strategyId} />
          )}
          
          {strategy_info.status !== 'pending' && (
            <Card>
              <CardHeader>
                <CardTitle>审核状态</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <Badge className={getStatusColor(strategy_info.status)}>
                    {strategy_info.status}
                  </Badge>
                  <div className="text-sm text-muted-foreground mt-2">
                    该策略已完成审核
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}