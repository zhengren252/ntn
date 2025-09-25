#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理器
NeuroTrade Nexus (NTN) - Risk Manager

核心功能：
1. 仓位管理和风险控制
2. 止损止盈策略
3. 最大回撤控制
4. 动态风险调整
5. 压力测试验证
6. 风险指标监控

遵循NeuroTrade Nexus核心设计理念：
- 微服务架构：独立的风险管理服务
- 数据隔离：严格的风险参数隔离
- 实时监控：持续的风险状态监控
- 可配置：灵活的风险参数配置
"""

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass
class RiskControlConfig:
    """风险控制配置"""

    max_portfolio_risk: float = 0.02
    max_position_size: float = 0.1
    max_daily_loss: float = 0.02
    max_drawdown_threshold: float = 0.05
    min_sharpe_ratio: float = 1.0
    max_correlation: float = 0.7
    liquidity_threshold: float = 0.1


@dataclass
class StopLossConfig:
    """止损止盈配置"""

    default_stop_loss: float = 0.03
    default_take_profit: float = 0.06
    trailing_stop_enabled: bool = True
    trailing_stop_distance: float = 0.02


@dataclass
class RiskManagerState:
    """风险管理器状态"""

    current_portfolio_risk: float = 0.0
    risk_monitoring_enabled: bool = True
    emergency_mode: bool = False


@dataclass
class RiskManagerData:
    """风险管理器数据"""

    current_positions: Dict[str, Any] = None
    risk_metrics_history: List[Any] = None
    daily_pnl_history: List[float] = None
    stress_test_scenarios: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.current_positions is None:
            self.current_positions = {}
        if self.risk_metrics_history is None:
            self.risk_metrics_history = []
        if self.daily_pnl_history is None:
            self.daily_pnl_history = []
        if self.stress_test_scenarios is None:
            self.stress_test_scenarios = []


@dataclass
class RiskAdjustmentConfig:
    """动态风险调整配置"""

    volatility_lookback: int = 20
    risk_adjustment_factor: float = 1.5


class RiskLevel(Enum):
    """风险等级枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    """风险控制动作类型"""

    ALLOW = "allow"
    REDUCE = "reduce"
    BLOCK = "block"
    EMERGENCY_EXIT = "emergency_exit"


@dataclass
class RiskMetrics:
    """风险指标数据结构"""

    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    var_95: float  # 95% VaR
    var_99: float  # 99% VaR
    beta: float
    volatility: float
    correlation_risk: float
    liquidity_risk: float
    concentration_risk: float
    timestamp: datetime


@dataclass
class PositionRisk:
    """仓位风险数据结构"""

    symbol: str
    strategy_id: str
    current_position: float
    max_position_allowed: float
    current_value: float
    unrealized_pnl: float
    risk_score: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    risk_level: RiskLevel
    last_updated: datetime


@dataclass
class RiskControlDecision:
    """风险控制决策"""

    symbol: str
    strategy_id: str
    action: ActionType
    recommended_position: float
    current_position: float
    risk_score: float
    risk_level: RiskLevel
    reasoning: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    timestamp: datetime
    emergency_exit: bool = False


