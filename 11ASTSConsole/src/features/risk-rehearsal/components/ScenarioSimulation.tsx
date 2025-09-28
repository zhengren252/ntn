'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  Play, 
  Pause, 
  Square, 
  Settings, 
  AlertTriangle, 
  TrendingDown, 
  Zap,
  BarChart3,
  Clock,
  Target
} from 'lucide-react'
import { useRiskScenarios, useCreateScenario, useRunScenario } from '@/hooks/useApi'

// 场景类型定义
interface RiskScenario {
  id: string
  name: string
  type: 'stress_test' | 'scenario_analysis' | 'market_crash' | 'liquidity_crisis' | 'system_failure'
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  duration: number // 分钟
  parameters: Record<string, unknown>
  status: 'draft' | 'ready' | 'running' | 'completed' | 'failed'
  createdAt: string
  lastRun?: string
  results?: {
    score: number
    issues: number
    recommendations: string[]
  }
}

// 模拟场景数据
const mockScenarios: RiskScenario[] = [
  {
    id: '1',
    name: '市场崩盘模拟',
    type: 'market_crash',
    description: '模拟股市大幅下跌30%的极端情况',
    severity: 'critical',
    duration: 60,
    parameters: {
      dropPercentage: 30,
      volatility: 'extreme',
      sectors: ['tech', 'finance']
    },
    status: 'ready',
    createdAt: '2024-01-15T10:00:00Z',
    lastRun: '2024-01-14T15:30:00Z',
    results: {
      score: 75,
      issues: 3,
      recommendations: ['增加对冲头寸', '调整止损策略', '优化资金配置']
    }
  },
  {
    id: '2',
    name: '流动性危机',
    type: 'liquidity_crisis',
    description: '模拟市场流动性急剧下降的情况',
    severity: 'high',
    duration: 45,
    parameters: {
      liquidityDrop: 60,
      spreadIncrease: 200,
      affectedMarkets: ['bonds', 'forex']
    },
    status: 'running',
    createdAt: '2024-01-14T14:20:00Z'
  },
  {
    id: '3',
    name: '系统故障演练',
    type: 'system_failure',
    description: '模拟交易系统部分功能失效',
    severity: 'medium',
    duration: 30,
    parameters: {
      failureType: 'partial',
      affectedModules: ['order_execution', 'risk_monitor'],
      recoveryTime: 15
    },
    status: 'completed',
    createdAt: '2024-01-13T09:15:00Z',
    lastRun: '2024-01-13T16:45:00Z',
    results: {
      score: 88,
      issues: 1,
      recommendations: ['优化故障切换机制']
    }
  }
]

// 场景类型配置
const scenarioTypes = {
  market_crash: { label: '市场崩盘', icon: TrendingDown, color: 'destructive' },
  liquidity_crisis: { label: '流动性危机', icon: AlertTriangle, color: 'warning' },
  system_failure: { label: '系统故障', icon: Zap, color: 'secondary' },
  stress_test: { label: '压力测试', icon: BarChart3, color: 'default' },
  scenario_analysis: { label: '场景分析', icon: Settings, color: 'outline' }
}

// 严重程度配置
const severityConfig = {
  low: { label: '低', color: 'bg-green-100 text-green-800' },
  medium: { label: '中', color: 'bg-yellow-100 text-yellow-800' },
  high: { label: '高', color: 'bg-orange-100 text-orange-800' },
  critical: { label: '严重', color: 'bg-red-100 text-red-800' }
}

// 状态配置
const statusConfig = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-800' },
  ready: { label: '就绪', color: 'bg-blue-100 text-blue-800' },
  running: { label: '运行中', color: 'bg-green-100 text-green-800' },
  completed: { label: '已完成', color: 'bg-purple-100 text-purple-800' },
  failed: { label: '失败', color: 'bg-red-100 text-red-800' }
}

