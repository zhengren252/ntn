'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAuditRules } from '@/hooks/useSystem'
import { formatDate, formatPercentage } from '@/lib/utils'
import { Settings, Plus, Edit, Trash2, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import type { AuditRule } from '@/store/review-store'

// 规则编辑对话框组件
function RuleEditDialog({ 
  rule, 
  isOpen, 
  onClose, 
  onSave 
}: { 
  rule?: AuditRule
  isOpen: boolean
  onClose: () => void
  onSave: (rule: AuditRule) => void
}) {
  const [formData, setFormData] = useState({
    name: rule?.name || '',
    description: rule?.description || '',
    rule_type: rule?.rule_type || 'risk_threshold',
    conditions: rule?.conditions || {
      max_risk_score: 0.8,
      min_liquidity_score: 0.3,
      max_volatility: 0.5,
      required_backtest_period: 90
    },
    actions: rule?.actions || {
      auto_reject: false,
      require_senior_approval: true,
      position_size_limit: 0.5
    },
    priority: rule?.priority || 1,
    is_active: rule?.is_active ?? true
  })
  
  if (!isOpen) return null
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      ...rule,
      ...formData,
      id: rule?.id || Date.now().toString(),
      created_at: rule?.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    onClose()
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">
            {rule ? '编辑规则' : '新建规则'}
          </h2>
          <Button variant="outline" size="sm" onClick={onClose}>
            取消
          </Button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 基本信息 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">规则名称</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border rounded-md text-sm"
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">规则类型</label>
              <select
                value={formData.rule_type}
                onChange={(e) => setFormData(prev => ({ ...prev, rule_type: e.target.value as AuditRule['rule_type'] }))}
                className="w-full px-3 py-2 border rounded-md text-sm"
              >
                <option value="risk_threshold">风险阈值</option>
                <option value="liquidity_check">流动性检查</option>
                <option value="volatility_limit">波动性限制</option>
                <option value="backtest_requirement">回测要求</option>
                <option value="position_limit">仓位限制</option>
              </select>
            </div>
          </div>
          
          <div>
            <label className="text-sm font-medium mb-2 block">规则描述</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-md text-sm"
              rows={3}
            />
          </div>
          
          {/* 条件设置 */}
          <div>
            <h3 className="text-lg font-medium mb-3">触发条件</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground">最大风险评分</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.conditions.max_risk_score as number || 0}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    conditions: {
                      ...prev.conditions,
                      max_risk_score: parseFloat(e.target.value)
                    }
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">最小流动性评分</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.conditions.min_liquidity_score as number || 0}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    conditions: {
                      ...prev.conditions,
                      min_liquidity_score: parseFloat(e.target.value)
                    }
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">最大波动率</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.conditions.max_volatility as number || 0}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    conditions: {
                      ...prev.conditions,
                      max_volatility: parseFloat(e.target.value)
                    }
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">回测周期要求(天)</label>
                <input
                  type="number"
                  min="1"
                  value={formData.conditions.required_backtest_period as number || 0}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    conditions: {
                      ...prev.conditions,
                      required_backtest_period: parseInt(e.target.value)
                    }
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
            </div>
          </div>
          
          {/* 执行动作 */}
          <div>
            <h3 className="text-lg font-medium mb-3">执行动作</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="auto_reject"
                  checked={formData.actions.auto_reject as boolean || false}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    actions: {
                      ...prev.actions,
                      auto_reject: e.target.checked
                    }
                  }))}
                  className="rounded"
                />
                <label htmlFor="auto_reject" className="text-sm">自动拒绝</label>
              </div>
              
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="require_senior_approval"
                  checked={formData.actions.require_senior_approval as boolean || false}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    actions: {
                      ...prev.actions,
                      require_senior_approval: e.target.checked
                    }
                  }))}
                  className="rounded"
                />
                <label htmlFor="require_senior_approval" className="text-sm">需要高级审核员批准</label>
              </div>
              
              <div>
                <label className="text-sm text-muted-foreground">仓位限制比例</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.actions.position_size_limit as number || 0}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    actions: {
                      ...prev.actions,
                      position_size_limit: parseFloat(e.target.value)
                    }
                  }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                />
              </div>
            </div>
          </div>
          
          {/* 其他设置 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">优先级</label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.priority}
                onChange={(e) => setFormData(prev => ({ ...prev, priority: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border rounded-md text-sm"
              />
            </div>
            <div className="flex items-center space-x-2 mt-6">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                className="rounded"
              />
              <label htmlFor="is_active" className="text-sm">启用规则</label>
            </div>
          </div>
          
          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onClose}>
              取消
            </Button>
            <Button type="submit">
              {rule ? '更新规则' : '创建规则'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RulesConfigPage() {
  const [editingRule, setEditingRule] = useState<AuditRule | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const { 
    rules, 
    isLoading, 
    error,
    createRule,
    updateRule,
    deleteRule,
    toggleRule,
    fetchRules
  } = useAuditRules()
  
  // 初始化时获取规则列表
  React.useEffect(() => {
    fetchRules()
  }, [fetchRules])
  
  const handleCreateRule = () => {
    setEditingRule(null)
    setIsDialogOpen(true)
  }
  
  const handleEditRule = (rule: AuditRule) => {
    setEditingRule(rule)
    setIsDialogOpen(true)
  }
  
  const handleSaveRule = async (rule: AuditRule) => {
    try {
      if (rule.id && rules.find(r => r.id === rule.id)) {
        // 更新现有规则
        await updateRule(rule.id, rule)
      } else {
        // 创建新规则
        await createRule(rule)
      }
      setEditingRule(null)
      setIsDialogOpen(false)
    } catch (error) {
      console.error('保存规则失败:', error)
    }
  }
  
  const handleDeleteRule = async (ruleId: string) => {
    if (window.confirm('确定要删除这个规则吗？此操作不可撤销。')) {
      try {
        await deleteRule(ruleId)
      } catch (error) {
        console.error('删除规则失败:', error)
      }
    }
  }
  
  const handleToggleRule = async (ruleId: string) => {
    try {
      await toggleRule(ruleId)
    } catch (error) {
      console.error('切换规则状态失败:', error)
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-medium">加载中...</div>
          <div className="text-sm text-muted-foreground mt-2">正在获取审核规则</div>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg font-medium text-red-600">加载失败</div>
          <div className="text-sm text-muted-foreground mt-2">
            {typeof error === 'string' ? error : '无法获取审核规则'}
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">审核规则配置</h1>
          <p className="text-muted-foreground">管理策略审核的自动化规则和风险参数</p>
        </div>
        <Button onClick={handleCreateRule} className="flex items-center space-x-2">
          <Plus className="h-4 w-4" />
          <span>新建规则</span>
        </Button>
      </div>
      
      {/* 规则统计 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总规则数</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{rules.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">启用规则</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {rules.filter(rule => rule.is_active).length}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">禁用规则</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {rules.filter(rule => !rule.is_active).length}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">自动拒绝规则</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {rules.filter(rule => rule.actions?.auto_reject).length}
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* 规则列表 */}
      <Card>
        <CardHeader>
          <CardTitle>规则列表</CardTitle>
          <CardDescription>
            当前配置的所有审核规则，按优先级排序
          </CardDescription>
        </CardHeader>
        <CardContent>
          {rules.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>规则名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>触发条件</TableHead>
                  <TableHead>执行动作</TableHead>
                  <TableHead>更新时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules
                  .sort((a, b) => a.priority - b.priority)
                  .map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{rule.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {rule.description}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {rule.rule_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Badge 
                            className={rule.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
                          >
                            {rule.is_active ? '启用' : '禁用'}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleRule(rule.id)}
                          >
                            {rule.is_active ? '禁用' : '启用'}
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{rule.priority}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm space-y-1">
                          {Boolean(rule.conditions.max_risk_score) && (
                            <div>风险 ≤ {formatPercentage(rule.conditions.max_risk_score as number)}</div>
                          )}
                          {Boolean(rule.conditions.min_liquidity_score) && (
                            <div>流动性 ≥ {formatPercentage(rule.conditions.min_liquidity_score as number)}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm space-y-1">
                          {Boolean(rule.actions.auto_reject) && (
                            <Badge variant="destructive">自动拒绝</Badge>
                          )}
                          {Boolean(rule.actions.require_senior_approval) && (
                            <Badge variant="secondary">高级审核</Badge>
                          )}
                          {Boolean(rule.actions.position_size_limit) && (rule.actions.position_size_limit as number) < 1 && (
                            <div>仓位限制: {formatPercentage(rule.actions.position_size_limit as number)}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {formatDate(rule.updated_at)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditRule(rule as AuditRule)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteRule(rule.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <div className="text-muted-foreground">暂无审核规则</div>
              <div className="text-sm text-muted-foreground mt-2">
                点击上方按钮创建第一个规则
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* 规则编辑对话框 */}
      <RuleEditDialog
        rule={editingRule || undefined}
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSave={handleSaveRule}
      />
    </div>
  )
}