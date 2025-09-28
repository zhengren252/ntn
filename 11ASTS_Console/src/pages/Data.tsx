/**
 * 数据中心页面组件
 * 提供市场数据和信息展示的基础界面框架
 */

import { useEffect } from 'react';

export default function Data() {
  // 设置页面标题：数据中心 - ASTS Console
  useEffect(() => {
    document.title = '数据中心 - ASTS Console';
  }, []);

  return (
    <div data-testid="page-data" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">数据中心</h1>
        <p className="text-muted-foreground">
          市场数据和信息展示
        </p>
      </div>
      
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <p className="text-center text-muted-foreground">
          数据中心功能正在开发中...
        </p>
      </div>
    </div>
  );
}