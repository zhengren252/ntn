'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Bot,
  MessageSquare,
  Zap,
  TrendingUp,
  Activity,
  Clock,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { useAiLabSession } from '@/hooks/useApi';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ComponentType<{ className?: string }>;
  status?: 'success' | 'warning' | 'error' | 'info';
  description?: string;
}

const StatCard = ({
  title,
  value,
  change,
  icon: Icon,
  status,
  description,
}: StatCardProps) => {
  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'error':
        return 'text-red-600';
      case 'info':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getChangeColor = () => {
    if (change === undefined) return '';
    return change >= 0 ? 'text-green-600' : 'text-red-600';
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${getStatusColor()}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center justify-between mt-1">
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
          {change !== undefined && (
            <p className={`text-xs ${getChangeColor()}`}>
              {change >= 0 ? '+' : ''}
              {change}%
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export const AiLabStats = () => {
  const { data: sessionData, isLoading } = useAiLabSession();

  // 模拟统计数据
  const stats = {
    activeSessions: sessionData?.data ? 1 : 3, // 基于session状态推断活跃会话数
    generatedStrategies: 24,
    successRate: 87.5,
    aiStatus: 'online' as 'online' | 'busy' | 'offline',
    todayRequests: 127,
    avgResponseTime: 1.2,
    strategiesInTesting: 5,
    strategiesLive: 12,
  };

  const getAiStatusInfo = () => {
    switch (stats.aiStatus) {
      case 'online':
        return {
          label: '在线',
          status: 'success' as const,
          icon: CheckCircle,
        };
      case 'busy':
        return {
          label: '繁忙',
          status: 'warning' as const,
          icon: Clock,
        };
      case 'offline':
        return {
          label: '离线',
          status: 'error' as const,
          icon: AlertCircle,
        };
      default:
        return {
          label: '未知',
          status: 'info' as const,
          icon: Activity,
        };
    }
  };

  const aiStatusInfo = getAiStatusInfo();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
              <div className="h-4 w-4 bg-gray-200 rounded animate-pulse" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-gray-200 rounded animate-pulse mb-2" />
              <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 主要统计指标 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="活跃会话"
          value={stats.activeSessions}
          change={12}
          icon={MessageSquare}
          status="info"
          description="当前进行中的对话"
        />
        <StatCard
          title="生成策略"
          value={stats.generatedStrategies}
          change={8}
          icon={Zap}
          status="success"
          description="本月累计生成"
        />
        <StatCard
          title="成功率"
          value={`${stats.successRate}%`}
          change={2.1}
          icon={TrendingUp}
          status="success"
          description="策略生成成功率"
        />
        <StatCard
          title="AI状态"
          value={aiStatusInfo.label}
          icon={aiStatusInfo.icon}
          status={aiStatusInfo.status}
          description={`响应时间 ${stats.avgResponseTime}s`}
        />
      </div>

      {/* 详细统计 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-4 w-4" />
              <span>今日活动</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">AI请求次数</span>
                <span className="font-medium">{stats.todayRequests}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">平均响应时间</span>
                <span className="font-medium">{stats.avgResponseTime}s</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">新建会话</span>
                <span className="font-medium">8</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bot className="h-4 w-4" />
              <span>策略状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">测试中</span>
                <div className="flex items-center space-x-2">
                  <span className="font-medium">
                    {stats.strategiesInTesting}
                  </span>
                  <Badge variant="secondary">测试</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">运行中</span>
                <div className="flex items-center space-x-2">
                  <span className="font-medium">{stats.strategiesLive}</span>
                  <Badge variant="default">运行</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">草稿</span>
                <div className="flex items-center space-x-2">
                  <span className="font-medium">7</span>
                  <Badge variant="outline">草稿</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4" />
              <span>性能指标</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">平均收益率</span>
                <span className="font-medium text-green-600">+12.3%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">最大回撤</span>
                <span className="font-medium text-red-600">-5.2%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">夏普比率</span>
                <span className="font-medium">1.85</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
