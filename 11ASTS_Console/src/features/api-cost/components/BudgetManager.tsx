'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DollarSign,
  Plus,
  Edit,
  Trash2,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Calendar,
  Target
} from 'lucide-react'
import { useBudgetManager, useUpdateBudget } from '@/hooks/useApi'
import { toast } from 'sonner'

interface Budget {
  id: string
  name: string
  amount: number
  spent: number
  period: 'monthly' | 'quarterly' | 'yearly'
  category: string
  alertThreshold: number
  status: 'active' | 'exceeded' | 'warning'
  createdAt: string
  updatedAt: string
}

interface BudgetFormData {
  name: string
  amount: number
  period: 'monthly' | 'quarterly' | 'yearly'
  category: string
  alertThreshold: number
}

const BudgetCard = ({ budget, onEdit, onDelete }: {
  budget: Budget
  onEdit: (budget: Budget) => void
  onDelete: (id: string) => void
}) => {
  const usagePercentage = (budget.spent / budget.amount) * 100
  const isOverBudget = usagePercentage > 100
  const isNearLimit = usagePercentage >= budget.alertThreshold

  const getStatusColor = () => {
    if (isOverBudget) return 'text-red-600'
    if (isNearLimit) return 'text-yellow-600'
    return 'text-green-600'
  }

  const getStatusIcon = () => {
    if (isOverBudget) return <AlertTriangle className="h-4 w-4 text-red-600" />
    if (isNearLimit) return <AlertTriangle className="h-4 w-4 text-yellow-600" />
    return <CheckCircle className="h-4 w-4 text-green-600" />
  }

  const getStatusBadge = () => {
    if (isOverBudget) return <Badge variant="destructive">超支</Badge>
    if (isNearLimit) return <Badge variant="secondary">警告</Badge>
    return <Badge variant="default">正常</Badge>
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <CardTitle className="text-base font-medium">{budget.name}</CardTitle>
          {getStatusIcon()}
        </div>
        <div className="flex items-center space-x-2">
          {getStatusBadge()}
          <div className="flex space-x-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(budget)}
            >
              <Edit className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(budget.id)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">已使用</span>
            <span className={`font-bold ${getStatusColor()}`}>
              ${budget.spent.toFixed(2)} / ${budget.amount.toFixed(2)}
            </span>
          </div>
          
          <Progress 
            value={Math.min(usagePercentage, 100)} 
            className="h-2"
          />
          
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">
              {usagePercentage.toFixed(1)}% 已使用
            </span>
            <span className="text-gray-500">
              剩余: ${Math.max(0, budget.amount - budget.spent).toFixed(2)}
            </span>
          </div>
          
          <div className="flex items-center justify-between text-xs">
            <Badge variant="outline">{budget.category}</Badge>
            <span className="text-gray-500">
              {budget.period === 'monthly' ? '月度' :
               budget.period === 'quarterly' ? '季度' : '年度'}
            </span>
          </div>
          
          <div className="text-xs text-gray-500">
            警告阈值: {budget.alertThreshold}%
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

const BudgetForm = ({ 
  budget, 
  onSubmit, 
  onCancel 
}: {
  budget?: Budget
  onSubmit: (data: BudgetFormData) => void
  onCancel: () => void
}) => {
  const [formData, setFormData] = useState<BudgetFormData>({
    name: budget?.name || '',
    amount: budget?.amount || 0,
    period: budget?.period || 'monthly',
    category: budget?.category || '',
    alertThreshold: budget?.alertThreshold || 80
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.amount || !formData.category) {
      toast.error('请填写所有必填字段')
      return
    }
    onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">预算名称 *</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="例如：API调用预算"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="amount">预算金额 *</Label>
        <Input
          id="amount"
          type="number"
          min="0"
          step="0.01"
          value={formData.amount}
          onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
          placeholder="0.00"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="period">预算周期 *</Label>
        <Select
          value={formData.period}
          onValueChange={(value: 'monthly' | 'quarterly' | 'yearly') => 
            setFormData({ ...formData, period: value })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="monthly">月度</SelectItem>
            <SelectItem value="quarterly">季度</SelectItem>
            <SelectItem value="yearly">年度</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="category">预算类别 *</Label>
        <Select
          value={formData.category}
          onValueChange={(value) => setFormData({ ...formData, category: value })}
        >
          <SelectTrigger>
            <SelectValue placeholder="选择类别" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="API调用">API调用</SelectItem>
            <SelectItem value="数据存储">数据存储</SelectItem>
            <SelectItem value="AI服务">AI服务</SelectItem>
            <SelectItem value="基础设施">基础设施</SelectItem>
            <SelectItem value="其他">其他</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="alertThreshold">警告阈值 (%)</Label>
        <Input
          id="alertThreshold"
          type="number"
          min="1"
          max="100"
          value={formData.alertThreshold}
          onChange={(e) => setFormData({ ...formData, alertThreshold: parseInt(e.target.value) || 80 })}
        />
        <p className="text-xs text-gray-500">
          当使用率达到此百分比时发送警告
        </p>
      </div>
      
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit">
          {budget ? '更新' : '创建'}
        </Button>
      </DialogFooter>
    </form>
  )
}

export const BudgetManager = () => {
  const { data: budgetData, isLoading } = useBudgetManager()
  const { mutate: updateBudget } = useUpdateBudget()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingBudget, setEditingBudget] = useState<Budget | undefined>()

  interface BudgetResponse {
    budgets: Budget[];
  }

  // 模拟预算数据
  const budgets: Budget[] = (budgetData?.data as unknown as BudgetResponse)?.budgets || [
    {
      id: '1',
      name: 'API调用预算',
      amount: 2000,
      spent: 1247.50,
      period: 'monthly',
      category: 'API调用',
      alertThreshold: 80,
      status: 'warning',
      createdAt: '2024-01-01',
      updatedAt: '2024-01-15'
    },
    {
      id: '2',
      name: 'AI服务预算',
      amount: 500,
      spent: 324.12,
      period: 'monthly',
      category: 'AI服务',
      alertThreshold: 75,
      status: 'active',
      createdAt: '2024-01-01',
      updatedAt: '2024-01-10'
    },
    {
      id: '3',
      name: '数据存储预算',
      amount: 300,
      spent: 156.23,
      period: 'monthly',
      category: '数据存储',
      alertThreshold: 85,
      status: 'active',
      createdAt: '2024-01-01',
      updatedAt: '2024-01-12'
    }
  ]

  const handleCreateBudget = (data: BudgetFormData) => {
    // 这里应该调用API创建预算
    console.log('Creating budget:', data)
    toast.success('预算创建成功')
    setIsDialogOpen(false)
  }

  const handleUpdateBudget = (data: BudgetFormData) => {
    if (!editingBudget) return
    // 这里应该调用API更新预算
    console.log('Updating budget:', editingBudget.id, data)
    toast.success('预算更新成功')
    setIsDialogOpen(false)
    setEditingBudget(undefined)
  }

  const handleDeleteBudget = (id: string) => {
    // 这里应该调用API删除预算
    console.log('Deleting budget:', id)
    toast.success('预算删除成功')
  }

  const handleEditBudget = (budget: Budget) => {
    setEditingBudget(budget)
    setIsDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setIsDialogOpen(false)
    setEditingBudget(undefined)
  }

  const getTotalBudget = () => budgets.reduce((sum, budget) => sum + budget.amount, 0)
  const getTotalSpent = () => budgets.reduce((sum, budget) => sum + budget.spent, 0)
  const getAverageUsage = () => {
    const totalUsage = budgets.reduce((sum, budget) => sum + (budget.spent / budget.amount), 0)
    return (totalUsage / budgets.length) * 100
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
                  <div className="h-2 w-full bg-gray-200 rounded animate-pulse" />
                  <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 预算概览 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总预算</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${getTotalBudget().toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              {budgets.length} 个活跃预算
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总支出</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${getTotalSpent().toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              剩余 ${(getTotalBudget() - getTotalSpent()).toFixed(2)}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均使用率</CardTitle>
            <Target className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{getAverageUsage().toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              所有预算平均值
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 预算管理 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>预算管理</CardTitle>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  新建预算
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>
                    {editingBudget ? '编辑预算' : '新建预算'}
                  </DialogTitle>
                  <DialogDescription>
                    {editingBudget ? '修改预算设置' : '创建新的预算计划'}
                  </DialogDescription>
                </DialogHeader>
                <BudgetForm
                  budget={editingBudget}
                  onSubmit={editingBudget ? handleUpdateBudget : handleCreateBudget}
                  onCancel={handleCloseDialog}
                />
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {budgets.map((budget) => (
              <BudgetCard
                key={budget.id}
                budget={budget}
                onEdit={handleEditBudget}
                onDelete={handleDeleteBudget}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}