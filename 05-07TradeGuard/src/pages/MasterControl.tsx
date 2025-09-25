import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Settings, 
  Shield, 
  DollarSign,
  TrendingUp,
  Server,
  Database,
  Power,
  RefreshCw
} from 'lucide-react';

interface ModuleStatus {
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'offline';
  uptime: string;
  lastUpdate: string;
  metrics?: {
    cpu?: number;
    memory?: number;
    requests?: number;
  };
}

interface SystemAlert {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
  resolved: boolean;
}

interface SystemHealth {
  score: number;
  status: 'excellent' | 'good' | 'warning' | 'critical';
  uptime: string;
  emergencyStop: boolean;
}

const MasterControl: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    score: 85,
    status: 'good',
    uptime: '2天 14小时 32分钟',
    emergencyStop: false
  });

  const [modules] = useState<ModuleStatus[]>([
    {
      name: '交易员模组',
      status: 'healthy',
      uptime: '2天 14小时',
      lastUpdate: '2分钟前',
      metrics: { cpu: 45, memory: 62, requests: 1250 }
    },
    {
      name: '风控模组',
      status: 'healthy',
      uptime: '2天 14小时',
      lastUpdate: '1分钟前',
      metrics: { cpu: 32, memory: 48, requests: 890 }
    },
    {
      name: '财务模组',
      status: 'warning',
      uptime: '2天 13小时',
      lastUpdate: '5分钟前',
      metrics: { cpu: 78, memory: 85, requests: 456 }
    },
    {
      name: 'API工厂',
      status: 'healthy',
      uptime: '2天 14小时',
      lastUpdate: '30秒前',
      metrics: { cpu: 55, memory: 71, requests: 2340 }
    }
  ]);

  const [alerts] = useState<SystemAlert[]>([
    {
      id: '1',
      type: 'high_memory',
      severity: 'medium',
      message: '财务模组内存使用率过高 (85%)',
      timestamp: '5分钟前',
      resolved: false
    },
    {
      id: '2',
      type: 'api_latency',
      severity: 'low',
      message: 'API响应延迟略有增加',
      timestamp: '15分钟前',
      resolved: false
    },
    {
      id: '3',
      type: 'connection_restored',
      severity: 'low',
      message: 'Redis连接已恢复正常',
      timestamp: '1小时前',
      resolved: true
    }
  ]);

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [emergencyDialogOpen, setEmergencyDialogOpen] = useState(false);

  // 模拟数据刷新
  const refreshData = async () => {
    setIsRefreshing(true);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsRefreshing(false);
  };

  // 紧急停止处理
  const handleEmergencyStop = () => {
    setSystemHealth(prev => ({ ...prev, emergencyStop: true }));
    setEmergencyDialogOpen(false);
    // 这里应该调用实际的紧急停止API
  };



  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'warning': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'error': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'offline': return <XCircle className="w-5 h-5 text-gray-500" />;
      default: return <Activity className="w-5 h-5 text-gray-500" />;
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

  useEffect(() => {
    // 设置定时刷新
    const interval = setInterval(() => {
      // 这里可以添加自动刷新逻辑
    }, 30000); // 30秒刷新一次

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 页面标题和控制按钮 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">系统总控台</h1>
            <p className="text-gray-600 mt-1">交易执行铁三角 - 全局监控与紧急控制中心</p>
          </div>
          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              onClick={refreshData}
              disabled={isRefreshing}
              className="flex items-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>刷新数据</span>
            </Button>
            <Button
              variant="destructive"
              onClick={() => setEmergencyDialogOpen(true)}
              disabled={systemHealth.emergencyStop}
              className="flex items-center space-x-2"
            >
              <Power className="w-4 h-4" />
              <span>{systemHealth.emergencyStop ? '已紧急停止' : '紧急停止'}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 紧急停止警告 */}
      {systemHealth.emergencyStop && (
        <Alert className="mb-6 border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            <strong>系统处于紧急停止状态</strong> - 所有交易活动已暂停，请联系系统管理员
          </AlertDescription>
        </Alert>
      )}

      {/* 系统健康概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">系统健康评分</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{systemHealth.score}</div>
            <Progress value={systemHealth.score} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-2">
              状态: <span className="font-medium">{systemHealth.status}</span>
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">系统运行时间</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{systemHealth.uptime}</div>
            <p className="text-xs text-muted-foreground mt-2">
              连续稳定运行
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活跃模组</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              {modules.filter(m => m.status === 'healthy').length}/{modules.length}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              健康模组数量
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">未解决警报</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {alerts.filter(a => !a.resolved).length}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              需要关注的警报
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 模组状态监控 */}
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Server className="w-5 h-5" />
              <span>模组状态监控</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {modules.map((module, index) => (
                <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(module.status)}
                    <div>
                      <h4 className="font-medium">{module.name}</h4>
                      <p className="text-sm text-gray-500">运行时间: {module.uptime}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge className={getSeverityColor(module.status === 'healthy' ? 'low' : 'medium')}>
                      {module.status}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-1">更新: {module.lastUpdate}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 系统警报 */}
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>系统警报</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className={`p-3 border rounded-lg ${
                  alert.resolved ? 'bg-gray-50 opacity-60' : 'bg-white'
                }`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <Badge className={getSeverityColor(alert.severity)}>
                          {alert.severity}
                        </Badge>
                        {alert.resolved && (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                      </div>
                      <p className="text-sm font-medium">{alert.message}</p>
                      <p className="text-xs text-gray-500 mt-1">{alert.timestamp}</p>
                    </div>
                    {!alert.resolved && (
                      <Button size="sm" variant="outline">
                        处理
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <Button variant="outline" className="w-full">
                查看所有警报
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 快速操作面板 */}
      <Card className="bg-white mt-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <span>快速操作</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button variant="outline" className="flex flex-col items-center space-y-2 h-20">
              <TrendingUp className="w-6 h-6" />
              <span className="text-sm">交易员工作台</span>
            </Button>
            <Button variant="outline" className="flex flex-col items-center space-y-2 h-20">
              <Shield className="w-6 h-6" />
              <span className="text-sm">风控管理台</span>
            </Button>
            <Button variant="outline" className="flex flex-col items-center space-y-2 h-20">
              <DollarSign className="w-6 h-6" />
              <span className="text-sm">财务管理台</span>
            </Button>
            <Button variant="outline" className="flex flex-col items-center space-y-2 h-20">
              <Settings className="w-6 h-6" />
              <span className="text-sm">系统配置</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 紧急停止确认对话框 */}
      {emergencyDialogOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <div className="flex items-center space-x-3 mb-4">
              <AlertTriangle className="w-8 h-8 text-red-500" />
              <h3 className="text-lg font-semibold text-red-800">紧急停止确认</h3>
            </div>
            <p className="text-gray-700 mb-6">
              您即将触发系统紧急停止，这将暂停所有交易活动。此操作不可逆转，请确认您要继续。
            </p>
            <div className="flex space-x-3">
              <Button
                variant="destructive"
                onClick={handleEmergencyStop}
                className="flex-1"
              >
                确认停止
              </Button>
              <Button
                variant="outline"
                onClick={() => setEmergencyDialogOpen(false)}
                className="flex-1"
              >
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MasterControl;