export default function ScenarioSimulation() {
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [runningScenarios, setRunningScenarios] = useState<Set<string>>(new Set(['2']))
  
  // API hooks
  const { data: scenariosResponse, isLoading } = useRiskScenarios()
  const createScenario = useCreateScenario()
  const runScenario = useRunScenario()
  
  // 使用模拟数据
  const scenarioData = scenariosResponse?.data || mockScenarios
  
  // 运行场景
  const handleRunScenario = async (scenarioId: string) => {
    try {
      setRunningScenarios(prev => new Set([...prev, scenarioId]))
      await runScenario.mutateAsync({ scenarioId, params: {} })
      
      // 模拟运行过程
      setTimeout(() => {
        setRunningScenarios(prev => {
          const newSet = new Set(prev)
          newSet.delete(scenarioId)
          return newSet
        })
      }, 5000)
    } catch (error) {
      setRunningScenarios(prev => {
        const newSet = new Set(prev)
        newSet.delete(scenarioId)
        return newSet
      })
    }
  }
  
  // 停止场景
  const handleStopScenario = (scenarioId: string) => {
    setRunningScenarios(prev => {
      const newSet = new Set(prev)
      newSet.delete(scenarioId)
      return newSet
    })
  }
  
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* 头部操作区 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">场景模拟</h3>
          <p className="text-sm text-muted-foreground">
            创建和运行风险场景，测试系统应对能力
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Settings className="mr-2 h-4 w-4" />
              创建场景
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>创建风险场景</DialogTitle>
            </DialogHeader>
            <CreateScenarioForm onClose={() => setIsCreateDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>
      
      {/* 场景列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" data-testid="scenario-list">
        {scenarioData.map((scenario) => {
          const typeConfig = scenarioTypes[(scenario as RiskScenario).type]
          const TypeIcon = typeConfig.icon
          const isRunning = runningScenarios.has(scenario.id)
          
          return (
            <Card key={scenario.id} className="relative">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <TypeIcon className="h-5 w-5 text-muted-foreground" />
                    <CardTitle className="text-base">{scenario.name}</CardTitle>
                  </div>
                  <div className="flex flex-col space-y-1">
                    <Badge 
                      variant="secondary" 
                      className={severityConfig[(scenario as RiskScenario).severity].color}
                    >
                      {severityConfig[(scenario as RiskScenario).severity].label}
                    </Badge>
                    <Badge 
                      variant="outline" 
                      className={statusConfig[(scenario as RiskScenario).status].color}
                    >
                      {statusConfig[(scenario as RiskScenario).status].label}
                    </Badge>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {(scenario as RiskScenario).description}
                </p>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* 场景信息 */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span>{(scenario as RiskScenario).duration}分钟</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    <span>{typeConfig.label}</span>
                  </div>
                </div>
                
                {/* 运行进度 */}
                {isRunning && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>运行进度</span>
                      <span>65%</span>
                    </div>
                    <Progress value={65} className="h-2" />
                  </div>
                )}
                
                {/* 上次结果 */}
                {(scenario as RiskScenario).results && !isRunning && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>评分</span>
                      <span className="font-medium">{(scenario as RiskScenario).results?.score}/100</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span>发现问题</span>
                      <span className="text-orange-600">{(scenario as RiskScenario).results?.issues}个</span>
                    </div>
                  </div>
                )}
                
                {/* 操作按钮 */}
                <div className="flex space-x-2">
                  {isRunning ? (
                    <>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleStopScenario(scenario.id)}
                      >
                        <Square className="mr-2 h-4 w-4" />
                        停止
                      </Button>
                      <Button size="sm" variant="outline" disabled>
                        <Pause className="mr-2 h-4 w-4" />
                        暂停
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button 
                        size="sm"
                        onClick={() => handleRunScenario(scenario.id)}
                        disabled={scenario.status === 'draft'}
                        data-testid="start-rehearsal-button"
                      >
                        <Play className="mr-2 h-4 w-4" />
                        运行
                      </Button>
                      <Button size="sm" variant="outline">
                        <Settings className="mr-2 h-4 w-4" />
                        配置
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

// 创建场景表单组件
function CreateScenarioForm({ onClose }: { onClose: () => void }) {
  const [formData, setFormData] = useState<{
    name: string;
    type: 'stress_test' | 'scenario_analysis' | 'market_crash' | 'liquidity_crisis' | 'system_failure';
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    duration: number;
    parameters: Record<string, unknown>;
  }>({
    name: '',
    type: 'market_crash',
    description: '',
    severity: 'medium',
    duration: 30,
    parameters: {}
  })
  
  const createScenario = useCreateScenario()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createScenario.mutateAsync(formData)
      onClose()
    } catch (error) {
      console.error('创建场景失败:', error)
    }
  }
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">场景名称</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            placeholder="输入场景名称"
            required
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="type">场景类型</Label>
          <Select 
            value={formData.type} 
            onValueChange={(value) => setFormData(prev => ({ ...prev, type: value as keyof typeof scenarioTypes }))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(scenarioTypes).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  {config.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="severity">严重程度</Label>
          <Select 
            value={formData.severity} 
            onValueChange={(value) => setFormData(prev => ({ ...prev, severity: value as keyof typeof severityConfig }))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(severityConfig).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  {config.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="duration">持续时间（分钟）</Label>
          <Input
            id="duration"
            type="number"
            value={formData.duration}
            onChange={(e) => setFormData(prev => ({ ...prev, duration: parseInt(e.target.value) }))}
            min={1}
            max={180}
            required
          />
        </div>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="description">场景描述</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="描述这个风险场景的具体情况和测试目标"
          rows={3}
          required
        />
      </div>
      
      <div className="flex justify-end space-x-2">
        <Button type="button" variant="outline" onClick={onClose}>
          取消
        </Button>
        <Button type="submit" disabled={createScenario.isPending}>
          {createScenario.isPending ? '创建中...' : '创建场景'}
        </Button>
      </div>
    </form>
  )
}