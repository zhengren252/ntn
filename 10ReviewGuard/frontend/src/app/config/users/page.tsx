'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Switch } from '@/components/ui/switch'
import { formatDate } from '@/lib/utils'
import {
  Users,
  UserPlus,
  Edit,
  Trash2,
  Shield,
  Eye,
  Crown,
  User
} from 'lucide-react'

// 用户角色定义
type UserRole = 'admin' | 'senior_reviewer' | 'reviewer' | 'readonly'

// 用户数据类型
interface UserData {
  id: string
  username: string
  email: string
  role: UserRole
  status: 'active' | 'inactive'
  last_login: string
  created_at: string
  permissions: string[]
}

// 模拟用户数据
const mockUsers: UserData[] = [
  {
    id: '1',
    username: 'admin',
    email: 'admin@reviewguard.com',
    role: 'admin',
    status: 'active',
    last_login: new Date().toISOString(),
    created_at: '2024-01-01T00:00:00Z',
    permissions: ['all']
  },
  {
    id: '2',
    username: 'senior_reviewer_01',
    email: 'senior@reviewguard.com',
    role: 'senior_reviewer',
    status: 'active',
    last_login: new Date(Date.now() - 3600000).toISOString(),
    created_at: '2024-01-02T00:00:00Z',
    permissions: ['review_all', 'approve_high_risk', 'manage_rules']
  },
  {
    id: '3',
    username: 'reviewer_01',
    email: 'reviewer1@reviewguard.com',
    role: 'reviewer',
    status: 'active',
    last_login: new Date(Date.now() - 7200000).toISOString(),
    created_at: '2024-01-03T00:00:00Z',
    permissions: ['review_low_medium', 'view_history']
  },
  {
    id: '4',
    username: 'readonly_user',
    email: 'readonly@reviewguard.com',
    role: 'readonly',
    status: 'active',
    last_login: new Date(Date.now() - 86400000).toISOString(),
    created_at: '2024-01-04T00:00:00Z',
    permissions: ['view_only']
  }
]

// 角色配置
const roleConfig = {
  admin: {
    label: '系统管理员',
    color: 'bg-red-100 text-red-800',
    icon: <Crown className="h-4 w-4" />,
    permissions: ['系统管理', '用户管理', '规则配置', '审核操作', '数据查看']
  },
  senior_reviewer: {
    label: '高级审核员',
    color: 'bg-purple-100 text-purple-800',
    icon: <Shield className="h-4 w-4" />,
    permissions: ['高风险审核', '规则配置', '审核操作', '数据查看']
  },
  reviewer: {
    label: '审核员',
    color: 'bg-blue-100 text-blue-800',
    icon: <User className="h-4 w-4" />,
    permissions: ['低中风险审核', '数据查看']
  },
  readonly: {
    label: '只读用户',
    color: 'bg-gray-100 text-gray-800',
    icon: <Eye className="h-4 w-4" />,
    permissions: ['数据查看']
  }
}

