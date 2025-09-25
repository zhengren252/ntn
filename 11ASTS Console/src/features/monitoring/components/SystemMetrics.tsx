'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Cpu,
  MemoryStick,
  HardDrive,
  Wifi,
  Thermometer,
  Zap,
  Activity,
  Server,
} from 'lucide-react';
import { useSystemMetrics } from '@/hooks/useApi';

interface MetricCardProps {
  title: string;
  value: string | number;
  percentage?: number;
  icon: React.ComponentType<{ className?: string }>;
  status?: 'normal' | 'warning' | 'critical';
  description?: string;
  trend?: 'up' | 'down' | 'stable';
}

const MetricCard = ({
  title,
  value,
  percentage,
  icon: Icon,
  status = 'normal',
  description,
  trend,
}: MetricCardProps) => {
  const getStatusColor = () => {
    switch (status) {
      case 'warning':
        return 'text-yellow-600';
      case 'critical':
        return 'text-red-600';
      default:
        return 'text-green-600';
    }
  };

  const getProgressColor = () => {
    if (percentage === undefined) return '';
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return '↗';
      case 'down':
        return '↘';
      case 'stable':
        return '→';
      default:
        return '';
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${getStatusColor()}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold flex items-center space-x-2">
          <span>{value}</span>
          {trend && (
            <span className={`text-sm ${getStatusColor()}`}>
              {getTrendIcon()}
            </span>
          )}
        </div>
        {percentage !== undefined && (
          <div className="mt-2">
            <Progress value={percentage} className="h-2" />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span>{percentage}%</span>
              <span>100%</span>
            </div>
          </div>
        )}
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </CardContent>
    </Card>
  );
};

export const SystemMetrics = () => {
  const { data: metricsData, isLoading } = useSystemMetrics();

  // 模拟系统指标数据
  const metrics = metricsData?.data || {
    cpu: {
      usage: 45.2,
      cores: 8,
      frequency: 3.2,
      temperature: 65,
    },
    memory: {
      used: 12.5,
      total: 32,
      percentage: 39.1,
    },
    disk: {
      used: 256,
      total: 1024,
      percentage: 25.0,
    },
    network: {
      status: 'connected',
      latency: 15,
      downloadSpeed: 125.6,
      uploadSpeed: 45.2,
    },
    power: {
      consumption: 180,
      efficiency: 92,
    },
    uptime: 2592000, // 30天的秒数
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days}天${hours}小时`;
  };

  const getNetworkStatus = () => {
    switch (metrics.network.status) {
      case 'connected':
        return { label: '已连接', status: 'normal' as const };
      case 'disconnected':
        return { label: '断开连接', status: 'critical' as const };
      case 'unstable':
        return { label: '不稳定', status: 'warning' as const };
      default:
        return { label: '未知', status: 'warning' as const };
    }
  };

  const getCpuStatus = () => {
    if (metrics.cpu.usage >= 90) return 'critical';
    if (metrics.cpu.usage >= 70) return 'warning';
    return 'normal';
  };

  const getMemoryStatus = () => {
    if (metrics.memory.percentage >= 90) return 'critical';
    if (metrics.memory.percentage >= 70) return 'warning';
    return 'normal';
  };

  const getDiskStatus = () => {
    if (metrics.disk.percentage >= 90) return 'critical';
    if (metrics.disk.percentage >= 80) return 'warning';
    return 'normal';
  };

  const getTemperatureStatus = () => {
    if (metrics.cpu.temperature >= 80) return 'critical';
    if (metrics.cpu.temperature >= 70) return 'warning';
    return 'normal';
  };

  const networkStatus = getNetworkStatus();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-4 bg-gray-200 rounded animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-gray-200 rounded animate-pulse mb-2" />
                <div className="h-2 w-full bg-gray-200 rounded animate-pulse mb-1" />
                <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 主要系统指标 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="CPU使用率"
          value={`${metrics.cpu.usage}%`}
          percentage={metrics.cpu.usage}
          icon={Cpu}
          status={getCpuStatus()}
          description={`${metrics.cpu.cores}核心 @ ${metrics.cpu.frequency}GHz`}
          trend="stable"
        />

        <MetricCard
          title="内存使用"
          value={`${metrics.memory.used}GB`}
          percentage={metrics.memory.percentage}
          icon={MemoryStick}
          status={getMemoryStatus()}
          description={`总计 ${metrics.memory.total}GB`}
          trend="up"
        />

        <MetricCard
          title="磁盘空间"
          value={`${metrics.disk.used}GB`}
          percentage={metrics.disk.percentage}
          icon={HardDrive}
          status={getDiskStatus()}
          description={`总计 ${metrics.disk.total}GB`}
          trend="stable"
        />

        <MetricCard
          title="网络状态"
          value={networkStatus.label}
          icon={Wifi}
          status={networkStatus.status}
          description={`延迟 ${metrics.network.latency}ms`}
          trend="stable"
        />
      </div>

      {/* 详细系统信息 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Thermometer className="h-4 w-4" />
              <span>系统温度</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">CPU温度</span>
                <div className="flex items-center space-x-2">
                  <span className="font-medium">
                    {metrics.cpu.temperature}°C
                  </span>
                  <Badge
                    variant={
                      getTemperatureStatus() === 'critical'
                        ? 'destructive'
                        : getTemperatureStatus() === 'warning'
                          ? 'secondary'
                          : 'default'
                    }
                  >
                    {getTemperatureStatus() === 'critical'
                      ? '过热'
                      : getTemperatureStatus() === 'warning'
                        ? '偏高'
                        : '正常'}
                  </Badge>
                </div>
              </div>
              <Progress
                value={(metrics.cpu.temperature / 100) * 100}
                className="h-2"
              />
              <div className="text-xs text-gray-500">安全范围: 0°C - 70°C</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-4 w-4" />
              <span>网络性能</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">下载速度</span>
                <span className="font-medium">
                  {metrics.network.downloadSpeed} Mbps
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">上传速度</span>
                <span className="font-medium">
                  {metrics.network.uploadSpeed} Mbps
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">网络延迟</span>
                <span className="font-medium">{metrics.network.latency}ms</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Server className="h-4 w-4" />
              <span>系统信息</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">系统运行时间</span>
                <span className="font-medium">
                  {formatUptime(metrics.uptime)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">功耗</span>
                <span className="font-medium">
                  {metrics.power?.consumption || 0}W
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">能效比</span>
                <div className="flex items-center space-x-2">
                  <span className="font-medium">
                    {metrics.power?.efficiency || 0}%
                  </span>
                  <Badge variant="default">优秀</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
