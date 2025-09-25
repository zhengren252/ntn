/**
 * 财务管理页面组件
 * 提供资金管理和绩效分析的基础界面框架
 */

import { useEffect } from 'react';

export default function Finance() {
  // 设置页面标题：财务管理 - ASTS Console
  useEffect(() => {
    document.title = '财务管理 - ASTS Console';
  }, []);

  return (
    <div data-testid="page-finance" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">财务管理</h1>
        <p className="text-muted-foreground">
          资金管理和绩效分析
        </p>
      </div>
      
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <p className="text-center text-muted-foreground">
          财务管理功能正在开发中...
        </p>
      </div>
    </div>
  );
}