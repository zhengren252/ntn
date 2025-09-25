'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Play,
  Square,
  RotateCcw,
  Settings,
  Activity,
  Cpu,
  MemoryStick,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { useModuleStatus, useRestartModule } from '@/hooks/useApi'
import { toast } from 'sonner'

interface Module {
  id: string
  name: string
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping'
  cpuUsage: number
  memoryUsage: number
  uptime: number
  lastRestart: Date
  description: string
  version: string
  dependencies: string[]
}

interface ModuleStatusProps {
  modules?: Module[]
}

export const ModuleStatus = ({ modules: propModules }: ModuleStatusProps) => {
  const { data: moduleData, isLoading, refetch } = useModuleStatus()
  const restartModuleMutation = useRestartModule()
  const [selectedModule, setSelectedModule] = useState<string | null>(null)

  const modules = propModules || moduleData?.data || []

  const getStatusIcon = (status: Module['status']) => {
    switch (status) {
      case 'running':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'stopped':
        return <Square className="h-4 w-4 text-gray-600" />
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'starting':
        return <Play className="h-4 w-4 text-blue-600" />
      case 'stopping':
        return <Square className="h-4 w-4 text-yellow-600" />
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-600" />
    }
  }

  const getStatusBadge = (status: Module['status']) => {
    switch (status) {
      case 'running':
        return <Badge variant="default">运行中</Badge>
      case 'stopped':
        return <Badge variant="secondary">已停止</Badge>
      case 'error':
        return <Badge variant="destructive">错误</Badge>
      case 'starting':
        return <Badge variant="outline">启动中</Badge>
      case 'stopping':
        return <Badge variant="outline">停止中</Badge>
      default:
        return <Badge variant="outline">未知</Badge>
    }
  }

  const getStatusColor = (status: Module['status']) => {
    switch (status) {
      case 'running':
        return 'border-green-200 bg-green-50'
      case 'stopped':
        return 'border-gray-200 bg-gray-50'
      case 'error':
        return 'border-red-200 bg-red-50'
      case 'starting':
      case 'stopping':
        return 'border-blue-200 bg-blue-50'
      default:
        return 'border-gray-200'
    }
  }

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) return `${days}天${hours}小时`
    if (hours > 0) return `${hours}小时${minutes}分钟`
    return `${minutes}分钟`
  }

  const formatMemoryUsage = (bytes: number) => {
    const mb = bytes / (1024 * 1024)
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(1)}GB`
    }
    return `${mb.toFixed(0)}MB`
  }

  const handleRestartModule = async (moduleId: string, moduleName: string) => {
    try {
      await restartModuleMutation.mutateAsync(moduleId)
      toast.success(`模块 "${moduleName}" 重启成功`)
      refetch()
    } catch (error) {
      toast.error(`模块 "${moduleName}" 重启失败`)
    }
  }

  const handleStartModule = (moduleId: string, moduleName: string) => {
    // 模拟启动模块
    toast.success(`模块 "${moduleName}" 启动中...`)
  }

  const handleStopModule = (moduleId: string, moduleName: string) => {
    // 模拟停止模块
    toast.success(`模块 "${moduleName}" 停止中...`)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>模块运行状态</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-4 h-4 bg-gray-200 rounded-full animate-pulse" />
                  <div className="space-y-2">
                    <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
                    <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
                  <div className="h-8 w-16 bg-gray-200 rounded animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>模块运行状态</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            刷新
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96">
          <div className="space-y-3">
            {modules.map((module) => (
              <div
                key={module.id}
                className={`p-4 border rounded-lg transition-all hover:shadow-sm ${
                  selectedModule === module.id ? 'ring-2 ring-blue-500' : ''
                } ${getStatusColor(module.status)}`}
                onClick={() => setSelectedModule(selectedModule === module.id ? null : module.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(module.status)}
                    <div>
                      <h4 className="font-medium text-sm">{module.name}</h4>
                      <p className="text-xs text-gray-500">{module.description}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(module.status)}
                    <div className="flex items-center space-x-1">
                      {module.status === 'running' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleStopModule(module.id, module.name)
                          }}
                        >
                          <Square className="h-3 w-3" />
                        </Button>
                      )}
                      {module.status === 'stopped' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleStartModule(module.id, module.name)
                          }}
                        >
                          <Play className="h-3 w-3" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRestartModule(module.id, module.name)
                        }}
                        disabled={restartModuleMutation.isPending}
                      >
                        <RotateCcw className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation()
                          // 打开模块设置
                        }}
                      >
                        <Settings className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* 展开的详细信息 */}
                {selectedModule === module.id && (
                  <div className="mt-4 pt-4 border-t space-y-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div className="flex items-center space-x-2">
                        <Cpu className="h-4 w-4 text-gray-500" />
                        <span className="text-gray-600">CPU:</span>
                        <span className="font-medium">{module.cpuUsage}%</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <MemoryStick className="h-4 w-4 text-gray-500" />
                        <span className="text-gray-600">内存:</span>
                        <span className="font-medium">{formatMemoryUsage(module.memoryUsage)}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Clock className="h-4 w-4 text-gray-500" />
                        <span className="text-gray-600">运行时间:</span>
                        <span className="font-medium">{formatUptime(module.uptime)}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-600">版本:</span>
                        <span className="font-medium">{module.version}</span>
                      </div>
                    </div>
                    
                    <div>
                      <span className="text-sm text-gray-600">依赖模块:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {module.dependencies.map((dep, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {dep}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    
                    <div className="text-xs text-gray-500">
                      最后重启: {module.lastRestart.toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}