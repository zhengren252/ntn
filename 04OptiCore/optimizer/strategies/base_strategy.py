#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础策略接口
定义所有策略必须实现的接口和通用功能

核心功能：
1. 策略接口定义
2. 参数管理
3. 信号生成
4. 风险控制
5. 性能统计
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class StrategyPerformanceMetrics:
    """策略性能指标"""

    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_value: float = 0.0


@dataclass
class StrategyRiskConfig:
    """策略风险控制配置"""

    max_position_size: float = 1.0
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    max_daily_trades: int = 10


@dataclass
class StrategyState:
    """策略状态"""

    is_initialized: bool = False
    current_position: float = 0.0
    entry_price: float = 0.0
    last_signal_time: Optional[datetime] = None


@dataclass
class StrategySignal:
    """策略信号"""

    timestamp: datetime
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    price: float
    quantity: float
    confidence: float  # 0-1
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyParameters:
    """策略参数"""

    strategy_id: str
    symbol: str
    parameters: Dict[str, Any]
    risk_params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class BaseStrategy(ABC):
    """
    基础策略抽象类

    所有策略必须继承此类并实现抽象方法
    遵循NeuroTrade Nexus核心设计理念：
    - 标准化接口
    - 参数化配置
    - 风险控制
    - 性能监控
    """

    def __init__(self, strategy_id: str, symbol: str, parameters: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.parameters = parameters
        self.logger = logging.getLogger(f"{__name__}.{strategy_id}")

        # 策略状态
        self.state = StrategyState()

        # 性能统计
        self.performance = StrategyPerformanceMetrics()

        # 风险控制参数
        self.risk_config = StrategyRiskConfig(
            max_position_size=parameters.get("max_position_size", 1.0),
            stop_loss_pct=parameters.get("stop_loss_pct", 0.02),
            take_profit_pct=parameters.get("take_profit_pct", 0.04),
            max_daily_trades=parameters.get("max_daily_trades", 10),
        )

        # 交易历史
        self.trade_history: List[Dict[str, Any]] = []
        self.signal_history: List[StrategySignal] = []

        self.logger.info("策略 %s 初始化完成", strategy_id)

    @abstractmethod
    def initialize(self, historical_data: pd.DataFrame) -> bool:
        """
        策略初始化

        Args:
            historical_data: 历史数据

        Returns:
            bool: 初始化是否成功
        """

    @abstractmethod
    def generate_signal(self, current_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """
        生成交易信号

        Args:
            current_data: 当前市场数据

        Returns:
            Optional[StrategySignal]: 交易信号，无信号时返回None
        """

    @abstractmethod
    def get_parameter_ranges(self) -> Dict[str, Dict[str, Any]]:
        """
        获取参数优化范围

        Returns:
            Dict: 参数范围定义
            格式: {
                'param_name': {
                    'type': 'int' | 'float',
                    'min': min_value,
                    'max': max_value,
                    'step': step_size (可选)
                }
            }
        """

    def update_parameters(self, new_parameters: Dict[str, Any]) -> bool:
        """
        更新策略参数

        Args:
            new_parameters: 新参数

        Returns:
            bool: 更新是否成功
        """
        try:
            # 验证参数
            if not self._validate_parameters(new_parameters):
                return False

            # 更新参数
            self.parameters.update(new_parameters)

            # 重新初始化相关组件
            self._reinitialize_components()

            self.logger.info("参数更新成功: %s", new_parameters)
            return True

        except (ValueError, AttributeError, TypeError) as e:
            self.logger.error("参数更新失败: %s", e)
            return False

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        验证参数有效性
        """
        try:
            param_ranges = self.get_parameter_ranges()

            for param_name, param_value in parameters.items():
                if param_name not in param_ranges:
                    self.logger.warning("未知参数: %s", param_name)
                    continue

                param_range = param_ranges[param_name]

                # 检查类型
                if param_range["type"] == "int" and not isinstance(param_value, int):
                    self.logger.error("参数 %s 类型错误，期望 int", param_name)
                    return False

                if param_range["type"] == "float" and not isinstance(
                    param_value, (int, float)
                ):
                    self.logger.error("参数 %s 类型错误，期望 float", param_name)
                    return False

                # 检查范围
                if param_value < param_range["min"] or param_value > param_range["max"]:
                    self.logger.error(
                        "参数 %s 超出范围 [%s, %s]",
                        param_name,
                        param_range["min"],
                        param_range["max"],
                    )
                    return False

            return True

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error("参数验证失败: %s", e)
            return False

    def _reinitialize_components(self):
        """
        重新初始化组件（子类可重写）
        """
        pass

    def process_market_data(
        self, market_data: Dict[str, Any]
    ) -> Optional[StrategySignal]:
        """
        处理市场数据并生成信号

        Args:
            market_data: 市场数据

        Returns:
            Optional[StrategySignal]: 交易信号
        """
        try:
            # 检查策略是否已初始化
            if not self.state.is_initialized:
                self.logger.warning("策略未初始化")
                return None

            # 风险控制检查
            if not self._risk_control_check(market_data):
                return None

            # 生成信号
            signal = self.generate_signal(market_data)

            if signal:
                # 记录信号
                self.signal_history.append(signal)
                self.state.last_signal_time = signal.timestamp

                # 更新统计信息
                self._update_statistics(signal, market_data)

                self.logger.debug("生成信号: %s @ %s", signal.action, signal.price)

            return signal

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            self.logger.error("处理市场数据失败: %s", e)
            return None

    def _risk_control_check(self, market_data: Dict[str, Any]) -> bool:
        """
        风险控制检查
        """
        try:
            current_time = market_data.get("timestamp", datetime.now())
            current_price = market_data.get("price", 0)

            # 检查每日交易次数限制
            today_trades = sum(
                1
                for trade in self.trade_history
                if trade["timestamp"].date() == current_time.date()
            )

            if today_trades >= self.risk_config.max_daily_trades:
                self.logger.debug("达到每日交易次数限制")
                return False

            # 检查止损
            if self.state.current_position != 0 and self.state.entry_price > 0:
                if self.state.current_position > 0:  # 多头持仓
                    loss_pct = (
                        self.state.entry_price - current_price
                    ) / self.state.entry_price
                    if loss_pct > self.risk_config.stop_loss_pct:
                        self.logger.info("触发止损: %.2%", loss_pct)
                        # 这里应该生成平仓信号，但为了简化，直接返回False
                        return False

                else:  # 空头持仓
                    loss_pct = (
                        current_price - self.state.entry_price
                    ) / self.state.entry_price
                    if loss_pct > self.risk_config.stop_loss_pct:
                        self.logger.info("触发止损: %.2%", loss_pct)
                        return False

            return True

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            self.logger.error("风险控制检查失败: %s", e)
            return False

    def _update_statistics(self, signal: StrategySignal, market_data: Dict[str, Any]):
        """
        更新统计信息
        """
        try:
            # 如果是开仓信号
            if signal.action in ["BUY", "SELL"] and self.state.current_position == 0:
                self.state.current_position = (
                    signal.quantity if signal.action == "BUY" else -signal.quantity
                )
                self.state.entry_price = signal.price

            # 如果是平仓信号
            elif signal.action in ["BUY", "SELL"] and self.state.current_position != 0:
                # 计算盈亏
                if self.state.current_position > 0:  # 平多头
                    pnl = (signal.price - self.state.entry_price) * abs(
                        self.state.current_position
                    )
                else:  # 平空头
                    pnl = (self.state.entry_price - signal.price) * abs(
                        self.state.current_position
                    )

                self.performance.total_pnl += pnl
                self.performance.total_trades += 1

                if pnl > 0:
                    self.performance.winning_trades += 1

                # 记录交易
                trade_record = {
                    "timestamp": signal.timestamp,
                    "symbol": signal.symbol,
                    "action": "CLOSE",
                    "entry_price": self.state.entry_price,
                    "exit_price": signal.price,
                    "quantity": abs(self.state.current_position),
                    "pnl": pnl,
                    "pnl_pct": pnl
                    / (self.state.entry_price * abs(self.state.current_position)),
                }

                self.trade_history.append(trade_record)

                # 重置持仓
                self.state.current_position = 0
                self.state.entry_price = 0

            # 更新最大回撤
            current_value = self.performance.total_pnl
            if current_value > self.performance.peak_value:
                self.performance.peak_value = current_value
            else:
                drawdown = (self.performance.peak_value - current_value) / max(
                    self.performance.peak_value, 1
                )
                self.performance.max_drawdown = max(
                    self.performance.max_drawdown, drawdown
                )

        except (ValueError, AttributeError, TypeError, ZeroDivisionError) as e:
            self.logger.error("统计信息更新失败: %s", e)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取策略性能指标

        Returns:
            Dict: 性能指标
        """
        try:
            if self.performance.total_trades == 0:
                return {
                    "total_trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "avg_pnl_per_trade": 0,
                    "max_drawdown": 0,
                    "profit_factor": 0,
                    "sharpe_ratio": 0,
                }

            # 基础指标
            win_rate = self.performance.winning_trades / self.performance.total_trades
            avg_pnl_per_trade = (
                self.performance.total_pnl / self.performance.total_trades
            )

            # 计算盈利因子
            winning_trades_pnl = sum(
                trade["pnl"] for trade in self.trade_history if trade["pnl"] > 0
            )
            losing_trades_pnl = abs(
                sum(trade["pnl"] for trade in self.trade_history if trade["pnl"] < 0)
            )

            profit_factor = winning_trades_pnl / max(losing_trades_pnl, 1)

            # 计算夏普比率（简化版）
            if len(self.trade_history) > 1:
                returns = [trade["pnl_pct"] for trade in self.trade_history]
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = avg_return / max(std_return, 0.001) * np.sqrt(252)  # 年化
            else:
                sharpe_ratio = 0

            return {
                "total_trades": self.performance.total_trades,
                "win_rate": win_rate,
                "total_pnl": self.performance.total_pnl,
                "avg_pnl_per_trade": avg_pnl_per_trade,
                "max_drawdown": self.performance.max_drawdown,
                "profit_factor": profit_factor,
                "sharpe_ratio": sharpe_ratio,
                "total_return": self.performance.total_pnl
                / max(abs(self.state.entry_price), 1000)
                if self.state.entry_price
                else 0,
            }

        except (ValueError, AttributeError, TypeError, ZeroDivisionError) as e:
            self.logger.error("性能指标计算失败: %s", e)
            return {}

    def reset_statistics(self):
        """
        重置统计信息
        """
        self.performance = StrategyPerformanceMetrics()
        self.state = StrategyState()
        self.trade_history.clear()
        self.signal_history.clear()

        self.logger.info("统计信息已重置")

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息

        Returns:
            Dict: 策略信息
        """
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "parameters": self.parameters.copy(),
            "is_initialized": self.state.is_initialized,
            "current_position": self.state.current_position,
            "last_signal_time": self.state.last_signal_time,
            "performance": self.get_performance_metrics(),
        }

    def save_state(self) -> Dict[str, Any]:
        """
        保存策略状态

        Returns:
            Dict: 策略状态
        """
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "parameters": self.parameters,
            "current_position": self.state.current_position,
            "entry_price": self.state.entry_price,
            "total_trades": self.performance.total_trades,
            "winning_trades": self.performance.winning_trades,
            "total_pnl": self.performance.total_pnl,
            "max_drawdown": self.performance.max_drawdown,
            "peak_value": self.performance.peak_value,
            "trade_history": self.trade_history,
            "last_signal_time": self.state.last_signal_time,
        }

    def load_state(self, state: Dict[str, Any]) -> bool:
        """
        加载策略状态

        Args:
            state: 策略状态

        Returns:
            bool: 加载是否成功
        """
        try:
            self.state.current_position = state.get("current_position", 0.0)
            self.state.entry_price = state.get("entry_price", 0.0)
            self.performance.total_trades = state.get("total_trades", 0)
            self.performance.winning_trades = state.get("winning_trades", 0)
            self.performance.total_pnl = state.get("total_pnl", 0.0)
            self.performance.max_drawdown = state.get("max_drawdown", 0.0)
            self.performance.peak_value = state.get("peak_value", 0.0)
            self.trade_history = state.get("trade_history", [])
            self.state.last_signal_time = state.get("last_signal_time")

            self.logger.info("策略状态加载成功")
            return True

        except Exception as e:
            self.logger.error("策略状态加载失败: %s", e)
            return False
