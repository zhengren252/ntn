#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格交易策略
基于价格网格的自动化交易策略

策略原理：
1. 在价格区间内设置多个买卖网格
2. 价格下跌时逐步买入
3. 价格上涨时逐步卖出
4. 适合震荡市场

核心参数：
- grid_num: 网格数量
- price_range: 价格区间
- profit_ratio: 利润比例
- base_amount: 基础交易量
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from optimizer.strategies.base_strategy import BaseStrategy, StrategySignal


@dataclass
class GridStrategyConfig:
    """网格策略配置"""

    grid_num: int = 10
    price_range_pct: float = 0.1  # 价格区间百分比
    profit_ratio: float = 0.01  # 利润比例1%
    base_amount: float = 100  # 基础交易量


@dataclass
class GridState:
    """网格状态"""

    center_price: float = 0.0
    grid_upper_bound: float = 0.0
    grid_lower_bound: float = 0.0
    grid_step: float = 0.0
    grid_levels: List[float] = field(default_factory=list)
    grid_positions: Dict[str, Any] = field(default_factory=dict)  # 每个网格的持仓状态


@dataclass
class MarketDataCache:
    """市场数据缓存"""

    price_history: List[float] = field(default_factory=list)
    volume_history: List[float] = field(default_factory=list)


class GridTradingStrategy(BaseStrategy):
    """
    网格交易策略实现

    遵循NeuroTrade Nexus核心设计理念：
    - 参数化配置
    - 风险控制
    - 性能监控
    - 标准化接口
    """

    def __init__(self, strategy_id: str, symbol: str, parameters: Dict[str, Any]):
        super().__init__(strategy_id, symbol, parameters)

        # 网格策略配置
        self.grid_config = GridStrategyConfig(
            grid_num=parameters.get("grid_num", 10),
            price_range_pct=parameters.get("price_range_pct", 0.1),
            profit_ratio=parameters.get("profit_ratio", 0.01),
            base_amount=parameters.get("base_amount", 100),
        )

        # 网格状态
        self.grid_state = GridState()

        # 市场数据缓存
        self.market_data = MarketDataCache()

        self.logger.info(
            f"网格交易策略初始化: 网格数={self.grid_config.grid_num}, 利润比例={self.grid_config.profit_ratio:.2%}"
        )

    def initialize(self, historical_data: pd.DataFrame) -> bool:
        """
        策略初始化

        Args:
            historical_data: 历史数据，包含 'close', 'volume' 等列

        Returns:
            bool: 初始化是否成功
        """
        try:
            if historical_data.empty:
                self.logger.error("历史数据为空")
                return False

            # 计算中心价格（使用最近20天的平均价格）
            recent_prices = historical_data["close"].tail(20)
            self.grid_state.center_price = recent_prices.mean()

            # 计算价格区间
            price_volatility = recent_prices.std()
            range_size = max(
                self.grid_state.center_price * self.grid_config.price_range_pct,
                price_volatility * 2,
            )

            self.grid_state.grid_upper_bound = (
                self.grid_state.center_price + range_size / 2
            )
            self.grid_state.grid_lower_bound = (
                self.grid_state.center_price - range_size / 2
            )
            self.grid_state.grid_step = range_size / self.grid_config.grid_num

            # 生成网格水平
            self.grid_state.grid_levels = []
            for i in range(self.grid_config.grid_num + 1):
                level_price = (
                    self.grid_state.grid_lower_bound + i * self.grid_state.grid_step
                )
                self.grid_state.grid_levels.append(level_price)

            # 初始化网格持仓状态
            self.grid_state.grid_positions = {
                level: {"has_position": False, "buy_price": 0.0}
                for level in self.grid_state.grid_levels
            }

            # 缓存历史数据
            self.market_data.price_history = historical_data["close"].tolist()
            if "volume" in historical_data.columns:
                self.market_data.volume_history = historical_data["volume"].tolist()

            self.is_initialized = True

            self.logger.info(
                f"网格初始化完成: 中心价格={self.center_price:.4f}, "
                f"区间=[{self.grid_lower_bound:.4f}, {self.grid_upper_bound:.4f}], "
                f"步长={self.grid_step:.4f}"
            )

            return True

        except Exception as e:
            self.logger.error(f"策略初始化失败: {e}")
            return False

    def generate_signal(self, current_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """
        生成交易信号

        Args:
            current_data: 当前市场数据
            {
                'price': float,
                'volume': float,
                'timestamp': datetime,
                'bid': float (可选),
                'ask': float (可选)
            }

        Returns:
            Optional[StrategySignal]: 交易信号
        """
        try:
            current_price = current_data.get("price", 0)
            current_time = current_data.get("timestamp", datetime.now())

            if current_price <= 0:
                return None

            # 更新价格历史
            self.market_data.price_history.append(current_price)
            if len(self.market_data.price_history) > 1000:  # 保持最近1000个价格
                self.market_data.price_history.pop(0)

            # 检查是否需要调整网格
            if self._should_adjust_grid(current_price):
                self._adjust_grid(current_price)

            # 查找最近的网格水平
            nearest_grid_level = self._find_nearest_grid_level(current_price)

            if nearest_grid_level is None:
                return None

            # 生成交易信号
            signal = self._generate_grid_signal(
                current_price, nearest_grid_level, current_time
            )

            return signal

        except Exception as e:
            self.logger.error(f"信号生成失败: {e}")
            return None

    def _should_adjust_grid(self, current_price: float) -> bool:
        """
        检查是否需要调整网格
        """
        # 如果价格超出网格范围，需要调整
        if (
            current_price > self.grid_state.grid_upper_bound * 1.1
            or current_price < self.grid_state.grid_lower_bound * 0.9
        ):
            return True

        # 如果价格波动性发生显著变化，也需要调整
        if len(self.market_data.price_history) >= 50:
            recent_volatility = np.std(self.market_data.price_history[-20:])
            historical_volatility = np.std(self.market_data.price_history[-50:-20])

            if (
                abs(recent_volatility - historical_volatility) / historical_volatility
                > 0.5
            ):
                return True

        return False

    def _adjust_grid(self, current_price: float):
        """
        调整网格参数
        """
        try:
            self.logger.info(f"调整网格，当前价格: {current_price:.4f}")

            # 重新计算中心价格
            if len(self.market_data.price_history) >= 20:
                self.grid_state.center_price = np.mean(
                    self.market_data.price_history[-20:]
                )
            else:
                self.grid_state.center_price = current_price

            # 重新计算价格区间
            if len(self.market_data.price_history) >= 20:
                price_volatility = np.std(self.market_data.price_history[-20:])
                range_size = max(
                    self.grid_state.center_price * self.grid_config.price_range_pct,
                    price_volatility * 2,
                )
            else:
                range_size = (
                    self.grid_state.center_price * self.grid_config.price_range_pct
                )

            self.grid_state.grid_upper_bound = (
                self.grid_state.center_price + range_size / 2
            )
            self.grid_state.grid_lower_bound = (
                self.grid_state.center_price - range_size / 2
            )
            self.grid_state.grid_step = range_size / self.grid_config.grid_num

            # 重新生成网格水平
            old_positions = self.grid_state.grid_positions.copy()
            self.grid_state.grid_levels = []

            for i in range(self.grid_config.grid_num + 1):
                level_price = (
                    self.grid_state.grid_lower_bound + i * self.grid_state.grid_step
                )
                self.grid_state.grid_levels.append(level_price)

            # 重新初始化网格持仓状态，保留有效持仓
            new_positions = {}
            for level in self.grid_state.grid_levels:
                new_positions[level] = {"has_position": False, "buy_price": 0.0}

                # 尝试从旧持仓中找到最接近的持仓
                closest_old_level = min(
                    old_positions.keys(), key=lambda x: abs(x - level)
                )

                if abs(closest_old_level - level) < self.grid_state.grid_step * 0.5:
                    new_positions[level] = old_positions[closest_old_level]

            self.grid_state.grid_positions = new_positions

            self.logger.info(
                "网格调整完成: 新区间=[%.4f, %.4f]",
                self.grid_state.grid_lower_bound,
                self.grid_state.grid_upper_bound,
            )

        except Exception as e:
            self.logger.error(f"网格调整失败: {e}")

    def _find_nearest_grid_level(self, current_price: float) -> Optional[float]:
        """
        查找最近的网格水平
        """
        if not self.grid_state.grid_levels:
            return None

        # 找到最接近当前价格的网格水平
        nearest_level = min(
            self.grid_state.grid_levels, key=lambda x: abs(x - current_price)
        )

        # 只有当价格足够接近网格水平时才触发交易
        if abs(current_price - nearest_level) <= self.grid_state.grid_step * 0.1:
            return nearest_level

        return None

    def _generate_grid_signal(
        self, current_price: float, grid_level: float, current_time: datetime
    ) -> Optional[StrategySignal]:
        """
        基于网格水平生成交易信号
        """
        try:
            grid_position = self.grid_state.grid_positions[grid_level]

            # 买入信号：价格接近网格水平且该水平没有持仓
            if not grid_position["has_position"]:
                # 计算买入量（基于网格水平调整）
                grid_index = self.grid_state.grid_levels.index(grid_level)
                # 越低的网格买入量越大
                quantity_multiplier = (
                    1 + (len(self.grid_state.grid_levels) - grid_index - 1) * 0.1
                )
                quantity = self.grid_config.base_amount * quantity_multiplier

                # 生成买入信号
                signal = StrategySignal(
                    timestamp=current_time,
                    symbol=self.symbol,
                    action="BUY",
                    price=current_price,
                    quantity=quantity,
                    confidence=0.8,
                    reason=f"网格买入 @ {grid_level:.4f}",
                    metadata={
                        "grid_level": grid_level,
                        "grid_index": grid_index,
                        "strategy_type": "grid_buy",
                    },
                )

                # 更新网格持仓状态
                self.grid_state.grid_positions[grid_level] = {
                    "has_position": True,
                    "buy_price": current_price,
                }

                return signal

            # 卖出信号：价格上涨达到利润目标
            elif grid_position["has_position"]:
                buy_price = grid_position["buy_price"]
                profit_pct = (current_price - buy_price) / buy_price

                if profit_pct >= self.grid_config.profit_ratio:
                    # 计算卖出量
                    grid_index = self.grid_state.grid_levels.index(grid_level)
                    quantity_multiplier = (
                        1 + (len(self.grid_state.grid_levels) - grid_index - 1) * 0.1
                    )
                    quantity = self.grid_config.base_amount * quantity_multiplier

                    # 生成卖出信号
                    signal = StrategySignal(
                        timestamp=current_time,
                        symbol=self.symbol,
                        action="SELL",
                        price=current_price,
                        quantity=quantity,
                        confidence=0.9,
                        reason=f"网格卖出 @ {grid_level:.4f}, 利润 {profit_pct:.2%}",
                        metadata={
                            "grid_level": grid_level,
                            "grid_index": grid_index,
                            "buy_price": buy_price,
                            "profit_pct": profit_pct,
                            "strategy_type": "grid_sell",
                        },
                    )

                    # 重置网格持仓状态
                    self.grid_state.grid_positions[grid_level] = {
                        "has_position": False,
                        "buy_price": 0.0,
                    }

                    return signal

            return None

        except Exception as e:
            self.logger.error(f"网格信号生成失败: {e}")
            return None

    def get_parameter_ranges(self) -> Dict[str, Dict[str, Any]]:
        """
        获取参数优化范围

        Returns:
            Dict: 参数范围定义
        """
        return {
            "grid_num": {"type": "int", "min": 5, "max": 50, "step": 1},
            "price_range_pct": {"type": "float", "min": 0.05, "max": 0.3, "step": 0.01},
            "profit_ratio": {"type": "float", "min": 0.005, "max": 0.05, "step": 0.001},
            "base_amount": {"type": "float", "min": 50, "max": 500, "step": 10},
        }

    def _reinitialize_components(self):
        """
        重新初始化组件
        """
        # 更新策略参数
        self.grid_config.grid_num = self.parameters.get(
            "grid_num", self.grid_config.grid_num
        )
        self.grid_config.price_range_pct = self.parameters.get(
            "price_range_pct", self.grid_config.price_range_pct
        )
        self.grid_config.profit_ratio = self.parameters.get(
            "profit_ratio", self.grid_config.profit_ratio
        )
        self.grid_config.base_amount = self.parameters.get(
            "base_amount", self.grid_config.base_amount
        )

        # 如果已经初始化，需要重新计算网格
        if self.is_initialized and self.market_data.price_history:
            current_price = self.market_data.price_history[-1]
            self._adjust_grid(current_price)

    def get_grid_status(self) -> Dict[str, Any]:
        """
        获取网格状态信息

        Returns:
            Dict: 网格状态
        """
        active_positions = sum(
            1 for pos in self.grid_state.grid_positions.values() if pos["has_position"]
        )
        total_invested = sum(
            pos["buy_price"] * self.grid_config.base_amount
            for pos in self.grid_state.grid_positions.values()
            if pos["has_position"]
        )

        return {
            "center_price": self.grid_state.center_price,
            "grid_upper_bound": self.grid_state.grid_upper_bound,
            "grid_lower_bound": self.grid_state.grid_lower_bound,
            "grid_step": self.grid_state.grid_step,
            "total_grids": len(self.grid_state.grid_levels),
            "active_positions": active_positions,
            "total_invested": total_invested,
            "grid_levels": self.grid_state.grid_levels,
            "grid_positions": self.grid_state.grid_positions,
        }

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息（重写父类方法）

        Returns:
            Dict: 策略信息
        """
        base_info = super().get_strategy_info()
        base_info["grid_status"] = self.get_grid_status()
        return base_info
