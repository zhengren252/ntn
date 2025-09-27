#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎测试
NeuroTrade Nexus (NTN) - Backtest Engine Tests

测试覆盖：
1. VectorBT回测引擎功能测试
2. 策略回测流程测试
3. 性能指标计算测试
4. 压力测试验证
5. 异常处理测试
6. 并发回测测试

遵循NeuroTrade Nexus测试规范：
- 独立测试：每个测试用例相互独立
- 数据隔离：使用测试专用数据
- 模拟环境：使用Mock对象模拟外部依赖
- 全面覆盖：覆盖正常和异常情况
"""

import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import get_config
from optimizer.backtester.engine import BacktestEngine
from optimizer.strategies.grid_strategy import GridTradingStrategy


@dataclass
class BacktestTask:
    """回测任务数据结构"""
    task_id: str
    strategy_id: str
    strategy_type: str
    symbol: str
    start_date: str
    end_date: str
    parameters: Dict[str, Any]
    market_data: Dict[str, Any]


@dataclass
class BacktestResult:
    """回测结果数据结构"""
    task_id: str
    strategy_id: str
    strategy_type: str
    symbol: str
    metrics: Dict[str, Any]
    trades: List[Dict[str, Any]] = None
    equity_curve: List[float] = None


@dataclass
class MACrossoverStrategy:
    """均线交叉策略"""
    fast_period: int = 5
    slow_period: int = 20
    signal_threshold: float = 0.01
    position_size: float = 0.2


@dataclass
class RSIStrategy:
    """RSI策略"""
    rsi_period: int = 14
    oversold_threshold: int = 30
    overbought_threshold: int = 70
    position_size: float = 0.15


class TestBacktestEngine(unittest.TestCase):
    """
    回测引擎测试类
    """

    def setUp(self):
        """
        测试初始化
        """
        # 创建测试配置
        self.test_config = {
            "database": {"path": ":memory:", "pool_size": 5},  # 使用内存数据库
            "backtest": {
                "max_concurrent": 2,
                "timeout": 60,
                "default_commission": 0.001,
                "default_slippage": 0.0005,
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 15,  # 使用测试专用数据库
                "timeout": 5,
            },
        }

        # 创建回测引擎实例
        self.engine = BacktestEngine(self.test_config)

        # 创建测试数据
        self.test_data = self._create_test_market_data()

        # 创建测试策略参数
        self.test_strategies = {
            "grid_trading": {
                "strategy_id": "grid_001",
                "strategy_type": "grid_trading",
                "parameters": {
                    "grid_num": 10,
                    "profit_ratio": 0.02,
                    "stop_loss": 0.1,
                    "position_size": 0.1,
                },
            },
            "ma_crossover": {
                "strategy_id": "ma_001",
                "strategy_type": "ma_crossover",
                "parameters": {
                    "fast_period": 5,
                    "slow_period": 20,
                    "signal_threshold": 0.01,
                    "position_size": 0.2,
                },
            },
            "rsi_strategy": {
                "strategy_id": "rsi_001",
                "strategy_type": "rsi_strategy",
                "parameters": {
                    "rsi_period": 14,
                    "oversold_threshold": 30,
                    "overbought_threshold": 70,
                    "position_size": 0.15,
                },
            },
        }

    def tearDown(self):
        """
        测试清理
        """
        # 清理异步任务
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(self.engine.cleanup())
        except (RuntimeError, AttributeError):
            pass

    def _create_test_market_data(self):
        """
        创建测试市场数据
        """
        # 生成100天的测试数据
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")

        # 生成模拟价格数据（随机游走）
        np.random.seed(42)  # 确保测试结果可重现
        returns = np.random.normal(0.001, 0.02, 100)  # 日收益率
        prices = [100.0]  # 初始价格

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        # 生成成交量数据
        volumes = np.random.lognormal(10, 0.5, 100)

        return {
            "symbol": "BTC/USDT",
            "timestamps": dates.tolist(),
            "open": prices,
            "high": [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            "low": [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            "close": prices,
            "volume": volumes.tolist(),
        }

    def test_engine_initialization(self):
        """
        测试引擎初始化
        """
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.max_concurrent_backtests, 2)
        self.assertEqual(self.engine.backtest_timeout, 60)
        self.assertIsNotNone(self.engine.task_queue)

    def test_create_backtest_task(self):
        """
        测试创建回测任务
        """
        strategy_config = self.test_strategies["grid_trading"]

        task = BacktestTask(
            task_id="test_task_001",
            strategy_id=strategy_config["strategy_id"],
            strategy_type=strategy_config["strategy_type"],
            symbol="BTC/USDT",
            start_date="2023-01-01",
            end_date="2023-04-10",
            parameters=strategy_config["parameters"],
            market_data=self.test_data,
        )

        self.assertEqual(task.task_id, "test_task_001")
        self.assertEqual(task.strategy_id, "grid_001")
        self.assertEqual(task.strategy_type, "grid_trading")
        self.assertEqual(task.symbol, "BTC/USDT")
        self.assertIsNotNone(task.parameters)

    @patch("optimizer.backtest.engine.BacktestEngine._save_backtest_result")
    def test_grid_trading_backtest(self, mock_save):
        """
        测试网格交易策略回测
        """
        mock_save.return_value = AsyncMock()

        async def run_test():
            strategy_config = self.test_strategies["grid_trading"]

            task = BacktestTask(
                task_id="grid_test_001",
                strategy_id=strategy_config["strategy_id"],
                strategy_type=strategy_config["strategy_type"],
                symbol="BTC/USDT",
                start_date="2023-01-01",
                end_date="2023-04-10",
                parameters=strategy_config["parameters"],
                market_data=self.test_data,
            )

            result = await self.engine.run_backtest(task)

            # 验证回测结果
            self.assertIsInstance(result, BacktestResult)
            self.assertEqual(result.task_id, "grid_test_001")
            self.assertEqual(result.strategy_id, "grid_001")
            self.assertIsNotNone(result.metrics)

            # 验证关键指标存在
            required_metrics = [
                "total_return",
                "sharpe_ratio",
                "max_drawdown",
                "win_rate",
                "profit_factor",
                "total_trades",
            ]
            for metric in required_metrics:
                self.assertIn(metric, result.metrics)

            # 验证指标合理性
            self.assertIsInstance(result.metrics["total_return"], (int, float))
            self.assertIsInstance(result.metrics["sharpe_ratio"], (int, float))
            self.assertGreaterEqual(result.metrics["win_rate"], 0)
            self.assertLessEqual(result.metrics["win_rate"], 1)
            self.assertGreaterEqual(result.metrics["total_trades"], 0)

        asyncio.run(run_test())

    @patch("optimizer.backtest.engine.BacktestEngine._save_backtest_result")
    def test_ma_crossover_backtest(self, mock_save):
        """
        测试均线交叉策略回测
        """
        mock_save.return_value = AsyncMock()

        async def run_test():
            strategy_config = self.test_strategies["ma_crossover"]

            task = BacktestTask(
                task_id="ma_test_001",
                strategy_id=strategy_config["strategy_id"],
                strategy_type=strategy_config["strategy_type"],
                symbol="BTC/USDT",
                start_date="2023-01-01",
                end_date="2023-04-10",
                parameters=strategy_config["parameters"],
                market_data=self.test_data,
            )

            result = await self.engine.run_backtest(task)

            # 验证回测结果
            self.assertIsInstance(result, BacktestResult)
            self.assertEqual(result.strategy_id, "ma_001")
            self.assertIsNotNone(result.metrics)

            # 验证均线策略特有指标
            self.assertIn("avg_trade_duration", result.metrics)
            self.assertIn("max_consecutive_wins", result.metrics)
            self.assertIn("max_consecutive_losses", result.metrics)

        asyncio.run(run_test())

    @patch("optimizer.backtest.engine.BacktestEngine._save_backtest_result")
    def test_rsi_strategy_backtest(self, mock_save):
        """
        测试RSI策略回测
        """
        mock_save.return_value = AsyncMock()

        async def run_test():
            strategy_config = self.test_strategies["rsi_strategy"]

            task = BacktestTask(
                task_id="rsi_test_001",
                strategy_id=strategy_config["strategy_id"],
                strategy_type=strategy_config["strategy_type"],
                symbol="BTC/USDT",
                start_date="2023-01-01",
                end_date="2023-04-10",
                parameters=strategy_config["parameters"],
                market_data=self.test_data,
            )

            result = await self.engine.run_backtest(task)

            # 验证回测结果
            self.assertIsInstance(result, BacktestResult)
            self.assertEqual(result.strategy_id, "rsi_001")
            self.assertIsNotNone(result.metrics)

            # 验证RSI策略特有指标
            self.assertIn("avg_rsi_entry", result.metrics)
            self.assertIn("avg_rsi_exit", result.metrics)

        asyncio.run(run_test())

    def test_invalid_strategy_type(self):
        """
        测试无效策略类型处理
        """

        async def run_test():
            task = BacktestTask(
                task_id="invalid_test_001",
                strategy_id="invalid_001",
                strategy_type="invalid_strategy",
                symbol="BTC/USDT",
                start_date="2023-01-01",
                end_date="2023-04-10",
                parameters={},
                market_data=self.test_data,
            )

            with self.assertRaises(ValueError):
                await self.engine.run_backtest(task)

        asyncio.run(run_test())

    def test_insufficient_data(self):
        """
        测试数据不足情况
        """

        async def run_test():
            # 创建数据不足的市场数据
            insufficient_data = {
                "symbol": "BTC/USDT",
                "timestamps": ["2023-01-01", "2023-01-02"],
                "open": [100, 101],
                "high": [102, 103],
                "low": [99, 100],
                "close": [101, 102],
                "volume": [1000, 1100],
            }

            task = BacktestTask(
                task_id="insufficient_data_test",
                strategy_id="grid_001",
                strategy_type="grid_trading",
                symbol="BTC/USDT",
                start_date="2023-01-01",
                end_date="2023-01-02",
                parameters=self.test_strategies["grid_trading"]["parameters"],
                market_data=insufficient_data,
            )

            with self.assertRaises(ValueError):
                await self.engine.run_backtest(task)

        asyncio.run(run_test())

    @patch("optimizer.backtest.engine.BacktestEngine._save_backtest_result")
    def test_concurrent_backtests(self, mock_save):
        """
        测试并发回测
        """
        mock_save.return_value = AsyncMock()

        async def run_test():
            tasks = []

            # 创建多个回测任务
            for i in range(3):
                strategy_config = self.test_strategies["grid_trading"]
                task = BacktestTask(
                    task_id=f"concurrent_test_{i:03d}",
                    strategy_id=f"grid_{i:03d}",
                    strategy_type=strategy_config["strategy_type"],
                    symbol="BTC/USDT",
                    start_date="2023-01-01",
                    end_date="2023-04-10",
                    parameters=strategy_config["parameters"],
                    market_data=self.test_data,
                )
                tasks.append(task)

            # 并发执行回测
            results = await asyncio.gather(
                *[self.engine.run_backtest(task) for task in tasks],
                return_exceptions=True,
            )

            # 验证结果
            successful_results = [r for r in results if isinstance(r, BacktestResult)]
            self.assertGreater(len(successful_results), 0)

            # 验证每个结果的唯一性
            task_ids = [r.task_id for r in successful_results]
            self.assertEqual(len(task_ids), len(set(task_ids)))

        asyncio.run(run_test())

    def test_stress_testing(self):
        """
        测试压力测试功能
        """

        async def run_test():
            strategy_config = self.test_strategies["grid_trading"]

            # 创建压力测试场景
            stress_scenarios = [
                {"market_condition": "bull_market", "volatility_multiplier": 1.5},
                {"market_condition": "bear_market", "volatility_multiplier": 2.0},
                {"market_condition": "sideways", "volatility_multiplier": 0.5},
            ]

            results = await self.engine.run_stress_test(
                strategy_id=strategy_config["strategy_id"],
                strategy_type=strategy_config["strategy_type"],
                parameters=strategy_config["parameters"],
                market_data=self.test_data,
                stress_scenarios=stress_scenarios,
            )

            # 验证压力测试结果
            self.assertIsInstance(results, dict)
            self.assertEqual(len(results), len(stress_scenarios))

            for _, result in results.items():
                self.assertIsInstance(result, BacktestResult)
                self.assertIsNotNone(result.metrics)

        asyncio.run(run_test())

    def test_performance_metrics_calculation(self):
        """
        测试性能指标计算
        """
        # 创建模拟交易记录
        trades = [
            {
                "entry_time": "2023-01-01",
                "exit_time": "2023-01-02",
                "pnl": 100,
                "return": 0.01,
            },
            {
                "entry_time": "2023-01-03",
                "exit_time": "2023-01-04",
                "pnl": -50,
                "return": -0.005,
            },
            {
                "entry_time": "2023-01-05",
                "exit_time": "2023-01-06",
                "pnl": 200,
                "return": 0.02,
            },
            {
                "entry_time": "2023-01-07",
                "exit_time": "2023-01-08",
                "pnl": 75,
                "return": 0.0075,
            },
        ]

        # 创建模拟权益曲线
        equity_curve = [10000, 10100, 10050, 10250, 10325]

        metrics = self.engine._calculate_performance_metrics(trades, equity_curve)

        # 验证指标计算
        self.assertIn("total_return", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("max_drawdown", metrics)
        self.assertIn("win_rate", metrics)
        self.assertIn("profit_factor", metrics)
        self.assertIn("total_trades", metrics)

        # 验证具体数值
        self.assertEqual(metrics["total_trades"], 4)
        self.assertEqual(metrics["win_rate"], 0.75)  # 3胜1负
        self.assertAlmostEqual(
            metrics["total_return"], 0.0325, places=4
        )  # (10325-10000)/10000

    def test_risk_metrics_calculation(self):
        """
        测试风险指标计算
        """
        # 创建模拟日收益率序列
        daily_returns = [0.01, -0.005, 0.02, 0.0075, -0.01, 0.015, -0.008, 0.012]

        risk_metrics = self.engine._calculate_risk_metrics(daily_returns)

        # 验证风险指标
        self.assertIn("volatility", risk_metrics)
        self.assertIn("var_95", risk_metrics)
        self.assertIn("cvar_95", risk_metrics)
        self.assertIn("calmar_ratio", risk_metrics)

        # 验证数值合理性
        self.assertGreater(risk_metrics["volatility"], 0)
        self.assertLess(risk_metrics["var_95"], 0)  # VaR应该是负数
        self.assertLess(risk_metrics["cvar_95"], risk_metrics["var_95"])  # CVaR应该比VaR更负

    @patch("optimizer.backtest.engine.BacktestEngine._save_backtest_result")
    def test_backtest_timeout(self, mock_save):
        """
        测试回测超时处理
        """
        mock_save.return_value = AsyncMock()

        # 临时修改超时时间为很短的时间
        original_timeout = self.engine.backtest_timeout
        self.engine.backtest_timeout = 0.001  # 1毫秒

        async def run_test():
            strategy_config = self.test_strategies["grid_trading"]

            task = BacktestTask(
                task_id="timeout_test_001",
                strategy_id=strategy_config["strategy_id"],
                strategy_type=strategy_config["strategy_type"],
                symbol="BTC/USDT",
                start_date="2023-01-01",
                end_date="2023-04-10",
                parameters=strategy_config["parameters"],
                market_data=self.test_data,
            )

            with self.assertRaises(asyncio.TimeoutError):
                await self.engine.run_backtest(task)

        try:
            asyncio.run(run_test())
        finally:
            # 恢复原始超时时间
            self.engine.backtest_timeout = original_timeout

    def test_data_validation(self):
        """
        测试数据验证
        """
        # 测试缺少必需字段的数据
        invalid_data = {
            "symbol": "BTC/USDT",
            "timestamps": ["2023-01-01", "2023-01-02"],
            # 缺少价格数据
        }

        with self.assertRaises(ValueError):
            self.engine._validate_market_data(invalid_data)

        # 测试数据长度不一致
        inconsistent_data = {
            "symbol": "BTC/USDT",
            "timestamps": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "open": [100, 101],  # 长度不匹配
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 1100],
        }

        with self.assertRaises(ValueError):
            self.engine._validate_market_data(inconsistent_data)

    def test_strategy_parameter_validation(self):
        """
        测试策略参数验证
        """
        # 测试网格策略参数验证
        valid_params = self.test_strategies["grid_trading"]["parameters"]
        self.assertTrue(
            self.engine._validate_strategy_parameters("grid_trading", valid_params)
        )

        # 测试无效参数
        invalid_params = {
            "grid_num": -5,  # 负数网格数
            "profit_ratio": 1.5,  # 过大的利润比例
            "stop_loss": -0.1,  # 负数止损
        }

        with self.assertRaises(ValueError):
            self.engine._validate_strategy_parameters("grid_trading", invalid_params)

    def test_memory_usage_monitoring(self):
        """
        测试内存使用监控
        """
        initial_memory = self.engine._get_memory_usage()
        self.assertIsInstance(initial_memory, (int, float))
        self.assertGreater(initial_memory, 0)

        # 检查内存使用是否在合理范围内
        self.assertLess(initial_memory, 1000)  # 假设小于1GB

    def test_cleanup(self):
        """
        测试资源清理
        """

        async def run_test():
            # 确保引擎正常运行
            self.assertIsNotNone(self.engine.task_queue)

            # 执行清理
            await self.engine.cleanup()

            # 验证清理后状态
            self.assertTrue(self.engine.task_queue.empty())

        asyncio.run(run_test())


class TestBacktestStrategies(unittest.TestCase):
    """
    回测策略测试类
    """

    def setUp(self):
        """
        测试初始化
        """
        self.test_data = self._create_test_data()

    def _create_test_data(self):
        """
        创建测试数据
        """
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        np.random.seed(42)

        prices = [100.0]
        for _ in range(49):
            change = np.random.normal(0, 0.02)
            prices.append(prices[-1] * (1 + change))

        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p * 1.02 for p in prices],
                "low": [p * 0.98 for p in prices],
                "close": prices,
                "volume": np.random.lognormal(10, 0.5, 50),
            }
        )

    def test_grid_trading_strategy(self):
        """
        测试网格交易策略
        """
        strategy = GridTradingStrategy(
            {
                "grid_num": 5,
                "profit_ratio": 0.02,
                "stop_loss": 0.1,
                "position_size": 0.2,
            }
        )

        signals = strategy.generate_signals(self.test_data)

        # 验证信号生成
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertIn("position_size", signals.columns)

        # 验证信号值在合理范围内
        unique_signals = signals["signal"].unique()
        valid_signals = [-1, 0, 1]  # 卖出、持有、买入
        for signal in unique_signals:
            self.assertIn(signal, valid_signals)

    def test_ma_crossover_strategy(self):
        """
        测试均线交叉策略
        """
        strategy = MACrossoverStrategy(
            {
                "fast_period": 5,
                "slow_period": 10,
                "signal_threshold": 0.01,
                "position_size": 0.3,
            }
        )

        signals = strategy.generate_signals(self.test_data)

        # 验证信号生成
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertIn("fast_ma", signals.columns)
        self.assertIn("slow_ma", signals.columns)

        # 验证均线计算
        self.assertTrue(signals["fast_ma"].notna().any())
        self.assertTrue(signals["slow_ma"].notna().any())

    def test_rsi_strategy(self):
        """
        测试RSI策略
        """
        strategy = RSIStrategy(
            {
                "rsi_period": 14,
                "oversold_threshold": 30,
                "overbought_threshold": 70,
                "position_size": 0.25,
            }
        )

        signals = strategy.generate_signals(self.test_data)

        # 验证信号生成
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertIn("rsi", signals.columns)

        # 验证RSI计算
        rsi_values = signals["rsi"].dropna()
        self.assertTrue((rsi_values >= 0).all())
        self.assertTrue((rsi_values <= 100).all())


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
