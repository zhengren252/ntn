/**
 * 系统监控页面 - MVP占位符组件
 * 提供系统状态监控和性能分析的基础界面框架
 */

export default function MonitorPage() {
  return (
    <div data-testid="page-monitor" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">系统监控</h1>
        <p className="text-muted-foreground">
          系统状态监控和性能分析
        </p>
      </div>
      
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <p className="text-center text-muted-foreground">
          系统监控功能正在开发中...
        </p>
      </div>
    </div>
  );
}