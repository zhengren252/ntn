/**
 * 系统监控页面组件
 * 提供系统状态监控和性能分析的基础界面框架
 */

import { useEffect } from 'react';

export default function Monitor() {
  // 设置页面标题：系统监控 - ASTS Console
  useEffect(() => {
    document.title = '系统监控 - ASTS Console';
  }, []);

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