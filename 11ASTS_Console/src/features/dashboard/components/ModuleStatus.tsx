'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Play, 
  Pause, 
  Square, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Clock,
  Activity
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useSystemStatusWebSocket } from '@/hooks/useWebSocket';

interface ModuleInfo {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping';
  health: 'healthy' | 'warning' | 'critical';
  cpu: number;
  memory: number;
  uptime: number;
  lastUpdate: number;
  description: string;
}

interface ModuleCardProps {
  module: ModuleInfo;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onRestart: (id: string) => void;
}

const ModuleCard = ({ module, onStart, onStop, onRestart }: ModuleCardProps) => {
  const getStatusConfig = () => {
    switch (module.status) {
      case 'running':
        return {
          icon: <CheckCircle className="h-4 w-4" />,
          badge: <Badge className="bg-green-500 hover:bg-green-600">运行中</Badge>,
          color: 'text-green-600'
        };
      case 'starting':
        return {
          icon: <RefreshCw className="h-4 w-4 animate-spin" />,
          badge: <Badge variant="outline">启动中</Badge>,
          color: 'text-blue-600'
        };
      case 'stopping':
        return {
          icon: <Clock className="h-4 w-4" />,
          badge: <Badge variant="outline">停止中</Badge>,
          color: 'text-orange-600'
        };
      case 'error':
        return {
          icon: <XCircle className="h-4 w-4" />,
          badge: <Badge variant="destructive">错误</Badge>,
          color: 'text-red-600'
        };
      default:
        return {
          icon: <Square className="h-4 w-4" />,
          badge: <Badge variant="secondary">已停止</Badge>,
          color: 'text-gray-600'
        };
    }
  };

  const getHealthConfig = () => {
    switch (module.health) {
      case 'healthy':
        return { color: 'bg-green-500', text: '健康' };
      case 'warning':
        return { color: 'bg-yellow-500', text: '警告' };
      case 'critical':
        return { color: 'bg-red-500', text: '严重' };
    }
  };

  const status = getStatusConfig();
  const health = getHealthConfig();

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <Card className="relative">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className={status.color}>
              {status.icon}
            </div>
            <div>
              <CardTitle className="text-base">{module.name}</CardTitle>
              <p className="text-xs text-muted-foreground">{module.description}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${health.color}`}></div>
            {status.badge}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-3">
          {/* 资源使用情况 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span>CPU使用率</span>
              <span>{module.cpu}%</span>
            </div>
            <Progress value={module.cpu} className="h-2" />
            
            <div className="flex justify-between text-xs">
              <span>内存使用率</span>
              <span>{module.memory}%</span>
            </div>
            <Progress value={module.memory} className="h-2" />
          </div>

          {/* 运行信息 */}
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>运行时间: {formatUptime(module.uptime)}</span>
            <span>健康状态: {health.text}</span>
          </div>

          {/* 控制按钮 */}
          <div className="flex space-x-2 pt-2">
            {module.status === 'stopped' && (
              <Button
                size="sm"
                onClick={() => onStart(module.id)}
                className="flex-1"
              >
                <Play className="h-3 w-3 mr-1" />
                启动
              </Button>
            )}
            
            {module.status === 'running' && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onStop(module.id)}
                  className="flex-1"
                >
                  <Pause className="h-3 w-3 mr-1" />
                  停止
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onRestart(module.id)}
                  className="flex-1"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  重启
                </Button>
              </>
            )}
            
            {(module.status === 'starting' || module.status === 'stopping') && (
              <Button size="sm" disabled className="flex-1">
                <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                处理中...
              </Button>
            )}
            
            {module.status === 'error' && (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => onRestart(module.id)}
                className="flex-1"
              >
                <AlertTriangle className="h-3 w-3 mr-1" />
                修复
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export const ModuleStatus = () => {
  const [modules, setModules] = useState<ModuleInfo[]>([
    {
      id: 'api-forge',
      name: 'API Forge',
      status: 'running',
      health: 'healthy',
      cpu: 15,
      memory: 32,
      uptime: 7200,
      lastUpdate: Date.now(),
      description: 'API网关服务'
    },
    {
      id: 'data-spider',
      name: 'Data Spider',
      status: 'running',
      health: 'healthy',
      cpu: 25,
      memory: 45,
      uptime: 7200,
      lastUpdate: Date.now(),
      description: '数据采集服务'
    },
    {
      id: 'scan-pulse',
      name: 'Scan Pulse',
      status: 'running',
      health: 'warning',
      cpu: 35,
      memory: 28,
      uptime: 3600,
      lastUpdate: Date.now(),
      description: '市场扫描服务'
    },
    {
      id: 'opti-core',
      name: 'Opti Core',
      status: 'running',
      health: 'healthy',
      cpu: 42,
      memory: 67,
      uptime: 7200,
      lastUpdate: Date.now(),
      description: '策略优化引擎'
    },
    {
      id: 'trade-guard',
      name: 'Trade Guard',
      status: 'running',
      health: 'healthy',
      cpu: 18,
      memory: 23,
      uptime: 7200,
      lastUpdate: Date.now(),
      description: '风险管理系统'
    },
    {
      id: 'neuro-hub',
      name: 'Neuro Hub',
      status: 'error',
      health: 'critical',
      cpu: 0,
      memory: 0,
      uptime: 0,
      lastUpdate: Date.now() - 300000,
      description: 'AI决策中心'
    }
  ]);

  const { lastMessage } = useSystemStatusWebSocket();

  // 模拟实时更新模块状态
  useEffect(() => {
    const interval = setInterval(() => {
      setModules(prev => prev.map(module => ({
        ...module,
        cpu: Math.max(0, Math.min(100, module.cpu + (Math.random() - 0.5) * 10)),
        memory: Math.max(0, Math.min(100, module.memory + (Math.random() - 0.5) * 5)),
        uptime: module.status === 'running' ? module.uptime + 5 : module.uptime,
        lastUpdate: Date.now()
      })));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 处理WebSocket消息更新
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'module_status') {
      const data = lastMessage.data as {
        moduleId: string;
        status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping';
        health: 'healthy' | 'warning' | 'critical';
        cpu: number;
        memory: number;
      };
      const { moduleId, status, health, cpu, memory } = data;
      setModules(prev => prev.map(module => 
        module.id === moduleId 
          ? { ...module, status, health, cpu, memory, lastUpdate: Date.now() }
          : module
      ));
    }
  }, [lastMessage]);

  const handleStart = async (moduleId: string) => {
    setModules(prev => prev.map(module => 
      module.id === moduleId ? { ...module, status: 'starting' } : module
    ));
    
    // 模拟API调用
    setTimeout(() => {
      setModules(prev => prev.map(module => 
        module.id === moduleId 
          ? { ...module, status: 'running', health: 'healthy', uptime: 0 }
          : module
      ));
    }, 2000);
  };

  const handleStop = async (moduleId: string) => {
    setModules(prev => prev.map(module => 
      module.id === moduleId ? { ...module, status: 'stopping' } : module
    ));
    
    // 模拟API调用
    setTimeout(() => {
      setModules(prev => prev.map(module => 
        module.id === moduleId 
          ? { ...module, status: 'stopped', cpu: 0, memory: 0, uptime: 0 }
          : module
      ));
    }, 1500);
  };

  const handleRestart = async (moduleId: string) => {
    setModules(prev => prev.map(module => 
      module.id === moduleId ? { ...module, status: 'stopping' } : module
    ));
    
    // 模拟重启过程
    setTimeout(() => {
      setModules(prev => prev.map(module => 
        module.id === moduleId ? { ...module, status: 'starting' } : module
      ));
      
      setTimeout(() => {
        setModules(prev => prev.map(module => 
          module.id === moduleId 
            ? { ...module, status: 'running', health: 'healthy', uptime: 0 }
            : module
        ));
      }, 2000);
    }, 1000);
  };

  const runningCount = modules.filter(m => m.status === 'running').length;
  const errorCount = modules.filter(m => m.status === 'error').length;
  const totalCount = modules.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>模块状态监控</span>
          <div className="flex items-center space-x-2">
            <Badge variant="outline">
              <Activity className="h-3 w-3 mr-1" />
              {runningCount}/{totalCount} 运行中
            </Badge>
            {errorCount > 0 && (
              <Badge variant="destructive">
                <AlertTriangle className="h-3 w-3 mr-1" />
                {errorCount} 错误
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => (
            <ModuleCard
              key={module.id}
              module={module}
              onStart={handleStart}
              onStop={handleStop}
              onRestart={handleRestart}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};