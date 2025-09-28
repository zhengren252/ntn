'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Settings,
  Save,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react'
import { useUpdateModuleConfig } from '@/hooks/useApi'
import { ModuleConfig } from '@/lib/types'

interface ModuleConfigurationProps {
  moduleId: string | null
  isOpen: boolean
  onClose: () => void
}

interface ExtendedModuleConfig extends ModuleConfig {
  name?: string
  logLevel?: string
  description?: string
  autoStart?: boolean
  maxMemory?: number
  maxCpu?: number
  threadCount?: number
  timeout?: number
  enableCache?: boolean
  apiKey?: string
  encryptionLevel?: string
  enableSsl?: boolean
  enableAuth?: boolean
  customConfig?: Record<string, unknown>
  restartPolicy?: string
  healthCheckInterval?: number
}

export default function ModuleConfiguration({ moduleId, isOpen, onClose }: ModuleConfigurationProps) {
  const [config, setConfig] = useState<ExtendedModuleConfig>({
    enabled: false,
    parameters: {}
  })
  const [hasChanges, setHasChanges] = useState(false)
  
  const updateConfig = useUpdateModuleConfig()

  if (!moduleId) return null

  // 模拟模块数据，实际应该从API获取
  const module = {
    id: moduleId,
    name: moduleId,
    version: 'v1.0.0',
    status: 'running',
    description: '模块描述',
    config: {},
    uptime: '2小时30分钟',
    cpuUsage: '15',
    memoryUsage: '256'
  }

  const handleConfigChange = (key: string, value: unknown) => {
    setConfig(prev => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  const handleSave = () => {
    // 只传递ModuleConfig需要的属性
    const moduleConfig: ModuleConfig = {
      enabled: config.autoStart || false,
      parameters: {
        name: config.name,
        logLevel: config.logLevel,
        description: config.description,
        maxMemory: config.maxMemory,
        maxCpu: config.maxCpu,
        threadCount: config.threadCount,
        timeout: config.timeout,
        enableCache: config.enableCache,
        apiKey: config.apiKey,
        encryptionLevel: config.encryptionLevel,
        enableSsl: config.enableSsl,
        enableAuth: config.enableAuth,
        restartPolicy: config.restartPolicy,
        healthCheckInterval: config.healthCheckInterval,
        ...config.customConfig
      },
      dependencies: config.dependencies
    }
    updateConfig.mutate({ moduleId: module.id, config: moduleConfig })
    setHasChanges(false)
  }

  const handleReset = () => {
    setConfig({
      enabled: false,
      parameters: {},
      ...module.config
    } as ExtendedModuleConfig)
    setHasChanges(false)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'stopped':
        return <AlertTriangle className="h-4 w-4 text-red-600" />
      default:
        return <Info className="h-4 w-4 text-blue-600" />
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto" data-testid="module-config-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <span>{module.name} - 配置管理</span>
            <Badge variant="outline">{module.version}</Badge>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* 模块状态 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">模块状态</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">当前状态</Label>
                  <div className="flex items-center space-x-2 mt-1">
                    {getStatusIcon(module.status)}
                    <Badge variant={module.status === 'running' ? 'default' : 'destructive'}>
                      {module.status === 'running' ? '运行中' : '已停止'}
                    </Badge>
                  </div>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">运行时间</Label>
                  <p className="text-sm mt-1">{module.uptime || 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">CPU使用率</Label>
                  <p className="text-sm mt-1">{module.cpuUsage || '0'}%</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-muted-foreground">内存使用</Label>
                  <p className="text-sm mt-1">{module.memoryUsage || '0'} MB</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 配置选项 */}
          <Tabs defaultValue="general" className="space-y-4">
            <TabsList>
              <TabsTrigger value="general" data-testid="tab-config-general">常规设置</TabsTrigger>
              <TabsTrigger value="performance" data-testid="tab-config-performance">性能配置</TabsTrigger>
              <TabsTrigger value="security" data-testid="tab-config-security">安全设置</TabsTrigger>
              <TabsTrigger value="advanced" data-testid="tab-config-advanced">高级选项</TabsTrigger>
            </TabsList>
            
            <TabsContent value="general" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>基本配置</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">模块名称</Label>
                      <Input
                        id="name"
                        value={config.name || module.name}
                        onChange={(e) => handleConfigChange('name', e.target.value)}
                        data-testid="input-module-name"
                      />
                    </div>
                    <div>
                      <Label htmlFor="logLevel">日志级别</Label>
                      <Select
                        value={config.logLevel || 'info'}
                        onValueChange={(value) => handleConfigChange('logLevel', value)}
                        data-testid="select-log-level"
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="debug">Debug</SelectItem>
                          <SelectItem value="info">Info</SelectItem>
                          <SelectItem value="warn">Warning</SelectItem>
                          <SelectItem value="error">Error</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div>
                    <Label htmlFor="description">描述</Label>
                    <Textarea
                      id="description"
                      value={config.description || module.description}
                      onChange={(e) => handleConfigChange('description', e.target.value)}
                      rows={3}
                      data-testid="textarea-description"
                    />
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="autoStart"
                      checked={config.autoStart || false}
                      onCheckedChange={(checked) => handleConfigChange('autoStart', checked)}
                      data-testid="switch-auto-start"
                    />
                    <Label htmlFor="autoStart">自动启动</Label>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="performance" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>性能配置</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="maxMemory">最大内存 (MB)</Label>
                      <Input
                        id="maxMemory"
                        type="number"
                        value={config.maxMemory || 512}
                        onChange={(e) => handleConfigChange('maxMemory', parseInt(e.target.value))}
                        data-testid="input-max-memory"
                      />
                    </div>
                    <div>
                      <Label htmlFor="maxCpu">最大CPU使用率 (%)</Label>
                      <Input
                        id="maxCpu"
                        type="number"
                        value={config.maxCpu || 80}
                        onChange={(e) => handleConfigChange('maxCpu', parseInt(e.target.value))}
                        data-testid="input-max-cpu"
                      />
                    </div>
                    <div>
                      <Label htmlFor="threadCount">线程数</Label>
                      <Input
                        id="threadCount"
                        type="number"
                        value={config.threadCount || 4}
                        onChange={(e) => handleConfigChange('threadCount', parseInt(e.target.value))}
                        data-testid="input-thread-count"
                      />
                    </div>
                    <div>
                      <Label htmlFor="timeout">超时时间 (秒)</Label>
                      <Input
                        id="timeout"
                        type="number"
                        value={config.timeout || 30}
                        onChange={(e) => handleConfigChange('timeout', parseInt(e.target.value))}
                        data-testid="input-timeout"
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="enableCache"
                      checked={config.enableCache || false}
                      onCheckedChange={(checked) => handleConfigChange('enableCache', checked)}
                      data-testid="switch-enable-cache"
                    />
                    <Label htmlFor="enableCache">启用缓存</Label>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="security" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>安全设置</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="apiKey">API密钥</Label>
                      <Input
                        id="apiKey"
                        type="password"
                        value={config.apiKey || ''}
                        onChange={(e) => handleConfigChange('apiKey', e.target.value)}
                        placeholder="输入API密钥"
                        data-testid="input-api-key"
                      />
                    </div>
                    <div>
                      <Label htmlFor="encryptionLevel">加密级别</Label>
                      <Select
                        value={config.encryptionLevel || 'standard'}
                        onValueChange={(value) => handleConfigChange('encryptionLevel', value)}
                        data-testid="select-encryption-level"
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="basic">基础</SelectItem>
                          <SelectItem value="standard">标准</SelectItem>
                          <SelectItem value="high">高级</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="enableSsl"
                        checked={config.enableSsl || false}
                        onCheckedChange={(checked) => handleConfigChange('enableSsl', checked)}
                        data-testid="switch-enable-ssl"
                      />
                      <Label htmlFor="enableSsl">启用SSL</Label>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="enableAuth"
                        checked={config.enableAuth || true}
                        onCheckedChange={(checked) => handleConfigChange('enableAuth', checked)}
                        data-testid="switch-enable-auth"
                      />
                      <Label htmlFor="enableAuth">启用身份验证</Label>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="advanced" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>高级选项</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="customConfig">自定义配置 (JSON)</Label>
                    <Textarea
                      id="customConfig"
                      value={JSON.stringify(config.customConfig || {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value)
                          handleConfigChange('customConfig', parsed)
                        } catch (error) {
                          // 忽略JSON解析错误
                        }
                      }}
                      rows={8}
                      className="font-mono text-sm"
                      data-testid="textarea-custom-config"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="restartPolicy">重启策略</Label>
                      <Select
                        value={config.restartPolicy || 'always'}
                        onValueChange={(value) => handleConfigChange('restartPolicy', value)}
                        data-testid="select-restart-policy"
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="never">从不</SelectItem>
                          <SelectItem value="on-failure">失败时</SelectItem>
                          <SelectItem value="always">总是</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="healthCheckInterval">健康检查间隔 (秒)</Label>
                      <Input
                        id="healthCheckInterval"
                        type="number"
                        value={config.healthCheckInterval || 60}
                        onChange={(e) => handleConfigChange('healthCheckInterval', parseInt(e.target.value))}
                        data-testid="input-health-check-interval"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
        
        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center space-x-2">
              {hasChanges && (
                <Badge variant="secondary" data-testid="badge-unsaved">有未保存的更改</Badge>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="outline" onClick={handleReset} disabled={!hasChanges} data-testid="btn-reset">
                <RotateCcw className="mr-2 h-4 w-4" />
                重置
              </Button>
              <Button variant="outline" onClick={onClose} data-testid="btn-cancel">
                取消
              </Button>
              <Button onClick={handleSave} disabled={!hasChanges} data-testid="btn-save">
                <Save className="mr-2 h-4 w-4" />
                保存配置
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}