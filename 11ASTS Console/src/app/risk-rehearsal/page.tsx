'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Shield, Target, Activity, FileText } from 'lucide-react';
import ScenarioSimulation from '@/features/risk-rehearsal/components/ScenarioSimulation';
import StressTesting from '@/features/risk-rehearsal/components/StressTesting';
import RehearsalReports from '@/features/risk-rehearsal/components/RehearsalReports';

export default function RiskRehearsalPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">风控演习中心</h2>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <FileText className="mr-2 h-4 w-4" />
            演习报告
          </Button>
          <Button data-testid="start-rehearsal-button">
            <Shield className="mr-2 h-4 w-4" />
            启动演习
          </Button>
        </div>
      </div>

      {/* 概览卡片 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">本月演习次数</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">25</div>
            <p className="text-xs text-muted-foreground">比上月增加 12%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均通过率</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">87.5%</div>
            <p className="text-xs text-muted-foreground">比上月提升 3.2%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">发现问题</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-muted-foreground">已修复 6 个问题</p>
          </CardContent>
        </Card>
      </div>

      {/* 主要功能区域 */}
      <Tabs defaultValue="scenarios" className="space-y-4" data-testid="risk-rehearsal-form">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger
            value="scenarios"
            className="flex items-center space-x-2"
          >
            <Target className="h-4 w-4" />
            <span>场景模拟</span>
          </TabsTrigger>
          <TabsTrigger value="stress" className="flex items-center space-x-2">
            <Activity className="h-4 w-4" />
            <span>压力测试</span>
          </TabsTrigger>
          <TabsTrigger value="reports" className="flex items-center space-x-2">
            <FileText className="h-4 w-4" />
            <span>演习报告</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="scenarios">
          <ScenarioSimulation />
        </TabsContent>

        <TabsContent value="stress">
          <StressTesting />
        </TabsContent>

        <TabsContent value="reports">
          <RehearsalReports />
        </TabsContent>
      </Tabs>
    </div>
  );
}
