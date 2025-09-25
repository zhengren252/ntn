/**
 * 交易执行页面组件
 * 提供订单管理和实时交易的基础界面框架
 */

import { useEffect } from 'react';

export default function Trading() {
  // 设置页面标题：交易执行 - ASTS Console
  useEffect(() => {
    document.title = '交易执行 - ASTS Console';
  }, []);

  return (
    <div data-testid="page-trading" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">交易执行</h1>
        <p className="text-muted-foreground">
          订单管理和实时交易
        </p>
      </div>
      
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <p className="text-center text-muted-foreground">
          交易执行功能正在开发中...
        </p>
      </div>
    </div>
  );
}