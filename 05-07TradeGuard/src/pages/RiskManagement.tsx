import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Eye, 
  CheckCircle, 
  XCircle, 
  Clock,
  BarChart3,
  RefreshCw,
  Bell,
  Settings,
  FileText,
  Calculator,
  Activity
} from 'lucide-react';

interface RiskAssessment {
  id: string;
  strategyId: string;
  strategyName: string;
  submittedBy: string;
  riskScore: number;
  status: 'pending' | 'approved' | 'rejected';
  assessmentDetails: {
    marketRisk: number;
    liquidityRisk: number;
    operationalRisk: number;
    concentrationRisk: number;
  };
  feedback?: string;
  submittedAt: string;
  assessedAt?: string;
}

interface RiskAlert {
  id: string;
  type: 'position_limit' | 'drawdown' | 'volatility' | 'correlation' | 'liquidity';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  affectedStrategy?: string;
  currentValue: number;
  threshold: number;
  timestamp: string;
  acknowledged: boolean;
}

interface RiskMetrics {
  portfolioVaR: number;
  maxDrawdown: number;
  sharpeRatio: number;
  volatility: number;
  beta: number;
  correlationRisk: number;
}

interface MonitoringItem {
  id: string;
  name: string;
  type: 'strategy' | 'portfolio' | 'position';
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  currentRisk: number;
  riskLimit: number;
  lastUpdate: string;
  status: 'normal' | 'warning' | 'breach';
}

const RiskManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'assessment' | 'monitoring' | 'alerts' | 'metrics'>('assessment');
  const [isLoading, setIsLoading] = useState(false);
  
  // 风险评估数据
  const [assessments, setAssessments] = useState<RiskAssessment[]>([
    {
      id: 'RISK001',
      strategyId: 'STR001',
      strategyName: '动量突破策略',
      submittedBy: '张交易员',
      riskScore: 7.2,
      status: 'approved',
      assessmentDetails: {
        marketRisk: 6.8,
        liquidityRisk: 5.5,
        operationalRisk: 4.2,
        concentrationRisk: 7.8
      },
      feedback: '策略风险可控，建议执行。注意监控集中度风险。',
      submittedAt: '2024-01-15 09:30:00',
      assessedAt: '2024-01-15 10:15:00'
    },
    {
      id: 'RISK002',
      strategyId: 'STR003',
      strategyName: '高频交易策略',
      submittedBy: '李交易员',
      riskScore: 8.9,
      status: 'pending',
      assessmentDetails: {
        marketRisk: 8.5,
        liquidityRisk: 9.2,
        operationalRisk: 8.8,
        concentrationRisk: 9.1
      },
      submittedAt: '2024-01-15 14:30:00'
    },
    {
      id: 'RISK003',
      strategyId: 'STR004',
      strategyName: '套利策略',
      submittedBy: '王交易员',
      riskScore: 9.5,
      status: 'rejected',
      assessmentDetails: {
        marketRisk: 9.8,
        liquidityRisk: 9.2,
        operationalRisk: 9.0,
        concentrationRisk: 9.8
      },
      feedback: '风险过高，不建议执行。市场风险和集中度风险超出可接受范围。',
      submittedAt: '2024-01-15 11:20:00',
      assessedAt: '2024-01-15 12:05:00'
    }
  ]);

  // 风险警报数据
  const [alerts, setAlerts] = useState<RiskAlert[]>([
    {
      id: 'ALERT001',
      type: 'drawdown',
      severity: 'high',
      message: '动量突破策略回撤超过警戒线',
      affectedStrategy: 'STR001',
      currentValue: 12.5,
      threshold: 10.0,
      timestamp: '2024-01-15 15:30:00',
      acknowledged: false
    },
    {
      id: 'ALERT002',
      type: 'position_limit',
      severity: 'medium',
      message: 'AAPL持仓接近限额',
      currentValue: 85,
      threshold: 90,
      timestamp: '2024-01-15 14:45:00',
      acknowledged: false
    },
    {
      id: 'ALERT003',
      type: 'volatility',
      severity: 'critical',
      message: '市场波动率异常升高',
      currentValue: 28.5,
      threshold: 25.0,
      timestamp: '2024-01-15 13:20:00',
      acknowledged: true
    }
  ]);

  // 风险指标数据
  const [riskMetrics] = useState<RiskMetrics>({
    portfolioVaR: 2.8,
    maxDrawdown: 8.5,
    sharpeRatio: 1.45,
    volatility: 15.2,
    beta: 1.12,
    correlationRisk: 6.8
  });

  // 监控项目数据
  const [monitoringItems] = useState<MonitoringItem[]>([
    {
      id: 'MON001',
      name: '动量突破策略',
      type: 'strategy',
      riskLevel: 'medium',
      currentRisk: 7.2,
      riskLimit: 8.0,
      lastUpdate: '2分钟前',
      status: 'warning'
    },
    {
      id: 'MON002',
      name: '整体投资组合',
      type: 'portfolio',
      riskLevel: 'low',
      currentRisk: 5.8,
      riskLimit: 7.5,
      lastUpdate: '1分钟前',
      status: 'normal'
    },
    {
      id: 'MON003',
      name: 'AAPL持仓',
      type: 'position',
      riskLevel: 'high',
      currentRisk: 8.5,
      riskLimit: 9.0,
      lastUpdate: '30秒前',
      status: 'warning'
    }
  ]);

  // 当前评估的策略
  const [currentAssessment, setCurrentAssessment] = useState<string | null>(null);
  const [assessmentFeedback, setAssessmentFeedback] = useState('');

  // 处理风险评估
  const handleAssessment = async (assessmentId: string, decision: 'approved' | 'rejected') => {
    setIsLoading(true);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setAssessments(prev => prev.map(assessment => 
      assessment.id === assessmentId 
        ? { 
            ...assessment, 
            status: decision,
            feedback: assessmentFeedback,
            assessedAt: new Date().toLocaleString()
          }
        : assessment
    ));
    
    setCurrentAssessment(null);
    setAssessmentFeedback('');
    setIsLoading(false);
  };

  // 确认警报
  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ));
  };

  // 获取风险等级颜色
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-600';
      case 'medium': return 'text-yellow-600';
      case 'high': return 'text-orange-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
      case 'normal':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'pending':
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'rejected':
      case 'breach':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 获取严重程度颜色
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">风控管理台</h1>
            <p className="text-gray-600 mt-1">风险评估 · 实时监控 · 警报管理 · 风险指标</p>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="outline" className="flex items-center space-x-2">
              <RefreshCw className="w-4 h-4" />
              <span>刷新数据</span>
            </Button>
            <Button variant="outline" className="flex items-center space-x-2">
              <Settings className="w-4 h-4" />
              <span>风控设置</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 关键指标概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">投资组合VaR</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{riskMetrics.portfolioVaR}%</div>
            <p className="text-xs text-muted-foreground mt-2">
              95%置信度下的风险价值
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">最大回撤</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{riskMetrics.maxDrawdown}%</div>
            <p className="text-xs text-muted-foreground mt-2">
              历史最大回撤幅度
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">夏普比率</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{riskMetrics.sharpeRatio}</div>
            <p className="text-xs text-muted-foreground mt-2">
              风险调整后收益
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">未确认警报</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {alerts.filter(a => !a.acknowledged).length}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              需要处理的风险警报
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 标签页导航 */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { key: 'assessment', label: '风险评估', icon: Calculator },
              { key: 'monitoring', label: '实时监控', icon: Eye },
              { key: 'alerts', label: '警报管理', icon: Bell },
              { key: 'metrics', label: '风险指标', icon: BarChart3 }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as 'assessment' | 'monitoring' | 'alerts' | 'metrics')}
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

      {/* 风险评估 */}
      {activeTab === 'assessment' && (
        <div className="space-y-6">
          {assessments.map((assessment) => (
            <Card key={assessment.id} className="bg-white">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-2">
                      <Calculator className="w-5 h-5" />
                      <span>{assessment.strategyName}</span>
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      提交者: {assessment.submittedBy} | 策略ID: {assessment.strategyId}
                    </p>
                  </div>
                  <Badge className={getStatusColor(assessment.status)}>
                    {assessment.status === 'approved' && <CheckCircle className="w-4 h-4 mr-1" />}
                    {assessment.status === 'rejected' && <XCircle className="w-4 h-4 mr-1" />}
                    {assessment.status === 'pending' && <Clock className="w-4 h-4 mr-1" />}
                    {assessment.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 风险评分 */}
                  <div>
                    <h4 className="font-medium mb-3">综合风险评分</h4>
                    <div className="text-center">
                      <div className={`text-4xl font-bold mb-2 ${
                        assessment.riskScore <= 5 ? 'text-green-600' :
                        assessment.riskScore <= 7 ? 'text-yellow-600' :
                        assessment.riskScore <= 8.5 ? 'text-orange-600' : 'text-red-600'
                      }`}>
                        {assessment.riskScore}
                      </div>
                      <Progress 
                        value={assessment.riskScore * 10} 
                        className="mb-2"
                      />
                      <p className="text-sm text-gray-500">风险等级: {
                        assessment.riskScore <= 5 ? '低风险' :
                        assessment.riskScore <= 7 ? '中等风险' :
                        assessment.riskScore <= 8.5 ? '高风险' : '极高风险'
                      }</p>
                    </div>
                  </div>

                  {/* 详细风险分析 */}
                  <div>
                    <h4 className="font-medium mb-3">详细风险分析</h4>
                    <div className="space-y-3">
                      {Object.entries(assessment.assessmentDetails).map(([key, value]) => {
                        const labels = {
                          marketRisk: '市场风险',
                          liquidityRisk: '流动性风险',
                          operationalRisk: '操作风险',
                          concentrationRisk: '集中度风险'
                        };
                        return (
                          <div key={key} className="flex items-center justify-between">
                            <span className="text-sm">{labels[key as keyof typeof labels]}</span>
                            <div className="flex items-center space-x-2">
                              <Progress value={value * 10} className="w-20" />
                              <span className={`text-sm font-medium ${
                                value <= 5 ? 'text-green-600' :
                                value <= 7 ? 'text-yellow-600' :
                                value <= 8.5 ? 'text-orange-600' : 'text-red-600'
                              }`}>
                                {value}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 评估反馈 */}
                {assessment.feedback && (
                  <div className="mt-4 p-3 bg-gray-50 rounded">
                    <h5 className="font-medium text-sm mb-1">评估反馈</h5>
                    <p className="text-sm text-gray-700">{assessment.feedback}</p>
                  </div>
                )}

                {/* 操作按钮 */}
                {assessment.status === 'pending' && (
                  <div className="mt-4 space-y-3">
                    {currentAssessment === assessment.id ? (
                      <div className="space-y-3">
                        <Textarea
                          value={assessmentFeedback}
                          onChange={(e) => setAssessmentFeedback(e.target.value)}
                          placeholder="请输入评估反馈..."
                          rows={3}
                        />
                        <div className="flex space-x-3">
                          <Button
                            onClick={() => handleAssessment(assessment.id, 'approved')}
                            disabled={isLoading}
                            className="flex items-center space-x-2 bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="w-4 h-4" />
                            <span>批准</span>
                          </Button>
                          <Button
                            onClick={() => handleAssessment(assessment.id, 'rejected')}
                            disabled={isLoading}
                            variant="destructive"
                            className="flex items-center space-x-2"
                          >
                            <XCircle className="w-4 h-4" />
                            <span>拒绝</span>
                          </Button>
                          <Button
                            onClick={() => setCurrentAssessment(null)}
                            variant="outline"
                          >
                            取消
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button
                        onClick={() => setCurrentAssessment(assessment.id)}
                        className="flex items-center space-x-2"
                      >
                        <FileText className="w-4 h-4" />
                        <span>开始评估</span>
                      </Button>
                    )}
                  </div>
                )}

                {/* 时间信息 */}
                <div className="mt-4 text-xs text-gray-500">
                  提交时间: {assessment.submittedAt}
                  {assessment.assessedAt && (
                    <span className="ml-4">评估时间: {assessment.assessedAt}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 实时监控 */}
      {activeTab === 'monitoring' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Eye className="w-5 h-5" />
                <span>监控项目</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {monitoringItems.map((item) => (
                  <div key={item.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{item.name}</h4>
                        <p className="text-sm text-gray-500">{item.type}</p>
                      </div>
                      <Badge className={getStatusColor(item.status)}>
                        {item.status === 'normal' && <CheckCircle className="w-4 h-4 mr-1" />}
                        {item.status === 'warning' && <AlertTriangle className="w-4 h-4 mr-1" />}
                        {item.status === 'breach' && <XCircle className="w-4 h-4 mr-1" />}
                        {item.status}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>当前风险:</span>
                        <span className={getRiskLevelColor(item.riskLevel)}>
                          {item.currentRisk}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span>风险限额:</span>
                        <span>{item.riskLimit}</span>
                      </div>
                      <Progress 
                        value={(item.currentRisk / item.riskLimit) * 100} 
                        className="mt-2"
                      />
                    </div>
                    <div className="mt-3 text-xs text-gray-500">
                      最后更新: {item.lastUpdate}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Activity className="w-5 h-5" />
                <span>实时风险图表</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
                <p className="text-gray-500">风险趋势图表区域</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 警报管理 */}
      {activeTab === 'alerts' && (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bell className="w-5 h-5" />
              <span>风险警报</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div key={alert.id} className={`border rounded-lg p-4 ${
                  alert.acknowledged ? 'bg-gray-50 opacity-60' : 'bg-white'
                }`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge className={getSeverityColor(alert.severity)}>
                          {alert.severity}
                        </Badge>
                        <span className="text-sm text-gray-500">{alert.type}</span>
                        {alert.acknowledged && (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                      </div>
                      <h4 className="font-medium mb-1">{alert.message}</h4>
                      {alert.affectedStrategy && (
                        <p className="text-sm text-gray-500">影响策略: {alert.affectedStrategy}</p>
                      )}
                      <div className="mt-2 text-sm">
                        <span className="text-gray-500">当前值: </span>
                        <span className="font-medium">{alert.currentValue}</span>
                        <span className="text-gray-500 mx-2">阈值: </span>
                        <span className="font-medium">{alert.threshold}</span>
                      </div>
                    </div>
                    {!alert.acknowledged && (
                      <Button
                        size="sm"
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="flex items-center space-x-1"
                      >
                        <CheckCircle className="w-3 h-3" />
                        <span>确认</span>
                      </Button>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    {alert.timestamp}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 风险指标 */}
      {activeTab === 'metrics' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="text-lg">投资组合VaR</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600 mb-2">
                {riskMetrics.portfolioVaR}%
              </div>
              <p className="text-sm text-gray-500">95%置信度下的风险价值</p>
              <Progress value={riskMetrics.portfolioVaR * 10} className="mt-3" />
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="text-lg">波动率</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-600 mb-2">
                {riskMetrics.volatility}%
              </div>
              <p className="text-sm text-gray-500">年化波动率</p>
              <Progress value={riskMetrics.volatility * 2} className="mt-3" />
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="text-lg">Beta系数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600 mb-2">
                {riskMetrics.beta}
              </div>
              <p className="text-sm text-gray-500">相对市场的系统性风险</p>
              <Progress value={riskMetrics.beta * 50} className="mt-3" />
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="text-lg">相关性风险</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-600 mb-2">
                {riskMetrics.correlationRisk}
              </div>
              <p className="text-sm text-gray-500">资产间相关性风险评分</p>
              <Progress value={riskMetrics.correlationRisk * 10} className="mt-3" />
            </CardContent>
          </Card>

          <Card className="bg-white col-span-1 md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">风险指标趋势</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48 flex items-center justify-center bg-gray-50 rounded">
                <p className="text-gray-500">风险指标趋势图表区域</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default RiskManagement;