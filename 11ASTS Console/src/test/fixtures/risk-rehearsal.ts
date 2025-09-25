/*
 * Risk Rehearsal API fixtures for Playwright route mocking
 * Provide stable, reusable payloads for risk rehearsal endpoints
 */

export type RehearsalScenario = {
  id: string;
  name: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high' | 'extreme';
};

export type RehearsalConfig = {
  scenarioId: string;
  duration: number;
  intensity: 'low' | 'medium' | 'high';
  parameters: Record<string, any>;
};

export type RehearsalStartResponse = {
  code: number;
  message: string;
  data: {
    rehearsalId: string;
    status: 'starting' | 'running' | 'completed' | 'failed';
    startTime: string;
    estimatedEndTime: string;
  };
};

export type RehearsalStatusResponse = {
  code: number;
  message: string;
  data: {
    rehearsalId: string;
    status: 'starting' | 'running' | 'completed' | 'failed';
    progress: number;
    currentPhase: string;
    metrics: {
      triggeredAlerts: number;
      processedEvents: number;
      responseTime: number;
    };
  };
};

export function makeRehearsalScenariosResponse(): { code: number; message: string; data: RehearsalScenario[] } {
  return {
    code: 0,
    message: 'ok',
    data: [
      {
        id: 'scenario_519',
        name: '519闪崩',
        description: '模拟2021年5月19日加密货币市场闪崩事件',
        riskLevel: 'extreme'
      },
      {
        id: 'scenario_black_monday',
        name: '黑色星期一',
        description: '模拟1987年黑色星期一股市崩盘',
        riskLevel: 'high'
      },
      {
        id: 'scenario_flash_crash',
        name: '闪电崩盘',
        description: '模拟2010年闪电崩盘事件',
        riskLevel: 'high'
      }
    ]
  };
}

export function makeRehearsalStartResponse(config: Partial<RehearsalConfig> = {}): RehearsalStartResponse {
  const rehearsalId = `rehearsal_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  const startTime = new Date().toISOString();
  const estimatedEndTime = new Date(Date.now() + (config.duration || 30) * 60000).toISOString();
  
  return {
    code: 0,
    message: 'ok',
    data: {
      rehearsalId,
      status: 'starting',
      startTime,
      estimatedEndTime
    }
  };
}

export function makeRehearsalStatusResponse(rehearsalId: string, progress: number = 0): RehearsalStatusResponse {
  return {
    code: 0,
    message: 'ok',
    data: {
      rehearsalId,
      status: progress < 100 ? 'running' : 'completed',
      progress,
      currentPhase: progress < 30 ? '初始化阶段' : progress < 70 ? '压力测试阶段' : '结果分析阶段',
      metrics: {
        triggeredAlerts: Math.floor(progress / 10),
        processedEvents: Math.floor(progress * 1.5),
        responseTime: 150 + Math.random() * 50
      }
    }
  };
}