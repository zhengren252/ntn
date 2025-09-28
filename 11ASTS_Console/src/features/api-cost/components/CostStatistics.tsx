'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Calendar,
  CreditCard,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { useCostStatistics } from '@/hooks/useApi';

interface CostMetricProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ComponentType<{ className?: string }>;
  status?: 'normal' | 'warning' | 'critical';
  description?: string;
  budget?: number;
  spent?: number;
}

const CostMetric = ({
  title,
  value,
  change,
  icon: Icon,
  status = 'normal',
  description,
  budget,
  spent,
}: CostMetricProps) => {
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

  const getChangeColor = () => {
    if (change === undefined) return '';
    return change >= 0 ? 'text-red-600' : 'text-green-600';
  };

  const getChangeIcon = () => {
    if (change === undefined) return null;
    return change >= 0 ? (
      <TrendingUp className="h-3 w-3" />
    ) : (
      <TrendingDown className="h-3 w-3" />
    );
  };

  const getBudgetUsage = () => {
    if (budget === undefined || spent === undefined) return null;
    const percentage = (spent / budget) * 100;
    return {
      percentage,
      status:
        percentage >= 90 ? 'critical' : percentage >= 75 ? 'warning' : 'normal',
    };
  };

  const budgetUsage = getBudgetUsage();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${getStatusColor()}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>

        {change !== undefined && (
          <div
            className={`flex items-center space-x-1 text-xs ${getChangeColor()}`}
          >
            {getChangeIcon()}
            <span>
              {change >= 0 ? '+' : ''}
              {change}%
            </span>
            <span className="text-gray-500">较上月</span>
          </div>
        )}

        {budgetUsage && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-600">预算使用</span>
              <span
                className={`font-medium ${
                  budgetUsage.status === 'critical'
                    ? 'text-red-600'
                    : budgetUsage.status === 'warning'
                      ? 'text-yellow-600'
                      : 'text-green-600'
                }`}
              >
                {budgetUsage.percentage.toFixed(1)}%
              </span>
            </div>
            <Progress value={budgetUsage.percentage} className="h-2" />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>${spent}</span>
              <span>${budget}</span>
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

export const CostStatistics = () => {
  const { data: costData, isLoading } = useCostStatistics();

  interface CostData {
    totalCost: number;
    monthlyBudget: number;
    dailyAverage: number;
    apiCalls: number;
    costPerCall: number;
    topServices: Array<{
      name: string;
      cost: number;
      calls: number;
      percentage: number;
    }>;
    monthlyTrend: Array<{
      month: string;
      cost: number;
    }>;
  }

  // 模拟成本数据 - API数据结构与组件期望不匹配，暂时使用模拟数据
  const costs: CostData = (costData?.data as unknown as CostData) || {
    totalCost: 1247.5,
    monthlyBudget: 2000,
    dailyAverage: 41.58,
    apiCalls: 125847,
    costPerCall: 0.0099,
    topServices: [
      { name: '币安API', cost: 456.78, calls: 45623, percentage: 36.6 },
      { name: 'OpenAI GPT-4', cost: 324.12, calls: 8934, percentage: 26.0 },
      { name: '火币API', cost: 198.45, calls: 32145, percentage: 15.9 },
      { name: '数据存储', cost: 156.23, calls: 0, percentage: 12.5 },
      { name: '其他服务', cost: 111.92, calls: 39145, percentage: 9.0 },
    ],
    monthlyTrend: [
      { month: '1月', cost: 1156.23 },
      { month: '2月', cost: 1089.45 },
      { month: '3月', cost: 1234.67 },
      { month: '4月', cost: 1347.89 },
      { month: '5月', cost: 1247.5 },
    ],
  };

  const getBudgetStatus = () => {
    const usage = (costs.totalCost / costs.monthlyBudget) * 100;
    if (usage >= 90) return 'critical';
    if (usage >= 75) return 'warning';
    return 'normal';
  };

  const getMonthlyChange = () => {
    const currentMonth = costs.monthlyTrend[costs.monthlyTrend.length - 1];
    const previousMonth = costs.monthlyTrend[costs.monthlyTrend.length - 2];
    if (!currentMonth || !previousMonth) return 0;
    return (
      ((currentMonth.cost - previousMonth.cost) / previousMonth.cost) * 100
    );
  };

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
      {/* 主要成本指标 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <CostMetric
          title="本月总成本"
          value={`$${costs.totalCost.toFixed(2)}`}
          change={getMonthlyChange()}
          icon={DollarSign}
          status={getBudgetStatus()}
          description="当前月份累计支出"
          budget={costs.monthlyBudget}
          spent={costs.totalCost}
        />

        <CostMetric
          title="日均成本"
          value={`$${costs.dailyAverage.toFixed(2)}`}
          change={-5.2}
          icon={Calendar}
          status="normal"
          description="过去30天平均值"
        />

        <CostMetric
          title="API调用次数"
          value={costs.apiCalls.toLocaleString()}
          change={12.8}
          icon={Activity}
          status="normal"
          description="本月累计调用"
        />

        <CostMetric
          title="单次调用成本"
          value={`$${costs.costPerCall.toFixed(4)}`}
          change={-2.1}
          icon={CreditCard}
          status="normal"
          description="平均每次API调用"
        />
      </div>

      {/* 服务成本分布 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-4 w-4" />
              <span>服务成本分布</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {costs.topServices.map((service, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">
                        {service.name}
                      </span>
                      <Badge variant="outline">{service.percentage}%</Badge>
                    </div>
                    <span className="font-bold">
                      ${service.cost.toFixed(2)}
                    </span>
                  </div>
                  <Progress value={service.percentage} className="h-2" />
                  {service.calls > 0 && (
                    <div className="text-xs text-gray-500">
                      {service.calls.toLocaleString()} 次调用
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4" />
              <span>月度趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {costs.monthlyTrend.map((month, index) => {
                const isCurrentMonth = index === costs.monthlyTrend.length - 1;
                const previousMonth = costs.monthlyTrend[index - 1];
                const change = previousMonth
                  ? ((month.cost - previousMonth.cost) / previousMonth.cost) *
                    100
                  : 0;

                return (
                  <div
                    key={index}
                    className={`flex items-center justify-between p-2 rounded ${
                      isCurrentMonth ? 'bg-blue-50 border border-blue-200' : ''
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">{month.month}</span>
                      {isCurrentMonth && <Badge variant="default">当前</Badge>}
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold">
                        ${month.cost.toFixed(2)}
                      </span>
                      {index > 0 && (
                        <div
                          className={`flex items-center space-x-1 text-xs ${
                            change >= 0 ? 'text-red-600' : 'text-green-600'
                          }`}
                        >
                          {change >= 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          <span>{Math.abs(change).toFixed(1)}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 预算状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <CheckCircle className="h-4 w-4" />
            <span>预算状态</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium">月度预算</h3>
                <p className="text-sm text-gray-600">
                  已使用 ${costs.totalCost.toFixed(2)} / ${costs.monthlyBudget}
                </p>
              </div>
              <div className="flex items-center space-x-2">
                {getBudgetStatus() === 'critical' && (
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                )}
                {getBudgetStatus() === 'warning' && (
                  <AlertTriangle className="h-5 w-5 text-yellow-600" />
                )}
                {getBudgetStatus() === 'normal' && (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                )}
                <Badge
                  variant={
                    getBudgetStatus() === 'critical'
                      ? 'destructive'
                      : getBudgetStatus() === 'warning'
                        ? 'secondary'
                        : 'default'
                  }
                >
                  {getBudgetStatus() === 'critical'
                    ? '超支风险'
                    : getBudgetStatus() === 'warning'
                      ? '接近预算'
                      : '预算充足'}
                </Badge>
              </div>
            </div>

            <Progress
              value={(costs.totalCost / costs.monthlyBudget) * 100}
              className="h-3"
            />

            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-600">剩余预算</span>
                <p className="font-medium">
                  ${(costs.monthlyBudget - costs.totalCost).toFixed(2)}
                </p>
              </div>
              <div>
                <span className="text-gray-600">预计月底</span>
                <p className="font-medium">
                  ${(costs.dailyAverage * 31).toFixed(2)}
                </p>
              </div>
              <div>
                <span className="text-gray-600">节省空间</span>
                <p className="font-medium text-green-600">
                  $
                  {Math.max(
                    0,
                    costs.monthlyBudget - costs.dailyAverage * 31
                  ).toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
