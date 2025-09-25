/*
 * Dashboard API fixtures for Playwright route mocking
 * Provide stable, reusable payloads for overview and chart endpoints
 */

export type OverviewResponse = {
  code: number;
  message: string;
  data: {
    totalProfit: number;
    profitChange: number;
    activeStrategies: number;
    strategiesChange: number;
    successRate: number;
    successRateChange: number;
    systemStatus: 'running' | 'stopped' | 'warning' | string;
  };
};

export type ChartResponse = {
  code: number;
  message: string;
  data: {
    timestamps: string[];
    cumulativeProfit: number[];
    dailyProfit: number[];
  };
};

export function makeOverviewResponse(partial?: Partial<OverviewResponse['data']>): OverviewResponse {
  return {
    code: 0,
    message: 'ok',
    data: {
      totalProfit: 15420.5,
      profitChange: 2.1,
      activeStrategies: 5,
      strategiesChange: 1.2,
      successRate: 94.2,
      successRateChange: 0.5,
      systemStatus: 'running',
      ...partial,
    },
  };
}

export function makeChartResponse(now: number = Date.now()): ChartResponse {
  return {
    code: 0,
    message: 'ok',
    data: {
      timestamps: [
        new Date(now - 60000).toISOString(),
        new Date(now - 30000).toISOString(),
        new Date(now).toISOString(),
      ],
      cumulativeProfit: [100, 101, 102],
      dailyProfit: [1, 0, 1],
    },
  };
}