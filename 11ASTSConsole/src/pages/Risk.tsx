/**
 * 风险控制页面组件
 * 提供风险监控和预警设置的基础界面框架
 */

import { useEffect } from 'react';

export default function Risk() {
  // 设置页面标题：风险控制 - ASTS Console
  useEffect(() => {
    document.title = '风险控制 - ASTS Console';
  }, []);

  return (
    <div data-testid="page-risk" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">风险控制</h1>
        <p className="text-muted-foreground">
          风险监控和预警设置
        </p>
      </div>
      
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <p className="text-center text-muted-foreground">
          风险控制功能正在开发中...
        </p>
      </div>
    </div>
  );
}