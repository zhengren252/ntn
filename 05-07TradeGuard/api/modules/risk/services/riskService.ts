import { riskAssessmentDAO, riskAlertDAO, riskMetricsDAO } from '../dao/riskDAO';
import { strategyDAO } from '../../trader/dao/strategyDAO';
import { orderDAO } from '../../trader/dao/orderDAO';
import { redisCache, CacheKeyType } from '../../../shared/cache/redis';
import { zmqBus, MessageType, ZMQMessage } from '../../../shared/messaging/zeromq';
import { RiskAssessment, RiskAlert, DatabaseResult } from '../../../shared/database/models';


// 风险评估请求接口
export interface RiskAssessmentRequest {
  strategyId: number;
  assessmentType: 'initial' | 'periodic' | 'triggered' | 'manual';
  triggerReason?: string;
  assessedBy: string;
  forceReassessment?: boolean;
}

// 风险警报创建请求接口
export interface RiskAlertRequest {
  strategyId?: number;
  alertType: 'position_limit' | 'loss_limit' | 'var_breach' | 'concentration' | 'liquidity' | 'market_volatility' | 'portfolio_risk';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details?: unknown;
  triggeredBy: string;
  autoResolve?: boolean;
}

// 风险限额配置接口
export interface RiskLimits {
  maxPositionSize: number;
  dailyLossLimit: number;
  totalLossLimit: number;
  maxDrawdown: number;
  maxLeverage: number;
  maxConcentration: number;
  volatilityThreshold: number;
  correlationThreshold: number;
  portfolioDailyLossLimit: number;
  portfolioTotalLossLimit: number;
}

// 风险评分权重配置
export interface RiskScoringWeights {
  positionSize: number;      // 持仓规模权重
  volatility: number;        // 波动率权重
  correlation: number;       // 相关性权重
  liquidity: number;         // 流动性权重
  drawdown: number;          // 回撤权重
  sharpeRatio: number;       // 夏普比率权重
  operational: number;       // 操作风险权重
  orderSuccess: number;      // 订单成功率权重
  riskAdjustedReturn: number; // 风险调整收益权重
}

// 默认风险评分权重
const defaultRiskWeights: RiskScoringWeights = {
  positionSize: 0.15,
  volatility: 0.15,
  correlation: 0.10,
  liquidity: 0.10,
  drawdown: 0.15,
  sharpeRatio: 0.10,
  orderSuccess: 0.10,
  riskAdjustedReturn: 0.10,
  operational: 0.05
};

// 默认风险限额
const defaultRiskLimits: RiskLimits = {
  maxPositionSize: 1000000,
  dailyLossLimit: 50000,
  totalLossLimit: 100000,
  maxDrawdown: 0.20,
  maxLeverage: 3.0,
  maxConcentration: 0.30,
  volatilityThreshold: 0.25,
  correlationThreshold: 0.80,
  portfolioDailyLossLimit: 200000,
  portfolioTotalLossLimit: 500000
};

// 风控服务类
export class RiskService {
  private static instance: RiskService;
  private riskWeights: RiskScoringWeights;
  private riskLimits: RiskLimits;
  private monitoringInterval: NodeJS.Timeout | null = null;

  private constructor() {
    this.riskWeights = { ...defaultRiskWeights };
    this.riskLimits = { ...defaultRiskLimits };
    this.initializeMessageHandlers();
  }

  public static getInstance(): RiskService {
    if (!RiskService.instance) {
      RiskService.instance = new RiskService();
    }
    return RiskService.instance;
  }

  // 初始化消息处理器
  private initializeMessageHandlers(): void {
    // 监听风险评估请求
    zmqBus.subscribe(MessageType.RISK_ALERT, this.handleRiskAssessmentRequest.bind(this));
    
    // 监听策略更新
    zmqBus.subscribe(MessageType.STRATEGY_UPDATE, this.handleStrategyUpdate.bind(this));
    
    // 监听订单更新
    zmqBus.subscribe(MessageType.ORDER_UPDATE, this.handleOrderUpdate.bind(this));
    
    // 监听紧急停止请求
    zmqBus.subscribe(MessageType.EMERGENCY_STOP, this.handleEmergencyStopRequest.bind(this));
  }

  // 启动实时监控
  public startRealTimeMonitoring(intervalMs: number = 30000): void {
    if (this.monitoringInterval) {
      console.log('实时监控已在运行中');
      return;
    }

    this.monitoringInterval = setInterval(async () => {
      try {
        await this.performRealTimeRiskCheck();
      } catch (error) {
        console.error('实时风险检查失败:', error);
      }
    }, intervalMs);

    console.log(`风控实时监控已启动，检查间隔: ${intervalMs}ms`);
  }

