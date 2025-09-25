import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Send,
  FileText,
  BarChart3,
  Target,
  Zap,
  RefreshCw,
  Upload
} from 'lucide-react';

interface StrategyPackage {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'approved' | 'rejected' | 'executing';
  riskScore: number;
  expectedReturn: number;
  maxDrawdown: number;
  submittedAt: string;
  approvedAt?: string;
}

interface Order {
  id: string;
  symbol: string;
  type: 'buy' | 'sell';
  quantity: number;
  price: number;
  status: 'pending' | 'filled' | 'cancelled' | 'rejected';
  timestamp: string;
  strategyId: string;
}

interface RiskAssessment {
  id: string;
  strategyId: string;
  riskScore: number;
  status: 'pending' | 'approved' | 'rejected';
  feedback?: string;
  assessedAt: string;
}

interface BudgetRequest {
  id: string;
  strategyId: string;
  amount: number;
  purpose: string;
  status: 'pending' | 'approved' | 'rejected';
  requestedAt: string;
  approvedAmount?: number;
}

const TraderWorkstation: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'strategies' | 'orders' | 'risk' | 'budget'>('strategies');
  const [isLoading, setIsLoading] = useState(false);
  
  // 策略包数据
  const [strategies, setStrategies] = useState<StrategyPackage[]>([
    {
      id: 'STR001',
      name: '动量突破策略',
      type: '趋势跟踪',
      status: 'executing',
      riskScore: 7.2,
      expectedReturn: 15.8,
      maxDrawdown: 8.5,
      submittedAt: '2024-01-15 09:30:00',
      approvedAt: '2024-01-15 10:15:00'
    },
    {
      id: 'STR002',
      name: '均值回归策略',
      type: '统计套利',
      status: 'approved',
      riskScore: 5.1,
      expectedReturn: 12.3,
      maxDrawdown: 6.2,
      submittedAt: '2024-01-15 11:20:00',
      approvedAt: '2024-01-15 11:45:00'
    },
    {
      id: 'STR003',
      name: '高频交易策略',
      type: '高频',
      status: 'pending',
      riskScore: 8.9,
      expectedReturn: 22.1,
      maxDrawdown: 12.3,
      submittedAt: '2024-01-15 14:30:00'
    }
  ]);

  // 订单数据
  const [orders] = useState<Order[]>([
    {
      id: 'ORD001',
      symbol: 'AAPL',
      type: 'buy',
      quantity: 100,
      price: 185.50,
      status: 'filled',
      timestamp: '2024-01-15 09:45:00',
      strategyId: 'STR001'
    },
    {
      id: 'ORD002',
      symbol: 'MSFT',
      type: 'sell',
      quantity: 50,
      price: 412.30,
      status: 'pending',
      timestamp: '2024-01-15 10:20:00',
      strategyId: 'STR001'
    },
    {
      id: 'ORD003',
      symbol: 'GOOGL',
      type: 'buy',
      quantity: 25,
      price: 142.80,
      status: 'rejected',
      timestamp: '2024-01-15 11:10:00',
      strategyId: 'STR002'
    }
  ]);

  // 风险评估数据
  const [riskAssessments] = useState<RiskAssessment[]>([
    {
      id: 'RISK001',
      strategyId: 'STR001',
      riskScore: 7.2,
      status: 'approved',
      feedback: '策略风险可控，建议执行',
      assessedAt: '2024-01-15 10:10:00'
    },
    {
      id: 'RISK002',
      strategyId: 'STR003',
      riskScore: 8.9,
      status: 'pending',
      assessedAt: '2024-01-15 14:35:00'
    }
  ]);

  // 预算申请数据
  const [budgetRequests] = useState<BudgetRequest[]>([
    {
      id: 'BUD001',
      strategyId: 'STR001',
      amount: 500000,
      purpose: '动量突破策略执行资金',
      status: 'approved',
      requestedAt: '2024-01-15 09:25:00',
      approvedAmount: 500000
    },
    {
      id: 'BUD002',
      strategyId: 'STR003',
      amount: 1000000,
      purpose: '高频交易策略启动资金',
      status: 'pending',
      requestedAt: '2024-01-15 14:25:00'
    }
  ]);

  // 新策略表单
  const [newStrategy, setNewStrategy] = useState({
    name: '',
    type: '',
    description: '',
    expectedReturn: '',
    maxDrawdown: '',
    budgetRequired: ''
  });

  // 提交新策略
  const handleSubmitStrategy = async () => {
    setIsLoading(true);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const strategy: StrategyPackage = {
      id: `STR${String(strategies.length + 1).padStart(3, '0')}`,
      name: newStrategy.name,
      type: newStrategy.type,
      status: 'pending',
      riskScore: 0,
      expectedReturn: parseFloat(newStrategy.expectedReturn) || 0,
      maxDrawdown: parseFloat(newStrategy.maxDrawdown) || 0,
      submittedAt: new Date().toLocaleString()
    };
    
    setStrategies(prev => [strategy, ...prev]);
    setNewStrategy({
      name: '',
      type: '',
      description: '',
      expectedReturn: '',
      maxDrawdown: '',
      budgetRequired: ''
    });
    setIsLoading(false);
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
      case 'filled':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'rejected':
      case 'cancelled':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'executing':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
      case 'filled':
        return <CheckCircle className="w-4 h-4" />;
      case 'pending':
        return <Clock className="w-4 h-4" />;
      case 'rejected':
      case 'cancelled':
        return <XCircle className="w-4 h-4" />;
      case 'executing':
        return <Zap className="w-4 h-4" />;
      default:
        return <AlertTriangle className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">交易员工作台</h1>
            <p className="text-gray-600 mt-1">策略管理 · 订单执行 · 风险申请 · 资金管理</p>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="outline" className="flex items-center space-x-2">
              <RefreshCw className="w-4 h-4" />
              <span>刷新数据</span>
            </Button>
            <Button className="flex items-center space-x-2">
              <Upload className="w-4 h-4" />
              <span>导入策略</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 统计概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃策略</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {strategies.filter(s => s.status === 'executing').length}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              正在执行的策略数量
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日订单</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{orders.length}</div>
            <p className="text-xs text-muted-foreground mt-2">
              成功执行: {orders.filter(o => o.status === 'filled').length}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">待审批</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {strategies.filter(s => s.status === 'pending').length}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              等待风控和财务审批
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总资金</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">$2.5M</div>
            <p className="text-xs text-muted-foreground mt-2">
              可用资金额度
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 标签页导航 */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { key: 'strategies', label: '策略包管理', icon: FileText },
              { key: 'orders', label: '订单执行', icon: Target },
              { key: 'risk', label: '风险评估', icon: AlertTriangle },
              { key: 'budget', label: '资金申请', icon: DollarSign }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as 'strategies' | 'orders' | 'risk' | 'budget')}
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

      {/* 策略包管理 */}
      {activeTab === 'strategies' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 新建策略 */}
          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="w-5 h-5" />
                <span>新建策略包</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="strategy-name">策略名称</Label>
                <Input
                  id="strategy-name"
                  value={newStrategy.name}
                  onChange={(e) => setNewStrategy(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="输入策略名称"
                />
              </div>
              <div>
                <Label htmlFor="strategy-type">策略类型</Label>
                <Input
                  id="strategy-type"
                  value={newStrategy.type}
                  onChange={(e) => setNewStrategy(prev => ({ ...prev, type: e.target.value }))}
                  placeholder="如：趋势跟踪、统计套利等"
                />
              </div>
              <div>
                <Label htmlFor="strategy-description">策略描述</Label>
                <Textarea
                  id="strategy-description"
                  value={newStrategy.description}
                  onChange={(e) => setNewStrategy(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="详细描述策略逻辑和执行方式"
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="expected-return">预期收益率 (%)</Label>
                  <Input
                    id="expected-return"
                    type="number"
                    value={newStrategy.expectedReturn}
                    onChange={(e) => setNewStrategy(prev => ({ ...prev, expectedReturn: e.target.value }))}
                    placeholder="15.5"
                  />
                </div>
                <div>
                  <Label htmlFor="max-drawdown">最大回撤 (%)</Label>
                  <Input
                    id="max-drawdown"
                    type="number"
                    value={newStrategy.maxDrawdown}
                    onChange={(e) => setNewStrategy(prev => ({ ...prev, maxDrawdown: e.target.value }))}
                    placeholder="8.0"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="budget-required">所需资金 ($)</Label>
                <Input
                  id="budget-required"
                  type="number"
                  value={newStrategy.budgetRequired}
                  onChange={(e) => setNewStrategy(prev => ({ ...prev, budgetRequired: e.target.value }))}
                  placeholder="500000"
                />
              </div>
              <Button 
                onClick={handleSubmitStrategy}
                disabled={isLoading || !newStrategy.name || !newStrategy.type}
                className="w-full flex items-center space-x-2"
              >
                <Send className="w-4 h-4" />
                <span>{isLoading ? '提交中...' : '提交策略包'}</span>
              </Button>
            </CardContent>
          </Card>

          {/* 策略列表 */}
          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5" />
                <span>策略包列表</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {strategies.map((strategy) => (
                  <div key={strategy.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{strategy.name}</h4>
                        <p className="text-sm text-gray-500">{strategy.type}</p>
                      </div>
                      <Badge className={getStatusColor(strategy.status)}>
                        {getStatusIcon(strategy.status)}
                        <span className="ml-1">{strategy.status}</span>
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">预期收益:</span>
                        <p className="font-medium text-green-600">{strategy.expectedReturn}%</p>
                      </div>
                      <div>
                        <span className="text-gray-500">最大回撤:</span>
                        <p className="font-medium text-red-600">{strategy.maxDrawdown}%</p>
                      </div>
                      <div>
                        <span className="text-gray-500">风险评分:</span>
                        <p className="font-medium">{strategy.riskScore || 'N/A'}</p>
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-gray-500">
                      提交时间: {strategy.submittedAt}
                      {strategy.approvedAt && (
                        <span className="ml-4">批准时间: {strategy.approvedAt}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 订单执行 */}
      {activeTab === 'orders' && (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Target className="w-5 h-5" />
              <span>订单执行记录</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">订单ID</th>
                    <th className="text-left py-3 px-4">标的</th>
                    <th className="text-left py-3 px-4">类型</th>
                    <th className="text-left py-3 px-4">数量</th>
                    <th className="text-left py-3 px-4">价格</th>
                    <th className="text-left py-3 px-4">状态</th>
                    <th className="text-left py-3 px-4">时间</th>
                    <th className="text-left py-3 px-4">策略</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-mono text-sm">{order.id}</td>
                      <td className="py-3 px-4 font-medium">{order.symbol}</td>
                      <td className="py-3 px-4">
                        <Badge className={order.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {order.type === 'buy' ? (
                            <TrendingUp className="w-3 h-3 mr-1" />
                          ) : (
                            <TrendingDown className="w-3 h-3 mr-1" />
                          )}
                          {order.type.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{order.quantity.toLocaleString()}</td>
                      <td className="py-3 px-4">${order.price.toFixed(2)}</td>
                      <td className="py-3 px-4">
                        <Badge className={getStatusColor(order.status)}>
                          {getStatusIcon(order.status)}
                          <span className="ml-1">{order.status}</span>
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-500">{order.timestamp}</td>
                      <td className="py-3 px-4 text-sm">{order.strategyId}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 风险评估 */}
      {activeTab === 'risk' && (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>风险评估状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {riskAssessments.map((assessment) => {
                const strategy = strategies.find(s => s.id === assessment.strategyId);
                return (
                  <div key={assessment.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{strategy?.name || assessment.strategyId}</h4>
                        <p className="text-sm text-gray-500">风险评分: {assessment.riskScore}</p>
                      </div>
                      <Badge className={getStatusColor(assessment.status)}>
                        {getStatusIcon(assessment.status)}
                        <span className="ml-1">{assessment.status}</span>
                      </Badge>
                    </div>
                    {assessment.feedback && (
                      <div className="bg-gray-50 p-3 rounded mb-3">
                        <p className="text-sm">{assessment.feedback}</p>
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      评估时间: {assessment.assessedAt}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 资金申请 */}
      {activeTab === 'budget' && (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <DollarSign className="w-5 h-5" />
              <span>资金申请状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {budgetRequests.map((request) => {
                const strategy = strategies.find(s => s.id === request.strategyId);
                return (
                  <div key={request.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{strategy?.name || request.strategyId}</h4>
                        <p className="text-sm text-gray-500">{request.purpose}</p>
                      </div>
                      <Badge className={getStatusColor(request.status)}>
                        {getStatusIcon(request.status)}
                        <span className="ml-1">{request.status}</span>
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">申请金额:</span>
                        <p className="font-medium">${request.amount.toLocaleString()}</p>
                      </div>
                      {request.approvedAmount && (
                        <div>
                          <span className="text-gray-500">批准金额:</span>
                          <p className="font-medium text-green-600">${request.approvedAmount.toLocaleString()}</p>
                        </div>
                      )}
                    </div>
                    <div className="mt-3 text-xs text-gray-500">
                      申请时间: {request.requestedAt}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TraderWorkstation;