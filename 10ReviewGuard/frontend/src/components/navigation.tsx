'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { usePendingReviews, useCurrentUser, useSystemStatus } from '@/hooks/use-reviews'
import { cn } from '@/lib/utils'
import { 
  LayoutDashboard, 
  FileText, 
  History, 
  Settings, 
  User, 
  Bell, 
  Menu, 
  X,
  AlertCircle,
  CheckCircle
} from 'lucide-react'

const navigationItems = [
  {
    name: '工作台',
    href: '/dashboard',
    icon: LayoutDashboard,
    description: '审核工作台概览'
  },
  {
    name: '待审核',
    href: '/reviews/pending',
    icon: FileText,
    description: '待处理的策略审核',
    showBadge: true
  },
  {
    name: '审核历史',
    href: '/reviews/history',
    icon: History,
    description: '已完成的审核记录'
  },
  {
    name: '规则配置',
    href: '/config/rules',
    icon: Settings,
    description: '审核规则和参数设置'
  },
  {
    name: '用户管理',
    href: '/config/users',
    icon: User,
    description: '用户权限和角色管理'
  },
  {
    name: '系统监控',
    href: '/monitor/status',
    icon: CheckCircle,
    description: '系统状态和性能监控'
  }
]

export function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const pathname = usePathname()
  const { data: currentUser } = useCurrentUser()
  const { data: pendingData } = usePendingReviews()
  const { data: systemStatus } = useSystemStatus()
  
  const pendingCount = pendingData?.total || 0
  
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo和主导航 */}
          <div className="flex">
            {/* Logo */}
            <div className="flex-shrink-0 flex items-center">
              <Link href="/dashboard" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <FileText className="h-5 w-5 text-white" />
                </div>
                <span className="text-xl font-bold text-gray-900">ReviewGuard</span>
              </Link>
            </div>
            
            {/* 桌面端导航 */}
            <div className="hidden md:ml-6 md:flex md:space-x-8">
              {navigationItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href || 
                  (item.href !== '/dashboard' && pathname.startsWith(item.href))
                
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    )}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    <span>{item.name}</span>
                    {item.showBadge && pendingCount > 0 && (
                      <Badge className="ml-2 bg-red-500 text-white">
                        {pendingCount}
                      </Badge>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
          
          {/* 右侧操作区 */}
          <div className="flex items-center space-x-4">
            {/* 系统状态指示器 */}
            {systemStatus && (
              <div className="hidden md:flex items-center space-x-2">
                {systemStatus.status === 'healthy' ? (
                  <div className="flex items-center space-x-1 text-green-600">
                    <CheckCircle className="h-4 w-4" />
                    <span className="text-sm">系统正常</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-1 text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm">系统异常</span>
                  </div>
                )}
              </div>
            )}
            
            {/* 通知按钮 */}
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="h-4 w-4" />
              {pendingCount > 0 && (
                <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full"></span>
              )}
            </Button>
            
            {/* 用户信息 */}
            {currentUser && (
              <div className="hidden md:flex items-center space-x-2">
                <div className="flex items-center space-x-2 px-3 py-2 rounded-md bg-gray-50">
                  <User className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700">
                    {currentUser.username}
                  </span>
                  <Badge variant="secondary">
                    {currentUser.role}
                  </Badge>
                </div>
              </div>
            )}
            
            {/* 移动端菜单按钮 */}
            <div className="md:hidden">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              >
                {isMobileMenuOpen ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Menu className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
      
      {/* 移动端导航菜单 */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="pt-2 pb-3 space-y-1 bg-white border-t border-gray-200">
            {navigationItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href || 
                (item.href !== '/dashboard' && pathname.startsWith(item.href))
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center px-4 py-2 text-base font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 border-r-4 border-blue-500 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  <span>{item.name}</span>
                  {item.showBadge && pendingCount > 0 && (
                    <Badge className="ml-auto bg-red-500 text-white">
                      {pendingCount}
                    </Badge>
                  )}
                </Link>
              )
            })}
            
            {/* 移动端用户信息 */}
            {currentUser && (
              <div className="px-4 py-3 border-t border-gray-200">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
                      <User className="h-4 w-4 text-gray-600" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      {currentUser.username}
                    </div>
                    <div className="text-sm text-gray-500">
                      {currentUser.role}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}