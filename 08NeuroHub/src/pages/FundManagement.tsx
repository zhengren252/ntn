import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Switch, Button, Progress, Statistic, Alert, Table, Tag, Modal, Form, InputNumber, Select, Space, Divider } from 'antd';
import {
  DollarOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  BankOutlined,
  LineChartOutlined,
  SafetyOutlined
} from '@ant-design/icons';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

// 类型定义
interface TradingMode {
  id: string;
  name: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high';
  max_position_size: number;
  stop_loss_threshold: number;
  enabled: boolean;
}

interface FundStatus {
  total_capital: number;
  available_capital: number;
  used_capital: number;
  unrealized_pnl: number;
  realized_pnl: number;
  daily_pnl: number;
  max_drawdown: number;
  win_rate: number;
}

interface RiskExposure {
  symbol: string;
  position_size: number;
  market_value: number;
  unrealized_pnl: number;
  risk_percentage: number;
  stop_loss: number;
  take_profit: number;
}

interface RiskLimit {
  type: string;
  current_value: number;
  limit_value: number;
  utilization: number;
  status: 'safe' | 'warning' | 'danger';
}

const FundManagement: React.FC = () => {
  const [tradingModes, setTradingModes] = useState<TradingMode[]>([]);
  const [fundStatus, setFundStatus] = useState<FundStatus | null>(null);
  const [riskExposures, setRiskExposures] = useState<RiskExposure[]>([]);
  const [riskLimits, setRiskLimits] = useState<RiskLimit[]>([]);
  const [loading, setLoading] = useState(true);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 模拟数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 模拟交易模式数据
        const mockTradingModes: TradingMode[] = [
          {
            id: 'conservative',
            name: '保守模式',
            description: '低风险稳健策略，适合资金保值',
            risk_level: 'low',
            max_position_size: 0.1,
            stop_loss_threshold: 0.02,
            enabled: true
          },
          {
            id: 'balanced',
            name: '平衡模式',
            description: '中等风险收益平衡策略',
            risk_level: 'medium',
            max_position_size: 0.3,
            stop_loss_threshold: 0.05,
            enabled: false
          },
          {
            id: 'aggressive',
            name: '激进模式',
            description: '高风险高收益策略，追求最大收益',
            risk_level: 'high',
            max_position_size: 0.5,
            stop_loss_threshold: 0.1,
            enabled: false
          }
        ];

        // 模拟资金状态数据
        const mockFundStatus: FundStatus = {
          total_capital: 1000000,
          available_capital: 650000,
          used_capital: 350000,
          unrealized_pnl: 25000,
          realized_pnl: 45000,
          daily_pnl: 8500,
          max_drawdown: 0.08,
          win_rate: 0.68
        };

        // 模拟风险敞口数据
        const mockRiskExposures: RiskExposure[] = [
          {
            symbol: 'BTC/USDT',
            position_size: 2.5,
            market_value: 125000,
            unrealized_pnl: 8500,
            risk_percentage: 12.5,
            stop_loss: 48000,
            take_profit: 55000
          },
          {
            symbol: 'ETH/USDT',
            position_size: 50,
            market_value: 150000,
            unrealized_pnl: -3200,
            risk_percentage: 15.0,
            stop_loss: 2800,
            take_profit: 3500
          },
          {
            symbol: 'ADA/USDT',
            position_size: 10000,
            market_value: 75000,
            unrealized_pnl: 2100,
            risk_percentage: 7.5,
            stop_loss: 0.68,
            take_profit: 0.85
          }
        ];

        // 模拟风险限制数据
        const mockRiskLimits: RiskLimit[] = [
          {
            type: '单日最大亏损',
            current_value: 15000,
            limit_value: 50000,
            utilization: 30,
            status: 'safe'
          },
          {
            type: '最大持仓比例',
            current_value: 35,
            limit_value: 50,
            utilization: 70,
            status: 'warning'
          },
          {
            type: '最大回撤',
            current_value: 8,
            limit_value: 15,
            utilization: 53,
            status: 'safe'
          },
          {
            type: '单笔最大损失',
            current_value: 8500,
            limit_value: 10000,
            utilization: 85,
            status: 'warning'
          }
        ];

        setTradingModes(mockTradingModes);
        setFundStatus(mockFundStatus);
        setRiskExposures(mockRiskExposures);
        setRiskLimits(mockRiskLimits);
      } catch (error) {
        console.error('获取数据失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // 每10秒更新一次

    return () => clearInterval(interval);
  }, []);

  // 切换交易模式
  const handleModeToggle = (modeId: string, enabled: boolean) => {
    setTradingModes(prev => prev.map(mode => ({
      ...mode,
      enabled: mode.id === modeId ? enabled : false // 只允许一个模式激活
    })));
  };

  // 获取风险等级颜色
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low': return '#52c41a';
      case 'medium': return '#faad14';
      case 'high': return '#ff4d4f';
      default: return '#1890ff';
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'safe': return 'success';
      case 'warning': return 'warning';
      case 'danger': return 'error';
      default: return 'default';
    }
  };

  // 资金分布数据
  const fundDistributionData = fundStatus ? [
    { name: '可用资金', value: fundStatus.available_capital, color: '#52c41a' },
    { name: '已用资金', value: fundStatus.used_capital, color: '#1890ff' }
  ] : [];

  // 风险敞口表格列定义
  const exposureColumns = [
    {
      title: '交易对',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text: string) => <strong>{text}</strong>
    },
    {
      title: '持仓数量',
      dataIndex: 'position_size',
      key: 'position_size',
      render: (value: number) => value.toFixed(4)
    },
    {
      title: '市值 (USDT)',
      dataIndex: 'market_value',
      key: 'market_value',
      render: (value: number) => `$${value.toLocaleString()}`
    },
    {
      title: '未实现盈亏',
      dataIndex: 'unrealized_pnl',
      key: 'unrealized_pnl',
      render: (value: number) => (
        <span style={{ color: value >= 0 ? '#52c41a' : '#ff4d4f' }}>
          ${value.toLocaleString()}
        </span>
      )
    },
    {
      title: '风险占比',
      dataIndex: 'risk_percentage',
      key: 'risk_percentage',
      render: (value: number) => (
        <Progress 
          percent={value} 
          size="small" 
          strokeColor={value > 20 ? '#ff4d4f' : value > 10 ? '#faad14' : '#52c41a'}
        />
      )
    }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-2xl mb-4">🏦</div>
          <div>加载资金管理模块...</div>
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
            <BankOutlined className="text-2xl text-green-400" />
            <h1 className="text-2xl font-bold">资金管理</h1>
            <Tag color="green">模式切换器</Tag>
          </div>
          <Button 
            type="primary" 
            icon={<SettingOutlined />}
            onClick={() => setConfigModalVisible(true)}
          >
            风险配置
          </Button>
        </div>
      </div>

      {/* 资金概览 */}
      {fundStatus && (
        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">总资金</span>}
                value={fundStatus.total_capital}
                precision={0}
                prefix="$"
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">可用资金</span>}
                value={fundStatus.available_capital}
                precision={0}
                prefix="$"
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">今日盈亏</span>}
                value={fundStatus.daily_pnl}
                precision={0}
                prefix={fundStatus.daily_pnl >= 0 ? '+$' : '-$'}
                valueStyle={{ color: fundStatus.daily_pnl >= 0 ? '#52c41a' : '#ff4d4f' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="bg-gray-800 border-gray-700">
              <Statistic
                title={<span className="text-gray-300">胜率</span>}
                value={fundStatus.win_rate * 100}
                precision={1}
                suffix="%"
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={[16, 16]}>
        {/* 交易模式切换器 */}
        <Col xs={24} lg={12}>
          <Card 
            title={<span className="text-white">交易模式切换器</span>}
            className="bg-gray-800 border-gray-700"
          >
            <div className="space-y-4">
              {tradingModes.map((mode) => (
                <div key={mode.id} className="p-4 bg-gray-700 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: getRiskLevelColor(mode.risk_level) }}
                      />
                      <span className="font-medium text-white">{mode.name}</span>
                      <Tag color={getRiskLevelColor(mode.risk_level)}>
                        {mode.risk_level.toUpperCase()}
                      </Tag>
                    </div>
                    <Switch
                      checked={mode.enabled}
                      onChange={(checked) => handleModeToggle(mode.id, checked)}
                      checkedChildren="启用"
                      unCheckedChildren="禁用"
                    />
                  </div>
                  <div className="text-sm text-gray-400 mb-2">{mode.description}</div>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-gray-500">最大仓位: </span>
                      <span className="text-white">{(mode.max_position_size * 100).toFixed(0)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">止损阈值: </span>
                      <span className="text-white">{(mode.stop_loss_threshold * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* 资金分布 */}
        <Col xs={24} lg={12}>
          <Card 
            title={<span className="text-white">资金分布</span>}
            className="bg-gray-800 border-gray-700"
          >
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={fundDistributionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {fundDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    color: '#F3F4F6'
                  }}
                  formatter={(value: number) => [`$${value.toLocaleString()}`, '金额']}
                />
                <Legend 
                  wrapperStyle={{ color: '#F3F4F6' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* 风险限制监控 */}
        <Col xs={24}>
          <Card 
            title={<span className="text-white">风险限制监控</span>}
            className="bg-gray-800 border-gray-700 mb-4"
          >
            <Row gutter={[16, 16]}>
              {riskLimits.map((limit, index) => (
                <Col xs={24} sm={12} md={6} key={index}>
                  <div className="p-4 bg-gray-700 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-300">{limit.type}</span>
                      <Tag color={getStatusColor(limit.status)}>
                        {limit.status.toUpperCase()}
                      </Tag>
                    </div>
                    <div className="mb-2">
                      <span className="text-lg font-bold text-white">
                        {limit.current_value.toLocaleString()}
                      </span>
                      <span className="text-sm text-gray-400 ml-1">
                        / {limit.limit_value.toLocaleString()}
                      </span>
                    </div>
                    <Progress 
                      percent={limit.utilization} 
                      size="small"
                      strokeColor={
                        limit.utilization > 80 ? '#ff4d4f' : 
                        limit.utilization > 60 ? '#faad14' : '#52c41a'
                      }
                      showInfo={false}
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      使用率: {limit.utilization}%
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        {/* 风险敞口详情 */}
        <Col xs={24}>
          <Card 
            title={<span className="text-white">风险敞口详情</span>}
            className="bg-gray-800 border-gray-700"
          >
            <Table
              columns={exposureColumns}
              dataSource={riskExposures}
              rowKey="symbol"
              pagination={false}
              className="dark-table"
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* 风险配置模态框 */}
      <Modal
        title="风险参数配置"
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
        className="dark-modal"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="单日最大亏损限制" name="daily_loss_limit">
            <InputNumber
              style={{ width: '100%' }}
              formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value!.replace(/\$\s?|(,*)/g, '')}
              placeholder="50000"
            />
          </Form.Item>
          <Form.Item label="最大持仓比例" name="max_position_ratio">
            <InputNumber
              style={{ width: '100%' }}
              formatter={value => `${value}%`}
              parser={value => value!.replace('%', '') as any}
              placeholder="50"
            />
          </Form.Item>
          <Form.Item label="最大回撤限制" name="max_drawdown">
            <InputNumber
              style={{ width: '100%' }}
              formatter={value => `${value}%`}
              parser={value => value!.replace('%', '') as any}
              placeholder="15"
            />
          </Form.Item>
          <Form.Item label="风险等级" name="risk_level">
            <Select placeholder="选择风险等级">
              <Select.Option value="low">低风险</Select.Option>
              <Select.Option value="medium">中等风险</Select.Option>
              <Select.Option value="high">高风险</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FundManagement;