'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Package,
  Play,
  Square,
  Settings,
  MoreHorizontal,
  Plus,
  Upload,

  GitBranch,
} from 'lucide-react';
import ModuleConfiguration from '@/features/modules/components/ModuleConfiguration';
import DependencyManager from '@/features/modules/components/DependencyManager';
import ModuleImportExport from '@/features/modules/components/ModuleImportExport';

interface Module {
  id: string;
  name: string;
  version: string;
  status: 'running' | 'stopped' | 'developing';
  description: string;
  lastUpdate: string;
}

export default function ModulesPage() {
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showDependencies, setShowDependencies] = useState(false);
  const [showImportExport, setShowImportExport] = useState(false);
  const [modules, setModules] = useState<Module[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // 获取模块列表
  const fetchModules = useCallback(async () => {
    setIsLoading(true);
    try {
      // 模拟API调用 - 在实际项目中这里应该调用真实的API
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const moduleData: Module[] = [
        {
          id: 'data-collector',
          name: '数据采集模块',
          version: 'v1.2.3',
          status: 'running',
          description: '负责从各大交易所采集实时市场数据',
          lastUpdate: '2024-01-15',
        },
        {
          id: 'strategy-executor',
          name: '策略执行模块',
          version: 'v2.1.0',
          status: 'running',
          description: '执行交易策略和订单管理',
          lastUpdate: '2024-01-14',
        },
        {
          id: 'risk-monitor',
          name: '风控监控模块',
          version: 'v1.5.2',
          status: 'running',
          description: '实时监控交易风险和资金安全',
          lastUpdate: '2024-01-13',
        },
        {
          id: 'api-gateway',
          name: 'API网关模块',
          version: 'v1.8.1',
          status: 'stopped',
          description: '提供统一的API接口服务',
          lastUpdate: '2024-01-12',
        },
        {
          id: 'data-storage',
          name: '数据存储模块',
          version: 'v1.3.4',
          status: 'running',
          description: '管理历史数据和实时数据存储',
          lastUpdate: '2024-01-11',
        },
        {
          id: 'ai-analyzer',
          name: 'AI分析模块',
          version: 'v0.9.1',
          status: 'developing',
          description: '基于机器学习的市场分析和预测',
          lastUpdate: '2024-01-10',
        },
      ];
      
      setModules(moduleData);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to fetch modules:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 手动刷新模块列表
  const handleRefresh = useCallback(() => {
    fetchModules();
  }, [fetchModules]);

  // 模块导入后的刷新逻辑
  const handleModuleImported = useCallback(() => {
    // 模块导入成功后自动刷新列表
    fetchModules();
  }, [fetchModules]);

  // 组件挂载时获取模块列表
  useEffect(() => {
    fetchModules();
  }, [fetchModules]);

  // 计算模块统计
  const moduleStats = {
    total: modules.length,
    running: modules.filter(m => m.status === 'running').length,
    stopped: modules.filter(m => m.status === 'stopped').length,
    developing: modules.filter(m => m.status === 'developing').length,
  };

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">模块管理</h2>
          <p className="text-sm text-muted-foreground">
            最后更新: {lastRefresh.toLocaleString()}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={handleRefresh} disabled={isLoading}>
            <Settings className="mr-2 h-4 w-4" />
            {isLoading ? '刷新中...' : '刷新'}
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            创建模块
          </Button>
          <Button variant="outline" onClick={() => setShowImportExport(true)}>
            <Upload className="mr-2 h-4 w-4" />
            导入/导出
          </Button>
        </div>
      </div>

      {/* 模块列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          // 加载状态
          Array.from({ length: 6 }).map((_, index) => (
            <Card key={module.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="h-6 bg-gray-200 rounded animate-pulse w-32"></div>
                  <div className="h-6 bg-gray-200 rounded animate-pulse w-16"></div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
                  <div className="flex justify-between">
                    <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
                    <div className="h-4 bg-gray-200 rounded animate-pulse w-24"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          modules.map((module, index) => (
          <Card key={index}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center space-x-2">
                  <Package className="h-5 w-5" />
                  <span className="text-lg">{module.name}</span>
                </CardTitle>
                <Badge
                  variant={
                    module.status === 'running'
                      ? 'default'
                      : module.status === 'stopped'
                        ? 'destructive'
                        : 'secondary'
                  }
                >
                  {module.status === 'running'
                    ? '运行中'
                    : module.status === 'stopped'
                      ? '已停止'
                      : '开发中'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {module.description}
                </p>

                <div className="flex items-center justify-between text-sm">
                  <span>版本: {module.version}</span>
                  <span className="text-muted-foreground">
                    更新: {module.lastUpdate}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  {module.status === 'running' ? (
                    <Button size="sm" variant="outline">
                      <Square className="h-3 w-3 mr-1" />
                      停止
                    </Button>
                  ) : module.status === 'stopped' ? (
                    <Button size="sm">
                      <Play className="h-3 w-3 mr-1" />
                      启动
                    </Button>
                  ) : (
                    <Button size="sm" variant="secondary" disabled>
                      开发中
                    </Button>
                  )}

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0">
                        <span className="sr-only">打开菜单</span>
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => {
                          setSelectedModule(module.id);
                          setShowConfig(true);
                        }}
                      >
                        <Settings className="mr-2 h-4 w-4" />
                        配置
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => {
                          setSelectedModule(module.id);
                          setShowDependencies(true);
                        }}
                      >
                        <GitBranch className="mr-2 h-4 w-4" />
                        依赖管理
                      </DropdownMenuItem>
                      <DropdownMenuItem>查看日志</DropdownMenuItem>
                      <DropdownMenuItem>删除模块</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </CardContent>
          </Card>
          ))
        )}
      </div>

      {/* 模块统计 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总模块数</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{moduleStats.total}</div>
            <p className="text-xs text-muted-foreground">已安装模块</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">运行中</CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{moduleStats.running}</div>
            <p className="text-xs text-muted-foreground">正常运行</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已停止</CardTitle>
            <Square className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{moduleStats.stopped}</div>
            <p className="text-xs text-muted-foreground">需要启动</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">开发中</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{moduleStats.developing}</div>
            <p className="text-xs text-muted-foreground">测试阶段</p>
          </CardContent>
        </Card>
      </div>

      {/* 模块配置对话框 */}
      <ModuleConfiguration
        moduleId={selectedModule}
        isOpen={showConfig}
        onClose={() => {
          setShowConfig(false);
          setSelectedModule(null);
        }}
      />

      {/* 依赖管理对话框 */}
      <DependencyManager
        moduleId={selectedModule}
        isOpen={showDependencies}
        onClose={() => {
          setShowDependencies(false);
          setSelectedModule(null);
        }}
      />

      {/* 导入导出对话框 */}
      <ModuleImportExport
        isOpen={showImportExport}
        onClose={() => setShowImportExport(false)}
        onModuleImported={handleModuleImported}
      />
    </div>
  );
}
