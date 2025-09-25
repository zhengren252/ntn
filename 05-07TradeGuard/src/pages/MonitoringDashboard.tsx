import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

import { 
  Activity, 
  Server, 
  Cpu, 
  HardDrive, 
  MemoryStick, 
  Network, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  Eye, 
  BarChart3, 
  LineChart, 
  PieChart
} from 'lucide-react';
import { LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart as RechartsPieChart, Cell } from 'recharts';

interface SystemMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  status: 'normal' | 'warning' | 'critical';
  threshold: {
    warning: number;
    critical: number;
  };
  trend: 'up' | 'down' | 'stable';
  history: { time: string; value: number }[];
}

interface ServiceStatus {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'degraded';
  uptime: string;
  responseTime: number;
  lastCheck: string;
  endpoint?: string;
}

interface AlertItem {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  source: string;
  acknowledged: boolean;
}

const MonitoringDashboard: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30); // 秒


  // 系统指标
  const [systemMetrics] = useState<SystemMetric[]>([
    {
      id: 'cpu',
      name: 'CPU使用率',
      value: 45.2,
      unit: '%',
      status: 'normal',
      threshold: { warning: 70, critical: 85 },
      trend: 'stable',
      history: Array.from({ length: 24 }, (_, i) => ({
        time: `${23 - i}:00`,
        value: Math.random() * 60 + 20
      }))
    },
    {
      id: 'memory',
      name: '内存使用率',
      value: 68.7,
      unit: '%',
      status: 'normal',
      threshold: { warning: 80, critical: 90 },
      trend: 'up',
      history: Array.from({ length: 24 }, (_, i) => ({
        time: `${23 - i}:00`,
        value: Math.random() * 40 + 40
      }))
    },
    {
      id: 'disk',
      name: '磁盘使用率',
      value: 34.1,
      unit: '%',
      status: 'normal',
      threshold: { warning: 80, critical: 90 },
      trend: 'stable',
      history: Array.from({ length: 24 }, (_, i) => ({
        time: `${23 - i}:00`,
        value: Math.random() * 20 + 25
      }))
    },
    {
      id: 'network',
      name: '网络吞吐量',
      value: 125.6,
      unit: 'MB/s',
      status: 'normal',
      threshold: { warning: 800, critical: 950 },
      trend: 'down',
      history: Array.from({ length: 24 }, (_, i) => ({
        time: `${23 - i}:00`,
        value: Math.random() * 200 + 50
      }))
    }
  ]);

  // 服务状态
  const [services] = useState<ServiceStatus[]>([
    {
      id: 'trader-module',
      name: '交易员模组',
      status: 'online',
      uptime: '99.9%',
      responseTime: 45,
      lastCheck: '刚刚',
      endpoint: '/api/trader/health'
    },
    {
      id: 'risk-module',
      name: '风控模组',
      status: 'online',
      uptime: '99.8%',
      responseTime: 32,
      lastCheck: '刚刚',
      endpoint: '/api/risk/health'
    },
    {
      id: 'finance-module',
      name: '财务模组',
      status: 'online',
      uptime: '99.7%',
      responseTime: 28,
      lastCheck: '刚刚',
      endpoint: '/api/finance/health'
    },
    {
      id: 'database',
      name: '数据库服务',
      status: 'online',
      uptime: '99.9%',
      responseTime: 12,
      lastCheck: '刚刚'
    },
    {
      id: 'redis',
      name: 'Redis缓存',
      status: 'online',
      uptime: '99.9%',
      responseTime: 8,
      lastCheck: '刚刚'
    },
    {
      id: 'zeromq',
      name: 'ZeroMQ消息队列',
      status: 'degraded',
      uptime: '98.5%',
      responseTime: 156,
      lastCheck: '30秒前'
    }
  ]);

  // 系统警报
  const [alerts, setAlerts] = useState<AlertItem[]>([
    {
      id: '1',
      type: 'warning',
      title: 'ZeroMQ响应时间过长',
      message: '消息队列响应时间超过100ms，可能影响系统性能',
      timestamp: '2024-01-15 14:35:22',
      source: 'ZeroMQ监控',
      acknowledged: false
    },
    {
      id: '2',
      type: 'info',
      title: '系统定期维护提醒',
      message: '系统将在今晚23:00进行定期维护，预计持续30分钟',
      timestamp: '2024-01-15 14:00:00',
      source: '系统管理',
      acknowledged: true
    },
    {
      id: '3',
      type: 'error',
      title: '策略执行失败',
      message: '策略ID: STR-2024-001 执行失败，错误代码: RISK_LIMIT_EXCEEDED',
      timestamp: '2024-01-15 13:45:18',
      source: '交易员模组',
      acknowledged: false
    }
  ]);

  // 性能统计数据
  const performanceData = [
    { name: '00:00', requests: 1200, errors: 5, responseTime: 45 },
    { name: '04:00', requests: 800, errors: 2, responseTime: 38 },
    { name: '08:00', requests: 2100, errors: 12, responseTime: 52 },
    { name: '12:00', requests: 3200, errors: 8, responseTime: 48 },
    { name: '16:00', requests: 2800, errors: 15, responseTime: 65 },
    { name: '20:00', requests: 1900, errors: 6, responseTime: 42 }
  ];

  // 模组使用率分布
  const moduleUsageData = [
    { name: '交易员模组', value: 35, color: '#3B82F6' },
    { name: '风控模组', value: 28, color: '#EF4444' },
    { name: '财务模组', value: 22, color: '#10B981' },
    { name: '总控模组', value: 15, color: '#F59E0B' }
  ];

  // 刷新数据
  const refreshData = async () => {
    setIsLoading(true);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLastUpdate(new Date());
    setIsLoading(false);
  };

  // 自动刷新
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(refreshData, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  // 确认警报
  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ));
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'normal':
        return 'text-green-600 bg-green-100';
      case 'warning':
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100';
      case 'critical':
      case 'offline':
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  // 获取趋势图标
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-red-500" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-green-500" />;
      default:
        return <div className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">监控仪表板</h1>
            <p className="text-gray-600 mt-1">实时系统监控 · 性能分析 · 告警管理</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">最后更新:</span>
              <span className="text-sm font-medium">{lastUpdate.toLocaleTimeString()}</span>
            </div>
            <div className="flex items-center space-x-2">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">自动刷新</span>
              </label>
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="px-2 py-1 border rounded text-sm"
                disabled={!autoRefresh}
              >
                <option value={10}>10秒</option>
                <option value={30}>30秒</option>
                <option value={60}>1分钟</option>
                <option value={300}>5分钟</option>
              </select>
            </div>
            <Button
              onClick={refreshData}
              disabled={isLoading}
              variant="outline"
              className="flex items-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>刷新</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 系统概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {systemMetrics.map((metric) => {
          const Icon = {
            cpu: Cpu,
            memory: MemoryStick,
            disk: HardDrive,
            network: Network
          }[metric.id] || Activity;

          return (
            <Card key={metric.id} className="bg-white">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`p-2 rounded-lg ${getStatusColor(metric.status)}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600">{metric.name}</p>
                      <div className="flex items-center space-x-2">
                        <p className="text-2xl font-bold">{metric.value}</p>
                        <span className="text-sm text-gray-500">{metric.unit}</span>
                        {getTrendIcon(metric.trend)}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-4">
                  <Progress 
                    value={metric.value} 
                    className="h-2"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0</span>
                    <span className="text-yellow-600">警告: {metric.threshold.warning}{metric.unit}</span>
                    <span className="text-red-600">危险: {metric.threshold.critical}{metric.unit}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* 服务状态 */}
      <Card className="bg-white mb-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Server className="w-5 h-5" />
            <span>服务状态</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service) => (
              <div key={service.id} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">{service.name}</h3>
                  <Badge className={getStatusColor(service.status)}>
                    {service.status === 'online' ? '在线' : 
                     service.status === 'offline' ? '离线' : '降级'}
                  </Badge>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>运行时间:</span>
                    <span className="font-medium">{service.uptime}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>响应时间:</span>
                    <span className={`font-medium ${
                      service.responseTime > 100 ? 'text-red-600' : 
                      service.responseTime > 50 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {service.responseTime}ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>最后检查:</span>
                    <span className="font-medium">{service.lastCheck}</span>
                  </div>
                  {service.endpoint && (
                    <div className="flex justify-between">
                      <span>端点:</span>
                      <span className="font-mono text-xs">{service.endpoint}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 性能图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* 系统性能趋势 */}
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <LineChart className="w-5 h-5" />
              <span>系统性能趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsLineChart data={systemMetrics[0].history}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} />
                </RechartsLineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* 模组使用率分布 */}
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <PieChart className="w-5 h-5" />
              <span>模组使用率分布</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPieChart>
                  <Tooltip />
                  <RechartsPieChart data={moduleUsageData} cx="50%" cy="50%" outerRadius={80}>
                    {moduleUsageData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </RechartsPieChart>
                </RechartsPieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {moduleUsageData.map((item) => (
                <div key={item.name} className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm">{item.name}</span>
                  <span className="text-sm font-medium">{item.value}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* API性能统计 */}
      <Card className="bg-white mb-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>API性能统计</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Bar yAxisId="left" dataKey="requests" fill="#3B82F6" name="请求数" />
                <Bar yAxisId="left" dataKey="errors" fill="#EF4444" name="错误数" />
                <Line yAxisId="right" type="monotone" dataKey="responseTime" stroke="#10B981" name="响应时间(ms)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* 系统警报 */}
      <Card className="bg-white">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>系统警报</span>
              <Badge variant="destructive">
                {alerts.filter(alert => !alert.acknowledged).length}
              </Badge>
            </div>
            <Button variant="outline" size="sm">
              <Eye className="w-4 h-4 mr-2" />
              查看全部
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {alerts.slice(0, 5).map((alert) => {
              const Icon = {
                error: XCircle,
                warning: AlertTriangle,
                info: CheckCircle
              }[alert.type];

              return (
                <div 
                  key={alert.id} 
                  className={`p-4 border rounded-lg ${
                    alert.acknowledged ? 'bg-gray-50 opacity-75' : 'bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <Icon className={`w-5 h-5 mt-0.5 ${
                        alert.type === 'error' ? 'text-red-500' :
                        alert.type === 'warning' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`} />
                      <div className="flex-1">
                        <h4 className="font-medium">{alert.title}</h4>
                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                        <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                          <span>来源: {alert.source}</span>
                          <span>时间: {alert.timestamp}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {alert.acknowledged ? (
                        <Badge variant="secondary">已确认</Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => acknowledgeAlert(alert.id)}
                        >
                          确认
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MonitoringDashboard;