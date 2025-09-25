/**
 * AI策略实验室页面组件
 * 支持动态交互和测试需求
 */

import { useEffect, useState } from 'react';

interface Message {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: number;
}

export default function AiLab() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'AI策略实验室 - ASTS Console';
  }, []);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: Date.now()
    };
    
    const currentInput = inputValue;
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);
    
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 模拟错误情况（用于测试错误处理）
      if (currentInput.includes('错误') || currentInput.includes('error')) {
        throw new Error('AI服务异常');
      }
      
      // 生成更长的AI响应内容
      let aiContent = '';
      if (currentInput.includes('RSI') || currentInput.includes('相对强弱')) {
        aiContent = 'RSI（相对强弱指数）是一个重要的技术分析指标，用于衡量价格变动的速度和幅度。当RSI超过70时通常被认为是超买信号，低于30时被认为是超卖信号。在当前市场环境下，建议结合其他指标如MACD和移动平均线来确认交易信号的有效性。';
      } else if (currentInput.includes('策略') || currentInput.includes('strategy')) {
        aiContent = `基于您的问题"${currentInput}"，我建议采用多元化的交易策略组合。首先考虑趋势跟踪策略，在明确的上升或下降趋势中表现优异；其次是均值回归策略，适用于震荡市场；最后是动量策略，可以捕捉短期价格突破。每种策略都应该配置适当的风险管理参数，包括止损点和仓位控制。`;
      } else {
        aiContent = `针对您的询问"${currentInput}"，我提供以下专业分析：当前市场呈现复杂的多重信号，建议采用谨慎的交易策略。技术面分析显示支撑位和阻力位较为明确，基本面因素也需要综合考虑。建议分批建仓，严格控制风险，并密切关注市场动态变化。`;
      }
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: aiContent,
        timestamp: Date.now()
      };
      
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      setError('AI服务暂时不可用');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div data-testid="page-ai-lab" className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI策略实验室</h1>
        <p className="text-muted-foreground">
          与AI助手对话，生成和优化交易策略
        </p>
      </div>
      
      {/* 聊天界面 */}
      <div className="chat-interface ai-chat" data-testid="ai-chat">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          {/* 消息显示区域 */}
          <div className="messages-container mb-4 space-y-3 min-h-[300px] max-h-[500px] overflow-y-auto">
            {messages.map((message) => (
              <div 
                key={message.id}
                className={`message chat-message ${message.type}-message message-${message.type} p-3 rounded-lg ${
                  message.type === 'user' 
                    ? 'bg-blue-50 ml-8' 
                    : 'bg-gray-50 mr-8 assistant-message'
                }`}
              >
                <p>{message.content}</p>
              </div>
            ))}
            {isLoading && (
               <div className="loading-message p-3 bg-gray-50 rounded-lg mr-8">
                 <p>正在思考中...</p>
               </div>
             )}
          </div>
          
          {/* 错误消息 */}
          {error && (
            <div className="error-message ai-error mb-4 p-3 bg-red-50 border border-red-200 rounded-lg" data-testid="error-message">
              <p className="text-red-600">{error}</p>
              <button 
                className="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded text-sm"
                onClick={() => setError(null)}
              >
                重试
              </button>
            </div>
          )}
          
          <div className="space-y-4">
            <textarea 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="请输入您的问题..." 
              className="w-full min-h-[100px] p-3 border rounded-md"
              disabled={isLoading}
            />
            <button 
              onClick={handleSendMessage}
              disabled={isLoading || !inputValue.trim()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
              data-testid="send-button"
            >
              {isLoading ? '发送中...' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}