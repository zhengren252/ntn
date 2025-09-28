'use client';

import { Button } from '@/components/ui/button';
import { SystemMetrics } from '@/features/monitoring/components/SystemMetrics';
import { ModuleStatus } from '@/features/monitoring/components/ModuleStatus';
import { AlertManager } from '@/features/monitoring/components/AlertManager';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Monitor, Download, Settings } from 'lucide-react';

export default function MonitoringPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">系统监控中心</h1>
          <p className="text-muted-foreground">
            实时监控系统状态、模块运行情况和告警信息
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            导出报告
          </Button>
          <Button>
            <Settings className="h-4 w-4 mr-2" />
            监控设置
          </Button>
        </div>
      </div>

      {/* 系统指标 */}
      <SystemMetrics />

      {/* 模块状态和告警管理 */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ModuleStatus />
        <AlertManager />
      </div>

      {/* 性能图表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Monitor className="h-5 w-5" />
            <span>系统性能趋势</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg">
            <div className="text-center">
              <Monitor className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-muted-foreground">性能监控图表将在此处显示</p>
              <p className="text-sm text-gray-400 mt-2">
                集成 ECharts 或其他图表库来展示实时性能数据
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
