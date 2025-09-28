'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CostStatistics } from '@/features/api-cost/components/CostStatistics';
import { BudgetManager } from '@/features/api-cost/components/BudgetManager';
import { CostAnalytics } from '@/features/api-cost/components/CostAnalytics';

export default function ApiCostPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">API成本中心</h2>
          <p className="text-muted-foreground">
            监控和管理API调用成本，优化预算分配
          </p>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">成本概览</TabsTrigger>
          <TabsTrigger value="budget">预算管理</TabsTrigger>
          <TabsTrigger value="analytics">成本分析</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <CostStatistics />
        </TabsContent>

        <TabsContent value="budget" className="space-y-4">
          <BudgetManager />
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <CostAnalytics />
        </TabsContent>
      </Tabs>
    </div>
  );
}