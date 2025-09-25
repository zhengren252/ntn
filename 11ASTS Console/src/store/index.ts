import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

// 系统状态接口
interface SystemState {
  isSystemRunning: boolean
  emergencyStop: boolean
  currentUser: User | null
  notifications: Notification[]
}

// 用户接口
interface User {
  id: string
  username: string
  role: 'trader' | 'analyst' | 'risk_manager' | 'admin'
  email: string
}

// 通知接口
interface Notification {
  id: string
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
  timestamp: Date
  read: boolean
}

// 系统状态操作接口
interface SystemActions {
  setSystemRunning: (running: boolean) => void
  triggerEmergencyStop: () => void
  setCurrentUser: (user: User | null) => void
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markNotificationRead: (id: string) => void
  clearNotifications: () => void
}

// 全局状态Store
export const useSystemStore = create<SystemState & SystemActions>()((
  devtools(
    (set, get) => ({
      // 初始状态
      isSystemRunning: false,
      emergencyStop: false,
      currentUser: null,
      notifications: [],

      // 操作方法
      setSystemRunning: (running) => {
        set({ isSystemRunning: running })
        if (running) {
          set({ emergencyStop: false })
        }
      },

      triggerEmergencyStop: () => {
        set({ 
          emergencyStop: true, 
          isSystemRunning: false 
        })
        // 添加紧急停止通知
        get().addNotification({
          type: 'error',
          title: '紧急停止',
          message: '系统已执行紧急停止操作'
        })
      },

      setCurrentUser: (user) => {
        set({ currentUser: user })
      },

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: Date.now().toString(),
          timestamp: new Date(),
          read: false
        }
        set((state) => ({
          notifications: [newNotification, ...state.notifications]
        }))
      },

      markNotificationRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map(n => 
            n.id === id ? { ...n, read: true } : n
          )
        }))
      },

      clearNotifications: () => {
        set({ notifications: [] })
      }
    }),
    {
      name: 'system-store'
    }
  )
))

// 导出类型
export type { User, Notification, SystemState, SystemActions }