import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Form,
  Input,
  Select,
  Switch,
  Button,
  Tabs,
  Space,
  Divider,
  Alert,
  Badge,
  Tooltip,
  InputNumber,
  Modal,
  message,
  Table,
  Tag
} from 'antd';
import {
  SettingOutlined,
  SaveOutlined,
  ReloadOutlined,
  ExportOutlined,
  ImportOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DatabaseOutlined,
  ApiOutlined,
  CloudOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface EnvironmentConfig {
  name: string;
  status: 'active' | 'inactive' | 'maintenance';
  database: {
    host: string;
    port: number;
    name: string;
    ssl: boolean;
  };
  redis: {
    host: string;
    port: number;
    password: string;
    ssl: boolean;
  };
  zeromq: {
    publisherPort: number;
    subscriberPort: number;
    heartbeatInterval: number;
  };
}

interface SystemMetrics {
  timestamp: string;
  cpuUsage: number;
  memoryUsage: number;
  networkLatency: number;
  activeConnections: number;
}

const SystemConfig: React.FC = () => {
  const [activeTab, setActiveTab] = useState('environment');
  const [currentEnvironment, setCurrentEnvironment] = useState('development');
  const [isLoading, setIsLoading] = useState(false);
  const [configChanged, setConfigChanged] = useState(false);
  const [form] = Form.useForm();
  const [envForm] = Form.useForm();
  const [zeromqForm] = Form.useForm();
  const [redisForm] = Form.useForm();

  // 模拟环境配置数据
  const [environments, setEnvironments] = useState<Record<string, EnvironmentConfig>>({
    development: {
      name: '开发环境',
      status: 'active',
      database: {
        host: 'localhost',
        port: 5432,
        name: 'neurohub_dev',
        ssl: false
      },
      redis: {
        host: 'localhost',
        port: 6379,
        password: '',
        ssl: false
      },
      zeromq: {
        publisherPort: 5555,
        subscriberPort: 5556,
        heartbeatInterval: 1000
      }
    },
    staging: {
      name: '测试环境',
      status: 'inactive',
      database: {
        host: 'staging-db.example.com',
        port: 5432,
        name: 'neurohub_staging',
        ssl: true
      },
      redis: {
        host: 'staging-redis.example.com',
        port: 6379,
        password: 'staging_password',
        ssl: true
      },
      zeromq: {
        publisherPort: 5557,
        subscriberPort: 5558,
        heartbeatInterval: 2000
      }
    },
    production: {
      name: '生产环境',
      status: 'maintenance',
      database: {
        host: 'prod-db.example.com',
        port: 5432,
        name: 'neurohub_prod',
        ssl: true
      },
      redis: {
        host: 'prod-redis.example.com',
        port: 6379,
        password: 'prod_password',
        ssl: true
      },
      zeromq: {
        publisherPort: 5559,
        subscriberPort: 5560,
        heartbeatInterval: 3000
      }
    }
  });

  // 模拟系统指标数据
  const [systemMetrics] = useState<SystemMetrics[]>([
    { timestamp: '14:00', cpuUsage: 45, memoryUsage: 62, networkLatency: 12, activeConnections: 156 },
    { timestamp: '14:05', cpuUsage: 52, memoryUsage: 58, networkLatency: 15, activeConnections: 142 },
    { timestamp: '14:10', cpuUsage: 38, memoryUsage: 65, networkLatency: 11, activeConnections: 168 },
    { timestamp: '14:15', cpuUsage: 41, memoryUsage: 61, networkLatency: 13, activeConnections: 159 },
    { timestamp: '14:20', cpuUsage: 47, memoryUsage: 59, networkLatency: 14, activeConnections: 173 },
    { timestamp: '14:25', cpuUsage: 43, memoryUsage: 63, networkLatency: 12, activeConnections: 161 }
  ]);

  // 模拟配置历史记录
  const [configHistory] = useState([
    {
      id: '1',
      timestamp: '2024-01-15 14:30:25',
      environment: 'development',
      action: '更新ZeroMQ配置',
      user: 'admin',
      changes: 'publisherPort: 5555 → 5557'
    },
    {
      id: '2',
      timestamp: '2024-01-15 13:15:10',
      environment: 'staging',
      action: '切换环境状态',
      user: 'admin',
      changes: 'status: active → inactive'
    },
    {
      id: '3',
      timestamp: '2024-01-15 12:45:33',
      environment: 'production',
      action: '更新数据库配置',
      user: 'admin',
      changes: 'ssl: false → true'
    }
  ]);

  // 初始化表单数据
  useEffect(() => {
    const currentConfig = environments[currentEnvironment];
    if (currentConfig) {
      envForm.setFieldsValue({
        name: currentConfig.name,
        status: currentConfig.status
      });
      zeromqForm.setFieldsValue(currentConfig.zeromq);
      redisForm.setFieldsValue(currentConfig.redis);
    }
  }, [currentEnvironment, environments, envForm, zeromqForm, redisForm]);

  // 保存配置
  const handleSaveConfig = async () => {
    try {
      setIsLoading(true);
      
      // 模拟保存操作
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      message.success('配置保存成功');
      setConfigChanged(false);
    } catch (error) {
      message.error('配置保存失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 测试连接
  const handleTestConnection = async (type: 'database' | 'redis' | 'zeromq') => {
    try {
      setIsLoading(true);
      
      // 模拟测试连接
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      message.success(`${type.toUpperCase()} 连接测试成功`);
    } catch (error) {
      message.error(`${type.toUpperCase()} 连接测试失败`);
    } finally {
      setIsLoading(false);
    }
  };

  // 切换环境
  const handleEnvironmentSwitch = (env: string) => {
    if (configChanged) {
      Modal.confirm({
        title: '确认切换环境',
        content: '当前配置有未保存的更改，切换环境将丢失这些更改。是否继续？',
        onOk: () => {
          setCurrentEnvironment(env);
          setConfigChanged(false);
        }
      });
    } else {
      setCurrentEnvironment(env);
    }
  };

  // 环境状态颜色映射
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'green';
      case 'inactive': return 'red';
      case 'maintenance': return 'orange';
      default: return 'gray';
    }
  };

  // 环境状态图标映射
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircleOutlined />;
      case 'inactive': return <CloseCircleOutlined />;
      case 'maintenance': return <SyncOutlined />;
      default: return <WarningOutlined />;
    }
  };

  // 配置历史表格列定义
  const historyColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 150
    },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      width: 100,
      render: (env: string) => (
        <Tag color={getStatusColor(environments[env]?.status || 'inactive')}>
          {environments[env]?.name || env}
        </Tag>
      )
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 150
    },
    {
      title: '用户',
      dataIndex: 'user',
      key: 'user',
      width: 100
    },
    {
      title: '变更内容',
      dataIndex: 'changes',
      key: 'changes',
      ellipsis: true
    }
  ];

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              <SettingOutlined className="mr-3 text-blue-600" />
              系统配置
            </h1>
            <p className="text-gray-600">环境管理和通信配置</p>
          </div>
          <div className="flex items-center space-x-4">
            {configChanged && (
              <Alert
                message="配置已修改"
                description="请保存配置以应用更改"
                type="warning"
                showIcon
                className="mb-0"
              />
            )}
            <Button 
              type="primary" 
              icon={<SaveOutlined />}
              loading={isLoading}
              onClick={handleSaveConfig}
              disabled={!configChanged}
            >
              保存配置
            </Button>
          </div>
        </div>
      </div>

      {/* 环境选择器 */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">当前环境</h3>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
              刷新
            </Button>
            <Button icon={<ExportOutlined />}>
              导出配置
            </Button>
            <Button icon={<ImportOutlined />}>
              导入配置
            </Button>
          </Space>
        </div>
        
        <Row gutter={[16, 16]}>
          {Object.entries(environments).map(([key, env]) => (
            <Col xs={24} sm={8} key={key}>
              <Card 
                size="small"
                className={`cursor-pointer transition-all ${
                  currentEnvironment === key 
                    ? 'border-blue-500 shadow-md' 
                    : 'hover:border-gray-400'
                }`}
                onClick={() => handleEnvironmentSwitch(key)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold">{env.name}</div>
                    <div className="text-sm text-gray-500">{key}</div>
                  </div>
                  <Badge 
                    status={env.status === 'active' ? 'processing' : 'default'}
                    text={
                      <span className={`text-${getStatusColor(env.status)}-600`}>
                        {getStatusIcon(env.status)} {env.status.toUpperCase()}
                      </span>
                    }
                  />
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 系统监控 */}
      <Card className="mb-6" title="系统监控">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={6}>
            <Card size="small">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">45%</div>
                <div className="text-gray-500">CPU使用率</div>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card size="small">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">63%</div>
                <div className="text-gray-500">内存使用率</div>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card size="small">
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">12ms</div>
                <div className="text-gray-500">网络延迟</div>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card size="small">
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">161</div>
                <div className="text-gray-500">活跃连接</div>
              </div>
            </Card>
          </Col>
        </Row>
        
        <div className="mt-6">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={systemMetrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <RechartsTooltip />
              <Line type="monotone" dataKey="cpuUsage" stroke="#1890ff" name="CPU使用率" />
              <Line type="monotone" dataKey="memoryUsage" stroke="#52c41a" name="内存使用率" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 配置标签页 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="环境配置" key="environment">
            <Form
              form={envForm}
              layout="vertical"
              onValuesChange={() => setConfigChanged(true)}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Form.Item label="环境名称" name="name">
                    <Input placeholder="请输入环境名称" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="环境状态" name="status">
                    <Select placeholder="请选择环境状态">
                      <Option value="active">活跃</Option>
                      <Option value="inactive">非活跃</Option>
                      <Option value="maintenance">维护中</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </TabPane>

          <TabPane tab="数据库配置" key="database">
            <Form layout="vertical" onValuesChange={() => setConfigChanged(true)}>
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Form.Item label="主机地址" initialValue={environments[currentEnvironment]?.database.host}>
                    <Input placeholder="请输入数据库主机地址" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="端口" initialValue={environments[currentEnvironment]?.database.port}>
                    <InputNumber 
                      placeholder="请输入端口号" 
                      style={{ width: '100%' }}
                      min={1}
                      max={65535}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="数据库名称" initialValue={environments[currentEnvironment]?.database.name}>
                    <Input placeholder="请输入数据库名称" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="SSL连接" valuePropName="checked" initialValue={environments[currentEnvironment]?.database.ssl}>
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              <Divider />
              <Space>
                <Button 
                  type="primary" 
                  icon={<DatabaseOutlined />}
                  loading={isLoading}
                  onClick={() => handleTestConnection('database')}
                >
                  测试连接
                </Button>
              </Space>
            </Form>
          </TabPane>

          <TabPane tab="Redis配置" key="redis">
            <Form 
              form={redisForm}
              layout="vertical" 
              onValuesChange={() => setConfigChanged(true)}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Form.Item label="主机地址" name="host">
                    <Input placeholder="请输入Redis主机地址" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="端口" name="port">
                    <InputNumber 
                      placeholder="请输入端口号" 
                      style={{ width: '100%' }}
                      min={1}
                      max={65535}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="密码" name="password">
                    <Input.Password placeholder="请输入Redis密码" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item label="SSL连接" name="ssl" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              <Divider />
              <Space>
                <Button 
                  type="primary" 
                  icon={<CloudOutlined />}
                  loading={isLoading}
                  onClick={() => handleTestConnection('redis')}
                >
                  测试连接
                </Button>
              </Space>
            </Form>
          </TabPane>

          <TabPane tab="ZeroMQ配置" key="zeromq">
            <Form 
              form={zeromqForm}
              layout="vertical" 
              onValuesChange={() => setConfigChanged(true)}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <Form.Item label="发布者端口" name="publisherPort">
                    <InputNumber 
                      placeholder="请输入发布者端口" 
                      style={{ width: '100%' }}
                      min={1024}
                      max={65535}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item label="订阅者端口" name="subscriberPort">
                    <InputNumber 
                      placeholder="请输入订阅者端口" 
                      style={{ width: '100%' }}
                      min={1024}
                      max={65535}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item label="心跳间隔(ms)" name="heartbeatInterval">
                    <InputNumber 
                      placeholder="请输入心跳间隔" 
                      style={{ width: '100%' }}
                      min={100}
                      max={10000}
                    />
                  </Form.Item>
                </Col>
              </Row>
              <Divider />
              <Space>
                <Button 
                  type="primary" 
                  icon={<ApiOutlined />}
                  loading={isLoading}
                  onClick={() => handleTestConnection('zeromq')}
                >
                  测试连接
                </Button>
              </Space>
            </Form>
          </TabPane>

          <TabPane tab="配置历史" key="history">
            <Table
              columns={historyColumns}
              dataSource={configHistory}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`
              }}
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default SystemConfig;