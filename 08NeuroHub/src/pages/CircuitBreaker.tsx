import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Switch, Alert, Table, Tag, Modal, Form, InputNumber, Select, Progress, Statistic, Timeline, Space, Divider } from 'antd';
import {
  ThunderboltOutlined,
  WarningOutlined,
  StopOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SettingOutlined,
  FireOutlined,
  SafetyOutlined,
  AlertOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

// 类型定义
interface CircuitBreakerRule {
  id: string;
  name: string;
  type: 'loss_limit' | 'volatility' | 'position_limit' | 'drawdown' | 'custom';
  threshold: number;
  action: 'stop_trading' | 'reduce_position' | 'alert_only' | 'emergency_exit';
  enabled: boolean;
  priority: 'low' | 'medium' | 'high' | 'critical';
  description: string;
}

interface RiskEvent {
  id: string;
  timestamp: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  triggered_rules: string[];
  actions_taken: string[];
  status: 'active' | 'resolved' | 'ignored';
  impact: number;
}

interface SystemStatus {
  trading_enabled: boolean;
  circuit_breaker_active: boolean;
  emergency_mode: boolean;
  last_trigger_time: string | null;
  total_triggers_today: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

interface TriggerHistory {
  timestamp: string;
  rule_name: string;
  threshold_value: number;
  actual_value: number;
  action_taken: string;
}

const CircuitBreaker: React.FC = () => {
  const [circuitRules, setCircuitRules] = useState<CircuitBreakerRule[]>([]);
  const [riskEvents, setRiskEvents] = useState<RiskEvent[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [triggerHistory, setTriggerHistory] = useState<TriggerHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [emergencyModalVisible, setEmergencyModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 模拟数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 模拟熔断规则数据
        const mockCircuitRules: CircuitBreakerRule[] = [
          {
            id: 'daily_loss',
            name: '单日亏损限制',
            type: 'loss_limit',
            threshold: 50000,
            action: 'stop_trading',
            enabled: true,
            priority: 'critical',
            description: '当日累计亏损超过5万美元时立即停止交易'
          },
          {
            id: 'volatility_spike',
            name: '市场波动率熔断',
            type: 'volatility',
            threshold: 15,
            action: 'reduce_position',
            enabled: true,
            priority: 'high',
            description: '市场波动率超过15%时减少持仓至50%'
          },
          {
            id: 'max_drawdown',
            name: '最大回撤保护',
            type: 'drawdown',
            threshold: 10,
            action: 'emergency_exit',
            enabled: true,
            priority: 'critical',
            description: '账户回撤超过10%时紧急平仓'
          },
          {
            id: 'position_concentration',
            name: '持仓集中度限制',
            type: 'position_limit',
            threshold: 30,
            action: 'alert_only',
            enabled: false,
            priority: 'medium',
            description: '单一资产持仓超过30%时发出警告'
          }
        ];

        // 模拟系统状态
        const mockSystemStatus: SystemStatus = {
          trading_enabled: true,
          circuit_breaker_active: false,
          emergency_mode: false,
          last_trigger_time: '2024-01-15T14:30:00Z',
          total_triggers_today: 2,
          risk_level: 'medium'
        };

        // 模拟风险事件
        const mockRiskEvents: RiskEvent[] = [
          {
            id: '1',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            type: '市场波动率异常',
            severity: 'high',
            description: 'BTC价格在1小时内波动超过8%，触发波动率熔断',
            triggered_rules: ['volatility_spike'],
            actions_taken: ['减少持仓至50%', '发送风险警报'],
            status: 'resolved',
            impact: 15000
          },
          {
            id: '2',
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            type: '单日亏损警告',
            severity: 'medium',
            description: '当日累计亏损达到35000美元，接近熔断阈值',
            triggered_rules: ['daily_loss'],
            actions_taken: ['发送预警通知'],
            status: 'active',
            impact: 35000
          }
        ];

        // 模拟触发历史
        const mockTriggerHistory: TriggerHistory[] = Array.from({ length: 10 }, (_, i) => ({
          timestamp: new Date(Date.now() - i * 3600000).toISOString(),
          rule_name: ['单日亏损限制', '市场波动率熔断', '最大回撤保护'][Math.floor(Math.random() * 3)],
          threshold_value: [50000, 15, 10][Math.floor(Math.random() * 3)],
          actual_value: Math.random() * 100000,
          action_taken: ['停止交易', '减少持仓', '发送警报'][Math.floor(Math.random() * 3)]
        }));

        setCircuitRules(mockCircuitRules);
        setSystemStatus(mockSystemStatus);
        setRiskEvents(mockRiskEvents);
        setTriggerHistory(mockTriggerHistory);
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

  // 切换规则启用状态
  const handleRuleToggle = (ruleId: string, enabled: boolean) => {
    setCircuitRules(prev => prev.map(rule => 
      rule.id === ruleId ? { ...rule, enabled } : rule
    ));
  };

  // 紧急停止交易
  const handleEmergencyStop = () => {
    Modal.confirm({
      title: '确认紧急停止',
      content: '此操作将立即停止所有交易活动并平仓所有持仓，确定要继续吗？',
      okText: '确认停止',
      cancelText: '取消',
      okType: 'danger',
      onOk: () => {
        setSystemStatus(prev => prev ? {
          ...prev,
          trading_enabled: false,
          emergency_mode: true,
          circuit_breaker_active: true
        } : null);
      }
    });
  };

  // 恢复交易
  const handleResumeTrading = () => {
    setSystemStatus(prev => prev ? {
      ...prev,
      trading_enabled: true,
      emergency_mode: false,
      circuit_breaker_active: false
    } : null);
  };

  // 获取优先级颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return '#ff4d4f';
      case 'high': return '#fa8c16';
      case 'medium': return '#faad14';
      case 'low': return '#52c41a';
      default: return '#1890ff';
    }
  };

  // 获取严重程度颜色
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  // 熔断规则表格列定义
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: CircuitBreakerRule) => (
        <div>
          <div className="font-medium">{text}</div>
          <div className="text-xs text-gray-500">{record.description}</div>
        </div>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color="blue">{type.replace('_', ' ').toUpperCase()}</Tag>
      )
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      render: (value: number, record: CircuitBreakerRule) => {
        const unit = record.type === 'loss_limit' ? '$' : '%';
        return `${value.toLocaleString()}${unit}`;
      }
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)}>
          {priority.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => action.replace('_', ' ').toUpperCase()
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record: CircuitBreakerRule) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleRuleToggle(record.id, checked)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      )
    }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-2xl mb-4">⚡</div>
          <div>加载熔断控制模块...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <ThunderboltOutlined className="text-2xl text-red-400" />
            <h1 className="text-2xl font-bold">熔断控制</h1>
            <Tag color={systemStatus?.circuit_breaker_active ? 'red' : 'green'}>
              {systemStatus?.circuit_breaker_active ? '熔断激活' : '正常运行'}
            </Tag>
          </div>
          <Space>
            <Button 
              type="primary" 
              icon={<SettingOutlined />}
              onClick={() => setConfigModalVisible(true)}
            >
              规则配置
            </Button>
            <Button 
              danger 
              icon={<StopOutlined />}
              onClick={handleEmergencyStop}
              disabled={systemStatus?.emergency_mode}
            >
              紧急停止
            </Button>
            {systemStatus?.emergency_mode && (
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />}
                onClick={handleResumeTrading}
              >
                恢复交易
              </Button>
            )}
          </Space>
        </div>
      </div>

      {/* 系统状态警告 */}
      {systemStatus?.emergency_mode && (
        <Alert
          message="紧急模式激活"
          description="系统已进入紧急模式，所有交易活动已停止。请检查风险状况后手动恢复交易。"
          type="error"
          showIcon
          className="mb-6"
          action={
            <Button size="small" danger onClick={handleResumeTrading}>
              恢复交易
            </Button>
          }
        />
      )}

      {/* 系统状态概览 */}
      {systemStatus && (
        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">交易状态</span>}
                value={systemStatus.trading_enabled ? '启用' : '禁用'}
                valueStyle={{ 
                  color: systemStatus.trading_enabled ? '#52c41a' : '#ff4d4f' 
                }}
                prefix={
                  systemStatus.trading_enabled ? 
                  <CheckCircleOutlined /> : <CloseCircleOutlined />
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">风险等级</span>}
                value={systemStatus.risk_level.toUpperCase()}
                valueStyle={{ 
                  color: systemStatus.risk_level === 'high' ? '#ff4d4f' : 
                         systemStatus.risk_level === 'medium' ? '#faad14' : '#52c41a'
                }}
                prefix={<AlertOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">今日触发次数</span>}
                value={systemStatus.total_triggers_today}
                valueStyle={{ color: '#1890ff' }}
                prefix={<FireOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">启用规则数</span>}
                value={circuitRules.filter(rule => rule.enabled).length}
                suffix={`/ ${circuitRules.length}`}
                valueStyle={{ color: '#52c41a' }}
                prefix={<SafetyOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={[16, 16]}>
        {/* 熔断规则配置 */}
        <Col xs={24} xl={14}>
          <Card 
            title={<span className="text-white">熔断规则配置</span>}
            className="bg-gray-800 border-gray-700 mb-4"
          >
            <Table
              columns={ruleColumns}
              dataSource={circuitRules}
              rowKey="id"
              pagination={false}
              className="dark-table"
              size="small"
            />
          </Card>
        </Col>

        {/* 实时风险监控 */}
        <Col xs={24} xl={10}>
          <Card 
            title={<span className="text-white">实时风险监控</span>}
            className="bg-gray-800 border-gray-700 mb-4"
          >
            <div className="space-y-4">
              {circuitRules.filter(rule => rule.enabled).map((rule) => {
                const currentValue = Math.random() * rule.threshold * 1.2;
                const utilization = (currentValue / rule.threshold) * 100;
                
                return (
                  <div key={rule.id} className="p-3 bg-gray-700 rounded">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{rule.name}</span>
                      <Tag 
                        color={utilization > 90 ? 'red' : utilization > 70 ? 'orange' : 'green'}
                      >
                        {utilization.toFixed(1)}%
                      </Tag>
                    </div>
                    <Progress 
                      percent={Math.min(utilization, 100)}
                      strokeColor={
                        utilization > 90 ? '#ff4d4f' :
                        utilization > 70 ? '#faad14' : '#52c41a'
                      }
                      size="small"
                      showInfo={false}
                    />
                    <div className="text-xs text-gray-400 mt-1">
                      当前: {currentValue.toFixed(0)} / 阈值: {rule.threshold}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </Col>

        {/* 风险事件时间线 */}
        <Col xs={24} xl={12}>
          <Card 
            title={<span className="text-white">风险事件时间线</span>}
            className="bg-gray-800 border-gray-700"
          >
            <Timeline
              items={riskEvents.map(event => ({
                color: event.severity === 'critical' ? 'red' : 
                       event.severity === 'high' ? 'orange' : 
                       event.severity === 'medium' ? 'yellow' : 'green',
                children: (
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="font-medium">{event.type}</span>
                      <Tag color={getSeverityColor(event.severity) as any}>
                        {event.severity.toUpperCase()}
                      </Tag>
                      <Tag color={event.status === 'active' ? 'red' : 'green'}>
                        {event.status.toUpperCase()}
                      </Tag>
                    </div>
                    <div className="text-sm text-gray-400 mb-1">
                      {event.description}
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(event.timestamp).toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">
                      影响: ${event.impact.toLocaleString()}
                    </div>
                  </div>
                )
              }))}
            />
          </Card>
        </Col>

        {/* 触发历史图表 */}
        <Col xs={24} xl={12}>
          <Card 
            title={<span className="text-white">触发历史趋势</span>}
            className="bg-gray-800 border-gray-700"
          >
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={triggerHistory.slice(0, 7).reverse()}>
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
                  dataKey="actual_value" 
                  stroke="#EF4444" 
                  fill="#EF4444" 
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* 规则配置模态框 */}
      <Modal
        title="熔断规则配置"
        open={configModalVisible}
        onCancel={() => setConfigModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setConfigModalVisible(false)}>
            取消
          </Button>,
          <Button key="submit" type="primary" onClick={() => setConfigModalVisible(false)}>
            保存配置
          </Button>
        ]}
        width={600}
        className="dark-modal"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="规则类型" name="rule_type">
            <Select placeholder="选择规则类型">
              <Select.Option value="loss_limit">亏损限制</Select.Option>
              <Select.Option value="volatility">波动率控制</Select.Option>
              <Select.Option value="position_limit">持仓限制</Select.Option>
              <Select.Option value="drawdown">回撤保护</Select.Option>
              <Select.Option value="custom">自定义规则</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="触发阈值" name="threshold">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="输入阈值"
            />
          </Form.Item>
          <Form.Item label="触发动作" name="action">
            <Select placeholder="选择触发动作">
              <Select.Option value="stop_trading">停止交易</Select.Option>
              <Select.Option value="reduce_position">减少持仓</Select.Option>
              <Select.Option value="alert_only">仅发送警报</Select.Option>
              <Select.Option value="emergency_exit">紧急平仓</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="优先级" name="priority">
            <Select placeholder="选择优先级">
              <Select.Option value="low">低</Select.Option>
              <Select.Option value="medium">中</Select.Option>
              <Select.Option value="high">高</Select.Option>
              <Select.Option value="critical">关键</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CircuitBreaker;