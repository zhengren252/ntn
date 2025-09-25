/*
 * Trading Replay API fixtures for Playwright route mocking
 * Provide stable, reusable payloads for trading history and chart endpoints
 */

export type TradeRecord = {
  id: string;
  symbol: string;
  type: 'buy' | 'sell';
  price: number;
  quantity: number;
  timestamp: string;
  strategyName: string;
  pnl: number;
  status: 'completed' | 'pending' | 'cancelled';
};

export type TradingHistoryResponse = {
  code: number;
  message: string;
  data: {
    trades: TradeRecord[];
    total: number;
    page: number;
    pageSize: number;
    summary: {
      totalPnl: number;
      winRate: number;
      totalTrades: number;
    };
  };
};

export type ChartDataResponse = {
  code: number;
  message: string;
  data: {
    symbol: string;
    timeframe: string;
    candles: Array<{
      timestamp: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>;
    trades: Array<{
      timestamp: string;
      type: 'buy' | 'sell';
      price: number;
      quantity: number;
    }>;
  };
};

export function makeTradingHistoryResponse(filters?: any): TradingHistoryResponse {
  const baseTrades: TradeRecord[] = [
    {
      id: 'trade_001',
      symbol: 'BTCUSDT',
      type: 'buy',
      price: 45000,
      quantity: 0.1,
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      strategyName: '均线突破策略',
      pnl: 150.5,
      status: 'completed'
    },
    {
      id: 'trade_002',
      symbol: 'ETHUSDT',
      type: 'sell',
      price: 3200,
      quantity: 0.5,
      timestamp: new Date(Date.now() - 43200000).toISOString(),
      strategyName: '网格交易策略',
      pnl: -25.3,
      status: 'completed'
    },
    {
      id: 'trade_003',
      symbol: 'BTCUSDT',
      type: 'buy',
      price: 45200,
      quantity: 0.05,
      timestamp: new Date(Date.now() - 21600000).toISOString(),
      strategyName: '均线突破策略',
      pnl: 75.8,
      status: 'completed'
    }
  ];

  // Apply basic filtering if provided
  let filteredTrades = baseTrades;
  if (filters?.tradeType) {
    filteredTrades = filteredTrades.filter(t => t.type === filters.tradeType);
  }
  if (filters?.profitLoss === 'profit') {
    filteredTrades = filteredTrades.filter(t => t.pnl > 0);
  }
  if (filters?.profitLoss === 'loss') {
    filteredTrades = filteredTrades.filter(t => t.pnl < 0);
  }

  const totalPnl = filteredTrades.reduce((sum, trade) => sum + trade.pnl, 0);
  const winningTrades = filteredTrades.filter(t => t.pnl > 0).length;

  return {
    code: 0,
    message: 'ok',
    data: {
      trades: filteredTrades,
      total: filteredTrades.length,
      page: 1,
      pageSize: 20,
      summary: {
        totalPnl,
        winRate: filteredTrades.length > 0 ? (winningTrades / filteredTrades.length) * 100 : 0,
        totalTrades: filteredTrades.length
      }
    }
  };
}

export function makeChartDataResponse(symbol: string = 'BTCUSDT'): ChartDataResponse {
  const now = Date.now();
  const candles = [];
  const trades = [];
  
  // Generate 24 hours of hourly candles
  for (let i = 23; i >= 0; i--) {
    const timestamp = new Date(now - i * 3600000).toISOString();
    const basePrice = 45000 + Math.sin(i / 4) * 1000;
    
    candles.push({
      timestamp,
      open: basePrice + Math.random() * 100 - 50,
      high: basePrice + Math.random() * 200,
      low: basePrice - Math.random() * 200,
      close: basePrice + Math.random() * 100 - 50,
      volume: 1000 + Math.random() * 5000
    });
    
    // Add some trade markers
    if (i % 6 === 0) {
      trades.push({
        timestamp,
        type: i % 12 === 0 ? 'buy' : 'sell',
        price: basePrice,
        quantity: 0.1 + Math.random() * 0.5
      });
    }
  }

  return {
    code: 0,
    message: 'ok',
    data: {
      symbol,
      timeframe: '1h',
      candles,
      trades
    }
  };
}