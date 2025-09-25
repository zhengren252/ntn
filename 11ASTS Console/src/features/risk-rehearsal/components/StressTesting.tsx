'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Activity,
  Cpu,
  Database,
  Network,
  Zap,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  Settings,
  Play,
  Square,
} from 'lucide-react';
import {
  useStressTests,
  useCreateStressTest,
  useRunStressTest,
} from '@/hooks/useApi';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

// 压力测试类型定义
interface StressTest {
  id: string;
  name: string;
  type: 'performance' | 'load' | 'volume' | 'endurance' | 'spike';
  description: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  config: {
    duration: number; // 分钟
    intensity: number; // 1-100
    targets: string[];
    metrics: string[];
    thresholds: Record<string, number>;
  };
  results?: {
    startTime: string;
    endTime: string;
    passed: boolean;
    score: number;
    metrics: Record<string, number>;
    issues: string[];
  };
  createdAt: string;
  lastRun?: string;
}

// 模拟压力测试数据
const mockStressTests: StressTest[] = [
  {
    id: '1',
    name: '高频交易压力测试',
    type: 'performance',
    description: '测试系统在高频交易场景下的性能表现',
    status: 'completed',
    config: {
      duration: 30,
      intensity: 85,
      targets: ['order_engine', 'risk_monitor', 'market_data'],
      metrics: ['latency', 'throughput', 'error_rate', 'cpu_usage'],
      thresholds: {
        latency: 10, // ms
        throughput: 1000, // orders/sec
        error_rate: 0.1, // %
        cpu_usage: 80, // %
      },
    },
    results: {
      startTime: '2024-01-15T10:00:00Z',
      endTime: '2024-01-15T10:30:00Z',
      passed: true,
      score: 92,
      metrics: {
        avg_latency: 8.5,
        peak_throughput: 1200,
        error_rate: 0.05,
        max_cpu_usage: 75,
      },
      issues: [],
    },
    createdAt: '2024-01-14T15:30:00Z',
    lastRun: '2024-01-15T10:00:00Z',
  },
  {
    id: '2',
    name: '数据库负载测试',
    type: 'load',
    description: '测试数据库在高并发查询下的稳定性',
    status: 'running',
    config: {
      duration: 60,
      intensity: 70,
      targets: ['database', 'cache'],
      metrics: ['query_time', 'connection_pool', 'memory_usage'],
      thresholds: {
        query_time: 100,
        connection_pool: 90,
        memory_usage: 85,
      },
    },
    createdAt: '2024-01-15T09:00:00Z',
  },
  {
    id: '3',
    name: '网络带宽压力测试',
    type: 'volume',
    description: '测试网络在大数据量传输时的表现',
    status: 'failed',
    config: {
      duration: 45,
      intensity: 95,
      targets: ['network', 'api_gateway'],
      metrics: ['bandwidth', 'packet_loss', 'latency'],
      thresholds: {
        bandwidth: 1000, // Mbps
        packet_loss: 0.01,
        latency: 50,
      },
    },
    results: {
      startTime: '2024-01-14T14:00:00Z',
      endTime: '2024-01-14T14:20:00Z',
      passed: false,
      score: 45,
      metrics: {
        avg_bandwidth: 800,
        packet_loss: 0.05,
        avg_latency: 75,
      },
      issues: ['网络延迟超过阈值', '丢包率过高', '带宽利用率不足'],
    },
    createdAt: '2024-01-14T13:30:00Z',
    lastRun: '2024-01-14T14:00:00Z',
  },
];

// 测试类型配置
const testTypes = {
  performance: {
    label: '性能测试',
    icon: Zap,
    color: 'bg-blue-100 text-blue-800',
  },
  load: {
    label: '负载测试',
    icon: Activity,
    color: 'bg-green-100 text-green-800',
  },
  volume: {
    label: '容量测试',
    icon: Database,
    color: 'bg-purple-100 text-purple-800',
  },
  endurance: {
    label: '耐久测试',
    icon: Clock,
    color: 'bg-orange-100 text-orange-800',
  },
  spike: {
    label: '峰值测试',
    icon: TrendingUp,
    color: 'bg-red-100 text-red-800',
  },
};

