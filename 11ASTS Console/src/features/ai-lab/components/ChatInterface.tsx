'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useAiLabChat, useAiLabSession } from '@/hooks/useApi'
import { Bot, User, Send, Loader2, Copy, Download } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AnalysisData {
  [key: string]: string | number | boolean
}

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  type?: 'text' | 'strategy' | 'analysis'
  metadata?: {
    strategyCode?: string
    analysisData?: AnalysisData
  }
}

interface ChatInterfaceProps {
  sessionId: string
}

export const ChatInterface = ({ sessionId }: ChatInterfaceProps) => {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: '您好！我是AI策略助手，可以帮助您分析市场数据、生成交易策略和优化现有策略。请告诉我您需要什么帮助？',
      role: 'assistant',
      timestamp: new Date(),
      type: 'text'
    }
  ])
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatMutation = useAiLabChat()
  const { data: sessionHistory } = useAiLabSession()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (sessionHistory?.data) {
      // sessionHistory.data 只包含 { sessionId, status, createdAt }
      // 实际的消息历史需要通过其他API获取或使用本地状态
      console.log('Session info:', sessionHistory.data)
    }
  }, [sessionHistory])

  const handleSendMessage = async () => {
    if (!message.trim() || chatMutation.isPending) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: message,
      role: 'user',
      timestamp: new Date(),
      type: 'text'
    }

    setMessages(prev => [...prev, userMessage])
    setMessage('')

    try {
      const response = await chatMutation.mutateAsync({
        message: message,
        sessionId
      })

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.content,
        role: 'assistant',
        timestamp: new Date(),
        type: response.type || 'text',
        metadata: response.metadata
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('发送消息失败:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: '抱歉，发送消息时出现错误，请稍后重试。',
        role: 'assistant',
        timestamp: new Date(),
        type: 'text'
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const copyToClipboard = (content: string) => {
    navigator.clipboard.writeText(content)
  }

  const downloadStrategy = (strategyCode: string, strategyName: string) => {
    const blob = new Blob([strategyCode], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${strategyName}.py`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const renderMessage = (msg: Message) => {
    const isUser = msg.role === 'user'
    
    return (
      <div key={msg.id} className={cn(
        "flex items-start space-x-3 mb-4",
        isUser ? "justify-end" : "justify-start"
      )}>
        {!isUser && (
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
            <Bot className="h-4 w-4 text-white" />
          </div>
        )}
        
        <div className={cn(
          "max-w-[80%] rounded-lg p-3 shadow-sm",
          isUser 
            ? "bg-blue-600 text-white" 
            : "bg-white border"
        )}>
          <div className="text-sm leading-relaxed">
            {msg.content}
          </div>
          
          {/* 策略代码显示 */}
          {msg.type === 'strategy' && msg.metadata?.strategyCode && (
            <div className="mt-3 p-3 bg-gray-100 rounded border">
              <div className="flex items-center justify-between mb-2">
                <Badge variant="secondary">策略代码</Badge>
                <div className="flex space-x-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyToClipboard(msg.metadata!.strategyCode!)}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => downloadStrategy(msg.metadata!.strategyCode!, 'ai_strategy')}
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              <pre className="text-xs overflow-x-auto">
                <code>{msg.metadata.strategyCode}</code>
              </pre>
            </div>
          )}
          
          {/* 分析数据显示 */}
          {msg.type === 'analysis' && msg.metadata?.analysisData && (
            <div className="mt-3 p-3 bg-blue-50 rounded border">
              <Badge variant="outline" className="mb-2">市场分析</Badge>
              <div className="text-xs space-y-1">
                {Object.entries(msg.metadata.analysisData).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="font-medium">{key}:</span>
                    <span>{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <div className="text-xs opacity-70 mt-2">
            {msg.timestamp.toLocaleTimeString()}
          </div>
        </div>
        
        {isUser && (
          <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center flex-shrink-0">
            <User className="h-4 w-4 text-white" />
          </div>
        )}
      </div>
    )
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Bot className="h-5 w-5" />
            <span>AI策略助手</span>
          </CardTitle>
          <Badge variant="default">在线</Badge>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col">
        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto mb-4 p-4 bg-gray-50 rounded-lg">
          {messages.map(renderMessage)}
          
          {/* 加载指示器 */}
          {chatMutation.isPending && (
            <div className="flex items-start space-x-3 mb-4">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <div className="bg-white border rounded-lg p-3 shadow-sm">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-gray-600">AI正在思考...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        {/* 输入区域 */}
        <div className="flex space-x-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题或需求..."
            disabled={chatMutation.isPending}
            className="flex-1"
          />
          <Button 
            onClick={handleSendMessage}
            disabled={!message.trim() || chatMutation.isPending}
            className="flex items-center space-x-2"
          >
            <Send className="h-4 w-4" />
            <span>发送</span>
          </Button>
        </div>
        
        {/* 快速操作提示 */}
        <div className="mt-2 text-xs text-gray-500">
          提示：您可以要求AI分析市场、生成策略、优化参数等
        </div>
      </CardContent>
    </Card>
  )
}