// 用户编辑对话框组件
function UserEditDialog({ user, isOpen, onClose, onSave }: {
  user?: UserData
  isOpen: boolean
  onClose: () => void
  onSave: (userData: Partial<UserData>) => void
}) {
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    role: user?.role || 'reviewer' as UserRole,
    status: user?.status || 'active' as 'active' | 'inactive'
  })

  const handleSave = () => {
    onSave(formData)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{user ? '编辑用户' : '新增用户'}</DialogTitle>
          <DialogDescription>
            {user ? '修改用户信息和权限设置' : '创建新的用户账户'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="username" className="text-right">
              用户名
            </Label>
            <Input
              id="username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="col-span-3"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="email" className="text-right">
              邮箱
            </Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="col-span-3"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="role" className="text-right">
              角色
            </Label>
            <Select
              value={formData.role}
              onValueChange={(value: UserRole) => setFormData({ ...formData, role: value })}
            >
              <SelectTrigger className="col-span-3">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(roleConfig).map(([key, config]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center space-x-2">
                      {config.icon}
                      <span>{config.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="status" className="text-right">
              状态
            </Label>
            <div className="col-span-3 flex items-center space-x-2">
              <Switch
                id="status"
                checked={formData.status === 'active'}
                onCheckedChange={(checked) => 
                  setFormData({ ...formData, status: checked ? 'active' : 'inactive' })
                }
              />
              <Label htmlFor="status">
                {formData.status === 'active' ? '启用' : '禁用'}
              </Label>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleSave}>
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function UsersConfigPage() {
  const [users, setUsers] = useState<UserData[]>(mockUsers)
  const [editingUser, setEditingUser] = useState<UserData | undefined>()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  // 筛选用户
  const filteredUsers = users.filter(user => 
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // 角色统计
  const roleStats = users.reduce((acc, user) => {
    acc[user.role] = (acc[user.role] || 0) + 1
    return acc
  }, {} as Record<UserRole, number>)

  const handleEditUser = (user: UserData) => {
    setEditingUser(user)
    setIsDialogOpen(true)
  }

  const handleAddUser = () => {
    setEditingUser(undefined)
    setIsDialogOpen(true)
  }

  const handleSaveUser = (userData: Partial<UserData>) => {
    if (editingUser) {
      // 编辑用户
      setUsers(users.map(user => 
        user.id === editingUser.id ? { ...user, ...userData } : user
      ))
    } else {
      // 新增用户
      const newUser: UserData = {
        id: Date.now().toString(),
        username: userData.username!,
        email: userData.email!,
        role: userData.role!,
        status: userData.status!,
        last_login: '',
        created_at: new Date().toISOString(),
        permissions: roleConfig[userData.role!].permissions
      }
      setUsers([...users, newUser])
    }
  }

  const handleDeleteUser = (userId: string) => {
    setUsers(users.filter(user => user.id !== userId))
  }

  const handleToggleStatus = (userId: string) => {
    setUsers(users.map(user => 
      user.id === userId 
        ? { ...user, status: user.status === 'active' ? 'inactive' : 'active' }
        : user
    ))
  }

  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">用户管理</h1>
          <p className="text-muted-foreground">管理审核员权限和角色分配</p>
        </div>
        <Button onClick={handleAddUser}>
          <UserPlus className="h-4 w-4 mr-2" />
          新增用户
        </Button>
      </div>

      {/* 角色统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Object.entries(roleConfig).map(([role, config]) => (
          <Card key={role}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{config.label}</CardTitle>
              {config.icon}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{roleStats[role as UserRole] || 0}</div>
              <p className="text-xs text-muted-foreground">
                {config.permissions.length} 项权限
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 搜索和筛选 */}
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Input
            placeholder="搜索用户名或邮箱..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-sm"
          />
        </div>
      </div>

      {/* 用户列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Users className="h-5 w-5" />
            <span>用户列表</span>
          </CardTitle>
          <CardDescription>共 {filteredUsers.length} 个用户</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>用户信息</TableHead>
                <TableHead>角色</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>最后登录</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{user.username}</div>
                      <div className="text-sm text-muted-foreground">{user.email}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={roleConfig[user.role].color}>
                      <div className="flex items-center space-x-1">
                        {roleConfig[user.role].icon}
                        <span>{roleConfig[user.role].label}</span>
                      </div>
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={user.status === 'active'}
                        onCheckedChange={() => handleToggleStatus(user.id)}

                      />
                      <span className={user.status === 'active' ? 'text-green-600' : 'text-red-600'}>
                        {user.status === 'active' ? '启用' : '禁用'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.last_login ? formatDate(user.last_login) : '从未登录'}
                  </TableCell>
                  <TableCell>{formatDate(user.created_at)}</TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditUser(user)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.role === 'admin'}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 用户编辑对话框 */}
      <UserEditDialog
        user={editingUser}
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSave={handleSaveUser}
      />
    </div>
  )
}