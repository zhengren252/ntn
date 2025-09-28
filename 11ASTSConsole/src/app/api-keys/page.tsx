'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Key, Edit, Trash2, Eye, EyeOff, Copy, Check } from 'lucide-react';
import { toast } from 'sonner';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Button,
} from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Badge,
} from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { CreateAPIKeyForm } from '@/components/api-keys/CreateAPIKeyForm';
import { EditAPIKeyForm } from '@/components/api-keys/EditAPIKeyForm';
import { useAPIKeys } from '@/hooks/useAPIKeys';
import { APIKey } from '@/lib/types';

export default function APIKeysPage() {
  const {
    apiKeys,
    isLoading,
    error,
    refetch,
    createAPIKey,
    updateAPIKey,
    deleteAPIKey,
    testAPIKey
  } = useAPIKeys();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingKey, setEditingKey] = useState<APIKey | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set());
  const [copiedKeys, setCopiedKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateKey = async (data: any) => {
    try {
      await createAPIKey(data);
      setShowCreateDialog(false);
      toast.success('API密钥创建成功');
    } catch (error) {
      toast.error('创建API密钥失败');
    }
  };

  const handleUpdateKey = async (id: string, data: any) => {
    try {
      await updateAPIKey({ id, data });
      setEditingKey(null);
      toast.success('API密钥更新成功');
    } catch (error) {
      toast.error('更新API密钥失败');
    }
  };

  const handleDeleteKey = async (id: string) => {
    try {
      await deleteAPIKey(id);
      toast.success('API密钥删除成功');
    } catch (error) {
      toast.error('删除API密钥失败');
    }
  };

  const handleTestKey = async (id: string) => {
    try {
      const result = await testAPIKey(id);
      if (result.success) {
        toast.success('API密钥测试成功');
      } else {
        toast.error(`API密钥测试失败: ${result.message}`);
      }
    } catch (error) {
      toast.error('API密钥测试失败');
    }
  };

  const toggleKeyVisibility = (keyId: string) => {
    const newVisibleKeys = new Set(visibleKeys);
    if (newVisibleKeys.has(keyId)) {
      newVisibleKeys.delete(keyId);
    } else {
      newVisibleKeys.add(keyId);
    }
    setVisibleKeys(newVisibleKeys);
  };

  const copyToClipboard = async (text: string, keyId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      const newCopiedKeys = new Set(copiedKeys);
      newCopiedKeys.add(keyId);
      setCopiedKeys(newCopiedKeys);
      toast.success('已复制到剪贴板');
      
      // 3秒后移除复制状态
      setTimeout(() => {
        setCopiedKeys(prev => {
          const updated = new Set(prev);
          updated.delete(keyId);
          return updated;
        });
      }, 3000);
    } catch (error) {
      toast.error('复制失败');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getProviderBadgeColor = (provider: string) => {
    const colors: Record<string, string> = {
      'openai': 'bg-green-100 text-green-800',
      'binance': 'bg-yellow-100 text-yellow-800',
      'yahoo_finance': 'bg-blue-100 text-blue-800',
      'alpha_vantage': 'bg-purple-100 text-purple-800',
      'custom': 'bg-gray-100 text-gray-800'
    };
    return colors[provider] || colors['custom'];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-600 mb-4">加载API密钥失败</p>
          <Button onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API密钥管理</h1>
          <p className="text-muted-foreground mt-2">
            管理系统中使用的各种API密钥，确保安全存储和访问控制
          </p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              添加API密钥
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>创建新的API密钥</DialogTitle>
              <DialogDescription>
                添加一个新的API密钥到系统中。密钥将被安全加密存储。
              </DialogDescription>
            </DialogHeader>
            <CreateAPIKeyForm
              onSubmit={handleCreateKey}
              onCancel={() => setShowCreateDialog(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API密钥列表
          </CardTitle>
          <CardDescription>
            当前系统中配置的所有API密钥
          </CardDescription>
        </CardHeader>
        <CardContent>
          {apiKeys.length === 0 ? (
            <div className="text-center py-8">
              <Key className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground mb-4">暂无API密钥</p>
              <Button
                onClick={() => setShowCreateDialog(true)}
                className="flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                添加第一个API密钥
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>提供商</TableHead>
                  <TableHead>密钥</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>最后使用</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">
                      <div>
                        <div>{key.name}</div>
                        {key.description && (
                          <div className="text-sm text-muted-foreground">
                            {key.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getProviderBadgeColor(key.provider)}>
                        {key.provider}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2 max-w-xs">
                        <code className="text-sm bg-muted px-2 py-1 rounded truncate">
                          {visibleKeys.has(key.id) ? key.key_preview : '••••••••••••••••'}
                        </code>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleKeyVisibility(key.id)}
                        >
                          {visibleKeys.has(key.id) ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </Button>
                        {visibleKeys.has(key.id) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(key.key_preview, key.id)}
                          >
                            {copiedKeys.has(key.id) ? (
                              <Check className="h-4 w-4 text-green-600" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={key.is_active ? 'default' : 'secondary'}>
                        {key.is_active ? '活跃' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {key.last_used_at ? formatDate(key.last_used_at) : '从未使用'}
                    </TableCell>
                    <TableCell>{formatDate(key.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTestKey(key.id)}
                        >
                          测试
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingKey(key)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>确认删除</AlertDialogTitle>
                              <AlertDialogDescription>
                                确定要删除API密钥 "{key.name}" 吗？此操作无法撤销。
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDeleteKey(key.id)}
                                className="bg-red-600 hover:bg-red-700"
                              >
                                删除
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 编辑对话框 */}
      {editingKey && (
        <Dialog open={!!editingKey} onOpenChange={() => setEditingKey(null)}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>编辑API密钥</DialogTitle>
              <DialogDescription>
                修改API密钥的配置信息
              </DialogDescription>
            </DialogHeader>
            <EditAPIKeyForm
              apiKey={editingKey}
              onSubmit={(data) => handleUpdateKey(editingKey.id, data)}
              onCancel={() => setEditingKey(null)}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}