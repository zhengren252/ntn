import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Progress, Badge, Alert, Spin, Button } from 'antd';
import {
  DashboardOutlined,
  HeartOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  DollarOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

// 类型定义
interface SystemStatus {
  module_name: string;
  status: 'online' | 'offline' | 'error';
  health: 'healthy' | 'warning' | 'critical';
  cpu_usage: number;
  memory_usage: number;
  last_heartbeat: string;
}

interface MarketData {
  timestamp: string;
  price: number;
  volume: number;
  bull_bear_index: number;
}

interface RiskAlert {
  id: string;
  type: string;
  level: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
}

const Dashboard: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus[]>([]);
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [riskAlerts, setRiskAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // 模拟数据 - 实际应用中应从API获取
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 模拟系统状态数据
        const mockSystemStatus: SystemStatus[] = [
          {
            module_name: 'master_control',
            status: 'online',
            health: 'healthy',
            cpu_usage: 15.2,
            memory_usage: 32.8,
            last_heartbeat: new Date().toISOString()
          },
          {
            module_name: 'data_collection',
            status: 'online',
            health: 'healthy',
            cpu_usage: 8.5,
            memory_usage: 28.3,
            last_heartbeat: new Date(Date.now() - 5000).toISOString()
          },
          {
            module_name: 'signal_generation',
            status: 'online',
            health: 'warning',
            cpu_usage: 45.7,
            memory_usage: 67.2,
            last_heartbeat: new Date(Date.now() - 2000).toISOString()
          },
          {
            module_name: 'execution_engine',
            status: 'offline',
            health: 'critical',
            cpu_usage: 0,
            memory_usage: 0,
            last_heartbeat: new Date(Date.now() - 120000).toISOString()
          },
          {
            module_name: 'risk_management',
            status: 'online',
            health: 'healthy',
            cpu_usage: 12.3,
            memory_usage: 24.1,
            last_heartbeat: new Date(Date.now() - 1000).toISOString()
          }
        ];

        // 模拟市场数据
        const mockMarketData: MarketData[] = Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
          price: 50000 + Math.random() * 5000,
          volume: Math.random() * 1000000,
          bull_bear_index: 0.3 + Math.random() * 0.4
        }));

        // 模拟风险告警
        const mockRiskAlerts: RiskAlert[] = [
          {
            id: '1',
            type: 'high_volatility',
            level: 'medium',
            message: '市场波动率超过阈值 5%',
            timestamp: new Date(Date.now() - 300000).toISOString()
          },
          {
            id: '2',
            type: 'module_offline',
            level: 'critical',
            message: '执行引擎模组离线',
            timestamp: new Date(Date.now() - 120000).toISOString()
          }
        ];

        setSystemStatus(mockSystemStatus);
        setMarketData(mockMarketData);
        setRiskAlerts(mockRiskAlerts);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('获取数据失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // 每5秒更新一次

    return () => clearInterval(interval);
  }, []);

  // 获取状态颜色
  const getStatusColor = (status: string, health: string) => {
    if (status === 'offline') return '#ff4d4f';
    if (health === 'critical') return '#ff4d4f';
    if (health === 'warning') return '#faad14';
    return '#52c41a';
  };

  // 获取状态图标
  const getStatusIcon = (status: string, health: string) => {
    if (status === 'offline') return <CloseCircleOutlined />;
    if (health === 'critical') return <WarningOutlined />;
    if (health === 'warning') return <WarningOutlined />;
    return <CheckCircleOutlined />;
  };

  // 计算系统总体健康度
  const calculateSystemHealth = () => {
    const onlineModules = systemStatus.filter(m => m.status === 'online').length;
    const totalModules = systemStatus.length;
    return totalModules > 0 ? Math.round((onlineModules / totalModules) * 100) : 0;
  };

  // 获取告警级别颜色
  const getAlertColor = (level: string) => {
    switch (level) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'warning';
      default: return 'info';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spin size="large" tip="加载战场仪表盘..." />
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <DashboardOutlined className="text-2xl text-blue-400" />
            <h1 className="text-2xl font-bold">战场仪表盘</h1>
            <Badge 
              status={calculateSystemHealth() > 80 ? 'success' : calculateSystemHealth() > 60 ? 'warning' : 'error'} 
              text={`系统健康度: ${calculateSystemHealth()}%`} 
              className="text-gray-300"
            />
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-400">
              最后更新: {lastUpdate.toLocaleTimeString()}
            </span>
            <Button 
              type="primary" 
              icon={<SyncOutlined />} 
              size="small"
              onClick={() => window.location.reload()}
            >
              刷新
            </Button>
          </div>
        </div>
      </div>

      {/* 关键指标卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} md={6}>
          <Card className="bg-gray-800 border-gray-700">
            <Statistic
              title={<span className="text-gray-300">在线模组</span>}
              value={systemStatus.filter(m => m.status === 'online').length}
              suffix={`/ ${systemStatus.length}`}
              valueStyle={{ color: '#52c41a' }}
              prefix={<HeartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="bg-gray-800 border-gray-700">
            <Statistic
              title={<span className="text-gray-300">系统负载</span>}
              value={systemStatus.reduce((acc, m) => acc + m.cpu_usage, 0) / systemStatus.length}
              precision={1}
              suffix="%"
              valueStyle={{ color: '#1890ff' }}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="bg-gray-800 border-gray-700">
            <Statistic
              title={<span className="text-gray-300">内存使用</span>}
              value={systemStatus.reduce((acc, m) => acc + m.memory_usage, 0) / systemStatus.length}
              precision={1}
              suffix="%"
              valueStyle={{ color: '#faad14' }}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="bg-gray-800 border-gray-700">
            <Statistic
              title={<span className="text-gray-300">活跃告警</span>}
              value={riskAlerts.length}
              valueStyle={{ color: riskAlerts.length > 0 ? '#ff4d4f' : '#52c41a' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 主要内容区域 */}
      <Row gutter={[16, 16]}>
        {/* 模组状态监控 */}
        <Col xs={24} lg={12}>
          <Card 
            title={<span className="text-white">模组状态监控</span>}
            className="bg-gray-800 border-gray-700 h-96"
          >
            <div className="space-y-4">
              {systemStatus.map((module) => (
                <div key={module.module_name} className="flex items-center justify-between p-3 bg-gray-700 rounded">
                  <div className="flex items-center space-x-3">
                    <span style={{ color: getStatusColor(module.status, module.health) }}>
                      {getStatusIcon(module.status, module.health)}
                    </span>
                    <div>
                      <div className="font-medium text-white">{module.module_name}</div>
                      <div className="text-sm text-gray-400">
                        CPU: {module.cpu_usage}% | 内存: {module.memory_usage}%
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge 
                      status={module.status === 'online' ? 'success' : 'error'} 
                      text={module.status}
                      className="text-gray-300"
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      {new Date(module.last_heartbeat).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* 市场数据趋势 */}
        <Col xs={24} lg={12}>
          <Card 
            title={<span className="text-white">市场数据趋势</span>}
            className="bg-gray-800 border-gray-700 h-96"
          >
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={marketData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                  stroke="#9CA3AF"
                />
                <YAxis stroke="#9CA3AF" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    color: '#F3F4F6'
                  }}
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                />
                <Area 
                  type="monotone" 
                  dataKey="bull_bear_index" 
                  stroke="#3B82F6" 
                  fill="#3B82F6" 
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* 风险告警面板 */}
        <Col xs={24}>
          <Card 
            title={<span className="text-white">风险告警面板</span>}
            className="bg-gray-800 border-gray-700"
          >
            {riskAlerts.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <CheckCircleOutlined className="text-4xl text-green-500 mb-2" />
                <div>系统运行正常，暂无风险告警</div>
              </div>
            ) : (
              <div className="space-y-3">
                {riskAlerts.map((alert) => (
                  <Alert
                    key={alert.id}
                    type={getAlertColor(alert.level) as any}
                    message={`${alert.type.toUpperCase()} - ${alert.level.toUpperCase()}`}
                    description={
                      <div>
                        <div>{alert.message}</div>
                        <div className="text-xs mt-1 opacity-75">
                          {new Date(alert.timestamp).toLocaleString()}
                        </div>
                      </div>
                    }
                    showIcon
                    className="bg-gray-700 border-gray-600"
                  />
                ))}
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;