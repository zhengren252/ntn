'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useLogin } from '@/hooks/use-reviews'
import { useReviewStore } from '@/store/review-store'
import { Shield, Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  
  const { mutate: login, isPending } = useLogin()
  const setCurrentUser = useReviewStore(state => state.setCurrentUser)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.username || !formData.password) {
      setError('请输入用户名和密码')
      return
    }

    login(formData, {
      onSuccess: (data) => {
        setCurrentUser(data.user)
        router.push('/dashboard')
      },
      onError: (error: unknown) => {
        setError(error instanceof Error ? error.message : '登录失败，请检查用户名和密码')
      }
    })
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (error) setError('') // 清除错误信息
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* 头部 */}
        <div className="text-center">
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-100">
            <Shield className="h-8 w-8 text-blue-600" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            ReviewGuard
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            人工审核模组 - 智能安全阀
          </p>
        </div>

        {/* 登录表单 */}
        <Card>
          <CardHeader>
            <CardTitle>用户登录</CardTitle>
            <CardDescription>
              请输入您的凭据以访问审核系统
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* 错误提示 */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* 用户名输入 */}
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="请输入用户名"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  disabled={isPending}
                  className="w-full"
                  autoComplete="username"
                />
              </div>

              {/* 密码输入 */}
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="请输入密码"
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    disabled={isPending}
                    className="w-full pr-10"
                    autoComplete="current-password"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={isPending}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-gray-400" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-400" />
                    )}
                  </Button>
                </div>
              </div>

              {/* 登录按钮 */}
              <Button
                type="submit"
                className="w-full"
                disabled={isPending || !formData.username || !formData.password}
              >
                {isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    登录中...
                  </>
                ) : (
                  '登录'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* 演示账户信息 */}
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-blue-800">演示账户</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2 text-sm text-blue-700">
              <div className="flex justify-between">
                <span>管理员:</span>
                <span className="font-mono">admin / admin123</span>
              </div>
              <div className="flex justify-between">
                <span>高级审核员:</span>
                <span className="font-mono">senior / senior123</span>
              </div>
              <div className="flex justify-between">
                <span>审核员:</span>
                <span className="font-mono">reviewer / review123</span>
              </div>
              <div className="flex justify-between">
                <span>只读用户:</span>
                <span className="font-mono">readonly / readonly123</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 系统信息 */}
        <div className="text-center text-xs text-gray-500">
          <p>ReviewGuard v1.0.0 - NeuroTrade Nexus 交易系统</p>
          <p className="mt-1">© 2024 智能安全审核模组</p>
        </div>
      </div>
    </div>
  )
}