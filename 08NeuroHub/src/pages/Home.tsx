import React from 'react';
import { Link } from 'react-router-dom';
import { Card, Row, Col, Button, Typography, Space } from 'antd';
import {
  DashboardOutlined,
  DollarOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  SettingOutlined,
  RocketOutlined
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

export default function Home() {
  const modules = [
    {
      title: '战场仪表盘',
      description: '实时监控面板和系统状态总览',
      icon: <DashboardOutlined className="text-4xl text-blue-500" />,
      path: '/dashboard',
      status: 'active'
    },
    {
      title: '资金管理',
      description: '模式切换器和风险敞口监控',
      icon: <DollarOutlined className="text-4xl text-green-500" />,
      path: '/fund-management',
      status: 'active'
    },
    {
      title: '熔断控制',
      description: '紧急熔断系统和风险事件处理',
      icon: <ThunderboltOutlined className="text-4xl text-red-500" />,
      path: '/circuit-breaker',
      status: 'active'
    },
    {
      title: '记忆网络',
      description: '历史事件库和决策学习引擎',
      icon: <DatabaseOutlined className="text-4xl text-purple-500" />,
      path: '/memory-network',
      status: 'active'
    },
    {
      title: '系统配置',
      description: '环境管理和通信配置',
      icon: <SettingOutlined className="text-4xl text-gray-500" />,
      path: '/system-config',
      status: 'active'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页面标题 */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <RocketOutlined className="text-6xl text-blue-400 mr-4" />
            <Title level={1} className="text-white mb-0">
              NeuroTrade Nexus
            </Title>
          </div>
          <Title level={2} className="text-blue-300 mb-4">
            模组八 - 总控模块
          </Title>
          <Paragraph className="text-gray-300 text-lg max-w-3xl mx-auto">
            基于神经网络的智能交易系统总控中心，实现多模组协同、实时监控、风险管控和智能决策。
            严格遵循ZeroMQ通信协议、Redis状态管理、SQLite持久化存储和三环境隔离规范。
          </Paragraph>
        </div>

        {/* 模组导航卡片 */}
        <Row gutter={[24, 24]}>
          {modules.map((module, index) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={index}>
              <Card
                 className="h-full bg-gray-800 border-gray-700 hover:border-blue-500 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20"
                 styles={{ body: { padding: '24px' } }}
               >
                <div className="text-center">
                  <div className="mb-4">
                    {module.icon}
                  </div>
                  <Title level={4} className="text-white mb-2">
                    {module.title}
                  </Title>
                  <Paragraph className="text-gray-400 mb-4 min-h-[48px]">
                    {module.description}
                  </Paragraph>
                  <Space direction="vertical" className="w-full">
                    {module.status === 'active' ? (
                      <Link to={module.path}>
                        <Button 
                          type="primary" 
                          size="large" 
                          className="w-full bg-blue-600 hover:bg-blue-500 border-blue-600 hover:border-blue-500"
                        >
                          进入模组
                        </Button>
                      </Link>
                    ) : (
                      <Button 
                        size="large" 
                        disabled 
                        className="w-full"
                      >
                        即将上线
                      </Button>
                    )}
                    <div className="text-xs text-gray-500">
                      状态: {module.status === 'active' ? '已激活' : '开发中'}
                    </div>
                  </Space>
                </div>
              </Card>
            </Col>
          ))}
        </Row>

        {/* 系统信息 */}
        <div className="mt-12 text-center">
          <Card className="bg-gray-800 border-gray-700">
            <Row gutter={[24, 24]}>
              <Col xs={24} md={8}>
                <div className="text-center">
                  <Title level={4} className="text-blue-400 mb-2">
                    通信协议
                  </Title>
                  <Paragraph className="text-gray-300 mb-0">
                    ZeroMQ 高性能异步消息传递
                  </Paragraph>
                </div>
              </Col>
              <Col xs={24} md={8}>
                <div className="text-center">
                  <Title level={4} className="text-green-400 mb-2">
                    状态管理
                  </Title>
                  <Paragraph className="text-gray-300 mb-0">
                    Redis 实时状态缓存与发布订阅
                  </Paragraph>
                </div>
              </Col>
              <Col xs={24} md={8}>
                <div className="text-center">
                  <Title level={4} className="text-purple-400 mb-2">
                    数据存储
                  </Title>
                  <Paragraph className="text-gray-300 mb-0">
                    SQLite 轻量级持久化存储
                  </Paragraph>
                </div>
              </Col>
            </Row>
          </Card>
        </div>

        {/* 版权信息 */}
        <div className="text-center mt-8 text-gray-500 text-sm">
          <Paragraph className="mb-0">
            NeuroTrade Nexus (NTN) - 模组八总控模块 | 基于核心设计理念的智能交易系统
          </Paragraph>
        </div>
      </div>
    </div>
  );
}