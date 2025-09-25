'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { BarChart3, TrendingUp, Activity, Download, Plus } from 'lucide-react';
import TradingHistory from '@/features/trading-replay/components/TradingHistory';
import PerformanceAnalysis from '@/features/trading-replay/components/PerformanceAnalysis';
import TradingViewChart from '@/features/trading-replay/components/TradingViewChart';
import TradeDetails from '@/features/trading-replay/components/TradeDetails';
import { useExportReplay } from '@/hooks/useApi';
import { TradingRecord as Trade } from '@/lib/types';

export default function ReplayPage() {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [isTradeDetailsOpen, setIsTradeDetailsOpen] = useState(false);
  const [selectedSymbol] = useState('BTCUSDT');

  const exportReplay = useExportReplay();

  const handleTradeSelect = (trade: Trade) => {
    setSelectedTrade(trade);
    setIsTradeDetailsOpen(true);
  };

  const handleExportReport = () => {
    exportReplay.mutate({ 
      replayId: 'current-session',
      format: 'csv', 
      includeMetadata: true
    });
  };

  // 模拟交易数据
  const mockTrades: Trade[] = [
    {
      id: '1',
      symbol: 'BTCUSDT',
      type: 'buy' as const,
      price: 45234.56,
      quantity: 0.1,
      timestamp: new Date().toISOString(),
      status: 'executed' as const,
      pnl: 234.56,
      strategy: {
        name: 'RSI突破策略',
        version: 'v1.2.0',
        signal: 'BUY',
        confidence: 0.85
      },
      marketCondition: {
        volatility: 0.15,
        trend: 'bullish',
        volume: 'high',
        liquidity: 'good'
      }
    },
    {
      id: '2',
      symbol: 'ETHUSDT',
      type: 'sell' as const,
      price: 2834.12,
      quantity: 1.5,
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      status: 'completed' as const,
      pnl: -123.45,
      strategy: {
        name: 'MACD背离策略',
        version: 'v2.1.0',
        signal: 'SELL',
        confidence: 0.78
      },
      marketCondition: {
        volatility: 0.22,
        trend: 'bearish',
        volume: 'medium',
        liquidity: 'fair'
      }
    },
  ];

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">高级交易复盘</h2>
          <p className="text-muted-foreground">
            深度分析交易表现，优化策略决策
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={handleExportReport}>
            <Download className="mr-2 h-4 w-4" />
            导出报告
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            新建复盘
          </Button>
        </div>
      </div>

      {/* 概览卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总交易次数</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,234</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+12%</span> 较上月
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总盈亏</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">+$12,345</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+8.5%</span> 收益率
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">胜率</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">68.5%</div>
            <Badge variant="default" className="mt-1">
              优秀
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">夏普比率</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.85</div>
            <Badge variant="default" className="mt-1">
              优秀
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* 主要内容区域 */}
      <Tabs defaultValue="chart" className="space-y-4">
        <TabsList>
          <TabsTrigger value="chart">图表分析</TabsTrigger>
          <TabsTrigger value="history">交易历史</TabsTrigger>
          <TabsTrigger value="performance">性能分析</TabsTrigger>
        </TabsList>

        <TabsContent value="chart" className="space-y-4">
          <TradingViewChart
            symbol={selectedSymbol}
            trades={mockTrades}
            onTradeClick={handleTradeSelect}
          />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <TradingHistory onTradeSelect={handleTradeSelect} />
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <PerformanceAnalysis />
        </TabsContent>
      </Tabs>

      {/* 交易详情弹窗 */}
      <TradeDetails
        trade={selectedTrade}
        isOpen={isTradeDetailsOpen}
        onClose={() => setIsTradeDetailsOpen(false)}
      />
    </div>
  );
}
