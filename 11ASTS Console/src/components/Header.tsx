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
import { useSystemStore } from '@/store'
import { Bell, User, Settings, LogOut, Power, PowerOff } from 'lucide-react'

export function Header() {
  const { 
    isSystemRunning, 
    emergencyStop, 
    currentUser, 
    notifications, 
    setSystemRunning, 
    triggerEmergencyStop,
    markNotificationRead 
  } = useSystemStore()
  
  const unreadCount = notifications.filter(n => !n.read).length

  const handleSystemToggle = () => {
    if (isSystemRunning) {
      triggerEmergencyStop()
    } else {
      setSystemRunning(true)
    }
  }

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold">ASTS Console</h1>
          <Badge 
            variant={isSystemRunning ? 'default' : 'destructive'}
            className={isSystemRunning ? 'bg-green-500' : 'bg-red-500'}
          >
            {isSystemRunning ? '运行中' : '已停止'}
          </Badge>
        </div>
        
        <div className="ml-auto flex items-center space-x-4">
          {/* 系统控制按钮 */}
          <Button
            variant={isSystemRunning ? 'destructive' : 'default'}
            size="sm"
            onClick={handleSystemToggle}
            className="flex items-center space-x-2"
          >
            {isSystemRunning ? (
              <>
                <PowerOff className="h-4 w-4" />
                <span>紧急停止</span>
              </>
            ) : (
              <>
                <Power className="h-4 w-4" />
                <span>启动系统</span>
              </>
            )}
          </Button>
          
          {/* 通知 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="relative">
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs"
                  >
                    {unreadCount}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>通知</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {notifications.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground">
                  暂无通知
                </div>
              ) : (
                notifications.slice(0, 5).map((notification) => (
                  <DropdownMenuItem
                    key={notification.id}
                    className="flex flex-col items-start p-4 cursor-pointer"
                    onClick={() => markNotificationRead(notification.id)}
                  >
                    <div className="flex items-center space-x-2 w-full">
                      <Badge 
                        variant={notification.type === 'error' ? 'destructive' : 'default'}
                        className="text-xs"
                      >
                        {notification.type}
                      </Badge>
                      {!notification.read && (
                        <div className="h-2 w-2 bg-blue-500 rounded-full" />
                      )}
                    </div>
                    <div className="font-medium">{notification.title}</div>
                    <div className="text-sm text-muted-foreground">
                      {notification.message}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {notification.timestamp.toLocaleString()}
                    </div>
                  </DropdownMenuItem>
                ))
              )}
            </DropdownMenuContent>
          </DropdownMenu>
          
          {/* 用户菜单 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="flex items-center space-x-2">
                <User className="h-4 w-4" />
                <span>{currentUser?.username || '未登录'}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>我的账户</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <Settings className="mr-2 h-4 w-4" />
                <span>设置</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <LogOut className="mr-2 h-4 w-4" />
                <span>退出登录</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}