'use client'

import { useState } from 'react'
import { AiLabStats } from '@/features/ai-lab/components/AiLabStats'
import { ChatInterface } from '@/features/ai-lab/components/ChatInterface'
import { AiLabSidebar } from '@/features/ai-lab/components/AiLabSidebar'

export default function AiLabPage() {
  const [currentSessionId, setCurrentSessionId] = useState('1')

  const handleSessionChange = (sessionId: string) => {
    setCurrentSessionId(sessionId)
  }

  const handleNewSession = () => {
    // 生成新的会话ID
    const newSessionId = `session_${Date.now()}`
    setCurrentSessionId(newSessionId)
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI策略实验室</h1>
        <p className="text-muted-foreground">
          与AI助手对话，生成和优化交易策略
        </p>
      </div>

      {/* AI助手统计 */}
      <AiLabStats />

      <div className="grid gap-6 lg:grid-cols-4">
        {/* AI对话界面 */}
        <div className="lg:col-span-3">
          <ChatInterface sessionId={currentSessionId} />
        </div>

        {/* 侧边栏 */}
        <div>
          <AiLabSidebar
            currentSessionId={currentSessionId}
            onSessionChange={handleSessionChange}
            onNewSession={handleNewSession}
          />
        </div>
      </div>
    </div>
  )
}