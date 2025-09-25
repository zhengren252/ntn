import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

import { 
  TrendingUp, 
  PieChart, 
  BarChart3, 
  CheckCircle, 
  XCircle, 
  Clock,
  AlertTriangle,
  CreditCard,
  Wallet,
  Calculator,
  FileText,
  RefreshCw,
  Download,
  Target
} from 'lucide-react';

interface BudgetRequest {
  id: string;
  strategyId: string;
  strategyName: string;
  requestedBy: string;
  amount: number;
  purpose: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'approved' | 'rejected' | 'partial';
  approvedAmount?: number;
  rejectionReason?: string;
  requestedAt: string;
  reviewedAt?: string;
  expectedROI: number;
  riskLevel: number;
}

interface Account {
  id: string;
  name: string;
  type: 'trading' | 'settlement' | 'margin' | 'reserve';
  balance: number;
  availableBalance: number;
  frozenAmount: number;
  currency: string;
  lastUpdate: string;
  healthScore: number;
  status: 'healthy' | 'warning' | 'critical';
}

interface Transaction {
  id: string;
  type: 'deposit' | 'withdrawal' | 'transfer' | 'trade_settlement' | 'fee' | 'interest';
  amount: number;
  currency: string;
  fromAccount?: string;
  toAccount?: string;
  description: string;
  status: 'pending' | 'completed' | 'failed' | 'cancelled';
  timestamp: string;
  reference?: string;
}

interface AllocationRule {
  id: string;
  name: string;
  strategyType: string;
  maxAllocation: number;
  currentAllocation: number;
  riskWeight: number;
  priority: number;
  isActive: boolean;
  lastModified: string;
}

interface FinancialMetrics {
  totalAssets: number;
  availableFunds: number;
  allocatedFunds: number;
  dailyPnL: number;
  monthlyPnL: number;
  utilizationRate: number;
  riskExposure: number;
}

const FinanceManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'budget' | 'accounts' | 'allocation' | 'transactions'>('budget');
  const [isLoading, setIsLoading] = useState(false);
  
  // 预算申请数据
  const [budgetRequests, setBudgetRequests] = useState<BudgetRequest[]>([
    {
      id: 'BUD001',
      strategyId: 'STR001',
      strategyName: '动量突破策略',
      requestedBy: '张交易员',
      amount: 500000,
      purpose: '执行动量突破策略，预期月收益15%',
      priority: 'high',
      status: 'approved',
      approvedAmount: 500000,
      requestedAt: '2024-01-15 09:25:00',
      reviewedAt: '2024-01-15 10:30:00',
      expectedROI: 15.8,
      riskLevel: 7.2
    },
    {
      id: 'BUD002',
      strategyId: 'STR003',
      strategyName: '高频交易策略',
      requestedBy: '李交易员',
      amount: 1000000,
      purpose: '高频交易策略启动资金，日内交易',
      priority: 'urgent',
      status: 'pending',
      requestedAt: '2024-01-15 14:25:00',
      expectedROI: 22.1,
      riskLevel: 8.9
    },
    {
      id: 'BUD003',
      strategyId: 'STR004',
      strategyName: '套利策略',
      requestedBy: '王交易员',
      amount: 300000,
      purpose: '跨市场套利机会，低风险稳定收益',
      priority: 'medium',
      status: 'rejected',
      rejectionReason: '当前资金紧张，建议降低申请金额',
      requestedAt: '2024-01-15 11:20:00',
      reviewedAt: '2024-01-15 13:15:00',
      expectedROI: 8.5,
      riskLevel: 4.2
    }
  ]);

  // 账户数据
  const [accounts] = useState<Account[]>([
    {
      id: 'ACC001',
      name: '主交易账户',
      type: 'trading',
      balance: 2500000,
      availableBalance: 1800000,
      frozenAmount: 700000,
      currency: 'USD',
      lastUpdate: '2分钟前',
      healthScore: 85,
      status: 'healthy'
    },
    {
      id: 'ACC002',
      name: '结算账户',
      type: 'settlement',
      balance: 500000,
      availableBalance: 500000,
      frozenAmount: 0,
      currency: 'USD',
      lastUpdate: '5分钟前',
      healthScore: 95,
      status: 'healthy'
    },
    {
      id: 'ACC003',
      name: '保证金账户',
      type: 'margin',
      balance: 800000,
      availableBalance: 200000,
      frozenAmount: 600000,
      currency: 'USD',
      lastUpdate: '1分钟前',
      healthScore: 65,
      status: 'warning'
    },
    {
      id: 'ACC004',
      name: '风险准备金',
      type: 'reserve',
      balance: 1000000,
      availableBalance: 1000000,
      frozenAmount: 0,
      currency: 'USD',
      lastUpdate: '10分钟前',
      healthScore: 100,
      status: 'healthy'
    }
  ]);

  // 交易记录数据
  const [transactions] = useState<Transaction[]>([
    {
      id: 'TXN001',
      type: 'trade_settlement',
      amount: 18500,
      currency: 'USD',
      fromAccount: 'ACC001',
      toAccount: 'ACC002',
      description: 'AAPL交易结算',
      status: 'completed',
      timestamp: '2024-01-15 15:30:00',
      reference: 'ORD001'
    },
    {
      id: 'TXN002',
      type: 'transfer',
      amount: 500000,
      currency: 'USD',
      fromAccount: 'ACC004',
      toAccount: 'ACC001',
      description: '策略资金分配',
      status: 'completed',
      timestamp: '2024-01-15 10:30:00',
      reference: 'BUD001'
    },
    {
      id: 'TXN003',
      type: 'fee',
      amount: -250,
      currency: 'USD',
      fromAccount: 'ACC001',
      description: '交易手续费',
      status: 'completed',
      timestamp: '2024-01-15 14:20:00'
    }
  ]);

  // 资金分配规则
  const [allocationRules] = useState<AllocationRule[]>([
    {
      id: 'RULE001',
      name: '趋势跟踪策略',
      strategyType: 'trend_following',
      maxAllocation: 40,
      currentAllocation: 35,
      riskWeight: 0.7,
      priority: 1,
      isActive: true,
      lastModified: '2024-01-10 09:00:00'
    },
    {
      id: 'RULE002',
      name: '统计套利策略',
      strategyType: 'statistical_arbitrage',
      maxAllocation: 30,
      currentAllocation: 25,
      riskWeight: 0.5,
      priority: 2,
      isActive: true,
      lastModified: '2024-01-12 14:30:00'
    },
    {
      id: 'RULE003',
      name: '高频交易策略',
      strategyType: 'high_frequency',
      maxAllocation: 20,
      currentAllocation: 0,
      riskWeight: 0.9,
      priority: 3,
      isActive: false,
      lastModified: '2024-01-08 11:15:00'
    }
  ]);

  // 财务指标
  const [financialMetrics] = useState<FinancialMetrics>({
    totalAssets: 4800000,
    availableFunds: 3500000,
    allocatedFunds: 1300000,
    dailyPnL: 25600,
    monthlyPnL: 384000,
    utilizationRate: 72.5,
    riskExposure: 68.2
  });

  // 当前审批的申请
  const [currentReview, setCurrentReview] = useState<string | null>(null);
  const [reviewFeedback, setReviewFeedback] = useState('');
  const [approvedAmount, setApprovedAmount] = useState('');

  // 处理预算审批
  const handleBudgetReview = async (requestId: string, decision: 'approved' | 'rejected' | 'partial') => {
    setIsLoading(true);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setBudgetRequests(prev => prev.map(request => 
      request.id === requestId 
        ? { 
            ...request, 
            status: decision,
            approvedAmount: decision === 'approved' ? request.amount : 
                          decision === 'partial' ? parseFloat(approvedAmount) || 0 : undefined,
            rejectionReason: decision === 'rejected' ? reviewFeedback : undefined,
            reviewedAt: new Date().toLocaleString()
          }
        : request
    ));
    
    setCurrentReview(null);
    setReviewFeedback('');
    setApprovedAmount('');
    setIsLoading(false);
  };

  // 获取优先级颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
      case 'completed':
      case 'healthy':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'pending':
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'rejected':
      case 'failed':
      case 'cancelled':
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'partial':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 获取账户类型标签
  const getAccountTypeLabel = (type: string) => {
    switch (type) {
      case 'trading': return '交易账户';
      case 'settlement': return '结算账户';
      case 'margin': return '保证金账户';
      case 'reserve': return '准备金账户';
      default: return type;
    }
  };

  // 获取交易类型标签
  const getTransactionTypeLabel = (type: string) => {
    switch (type) {
      case 'deposit': return '存款';
      case 'withdrawal': return '提款';
      case 'transfer': return '转账';
      case 'trade_settlement': return '交易结算';
      case 'fee': return '手续费';
      case 'interest': return '利息';
      default: return type;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">财务管理台</h1>
            <p className="text-gray-600 mt-1">预算审批 · 账户管理 · 资金分配 · 交易记录</p>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="outline" className="flex items-center space-x-2">
              <RefreshCw className="w-4 h-4" />
              <span>刷新数据</span>
            </Button>
            <Button variant="outline" className="flex items-center space-x-2">
              <Download className="w-4 h-4" />
              <span>导出报告</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 财务指标概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总资产</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              ${financialMetrics.totalAssets.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              可用: ${financialMetrics.availableFunds.toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日盈亏</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              financialMetrics.dailyPnL >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              ${financialMetrics.dailyPnL.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              月度: ${financialMetrics.monthlyPnL.toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">资金利用率</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              {financialMetrics.utilizationRate}%
            </div>
            <Progress value={financialMetrics.utilizationRate} className="mt-2" />
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">待审批</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {budgetRequests.filter(r => r.status === 'pending').length}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              预算申请待处理
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 标签页导航 */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { key: 'budget', label: '预算审批', icon: Calculator },
              { key: 'accounts', label: '账户管理', icon: CreditCard },
              { key: 'allocation', label: '资金分配', icon: PieChart },
              { key: 'transactions', label: '交易记录', icon: FileText }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as 'budget' | 'accounts' | 'allocation' | 'transactions')}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* 预算审批 */}
      {activeTab === 'budget' && (
        <div className="space-y-6">
          {budgetRequests.map((request) => (
            <Card key={request.id} className="bg-white">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-2">
                      <Calculator className="w-5 h-5" />
                      <span>{request.strategyName}</span>
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      申请人: {request.requestedBy} | 策略ID: {request.strategyId}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className={getPriorityColor(request.priority)}>
                      {request.priority}
                    </Badge>
                    <Badge className={getStatusColor(request.status)}>
                      {request.status === 'approved' && <CheckCircle className="w-4 h-4 mr-1" />}
                      {request.status === 'rejected' && <XCircle className="w-4 h-4 mr-1" />}
                      {request.status === 'pending' && <Clock className="w-4 h-4 mr-1" />}
                      {request.status === 'partial' && <Target className="w-4 h-4 mr-1" />}
                      {request.status}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 申请详情 */}
                  <div>
                    <h4 className="font-medium mb-3">申请详情</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-500">申请金额:</span>
                        <span className="font-medium">${request.amount.toLocaleString()}</span>
                      </div>
                      {request.approvedAmount && (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-500">批准金额:</span>
                          <span className="font-medium text-green-600">
                            ${request.approvedAmount.toLocaleString()}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-500">预期ROI:</span>
                        <span className="font-medium text-blue-600">{request.expectedROI}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-500">风险等级:</span>
                        <span className={`font-medium ${
                          request.riskLevel <= 5 ? 'text-green-600' :
                          request.riskLevel <= 7 ? 'text-yellow-600' :
                          request.riskLevel <= 8.5 ? 'text-orange-600' : 'text-red-600'
                        }`}>
                          {request.riskLevel}
                        </span>
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-gray-50 rounded">
                      <h5 className="font-medium text-sm mb-1">申请目的</h5>
                      <p className="text-sm text-gray-700">{request.purpose}</p>
                    </div>
                  </div>

                  {/* 风险评估 */}
                  <div>
                    <h4 className="font-medium mb-3">风险评估</h4>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">风险评分</span>
                          <span className="text-sm font-medium">{request.riskLevel}/10</span>
                        </div>
                        <Progress value={request.riskLevel * 10} />
                      </div>
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">预期收益</span>
                          <span className="text-sm font-medium">{request.expectedROI}%</span>
                        </div>
                        <Progress value={request.expectedROI * 2} className="bg-green-100" />
                      </div>
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">资金占比</span>
                          <span className="text-sm font-medium">
                            {((request.amount / financialMetrics.totalAssets) * 100).toFixed(1)}%
                          </span>
                        </div>
                        <Progress value={(request.amount / financialMetrics.totalAssets) * 100} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 拒绝原因 */}
                {request.rejectionReason && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                    <h5 className="font-medium text-sm mb-1 text-red-800">拒绝原因</h5>
                    <p className="text-sm text-red-700">{request.rejectionReason}</p>
                  </div>
                )}

                {/* 操作按钮 */}
                {request.status === 'pending' && (
                  <div className="mt-4 space-y-3">
                    {currentReview === request.id ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="approved-amount">批准金额 (部分批准时)</Label>
                            <Input
                              id="approved-amount"
                              type="number"
                              value={approvedAmount}
                              onChange={(e) => setApprovedAmount(e.target.value)}
                              placeholder={request.amount.toString()}
                            />
                          </div>
                          <div></div>
                        </div>
                        <Textarea
                          value={reviewFeedback}
                          onChange={(e) => setReviewFeedback(e.target.value)}
                          placeholder="请输入审批意见..."
                          rows={3}
                        />
                        <div className="flex space-x-3">
                          <Button
                            onClick={() => handleBudgetReview(request.id, 'approved')}
                            disabled={isLoading}
                            className="flex items-center space-x-2 bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="w-4 h-4" />
                            <span>全额批准</span>
                          </Button>
                          <Button
                            onClick={() => handleBudgetReview(request.id, 'partial')}
                            disabled={isLoading || !approvedAmount}
                            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700"
                          >
                            <Target className="w-4 h-4" />
                            <span>部分批准</span>
                          </Button>
                          <Button
                            onClick={() => handleBudgetReview(request.id, 'rejected')}
                            disabled={isLoading}
                            variant="destructive"
                            className="flex items-center space-x-2"
                          >
                            <XCircle className="w-4 h-4" />
                            <span>拒绝</span>
                          </Button>
                          <Button
                            onClick={() => setCurrentReview(null)}
                            variant="outline"
                          >
                            取消
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button
                        onClick={() => setCurrentReview(request.id)}
                        className="flex items-center space-x-2"
                      >
                        <FileText className="w-4 h-4" />
                        <span>开始审批</span>
                      </Button>
                    )}
                  </div>
                )}

                {/* 时间信息 */}
                <div className="mt-4 text-xs text-gray-500">
                  申请时间: {request.requestedAt}
                  {request.reviewedAt && (
                    <span className="ml-4">审批时间: {request.reviewedAt}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 账户管理 */}
      {activeTab === 'accounts' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {accounts.map((account) => (
            <Card key={account.id} className="bg-white">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-2">
                      <CreditCard className="w-5 h-5" />
                      <span>{account.name}</span>
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      {getAccountTypeLabel(account.type)} | {account.currency}
                    </p>
                  </div>
                  <Badge className={getStatusColor(account.status)}>
                    {account.status === 'healthy' && <CheckCircle className="w-4 h-4 mr-1" />}
                    {account.status === 'warning' && <AlertTriangle className="w-4 h-4 mr-1" />}
                    {account.status === 'critical' && <XCircle className="w-4 h-4 mr-1" />}
                    {account.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* 余额信息 */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">总余额</p>
                      <p className="text-xl font-bold">${account.balance.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">可用余额</p>
                      <p className="text-xl font-bold text-green-600">
                        ${account.availableBalance.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  
                  {account.frozenAmount > 0 && (
                    <div>
                      <p className="text-sm text-gray-500">冻结金额</p>
                      <p className="text-lg font-medium text-orange-600">
                        ${account.frozenAmount.toLocaleString()}
                      </p>
                    </div>
                  )}

                  {/* 健康评分 */}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-gray-500">账户健康评分</span>
                      <span className="text-sm font-medium">{account.healthScore}/100</span>
                    </div>
                    <Progress value={account.healthScore} />
                  </div>

                  {/* 资金利用率 */}
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-sm text-gray-500">资金利用率</span>
                      <span className="text-sm font-medium">
                        {((account.balance - account.availableBalance) / account.balance * 100).toFixed(1)}%
                      </span>
                    </div>
                    <Progress value={(account.balance - account.availableBalance) / account.balance * 100} />
                  </div>

                  <div className="text-xs text-gray-500">
                    最后更新: {account.lastUpdate}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 资金分配 */}
      {activeTab === 'allocation' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <PieChart className="w-5 h-5" />
                <span>分配规则</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {allocationRules.map((rule) => (
                  <div key={rule.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{rule.name}</h4>
                        <p className="text-sm text-gray-500">{rule.strategyType}</p>
                      </div>
                      <Badge className={rule.isActive ? getStatusColor('approved') : getStatusColor('rejected')}>
                        {rule.isActive ? '启用' : '禁用'}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>最大分配:</span>
                        <span>{rule.maxAllocation}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>当前分配:</span>
                        <span className="font-medium">{rule.currentAllocation}%</span>
                      </div>
                      <Progress value={(rule.currentAllocation / rule.maxAllocation) * 100} />
                      <div className="flex justify-between text-sm">
                        <span>风险权重:</span>
                        <span>{rule.riskWeight}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>优先级:</span>
                        <span>{rule.priority}</span>
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-gray-500">
                      最后修改: {rule.lastModified}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5" />
                <span>分配概览</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* 总体分配情况 */}
                <div>
                  <h4 className="font-medium mb-3">总体分配情况</h4>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm">已分配资金:</span>
                      <span className="font-medium">${financialMetrics.allocatedFunds.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">可用资金:</span>
                      <span className="font-medium text-green-600">
                        ${financialMetrics.availableFunds.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">利用率:</span>
                      <span className="font-medium">{financialMetrics.utilizationRate}%</span>
                    </div>
                    <Progress value={financialMetrics.utilizationRate} />
                  </div>
                </div>

                {/* 风险暴露 */}
                <div>
                  <h4 className="font-medium mb-3">风险暴露</h4>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm">风险暴露度:</span>
                      <span className={`font-medium ${
                        financialMetrics.riskExposure <= 50 ? 'text-green-600' :
                        financialMetrics.riskExposure <= 75 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {financialMetrics.riskExposure}%
                      </span>
                    </div>
                    <Progress value={financialMetrics.riskExposure} />
                    <p className="text-xs text-gray-500">
                      建议保持在75%以下
                    </p>
                  </div>
                </div>

                {/* 分配图表区域 */}
                <div>
                  <h4 className="font-medium mb-3">分配图表</h4>
                  <div className="h-48 flex items-center justify-center bg-gray-50 rounded">
                    <p className="text-gray-500">资金分配饼图区域</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 交易记录 */}
      {activeTab === 'transactions' && (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>交易记录</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">交易ID</th>
                    <th className="text-left py-3 px-4">类型</th>
                    <th className="text-left py-3 px-4">金额</th>
                    <th className="text-left py-3 px-4">来源账户</th>
                    <th className="text-left py-3 px-4">目标账户</th>
                    <th className="text-left py-3 px-4">描述</th>
                    <th className="text-left py-3 px-4">状态</th>
                    <th className="text-left py-3 px-4">时间</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction) => (
                    <tr key={transaction.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-mono text-sm">{transaction.id}</td>
                      <td className="py-3 px-4">
                        <Badge className="text-xs">
                          {getTransactionTypeLabel(transaction.type)}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`font-medium ${
                          transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {transaction.amount >= 0 ? '+' : ''}
                          ${Math.abs(transaction.amount).toLocaleString()}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {transaction.fromAccount || '-'}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {transaction.toAccount || '-'}
                      </td>
                      <td className="py-3 px-4 text-sm">{transaction.description}</td>
                      <td className="py-3 px-4">
                        <Badge className={getStatusColor(transaction.status)}>
                          {transaction.status === 'completed' && <CheckCircle className="w-3 h-3 mr-1" />}
                          {transaction.status === 'pending' && <Clock className="w-3 h-3 mr-1" />}
                          {transaction.status === 'failed' && <XCircle className="w-3 h-3 mr-1" />}
                          {transaction.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-500">{transaction.timestamp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default FinanceManagement;