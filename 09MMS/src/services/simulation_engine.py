#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 仿真引擎核心
实现市场微结构仿真的核心逻辑

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import json

from src.models.simulation import ScenarioType, TaskStatus
from src.core.database import DatabaseManager
from src.utils.logger import get_logger, log_async_execution_time
from src.utils.metrics import MetricsCollector

logger = get_logger(__name__)


class OrderType(Enum):
    """订单类型"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """订单方向"""

    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """订单模型"""

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    status: str = "pending"


@dataclass
class MarketState:
    """市场状态"""

    timestamp: datetime
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    last_price: float
    volume: float
    volatility: float
    liquidity_score: float


@dataclass
class SimulationResult:
    """仿真结果"""

    simulation_id: str
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    slippage: float
    fill_probability: float
    price_impact: float
    execution_time: float
    trades: List[Dict]
    market_states: List[MarketState]
    risk_metrics: Dict[str, float]


class MarketDataGenerator:
    """市场数据生成器"""

    def __init__(self, scenario: ScenarioType, base_price: float = 50000.0):
        self.scenario = scenario
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = self._get_scenario_volatility()
        self.liquidity_factor = self._get_scenario_liquidity()

    def _get_scenario_volatility(self) -> float:
        """根据场景获取波动率"""
        volatility_map = {
            ScenarioType.NORMAL: 0.02,
            ScenarioType.BLACK_SWAN: 0.15,
            ScenarioType.HIGH_VOLATILITY: 0.08,
            ScenarioType.LOW_LIQUIDITY: 0.03,
            ScenarioType.FLASH_CRASH: 0.25,
        }
        return volatility_map.get(self.scenario, 0.02)

    def _get_scenario_liquidity(self) -> float:
        """根据场景获取流动性因子"""
        liquidity_map = {
            ScenarioType.NORMAL: 1.0,
            ScenarioType.BLACK_SWAN: 0.3,
            ScenarioType.HIGH_VOLATILITY: 0.7,
            ScenarioType.LOW_LIQUIDITY: 0.4,
            ScenarioType.FLASH_CRASH: 0.1,
        }
        return liquidity_map.get(self.scenario, 1.0)

    def generate_market_state(self, timestamp: datetime) -> MarketState:
        """生成市场状态"""
        # 价格随机游走
        price_change = np.random.normal(0, self.volatility * self.current_price * 0.01)

        # 特殊场景处理
        if self.scenario == ScenarioType.FLASH_CRASH:
            # 模拟闪崩
            if np.random.random() < 0.001:  # 0.1%概率发生闪崩
                price_change = -self.current_price * 0.1  # 10%下跌
        elif self.scenario == ScenarioType.BLACK_SWAN:
            # 模拟黑天鹅事件
            if np.random.random() < 0.0001:  # 0.01%概率
                price_change = np.random.choice([-1, 1]) * self.current_price * 0.2

        self.current_price = max(
            self.current_price + price_change, self.base_price * 0.1
        )

        # 计算买卖价差
        spread_factor = (2 - self.liquidity_factor) * 0.001  # 流动性越低，价差越大
        spread = self.current_price * spread_factor

        bid_price = self.current_price - spread / 2
        ask_price = self.current_price + spread / 2

        # 计算订单簿深度
        base_size = 10.0 * self.liquidity_factor
        bid_size = np.random.exponential(base_size)
        ask_size = np.random.exponential(base_size)

        # 计算成交量
        volume = np.random.exponential(100 * self.liquidity_factor)

        # 计算流动性评分
        liquidity_score = min(1.0, (bid_size + ask_size) / 50.0 * self.liquidity_factor)

        return MarketState(
            timestamp=timestamp,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=bid_size,
            ask_size=ask_size,
            last_price=self.current_price,
            volume=volume,
            volatility=self.volatility,
            liquidity_score=liquidity_score,
        )


class OrderExecutionEngine:
    """订单执行引擎"""

    def __init__(self, scenario: ScenarioType):
        self.scenario = scenario
        self.base_slippage = self._get_base_slippage()
        self.fill_probability_base = self._get_fill_probability()

    def _get_base_slippage(self) -> float:
        """获取基础滑点"""
        slippage_map = {
            ScenarioType.NORMAL: 0.0005,
            ScenarioType.BLACK_SWAN: 0.005,
            ScenarioType.HIGH_VOLATILITY: 0.002,
            ScenarioType.LOW_LIQUIDITY: 0.003,
            ScenarioType.FLASH_CRASH: 0.01,
        }
        return slippage_map.get(self.scenario, 0.0005)

    def _get_fill_probability(self) -> float:
        """获取基础成交概率"""
        fill_prob_map = {
            ScenarioType.NORMAL: 0.98,
            ScenarioType.BLACK_SWAN: 0.7,
            ScenarioType.HIGH_VOLATILITY: 0.85,
            ScenarioType.LOW_LIQUIDITY: 0.75,
            ScenarioType.FLASH_CRASH: 0.5,
        }
        return fill_prob_map.get(self.scenario, 0.98)

    def execute_order(
        self, order: Order, market_state: MarketState
    ) -> Tuple[bool, float, float]:
        """执行订单

        Returns:
            Tuple[bool, float, float]: (是否成交, 成交价格, 滑点)
        """
        # 计算动态滑点
        volatility_factor = market_state.volatility / 0.02  # 标准化波动率
        liquidity_factor = market_state.liquidity_score

        dynamic_slippage = self.base_slippage * volatility_factor / liquidity_factor

        # 计算成交概率
        fill_probability = self.fill_probability_base * liquidity_factor

        # 判断是否成交
        if np.random.random() > fill_probability:
            return False, 0.0, 0.0

        # 计算成交价格
        if order.order_type == OrderType.MARKET:
            if order.side == OrderSide.BUY:
                base_price = market_state.ask_price
                slippage_direction = 1
            else:
                base_price = market_state.bid_price
                slippage_direction = -1

            # 应用滑点
            slippage_amount = base_price * dynamic_slippage * slippage_direction
            fill_price = base_price + slippage_amount

            return True, fill_price, abs(slippage_amount / base_price)

        elif order.order_type == OrderType.LIMIT:
            # 限价单逻辑
            if order.side == OrderSide.BUY and order.price >= market_state.ask_price:
                return True, min(order.price, market_state.ask_price), 0.0
            elif order.side == OrderSide.SELL and order.price <= market_state.bid_price:
                return True, max(order.price, market_state.bid_price), 0.0
            else:
                return False, 0.0, 0.0

        return False, 0.0, 0.0

    def calculate_price_impact(
        self, order_size: float, market_state: MarketState
    ) -> float:
        """计算价格冲击"""
        # 简化的价格冲击模型
        available_liquidity = (market_state.bid_size + market_state.ask_size) / 2
        impact_ratio = order_size / available_liquidity

        # 非线性价格冲击
        base_impact = 0.0001  # 基础冲击
        impact = base_impact * np.sqrt(impact_ratio) / market_state.liquidity_score

        return min(impact, 0.05)  # 最大5%冲击


class StrategyEngine:
    """策略引擎"""

    def __init__(self, strategy_params: Dict[str, Any]):
        self.strategy_params = strategy_params
        self.position = 0.0
        self.cash = 100000.0  # 初始资金
        self.trades = []
        self.portfolio_values = []

    def generate_signal(self, market_states: List[MarketState]) -> Optional[Order]:
        """生成交易信号"""
        if len(market_states) < 2:
            return None

        current_state = market_states[-1]
        prev_state = market_states[-2]

        # 简单的均值回归策略
        price_change = (
            current_state.last_price - prev_state.last_price
        ) / prev_state.last_price

        entry_threshold = self.strategy_params.get("entry_threshold", 0.02)
        exit_threshold = self.strategy_params.get("exit_threshold", 0.01)
        position_size = self.strategy_params.get("position_size", 0.1)

        # 开仓信号
        if abs(self.position) < 0.01:  # 无持仓
            if price_change < -entry_threshold:  # 价格下跌，买入
                quantity = (self.cash * position_size) / current_state.ask_price
                return Order(
                    order_id=f"order_{len(self.trades) + 1}",
                    symbol="BTCUSDT",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=quantity,
                    timestamp=current_state.timestamp,
                )
            elif price_change > entry_threshold:  # 价格上涨，卖出
                quantity = (self.cash * position_size) / current_state.bid_price
                return Order(
                    order_id=f"order_{len(self.trades) + 1}",
                    symbol="BTCUSDT",
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=quantity,
                    timestamp=current_state.timestamp,
                )

        # 平仓信号
        elif self.position > 0 and price_change > exit_threshold:  # 多头平仓
            return Order(
                order_id=f"order_{len(self.trades) + 1}",
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=abs(self.position),
                timestamp=current_state.timestamp,
            )
        elif self.position < 0 and price_change < -exit_threshold:  # 空头平仓
            return Order(
                order_id=f"order_{len(self.trades) + 1}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=abs(self.position),
                timestamp=current_state.timestamp,
            )

        return None

    def update_portfolio(
        self, order: Order, fill_price: float, market_state: MarketState
    ):
        """更新投资组合"""
        if order.side == OrderSide.BUY:
            self.position += order.quantity
            self.cash -= order.quantity * fill_price
        else:
            self.position -= order.quantity
            self.cash += order.quantity * fill_price

        # 记录交易
        trade = {
            "timestamp": order.timestamp.isoformat(),
            "side": order.side.value,
            "quantity": order.quantity,
            "price": fill_price,
            "value": order.quantity * fill_price,
            "position_after": self.position,
            "cash_after": self.cash,
        }
        self.trades.append(trade)

        # 计算组合价值
        portfolio_value = self.cash + self.position * market_state.last_price
        self.portfolio_values.append(
            {
                "timestamp": market_state.timestamp.isoformat(),
                "value": portfolio_value,
                "position": self.position,
                "cash": self.cash,
            }
        )

    def calculate_performance_metrics(self) -> Dict[str, float]:
        """计算绩效指标"""
        if len(self.portfolio_values) < 2:
            return {
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0,
            }

        values = [pv["value"] for pv in self.portfolio_values]
        initial_value = values[0]
        final_value = values[-1]

        # 总收益率
        total_return = (final_value - initial_value) / initial_value

        # 计算回撤
        peak = initial_value
        max_drawdown = 0.0

        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)

        # 计算收益率序列
        returns = []
        for i in range(1, len(values)):
            ret = (values[i] - values[i - 1]) / values[i - 1]
            returns.append(ret)

        if returns:
            # 波动率
            volatility = np.std(returns) * np.sqrt(252)  # 年化波动率

            # 夏普比率（假设无风险利率为0）
            avg_return = np.mean(returns) * 252  # 年化收益率
            sharpe_ratio = avg_return / volatility if volatility > 0 else 0.0
        else:
            volatility = 0.0
            sharpe_ratio = 0.0

        return {
            "total_return": total_return,
            "max_drawdown": -max_drawdown,  # 负值表示回撤
            "sharpe_ratio": sharpe_ratio,
            "volatility": volatility,
        }


class SimulationEngine:
    """仿真引擎主类"""

    def __init__(
        self, db_manager: DatabaseManager, metrics_collector: MetricsCollector
    ):
        self.db_manager = db_manager
        self.metrics_collector = metrics_collector
        logger.info("仿真引擎初始化完成")

    @log_async_execution_time("simulation_engine")
    async def run_simulation(self, task_data: Dict[str, Any]) -> SimulationResult:
        """运行仿真"""
        simulation_id = task_data["task_id"]
        symbol = task_data["symbol"]
        scenario = ScenarioType(task_data["scenario"])
        strategy_params = task_data["strategy_params"]
        period = task_data["period"]

        logger.info(f"开始仿真: {simulation_id}, 场景: {scenario.value}")

        start_time = datetime.now()

        try:
            # 获取校准参数
            calibration_params = await self._get_calibration_params(symbol, scenario)

            # 初始化组件
            market_generator = MarketDataGenerator(scenario)
            execution_engine = OrderExecutionEngine(scenario)
            strategy_engine = StrategyEngine(strategy_params)

            # 生成仿真时间序列
            simulation_steps = self._get_simulation_steps(period)
            market_states = []
            all_slippages = []
            all_price_impacts = []
            fill_count = 0
            total_orders = 0

            # 运行仿真循环
            for step in range(simulation_steps):
                timestamp = start_time + timedelta(minutes=step)

                # 生成市场状态
                market_state = market_generator.generate_market_state(timestamp)
                market_states.append(market_state)

                # 生成交易信号
                order = strategy_engine.generate_signal(market_states)

                if order:
                    total_orders += 1

                    # 执行订单
                    filled, fill_price, slippage = execution_engine.execute_order(
                        order, market_state
                    )

                    if filled:
                        fill_count += 1
                        all_slippages.append(slippage)

                        # 计算价格冲击
                        price_impact = execution_engine.calculate_price_impact(
                            order.quantity, market_state
                        )
                        all_price_impacts.append(price_impact)

                        # 更新投资组合
                        strategy_engine.update_portfolio(
                            order, fill_price, market_state
                        )

                # 定期记录进度
                if step % 100 == 0:
                    progress = (step / simulation_steps) * 100
                    logger.debug(f"仿真进度: {progress:.1f}%")

            # 计算仿真结果
            performance_metrics = strategy_engine.calculate_performance_metrics()

            # 计算统计指标
            avg_slippage = np.mean(all_slippages) if all_slippages else 0.0
            avg_price_impact = np.mean(all_price_impacts) if all_price_impacts else 0.0
            fill_probability = fill_count / max(total_orders, 1)

            execution_time = (datetime.now() - start_time).total_seconds()

            # 构建结果
            result = SimulationResult(
                simulation_id=simulation_id,
                total_return=performance_metrics["total_return"],
                max_drawdown=performance_metrics["max_drawdown"],
                sharpe_ratio=performance_metrics["sharpe_ratio"],
                slippage=avg_slippage,
                fill_probability=fill_probability,
                price_impact=avg_price_impact,
                execution_time=execution_time,
                trades=strategy_engine.trades,
                market_states=market_states,
                risk_metrics={
                    "volatility": performance_metrics["volatility"],
                    "var_95": self._calculate_var(
                        strategy_engine.portfolio_values, 0.95
                    ),
                    "max_consecutive_losses": self._calculate_max_consecutive_losses(
                        strategy_engine.trades
                    ),
                },
            )

            # 保存结果到数据库
            await self._save_simulation_result(result)

            logger.info(f"仿真完成: {simulation_id}, 耗时: {execution_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"仿真执行失败: {simulation_id}, 错误: {e}")
            raise

    async def _get_calibration_params(
        self, symbol: str, scenario: ScenarioType
    ) -> Dict[str, float]:
        """获取校准参数"""
        try:
            params = await self.db_manager.get_calibration_params(
                symbol, scenario.value
            )
            if params:
                return params
        except Exception as e:
            logger.warning(f"获取校准参数失败: {e}")

        # 返回默认参数
        return {
            "base_slippage": 0.001,
            "volatility_factor": 1.0,
            "liquidity_factor": 1.0,
        }

    def _get_simulation_steps(self, period: str) -> int:
        """获取仿真步数"""
        period_map = {
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "7d": 10080,
            "30d": 43200,
            "90d": 129600,
        }
        return period_map.get(period, 1440)

    def _calculate_var(self, portfolio_values: List[Dict], confidence: float) -> float:
        """计算风险价值(VaR)"""
        if len(portfolio_values) < 2:
            return 0.0

        returns = []
        for i in range(1, len(portfolio_values)):
            ret = (
                portfolio_values[i]["value"] - portfolio_values[i - 1]["value"]
            ) / portfolio_values[i - 1]["value"]
            returns.append(ret)

        if returns:
            return np.percentile(returns, (1 - confidence) * 100)
        return 0.0

    def _calculate_max_consecutive_losses(self, trades: List[Dict]) -> int:
        """计算最大连续亏损次数"""
        if not trades:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for i in range(1, len(trades)):
            current_pnl = trades[i]["value"] - trades[i - 1]["value"]
            if current_pnl < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    async def _save_simulation_result(self, result: SimulationResult):
        """保存仿真结果"""
        result_data = {
            "result_id": f"result_{result.simulation_id}",
            "task_id": result.simulation_id,
            "slippage": result.slippage,
            "fill_probability": result.fill_probability,
            "price_impact": result.price_impact,
            "total_return": result.total_return,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "execution_time": result.execution_time,
            "report_path": f"/reports/{result.simulation_id}.json",
        }

        await self.db_manager.save_simulation_result(result_data)

        # 保存详细报告
        await self._save_detailed_report(result)

    async def _save_detailed_report(self, result: SimulationResult):
        """保存详细报告"""
        import os
        from pathlib import Path

        # 创建报告目录
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        # 构建详细报告
        detailed_report = {
            "simulation_id": result.simulation_id,
            "summary": {
                "total_return": result.total_return,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "execution_time": result.execution_time,
            },
            "market_impact": {
                "slippage": result.slippage,
                "fill_probability": result.fill_probability,
                "price_impact": result.price_impact,
            },
            "risk_metrics": result.risk_metrics,
            "trades": result.trades,
            "market_data_sample": [
                {
                    "timestamp": state.timestamp.isoformat(),
                    "price": state.last_price,
                    "spread": state.ask_price - state.bid_price,
                    "liquidity_score": state.liquidity_score,
                }
                for state in result.market_states[::100]  # 采样数据
            ],
            "generated_at": datetime.now().isoformat(),
            "report_version": "1.0.0",
        }

        # 保存到文件
        report_file = reports_dir / f"{result.simulation_id}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(detailed_report, f, indent=2, ensure_ascii=False)

        logger.info(f"详细报告已保存: {report_file}")
