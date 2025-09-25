'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';
import { APIKey, APIKeyCreate, APIKeyUpdate } from '@/lib/types';

// API密钥相关的API调用函数
const apiKeysApi = {
  // 获取所有API密钥
  getAll: async (): Promise<APIKey[]> => {
    const response = await apiClient.get('/api/v1/keys');
    return response.data.data || [];
  },

  // 根据ID获取单个API密钥
  getById: async (id: string): Promise<APIKey> => {
    const response = await apiClient.get(`/api/v1/keys/${id}`);
    return response.data.data;
  },

  // 创建新的API密钥
  create: async (data: APIKeyCreate): Promise<APIKey> => {
    const response = await apiClient.post('/api/v1/keys', data);
    return response.data.data;
  },

  // 更新API密钥
  update: async (id: string, data: APIKeyUpdate): Promise<APIKey> => {
    const response = await apiClient.put(`/api/v1/keys/${id}`, data);
    return response.data.data;
  },

  // 删除API密钥
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/keys/${id}`);
  },

  // 测试API密钥
  test: async (id: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post(`/api/v1/keys/${id}/test`);
    return response.data;
  },

  // 健康检查
  healthCheck: async (): Promise<{ status: string; timestamp: string }> => {
    const response = await apiClient.get('/api/v1/keys/health');
    return response.data;
  },
};

// 主要的useAPIKeys Hook
export function useAPIKeys() {
  const queryClient = useQueryClient();

  // 获取所有API密钥
  const {
    data: apiKeys = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: apiKeysApi.getAll,
    staleTime: 5 * 60 * 1000, // 5分钟
    retry: 2,
  });

  // 创建API密钥的mutation
  const createMutation = useMutation({
    mutationFn: apiKeysApi.create,
    onSuccess: (newApiKey) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      toast.success('API密钥创建成功');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'API密钥创建失败';
      toast.error(message);
    },
  });

  // 更新API密钥的mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: APIKeyUpdate }) =>
      apiKeysApi.update(id, data),
    onSuccess: (updatedApiKey) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      toast.success('API密钥更新成功');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'API密钥更新失败';
      toast.error(message);
    },
  });

  // 删除API密钥的mutation
  const deleteMutation = useMutation({
    mutationFn: apiKeysApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      toast.success('API密钥删除成功');
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'API密钥删除失败';
      toast.error(message);
    },
  });

  // 测试API密钥的mutation
  const testMutation = useMutation({
    mutationFn: apiKeysApi.test,
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message || 'API密钥测试成功');
      } else {
        toast.error(result.message || 'API密钥测试失败');
      }
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || 'API密钥测试失败';
      toast.error(message);
    },
  });

  return {
    // 数据
    apiKeys,
    isLoading,
    error,

    // 操作函数
    createAPIKey: createMutation.mutateAsync,
    updateAPIKey: updateMutation.mutateAsync,
    deleteAPIKey: deleteMutation.mutateAsync,
    testAPIKey: testMutation.mutateAsync,
    refetch,

    // 加载状态
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isTesting: testMutation.isPending,
  };
}

// 获取单个API密钥的Hook
export function useAPIKey(id: string) {
  return useQuery({
    queryKey: ['apiKey', id],
    queryFn: () => apiKeysApi.getById(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5分钟
    retry: 2,
  });
}

// 健康检查Hook
export function useAPIKeysHealth() {
  return useQuery({
    queryKey: ['apiKeysHealth'],
    queryFn: apiKeysApi.healthCheck,
    refetchInterval: 30 * 1000, // 每30秒检查一次
    retry: 1,
  });
}

// 本地状态管理Hook（用于UI状态）
export function useAPIKeysLocalState() {
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterProvider, setFilterProvider] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');

  // 清除选择
  const clearSelection = () => setSelectedKeys([]);

  // 切换选择
  const toggleSelection = (id: string) => {
    setSelectedKeys(prev => 
      prev.includes(id) 
        ? prev.filter(keyId => keyId !== id)
        : [...prev, id]
    );
  };

  // 全选/取消全选
  const toggleSelectAll = (allIds: string[]) => {
    setSelectedKeys(prev => 
      prev.length === allIds.length ? [] : allIds
    );
  };

  // 过滤API密钥
  const filterAPIKeys = (apiKeys: APIKey[]) => {
    return apiKeys.filter(key => {
      // 搜索过滤
      const matchesSearch = searchTerm === '' || 
        key.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        key.provider.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (key.description && key.description.toLowerCase().includes(searchTerm.toLowerCase()));

      // 提供商过滤
      const matchesProvider = filterProvider === 'all' || key.provider === filterProvider;

      // 状态过滤
      const matchesStatus = filterStatus === 'all' || 
        (filterStatus === 'active' && key.is_active) ||
        (filterStatus === 'inactive' && !key.is_active);

      return matchesSearch && matchesProvider && matchesStatus;
    });
  };

  return {
    // 选择状态
    selectedKeys,
    setSelectedKeys,
    clearSelection,
    toggleSelection,
    toggleSelectAll,

    // 过滤状态
    searchTerm,
    setSearchTerm,
    filterProvider,
    setFilterProvider,
    filterStatus,
    setFilterStatus,
    filterAPIKeys,
  };
}