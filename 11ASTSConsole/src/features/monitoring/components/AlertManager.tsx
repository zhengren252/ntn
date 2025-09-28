'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Clock,
  Filter,
  Search,
  Bell,
  BellOff,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react'
import { toast } from 'sonner'

interface Alert {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  title: string
  message: string
  source: string
  timestamp: Date
  isRead: boolean
  isResolved: boolean
  category: 'system' | 'module' | 'network' | 'security' | 'performance'
}

interface AlertManagerProps {
  alerts?: Alert[]
}

export const AlertManager = ({ alerts: propAlerts }: AlertManagerProps) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLevel, setSelectedLevel] = useState<string>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [showResolved, setShowResolved] = useState(false)
  const [selectedAlerts, setSelectedAlerts] = useState<string[]>([])

  // 模拟告警数据
  const defaultAlerts: Alert[] = [
    {
      id: '1',
      level: 'critical',
      title: '数据库连接失败',
      message: '主数据库连接超时，系统正在尝试连接备用数据库',
      source: '数据存储模块',
      timestamp: new Date(Date.now() - 1000 * 60 * 5), // 5分钟前
      isRead: false,
      isResolved: false,
      category: 'system'
    },
    {
      id: '2',
      level: 'warning',
      title: 'API网关CPU使用率过高',
      message: 'API网关模块CPU使用率达到85%，建议检查负载情况',
      source: 'API网关模块',
      timestamp: new Date(Date.now() - 1000 * 60 * 15), // 15分钟前
      isRead: true,
      isResolved: false,
      category: 'performance'
    },
    {
      id: '3',
      level: 'error',
      title: '外部API调用失败',
      message: '币安API连接超时，影响实时数据获取',
      source: '数据采集模块',
      timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30分钟前
      isRead: true,
      isResolved: true,
      category: 'network'
    },
    {
      id: '4',
      level: 'info',
      title: '模块重启完成',
      message: '策略执行模块重启成功，所有功能恢复正常',
      source: '策略执行模块',
      timestamp: new Date(Date.now() - 1000 * 60 * 60), // 1小时前
      isRead: true,
      isResolved: true,
      category: 'module'
    },
    {
      id: '5',
      level: 'warning',
      title: '磁盘空间不足',
      message: '系统磁盘使用率达到85%，建议清理日志文件',
      source: '系统监控',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2小时前
      isRead: false,
      isResolved: false,
      category: 'system'
    }
  ]

  const alerts = propAlerts || defaultAlerts

  const getAlertIcon = (level: Alert['level']) => {
    switch (level) {
      case 'critical':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />
      default:
        return <Info className="h-4 w-4 text-gray-500" />
    }
  }

  const getAlertBadge = (level: Alert['level']) => {
    switch (level) {
      case 'critical':
        return <Badge variant="destructive">严重</Badge>
      case 'error':
        return <Badge variant="destructive">错误</Badge>
      case 'warning':
        return <Badge variant="secondary">警告</Badge>
      case 'info':
        return <Badge variant="default">信息</Badge>
      default:
        return <Badge variant="outline">未知</Badge>
    }
  }

  const getAlertColor = (level: Alert['level'], isRead: boolean) => {
    const baseColor = (() => {
      switch (level) {
        case 'critical':
          return 'border-red-200 bg-red-50'
        case 'error':
          return 'border-red-200 bg-red-50'
        case 'warning':
          return 'border-yellow-200 bg-yellow-50'
        case 'info':
          return 'border-blue-200 bg-blue-50'
        default:
          return 'border-gray-200'
      }
    })()
    
    return isRead ? `${baseColor} opacity-60` : baseColor
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

  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch = alert.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         alert.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         alert.source.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesLevel = selectedLevel === 'all' || alert.level === selectedLevel
    const matchesCategory = selectedCategory === 'all' || alert.category === selectedCategory
    const matchesResolved = showResolved || !alert.isResolved
    
    return matchesSearch && matchesLevel && matchesCategory && matchesResolved
  })

  const unreadCount = alerts.filter(alert => !alert.isRead && !alert.isResolved).length
  const criticalCount = alerts.filter(alert => alert.level === 'critical' && !alert.isResolved).length

  const handleMarkAsRead = (alertId: string) => {
    toast.success('告警已标记为已读')
  }

  const handleResolve = (alertId: string) => {
    toast.success('告警已解决')
  }

  const handleDelete = (alertId: string) => {
    toast.success('告警已删除')
  }

  const handleBatchAction = (action: 'read' | 'resolve' | 'delete') => {
    if (selectedAlerts.length === 0) {
      toast.error('请先选择要操作的告警')
      return
    }
    
    const actionText = {
      read: '标记为已读',
      resolve: '解决',
      delete: '删除'
    }[action]
    
    toast.success(`已${actionText} ${selectedAlerts.length} 条告警`)
    setSelectedAlerts([])
  }

  const toggleSelectAlert = (alertId: string) => {
    setSelectedAlerts(prev => 
      prev.includes(alertId) 
        ? prev.filter(id => id !== alertId)
        : [...prev, alertId]
    )
  }

  const selectAllVisible = () => {
    const visibleIds = filteredAlerts.map(alert => alert.id)
    setSelectedAlerts(visibleIds)
  }

  const clearSelection = () => {
    setSelectedAlerts([])
  }

  return (
    <Card data-testid="alert-manager-root">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Bell className="h-5 w-5" />
            <span>系统告警</span>
            {unreadCount > 0 && (
              <Badge variant="destructive" data-testid="badge-unread">{unreadCount}</Badge>
            )}
            {criticalCount > 0 && (
              <Badge variant="destructive" data-testid="badge-critical">严重 {criticalCount}</Badge>
            )}
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowResolved(!showResolved)}
              data-testid="btn-toggle-resolved"
            >
              {showResolved ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showResolved ? '隐藏已解决' : '显示已解决'}
            </Button>
          </div>
        </div>
        
        {/* 搜索和筛选 */}
        <div className="space-y-3" data-testid="alert-filters">
          <div className="flex items-center space-x-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="搜索告警..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
                data-testid="input-search-alert"
              />
            </div>
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="select-level"
            >
              <option value="all">所有级别</option>
              <option value="critical">严重</option>
              <option value="error">错误</option>
              <option value="warning">警告</option>
              <option value="info">信息</option>
            </select>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="select-category"
            >
              <option value="all">所有类别</option>
              <option value="system">系统</option>
              <option value="module">模块</option>
              <option value="network">网络</option>
              <option value="security">安全</option>
              <option value="performance">性能</option>
            </select>
          </div>
          
          {/* 批量操作 */}
          {selectedAlerts.length > 0 && (
            <div className="flex items-center justify-between p-2 bg-blue-50 rounded-lg" data-testid="batch-toolbar">
              <span className="text-sm text-blue-700">
                已选择 {selectedAlerts.length} 条告警
              </span>
              <div className="flex items-center space-x-2">
                <Button size="sm" variant="outline" onClick={() => handleBatchAction('read')} data-testid="btn-batch-read">
                  <Eye className="h-3 w-3 mr-1" />
                  标记已读
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleBatchAction('resolve')} data-testid="btn-batch-resolve">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  解决
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleBatchAction('delete')} data-testid="btn-batch-delete">
                  <Trash2 className="h-3 w-3 mr-1" />
                  删除
                </Button>
                <Button size="sm" variant="ghost" onClick={clearSelection} data-testid="btn-clear-selection">
                  取消选择
                </Button>
              </div>
            </div>
          )}
          
          <div className="flex items-center space-x-2">
            <Button size="sm" variant="outline" onClick={selectAllVisible} data-testid="btn-select-all">
              全选当前页
            </Button>
            <span className="text-sm text-gray-500" data-testid="text-count">
              显示 {filteredAlerts.length} / {alerts.length} 条告警
            </span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <ScrollArea className="h-96" data-testid="alert-list">
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 border rounded-lg transition-all hover:shadow-sm ${
                  selectedAlerts.includes(alert.id) ? 'ring-2 ring-blue-500' : ''
                } ${getAlertColor(alert.level, alert.isRead)}`}
                data-testid={`alert-row-${alert.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <input
                      type="checkbox"
                      checked={selectedAlerts.includes(alert.id)}
                      onChange={() => toggleSelectAlert(alert.id)}
                      className="mt-1"
                      data-testid={`checkbox-${alert.id}`}
                    />
                    {getAlertIcon(alert.level)}
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className={`font-medium text-sm ${
                          alert.isRead ? 'text-gray-600' : 'text-gray-900'
                        }`} data-testid={`alert-title-${alert.id}`}>
                          {alert.title}
                        </h4>
                        {!alert.isRead && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full" data-testid={`dot-unread-${alert.id}`} />
                        )}
                        {alert.isResolved && (
                          <Badge variant="outline" data-testid={`badge-resolved-${alert.id}`}>已解决</Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-2" data-testid={`alert-message-${alert.id}`}>{alert.message}</p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span className="flex items-center space-x-1">
                          <Clock className="h-3 w-3" />
                          <span data-testid={`alert-time-${alert.id}`}>{formatTimeAgo(alert.timestamp)}</span>
                        </span>
                        <span data-testid={`alert-source-${alert.id}`}>来源: {alert.source}</span>
                        <span data-testid={`alert-category-${alert.id}`}>类别: {alert.category}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    {getAlertBadge(alert.level)}
                    <div className="flex items-center space-x-1">
                      {!alert.isRead && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleMarkAsRead(alert.id)}
                          data-testid={`btn-mark-read-${alert.id}`}
                        >
                          <Eye className="h-3 w-3" />
                        </Button>
                      )}
                      {!alert.isResolved && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleResolve(alert.id)}
                          data-testid={`btn-resolve-${alert.id}`}
                        >
                          <CheckCircle className="h-3 w-3" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(alert.id)}
                        data-testid={`btn-delete-${alert.id}`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {filteredAlerts.length === 0 && (
              <div className="text-center py-8 text-gray-500" data-testid="empty-alerts">
                <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>没有找到匹配的告警</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}