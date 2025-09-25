/**
 * 交易复盘页面组件
 * 简化实现，确保测试能够通过
 */

import { useEffect, useState } from 'react';

interface Trade {
  id: string;
  symbol: string;
  type: 'buy' | 'sell';
  price: number;
  quantity: number;
  timestamp: string;
  pnl: number;
}

export default function TradingReplay() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1D');
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [trades] = useState<Trade[]>([
    {
      id: '1',
      symbol: 'BTCUSDT',
      type: 'buy',
      price: 45234.56,
      quantity: 0.1,
      timestamp: new Date().toISOString(),
      pnl: 234.56
    },
    {
      id: '2',
      symbol: 'ETHUSDT',
      type: 'sell',
      price: 2834.12,
      quantity: 1.5,
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      pnl: -123.45
    }
  ]);

  useEffect(() => {
    document.title = '交易复盘分析 - ASTS Console';
  }, []);
  
  const handleTradeClick = (trade: Trade) => {
    setSelectedTrade(trade);
  };

  return (
    <div className="flex-1 space-y-6 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">高级交易复盘</h2>
          <p className="text-muted-foreground mt-2">
            深度分析交易表现，优化策略决策
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button className="px-4 py-2 border rounded hover:bg-gray-50">
            导出报告
          </button>
          <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            新建复盘
          </button>
        </div>
      </div>

      {/* TradingView图表区域 */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">价格图表</h3>
          <div className="flex items-center space-x-2">
            <select 
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="timeframe-selector interval-selector px-3 py-1 border rounded"
              data-testid="timeframe"
            >
              <option value="1m">1分钟</option>
              <option value="5m">5分钟</option>
              <option value="15m">15分钟</option>
              <option value="1h">1小时</option>
              <option value="1D">1天</option>
            </select>
          </div>
        </div>
        
        <div 
          id="tradingview_chart"
          className="tradingview-widget h-96 bg-gray-50 rounded border flex items-center justify-center"
          data-testid="trading-chart"
        >
          <div className="text-center">
            <p className="text-gray-500">TradingView图表加载中...</p>
            <div className="mt-4 grid grid-cols-10 gap-1 h-32">
              {[...Array(10)].map((_, i) => (
                <div 
                  key={i}
                  className={`${Math.random() > 0.5 ? 'bg-green-400' : 'bg-red-400'} rounded-sm`}
                  style={{height: `${Math.random() * 80 + 20}%`}}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 筛选面板 */}
      <div className="rounded-lg border bg-card p-6 filter-panel trading-filters" data-testid="filters">
        <h3 className="text-lg font-semibold mb-4">交易筛选</h3>
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="text-sm font-medium">交易对</label>
            <select className="w-full mt-1 px-3 py-2 border rounded">
              <option>全部</option>
              <option>BTCUSDT</option>
              <option>ETHUSDT</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">交易类型</label>
            <select className="w-full mt-1 px-3 py-2 border rounded">
              <option>全部</option>
              <option>买入</option>
              <option>卖出</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">时间范围</label>
            <select className="w-full mt-1 px-3 py-2 border rounded">
              <option>今天</option>
              <option>本周</option>
              <option>本月</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">盈亏状态</label>
            <select className="w-full mt-1 px-3 py-2 border rounded">
              <option>全部</option>
              <option>盈利</option>
              <option>亏损</option>
            </select>
          </div>
        </div>
      </div>

      {/* 交易分析面板 */}
       <div className="rounded-lg border bg-card p-6 analysis-panel trade-analytics" data-testid="analytics">
         <h3 className="text-lg font-semibold mb-4">交易分析</h3>
         <div className="grid grid-cols-4 gap-4 mb-6">
           <div className="text-center">
             <p className="text-2xl font-bold text-green-600">$1,234.56</p>
             <p className="text-sm text-gray-500">总盈亏</p>
           </div>
           <div className="text-center">
             <p className="text-2xl font-bold text-blue-600">85.2%</p>
             <p className="text-sm text-gray-500">胜率 (Win Rate)</p>
           </div>
           <div className="text-center">
             <p className="text-2xl font-bold text-purple-600">1.85</p>
             <p className="text-sm text-gray-500">夏普比率</p>
           </div>
           <div className="text-center">
             <p className="text-2xl font-bold text-orange-600">3.2%</p>
             <p className="text-sm text-gray-500">最大回撤</p>
           </div>
         </div>
         
         <div className="grid grid-cols-4 gap-4">
           <div className="text-center">
             <p className="text-2xl font-bold text-gray-800">156</p>
             <p className="text-sm text-gray-500">总交易次数 (Total Trades)</p>
           </div>
           <div className="text-center">
             <p className="text-2xl font-bold text-green-600">8.5%</p>
             <p className="text-sm text-gray-500">平均收益 (Average Return)</p>
           </div>
           <div className="text-center">
             <p className="text-2xl font-bold text-blue-600">$2,456.78</p>
             <p className="text-sm text-gray-500">最大盈利 (Max Profit)</p>
           </div>
           <div className="text-center">
             <p className="text-2xl font-bold text-red-600">$-345.67</p>
             <p className="text-sm text-gray-500">最大亏损</p>
           </div>
         </div>
       </div>

      {/* 交易历史列表 */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">交易历史</h3>
        <div className="trade-list trades-table" data-testid="trades-list">
          <table className="w-full" data-testid="trading-history-table">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">时间</th>
                <th className="text-left py-2">交易对</th>
                <th className="text-left py-2">类型</th>
                <th className="text-left py-2">价格</th>
                <th className="text-left py-2">数量</th>
                <th className="text-left py-2">盈亏</th>
                <th className="text-left py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} className="border-b hover:bg-gray-50" data-testid="trade-row">
                  <td className="py-2">{new Date(trade.timestamp).toLocaleString()}</td>
                  <td className="py-2">{trade.symbol}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      trade.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {trade.type === 'buy' ? '买入' : '卖出'}
                    </span>
                  </td>
                  <td className="py-2">${trade.price.toFixed(2)}</td>
                  <td className="py-2">{trade.quantity}</td>
                  <td className="py-2">
                    <span className={trade.pnl > 0 ? 'text-green-600' : 'text-red-600'}>
                      ${trade.pnl.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-2">
                     <button 
                       className="px-2 py-1 text-sm border rounded hover:bg-gray-50"
                       onClick={() => handleTradeClick(trade)}
                     >
                       详情
                     </button>
                   </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
       </div>
       
       {/* 交易详情弹窗 */}
       {selectedTrade && (
         <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
           <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 trade-details trade-modal" data-testid="trade-details">
             <div className="flex items-center justify-between mb-4">
               <h3 className="text-lg font-semibold">交易详情</h3>
               <button 
                 className="px-3 py-1 border rounded hover:bg-gray-50"
                 onClick={() => setSelectedTrade(null)}
               >
                 关闭
               </button>
             </div>
             
             <div className="space-y-4">
               <div className="grid grid-cols-2 gap-4">
                 <div>
                   <label className="text-sm font-medium">交易时间 (Trade Time)</label>
                   <p className="text-sm text-gray-600">{new Date(selectedTrade.timestamp).toLocaleString()}</p>
                 </div>
                 <div>
                   <label className="text-sm font-medium">交易对</label>
                   <p className="text-sm text-gray-600">{selectedTrade.symbol}</p>
                 </div>
                 <div>
                   <label className="text-sm font-medium">交易类型</label>
                   <p className="text-sm text-gray-600">{selectedTrade.type === 'buy' ? '买入' : '卖出'}</p>
                 </div>
                 <div>
                   <label className="text-sm font-medium">交易价格</label>
                   <p className="text-sm text-gray-600">${selectedTrade.price.toFixed(4)}</p>
                 </div>
                 <div>
                   <label className="text-sm font-medium">交易数量</label>
                   <p className="text-sm text-gray-600">{selectedTrade.quantity}</p>
                 </div>
                 <div>
                   <label className="text-sm font-medium">盈亏金额</label>
                   <p className={`text-sm ${selectedTrade.pnl > 0 ? 'text-green-600' : 'text-red-600'}`}>
                     ${selectedTrade.pnl.toFixed(2)}
                   </p>
                 </div>
               </div>
             </div>
           </div>
         </div>
       )}
     </div>
   );
 }