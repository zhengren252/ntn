'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Bot,
  MessageSquare,
  Zap,
  TrendingUp,
  History,
  FileText,
  Settings,
  Plus,
  Clock
} from 'lucide-react'

interface Session {
  id: string
  title: string
  lastMessage: string
  timestamp: Date
  messageCount: number
}

interface Strategy {
  id: string
  name: string
  createdAt: Date
  performance: number
  status: 'draft' | 'testing' | 'live'
}

interface AiLabSidebarProps {
  currentSessionId: string
  onSessionChange: (sessionId: string) => void
  onNewSession: () => void
}

export const AiLabSidebar = ({ 
  currentSessionId, 
  onSessionChange, 
  onNewSession 
}: AiLabSidebarProps) => {
  const [activeTab, setActiveTab] = useState<'sessions' | 'strategies'>('sessions')
  
  // 模拟数据
  const sessions: Session[] = [
    {
      id: '1',
      title: 'BTCUSDT趋势分析',
      lastMessage: '根据技术指标分析，建议关注支撑位...',
      timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30分钟前
      messageCount: 12
    },
    {
      id: '2',
      title: '网格交易策略优化',
      lastMessage: '已生成优化后的网格策略代码',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2小时前
      messageCount: 8
    },
    {
      id: '3',
      title: '风险管理策略',
      lastMessage: '建议设置止损位为2%',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1天前
      messageCount: 15
    }
  ]

  const strategies: Strategy[] = [
    {
      id: '1',
      name: 'AI动量策略v1.2',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
      performance: 15.2,
      status: 'testing'
    },
    {
      id: '2',
      name: '智能网格策略',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 6),
      performance: 8.7,
      status: 'live'
    },
    {
      id: '3',
      name: '均值回归策略',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
      performance: -2.1,
      status: 'draft'
    }
  ]

  const quickActions = [
    {
      icon: Zap,
      label: '生成新策略',
      description: '基于市场数据生成交易策略',
      action: () => console.log('生成新策略')
    },
    {
      icon: TrendingUp,
      label: '市场分析',
      description: '分析当前市场趋势和机会',
      action: () => console.log('市场分析')
    },
    {
      icon: Bot,
      label: '策略优化',
      description: '优化现有策略参数',
      action: () => console.log('策略优化')
    },
    {
      icon: FileText,
      label: '回测分析',
      description: '对策略进行历史回测',
      action: () => console.log('回测分析')
    }
  ]

  const getStatusBadge = (status: Strategy['status']) => {
    switch (status) {
      case 'live':
        return <Badge variant="default">运行中</Badge>
      case 'testing':
        return <Badge variant="secondary">测试中</Badge>
      case 'draft':
        return <Badge variant="outline">草稿</Badge>
      default:
        return null
    }
  }

  const getPerformanceColor = (performance: number) => {
    if (performance > 0) return 'text-green-600'
    if (performance < 0) return 'text-red-600'
    return 'text-gray-600'
  }

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    return `${diffDays}天前`
  }

  return (
    <div className="space-y-4">
      {/* 快速操作 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Zap className="h-4 w-4" />
            <span>快速操作</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {quickActions.map((action, index) => {
              const Icon = action.icon
              return (
                <Button
                  key={index}
                  variant="outline"
                  className="w-full justify-start h-auto p-3"
                  onClick={action.action}
                >
                  <div className="flex items-start space-x-3">
                    <Icon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <div className="text-left">
                      <div className="font-medium text-sm">{action.label}</div>
                      <div className="text-xs text-gray-500">{action.description}</div>
                    </div>
                  </div>
                </Button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* 会话和策略切换 */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Button
              variant={activeTab === 'sessions' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('sessions')}
              className="flex items-center space-x-1"
            >
              <MessageSquare className="h-3 w-3" />
              <span>会话</span>
            </Button>
            <Button
              variant={activeTab === 'strategies' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('strategies')}
              className="flex items-center space-x-1"
            >
              <Bot className="h-3 w-3" />
              <span>策略</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {activeTab === 'sessions' && (
            <div className="space-y-3">
              <Button
                onClick={onNewSession}
                className="w-full flex items-center space-x-2"
                size="sm"
              >
                <Plus className="h-4 w-4" />
                <span>新建会话</span>
              </Button>
              
              <ScrollArea className="h-64">
                <div className="space-y-2">
                  {sessions.map((session) => (
                    <div
                      key={session.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-gray-50 ${
                        currentSessionId === session.id ? 'border-blue-500 bg-blue-50' : ''
                      }`}
                      onClick={() => onSessionChange(session.id)}
                    >
                      <div className="flex items-start justify-between mb-1">
                        <h4 className="font-medium text-sm truncate flex-1">
                          {session.title}
                        </h4>
                        <Badge variant="outline" className="text-xs ml-2">
                          {session.messageCount}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 line-clamp-2 mb-2">
                        {session.lastMessage}
                      </p>
                      <div className="flex items-center space-x-1 text-xs text-gray-400">
                        <Clock className="h-3 w-3" />
                        <span>{formatTimeAgo(session.timestamp)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {activeTab === 'strategies' && (
            <ScrollArea className="h-80">
              <div className="space-y-2">
                {strategies.map((strategy) => (
                  <div
                    key={strategy.id}
                    className="p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-sm truncate flex-1">
                        {strategy.name}
                      </h4>
                      {getStatusBadge(strategy.status)}
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">
                        {formatTimeAgo(strategy.createdAt)}
                      </span>
                      <span className={`font-medium ${getPerformanceColor(strategy.performance)}`}>
                        {strategy.performance > 0 ? '+' : ''}{strategy.performance}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* AI状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Bot className="h-4 w-4" />
            <span>AI状态</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">服务状态</span>
              <Badge variant="default">在线</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">响应时间</span>
              <span className="text-sm text-gray-600">1.2s</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">今日请求</span>
              <span className="text-sm text-gray-600">127</span>
            </div>
            <Button variant="outline" size="sm" className="w-full">
              <Settings className="h-3 w-3 mr-1" />
              AI设置
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}