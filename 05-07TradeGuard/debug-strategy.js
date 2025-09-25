import request from 'supertest';
import app from './api/app.ts';

async function debugStrategyCreation() {
  const strategyData = {
    packageName: `测试策略_${Date.now()}`,
    packageType: 'momentum',
    strategyType: 'momentum',
    submittedBy: 'test_user',
    sessionId: 1,
    parameters: {
      symbol: 'BTCUSDT',
      timeframe: '1h',
      risk_level: 'medium'
    },
    riskLevel: 'medium',
    expectedReturn: 0.1,
    maxPositionSize: 10000,
    stopLossPct: 0.05,
    takeProfitPct: 0.15
  };

  console.log('发送的数据:', JSON.stringify(strategyData, null, 2));

  try {
    const response = await request(app)
      .post('/api/trader/strategy-packages')
      .send(strategyData);
    
    console.log('响应状态:', response.status);
    console.log('响应体:', JSON.stringify(response.body, null, 2));
  } catch (error) {
    console.error('请求失败:', error.message);
  }
}

debugStrategyCreation();