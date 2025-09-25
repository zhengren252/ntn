import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Eye, 
  FileText, 
  TrendingUp,
  DollarSign,
  BarChart3,
  Calendar,
  User,
  Filter,
  Search,
  Download,
  RefreshCw
} from 'lucide-react'
import { useReviewQueue, useReviewActions } from '@/hooks/useApi'
import { cn } from '@/lib/utils'

interface ReviewItem {
  id: string
  type: 'strategy' | 'trade' | 'risk_adjustment' | 'system_config'
  title: string
  description: string
  submitter: string
  submitTime: string
  priority: 'high' | 'medium' | 'low'
  status: 'pending' | 'in_review' | 'approved' | 'rejected'
  estimatedImpact: {
    risk: number
    profit: number
    complexity: number
  }
  details: {
    strategy?: {
      name: string
      algorithm: string
      backtestResults: {
        totalReturn: number
        sharpeRatio: number
        maxDrawdown: number
        winRate: number
      }
    }
    trade?: {
      symbol: string
      action: 'buy' | 'sell'
      quantity: number
      price: number
      reasoning: string
    }
    riskAdjustment?: {
      currentLimit: number
      proposedLimit: number
      justification: string
    }
  }
}

interface ReviewWorkflowProps {
  className?: string
}

export const ReviewWorkflow: React.FC<ReviewWorkflowProps> = ({ className }) => {
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterType, setFilterType] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  
  // API hooks
  const { data: reviewQueue, isLoading, refetch } = useReviewQueue()
  const { approveReview, rejectReview } = useReviewActions()

  // Mock data for demonstration
  const mockReviewItems: ReviewItem[] = [
    {
      id: '1',
      type: 'strategy',
      title: 'AI动量策略v2.1',
      description: '基于深度学习的动量交易策略，优化了风险控制参数',
      submitter: 'AI策略生成器',
      submitTime: '2024-01-15 14:30:00',
      priority: 'high',
      status: 'pending',
      estimatedImpact: {
        risk: 75,
        profit: 85,
        complexity: 60
      },
      details: {
        strategy: {
          name: 'AI动量策略v2.1',
          algorithm: 'LSTM + Transformer',
          backtestResults: {
            totalReturn: 23.5,
            sharpeRatio: 1.85,
            maxDrawdown: -8.2,
            winRate: 68.5
          }
        }
      }
    },
    {
      id: '2',
      type: 'trade',
      title: '大额交易执行申请',
      description: 'AAPL股票大额买入订单，需要人工确认',
      submitter: '交易执行模块',
      submitTime: '2024-01-15 15:45:00',
      priority: 'high',
      status: 'in_review',
      estimatedImpact: {
        risk: 60,
        profit: 70,
        complexity: 30
      },
      details: {
        trade: {
          symbol: 'AAPL',
          action: 'buy',
          quantity: 10000,
          price: 185.50,
          reasoning: 'AI模型预测未来5日上涨概率85%，技术指标显示突破信号'
        }
      }
    },
    {
      id: '3',
      type: 'risk_adjustment',
      title: '风险限额调整申请',
      description: '申请提高单笔交易风险限额至5%',
      submitter: '风险管理模块',
      submitTime: '2024-01-15 16:20:00',
      priority: 'medium',
      status: 'pending',
      estimatedImpact: {
        risk: 90,
        profit: 40,
        complexity: 20
      },
      details: {
        riskAdjustment: {
          currentLimit: 3,
          proposedLimit: 5,
          justification: '当前市场波动率降低，可适当提高风险敞口以获取更高收益'
        }
      }
    }
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'in_review':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'approved':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4" />
      case 'in_review':
        return <Eye className="h-4 w-4" />
      case 'approved':
        return <CheckCircle className="h-4 w-4" />
      case 'rejected':
        return <XCircle className="h-4 w-4" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'strategy':
        return <BarChart3 className="h-4 w-4" />
      case 'trade':
        return <DollarSign className="h-4 w-4" />
      case 'risk_adjustment':
        return <AlertTriangle className="h-4 w-4" />
      case 'system_config':
        return <FileText className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const handleApprove = async (itemId: string) => {
    try {
      await approveReview.mutateAsync({ reviewId: itemId, action: 'approve' })
      setSelectedItem(null)
      refetch()
    } catch (error) {
      console.error('审核通过失败:', error)
    }
  }

  const handleReject = async (itemId: string) => {
    if (!rejectReason.trim()) {
      alert('请填写拒绝原因')
      return
    }
    
    try {
      await rejectReview.mutateAsync({ reviewId: itemId, reason: rejectReason })
      setSelectedItem(null)
      setRejectReason('')
      refetch()
    } catch (error) {
      console.error('审核拒绝失败:', error)
    }
  }

  const filteredItems = mockReviewItems.filter(item => {
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus
    const matchesType = filterType === 'all' || item.type === filterType
    const matchesSearch = searchQuery === '' || 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase())
    
    return matchesStatus && matchesType && matchesSearch
  })

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 2
    }).format(value)
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* 头部操作栏 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl font-semibold">人工审核工作流</CardTitle>
              <CardDescription>管理和审核系统自动生成的策略、交易和配置变更</CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                刷新
              </Button>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                导出
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            {/* 搜索框 */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="搜索审核项目..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            {/* 筛选器 */}
            <div className="flex gap-2">
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="pending">待审核</SelectItem>
                  <SelectItem value="in_review">审核中</SelectItem>
                  <SelectItem value="approved">已通过</SelectItem>
                  <SelectItem value="rejected">已拒绝</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="strategy">策略</SelectItem>
                  <SelectItem value="trade">交易</SelectItem>
                  <SelectItem value="risk_adjustment">风险调整</SelectItem>
                  <SelectItem value="system_config">系统配置</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 统计概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-yellow-500" />
              <div>
                <div className="text-2xl font-bold">8</div>
                <div className="text-sm text-gray-500">待审核</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Eye className="h-5 w-5 text-blue-500" />
              <div>
                <div className="text-2xl font-bold">3</div>
                <div className="text-sm text-gray-500">审核中</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <div>
                <div className="text-2xl font-bold">25</div>
                <div className="text-sm text-gray-500">已通过</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <XCircle className="h-5 w-5 text-red-500" />
              <div>
                <div className="text-2xl font-bold">5</div>
                <div className="text-sm text-gray-500">已拒绝</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 审核列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">审核队列</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredItems.map((item) => (
              <div key={item.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {getTypeIcon(item.type)}
                      <h3 className="font-semibold text-lg">{item.title}</h3>
                      <Badge className={getPriorityColor(item.priority)}>
                        {item.priority}
                      </Badge>
                      <Badge className={getStatusColor(item.status)}>
                        {getStatusIcon(item.status)}
                        <span className="ml-1">{item.status}</span>
                      </Badge>
                    </div>
                    
                    <p className="text-gray-600 mb-3">{item.description}</p>
                    
                    <div className="flex items-center space-x-6 text-sm text-gray-500">
                      <div className="flex items-center space-x-1">
                        <User className="h-4 w-4" />
                        <span>{item.submitter}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{item.submitTime}</span>
                      </div>
                    </div>
                    
                    {/* 影响评估 */}
                    <div className="mt-3 grid grid-cols-3 gap-4">
                      <div className="text-center">
                        <div className="text-xs text-gray-500">风险影响</div>
                        <div className={cn(
                          'text-sm font-medium',
                          item.estimatedImpact.risk > 70 ? 'text-red-600' :
                          item.estimatedImpact.risk > 40 ? 'text-yellow-600' : 'text-green-600'
                        )}>
                          {item.estimatedImpact.risk}%
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-500">收益潜力</div>
                        <div className={cn(
                          'text-sm font-medium',
                          item.estimatedImpact.profit > 70 ? 'text-green-600' :
                          item.estimatedImpact.profit > 40 ? 'text-yellow-600' : 'text-red-600'
                        )}>
                          {item.estimatedImpact.profit}%
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-xs text-gray-500">复杂度</div>
                        <div className={cn(
                          'text-sm font-medium',
                          item.estimatedImpact.complexity > 70 ? 'text-red-600' :
                          item.estimatedImpact.complexity > 40 ? 'text-yellow-600' : 'text-green-600'
                        )}>
                          {item.estimatedImpact.complexity}%
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex flex-col space-y-2 ml-4">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm" onClick={() => setSelectedItem(item)}>
                          <Eye className="h-4 w-4 mr-2" />
                          查看详情
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                          <DialogTitle className="flex items-center space-x-2">
                            {getTypeIcon(item.type)}
                            <span>{item.title}</span>
                          </DialogTitle>
                          <DialogDescription>{item.description}</DialogDescription>
                        </DialogHeader>
                        
                        {selectedItem && (
                          <div className="space-y-6">
                            {/* 基本信息 */}
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <Label className="text-sm font-medium">提交者</Label>
                                <div className="mt-1 text-sm">{selectedItem.submitter}</div>
                              </div>
                              <div>
                                <Label className="text-sm font-medium">提交时间</Label>
                                <div className="mt-1 text-sm">{selectedItem.submitTime}</div>
                              </div>
                            </div>
                            
                            {/* 详细信息 */}
                            {selectedItem.details.strategy && (
                              <div className="space-y-4">
                                <h4 className="font-semibold">策略详情</h4>
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label className="text-sm font-medium">策略名称</Label>
                                    <div className="mt-1 text-sm">{selectedItem.details.strategy.name}</div>
                                  </div>
                                  <div>
                                    <Label className="text-sm font-medium">算法类型</Label>
                                    <div className="mt-1 text-sm">{selectedItem.details.strategy.algorithm}</div>
                                  </div>
                                </div>
                                
                                <div>
                                  <Label className="text-sm font-medium">回测结果</Label>
                                  <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="text-center p-3 bg-gray-50 rounded">
                                      <div className="text-lg font-bold text-green-600">
                                        {selectedItem.details.strategy.backtestResults.totalReturn}%
                                      </div>
                                      <div className="text-xs text-gray-500">总收益率</div>
                                    </div>
                                    <div className="text-center p-3 bg-gray-50 rounded">
                                      <div className="text-lg font-bold">
                                        {selectedItem.details.strategy.backtestResults.sharpeRatio}
                                      </div>
                                      <div className="text-xs text-gray-500">夏普比率</div>
                                    </div>
                                    <div className="text-center p-3 bg-gray-50 rounded">
                                      <div className="text-lg font-bold text-red-600">
                                        {selectedItem.details.strategy.backtestResults.maxDrawdown}%
                                      </div>
                                      <div className="text-xs text-gray-500">最大回撤</div>
                                    </div>
                                    <div className="text-center p-3 bg-gray-50 rounded">
                                      <div className="text-lg font-bold">
                                        {selectedItem.details.strategy.backtestResults.winRate}%
                                      </div>
                                      <div className="text-xs text-gray-500">胜率</div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                            
                            {selectedItem.details.trade && (
                              <div className="space-y-4">
                                <h4 className="font-semibold">交易详情</h4>
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label className="text-sm font-medium">交易标的</Label>
                                    <div className="mt-1 text-sm font-mono">{selectedItem.details.trade.symbol}</div>
                                  </div>
                                  <div>
                                    <Label className="text-sm font-medium">交易方向</Label>
                                    <div className="mt-1">
                                      <Badge className={selectedItem.details.trade.action === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                                        {selectedItem.details.trade.action === 'buy' ? '买入' : '卖出'}
                                      </Badge>
                                    </div>
                                  </div>
                                  <div>
                                    <Label className="text-sm font-medium">数量</Label>
                                    <div className="mt-1 text-sm">{selectedItem.details.trade.quantity.toLocaleString()} 股</div>
                                  </div>
                                  <div>
                                    <Label className="text-sm font-medium">价格</Label>
                                    <div className="mt-1 text-sm font-mono">${selectedItem.details.trade.price}</div>
                                  </div>
                                </div>
                                <div>
                                  <Label className="text-sm font-medium">交易理由</Label>
                                  <div className="mt-1 text-sm p-3 bg-gray-50 rounded">{selectedItem.details.trade.reasoning}</div>
                                </div>
                              </div>
                            )}
                            
                            {selectedItem.details.riskAdjustment && (
                              <div className="space-y-4">
                                <h4 className="font-semibold">风险调整详情</h4>
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label className="text-sm font-medium">当前限额</Label>
                                    <div className="mt-1 text-sm">{selectedItem.details.riskAdjustment.currentLimit}%</div>
                                  </div>
                                  <div>
                                    <Label className="text-sm font-medium">建议限额</Label>
                                    <div className="mt-1 text-sm font-bold">{selectedItem.details.riskAdjustment.proposedLimit}%</div>
                                  </div>
                                </div>
                                <div>
                                  <Label className="text-sm font-medium">调整理由</Label>
                                  <div className="mt-1 text-sm p-3 bg-gray-50 rounded">{selectedItem.details.riskAdjustment.justification}</div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        
                        <DialogFooter className="space-x-2">
                          {selectedItem?.status === 'pending' && (
                            <>
                              <Dialog>
                                <DialogTrigger asChild>
                                  <Button variant="destructive">
                                    <XCircle className="h-4 w-4 mr-2" />
                                    拒绝
                                  </Button>
                                </DialogTrigger>
                                <DialogContent>
                                  <DialogHeader>
                                    <DialogTitle>拒绝审核</DialogTitle>
                                    <DialogDescription>
                                      请说明拒绝的原因，这将帮助系统改进。
                                    </DialogDescription>
                                  </DialogHeader>
                                  <div className="space-y-4">
                                    <div>
                                      <Label htmlFor="reject-reason">拒绝原因</Label>
                                      <Textarea
                                        id="reject-reason"
                                        placeholder="请详细说明拒绝的原因..."
                                        value={rejectReason}
                                        onChange={(e) => setRejectReason(e.target.value)}
                                        className="mt-1"
                                      />
                                    </div>
                                  </div>
                                  <DialogFooter>
                                    <Button 
                                      variant="destructive" 
                                      onClick={() => selectedItem && handleReject(selectedItem.id)}
                                      disabled={!rejectReason.trim()}
                                    >
                                      确认拒绝
                                    </Button>
                                  </DialogFooter>
                                </DialogContent>
                              </Dialog>
                              
                              <Button 
                                onClick={() => selectedItem && handleApprove(selectedItem.id)}
                                className="bg-green-600 hover:bg-green-700"
                              >
                                <CheckCircle className="h-4 w-4 mr-2" />
                                通过审核
                              </Button>
                            </>
                          )}
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                    
                    {item.status === 'pending' && (
                      <div className="flex space-x-2">
                        <Button 
                          size="sm" 
                          variant="destructive"
                          onClick={() => {
                            setSelectedItem(item)
                            // 这里可以直接打开拒绝对话框
                          }}
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                        <Button 
                          size="sm" 
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => handleApprove(item.id)}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {filteredItems.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <div className="text-lg font-medium mb-2">暂无审核项目</div>
                <div className="text-sm">当前没有符合筛选条件的审核项目</div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ReviewWorkflow