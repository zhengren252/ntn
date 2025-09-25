'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useReviewHistory } from '@/hooks/use-reviews'
import { formatDate, getStatusColor } from '@/lib/utils'

// 辅助函数：根据时间范围获取开始日期
function getStartDate(timeRange: string): string | undefined {
  const now = new Date()
  switch (timeRange) {
    case '7d':
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      return weekAgo.toISOString()
    case '30d':
      const monthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate())
      return monthAgo.toISOString()
    case '90d':
      const quarterAgo = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate())
      return quarterAgo.toISOString()
    default:
      return undefined
  }
}

// 辅助函数：根据时间范围获取结束日期
function getEndDate(timeRange: string): string | undefined {
  const now = new Date()
  switch (timeRange) {
    case '7d':
    case '30d':
    case '90d':
      return now.toISOString()
    default:
      return undefined
  }
}
import { Search, Filter, Clock, CheckCircle, XCircle } from 'lucide-react'
import Link from 'next/link'

type FilterStatus = 'all' | 'approved' | 'rejected' | 'deferred'
type FilterTimeRange = '7d' | '30d' | '90d' | 'all'

export default function ReviewHistoryPage() {
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')
  const [timeRangeFilter, setTimeRangeFilter] = useState<FilterTimeRange>('30d')
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 20
  
  const { data: historyData, isLoading, error } = useReviewHistory({
    page: currentPage,
    limit: pageSize,
    start_date: timeRangeFilter === 'all' ? undefined : getStartDate(timeRangeFilter),
    end_date: timeRangeFilter === 'all' ? undefined : getEndDate(timeRangeFilter)
  })
  
  const reviews = historyData?.data || []
  const pagination = historyData?.page_info
  const total = historyData?.total || 0
  
  // 过滤选项
  const statusOptions = [
    { value: 'all', label: '全部状态', icon: Filter },
    { value: 'approved', label: '已批准', icon: CheckCircle },
    { value: 'rejected', label: '已拒绝', icon: XCircle },
    { value: 'deferred', label: '已暂缓', icon: Clock }
  ]
  
  const timeRangeOptions = [
    { value: '7d', label: '最近7天' },
    { value: '30d', label: '最近30天' },
    { value: '90d', label: '最近90天' },
    { value: 'all', label: '全部时间' }
  ]
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setCurrentPage(1)
  }
  
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-medium">加载中...</div>
          <div className="text-sm text-muted-foreground mt-2">正在获取审核历史</div>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-medium text-red-600">加载失败</div>
          <div className="text-sm text-muted-foreground mt-2">
            {error instanceof Error ? error.message : '无法获取审核历史'}
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">审核历史</h1>
          <p className="text-muted-foreground">查看已完成的策略审核记录</p>
        </div>
      </div>
      
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总审核数</CardTitle>
            <Filter className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{total}</div>
            <p className="text-xs text-muted-foreground">
              当前筛选条件
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已批准</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
               {reviews.filter(r => r.decision === 'approve').length}
             </div>
            <p className="text-xs text-muted-foreground">
              当前页面数据
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已拒绝</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
               {reviews.filter(r => r.decision === 'reject').length}
             </div>
            <p className="text-xs text-muted-foreground">
              当前页面数据
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已暂缓</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
               {reviews.filter(r => r.decision === 'defer').length}
             </div>
            <p className="text-xs text-muted-foreground">
              当前页面数据
            </p>
          </CardContent>
        </Card>
      </div>
      
      {/* 过滤和搜索 */}
      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            {/* 搜索框 */}
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="搜索策略ID、交易对或审核员..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-md text-sm"
                />
              </div>
            </form>
            
            {/* 状态过滤 */}
            <div className="flex space-x-2">
              {statusOptions.map((option) => {
                const Icon = option.icon
                return (
                  <Button
                    key={option.value}
                    variant={statusFilter === option.value ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => {
                      setStatusFilter(option.value as FilterStatus)
                      setCurrentPage(1)
                    }}
                    className="flex items-center space-x-1"
                  >
                    <Icon className="h-4 w-4" />
                    <span>{option.label}</span>
                  </Button>
                )
              })}
            </div>
            
            {/* 时间范围过滤 */}
            <div className="flex space-x-2">
              {timeRangeOptions.map((option) => (
                <Button
                  key={option.value}
                  variant={timeRangeFilter === option.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    setTimeRangeFilter(option.value as FilterTimeRange)
                    setCurrentPage(1)
                  }}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* 审核历史表格 */}
      <Card>
        <CardHeader>
          <CardTitle>审核记录</CardTitle>
          <CardDescription>
            {pagination && (
              `显示第 ${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, pagination.total)} 条，共 ${pagination.total} 条记录`
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reviews.length > 0 ? (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>策略信息</TableHead>
                    <TableHead>风险等级</TableHead>
                    <TableHead>审核结果</TableHead>
                    <TableHead>审核员</TableHead>
                    <TableHead>审核时间</TableHead>
                    <TableHead>处理时长</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reviews.map((review) => (
                    <TableRow key={review.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{review.strategy_review_id}</div>
                          <div className="text-sm text-muted-foreground">
                            审核决策记录
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {review.decision}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Badge className={getStatusColor(review.decision)}>
                            {review.decision === 'approve' && '已批准'}
                            {review.decision === 'reject' && '已拒绝'}
                            {review.decision === 'defer' && '已暂缓'}
                          </Badge>
                          {review.reason && (
                            <div className="text-xs text-muted-foreground max-w-32 truncate">
                              {review.reason}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                          <div className="text-sm">{review.reviewer_id}</div>
                        </TableCell>
                      <TableCell>
                          <div className="text-sm">
                            <div>{formatDate(review.decision_time)}</div>
                            <div className="text-muted-foreground">
                              决策时间
                            </div>
                          </div>
                        </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          -
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/reviews/detail/${review.strategy_review_id}`}>
                            查看详情
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              {/* 分页 */}
              {pagination && pagination.total_pages > 1 && (
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    第 {currentPage} 页，共 {pagination.total_pages} 页
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                    >
                      上一页
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.min(pagination.total_pages, prev + 1))}
                      disabled={currentPage === pagination.total_pages}
                    >
                      下一页
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-muted-foreground">暂无审核记录</div>
              <div className="text-sm text-muted-foreground mt-2">
                尝试调整筛选条件或时间范围
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}