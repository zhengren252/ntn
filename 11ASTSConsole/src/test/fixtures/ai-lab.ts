/*
 * AI Lab API fixtures for Playwright route mocking
 * Provide stable, reusable payloads for AI chat and strategy endpoints
 */

export type AIChatResponse = {
  code: number;
  message: string;
  data: {
    response: string;
    timestamp: number;
    conversationId: string;
  };
};

export type StrategyCodeResponse = {
  code: number;
  message: string;
  data: {
    code: string;
    language: string;
    description: string;
  };
};

export function makeAIChatResponse(userMessage?: string): AIChatResponse {
  const responses = [
    "基于当前市场分析，建议采用均线突破策略。该策略在震荡市场中表现稳定，风险可控。",
    "根据技术指标分析，当前市场呈现上升趋势，建议关注动量策略和趋势跟踪策略。",
    "市场波动性较高，建议采用网格交易策略，可以在震荡中获取稳定收益。"
  ];
  
  return {
    code: 0,
    message: 'ok',
    data: {
      response: responses[Math.floor(Math.random() * responses.length)],
      timestamp: Date.now(),
      conversationId: `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    }
  };
}

export function makeStrategyCodeResponse(): StrategyCodeResponse {
  return {
    code: 0,
    message: 'ok',
    data: {
      code: `def moving_average_strategy(data, short_window=20, long_window=50):
    """
    基于移动平均线的交易策略
    """
    data['short_ma'] = data['close'].rolling(window=short_window).mean()
    data['long_ma'] = data['close'].rolling(window=long_window).mean()
    
    # 生成交易信号
    data['signal'] = 0
    data['signal'][short_window:] = np.where(
        data['short_ma'][short_window:] > data['long_ma'][short_window:], 1, 0
    )
    
    return data`,
      language: 'python',
      description: '基于短期和长期移动平均线交叉的经典交易策略'
    }
  };
}