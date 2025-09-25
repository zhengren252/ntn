'use client'

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useSystemStatus } from '@/hooks/use-reviews'
import { useReviewStore } from '@/store/review-store'
import { formatDate, formatPercentage, getRiskLevelColor, getStatusColor } from '@/lib/utils'
import { Eye, CheckCircle, XCircle, Clock, TrendingUp, AlertTriangle, Activity } from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const { data: systemStatus, isLoading: statusLoading } = useSystemStatus()
  const { pendingReviews: reviews, setSelectedReview } = useReviewStore()

  // 统计数据
  const stats = {
    total: reviews.length,
    pending: reviews.filter(r => r.status === 'pending').length,
    processing: reviews.filter(r => r.status === 'processing').length,
    highRisk: reviews.filter(r => r.risk_level === 'high').length
  }

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">审核工作台</h2>
        <div className="flex items-center space-x-2">
          <Button asChild>
            <Link href="/reviews/pending">查看全部待审核</Link>
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">待审核总数</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.pending}</div>
            <p className="text-xs text-muted-foreground">
              共 {stats.total} 个策略
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">处理中</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.processing}</div>
            <p className="text-xs text-muted-foreground">
              正在审核中
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">高风险策略</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.highRisk}</div>
            <p className="text-xs text-muted-foreground">
              需要重点关注
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日处理</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemStatus?.processed_today || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              平均用时 {systemStatus?.avg_processing_time || 0} 分钟
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 系统状态 */}
      {systemStatus && (
        <Card>
          <CardHeader>
            <CardTitle>系统状态</CardTitle>
            <CardDescription>实时监控系统运行状态</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`h-2 w-2 rounded-full ${
                  systemStatus.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <span className="text-sm font-medium">
                  {systemStatus.status === 'healthy' ? '系统正常' : '系统异常'}
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                系统负载: {(systemStatus.system_load * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-muted-foreground">
                待处理: {systemStatus.pending_count} 个
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 最近待审核策略 */}
      <Card>
        <CardHeader>
          <CardTitle>最近待审核策略</CardTitle>
          <CardDescription>
            显示最新提交的策略，点击查看详情
          </CardDescription>
        </CardHeader>
        <CardContent>
          {statusLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-muted-foreground">加载中...</div>
            </div>
          ) : reviews.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-muted-foreground">暂无待审核策略</div>
            </div>
          ) : (
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
                {reviews.slice(0, 5).map((review) => (
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
                            >
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-red-600 hover:text-red-700"
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          
          {reviews.length > 5 && (
            <div className="mt-4 text-center">
              <Button variant="outline" asChild>
                <Link href="/reviews/pending">
                  查看全部 {reviews.length} 个待审核策略
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}