/**
 * 策略管理页面组件
 * 提供策略创建、编辑、优化配置的基础界面框架
 */

import { useEffect } from 'react';

export default function Strategy() {
  // 设置页面标题：策略管理 - ASTS Console
  useEffect(() => {
    document.title = '策略管理 - ASTS Console';
  }, []);

  return (
    <div data-testid="page-strategy" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">策略管理</h1>
        <p className="text-muted-foreground">
          策略创建和优化配置
        </p>
      </div>
      
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <p className="text-center text-muted-foreground">
          策略管理功能正在开发中...
        </p>
      </div>
    </div>
  );
}