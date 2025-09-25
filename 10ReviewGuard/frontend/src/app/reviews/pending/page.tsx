'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { usePendingReviews, useSubmitReviewDecision } from '@/hooks/use-reviews'
import { useReviewStore } from '@/store/review-store'
import { formatDate, formatPercentage, getRiskLevelColor, getStatusColor } from '@/lib/utils'
import { Eye, CheckCircle, Filter, ChevronLeft, ChevronRight } from 'lucide-react'
import Link from 'next/link'

// 筛选组件
function ReviewFilters() {
  const { filters, setFilters } = useReviewStore()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Filter className="h-5 w-5" />
          <span>筛选条件</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4">
          <div className="flex flex-col space-y-2">
            <label className="text-sm font-medium">风险等级</label>
            <select
              value={filters.risk_level || ''}
              onChange={(e) => setFilters({ risk_level: e.target.value || undefined })}
              className="px-3 py-2 border rounded-md text-sm"
            >
              <option value="">全部</option>
              <option value="low">低风险</option>
              <option value="medium">中风险</option>
              <option value="high">高风险</option>
            </select>
          </div>
          
          <div className="flex flex-col space-y-2">
            <label className="text-sm font-medium">状态</label>
            <select
              value={filters.status || ''}
              onChange={(e) => setFilters({ status: e.target.value || undefined })}
              className="px-3 py-2 border rounded-md text-sm"
            >
              <option value="">全部</option>
              <option value="pending">待审核</option>
              <option value="processing">处理中</option>
            </select>
          </div>
          
          <div className="flex flex-col space-y-2">
            <label className="text-sm font-medium">每页显示</label>
            <select
              value={filters.limit}
              onChange={(e) => setFilters({ limit: parseInt(e.target.value), page: 1 })}
              className="px-3 py-2 border rounded-md text-sm"
            >
              <option value="10">10条</option>
              <option value="20">20条</option>
              <option value="50">50条</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <Button
              variant="outline"
              onClick={() => setFilters({ risk_level: undefined, status: undefined, page: 1 })}
            >
              重置筛选
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// 分页组件
function Pagination() {
  const { pagination, setFilters } = useReviewStore()
  
  if (!pagination) return null
  
  const { current_page, total_pages, has_next } = pagination
  
  return (
    <div className="flex items-center justify-between">
      <div className="text-sm text-muted-foreground">
        第 {current_page} 页，共 {total_pages} 页
      </div>
      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFilters({ page: current_page - 1 })}
          disabled={current_page <= 1}
        >
          <ChevronLeft className="h-4 w-4" />
          上一页
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFilters({ page: current_page + 1 })}
          disabled={!has_next}
        >
          下一页
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

// 快速审核对话框
function QuickReviewDialog({ 
  reviewId, 
  isOpen, 
  onClose 
}: { 
  reviewId: string | null
  isOpen: boolean
  onClose: () => void 
}) {
  const [decision, setDecision] = useState<'approve' | 'reject' | 'defer'>('approve')
  const [reason, setReason] = useState('')
  const submitDecision = useSubmitReviewDecision()
  
  const handleSubmit = async () => {
    if (!reviewId) return
    
    try {
      await submitDecision.mutateAsync({
        reviewId,
        decision: { decision, reason }
      })
      onClose()
      setReason('')
    } catch (error) {
      console.error('提交审核决策失败:', error)
    }
  }
  
  if (!isOpen || !reviewId) return null
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">快速审核</h3>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">审核决策</label>
            <div className="flex space-x-2 mt-2">
              <Button
                variant={decision === 'approve' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDecision('approve')}
              >
                批准
              </Button>
              <Button
                variant={decision === 'reject' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDecision('reject')}
              >
                拒绝
              </Button>
              <Button
                variant={decision === 'defer' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDecision('defer')}
              >
                暂缓
              </Button>
            </div>
          </div>
          
          <div>
            <label className="text-sm font-medium">审核理由</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full mt-2 px-3 py-2 border rounded-md text-sm"
              rows={3}
              placeholder="请输入审核理由..."
            />
          </div>
        </div>
        
        <div className="flex justify-end space-x-2 mt-6">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={submitDecision.isPending}
          >
            {submitDecision.isPending ? '提交中...' : '提交'}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function PendingReviewsPage() {
  const { isLoading } = usePendingReviews()
  const { pendingReviews: reviews, setSelectedReview } = useReviewStore()
  const [quickReviewId, setQuickReviewId] = useState<string | null>(null)
  
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">待审核策略</h2>
        <div className="flex items-center space-x-2">
          <Button variant="outline" asChild>
            <Link href="/dashboard">返回工作台</Link>
          </Button>
        </div>
      </div>

      {/* 筛选条件 */}
      <ReviewFilters />

      {/* 策略列表 */}
      <Card>
        <CardHeader>
          <CardTitle>策略列表</CardTitle>
          <CardDescription>
            共 {reviews.length} 个待审核策略
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-muted-foreground">加载中...</div>
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-muted-foreground">暂无待审核策略</div>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>策略ID</TableHead>
                    <TableHead>交易对</TableHead>
                    <TableHead>策略类型</TableHead>
                    <TableHead>预期收益</TableHead>
                    <TableHead>最大回撤</TableHead>
                    <TableHead>风险等级</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>提交时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reviews.map((review) => (
                    <TableRow key={review.id}>
                      <TableCell className="font-medium">
                        {review.strategy_id}
                      </TableCell>
                      <TableCell>{review.symbol}</TableCell>
                      <TableCell>{review.strategy_type}</TableCell>
                      <TableCell className="text-green-600">
                        {formatPercentage(review.expected_return)}
                      </TableCell>
                      <TableCell className="text-red-600">
                        {formatPercentage(review.max_drawdown)}
                      </TableCell>
                      <TableCell>
                        <Badge className={getRiskLevelColor(review.risk_level)}>
                          {review.risk_level}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(review.status)}>
                          {review.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(review.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedReview(review)}
                            asChild
                          >
                            <Link href={`/reviews/detail/${review.id}`}>
                              <Eye className="h-4 w-4" />
                            </Link>
                          </Button>
                          {review.status === 'pending' && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-green-600 hover:text-green-700"
                                onClick={() => setQuickReviewId(review.id)}
                              >
                                <CheckCircle className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              <div className="mt-4">
                <Pagination />
              </div>
            </>
          )}
        </CardContent>
      </Card>
      
      {/* 快速审核对话框 */}
      <QuickReviewDialog
        reviewId={quickReviewId}
        isOpen={!!quickReviewId}
        onClose={() => setQuickReviewId(null)}
      />
    </div>
  )
}