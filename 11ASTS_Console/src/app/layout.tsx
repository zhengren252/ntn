import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ASTS Console - NeuroTrade Nexus',
  description: '前端管理界面 - 智能交易系统控制台',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <Providers>
          <div className="flex h-screen bg-gray-50">
            {/* 侧边栏 */}
            <Sidebar />
            
            {/* 主内容区域 */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* 顶部导航 */}
              <Header />
              
              {/* 页面内容 */}
              <main className="flex-1 overflow-y-auto">
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  )
}