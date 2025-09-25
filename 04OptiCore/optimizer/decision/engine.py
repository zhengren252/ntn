#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略决策引擎
负责策略选择、风险控制和最终决策

核心功能：
1. 策略评估与排序
2. 风险控制检查
3. 策略组合优化
4. 最终决策生成
5. 压力测试验证
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class DecisionEngineRiskConfig:
    """决策引擎风险控制配置"""

    max_position_size: float = 0.1
    max_daily_loss: float = 0.02
    max_drawdown_threshold: float = 0.05
    min_confidence_threshold: float = 0.6


@dataclass
class StrategyWeights:
    """策略权重配置"""

    return_weight: float = 0.4
    risk_weight: float = 0.3
    stability_weight: float = 0.2
    liquidity_weight: float = 0.1


@dataclass
class MarketState:
    """市场状态"""

    volatility: float = 0.0
    trend: str = "neutral"
    liquidity: str = "normal"


@dataclass
class StrategyDecision:
    """策略决策结果"""

    strategy_id: str
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-1
    risk_score: float  # 0-1
    expected_return: float
    max_drawdown: float
    position_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reasoning: str
    timestamp: datetime


class DecisionEngine:
    """
    策略决策引擎

    遵循NeuroTrade Nexus核心设计理念：
    - 微服务架构：独立的决策服务
    - 数据隔离：严格的风险控制
    - 高性能：快速决策生成
    - 可扩展：支持多种决策算法
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 风险控制配置
        self.risk_config = DecisionEngineRiskConfig(
            max_position_size=config.get("max_position_size", 0.1),
            max_daily_loss=config.get("max_daily_loss", 0.02),
            max_drawdown_threshold=config.get("max_drawdown_threshold", 0.05),
            min_confidence_threshold=config.get("min_confidence_threshold", 0.6),
        )

        # 策略权重配置
        strategy_weights_config = config.get(
            "strategy_weights",
            {"return": 0.4, "risk": 0.3, "stability": 0.2, "liquidity": 0.1},
        )
        self.strategy_weights = StrategyWeights(
            return_weight=strategy_weights_config.get("return", 0.4),
            risk_weight=strategy_weights_config.get("risk", 0.3),
            stability_weight=strategy_weights_config.get("stability", 0.2),
            liquidity_weight=strategy_weights_config.get("liquidity", 0.1),
        )

        # 压力测试配置
        self.stress_test_scenarios = config.get(
            "stress_test_scenarios",
            [
                {"name": "2008_crisis", "market_drop": -0.4, "volatility_spike": 3.0},
                {"name": "2020_covid", "market_drop": -0.35, "volatility_spike": 2.5},
                {
                    "name": "2022_crypto_winter",
                    "market_drop": -0.7,
                    "volatility_spike": 4.0,
                },
            ],
        )

        # 当前市场状态
        self.current_market_state = MarketState()

        self.logger.info("决策引擎初始化完成")

    async def initialize(self):
        """
        异步初始化决策引擎
        """
        self.logger.info("开始异步初始化决策引擎")
        # 这里可以添加需要异步初始化的组件
        # 例如：数据库连接、外部API连接等
        self.logger.info("决策引擎异步初始化完成")

    async def cleanup(self):
        """
        清理决策引擎资源
        """
        self.logger.info("开始清理决策引擎资源")
        # 这里可以添加资源清理逻辑
        # 例如：关闭数据库连接、清理缓存等
        self.logger.info("决策引擎资源清理完成")

    async def make_decision(
        self, optimization_results: Dict[str, Any], market_data: Dict[str, Any]
    ) -> List[StrategyDecision]:
        """
        基于优化结果和市场数据做出策略决策

        Args:
            optimization_results: 策略优化结果
            market_data: 当前市场数据

        Returns:
            List[StrategyDecision]: 策略决策列表
        """
        self.logger.info("开始策略决策分析")

        try:
            # 更新市场状态
            await self._update_market_state(market_data)

            # 评估所有策略
            strategy_evaluations = await self._evaluate_strategies(optimization_results)

            # 风险控制检查
            filtered_strategies = await self._risk_control_filter(strategy_evaluations)

            # 策略组合优化
            optimized_portfolio = await self._optimize_portfolio(filtered_strategies)

            # 生成最终决策
            decisions = await self._generate_decisions(optimized_portfolio, market_data)

            # 压力测试验证
            validated_decisions = await self._stress_test_validation(decisions)

            self.logger.info("决策分析完成，生成 %d 个决策", len(validated_decisions))
            return validated_decisions

        except Exception as e:
            self.logger.error("决策分析失败: %s", e)
            return []

    async def _update_market_state(self, market_data: Dict[str, Any]):
        """
        更新当前市场状态
        """
        try:
            # 计算市场波动率
            if "price_history" in market_data:
                prices = np.array(market_data["price_history"])
                returns = np.diff(np.log(prices))
                self.current_market_state.volatility = np.std(returns) * np.sqrt(252)

            # 判断市场趋势
            if "trend_indicators" in market_data:
                trend_score = market_data["trend_indicators"].get("trend_score", 0)
                if trend_score > 0.1:
                    self.current_market_state.trend = "bullish"
                elif trend_score < -0.1:
                    self.current_market_state.trend = "bearish"
                else:
                    self.current_market_state.trend = "neutral"

            # 评估市场流动性
            if "volume_data" in market_data:
                avg_volume = np.mean(market_data["volume_data"])
                recent_volume = market_data["volume_data"][-1]

                if recent_volume > avg_volume * 1.5:
                    self.current_market_state.liquidity = "high"
                elif recent_volume < avg_volume * 0.5:
                    self.current_market_state.liquidity = "low"
                else:
                    self.current_market_state.liquidity = "normal"

            self.logger.debug("市场状态更新: %s", self.current_market_state)

        except Exception as e:
            self.logger.warning("市场状态更新失败: %s", e)

    async def _evaluate_strategies(
        self, optimization_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        评估所有策略
        """
        evaluations = []

        for symbol, symbol_results in optimization_results.items():
            if "optimized_strategies" not in symbol_results:
                continue

            for strategy_id, strategy_result in symbol_results[
                "optimized_strategies"
            ].items():
                evaluation = await self._evaluate_single_strategy(
                    symbol, strategy_id, strategy_result
                )

                if evaluation:
                    evaluations.append(evaluation)

        # 按综合评分排序
        evaluations.sort(key=lambda x: x["total_score"], reverse=True)

        self.logger.info("策略评估完成，共评估 %d 个策略", len(evaluations))
        return evaluations

    async def _evaluate_single_strategy(
        self, symbol: str, strategy_id: str, strategy_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        评估单个策略
        """
        try:
            # 提取关键指标
            total_return = strategy_result.get("total_return", 0)
            max_drawdown = abs(strategy_result.get("max_drawdown", 0))
            sharpe_ratio = strategy_result.get("sharpe_ratio", 0)
            win_rate = strategy_result.get("win_rate", 0)
            profit_factor = strategy_result.get("profit_factor", 1)

            # 计算各维度评分
            return_score = min(total_return * 100, 100)  # 收益评分
            risk_score = max(0, 100 - max_drawdown * 1000)  # 风险评分
            stability_score = min(sharpe_ratio * 20, 100)  # 稳定性评分

            # 流动性评分（基于策略类型）
            liquidity_score = self._calculate_liquidity_score(strategy_id)

            # 市场适应性评分
            market_fit_score = self._calculate_market_fit_score(
                strategy_id, strategy_result
            )

            # 计算综合评分
            total_score = (
                return_score * self.strategy_weights.return_weight
                + risk_score * self.strategy_weights.risk_weight
                + stability_score * self.strategy_weights.stability_weight
                + liquidity_score * self.strategy_weights.liquidity_weight
            ) * market_fit_score

            evaluation = {
                "symbol": symbol,
                "strategy_id": strategy_id,
                "strategy_result": strategy_result,
                "scores": {
                    "return": return_score,
                    "risk": risk_score,
                    "stability": stability_score,
                    "liquidity": liquidity_score,
                    "market_fit": market_fit_score,
                },
                "total_score": total_score,
                "key_metrics": {
                    "total_return": total_return,
                    "max_drawdown": max_drawdown,
                    "sharpe_ratio": sharpe_ratio,
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                },
            }

            return evaluation

        except Exception as e:
            self.logger.warning("策略评估失败 %s: %s", strategy_id, e)
            return None

    def _calculate_liquidity_score(self, strategy_id: str) -> float:
        """
        计算策略流动性评分
        """
        # 基于策略类型的流动性评分
        liquidity_scores = {
            "grid_trading": 85,  # 网格交易流动性较好
            "ma_crossover": 90,  # 均线策略流动性很好
            "mean_reversion": 80,  # 均值回归流动性中等
            "momentum": 95,  # 动量策略流动性最好
            "arbitrage": 70,  # 套利策略流动性较低
        }

        # 根据策略ID推断策略类型
        for strategy_type, score in liquidity_scores.items():
            if strategy_type in strategy_id.lower():
                return score

        return 75  # 默认评分

    def _calculate_market_fit_score(
        self, strategy_id: str, strategy_result: Dict[str, Any]
    ) -> float:
        """
        计算策略与当前市场的适应性评分
        """
        base_score = 1.0

        # 根据市场趋势调整
        if self.current_market_state.trend == "bullish":
            if "momentum" in strategy_id.lower() or "trend" in strategy_id.lower():
                base_score *= 1.2  # 牛市中趋势策略表现更好
            elif "mean_reversion" in strategy_id.lower():
                base_score *= 0.8  # 牛市中均值回归策略表现较差

        elif self.current_market_state.trend == "bearish":
            if "mean_reversion" in strategy_id.lower():
                base_score *= 1.1  # 熊市中均值回归策略可能表现更好
            elif "momentum" in strategy_id.lower():
                base_score *= 0.9  # 熊市中动量策略风险较高

        # 根据市场波动率调整
        volatility = self.current_market_state.volatility
        if volatility > 0.3:  # 高波动市场
            if "grid" in strategy_id.lower():
                base_score *= 1.1  # 网格策略在高波动中表现更好
        elif volatility < 0.1:  # 低波动市场
            if "breakout" in strategy_id.lower():
                base_score *= 0.8  # 突破策略在低波动中表现较差

        # 根据流动性调整
        if self.current_market_state.liquidity == "low":
            base_score *= 0.9  # 低流动性市场整体降低评分

        return min(base_score, 1.5)  # 限制最大调整幅度

    async def _risk_control_filter(
        self, strategy_evaluations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        风险控制过滤
        """
        filtered_strategies = []

        for evaluation in strategy_evaluations:
            # 检查最大回撤
            max_drawdown = evaluation["key_metrics"]["max_drawdown"]
            if max_drawdown > self.risk_config.max_drawdown_threshold:
                self.logger.debug(
                    f"策略 {evaluation['strategy_id']} 回撤过大: {max_drawdown:.3f}"
                )
                continue

            # 检查夏普比率
            sharpe_ratio = evaluation["key_metrics"]["sharpe_ratio"]
            if sharpe_ratio < 0.5:  # 最小夏普比率要求
                self.logger.debug(
                    f"策略 {evaluation['strategy_id']} 夏普比率过低: {sharpe_ratio:.3f}"
                )
                continue

            # 检查胜率
            win_rate = evaluation["key_metrics"]["win_rate"]
            if win_rate < 0.4:  # 最小胜率要求
                self.logger.debug(
                    f"策略 {evaluation['strategy_id']} 胜率过低: {win_rate:.3f}"
                )
                continue

            # 检查盈利因子
            profit_factor = evaluation["key_metrics"]["profit_factor"]
            if profit_factor < 1.2:  # 最小盈利因子要求
                self.logger.debug(
                    f"策略 {evaluation['strategy_id']} 盈利因子过低: {profit_factor:.3f}"
                )
                continue

            filtered_strategies.append(evaluation)

        self.logger.info("风险控制过滤完成，保留 %d 个策略", len(filtered_strategies))
        return filtered_strategies

    async def _optimize_portfolio(
        self, filtered_strategies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        策略组合优化
        """
        if not filtered_strategies:
            return []

        # 按符号分组
        symbol_groups = {}
        for strategy in filtered_strategies:
            symbol = strategy["symbol"]
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(strategy)

        optimized_portfolio = []

        # 为每个符号选择最优策略
        for symbol, strategies in symbol_groups.items():
            # 选择评分最高的策略
            best_strategy = max(strategies, key=lambda x: x["total_score"])

            # 计算建议仓位大小
            position_size = self._calculate_position_size(best_strategy)
            best_strategy["recommended_position_size"] = position_size

            optimized_portfolio.append(best_strategy)

        # 按总评分排序
        optimized_portfolio.sort(key=lambda x: x["total_score"], reverse=True)

        # 限制组合大小（最多5个策略）
        optimized_portfolio = optimized_portfolio[:5]

        self.logger.info("组合优化完成，选择 %d 个策略", len(optimized_portfolio))
        return optimized_portfolio

    def _calculate_position_size(self, strategy_evaluation: Dict[str, Any]) -> float:
        """
        计算建议仓位大小
        """
        # 基础仓位大小
        base_position = self.risk_config.max_position_size

        # 根据策略评分调整
        score_factor = strategy_evaluation["total_score"] / 100

        # 根据风险调整
        max_drawdown = strategy_evaluation["key_metrics"]["max_drawdown"]
        risk_factor = max(0.1, 1 - max_drawdown * 10)  # 回撤越大，仓位越小

        # 根据夏普比率调整
        sharpe_ratio = strategy_evaluation["key_metrics"]["sharpe_ratio"]
        sharpe_factor = min(2.0, max(0.5, sharpe_ratio))  # 夏普比率调整因子

        # 计算最终仓位
        position_size = base_position * score_factor * risk_factor * sharpe_factor

        # 确保仓位在合理范围内
        return max(0.01, min(self.risk_config.max_position_size, position_size))

    async def _generate_decisions(
        self, optimized_portfolio: List[Dict[str, Any]], market_data: Dict[str, Any]
    ) -> List[StrategyDecision]:
        """
        生成最终决策
        """
        decisions = []

        for strategy_eval in optimized_portfolio:
            try:
                decision = await self._create_strategy_decision(
                    strategy_eval, market_data
                )

                if decision:
                    decisions.append(decision)

            except Exception as e:
                self.logger.warning("决策生成失败: %s", e)

        return decisions

    async def _create_strategy_decision(
        self, strategy_eval: Dict[str, Any], market_data: Dict[str, Any]
    ) -> Optional[StrategyDecision]:
        """
        创建单个策略决策
        """
        try:
            symbol = strategy_eval["symbol"]
            strategy_id = strategy_eval["strategy_id"]
            strategy_result = strategy_eval["strategy_result"]

            # 确定交易动作
            action = self._determine_action(strategy_result, market_data)

            # 计算置信度
            confidence = self._calculate_confidence(strategy_eval)

            # 计算风险评分
            risk_score = 1 - strategy_eval["scores"]["risk"] / 100

            # 设置止损和止盈
            current_price = market_data.get("current_price", {}).get(symbol, 0)
            stop_loss, take_profit = self._calculate_stop_levels(
                action, current_price, strategy_result
            )

            # 生成决策理由
            reasoning = self._generate_reasoning(strategy_eval, action)

            decision = StrategyDecision(
                strategy_id=strategy_id,
                symbol=symbol,
                action=action,
                confidence=confidence,
                risk_score=risk_score,
                expected_return=strategy_result.get("total_return", 0),
                max_drawdown=abs(strategy_result.get("max_drawdown", 0)),
                position_size=strategy_eval["recommended_position_size"],
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=reasoning,
                timestamp=datetime.now(),
            )

            return decision

        except Exception as e:
            self.logger.error("创建策略决策失败: %s", e)
            return None

    def _determine_action(
        self, strategy_result: Dict[str, Any], market_data: Dict[str, Any]
    ) -> str:
        """
        确定交易动作
        """
        # 基于策略信号确定动作
        signal = strategy_result.get("current_signal", "HOLD")

        # 考虑市场状态调整
        if signal == "BUY" and self.current_market_state.trend == "bearish":
            # 在熊市中谨慎买入
            if strategy_result.get("confidence", 0) < 0.8:
                signal = "HOLD"

        elif signal == "SELL" and self.current_market_state.trend == "bullish":
            # 在牛市中谨慎卖出
            if strategy_result.get("confidence", 0) < 0.8:
                signal = "HOLD"

        return signal

    def _calculate_confidence(self, strategy_eval: Dict[str, Any]) -> float:
        """
        计算决策置信度
        """
        # 基于策略评分计算置信度
        base_confidence = strategy_eval["total_score"] / 100

        # 根据关键指标调整
        sharpe_ratio = strategy_eval["key_metrics"]["sharpe_ratio"]
        win_rate = strategy_eval["key_metrics"]["win_rate"]

        # 夏普比率调整
        sharpe_factor = min(1.2, max(0.8, 1 + (sharpe_ratio - 1) * 0.2))

        # 胜率调整
        win_rate_factor = min(1.2, max(0.8, win_rate * 1.5))

        # 市场适应性调整
        market_fit = strategy_eval["scores"]["market_fit"]

        confidence = base_confidence * sharpe_factor * win_rate_factor * market_fit

        return max(0.1, min(1.0, confidence))

    def _calculate_stop_levels(
        self, action: str, current_price: float, strategy_result: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        计算止损和止盈水平
        """
        if action == "HOLD" or current_price <= 0:
            return None, None

        # 基于ATR计算止损距离
        atr = strategy_result.get("atr", current_price * 0.02)  # 默认2%

        if action == "BUY":
            stop_loss = current_price - atr * 2  # 2倍ATR止损
            take_profit = current_price + atr * 3  # 3倍ATR止盈
        else:  # SELL
            stop_loss = current_price + atr * 2
            take_profit = current_price - atr * 3

        return stop_loss, take_profit

    def _generate_reasoning(self, strategy_eval: Dict[str, Any], action: str) -> str:
        """
        生成决策理由
        """
        strategy_id = strategy_eval["strategy_id"]
        total_score = strategy_eval["total_score"]
        key_metrics = strategy_eval["key_metrics"]

        reasoning = f"策略 {strategy_id} 综合评分 {total_score:.1f}，"
        reasoning += f"预期收益 {key_metrics['total_return']:.2%}，"
        reasoning += f"最大回撤 {key_metrics['max_drawdown']:.2%}，"
        reasoning += f"夏普比率 {key_metrics['sharpe_ratio']:.2f}。"

        if action == "BUY":
            reasoning += "市场条件适合买入。"
        elif action == "SELL":
            reasoning += "市场条件适合卖出。"
        else:
            reasoning += "建议观望等待更好机会。"

        return reasoning

    async def _stress_test_validation(
        self, decisions: List[StrategyDecision]
    ) -> List[StrategyDecision]:
        """
        压力测试验证
        """
        validated_decisions = []

        for decision in decisions:
            # 对每个决策进行压力测试
            stress_test_passed = await self._run_stress_test(decision)

            if stress_test_passed:
                validated_decisions.append(decision)
            else:
                self.logger.warning("策略 %s 未通过压力测试", decision.strategy_id)

        self.logger.info("压力测试完成，%d/%d 个决策通过", len(validated_decisions), len(decisions))
        return validated_decisions

    async def _run_stress_test(self, decision: StrategyDecision) -> bool:
        """
        运行单个决策的压力测试
        """
        try:
            # 检查在极端市场条件下的表现
            for scenario in self.stress_test_scenarios:
                # 模拟极端市场条件
                stressed_return = decision.expected_return * (
                    1 + scenario["market_drop"]
                )
                stressed_drawdown = decision.max_drawdown * scenario["volatility_spike"]

                # 检查是否超过风险阈值
                if (
                    stressed_drawdown > self.risk_config.max_drawdown_threshold * 2
                ):  # 压力测试阈值更严格
                    self.logger.debug(
                        f"策略 {decision.strategy_id} 在 {scenario['name']} 场景下回撤过大"
                    )
                    return False

                if stressed_return < -self.risk_config.max_daily_loss * 5:  # 极端损失检查
                    self.logger.debug(
                        f"策略 {decision.strategy_id} 在 {scenario['name']} 场景下损失过大"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.warning("压力测试失败: %s", e)
            return False
