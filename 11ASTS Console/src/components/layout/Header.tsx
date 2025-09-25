'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Bell,
  User,
  Settings,
  LogOut,
  Moon,
  Sun,
  Search,
  HelpCircle
} from 'lucide-react'
import { useSystemStore } from '@/store'
import { cn } from '@/lib/utils'

interface HeaderProps {
  className?: string
}

export const Header = ({ className }: HeaderProps) => {
  const [isDarkMode, setIsDarkMode] = useState(false)
  const { notifications, currentUser, markNotificationRead, clearNotifications } = useSystemStore()
  const unreadCount = notifications.filter(n => !n.read).length

  const handleNotificationClick = (notificationId: string) => {
    markNotificationRead(notificationId)
  }

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode)
    // 这里可以添加实际的主题切换逻辑
    document.documentElement.classList.toggle('dark')
  }

  return (
    <header className={cn(
      "flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200",
      className
    )}>
      {/* 左侧：搜索栏 */}
      <div className="flex items-center space-x-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索功能、策略或数据..."
            className="pl-10 pr-4 py-2 w-80 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* 右侧：操作按钮 */}
      <div className="flex items-center space-x-4">
        {/* 帮助按钮 */}
        <Button variant="ghost" size="sm">
          <HelpCircle className="h-4 w-4" />
        </Button>

        {/* 主题切换 */}
        <Button variant="ghost" size="sm" onClick={toggleDarkMode}>
          {isDarkMode ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>

        {/* 通知中心 */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <Badge 
                  variant="destructive" 
                  className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center text-xs p-0"
                >
                  {unreadCount > 99 ? '99+' : unreadCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>通知中心</span>
              {notifications.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearNotifications}
                  className="text-xs"
                >
                  清空全部
                </Button>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                暂无通知
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto">
                {notifications.slice(0, 10).map((notification) => (
                  <DropdownMenuItem
                    key={notification.id}
                    className={cn(
                      "flex flex-col items-start p-3 cursor-pointer",
                      !notification.read && "bg-blue-50"
                    )}
                    onClick={() => handleNotificationClick(notification.id)}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-medium text-sm">{notification.title}</span>
                      <Badge 
                        variant={notification.type === 'error' ? 'destructive' : 
                                notification.type === 'warning' ? 'secondary' : 'default'}
                        className="text-xs"
                      >
                        {notification.type}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">{notification.message}</p>
                    <span className="text-xs text-gray-400 mt-1">
                      {notification.timestamp.toLocaleString()}
                    </span>
                  </DropdownMenuItem>
                ))}
              </div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* 用户菜单 */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
              <div className="hidden md:block text-left">
                <div className="text-sm font-medium">
                  {currentUser?.username || '未登录'}
                </div>
                <div className="text-xs text-gray-500">
                  {currentUser?.role || 'guest'}
                </div>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>我的账户</DropdownMenuLabel>
            <DropdownMenuSeparator />
            
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>个人资料</span>
            </DropdownMenuItem>
            
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>系统设置</span>
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            
            <DropdownMenuItem className="text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              <span>退出登录</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}