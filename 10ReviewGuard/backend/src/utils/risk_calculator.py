#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReviewGuard人工审核模组 - 风险计算器
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RiskMetrics:
    """风险指标数据类"""
    volatility_score: float
    liquidity_score: float
    correlation_risk: float
    drawdown_risk: float
    position_risk: float
    overall_score: float
    risk_level: str
    confidence: float


class RiskCalculator:
    """风险计算器"""
    
    def __init__(self):
        # 风险权重配置
        self.weights = {
            'volatility': 0.25,
            'liquidity': 0.20,
            'correlation': 0.20,
            'drawdown': 0.20,
            'position': 0.15
        }
        
        # 风险阈值
        self.thresholds = {
            'low': 0.3,
            'medium': 0.7,
            'high': 1.0
        }
    
    def calculate_strategy_risk(self, strategy_data: Dict[str, Any]) -> RiskMetrics:
        """
        计算策略综合风险
        
        Args:
            strategy_data: 策略数据
            
        Returns:
            风险指标对象
        """
        
        # 计算各项风险指标
        volatility_score = self._calculate_volatility_risk(strategy_data)
        liquidity_score = self._calculate_liquidity_risk(strategy_data)
        correlation_risk = self._calculate_correlation_risk(strategy_data)
        drawdown_risk = self._calculate_drawdown_risk(strategy_data)
        position_risk = self._calculate_position_risk(strategy_data)
        
        # 计算综合风险评分
        overall_score = (
            volatility_score * self.weights['volatility'] +
            liquidity_score * self.weights['liquidity'] +
            correlation_risk * self.weights['correlation'] +
            drawdown_risk * self.weights['drawdown'] +
            position_risk * self.weights['position']
        )
        
        # 确定风险等级
        risk_level = self._determine_risk_level(overall_score)
        
        # 计算置信度
        confidence = self._calculate_confidence(strategy_data)
        
        return RiskMetrics(
            volatility_score=volatility_score,
            liquidity_score=liquidity_score,
            correlation_risk=correlation_risk,
            drawdown_risk=drawdown_risk,
            position_risk=position_risk,
            overall_score=overall_score,
            risk_level=risk_level,
            confidence=confidence
        )
    
    def _calculate_volatility_risk(self, strategy_data: Dict[str, Any]) -> float:
        """
        计算波动率风险
        """
        # 获取历史收益率数据
        returns = strategy_data.get('historical_returns', [])
        
        if not returns or len(returns) < 2:
            # 如果没有历史数据，使用预期收益率估算
            expected_return = strategy_data.get('expected_return', 0)
            return min(abs(expected_return) * 2, 1.0)
        
        # 计算收益率标准差
        returns_array = np.array(returns)
        volatility = np.std(returns_array)
        
        # 年化波动率
        annualized_volatility = volatility * math.sqrt(252)  # 假设252个交易日
        
        # 将波动率转换为风险评分 (0-1)
        # 波动率超过50%认为是高风险
        risk_score = min(annualized_volatility / 0.5, 1.0)
        
        return risk_score
    
    def _calculate_liquidity_risk(self, strategy_data: Dict[str, Any]) -> float:
        """
        计算流动性风险
        """
        symbol = strategy_data.get('symbol', '')
        position_size = strategy_data.get('position_size', 0.05)
        
        # 基于交易品种的流动性评估
        liquidity_scores = {
            # 主要货币对 - 低风险
            'EURUSD': 0.1, 'GBPUSD': 0.1, 'USDJPY': 0.1,
            'USDCHF': 0.15, 'AUDUSD': 0.15, 'USDCAD': 0.15,
            
            # 次要货币对 - 中等风险
            'EURGBP': 0.3, 'EURJPY': 0.3, 'GBPJPY': 0.35,
            'NZDUSD': 0.4, 'EURCHF': 0.3,
            
            # 新兴市场货币 - 高风险
            'USDTRY': 0.8, 'USDZAR': 0.8, 'USDMXN': 0.7,
            
            # 加密货币 - 极高风险
            'BTCUSD': 0.9, 'ETHUSD': 0.9, 'XRPUSD': 0.95
        }
        
        base_liquidity_risk = liquidity_scores.get(symbol.upper(), 0.5)
        
        # 仓位大小调整
        position_multiplier = min(position_size / 0.1, 2.0)  # 10%以上仓位增加风险
        
        liquidity_risk = min(base_liquidity_risk * position_multiplier, 1.0)
        
        return liquidity_risk
    
    def _calculate_correlation_risk(self, strategy_data: Dict[str, Any]) -> float:
        """
        计算相关性风险
        """
        strategy_type = strategy_data.get('strategy_type', '')
        symbol = strategy_data.get('symbol', '')
        
        # 基于策略类型的相关性风险
        strategy_correlation = {
            'trend_following': 0.4,  # 趋势策略相关性较高
            'mean_reversion': 0.3,   # 均值回归策略相关性中等
            'arbitrage': 0.2,        # 套利策略相关性较低
            'scalping': 0.5,         # 剥头皮策略相关性较高
            'breakout': 0.4,         # 突破策略相关性较高
            'grid': 0.6,             # 网格策略相关性很高
        }
        
        base_correlation = strategy_correlation.get(strategy_type.lower(), 0.4)
        
        # 考虑交易品种的相关性
        if 'USD' in symbol.upper():
            base_correlation += 0.1  # 美元相关品种增加相关性风险
        
        return min(base_correlation, 1.0)
    
    def _calculate_drawdown_risk(self, strategy_data: Dict[str, Any]) -> float:
        """
        计算回撤风险
        """
        max_drawdown = strategy_data.get('max_drawdown', 0)
        historical_drawdowns = strategy_data.get('historical_drawdowns', [])
        
        # 基于最大回撤的风险评估
        drawdown_risk = min(max_drawdown / 0.2, 1.0)  # 20%回撤为高风险阈值
        
        # 如果有历史回撤数据，考虑回撤频率
        if historical_drawdowns:
            drawdown_frequency = len([d for d in historical_drawdowns if d > 0.05]) / len(historical_drawdowns)
            drawdown_risk = max(drawdown_risk, drawdown_frequency)
        
        return drawdown_risk
    
    def _calculate_position_risk(self, strategy_data: Dict[str, Any]) -> float:
        """
        计算仓位风险
        """
        position_size = strategy_data.get('position_size', 0.05)
        leverage = strategy_data.get('leverage', 1.0)
        
        # 实际风险敞口
        actual_exposure = position_size * leverage
        
        # 仓位风险评分
        position_risk = min(actual_exposure / 0.5, 1.0)  # 50%敞口为高风险阈值
        
        return position_risk
    
    def _determine_risk_level(self, overall_score: float) -> str:
        """
        确定风险等级
        """
        if overall_score <= self.thresholds['low']:
            return RiskLevel.LOW.value
        elif overall_score <= self.thresholds['medium']:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.HIGH.value
    
    def _calculate_confidence(self, strategy_data: Dict[str, Any]) -> float:
        """
        计算风险评估置信度
        """
        confidence_factors = []
        
        # 历史数据完整性
        historical_returns = strategy_data.get('historical_returns', [])
        if len(historical_returns) >= 100:
            confidence_factors.append(0.9)
        elif len(historical_returns) >= 50:
            confidence_factors.append(0.7)
        elif len(historical_returns) >= 20:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # 策略运行时间
        backtest_period = strategy_data.get('backtest_period_days', 0)
        if backtest_period >= 365:
            confidence_factors.append(0.9)
        elif backtest_period >= 180:
            confidence_factors.append(0.7)
        elif backtest_period >= 90:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # 交易次数
        trade_count = strategy_data.get('total_trades', 0)
        if trade_count >= 1000:
            confidence_factors.append(0.9)
        elif trade_count >= 500:
            confidence_factors.append(0.7)
        elif trade_count >= 100:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # 计算平均置信度
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5
    
    def calculate_portfolio_risk(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算投资组合风险
        
        Args:
            strategies: 策略列表
            
        Returns:
            投资组合风险指标
        """
        if not strategies:
            return {
                'portfolio_risk': 0.0,
                'diversification_benefit': 0.0,
                'concentration_risk': 0.0,
                'correlation_matrix': []
            }
        
        # 计算各策略风险
        strategy_risks = []
        strategy_weights = []
        
        for strategy in strategies:
            risk_metrics = self.calculate_strategy_risk(strategy)
            strategy_risks.append(risk_metrics.overall_score)
            strategy_weights.append(strategy.get('allocation_weight', 1.0))
        
        # 标准化权重
        total_weight = sum(strategy_weights)
        if total_weight > 0:
            strategy_weights = [w / total_weight for w in strategy_weights]
        
        # 计算加权平均风险
        weighted_risk = sum(risk * weight for risk, weight in zip(strategy_risks, strategy_weights))
        
        # 计算集中度风险
        concentration_risk = self._calculate_concentration_risk(strategy_weights)
        
        # 计算分散化收益（简化版本）
        diversification_benefit = max(0, 1 - len(strategies) / 10)  # 最多10个策略获得最大分散化收益
        
        # 调整投资组合风险
        portfolio_risk = weighted_risk * (1 + concentration_risk) * (1 - diversification_benefit * 0.2)
        
        return {
            'portfolio_risk': min(portfolio_risk, 1.0),
            'diversification_benefit': diversification_benefit,
            'concentration_risk': concentration_risk,
            'strategy_count': len(strategies),
            'individual_risks': strategy_risks,
            'strategy_weights': strategy_weights
        }
    
    def _calculate_concentration_risk(self, weights: List[float]) -> float:
        """
        计算集中度风险（基于赫芬达尔指数）
        """
        if not weights:
            return 0.0
        
        # 赫芬达尔指数
        hhi = sum(w ** 2 for w in weights)
        
        # 转换为风险评分 (0-1)
        # HHI = 1 表示完全集中，HHI = 1/n 表示完全分散
        max_diversification = 1.0 / len(weights) if weights else 1.0
        concentration_risk = (hhi - max_diversification) / (1.0 - max_diversification)
        
        return max(0, min(concentration_risk, 1.0))


if __name__ == "__main__":
    # 测试风险计算器
    calculator = RiskCalculator()
    
    # 测试策略数据
    test_strategy = {
        'strategy_id': 'test_001',
        'symbol': 'EURUSD',
        'strategy_type': 'trend_following',
        'expected_return': 0.15,
        'max_drawdown': 0.08,
        'position_size': 0.05,
        'leverage': 2.0,
        'historical_returns': [0.01, -0.02, 0.015, -0.01, 0.02] * 20,
        'backtest_period_days': 365,
        'total_trades': 500
    }
    
    # 计算风险
    risk_metrics = calculator.calculate_strategy_risk(test_strategy)
    
    print("策略风险评估结果:")
    print(f"波动率风险: {risk_metrics.volatility_score:.3f}")
    print(f"流动性风险: {risk_metrics.liquidity_score:.3f}")
    print(f"相关性风险: {risk_metrics.correlation_risk:.3f}")
    print(f"回撤风险: {risk_metrics.drawdown_risk:.3f}")
    print(f"仓位风险: {risk_metrics.position_risk:.3f}")
    print(f"综合风险: {risk_metrics.overall_score:.3f}")
    print(f"风险等级: {risk_metrics.risk_level}")
    print(f"置信度: {risk_metrics.confidence:.3f}")
    
    # 测试投资组合风险
    test_portfolio = [test_strategy, test_strategy.copy()]
    portfolio_risk = calculator.calculate_portfolio_risk(test_portfolio)
    
    print("\n投资组合风险评估结果:")
    print(f"投资组合风险: {portfolio_risk['portfolio_risk']:.3f}")
    print(f"分散化收益: {portfolio_risk['diversification_benefit']:.3f}")
    print(f"集中度风险: {portfolio_risk['concentration_risk']:.3f}")