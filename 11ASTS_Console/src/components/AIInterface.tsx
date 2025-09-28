import React, { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Send, 
  Bot, 
  User, 
  Sparkles, 
  TrendingUp, 
  BarChart3, 
  Brain, 
  Lightbulb, 
  Download, 
  Copy, 
  RefreshCw, 
  Settings, 
  MessageSquare, 
  Zap, 
  Target, 
  AlertCircle, 
  CheckCircle
} from 'lucide-react'
import { useAIChat, useAIStrategyGenerate } from '@/hooks/useApi'
import { cn } from '@/lib/utils'

interface GeneratedStrategy {
  name?: string
  description?: string
  expectedReturn?: number
  maxDrawdown?: number
  riskLevel?: string
}

interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: string
  metadata?: {
    confidence?: number
    sources?: string[]
    suggestions?: string[]
  }
}

interface StrategyGenerationParams {
  marketType: string
  riskLevel: string
  timeframe: string
  targetReturn: number
  maxDrawdown: number
  description: string
}

interface AIInterfaceProps {
  className?: string
}

export const AIInterface: React.FC<AIInterfaceProps> = ({ className }) => {
  // 聊天相关状态
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'ai',
      content: '您好！我是ASTS智能交易助手。我可以帮您分析市场、生成交易策略、解答问题。请问有什么可以帮助您的吗？',
      timestamp: new Date().toISOString(),
      metadata: {
        confidence: 100
      }
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // 策略生成相关状态
  const [strategyParams, setStrategyParams] = useState<StrategyGenerationParams>({
    marketType: 'stock',
    riskLevel: 'medium',
    timeframe: '1d',
    targetReturn: 15,
    maxDrawdown: 10,
    description: ''
  })
  const [generatedStrategy, setGeneratedStrategy] = useState<GeneratedStrategy | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  
  // API hooks
  const aiChat = useAIChat()
  const aiStrategyGenerate = useAIStrategyGenerate()
  
  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return
    
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)
    
    try {
      const response = await aiChat.mutateAsync(inputMessage)
      const responseData = response.data as { message: string; confidence?: number; sources?: string[]; suggestions?: string[] }
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: responseData.message,
        timestamp: new Date().toISOString(),
        metadata: {
          confidence: responseData.confidence || 85,
          sources: responseData.sources || [],
          suggestions: responseData.suggestions || []
        }
      }
      
      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: '抱歉，我遇到了一些问题。请稍后再试。',
        timestamp: new Date().toISOString(),
        metadata: {
          confidence: 0
        }
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }
  
  const handleGenerateStrategy = async () => {
    setIsGenerating(true)
    
    try {
      const response = await aiStrategyGenerate.mutateAsync(strategyParams)
      setGeneratedStrategy(response.data as GeneratedStrategy)
    } catch (error) {
      console.error('策略生成失败:', error)
    } finally {
      setIsGenerating(false)
    }
  }
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // 这里可以添加toast提示
  }
  
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  const quickQuestions = [
    '当前市场趋势如何？',
    '推荐一些低风险策略',
    '分析AAPL的技术指标',
    '如何优化现有策略？',
    '市场波动率分析',
    '风险管理建议'
  ]
  
  return (
    <div className={cn('space-y-6', className)}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Brain className="h-6 w-6 text-blue-500" />
              <div>
                <CardTitle className="text-xl font-semibold">AI智能助手</CardTitle>
                <CardDescription>基于大语言模型的智能交易分析与策略生成</CardDescription>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className="text-green-600 border-green-200">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                在线
              </Badge>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>
      
      <Tabs defaultValue="chat" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="chat" className="flex items-center space-x-2">
            <MessageSquare className="h-4 w-4" />
            <span>智能对话</span>
          </TabsTrigger>
          <TabsTrigger value="strategy" className="flex items-center space-x-2">
            <Sparkles className="h-4 w-4" />
            <span>策略生成</span>
          </TabsTrigger>
          <TabsTrigger value="analysis" className="flex items-center space-x-2">
            <BarChart3 className="h-4 w-4" />
            <span>市场分析</span>
          </TabsTrigger>
        </TabsList>
        
        {/* 智能对话面板 */}
        <TabsContent value="chat" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* 聊天区域 */}
            <div className="lg:col-span-3">
              <Card className="h-[600px] flex flex-col">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold flex items-center">
                    <Bot className="h-5 w-5 mr-2 text-blue-500" />
                    智能对话
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  {/* 消息列表 */}
                  <ScrollArea className="flex-1 pr-4">
                    <div className="space-y-4">
                      {messages.map((message) => (
                        <div key={message.id} className={cn(
                          'flex',
                          message.type === 'user' ? 'justify-end' : 'justify-start'
                        )}>
                          <div className={cn(
                            'max-w-[80%] rounded-lg p-3',
                            message.type === 'user' 
                              ? 'bg-blue-500 text-white' 
                              : 'bg-gray-100 text-gray-900'
                          )}>
                            <div className="flex items-start space-x-2">
                              {message.type === 'ai' && (
                                <Bot className="h-4 w-4 mt-0.5 text-blue-500" />
                              )}
                              {message.type === 'user' && (
                                <User className="h-4 w-4 mt-0.5" />
                              )}
                              <div className="flex-1">
                                <div className="text-sm">{message.content}</div>
                                <div className="flex items-center justify-between mt-2">
                                  <div className="text-xs opacity-70">
                                    {formatTimestamp(message.timestamp)}
                                  </div>
                                  {message.type === 'ai' && (
                                    <div className="flex items-center space-x-2">
                                      {message.metadata?.confidence && (
                                        <div className="text-xs opacity-70">
                                          置信度: {message.metadata.confidence}%
                                        </div>
                                      )}
                                      <Button 
                                        variant="ghost" 
                                        size="sm" 
                                        className="h-6 w-6 p-0"
                                        onClick={() => copyToClipboard(message.content)}
                                      >
                                        <Copy className="h-3 w-3" />
                                      </Button>
                                    </div>
                                  )}
                                </div>
                                
                                {/* AI消息的建议 */}
                                {message.type === 'ai' && message.metadata?.suggestions && message.metadata.suggestions.length > 0 && (
                                  <div className="mt-2 space-y-1">
                                    <div className="text-xs opacity-70">相关建议:</div>
                                    {message.metadata.suggestions.map((suggestion, index) => (
                                      <Button
                                        key={index}
                                        variant="outline"
                                        size="sm"
                                        className="text-xs h-6 mr-1 mb-1"
                                        onClick={() => setInputMessage(suggestion)}
                                      >
                                        {suggestion}
                                      </Button>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                      
                      {/* 正在输入指示器 */}
                      {isTyping && (
                        <div className="flex justify-start">
                          <div className="bg-gray-100 rounded-lg p-3 max-w-[80%]">
                            <div className="flex items-center space-x-2">
                              <Bot className="h-4 w-4 text-blue-500" />
                              <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <div ref={messagesEndRef} />
                    </div>
                  </ScrollArea>
                  
                  {/* 输入区域 */}
                  <div className="mt-4 space-y-3">
                    <div className="flex space-x-2">
                      <Input
                        placeholder="输入您的问题..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        className="flex-1"
                      />
                      <Button 
                        onClick={handleSendMessage}
                        disabled={!inputMessage.trim() || isTyping}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* 快捷操作面板 */}
            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">快捷问题</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {quickQuestions.map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        className="w-full text-left justify-start text-xs h-8"
                        onClick={() => setInputMessage(question)}
                      >
                        <Lightbulb className="h-3 w-3 mr-2" />
                        {question}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">AI状态</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span>模型状态</span>
                      <Badge variant="outline" className="text-green-600">
                        正常
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span>响应时间</span>
                      <span className="text-sm text-gray-500">1.2s</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span>今日对话</span>
                      <span className="text-sm text-gray-500">23次</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>
        
        {/* 策略生成面板 */}
        <TabsContent value="strategy" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 参数配置 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center">
                  <Sparkles className="h-5 w-5 mr-2 text-purple-500" />
                  策略生成配置
                </CardTitle>
                <CardDescription>配置参数以生成个性化交易策略</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="market-type">市场类型</Label>
                    <Select value={strategyParams.marketType} onValueChange={(value) => 
                      setStrategyParams(prev => ({ ...prev, marketType: value }))
                    }>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="stock">股票</SelectItem>
                        <SelectItem value="forex">外汇</SelectItem>
                        <SelectItem value="crypto">加密货币</SelectItem>
                        <SelectItem value="commodity">商品</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="risk-level">风险等级</Label>
                    <Select value={strategyParams.riskLevel} onValueChange={(value) => 
                      setStrategyParams(prev => ({ ...prev, riskLevel: value }))
                    }>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">低风险</SelectItem>
                        <SelectItem value="medium">中等风险</SelectItem>
                        <SelectItem value="high">高风险</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="timeframe">时间周期</Label>
                    <Select value={strategyParams.timeframe} onValueChange={(value) => 
                      setStrategyParams(prev => ({ ...prev, timeframe: value }))
                    }>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1m">1分钟</SelectItem>
                        <SelectItem value="5m">5分钟</SelectItem>
                        <SelectItem value="1h">1小时</SelectItem>
                        <SelectItem value="1d">1天</SelectItem>
                        <SelectItem value="1w">1周</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="target-return">目标收益率 (%)</Label>
                    <Input
                      id="target-return"
                      type="number"
                      value={strategyParams.targetReturn}
                      onChange={(e) => setStrategyParams(prev => ({ 
                        ...prev, 
                        targetReturn: parseFloat(e.target.value) || 0 
                      }))}
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="max-drawdown">最大回撤 (%)</Label>
                  <Input
                    id="max-drawdown"
                    type="number"
                    value={strategyParams.maxDrawdown}
                    onChange={(e) => setStrategyParams(prev => ({ 
                      ...prev, 
                      maxDrawdown: parseFloat(e.target.value) || 0 
                    }))}
                  />
                </div>
                
                <div>
                  <Label htmlFor="description">策略描述</Label>
                  <Textarea
                    id="description"
                    placeholder="描述您希望的策略特点和要求..."
                    value={strategyParams.description}
                    onChange={(e) => setStrategyParams(prev => ({ 
                      ...prev, 
                      description: e.target.value 
                    }))}
                    rows={3}
                  />
                </div>
                
                <Button 
                  onClick={handleGenerateStrategy}
                  disabled={isGenerating}
                  className="w-full"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-2" />
                      生成策略
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
            
            {/* 生成结果 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center">
                  <Target className="h-5 w-5 mr-2 text-green-500" />
                  生成结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isGenerating ? (
                  <div className="space-y-4">
                    <div className="text-center py-8">
                      <RefreshCw className="h-8 w-8 mx-auto mb-4 animate-spin text-blue-500" />
                      <div className="text-lg font-medium mb-2">AI正在生成策略...</div>
                      <div className="text-sm text-gray-500">这可能需要几秒钟时间</div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>分析市场数据</span>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>优化参数</span>
                        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                      </div>
                      <div className="flex justify-between text-sm text-gray-400">
                        <span>生成策略代码</span>
                        <AlertCircle className="h-4 w-4" />
                      </div>
                    </div>
                  </div>
                ) : generatedStrategy ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center space-x-2 mb-2">
                        <CheckCircle className="h-5 w-5 text-green-500" />
                        <span className="font-semibold text-green-800">策略生成成功</span>
                      </div>
                      <div className="text-sm text-green-700">
                        基于您的参数，AI已生成一个优化的交易策略
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div>
                        <Label className="text-sm font-medium">策略名称</Label>
                        <div className="mt-1 text-sm font-mono bg-gray-50 p-2 rounded">
                          {generatedStrategy.name || 'AI智能策略v1.0'}
                        </div>
                      </div>
                      
                      <div>
                        <Label className="text-sm font-medium">预期表现</Label>
                        <div className="mt-1 grid grid-cols-2 gap-2 text-sm">
                          <div className="bg-gray-50 p-2 rounded text-center">
                            <div className="font-bold text-green-600">+18.5%</div>
                            <div className="text-xs text-gray-500">年化收益</div>
                          </div>
                          <div className="bg-gray-50 p-2 rounded text-center">
                            <div className="font-bold text-red-600">-7.2%</div>
                            <div className="text-xs text-gray-500">最大回撤</div>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <Label className="text-sm font-medium">策略描述</Label>
                        <div className="mt-1 text-sm bg-gray-50 p-3 rounded">
                          基于机器学习的动量策略，结合技术指标和市场情绪分析，
                          适用于中等风险偏好的投资者。策略采用自适应止损和动态仓位管理。
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex space-x-2">
                      <Button variant="outline" size="sm" className="flex-1">
                        <Download className="h-4 w-4 mr-2" />
                        下载策略
                      </Button>
                      <Button size="sm" className="flex-1">
                        <CheckCircle className="h-4 w-4 mr-2" />
                        部署策略
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Sparkles className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <div className="text-lg font-medium mb-2">等待生成策略</div>
                    <div className="text-sm">配置参数后点击生成按钮</div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        {/* 市场分析面板 */}
        <TabsContent value="analysis" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 分析工具 */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center">
                  <BarChart3 className="h-5 w-5 mr-2 text-blue-500" />
                  AI市场分析
                </CardTitle>
                <CardDescription>基于AI的实时市场分析和预测</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* 市场概览 */}
                  <div>
                    <h4 className="font-semibold mb-3">市场概览</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-3 bg-green-50 rounded">
                        <div className="text-lg font-bold text-green-600">看涨</div>
                        <div className="text-xs text-gray-500">整体趋势</div>
                      </div>
                      <div className="text-center p-3 bg-blue-50 rounded">
                        <div className="text-lg font-bold text-blue-600">中等</div>
                        <div className="text-xs text-gray-500">波动率</div>
                      </div>
                      <div className="text-center p-3 bg-yellow-50 rounded">
                        <div className="text-lg font-bold text-yellow-600">谨慎</div>
                        <div className="text-xs text-gray-500">情绪指数</div>
                      </div>
                      <div className="text-center p-3 bg-purple-50 rounded">
                        <div className="text-lg font-bold text-purple-600">85%</div>
                        <div className="text-xs text-gray-500">AI信心</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* 热门标的分析 */}
                  <div>
                    <h4 className="font-semibold mb-3">热门标的分析</h4>
                    <div className="space-y-3">
                      {[
                        { symbol: 'AAPL', prediction: '上涨', confidence: 78, reason: '技术突破，基本面强劲' },
                        { symbol: 'TSLA', prediction: '震荡', confidence: 65, reason: '等待财报，市场观望' },
                        { symbol: 'NVDA', prediction: '上涨', confidence: 82, reason: 'AI概念持续火热' }
                      ].map((item, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                          <div className="flex items-center space-x-3">
                            <span className="font-mono font-bold">{item.symbol}</span>
                            <Badge className={cn(
                              item.prediction === '上涨' ? 'bg-green-100 text-green-800' :
                              item.prediction === '下跌' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            )}>
                              {item.prediction}
                            </Badge>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium">{item.confidence}% 置信度</div>
                            <div className="text-xs text-gray-500">{item.reason}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* AI洞察 */}
                  <div>
                    <h4 className="font-semibold mb-3">AI洞察</h4>
                    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="flex items-start space-x-2">
                        <Brain className="h-5 w-5 text-blue-500 mt-0.5" />
                        <div>
                          <div className="font-medium text-blue-800 mb-1">市场机会识别</div>
                          <div className="text-sm text-blue-700">
                            AI检测到科技股板块出现技术性回调后的反弹信号，
                            建议关注FAANG股票的短期交易机会。同时，
                            美联储政策预期变化可能为金融股带来上涨动力。
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* 分析历史 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">分析历史</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { time: '14:30', type: '技术分析', accuracy: 85 },
                    { time: '13:45', type: '情绪分析', accuracy: 92 },
                    { time: '12:20', type: '基本面分析', accuracy: 78 },
                    { time: '11:15', type: '宏观分析', accuracy: 88 }
                  ].map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded bg-gray-50">
                      <div>
                        <div className="text-sm font-medium">{item.type}</div>
                        <div className="text-xs text-gray-500">{item.time}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-green-600">{item.accuracy}%</div>
                        <div className="text-xs text-gray-500">准确率</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default AIInterface