class RiskManager:
    """
    风险管理器

    负责整个策略优化模组的风险控制和管理
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化配置对象
        self.risk_control_config = RiskControlConfig(
            max_portfolio_risk=config.get("max_portfolio_risk", 0.02),
            max_position_size=config.get("max_position_size", 0.1),
            max_daily_loss=config.get("max_daily_loss", 0.02),
            max_drawdown_threshold=config.get("max_drawdown_threshold", 0.05),
            min_sharpe_ratio=config.get("min_sharpe_ratio", 1.0),
            max_correlation=config.get("max_correlation", 0.7),
            liquidity_threshold=config.get("liquidity_threshold", 0.1),
        )

        self.stop_loss_config = StopLossConfig(
            default_stop_loss=config.get("default_stop_loss", 0.03),
            default_take_profit=config.get("default_take_profit", 0.06),
            trailing_stop_enabled=config.get("trailing_stop_enabled", True),
            trailing_stop_distance=config.get("trailing_stop_distance", 0.02),
        )

        self.risk_adjustment_config = RiskAdjustmentConfig(
            volatility_lookback=config.get("volatility_lookback", 20),
            risk_adjustment_factor=config.get("risk_adjustment_factor", 1.5),
        )

        # 使用数据类管理状态和数据
        self.state = RiskManagerState()
        self.data = RiskManagerData(
            stress_test_scenarios=config.get(
                "stress_test_scenarios",
                [
                    {
                        "name": "market_crash",
                        "market_drop": -0.2,
                        "volatility_spike": 2.0,
                    },
                    {
                        "name": "flash_crash",
                        "market_drop": -0.1,
                        "volatility_spike": 5.0,
                    },
                    {
                        "name": "liquidity_crisis",
                        "market_drop": -0.15,
                        "liquidity_drop": 0.5,
                    },
                ],
            )
        )

        self.logger.info("风险管理器初始化完成")

    async def initialize(self):
        """
        异步初始化风险管理器
        """
        try:
            # 初始化风险监控
            self.state.risk_monitoring_enabled = True
            self.state.emergency_mode = False

            # 重置风险状态
            self.state.current_portfolio_risk = 0.0
            self.data.current_positions.clear()
            self.data.risk_metrics_history.clear()
            self.data.daily_pnl_history.clear()

            self.logger.info("风险管理器异步初始化完成")

        except Exception as e:
            self.logger.error(f"风险管理器初始化失败: {e}")
            raise

    async def evaluate_position_risk(
        self,
        symbol: str,
        strategy_id: str,
        position_size: float,
        current_price: float,
        strategy_metrics: Dict[str, Any],
    ) -> RiskControlDecision:
        """
        评估仓位风险并生成控制决策

        Args:
            symbol: 交易对符号
            strategy_id: 策略ID
            position_size: 建议仓位大小
            current_price: 当前价格
            strategy_metrics: 策略指标

        Returns:
            RiskControlDecision: 风险控制决策
        """
        try:
            # 计算仓位风险指标
            risk_score = await self._calculate_position_risk_score(
                symbol, strategy_id, position_size, strategy_metrics
            )

            # 确定风险等级
            risk_level = self._determine_risk_level(risk_score)

            # 检查仓位限制
            max_allowed_position = await self._calculate_max_allowed_position(
                symbol, strategy_id, strategy_metrics
            )

            # 调整仓位大小
            adjusted_position = min(position_size, max_allowed_position)

            # 确定控制动作
            action = self._determine_control_action(
                risk_level, adjusted_position, position_size
            )

            # 计算止损止盈价格
            stop_loss, take_profit = await self._calculate_stop_levels(
                symbol, current_price, strategy_metrics
            )

            # 生成决策理由
            reasoning = self._generate_risk_reasoning(
                risk_score, risk_level, action, adjusted_position, position_size
            )

            decision = RiskControlDecision(
                symbol=symbol,
                strategy_id=strategy_id,
                action=action,
                recommended_position=adjusted_position,
                current_position=position_size,
                risk_score=risk_score,
                risk_level=risk_level,
                reasoning=reasoning,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.now(),
                emergency_exit=self.emergency_mode,
            )

            self.logger.debug(f"仓位风险评估完成: {symbol} - {action.value}")
            return decision

        except Exception as e:
            self.logger.error(f"仓位风险评估失败: {e}")
            # 返回保守的决策
            return RiskControlDecision(
                symbol=symbol,
                strategy_id=strategy_id,
                action=ActionType.BLOCK,
                recommended_position=0.0,
                current_position=position_size,
                risk_score=1.0,
                risk_level=RiskLevel.CRITICAL,
                reasoning="风险评估失败，采用保守策略",
                stop_loss=None,
                take_profit=None,
                timestamp=datetime.now(),
                emergency_exit=True,
            )

    async def _calculate_position_risk_score(
        self,
        symbol: str,
        strategy_id: str,
        position_size: float,
        strategy_metrics: Dict[str, Any],
    ) -> float:
        """
        计算仓位风险评分
        """
        risk_factors = []

        # 1. 仓位大小风险
        position_risk = position_size / self.risk_control_config.max_position_size
        risk_factors.append(position_risk * 0.3)

        # 2. 策略历史表现风险
        max_drawdown = abs(strategy_metrics.get("max_drawdown", 0))
        drawdown_risk = max_drawdown / self.risk_control_config.max_drawdown_threshold
        risk_factors.append(drawdown_risk * 0.25)

        # 3. 夏普比率风险
        sharpe_ratio = strategy_metrics.get("sharpe_ratio", 0)
        sharpe_risk = max(
            0,
            (self.risk_control_config.min_sharpe_ratio - sharpe_ratio)
            / self.risk_control_config.min_sharpe_ratio,
        )
        risk_factors.append(sharpe_risk * 0.2)

        # 4. 波动率风险
        volatility = strategy_metrics.get("volatility", 0)
        volatility_risk = min(1.0, volatility / 0.3)  # 30%波动率为高风险
        risk_factors.append(volatility_risk * 0.15)

        # 5. 相关性风险
        correlation_risk = await self._calculate_correlation_risk(symbol, strategy_id)
        risk_factors.append(correlation_risk * 0.1)

        # 计算综合风险评分
        total_risk = sum(risk_factors)
        return min(1.0, total_risk)

    async def _calculate_correlation_risk(self, symbol: str, strategy_id: str) -> float:
        """
        计算与现有仓位的相关性风险
        """
        if not self.current_positions:
            return 0.0

        max_correlation = 0.0

        for _pos_key, position in self.current_positions.items():
            if position.symbol == symbol:
                # 同一交易对的相关性风险
                max_correlation = max(max_correlation, 0.8)
            elif position.symbol.split("/")[0] == symbol.split("/")[0]:
                # 同一基础货币的相关性风险
                max_correlation = max(max_correlation, 0.6)
            elif position.strategy_id == strategy_id:
                # 同一策略的相关性风险
                max_correlation = max(max_correlation, 0.5)

        return min(1.0, max_correlation / self.risk_control_config.max_correlation)

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """
        根据风险评分确定风险等级
        """
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    async def _calculate_max_allowed_position(
        self, symbol: str, strategy_id: str, strategy_metrics: Dict[str, Any]
    ) -> float:
        """
        计算最大允许仓位
        """
        # 基础最大仓位
        base_max = self.risk_control_config.max_position_size

        # 根据策略表现调整
        sharpe_ratio = strategy_metrics.get("sharpe_ratio", 0)
        max_drawdown = abs(strategy_metrics.get("max_drawdown", 0))

        # 夏普比率调整因子
        sharpe_factor = min(
            1.5, max(0.5, sharpe_ratio / self.risk_control_config.min_sharpe_ratio)
        )

        # 回撤调整因子
        drawdown_factor = max(
            0.3, 1 - (max_drawdown / self.risk_control_config.max_drawdown_threshold)
        )

        # 组合风险调整
        portfolio_factor = max(
            0.5,
            1
            - (
                self.current_portfolio_risk
                / self.risk_control_config.max_portfolio_risk
            ),
        )

        # 计算调整后的最大仓位
        adjusted_max = base_max * sharpe_factor * drawdown_factor * portfolio_factor

        return max(0.01, min(self.risk_control_config.max_position_size, adjusted_max))

    def _determine_control_action(
        self, risk_level: RiskLevel, adjusted_position: float, original_position: float
    ) -> ActionType:
        """
        确定风险控制动作
        """
        if self.emergency_mode or risk_level == RiskLevel.CRITICAL:
            return ActionType.EMERGENCY_EXIT
        elif risk_level == RiskLevel.HIGH:
            return ActionType.BLOCK
        elif adjusted_position < original_position * 0.8:
            return ActionType.REDUCE
        else:
            return ActionType.ALLOW

    async def _calculate_stop_levels(
        self, symbol: str, current_price: float, strategy_metrics: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        计算止损止盈价格
        """
        try:
            # 动态调整止损止盈比例
            volatility = strategy_metrics.get("volatility", 0.02)

            # 根据波动率调整止损距离
            stop_loss_pct = max(
                self.stop_loss_config.default_stop_loss, volatility * 1.5
            )
            take_profit_pct = max(
                self.stop_loss_config.default_take_profit, stop_loss_pct * 2
            )

            # 计算价格
            stop_loss_price = current_price * (1 - stop_loss_pct)
            take_profit_price = current_price * (1 + take_profit_pct)

            return stop_loss_price, take_profit_price

        except Exception as e:
            self.logger.warning(f"计算止损止盈失败: {e}")
            return None, None

    def _generate_risk_reasoning(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        action: ActionType,
        adjusted_position: float,
        original_position: float,
    ) -> str:
        """
        生成风险控制决策理由
        """
        reasons = []

        # 风险评分说明
        reasons.append(f"风险评分: {risk_score:.3f} ({risk_level.value})")

        # 动作说明
        if action == ActionType.EMERGENCY_EXIT:
            reasons.append("紧急退出：风险过高或进入紧急模式")
        elif action == ActionType.BLOCK:
            reasons.append("阻止交易：风险等级过高")
        elif action == ActionType.REDUCE:
            reduction_pct = (1 - adjusted_position / original_position) * 100
            reasons.append(f"减少仓位：降低 {reduction_pct:.1f}% 以控制风险")
        else:
            reasons.append("允许交易：风险在可接受范围内")

        # 组合风险说明
        if (
            self.current_portfolio_risk
            > self.risk_control_config.max_portfolio_risk * 0.8
        ):
            reasons.append(f"组合风险接近上限: {self.current_portfolio_risk:.3f}")

        return "; ".join(reasons)

    async def update_position(
        self, symbol: str, strategy_id: str, position_data: Dict[str, Any]
    ):
        """
        更新仓位信息

        Args:
            symbol: 交易对符号
            strategy_id: 策略ID
            position_data: 仓位数据
        """
        try:
            position_key = f"{symbol}_{strategy_id}"

            # 计算风险指标
            risk_score = await self._calculate_position_risk_score(
                symbol,
                strategy_id,
                position_data.get("position_size", 0),
                position_data.get("metrics", {}),
            )

            # 创建或更新仓位风险对象
            position_risk = PositionRisk(
                symbol=symbol,
                strategy_id=strategy_id,
                current_position=position_data.get("position_size", 0),
                max_position_allowed=await self._calculate_max_allowed_position(
                    symbol, strategy_id, position_data.get("metrics", {})
                ),
                current_value=position_data.get("current_value", 0),
                unrealized_pnl=position_data.get("unrealized_pnl", 0),
                risk_score=risk_score,
                stop_loss_price=position_data.get("stop_loss_price"),
                take_profit_price=position_data.get("take_profit_price"),
                risk_level=self._determine_risk_level(risk_score),
                last_updated=datetime.now(),
            )

            self.data.current_positions[position_key] = position_risk

            # 更新组合风险
            await self._update_portfolio_risk()

            self.logger.debug(f"仓位更新完成: {position_key}")

        except Exception as e:
            self.logger.error(f"更新仓位失败: {e}")

    async def _update_portfolio_risk(self):
        """
        更新组合风险
        """
        if not self.data.current_positions:
            self.state.current_portfolio_risk = 0.0
            return

        # 计算组合总风险
        total_risk = 0.0
        total_value = 0.0

        for position in self.data.current_positions.values():
            position_value = abs(position.current_value)
            position_risk = position.risk_score * position_value

            total_risk += position_risk
            total_value += position_value

        # 计算风险比例
        if total_value > 0:
            self.state.current_portfolio_risk = total_risk / total_value
        else:
            self.state.current_portfolio_risk = 0.0

        # 检查是否需要进入紧急模式
        if (
            self.state.current_portfolio_risk
            > self.risk_control_config.max_portfolio_risk * 1.2
        ):
            self.state.emergency_mode = True
            self.logger.warning(f"进入紧急模式：组合风险 {self.state.current_portfolio_risk:.3f}")
        elif (
            self.state.current_portfolio_risk
            < self.risk_control_config.max_portfolio_risk * 0.8
        ):
            self.state.emergency_mode = False

    async def perform_stress_test(
        self, scenarios: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        执行压力测试

        Args:
            scenarios: 压力测试场景，如果为None则使用默认场景

        Returns:
            Dict[str, Any]: 压力测试结果
        """
        if scenarios is None:
            scenarios = self.data.stress_test_scenarios

        stress_test_results = {
            "timestamp": datetime.now().isoformat(),
            "current_portfolio_risk": self.state.current_portfolio_risk,
            "scenarios": {},
        }

        for scenario in scenarios:
            scenario_name = scenario["name"]
            scenario_result = await self._run_stress_scenario(scenario)
            stress_test_results["scenarios"][scenario_name] = scenario_result

        # 计算整体压力测试评分
        stress_test_results["overall_score"] = self._calculate_stress_test_score(
            stress_test_results["scenarios"]
        )

        self.logger.info(f"压力测试完成，整体评分: {stress_test_results['overall_score']:.3f}")
        return stress_test_results

    async def _run_stress_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行单个压力测试场景
        """
        scenario_result = {
            "scenario_name": scenario["name"],
            "parameters": scenario,
            "position_impacts": {},
            "total_loss": 0.0,
            "max_drawdown": 0.0,
            "survival_probability": 0.0,
        }

        total_portfolio_value = sum(
            pos.current_value for pos in self.data.current_positions.values()
        )
        total_loss = 0.0

        for pos_key, position in self.data.current_positions.items():
            # 计算该仓位在压力场景下的损失
            position_loss = self._calculate_position_stress_loss(position, scenario)

            scenario_result["position_impacts"][pos_key] = {
                "current_value": position.current_value,
                "stress_loss": position_loss,
                "loss_percentage": position_loss / position.current_value
                if position.current_value > 0
                else 0,
            }

            total_loss += position_loss

        # 计算组合层面的影响
        if total_portfolio_value > 0:
            scenario_result["total_loss"] = total_loss
            scenario_result["max_drawdown"] = total_loss / total_portfolio_value
            scenario_result["survival_probability"] = max(
                0, 1 - scenario_result["max_drawdown"] / 0.5
            )

        return scenario_result

    def _calculate_position_stress_loss(
        self, position: PositionRisk, scenario: Dict[str, Any]
    ) -> float:
        """
        计算仓位在压力场景下的损失
        """
        # 基础市场冲击
        market_drop = scenario.get("market_drop", 0)
        base_loss = position.current_value * abs(market_drop)

        # 波动率冲击
        volatility_spike = scenario.get("volatility_spike", 1.0)
        volatility_loss = (
            position.current_value * position.risk_score * (volatility_spike - 1) * 0.1
        )

        # 流动性冲击
        liquidity_drop = scenario.get("liquidity_drop", 0)
        liquidity_loss = position.current_value * liquidity_drop * 0.05

        return base_loss + volatility_loss + liquidity_loss

    def _calculate_stress_test_score(self, scenario_results: Dict[str, Any]) -> float:
        """
        计算压力测试综合评分
        """
        if not scenario_results:
            return 0.0

        total_score = 0.0
        scenario_count = len(scenario_results)

        for scenario_result in scenario_results.values():
            # 基于生存概率计算评分
            survival_prob = scenario_result.get("survival_probability", 0)
            scenario_score = survival_prob * 100
            total_score += scenario_score

        return total_score / scenario_count if scenario_count > 0 else 0.0

    async def get_risk_report(self) -> Dict[str, Any]:
        """
        生成风险报告

        Returns:
            Dict[str, Any]: 详细的风险报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_overview": {
                "total_positions": len(self.data.current_positions),
                "current_portfolio_risk": self.state.current_portfolio_risk,
                "max_portfolio_risk": self.risk_control_config.max_portfolio_risk,
                "emergency_mode": self.state.emergency_mode,
                "risk_utilization": self.state.current_portfolio_risk
                / self.risk_control_config.max_portfolio_risk,
            },
            "position_details": {},
            "risk_metrics": {},
            "recommendations": [],
        }

        # 仓位详情
        for pos_key, position in self.data.current_positions.items():
            report["position_details"][pos_key] = asdict(position)

        # 风险指标
        if self.data.risk_metrics_history:
            latest_metrics = self.data.risk_metrics_history[-1]
            report["risk_metrics"] = asdict(latest_metrics)

        # 生成建议
        recommendations = await self._generate_risk_recommendations()
        report["recommendations"] = recommendations

        return report

    async def _generate_risk_recommendations(self) -> List[str]:
        """
        生成风险管理建议
        """
        recommendations = []

        # 组合风险建议
        if (
            self.state.current_portfolio_risk
            > self.risk_control_config.max_portfolio_risk * 0.9
        ):
            recommendations.append("组合风险接近上限，建议减少新增仓位")
        elif (
            self.state.current_portfolio_risk
            < self.risk_control_config.max_portfolio_risk * 0.3
        ):
            recommendations.append("组合风险较低，可以考虑增加仓位")

        # 仓位集中度建议
        if len(self.data.current_positions) < 3:
            recommendations.append("仓位过于集中，建议增加策略多样性")

        # 高风险仓位建议
        high_risk_positions = [
            pos
            for pos in self.current_positions.values()
            if pos.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

        if high_risk_positions:
            recommendations.append(f"发现 {len(high_risk_positions)} 个高风险仓位，建议重点监控")

        # 紧急模式建议
        if self.emergency_mode:
            recommendations.append("当前处于紧急模式，建议立即减少风险敞口")

        return recommendations

    def get_risk_limits(self) -> Dict[str, Any]:
        """
        获取当前风险限制配置

        Returns:
            Dict[str, Any]: 风险限制配置
        """
        return {
            "max_portfolio_risk": self.risk_control_config.max_portfolio_risk,
            "max_position_size": self.risk_control_config.max_position_size,
            "max_daily_loss": self.risk_control_config.max_daily_loss,
            "max_drawdown_threshold": self.risk_control_config.max_drawdown_threshold,
            "min_sharpe_ratio": self.risk_control_config.min_sharpe_ratio,
            "max_correlation": self.risk_control_config.max_correlation,
            "default_stop_loss": self.stop_loss_config.default_stop_loss,
            "default_take_profit": self.stop_loss_config.default_take_profit,
            "trailing_stop_enabled": self.stop_loss_config.trailing_stop_enabled,
        }

    async def update_risk_limits(self, new_limits: Dict[str, Any]):
        """
        更新风险限制配置

        Args:
            new_limits: 新的风险限制配置
        """
        try:
            # 验证新限制的合理性
            if "max_portfolio_risk" in new_limits:
                if not 0 < new_limits["max_portfolio_risk"] <= 0.1:
                    raise ValueError("组合风险限制必须在0-10%之间")
                self.risk_control_config.max_portfolio_risk = new_limits[
                    "max_portfolio_risk"
                ]

            if "max_position_size" in new_limits:
                if not 0 < new_limits["max_position_size"] <= 0.5:
                    raise ValueError("单仓位限制必须在0-50%之间")
                self.risk_control_config.max_position_size = new_limits[
                    "max_position_size"
                ]

            if "max_drawdown_threshold" in new_limits:
                if not 0 < new_limits["max_drawdown_threshold"] <= 0.2:
                    raise ValueError("最大回撤限制必须在0-20%之间")
                self.risk_control_config.max_drawdown_threshold = new_limits[
                    "max_drawdown_threshold"
                ]

            # 更新其他限制
            for key, value in new_limits.items():
                if key in [
                    "max_daily_loss",
                    "min_sharpe_ratio",
                    "max_correlation",
                    "liquidity_threshold",
                ]:
                    setattr(self.risk_control_config, key, value)
                elif key in [
                    "default_stop_loss",
                    "default_take_profit",
                    "trailing_stop_enabled",
                    "trailing_stop_distance",
                ]:
                    setattr(self.stop_loss_config, key, value)
                elif key in ["volatility_lookback", "risk_adjustment_factor"]:
                    setattr(self.risk_adjustment_config, key, value)

            self.logger.info(f"风险限制更新完成: {list(new_limits.keys())}")

        except Exception as e:
            self.logger.error(f"更新风险限制失败: {e}")
            raise

    async def check_position_limits(
        self, symbol: str, proposed_size: float, current_portfolio: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        检查仓位限制

        Args:
            symbol: 交易对符号
            proposed_size: 建议仓位大小
            current_portfolio: 当前组合仓位

        Returns:
            Dict[str, Any]: 检查结果
        """
        try:
            # 检查单仓位限制
            position_approved = (
                proposed_size <= self.risk_control_config.max_position_size
            )

            # 检查组合风险限制
            total_exposure = sum(
                abs(size) for size in current_portfolio.values()
            ) + abs(proposed_size)
            portfolio_approved = total_exposure <= 1.0  # 总敞口不超过100%

            # 检查相关性风险
            correlation_approved = True
            if symbol in current_portfolio:
                total_symbol_exposure = abs(current_portfolio[symbol]) + abs(
                    proposed_size
                )
                correlation_approved = (
                    total_symbol_exposure <= self.risk_control_config.max_position_size
                )

            approved = position_approved and portfolio_approved and correlation_approved

            result = {
                "approved": approved,
                "position_check": position_approved,
                "portfolio_check": portfolio_approved,
                "correlation_check": correlation_approved,
                "max_allowed_size": self.risk_control_config.max_position_size,
                "proposed_size": proposed_size,
                "reason": self._get_position_limit_reason(
                    position_approved, portfolio_approved, correlation_approved
                ),
            }

            self.logger.debug(f"仓位限制检查完成: {symbol} - {approved}")
            return result

        except Exception as e:
            self.logger.error(f"仓位限制检查失败: {e}")
            return {
                "approved": False,
                "position_check": False,
                "portfolio_check": False,
                "correlation_check": False,
                "max_allowed_size": 0.0,
                "proposed_size": proposed_size,
                "reason": f"检查失败: {str(e)}",
            }

    def _get_position_limit_reason(
        self, position_check: bool, portfolio_check: bool, correlation_check: bool
    ) -> str:
        """
        获取仓位限制检查的原因说明
        """
        if not position_check:
            return "单仓位超过限制"
        elif not portfolio_check:
            return "组合总敞口超过限制"
        elif not correlation_check:
            return "相关性风险过高"
        else:
            return "通过所有检查"

    async def calculate_risk_metrics(
        self, backtest_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算风险指标

        Args:
            backtest_result: 回测结果

        Returns:
            Dict[str, Any]: 风险指标
        """
        try:
            # 提取回测数据
            returns = backtest_result.get("returns", [])
            equity_curve = backtest_result.get("equity_curve", [])

            if not returns or not equity_curve:
                self.logger.warning("回测结果数据不足，使用默认风险指标")
                return self._get_default_risk_metrics()

            # 转换为numpy数组进行计算
            returns_array = np.array(returns)
            equity_array = np.array(equity_curve)

            # 计算基础风险指标
            risk_metrics = {
                "max_drawdown": self._calculate_max_drawdown(equity_array),
                "volatility": np.std(returns_array) * np.sqrt(252),  # 年化波动率
                "sharpe_ratio": self._calculate_sharpe_ratio(returns_array),
                "sortino_ratio": self._calculate_sortino_ratio(returns_array),
                "var_95": np.percentile(returns_array, 5),  # 95% VaR
                "var_99": np.percentile(returns_array, 1),  # 99% VaR
                "skewness": self._calculate_skewness(returns_array),
                "kurtosis": self._calculate_kurtosis(returns_array),
                "calmar_ratio": self._calculate_calmar_ratio(
                    returns_array, equity_array
                ),
                "win_rate": self._calculate_win_rate(returns_array),
                "profit_factor": self._calculate_profit_factor(returns_array),
                "timestamp": datetime.now().isoformat(),
            }

            # 保存到历史记录
            risk_metrics_obj = RiskMetrics(
                max_drawdown=risk_metrics["max_drawdown"],
                current_drawdown=self._calculate_current_drawdown(equity_array),
                sharpe_ratio=risk_metrics["sharpe_ratio"],
                sortino_ratio=risk_metrics["sortino_ratio"],
                var_95=risk_metrics["var_95"],
                var_99=risk_metrics["var_99"],
                beta=0.0,  # 需要市场数据计算
                volatility=risk_metrics["volatility"],
                correlation_risk=0.0,  # 需要组合数据计算
                liquidity_risk=0.0,  # 需要流动性数据计算
                concentration_risk=0.0,  # 需要持仓数据计算
                timestamp=datetime.now(),
            )

            self.risk_metrics_history.append(risk_metrics_obj)

            # 保持历史记录在合理范围内
            if len(self.risk_metrics_history) > 100:
                self.risk_metrics_history = self.risk_metrics_history[-100:]

            self.logger.debug("风险指标计算完成")
            return risk_metrics

        except Exception as e:
            self.logger.error(f"风险指标计算失败: {e}")
            return self._get_default_risk_metrics()

    def _get_default_risk_metrics(self) -> Dict[str, Any]:
        """
        获取默认风险指标
        """
        return {
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "var_95": 0.0,
            "var_99": 0.0,
            "skewness": 0.0,
            "kurtosis": 0.0,
            "calmar_ratio": 0.0,
            "win_rate": 0.0,
            "profit_factor": 1.0,
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_max_drawdown(self, equity_curve: np.ndarray) -> float:
        """
        计算最大回撤
        """
        if len(equity_curve) == 0:
            return 0.0

        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        return abs(np.min(drawdown))

    def _calculate_current_drawdown(self, equity_curve: np.ndarray) -> float:
        """
        计算当前回撤
        """
        if len(equity_curve) == 0:
            return 0.0

        peak = np.max(equity_curve)
        current_value = equity_curve[-1]
        return abs((current_value - peak) / peak) if peak > 0 else 0.0

    def _calculate_sharpe_ratio(
        self, returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> float:
        """
        计算夏普比率
        """
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0

        excess_returns = np.mean(returns) * 252 - risk_free_rate  # 年化超额收益
        volatility = np.std(returns) * np.sqrt(252)  # 年化波动率

        return excess_returns / volatility if volatility > 0 else 0.0

    def _calculate_sortino_ratio(
        self, returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> float:
        """
        计算索提诺比率
        """
        if len(returns) == 0:
            return 0.0

        excess_returns = np.mean(returns) * 252 - risk_free_rate
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return float("inf") if excess_returns > 0 else 0.0

        downside_deviation = np.std(downside_returns) * np.sqrt(252)

        return excess_returns / downside_deviation if downside_deviation > 0 else 0.0

    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """
        计算偏度
        """
        if len(returns) < 3:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        skewness = np.mean(((returns - mean_return) / std_return) ** 3)
        return skewness

    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """
        计算峰度
        """
        if len(returns) < 4:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
        return kurtosis

    def _calculate_calmar_ratio(
        self, returns: np.ndarray, equity_curve: np.ndarray
    ) -> float:
        """
        计算卡玛比率
        """
        if len(returns) == 0 or len(equity_curve) == 0:
            return 0.0

        annual_return = np.mean(returns) * 252
        max_drawdown = self._calculate_max_drawdown(equity_curve)

        return annual_return / max_drawdown if max_drawdown > 0 else 0.0

    def _calculate_win_rate(self, returns: np.ndarray) -> float:
        """
        计算胜率
        """
        if len(returns) == 0:
            return 0.0

        winning_trades = np.sum(returns > 0)
        total_trades = len(returns)

        return winning_trades / total_trades if total_trades > 0 else 0.0

    def _calculate_profit_factor(self, returns: np.ndarray) -> float:
        """
        计算盈利因子
        """
        if len(returns) == 0:
            return 1.0

        gross_profit = np.sum(returns[returns > 0])
        gross_loss = abs(np.sum(returns[returns < 0]))

        return (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf")
            if gross_profit > 0
            else 1.0
        )

    async def cleanup(self):
        """
        清理资源
        """
        self.logger.info("风险管理器清理完成")


def create_risk_manager(config: Dict[str, Any]) -> RiskManager:
    """
    创建风险管理器实例

    Args:
        config: 配置字典

    Returns:
        RiskManager: 风险管理器实例
    """
    return RiskManager(config)