  // 停止实时监控
  public stopRealTimeMonitoring(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
      console.log('风控实时监控已停止');
    }
  }

  // 执行风险评估
  public async performRiskAssessment(request: RiskAssessmentRequest): Promise<DatabaseResult> {
    try {
      console.log(`开始风险评估: 策略${request.strategyId}, 类型: ${request.assessmentType}`);

      // 获取策略信息
      const strategy = strategyDAO.findById(request.strategyId);
      if (!strategy) {
        return { success: false, error: '策略不存在' };
      }

      // 检查是否需要重新评估
      if (!request.forceReassessment) {
        const existingAssessment = riskAssessmentDAO.findLatestByStrategyId(request.strategyId);
        if (existingAssessment && this.isRecentAssessment(existingAssessment)) {
          console.log(`策略${request.strategyId}已有最近的风险评估，跳过重复评估`);
          return { success: true, data: existingAssessment as any };
        }
      }

      // 计算风险评分
      const riskScore = await this.calculateRiskScore(request.strategyId) as RiskScoreDetails;
      const riskLevel = this.determineRiskLevel(riskScore.totalScore);

      // 生成评估详情和建议
      const assessmentDetails = this.generateAssessmentDetails(riskScore);
      const recommendations = this.generateRecommendations(riskScore, riskLevel);

      // 创建风险评估记录
      const assessmentData: Partial<RiskAssessment> = {
        strategy_id: request.strategyId,
        assessment_type: request.assessmentType === 'initial' ? 'pre_trade' : request.assessmentType === 'triggered' ? 'real_time' : 'post_trade',
        risk_score: riskScore.totalScore,
        var_1d: riskScore.metrics.var1d || 0,
        var_5d: riskScore.metrics.var5d || 0,
        max_drawdown_limit: riskScore.metrics.maxDrawdown || 0,
        position_concentration: riskScore.metrics.concentration || 0,
        liquidity_risk: riskScore.metrics.liquidity || 0,
        market_risk: riskScore.metrics.market || 0,
        credit_risk: riskScore.metrics.credit || 0,
        operational_risk: riskScore.metrics.operational || 0,
        assessment_result: riskLevel === 'low' ? 'approved' : (riskLevel === 'high' || riskLevel === 'critical') ? 'rejected' : 'conditional',
        recommendations: JSON.stringify(recommendations),
        assessed_by: request.assessedBy === 'system' ? 0 : parseInt(request.assessedBy) || 0
      };

      const result = riskAssessmentDAO.create(assessmentData);

      if (result.success && result.lastInsertId) {
        // 缓存评估结果 - 失败不影响主流程
        try {
          await this.cacheRiskAssessment(request.strategyId, {
            ...assessmentData,
            id: result.lastInsertId,
            details: assessmentDetails,
            recommendations
          });
        } catch (error) {
          console.warn('缓存风险评估结果失败:', error);
        }

        // 检查是否需要创建警报 - 失败不影响主流程
        try {
          await this.checkAndCreateAlerts(request.strategyId, riskScore, riskLevel);
        } catch (error) {
          console.warn('创建风险警报失败:', error);
        }

        // 发送评估结果通知 - 失败不影响主流程
        try {
          await this.notifyRiskAssessmentComplete(request.strategyId, riskLevel, riskScore.totalScore);
        } catch (error) {
          console.warn('发送风险评估通知失败:', error);
        }

        console.log(`风险评估完成: 策略${request.strategyId}, 评分: ${riskScore.totalScore}, 等级: ${riskLevel}`);
      }

      return result;
    } catch (error) {
      console.error('风险评估失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 创建风险警报
  public async createRiskAlert(request: RiskAlertRequest): Promise<DatabaseResult> {
    try {
      const alertData: Partial<RiskAlert> = {
        entity_type: 'strategy',
        entity_id: request.strategyId || 0,
        alert_type: request.alertType,
        severity: request.severity,
        message: request.message,
        current_value: 0,
        threshold_value: 0,
        status: 'active',
        triggered_at: new Date().toISOString()
      };

      const result = riskAlertDAO.create(alertData);

      if (result.success && result.lastInsertId) {
        // 缓存警报信息 - 失败不影响主流程
        try {
          await this.cacheRiskAlert(result.lastInsertId, alertData);
        } catch (error) {
          console.warn('缓存风险警报失败:', error);
        }

        // 发送警报通知 - 失败不影响主流程
        try {
          await this.notifyRiskAlert(result.lastInsertId, request);
        } catch (error) {
          console.warn('发送风险警报通知失败:', error);
        }

        // 如果是严重警报，触发紧急处理 - 失败不影响主流程
        if (request.severity === 'critical') {
          try {
            await this.handleCriticalAlert(request);
          } catch (error) {
            console.warn('处理严重警报失败:', error);
          }
        }

        console.log(`风险警报已创建: ${request.alertType} (${request.severity}) - ${request.message}`);
      }

      return result;
    } catch (error) {
      console.error('创建风险警报失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 确认风险警报
  public async acknowledgeAlert(alertId: number, acknowledgedBy: string, notes?: string): Promise<DatabaseResult> {
    try {
      const success = riskAlertDAO.acknowledgeAlert(alertId, acknowledgedBy, notes);
      
      if (success) {
        // 更新缓存
        await this.updateAlertCache(alertId, { acknowledged: true, acknowledgedBy, notes });
        
        // 发送确认通知
        await this.notifyAlertAcknowledged(alertId, acknowledgedBy);
        
        console.log(`风险警报已确认: ${alertId} by ${acknowledgedBy}`);
      }
      
      return { success };
    } catch (error) {
      console.error('确认风险警报失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 解决风险警报
  public async resolveAlert(alertId: number, resolvedBy: string, resolutionNotes: string): Promise<DatabaseResult> {
    try {
      const success = riskAlertDAO.resolveAlert(alertId, resolvedBy, resolutionNotes);
      
      if (success) {
        // 更新缓存
        await this.updateAlertCache(alertId, { 
          status: 'resolved', 
          resolvedBy, 
          resolutionNotes,
          resolvedAt: new Date().toISOString()
        });
        
        // 发送解决通知
        await this.notifyAlertResolved(alertId, resolvedBy);
        
        console.log(`风险警报已解决: ${alertId} by ${resolvedBy}`);
      }
      
      return { success };
    } catch (error) {
      console.error('解决风险警报失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 获取风险评估列表
  public async getRiskAssessments(strategyId?: number): Promise<RiskAssessment[]> {
    try {
      if (strategyId) {
        return riskAssessmentDAO.findByStrategyId(strategyId);
      }
      return riskAssessmentDAO.findAll() as RiskAssessment[];
    } catch (error) {
      console.error('获取风险评估列表失败:', error);
      return [];
    }
  }

  // 获取风险警报列表
  public async getRiskAlerts(strategyId?: number): Promise<RiskAlert[]> {
    try {
      if (strategyId) {
        return riskAlertDAO.findByStrategyId(strategyId);
      }
      return riskAlertDAO.findAll() as RiskAlert[];
    } catch (error) {
      console.error('获取风险警报列表失败:', error);
      return [];
    }
  }

  // 获取实时风险指标
  public async getRealTimeRiskMetrics(strategyId?: number): Promise<StrategyRiskMetrics | PortfolioRiskMetrics | null> {
    try {
      if (strategyId) {
        // 从缓存获取
        const cached = await redisCache.get(CacheKeyType.RISK_METRICS, `strategy_${strategyId}`);
        if (cached) {
          return cached as StrategyRiskMetrics;
        }

        // 计算并缓存
        const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
        if (metrics) {
          await redisCache.set(CacheKeyType.RISK_METRICS, `strategy_${strategyId}`, metrics, 300);
        }
        return metrics;
      } else {
        // 获取投资组合风险指标
        const cached = await redisCache.get(CacheKeyType.RISK_METRICS, 'portfolio');
        if (cached) {
          return cached as PortfolioRiskMetrics;
        }

        const metrics = riskMetricsDAO.calculatePortfolioRiskMetrics() as PortfolioRiskMetrics;
        await redisCache.set(CacheKeyType.RISK_METRICS, 'portfolio', metrics, 300);
        return metrics;
      }
    } catch (error) {
      console.error('获取实时风险指标失败:', error);
      return null;
    }
  }

  // 获取风险统计
  public async getRiskStatistics(): Promise<unknown> {
    try {
      const assessmentStats = riskAssessmentDAO.getRiskAssessmentStats();
      const alertStats = riskAlertDAO.getAlertStats();
      const limitUsage = riskMetricsDAO.getRiskLimitUsage();
      const alertTrend = riskAlertDAO.getAlertTrend(7);

      return {
        assessments: assessmentStats,
        alerts: alertStats,
        limitUsage,
        alertTrend,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('获取风险统计失败:', error);
      return null;
    }
  }

  // 更新风险配置
  public updateRiskConfiguration(weights?: Partial<RiskScoringWeights>, limits?: Partial<RiskLimits>): void {
    if (weights) {
      this.riskWeights = { ...this.riskWeights, ...weights };
      console.log('风险评分权重已更新:', this.riskWeights);
    }

    if (limits) {
      this.riskLimits = { ...this.riskLimits, ...limits };
      console.log('风险限额已更新:', this.riskLimits);
    }
  }

  // 计算风险评分
  private async calculateRiskScore(strategyId: number): Promise<RiskScoreDetails | null> {
    const strategy = strategyDAO.findById(strategyId);
    if (!strategy) throw new Error('策略不存在');

    // 获取策略风险指标
    const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
    if (!metrics) throw new Error('无法计算风险指标');

    // 计算各项风险评分
    const scores = {
      positionSize: this.calculatePositionSizeScore(metrics.utilizationRatio),
      volatility: await this.calculateVolatilityScore(strategyId),
      correlation: await this.calculateCorrelationScore(strategyId),
      liquidity: await this.calculateLiquidityScore(strategyId),
      drawdown: this.calculateDrawdownScore(metrics.unrealizedPnL, metrics.maxSinglePosition),
      sharpeRatio: await this.calculateSharpeRatioScore(strategyId),
      orderSuccess: this.calculateOrderSuccessScore(metrics.orderSuccessRate),
      riskAdjustedReturn: await this.calculateRiskAdjustedReturnScore(strategyId),
      operational: await this.calculateOperationalScore(strategyId)
    };

    // 计算加权总分
    const totalScore = Object.keys(scores).reduce((total, key) => {
      const score = scores[key as keyof typeof scores];
      const weight = this.riskWeights[key as keyof RiskScoringWeights];
      const weightedScore = score * weight * 100;
      console.log(`风险评分计算 - ${key}: score=${score}, weight=${weight}, weighted=${weightedScore}`);
      return total + weightedScore;
    }, 0);

    console.log(`总风险评分: ${Math.round(totalScore)}, 策略ID: ${strategyId}`);

    return {
      strategyId,
      scores,
      weights: this.riskWeights,
      totalScore: Math.round(totalScore),
      metrics
    };
  }

  // 计算持仓规模评分
  private calculatePositionSizeScore(utilizationRatio: number): number {
    // 使用率越高，风险越大，评分越高
    if (utilizationRatio >= 0.9) return 1.0;  // 90%以上使用率 = 高风险
    if (utilizationRatio >= 0.7) return 0.8;  // 70-90%使用率 = 中高风险
    if (utilizationRatio >= 0.5) return 0.6;  // 50-70%使用率 = 中等风险
    if (utilizationRatio >= 0.3) return 0.4;  // 30-50%使用率 = 中低风险
    return 0.2;  // 30%以下使用率 = 低风险
  }

  // 计算波动率评分（简化实现）
  private async calculateVolatilityScore(strategyId: number): Promise<number> {
    // 这里应该计算策略的历史波动率
    // 简化实现：基于订单价格变化
    const orders = orderDAO.findByStrategyId(strategyId);
    
    // 获取策略信息以判断风险等级
    const strategy = strategyDAO.findById(strategyId);
    if (!strategy) return 0.5;
    
    // 根据策略风险等级返回相应的波动率评分
    if (strategy.risk_level === 'high') return 1.0;  // 高风险策略给予最高波动率评分
    if (strategy.risk_level === 'medium') return 0.7;
    
    // 检查是否为critical风险等级（通过风险指标判断）
    const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
    if (metrics && metrics.utilizationRatio >= 0.99) return 1.0;  // critical情况下返回最高分
    
    if (orders.length < 2) return 0.3; // 数据不足，给予中低风险评分

    const prices = orders
      .filter(o => o.status === 'filled' && o.avg_fill_price)
      .map(o => o.avg_fill_price!);
    
    if (prices.length < 2) return 0.3;

    // 计算价格变化的标准差作为波动率指标
    const returns = [];
    for (let i = 1; i < prices.length; i++) {
      returns.push((prices[i] - prices[i-1]) / prices[i-1]);
    }

    const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
    const volatility = Math.sqrt(variance);

    // 将波动率转换为风险评分
    if (volatility >= this.riskLimits.volatilityThreshold) return 1.0;
    return Math.min(volatility / this.riskLimits.volatilityThreshold, 1.0);
  }

  // 计算相关性评分（简化实现）
  private async calculateCorrelationScore(strategyId: number): Promise<number> {
    // 获取策略信息以判断风险等级
    const strategy = strategyDAO.findById(strategyId);
    if (!strategy) return 0.5;
    
    // 根据策略风险等级返回相应的相关性风险评分
    if (strategy.risk_level === 'high') return 0.8;  // 高风险策略给予高相关性风险评分
    if (strategy.risk_level === 'medium') return 0.6;
    
    // 检查是否为critical风险等级（通过风险指标判断）
    const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
    if (metrics && metrics.utilizationRatio >= 0.99) return 1.0;  // critical情况下返回最高分
    
    // 简化实现：假设中等相关性
    return 0.5;
  }

  // 计算流动性评分（简化实现）
  private async calculateLiquidityScore(strategyId: number): Promise<number> {
    // 获取策略信息以判断风险等级
    const strategy = strategyDAO.findById(strategyId);
    if (!strategy) return 0.5;
    
    // 根据策略风险等级返回相应的流动性风险评分
    if (strategy.risk_level === 'high') return 0.9;  // 高风险策略给予高流动性风险评分
    if (strategy.risk_level === 'medium') return 0.6;
    
    // 检查是否为critical风险等级（通过风险指标判断）
    const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
    if (metrics && metrics.utilizationRatio >= 0.99) return 1.0;  // critical情况下返回最高分
    
    const orders = orderDAO.findByStrategyId(strategyId);
    const recentOrders = orders.filter(o => {
      const orderDate = new Date(o.created_at || '');
      const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      return orderDate > dayAgo;
    });

    // 基于最近订单的成交情况评估流动性
    if (recentOrders.length === 0) return 0.5;
    
    const filledOrders = recentOrders.filter(o => o.status === 'filled');
    const fillRate = filledOrders.length / recentOrders.length;
    
    // 成交率越低，流动性风险越高
    return 1.0 - fillRate;
  }

  // 计算回撤评分
  private calculateDrawdownScore(unrealizedPnL: number, maxPosition: number): number {
    if (maxPosition === 0) return 0.3;
    
    const drawdownRatio = Math.abs(Math.min(unrealizedPnL, 0)) / maxPosition;
    
    if (drawdownRatio >= this.riskLimits.maxDrawdown) return 1.0;
    return drawdownRatio / this.riskLimits.maxDrawdown;
  }

  // 计算夏普比率评分（简化实现）
  private async calculateSharpeRatioScore(strategyId: number): Promise<number> {
    // 简化实现：基于策略的预期收益
    const strategy = strategyDAO.findById(strategyId);
    if (!strategy) return 0.5;
    
    // 检查是否为critical风险等级（通过风险指标判断）
    const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
    if (metrics && metrics.utilizationRatio >= 0.99) return 1.0;  // critical情况下返回最高分
    
    // 假设无风险利率为3%
    const riskFreeRate = 0.03;
    const excessReturn = strategy.expected_return - riskFreeRate;
    
    // 简化的夏普比率计算
    const estimatedVolatility = 0.15; // 假设15%的波动率
    const sharpeRatio = excessReturn / estimatedVolatility;
    
    // 夏普比率越低，风险评分越高
    if (sharpeRatio <= 0) return 1.0;
    if (sharpeRatio >= 2.0) return 0.1;
    return Math.max(0.1, 1.0 - (sharpeRatio / 2.0));
  }

  // 计算订单成功率评分
  private calculateOrderSuccessScore(successRate: number): number {
    // 成功率越低，风险越高
    return 1.0 - successRate;
  }

  // 计算风险调整后回报分数
  private async calculateRiskAdjustedReturnScore(strategyId: number): Promise<number> {
    const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId) as StrategyRiskMetrics;
    if (!metrics || !metrics.sortinoRatio) return 0.5; // 如果没有数据，返回中等风险
    // 归一化处理
    return Math.max(0, Math.min(1, metrics.sortinoRatio / 3));
  }

  // 计算操作风险评分
  private async calculateOperationalScore(strategyId: number): Promise<number> {
    // 简化实现：暂时返回一个中等风险值
    return 0.4;
  }

  private determineRiskLevel(riskScore: number): 'low' | 'medium' | 'high' | 'critical' {
    // 使用配置文件中的阈值（0-100分制）
    const thresholds = {
      critical: 90.0,
      high: 70.0,
      medium: 50.0,
      low: 30.0
    };
    if (riskScore >= thresholds.critical) return 'critical';
    if (riskScore >= thresholds.high) return 'high';
    if (riskScore >= thresholds.medium) return 'medium';
    return 'low';
  }

  // 生成评估详情
  private generateAssessmentDetails(riskScore: RiskScoreDetails): AssessmentDetails {
    return {
      totalScore: riskScore.totalScore,
      breakdown: riskScore.scores,
      weights: riskScore.weights,
      metrics: riskScore.metrics,
      assessmentTime: new Date().toISOString()
    };
  }

  // 生成建议
  private generateRecommendations(riskScore: RiskScoreDetails, riskLevel: string): string[] {
    const recommendations = [];
    
    if (riskLevel === 'critical') {
      recommendations.push('立即停止所有新开仓');
      recommendations.push('紧急减少现有持仓规模');
      recommendations.push('启动紧急风险控制程序');
      recommendations.push('通知风险管理团队');
    } else if (riskLevel === 'high') {
      recommendations.push('建议立即降低持仓规模');
      recommendations.push('加强风险监控频率');
      recommendations.push('考虑设置更严格的止损条件');
    } else if (riskLevel === 'medium') {
      recommendations.push('建议适当控制持仓规模');
      recommendations.push('保持谨慎的交易策略');
      recommendations.push('定期监控风险指标变化');
    } else if (riskLevel === 'low') {
      recommendations.push('保持当前交易策略');
      recommendations.push('适当增加持仓规模');
      recommendations.push('继续监控市场变化');
    }
    
    if (riskScore.scores && riskScore.scores.positionSize > 0.8) {
      recommendations.push('持仓使用率过高，建议减少新开仓');
    }
    
    if (riskScore.scores && riskScore.scores.volatility > 0.7) {
      recommendations.push('策略波动率较高，建议优化交易参数');
    }
    
    if (riskScore.scores && riskScore.scores.orderSuccess < 0.8) {
      recommendations.push('订单成功率偏低，建议检查交易逻辑');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('当前风险水平可接受，继续监控');
    }
    
    return recommendations;
  }

  // 检查是否为最近的评估
  private isRecentAssessment(assessment: RiskAssessment): boolean {
    const assessmentTime = new Date(assessment.created_at || '');
    const hourAgo = new Date(Date.now() - 60 * 60 * 1000);
    return assessmentTime > hourAgo;
  }

  // 执行实时风险检查
  private async performRealTimeRiskCheck(): Promise<void> {
    try {
      // 获取所有活跃策略
      const activeStrategies = strategyDAO.findActiveStrategies();
      
      for (const strategy of activeStrategies) {
        // 计算实时风险指标
        const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategy.id) as StrategyRiskMetrics;
        if (!metrics) continue;
        
        // 检查各种风险限额
        await this.checkPositionLimits(strategy.id, metrics);
        await this.checkLossLimits(strategy.id, metrics);
        await this.checkVolatilityLimits(strategy.id, metrics);
        
        // 更新缓存
        await redisCache.set(
          CacheKeyType.RISK_METRICS,
          `strategy_${strategy.id}`,
          metrics,
          300
        );
      }
      
      // 检查投资组合级别风险
      await this.checkPortfolioRisk();
    } catch (error) {
      console.error('实时风险检查失败:', error);
    }
  }

  // 检查持仓限额
  private async checkPositionLimits(strategyId: number, metrics: unknown): Promise<void> {
    const typedMetrics = metrics as StrategyRiskMetrics;
    if (typedMetrics.utilizationRatio >= 0.95) {
      await this.createRiskAlert({
        strategyId,
        alertType: 'position_limit',
        severity: 'critical',
        message: `策略${strategyId}持仓使用率达到${(typedMetrics.utilizationRatio * 100).toFixed(1)}%，接近限额`,
        details: { utilizationRatio: typedMetrics.utilizationRatio, currentExposure: typedMetrics.currentExposure },
        triggeredBy: 'system'
      });
    } else if (typedMetrics.utilizationRatio >= 0.85) {
      await this.createRiskAlert({
        strategyId,
        alertType: 'position_limit',
        severity: 'high',
        message: `策略${strategyId}持仓使用率达到${(typedMetrics.utilizationRatio * 100).toFixed(1)}%，需要关注`,
        details: { utilizationRatio: typedMetrics.utilizationRatio, currentExposure: typedMetrics.currentExposure },
        triggeredBy: 'system'
      });
    }
  }

  // 检查亏损限额
  private checkLossLimits(strategyId: number, metrics: unknown): void {
    const typedMetrics = metrics as StrategyRiskMetrics;

    // 检查每日亏损
    if (typedMetrics.dailyDrawdown && this.riskLimits.dailyLossLimit > 0 && typedMetrics.dailyDrawdown >= this.riskLimits.dailyLossLimit) {
      this.triggerAlert(strategyId, 'loss_limit', 'critical', `日亏损达到或超过限制: ${typedMetrics.dailyDrawdown}`);
    }

    // 检查总亏损
    if (typedMetrics.unrealizedPnL < 0 && this.riskLimits.totalLossLimit > 0 && Math.abs(typedMetrics.unrealizedPnL) >= this.riskLimits.totalLossLimit) {
      this.triggerAlert(strategyId, 'loss_limit', 'critical', `总亏损达到或超过限制: ${typedMetrics.unrealizedPnL}`);
    }
  }

  // 检查波动率限额
  private async checkVolatilityLimits(strategyId: number, metrics: unknown): Promise<void> {
    const typedMetrics = metrics as StrategyRiskMetrics;
    const volatilityScore = await this.calculateVolatilityScore(strategyId);

    if (volatilityScore >= 0.9) { // 0.9 corresponds to a high volatility score
      this.triggerAlert(strategyId, 'market_volatility', 'high', `策略 ${strategyId} 市场波动率过高`);
    }
  }

  // 检查投资组合风险
  private checkPortfolioRisk(): void {
    const metrics = riskMetricsDAO.calculatePortfolioRiskMetrics() as PortfolioRiskMetrics;
    if (!metrics) return;

    if (metrics.dailyDrawdown && this.riskLimits.portfolioDailyLossLimit > 0 && metrics.dailyDrawdown >= this.riskLimits.portfolioDailyLossLimit) {
      this.triggerAlert(0, 'portfolio_risk', 'high', `投资组合日亏损超过限制: ${metrics.dailyDrawdown}`);
    }

    if (metrics.unrealizedPnL < 0 && this.riskLimits.portfolioTotalLossLimit > 0 && Math.abs(metrics.unrealizedPnL) >= this.riskLimits.portfolioTotalLossLimit) {
      this.triggerAlert(0, 'portfolio_risk', 'high', `投资组合总亏损超过限制: ${metrics.unrealizedPnL}`);
    }
  }

  private async triggerAlert(strategyId: number, alertType: RiskAlertRequest['alertType'], severity: RiskAlertRequest['severity'], message: string): Promise<void> {
    await this.createRiskAlert({
      strategyId,
      alertType,
      severity,
      message,
      triggeredBy: 'system'
    });
  }

  // 触发警报
  private async handleCriticalAlert(request: RiskAlertRequest): Promise<void> {
    console.log(`处理严重警报: ${request.alertType} - ${request.message}`);
    
    // 发送紧急通知
    const emergencyMessage: ZMQMessage = {
      type: MessageType.EMERGENCY_STOP,
      timestamp: new Date().toISOString(),
      source: 'risk_module',
      data: {
        reason: `严重风险警报: ${request.message}`,
        alertType: request.alertType,
        strategyId: request.strategyId,
        severity: request.severity
      }
    };
    
    await zmqBus.publish(emergencyMessage);
    
    // 如果是策略相关的严重警报，暂停策略
    if (request.strategyId && request.alertType === 'position_limit') {
      strategyDAO.updateStatus(request.strategyId, 'paused');
      console.log(`策略${request.strategyId}因严重风险警报被暂停`);
    }
  }

  // 处理风险评估请求
  private async handleRiskAssessmentRequest(message: ZMQMessage): Promise<void> {
    try {
      const { action, strategyId } = message.data;
      
      if (action === 'request_assessment') {
        const request: RiskAssessmentRequest = {
          strategyId: strategyId as number,
          assessmentType: 'triggered',
          triggerReason: '交易员模组请求',
          assessedBy: 'system'
        };
        
        const result = await this.performRiskAssessment(request);
        
        // 发送评估结果回复
        const response: ZMQMessage = {
          type: MessageType.RISK_ALERT,
          timestamp: new Date().toISOString(),
          source: 'risk_module',
          target: message.source,
          correlationId: message.correlationId,
          data: {
            action: 'assessment_response',
            strategyId,
            result
          }
        };
        
        await zmqBus.publish(response);
      }
    } catch (error) {
      console.error('处理风险评估请求失败:', error);
    }
  }

  // 处理策略更新
  private async handleStrategyUpdate(message: ZMQMessage): Promise<void> {
    try {
      const { action, strategyId } = message.data;
      
      if (action === 'strategy_created') {
        // 新策略创建时进行初始风险评估
        const request: RiskAssessmentRequest = {
          strategyId: strategyId as number,
          assessmentType: 'initial',
          assessedBy: 'system'
        };
        
        await this.performRiskAssessment(request);
      }
    } catch (error) {
      console.error('处理策略更新失败:', error);
    }
  }

  // 处理订单更新
  private async handleOrderUpdate(message: ZMQMessage): Promise<void> {
    try {
      const { strategyId, status } = message.data;
      
      if (status === 'filled') {
        // 订单成交后重新计算风险指标
        const metrics = riskMetricsDAO.calculateStrategyRiskMetrics(strategyId as number);
        if (metrics) {
          await redisCache.set(
            CacheKeyType.RISK_METRICS,
            `strategy_${strategyId}`,
            metrics,
            300
          );
        }
      }
    } catch (error) {
      console.error('处理订单更新失败:', error);
    }
  }

  // 处理紧急停止请求
  private async handleEmergencyStopRequest(message: ZMQMessage): Promise<void> {
    try {
      console.log('收到紧急停止请求，创建系统级警报');
      
      await this.createRiskAlert({
        alertType: 'market_volatility',
        severity: 'critical',
        message: `紧急停止: ${message.data.reason}`,
        details: message.data,
        triggeredBy: message.source || 'system'
      });
    } catch (error) {
      console.error('处理紧急停止请求失败:', error);
    }
  }

  // 检查并创建警报
  private async checkAndCreateAlerts(strategyId: number, riskScore: unknown, riskLevel: string): Promise<void> {
    const typedRiskScore = riskScore as RiskScoreDetails;
    // 根据风险等级和评分创建相应的警报
    if (riskLevel === 'high' || riskLevel === 'critical') {
      await this.createRiskAlert({
        strategyId,
        alertType: 'var_breach',
        severity: riskLevel === 'critical' ? 'critical' : 'high',
        message: `策略${strategyId}风险评分过高: ${typedRiskScore.totalScore}`,
        details: typedRiskScore,
        triggeredBy: 'system'
      });
    }
  }

  // 缓存风险评估
  private async cacheRiskAssessment(strategyId: number, assessment: any): Promise<void> {
    await redisCache.set(
      CacheKeyType.RISK_METRICS,
      `assessment_${strategyId}`,
      assessment,
      3600 // 1小时缓存
    );
  }

  // 缓存风险警报
  private async cacheRiskAlert(alertId: number, alert: unknown): Promise<void> {
    await redisCache.set(
      CacheKeyType.RISK_METRICS,
      `alert_${alertId}`,
      alert,
      1800 // 30分钟缓存
    );
  }

  // 更新警报缓存
  private async updateAlertCache(alertId: number, updateData: Record<string, unknown>): Promise<void> {
    const cached = await redisCache.get(CacheKeyType.RISK_METRICS, `alert_${alertId}`);
    if (cached && typeof cached === 'object') {
      const updated = { ...cached, ...updateData, updated_at: new Date().toISOString() };
      await redisCache.set(CacheKeyType.RISK_METRICS, `alert_${alertId}`, updated, 1800);
    }
  }

  // 发送风险评估完成通知
  private async notifyRiskAssessmentComplete(strategyId: number, riskLevel: string, riskScore: number): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.RISK_ALERT,
      timestamp: new Date().toISOString(),
      source: 'risk_module',
      data: {
        action: 'assessment_completed',
        strategyId,
        riskLevel,
        riskScore
      }
    };
    
    await zmqBus.publish(message);
  }

  // 发送风险警报通知
  private async notifyRiskAlert(alertId: number, request: RiskAlertRequest): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.RISK_ALERT,
      timestamp: new Date().toISOString(),
      source: 'risk_module',
      data: {
        action: 'alert_created',
        alertId,
        alertType: request.alertType,
        severity: request.severity,
        message: request.message,
        strategyId: request.strategyId
      }
    };
    
    await zmqBus.publish(message);
  }

  // 发送警报确认通知
  private async notifyAlertAcknowledged(alertId: number, acknowledgedBy: string): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.RISK_ALERT,
      timestamp: new Date().toISOString(),
      source: 'risk_module',
      data: {
        action: 'alert_acknowledged',
        alertId,
        acknowledgedBy
      }
    };
    
    await zmqBus.publish(message);
  }

  // 发送警报解决通知
  private async notifyAlertResolved(alertId: number, resolvedBy: string): Promise<void> {
    const message: ZMQMessage = {
      type: MessageType.RISK_ALERT,
      timestamp: new Date().toISOString(),
      source: 'risk_module',
      data: {
        action: 'alert_resolved',
        alertId,
        resolvedBy
      }
    };
    
    await zmqBus.publish(message);
  }
}

// 导出服务实例
export const riskService = RiskService.getInstance();
export default RiskService;


// 接口定义

// 单个策略的风险指标
export interface StrategyRiskMetrics {
  strategyId: number;
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  sortinoRatio?: number; // 添加 Sortino 比率
  utilizationRatio: number;
  unrealizedPnL: number;
  maxSinglePosition: number;
  orderSuccessRate: number;
  totalPortfolioValue?: number; // 可选，因为可能在投资组合级别计算
  totalMargin?: number; // 可选
  openPositions?: number; // 可选
  dailyDrawdown?: number; // 可选
  monthlyDrawdown?: number; // 可选
  currentExposure?: number;
  var1d?: number;
  var5d?: number;
  maxDrawdown?: number;
  concentration?: number;
  liquidity?: number;
  market?: number;
  credit?: number;
  operational?: number;
}

// 投资组合的风险指标
export interface PortfolioRiskMetrics {
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  totalPortfolioValue?: number;
  totalMargin?: number;
  openPositions?: number;
  dailyDrawdown?: number;
  monthlyDrawdown?: number;
  unrealizedPnL?: number;
  totalStrategies?: number;
  totalExposure?: number;
  totalUnrealizedPnL?: number;
  totalMaxPositionSize?: number;
  portfolioUtilization?: number;
  avgUtilization?: number;
  strategyMetrics?: any[];
  calculatedAt?: string;
}

// 风险评分详情
export interface RiskScoreDetails {
  strategyId: number;
  scores: {
    positionSize: number;
    volatility: number;
    correlation: number;
    liquidity: number;
    drawdown: number;
    sharpeRatio: number;
    orderSuccess: number;
    riskAdjustedReturn: number;
    operational: number;
  };
  weights: RiskScoringWeights;
  totalScore: number;
  metrics: StrategyRiskMetrics;
}

// 评估详情
export interface AssessmentDetails {
  totalScore: number;
  breakdown: RiskScoreDetails['scores'];
  weights: RiskScoringWeights;
  metrics: StrategyRiskMetrics;
  assessmentTime: string;
}