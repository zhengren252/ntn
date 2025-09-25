'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 数据缓存时间
            staleTime: 60 * 1000, // 1分钟
            // 缓存保持时间
            gcTime: 10 * 60 * 1000, // 10分钟
            // 重试配置
            retry: (failureCount, error) => {
              // 对于认证错误不重试
              if (error instanceof Error && error.message.includes('401')) {
                return false
              }
              // 最多重试2次
              return failureCount < 2
            },
            // 重新获取配置
            refetchOnWindowFocus: false,
            refetchOnReconnect: true,
          },
          mutations: {
            // 变更重试配置
            retry: 1,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}