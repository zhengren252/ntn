import { useCallback, useEffect } from 'react'
import { useReviewStore } from '@/store/review-store'
import type { User } from '@/store/review-store'

// 用户认证hook
export const useAuth = () => {
  const {
    currentUser,
    isLoading,
    error,
    setCurrentUser,
    setLoading,
    setError,
    clearError
  } = useReviewStore()

  // 登录
  const login = useCallback(async (username: string, password: string) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // 模拟用户验证
      const mockUsers: Record<string, User> = {
        'admin': {
          id: 'USER-001',
          username: 'admin',
          email: 'admin@reviewguard.com',
          role: 'admin',
          status: 'active',
          created_at: '2024-01-01T00:00:00Z',
          last_login: new Date().toISOString()
        },
        'reviewer': {
          id: 'USER-002',
          username: 'reviewer',
          email: 'reviewer@reviewguard.com',
          role: 'reviewer',
          status: 'active',
          created_at: '2024-01-01T00:00:00Z',
          last_login: new Date().toISOString()
        },
        'analyst': {
          id: 'USER-003',
          username: 'analyst',
          email: 'analyst@reviewguard.com',
          role: 'analyst',
          status: 'active',
          created_at: '2024-01-01T00:00:00Z',
          last_login: new Date().toISOString()
        }
      }
      
      const user = mockUsers[username]
      // 在生产环境中，这应该通过API验证
    const validPassword = process.env.NEXT_PUBLIC_DEMO_PASSWORD || 'demo123';
    if (!user || password !== validPassword) {
        throw new Error('用户名或密码错误')
      }
      
      if (user.status !== 'active') {
        throw new Error('账户已被禁用')
      }
      
      // 保存用户信息
      setCurrentUser(user)
      
      // 保存到localStorage
      localStorage.setItem('reviewguard_user', JSON.stringify(user))
      localStorage.setItem('reviewguard_token', `token_${user.id}_${Date.now()}`)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [setCurrentUser, setLoading, setError])

  // 登出
  const logout = useCallback(async () => {
    setLoading(true)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 清除用户信息
      setCurrentUser(null)
      
      // 清除localStorage
      localStorage.removeItem('reviewguard_user')
      localStorage.removeItem('reviewguard_token')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '登出失败')
    } finally {
      setLoading(false)
    }
  }, [setCurrentUser, setLoading, setError])

  // 检查认证状态
  const checkAuth = useCallback(async () => {
    const savedUser = localStorage.getItem('reviewguard_user')
    const savedToken = localStorage.getItem('reviewguard_token')
    
    if (savedUser && savedToken) {
      try {
        const user = JSON.parse(savedUser) as User
        
        // 验证token有效性（模拟）
        const tokenParts = savedToken.split('_')
        const tokenTime = parseInt(tokenParts[2])
        const now = Date.now()
        
        // token 24小时过期
        if (now - tokenTime > 24 * 60 * 60 * 1000) {
          throw new Error('登录已过期')
        }
        
        setCurrentUser(user)
      } catch {
        // token无效，清除本地存储
        localStorage.removeItem('reviewguard_user')
        localStorage.removeItem('reviewguard_token')
        setError('登录已过期，请重新登录')
      }
    }
  }, [setCurrentUser, setError])

  // 权限检查
  const hasPermission = useCallback((permission: string): boolean => {
    if (!currentUser) return false
    
    const rolePermissions: Record<string, string[]> = {
      admin: [
        'review:read',
        'review:write',
        'review:approve',
        'review:reject',
        'review:defer',
        'review:batch',
        'config:read',
        'config:write',
        'user:read',
        'user:write',
        'monitor:read',
        'history:read'
      ],
      reviewer: [
        'review:read',
        'review:approve',
        'review:reject',
        'review:defer',
        'history:read',
        'monitor:read'
      ],
      analyst: [
        'review:read',
        'history:read',
        'monitor:read'
      ]
    }
    
    const userPermissions = rolePermissions[currentUser.role] || []
    return userPermissions.includes(permission)
  }, [currentUser])

  // 角色检查
  const hasRole = useCallback((role: string): boolean => {
    return currentUser?.role === role
  }, [currentUser])

  // 是否为管理员
  const isAdmin = useCallback((): boolean => {
    return hasRole('admin')
  }, [hasRole])

  // 是否为审核员
  const isReviewer = useCallback((): boolean => {
    return hasRole('reviewer') || hasRole('admin')
  }, [hasRole])

  // 是否为分析师
  const isAnalyst = useCallback((): boolean => {
    return hasRole('analyst') || hasRole('reviewer') || hasRole('admin')
  }, [hasRole])

  // 更新用户信息
  const updateProfile = useCallback(async (updates: Partial<User>) => {
    if (!currentUser) return
    
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      const updatedUser = {
        ...currentUser,
        ...updates,
        updated_at: new Date().toISOString()
      }
      
      setCurrentUser(updatedUser)
      localStorage.setItem('reviewguard_user', JSON.stringify(updatedUser))
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [currentUser, setCurrentUser, setLoading, setError])

  // 修改密码
  const changePassword = useCallback(async (oldPassword: string, newPassword: string) => {
    setLoading(true)
    setError(null)
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // 验证旧密码（模拟）
      // 在生产环境中，这应该通过API验证
    const validPassword = process.env.NEXT_PUBLIC_DEMO_PASSWORD || 'demo123';
    if (oldPassword !== validPassword) {
        throw new Error('原密码错误')
      }
      
      if (newPassword.length < 6) {
        throw new Error('新密码长度不能少于6位')
      }
      
      // 密码修改成功后，重新生成token
      if (currentUser) {
        const newToken = `token_${currentUser.id}_${Date.now()}`
        localStorage.setItem('reviewguard_token', newToken)
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '密码修改失败')
      throw err
    } finally {
      setLoading(false)
    }
  }, [currentUser, setLoading, setError])

  // 初始化时检查认证状态
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return {
    // 状态
    user: currentUser,
    isAuthenticated: !!currentUser,
    isLoading,
    error,
    
    // 认证操作
    login,
    logout,
    checkAuth,
    
    // 权限检查
    hasPermission,
    hasRole,
    isAdmin,
    isReviewer,
    isAnalyst,
    
    // 用户管理
    updateProfile,
    changePassword,
    
    // 工具
    clearError
  }
}

// 权限保护hook
export const useRequireAuth = (requiredPermission?: string) => {
  const { isAuthenticated, hasPermission, user } = useAuth()
  
  const canAccess = isAuthenticated && (!requiredPermission || hasPermission(requiredPermission))
  
  return {
    canAccess,
    isAuthenticated,
    user,
    hasPermission
  }
}

// 角色保护hook
export const useRequireRole = (requiredRole: string) => {
  const { isAuthenticated, hasRole, user } = useAuth()
  
  const canAccess = isAuthenticated && hasRole(requiredRole)
  
  return {
    canAccess,
    isAuthenticated,
    user,
    hasRole
  }
}