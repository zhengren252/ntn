import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Input,
  Select,
  DatePicker,
  Button,
  Tag,
  Progress,
  Statistic,
  Timeline,
  Tabs,
  Space,
  Badge,
  Tooltip,
  Modal,
  Form,
  Switch
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  BarChartOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TabPane } = Tabs;

interface HistoryEvent {
  id: string;
  timestamp: string;
  type: 'trade' | 'risk' | 'system' | 'decision';
  category: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  result: 'success' | 'failure' | 'partial';
  confidence: number;
  learningValue: number;
}

interface DecisionPattern {
  id: string;
  pattern: string;
  frequency: number;
  successRate: number;
  avgReturn: number;
  riskLevel: string;
  lastUsed: string;
}

interface LearningModel {
  id: string;
  name: string;
  type: 'neural' | 'reinforcement' | 'ensemble';
  accuracy: number;
  trainingData: number;
  status: 'active' | 'training' | 'paused';
  lastUpdate: string;
}

const MemoryNetwork: React.FC = () => {
  const [activeTab, setActiveTab] = useState('events');
  const [searchText, setSearchText] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [dateRange, setDateRange] = useState<any>(null);
  const [selectedEvent, setSelectedEvent] = useState<HistoryEvent | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [learningEnabled, setLearningEnabled] = useState(true);

  // 模拟历史事件数据
  const [historyEvents] = useState<HistoryEvent[]>([
    {
      id: '1',
      timestamp: '2024-01-15 14:30:25',
      type: 'trade',
      category: '股票交易',
      description: '执行大额买入订单 - AAPL 1000股',
      impact: 'high',
      result: 'success',
      confidence: 0.92,
      learningValue: 0.85
    },
    {
      id: '2',
      timestamp: '2024-01-15 13:45:12',
      type: 'risk',
      category: '风险控制',
      description: '检测到异常波动，触发风险预警',
      impact: 'medium',
      result: 'success',
      confidence: 0.78,
      learningValue: 0.72
    },
    {
      id: '3',
      timestamp: '2024-01-15 12:20:08',
      type: 'decision',
      category: '策略决策',
      description: '基于技术指标调整仓位配置',
      impact: 'medium',
      result: 'partial',
      confidence: 0.65,
      learningValue: 0.58
    }
  ]);

  // 模拟决策模式数据
  const [decisionPatterns] = useState<DecisionPattern[]>([
    {
      id: '1',
      pattern: '突破买入模式',
      frequency: 156,
      successRate: 0.73,
      avgReturn: 0.045,
      riskLevel: 'medium',
      lastUsed: '2024-01-15 14:30:25'
    },
    {
      id: '2',
      pattern: '均值回归模式',
      frequency: 89,
      successRate: 0.68,
      avgReturn: 0.032,
      riskLevel: 'low',
      lastUsed: '2024-01-15 13:15:10'
    },
    {
      id: '3',
      pattern: '动量追踪模式',
      frequency: 234,
      successRate: 0.81,
      avgReturn: 0.067,
      riskLevel: 'high',
      lastUsed: '2024-01-15 12:45:33'
    }
  ]);

  // 模拟学习模型数据
  const [learningModels] = useState<LearningModel[]>([
    {
      id: '1',
      name: '深度强化学习模型',
      type: 'reinforcement',
      accuracy: 0.847,
      trainingData: 125000,
      status: 'active',
      lastUpdate: '2024-01-15 10:30:00'
    },
    {
      id: '2',
      name: '神经网络预测模型',
      type: 'neural',
      accuracy: 0.792,
      trainingData: 89000,
      status: 'training',
      lastUpdate: '2024-01-15 09:15:00'
    },
    {
      id: '3',
      name: '集成学习模型',
      type: 'ensemble',
      accuracy: 0.865,
      trainingData: 156000,
      status: 'active',
      lastUpdate: '2024-01-15 11:45:00'
    }
  ]);

  // 模拟学习效果数据
  const learningEffectData = [
    { date: '01-10', accuracy: 0.72, confidence: 0.68 },
    { date: '01-11', accuracy: 0.75, confidence: 0.71 },
    { date: '01-12', accuracy: 0.78, confidence: 0.74 },
    { date: '01-13', accuracy: 0.81, confidence: 0.77 },
    { date: '01-14', accuracy: 0.84, confidence: 0.80 },
    { date: '01-15', accuracy: 0.87, confidence: 0.83 }
  ];

  // 模拟决策分布数据
  const decisionDistributionData = [
    { name: '成功决策', value: 73, color: '#52c41a' },
    { name: '部分成功', value: 18, color: '#faad14' },
    { name: '失败决策', value: 9, color: '#ff4d4f' }
  ];

  // 历史事件表格列定义
  const eventColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 150,
      render: (text: string) => dayjs(text).format('MM-DD HH:mm:ss')
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => {
        const colors = {
          trade: 'blue',
          risk: 'red',
          system: 'green',
          decision: 'purple'
        };
        return <Tag color={colors[type as keyof typeof colors]}>{type.toUpperCase()}</Tag>;
      }
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '影响度',
      dataIndex: 'impact',
      key: 'impact',
      width: 80,
      render: (impact: string) => {
        const colors = { high: 'red', medium: 'orange', low: 'green' };
        return <Tag color={colors[impact as keyof typeof colors]}>{impact.toUpperCase()}</Tag>;
      }
    },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 80,
      render: (result: string) => {
        const colors = { success: 'green', failure: 'red', partial: 'orange' };
        return <Tag color={colors[result as keyof typeof colors]}>{result.toUpperCase()}</Tag>;
      }
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 100,
      render: (confidence: number) => (
        <Progress percent={Math.round(confidence * 100)} size="small" />
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: any, record: HistoryEvent) => (
        <Button 
          type="link" 
          size="small"
          onClick={() => {
            setSelectedEvent(record);
            setIsModalVisible(true);
          }}
        >
          详情
        </Button>
      )
    }
  ];

  // 决策模式表格列定义
  const patternColumns = [
    {
      title: '模式名称',
      dataIndex: 'pattern',
      key: 'pattern'
    },
    {
      title: '使用频次',
      dataIndex: 'frequency',
      key: 'frequency',
      render: (freq: number) => <Badge count={freq} style={{ backgroundColor: '#52c41a' }} />
    },
    {
      title: '成功率',
      dataIndex: 'successRate',
      key: 'successRate',
      render: (rate: number) => (
        <Progress percent={Math.round(rate * 100)} size="small" />
      )
    },
    {
      title: '平均收益',
      dataIndex: 'avgReturn',
      key: 'avgReturn',
      render: (ret: number) => (
        <span style={{ color: ret > 0 ? '#52c41a' : '#ff4d4f' }}>
          {(ret * 100).toFixed(2)}%
        </span>
      )
    },
    {
      title: '风险等级',
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      render: (level: string) => {
        const colors = { high: 'red', medium: 'orange', low: 'green' };
        return <Tag color={colors[level as keyof typeof colors]}>{level.toUpperCase()}</Tag>;
      }
    },
    {
      title: '最后使用',
      dataIndex: 'lastUsed',
      key: 'lastUsed',
      render: (text: string) => dayjs(text).format('MM-DD HH:mm')
    }
  ];

  // 学习模型表格列定义
  const modelColumns = [
    {
      title: '模型名称',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          neural: 'blue',
          reinforcement: 'purple',
          ensemble: 'green'
        };
        return <Tag color={colors[type as keyof typeof colors]}>{type.toUpperCase()}</Tag>;
      }
    },
    {
      title: '准确率',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (accuracy: number) => (
        <Progress percent={Math.round(accuracy * 100)} size="small" />
      )
    },
    {
      title: '训练数据量',
      dataIndex: 'trainingData',
      key: 'trainingData',
      render: (data: number) => `${(data / 1000).toFixed(0)}K`
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = { active: 'green', training: 'blue', paused: 'orange' };
        return <Badge status={status === 'active' ? 'processing' : 'default'} text={status.toUpperCase()} />;
      }
    },
    {
      title: '最后更新',
      dataIndex: 'lastUpdate',
      key: 'lastUpdate',
      render: (text: string) => dayjs(text).format('MM-DD HH:mm')
    }
  ];

  // 过滤历史事件
  const filteredEvents = historyEvents.filter(event => {
    const matchesSearch = event.description.toLowerCase().includes(searchText.toLowerCase()) ||
                         event.category.toLowerCase().includes(searchText.toLowerCase());
    const matchesType = selectedType === 'all' || event.type === selectedType;
    const matchesDate = !dateRange || (
      dayjs(event.timestamp).isAfter(dateRange[0]) && 
      dayjs(event.timestamp).isBefore(dateRange[1])
    );
    return matchesSearch && matchesType && matchesDate;
  });

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          <DatabaseOutlined className="mr-3 text-purple-600" />
          记忆网络
        </h1>
        <p className="text-gray-600">历史事件库和决策学习引擎</p>
      </div>

      {/* 总览统计 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="历史事件总数"
              value={historyEvents.length}
              prefix={<HistoryOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="决策模式数量"
              value={decisionPatterns.length}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="学习模型数量"
              value={learningModels.length}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-gray-500 text-sm mb-1">学习引擎</div>
                <div className="text-2xl font-bold text-green-600">
                  {learningEnabled ? '运行中' : '已暂停'}
                </div>
              </div>
              <Switch
                checked={learningEnabled}
                onChange={setLearningEnabled}
                checkedChildren={<PlayCircleOutlined />}
                unCheckedChildren={<PauseCircleOutlined />}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 学习效果图表 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={16}>
          <Card title="学习效果趋势" extra={<SettingOutlined />}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={learningEffectData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 1]} />
                <RechartsTooltip />
                <Line 
                  type="monotone" 
                  dataKey="accuracy" 
                  stroke="#1890ff" 
                  strokeWidth={2}
                  name="准确率"
                />
                <Line 
                  type="monotone" 
                  dataKey="confidence" 
                  stroke="#52c41a" 
                  strokeWidth={2}
                  name="置信度"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="决策结果分布">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={decisionDistributionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {decisionDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4">
              {decisionDistributionData.map((item, index) => (
                <div key={index} className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <div 
                      className="w-3 h-3 rounded mr-2" 
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm">{item.name}</span>
                  </div>
                  <span className="font-semibold">{item.value}%</span>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 主要内容标签页 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="历史事件" key="events">
            {/* 搜索和过滤 */}
            <div className="mb-4">
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <Input
                    placeholder="搜索事件描述或分类"
                    prefix={<SearchOutlined />}
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                  />
                </Col>
                <Col xs={24} sm={6}>
                  <Select
                    placeholder="选择类型"
                    value={selectedType}
                    onChange={setSelectedType}
                    style={{ width: '100%' }}
                  >
                    <Option value="all">全部类型</Option>
                    <Option value="trade">交易</Option>
                    <Option value="risk">风险</Option>
                    <Option value="system">系统</Option>
                    <Option value="decision">决策</Option>
                  </Select>
                </Col>
                <Col xs={24} sm={8}>
                  <RangePicker
                    value={dateRange}
                    onChange={setDateRange}
                    style={{ width: '100%' }}
                  />
                </Col>
                <Col xs={24} sm={2}>
                  <Button icon={<DownloadOutlined />} type="primary">
                    导出
                  </Button>
                </Col>
              </Row>
            </div>

            <Table
              columns={eventColumns}
              dataSource={filteredEvents}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`
              }}
              scroll={{ x: 1000 }}
            />
          </TabPane>

          <TabPane tab="决策模式" key="patterns">
            <Table
              columns={patternColumns}
              dataSource={decisionPatterns}
              rowKey="id"
              pagination={false}
            />
          </TabPane>

          <TabPane tab="学习模型" key="models">
            <Table
              columns={modelColumns}
              dataSource={learningModels}
              rowKey="id"
              pagination={false}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 事件详情模态框 */}
      <Modal
        title="事件详情"
        visible={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setIsModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={600}
      >
        {selectedEvent && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">事件ID</div>
                  <div className="font-semibold">{selectedEvent.id}</div>
                </div>
              </Col>
              <Col span={12}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">时间戳</div>
                  <div className="font-semibold">{selectedEvent.timestamp}</div>
                </div>
              </Col>
              <Col span={12}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">类型</div>
                  <Tag color="blue">{selectedEvent.type.toUpperCase()}</Tag>
                </div>
              </Col>
              <Col span={12}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">分类</div>
                  <div className="font-semibold">{selectedEvent.category}</div>
                </div>
              </Col>
              <Col span={24}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">描述</div>
                  <div className="font-semibold">{selectedEvent.description}</div>
                </div>
              </Col>
              <Col span={8}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">影响度</div>
                  <Tag color={selectedEvent.impact === 'high' ? 'red' : selectedEvent.impact === 'medium' ? 'orange' : 'green'}>
                    {selectedEvent.impact.toUpperCase()}
                  </Tag>
                </div>
              </Col>
              <Col span={8}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">结果</div>
                  <Tag color={selectedEvent.result === 'success' ? 'green' : selectedEvent.result === 'failure' ? 'red' : 'orange'}>
                    {selectedEvent.result.toUpperCase()}
                  </Tag>
                </div>
              </Col>
              <Col span={8}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">置信度</div>
                  <Progress percent={Math.round(selectedEvent.confidence * 100)} size="small" />
                </div>
              </Col>
              <Col span={24}>
                <div className="mb-4">
                  <div className="text-gray-500 text-sm mb-1">学习价值</div>
                  <Progress 
                    percent={Math.round(selectedEvent.learningValue * 100)} 
                    size="small"
                    strokeColor="#722ed1"
                  />
                </div>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default MemoryNetwork;