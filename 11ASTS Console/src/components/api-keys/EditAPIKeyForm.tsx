'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Input,
} from '@/components/ui/input';
import {
  Textarea,
} from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Button,
} from '@/components/ui/button';
import {
  Switch,
} from '@/components/ui/switch';
import { DialogFooter } from '@/components/ui/dialog';
import { APIKey } from '@/lib/types';

const editAPIKeySchema = z.object({
  name: z.string().min(1, '名称不能为空').max(100, '名称不能超过100个字符'),
  provider: z.string().min(1, '请选择提供商'),
  description: z.string().optional(),
  is_active: z.boolean(),
});

type EditAPIKeyFormData = z.infer<typeof editAPIKeySchema>;

interface EditAPIKeyFormProps {
  apiKey: APIKey;
  onSubmit: (data: EditAPIKeyFormData) => Promise<void>;
  onCancel: () => void;
}

const API_PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'binance', label: 'Binance' },
  { value: 'yahoo_finance', label: 'Yahoo Finance' },
  { value: 'alpha_vantage', label: 'Alpha Vantage' },
  { value: 'custom', label: '自定义' },
];

export function EditAPIKeyForm({ apiKey, onSubmit, onCancel }: EditAPIKeyFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<EditAPIKeyFormData>({
    resolver: zodResolver(editAPIKeySchema),
    defaultValues: {
      name: apiKey.name,
      provider: apiKey.provider,
      description: apiKey.description || '',
      is_active: apiKey.is_active,
    },
  });

  const handleSubmit = async (data: EditAPIKeyFormData) => {
    setIsSubmitting(true);
    try {
      await onSubmit(data);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>名称 *</FormLabel>
              <FormControl>
                <Input
                  placeholder="输入API密钥名称"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                为这个API密钥设置一个易于识别的名称
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="provider"
          render={({ field }) => (
            <FormItem>
              <FormLabel>提供商 *</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="选择API提供商" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {API_PROVIDERS.map((provider) => (
                    <SelectItem key={provider.value} value={provider.value}>
                      {provider.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                选择API密钥的提供商类型
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>描述</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="输入API密钥的描述信息（可选）"
                  className="resize-none"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                可选的描述信息，帮助您记住这个密钥的用途
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <FormLabel className="text-base">
                  启用状态
                </FormLabel>
                <FormDescription>
                  是否启用这个API密钥
                </FormDescription>
              </div>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
            </FormItem>
          )}
        />

        <div className="bg-muted/50 p-4 rounded-lg">
          <p className="text-sm text-muted-foreground">
            <strong>注意：</strong> 出于安全考虑，API密钥本身无法在编辑时修改。如需更换密钥，请删除当前密钥并创建新的密钥。
          </p>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            取消
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? '更新中...' : '更新'}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  );
}