// 状态配置
const statusConfig = {
  idle: { label: '待运行', icon: Clock, color: 'bg-gray-100 text-gray-800' },
  running: {
    label: '运行中',
    icon: Activity,
    color: 'bg-blue-100 text-blue-800',
  },
  completed: {
    label: '已完成',
    icon: CheckCircle,
    color: 'bg-green-100 text-green-800',
  },
  failed: { label: '失败', icon: XCircle, color: 'bg-red-100 text-red-800' },
};

// 模拟实时数据
const generateRealtimeData = () => {
  const data = [];
  for (let i = 0; i < 30; i++) {
    data.push({
      time: `${i}s`,
      cpu: Math.random() * 100,
      memory: Math.random() * 100,
      latency: Math.random() * 50,
      throughput: Math.random() * 1000,
    });
  }
  return data;
};

export default function StressTesting() {
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [runningTests, setRunningTests] = useState<Set<string>>(new Set(['2']));
  const [realtimeData] = useState(generateRealtimeData());

  // API hooks
  const { data: stressTestsResponse, isLoading } = useStressTests();
  const createStressTest = useCreateStressTest();
  const runStressTest = useRunStressTest();

  // 使用模拟数据
  const testData = stressTestsResponse?.data || mockStressTests;

  // 运行测试
  const handleRunTest = async (testId: string) => {
    try {
      setRunningTests((prev) => new Set([...prev, testId]));
      await runStressTest.mutateAsync(testId);

      // 模拟测试过程
      setTimeout(() => {
        setRunningTests((prev) => {
          const newSet = new Set(prev);
          newSet.delete(testId);
          return newSet;
        });
      }, 10000);
    } catch (error) {
      setRunningTests((prev) => {
        const newSet = new Set(prev);
        newSet.delete(testId);
        return newSet;
      });
    }
  };

  // 停止测试
  const handleStopTest = (testId: string) => {
    setRunningTests((prev) => {
      const newSet = new Set(prev);
      newSet.delete(testId);
      return newSet;
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部操作区 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">压力测试</h3>
          <p className="text-sm text-muted-foreground">
            对系统进行各种压力测试，评估性能极限和稳定性
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Settings className="mr-2 h-4 w-4" />
              创建测试
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle>创建压力测试</DialogTitle>
            </DialogHeader>
            <CreateTestForm onClose={() => setIsCreateDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="tests" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tests">测试列表</TabsTrigger>
          <TabsTrigger value="monitor">实时监控</TabsTrigger>
        </TabsList>

        <TabsContent value="tests" className="space-y-4">
          {/* 测试列表 */}
          <div className="grid gap-4 md:grid-cols-2">
            {testData.map((test) => {
              const typeConfig = testTypes[test.type];
              const statusConf = statusConfig[test.status];
              const TypeIcon = typeConfig.icon;
              const StatusIcon = statusConf.icon;
              const isRunning = runningTests.has(test.id);

              return (
                <Card key={test.id} className="relative">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2">
                        <TypeIcon className="h-5 w-5 text-muted-foreground" />
                        <CardTitle className="text-base">{test.name}</CardTitle>
                      </div>
                      <div className="flex flex-col space-y-1">
                        <Badge className={typeConfig.color}>
                          {typeConfig.label}
                        </Badge>
                        <Badge variant="outline" className={statusConf.color}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {statusConf.label}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {test.description}
                    </p>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {/* 测试配置 */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">持续时间:</span>
                        <span className="ml-2 font-medium">
                          {test.config.duration}分钟
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">强度:</span>
                        <span className="ml-2 font-medium">
                          {test.config.intensity}%
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">目标:</span>
                        <span className="ml-2 font-medium">
                          {test.config.targets.length}个
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">指标:</span>
                        <span className="ml-2 font-medium">
                          {test.config.metrics.length}个
                        </span>
                      </div>
                    </div>

                    {/* 运行进度 */}
                    {isRunning && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span>测试进度</span>
                          <span>45%</span>
                        </div>
                        <Progress value={45} className="h-2" />
                        <div className="text-xs text-muted-foreground">
                          预计剩余时间: 15分钟
                        </div>
                      </div>
                    )}

                    {/* 测试结果 */}
                    {test.results && !isRunning && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">测试结果</span>
                          <div className="flex items-center space-x-2">
                            {test.results.passed ? (
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-600" />
                            )}
                            <span className="text-sm font-medium">
                              {test.results.score}/100
                            </span>
                          </div>
                        </div>

                        {test.results.issues.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-xs text-muted-foreground">
                              发现问题:
                            </span>
                            {test.results.issues
                              .slice(0, 2)
                              .map((issue, index) => (
                                <div
                                  key={index}
                                  className="flex items-center space-x-2"
                                >
                                  <AlertCircle className="h-3 w-3 text-orange-500" />
                                  <span className="text-xs">{issue}</span>
                                </div>
                              ))}
                            {test.results.issues.length > 2 && (
                              <span className="text-xs text-muted-foreground">
                                +{test.results.issues.length - 2}个问题
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* 操作按钮 */}
                    <div className="flex space-x-2">
                      {isRunning ? (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleStopTest(test.id)}
                        >
                          <Square className="mr-2 h-4 w-4" />
                          停止测试
                        </Button>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            onClick={() => handleRunTest(test.id)}
                          >
                            <Play className="mr-2 h-4 w-4" />
                            运行测试
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
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="monitor" className="space-y-4">
          {/* 实时监控 */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Cpu className="h-5 w-5" />
                  <span>CPU & 内存使用率</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={realtimeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="cpu"
                      stroke="#8884d8"
                      name="CPU"
                    />
                    <Line
                      type="monotone"
                      dataKey="memory"
                      stroke="#82ca9d"
                      name="内存"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Network className="h-5 w-5" />
                  <span>延迟 & 吞吐量</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={realtimeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="latency"
                      stackId="1"
                      stroke="#ffc658"
                      fill="#ffc658"
                      name="延迟(ms)"
                    />
                    <Area
                      type="monotone"
                      dataKey="throughput"
                      stackId="2"
                      stroke="#ff7300"
                      fill="#ff7300"
                      name="吞吐量"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 创建测试表单组件
function CreateTestForm({ onClose }: { onClose: () => void }) {
  const [formData, setFormData] = useState<{
    name: string;
    type: 'performance' | 'load' | 'volume' | 'endurance' | 'spike';
    description: string;
    duration: number;
    intensity: number;
    targets: string[];
    metrics: string[];
    thresholds: Record<string, number>;
  }>({
    name: '',
    type: 'performance',
    description: '',
    duration: 30,
    intensity: 70,
    targets: [],
    metrics: [],
    thresholds: {},
  });

  const createStressTest = useCreateStressTest();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createStressTest.mutateAsync({
        name: formData.name,
        description: formData.description,
        scenarios: formData.targets,
        parameters: {
          maxDrawdown: formData.thresholds.maxDrawdown || 0.1,
          volatilityMultiplier: formData.intensity / 100,
          liquidityStress: formData.thresholds.liquidityStress || 0.5,
        },
        duration: formData.duration,
      });
      onClose();
    } catch (error) {
      console.error('创建测试失败:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">测试名称</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, name: e.target.value }))
            }
            placeholder="输入测试名称"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="type">测试类型</Label>
          <Select
            value={formData.type}
            onValueChange={(value) =>
              setFormData((prev) => ({ ...prev, type: value as 'performance' | 'load' | 'volume' | 'endurance' | 'spike' }))
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(testTypes).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  {config.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">测试描述</Label>
        <Input
          id="description"
          value={formData.description}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, description: e.target.value }))
          }
          placeholder="描述这个压力测试的目标和范围"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="duration">持续时间（分钟）</Label>
          <Input
            id="duration"
            type="number"
            value={formData.duration}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                duration: parseInt(e.target.value),
              }))
            }
            min={1}
            max={180}
            required
          />
        </div>

        <div className="space-y-3">
          <Label>测试强度: {formData.intensity}%</Label>
          <Slider
            value={[formData.intensity]}
            onValueChange={([value]) =>
              setFormData((prev) => ({ ...prev, intensity: value }))
            }
            max={100}
            min={1}
            step={1}
            className="w-full"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2">
        <Button type="button" variant="outline" onClick={onClose}>
          取消
        </Button>
        <Button type="submit" disabled={createStressTest.isPending}>
          {createStressTest.isPending ? '创建中...' : '创建测试'}
        </Button>
      </div>
    </form>
  );
}
