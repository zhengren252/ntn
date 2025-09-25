'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { MetricsCards } from '@/features/dashboard/components/MetricsCards'
import { TradingChart } from '@/features/dashboard/components/TradingChart';
import { SystemControls } from '@/features/dashboard/components/SystemControls';

export default function DashboardPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">仪表盘</h2>
      </div>

      {/* 系统控制面板 */}
      <SystemControls />

      {/* 关键指标卡片 */}
      <MetricsCards />

      {/* 主要内容区域 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* 实时交易图表 */}
        <div className="col-span-4">
          <TradingChart />
        </div>

        {/* 最近活动 */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>最近活动</CardTitle>
            <CardDescription>系统最新动态和交易记录</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center">
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    策略 "趋势跟踪A" 执行成功
                  </p>
                  <p className="text-sm text-muted-foreground">
                    盈利 +¥1,234.56
                  </p>
                </div>
                <div className="ml-auto font-medium trading-profit">+2.1%</div>
              </div>

              <div className="flex items-center">
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    新策略等待审核
                  </p>
                  <p className="text-sm text-muted-foreground">
                    "均值回归B" 策略
                  </p>
                </div>
                <div className="ml-auto font-medium">
                  <Badge variant="outline">待审核</Badge>
                </div>
              </div>

              <div className="flex items-center">
                <div className="ml-4 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    模组状态更新
                  </p>
                  <p className="text-sm text-muted-foreground">
                    扫描器模组重启完成
                  </p>
                </div>
                <div className="ml-auto font-medium">
                  <Badge className="status-running">正常</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
