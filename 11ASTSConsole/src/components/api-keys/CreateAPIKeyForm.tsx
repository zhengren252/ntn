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

const createAPIKeySchema = z.object({
  name: z.string().min(1, '名称不能为空').max(100, '名称不能超过100个字符'),
  provider: z.string().min(1, '请选择提供商'),
  key: z.string().min(1, 'API密钥不能为空'),
  description: z.string().optional(),
  is_active: z.boolean().default(true),
});

// 使用 z.input / z.output 对齐 react-hook-form 的 TFieldValues 与 TTransformedValues
type CreateAPIKeyFormInput = z.input<typeof createAPIKeySchema>;
type CreateAPIKeyFormOutput = z.output<typeof createAPIKeySchema>;

interface CreateAPIKeyFormProps {
  onSubmit: (data: CreateAPIKeyFormOutput) => Promise<void>;
  onCancel: () => void;
}

const API_PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'binance', label: 'Binance' },
  { value: 'yahoo_finance', label: 'Yahoo Finance' },
  { value: 'alpha_vantage', label: 'Alpha Vantage' },
  { value: 'custom', label: '自定义' },
];

export function CreateAPIKeyForm({ onSubmit, onCancel }: CreateAPIKeyFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<CreateAPIKeyFormInput, any, CreateAPIKeyFormOutput>({
    resolver: zodResolver(createAPIKeySchema),
    defaultValues: {
      name: '',
      provider: '',
      key: '',
      description: '',
      is_active: true,
    },
  });

  const handleSubmit = async (data: CreateAPIKeyFormOutput) => {
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
          name="key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>API密钥 *</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="输入API密钥"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                API密钥将被安全加密存储
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
                  是否立即启用这个API密钥
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
            {isSubmitting ? '创建中...' : '创建'}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  );
}