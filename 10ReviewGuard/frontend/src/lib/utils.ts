import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// 格式化日期
export function formatDate(date: Date | string): string {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化百分比
export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

// 格式化货币
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2
  }).format(value)
}

// 风险等级颜色映射
export function getRiskLevelColor(level: string): string {
  switch (level) {
    case 'low':
      return 'text-green-600 bg-green-50'
    case 'medium':
      return 'text-yellow-600 bg-yellow-50'
    case 'high':
      return 'text-red-600 bg-red-50'
    default:
      return 'text-gray-600 bg-gray-50'
  }
}

// 状态颜色映射
export function getStatusColor(status: string): string {
  switch (status) {
    case 'pending':
      return 'text-blue-600 bg-blue-50'
    case 'processing':
      return 'text-yellow-600 bg-yellow-50'
    case 'approved':
      return 'text-green-600 bg-green-50'
    case 'rejected':
      return 'text-red-600 bg-red-50'
    case 'deferred':
      return 'text-gray-600 bg-gray-50'
    default:
      return 'text-gray-600 bg-gray-50'
  }
}