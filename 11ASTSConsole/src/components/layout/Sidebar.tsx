'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  LayoutDashboard,
  FileCheck,
  Bot,
  Monitor,
  BarChart3,
  DollarSign,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bell,
} from 'lucide-react';
import { useSystemStore } from '@/store';

interface SidebarProps {
  className?: string;
}

const navigation = [
  {
    name: '仪表盘',
    href: '/dashboard',
    icon: LayoutDashboard,
    description: '系统概览和实时监控',
  },
  {
    name: '人工审核中心',
    href: '/review',
    icon: FileCheck,
    description: '策略审核和风险评估',
  },
  {
    name: 'AI策略实验室',
    href: '/ai-lab',
    icon: Bot,
    description: 'AI辅助策略开发',
  },
  {
    name: '系统监控',
    href: '/monitoring',
    icon: Monitor,
    description: '模块状态和性能监控',
  },
  {
    name: '交易复盘',
    href: '/replay',
    icon: BarChart3,
    description: '历史交易分析',
  },
  {
    name: 'API成本中心',
    href: '/api-cost',
    icon: DollarSign,
    description: 'API使用成本管理',
  },
  {
    name: '风控演习',
    href: '/risk-rehearsal',
    icon: Shield,
    description: '风险场景模拟',
  },
  {
    name: '模块管理',
    href: '/modules',
    icon: Settings,
    description: '系统模块配置',
  },
];

export const Sidebar = ({ className }: SidebarProps) => {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const notifications = useSystemStore((state) => state.notifications);
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div
      className={cn(
        'flex flex-col bg-white border-r border-gray-200 transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        {!collapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">NT</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                ASTS Console
              </h1>
              <p className="text-xs text-gray-500">NeuroTrade Nexus</p>
            </div>
          </div>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* 通知区域 */}
      {!collapsed && unreadCount > 0 && (
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center space-x-2 text-sm text-orange-600">
            <Bell className="h-4 w-4" />
            <span>{unreadCount} 条未读通知</span>
          </div>
        </div>
      )}

      {/* 导航菜单 */}
      <nav className="flex-1 p-4 space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link key={item.name} href={item.href}>
              <div
                className={cn(
                  'flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <Icon
                  className={cn(
                    'h-5 w-5 flex-shrink-0',
                    isActive ? 'text-blue-700' : 'text-gray-400'
                  )}
                />

                {!collapsed && (
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{item.name}</div>
                    <div className="text-xs text-gray-500 truncate">
                      {item.description}
                    </div>
                  </div>
                )}

                {/* 活动指示器 */}
                {isActive && (
                  <div className="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0" />
                )}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* 底部状态 */}
      <div className="p-4 border-t border-gray-200">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>系统版本</span>
              <span>v1.0.0</span>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>运行时间</span>
              <span>2天3小时</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
          </div>
        )}
      </div>
    </div>
  );
};
