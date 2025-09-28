'use client';

import { Button } from '@/components/ui/button';
import { Settings, Users } from 'lucide-react';
import { ReviewStats } from '@/features/review/components/ReviewStats';
import { StrategyReviewList } from '@/features/review/components/StrategyReviewList';

export default function ReviewPage() {
  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">人工审核中心</h2>
          <p className="text-muted-foreground mt-2">
            管理和审核AI生成的交易策略，确保策略质量和风险控制
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" className="flex items-center space-x-2">
            <Users className="h-4 w-4" />
            <span>批量审核</span>
          </Button>
          <Button className="flex items-center space-x-2">
            <Settings className="h-4 w-4" />
            <span>审核设置</span>
          </Button>
        </div>
      </div>

      {/* 审核统计 */}
      <ReviewStats />

      {/* 待审核列表 */}
      <StrategyReviewList />
    </div>
  );
}
