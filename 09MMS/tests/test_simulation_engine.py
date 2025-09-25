# -*- coding: utf-8 -*-
"""
仿真引擎测试模块

测试市场微结构仿真引擎的核心功能
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.services.simulation_engine import (
    SimulationEngine,
    MarketDataGenerator,
    OrderExecutionEngine,
    StrategyEngine,
    OrderType,
    OrderSide,
)
from src.models.simulation import SimulationRequest, ScenarioType


class TestMarketDataGenerator:
    """市场数据生成器测试"""

    def test_generate_normal_scenario(self, test_config):
        """测试正常市场场景数据生成"""
        generator = MarketDataGenerator(test_config)

        data = generator.generate_scenario_data(
            symbol="BTCUSDT", scenario=ScenarioType.NORMAL, days=30
        )

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert all(
            col in data.columns
            for col in [
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "bid",
                "ask",
                "bid_size",
                "ask_size",
            ]
        )

        # 检查价格合理性
        assert (data["high"] >= data["low"]).all()
        assert (data["high"] >= data["open"]).all()
        assert (data["high"] >= data["close"]).all()
        assert (data["low"] <= data["open"]).all()
        assert (data["low"] <= data["close"]).all()

        # 检查买卖价差
        assert (data["ask"] >= data["bid"]).all()

    def test_generate_black_swan_scenario(self, test_config):
        """测试黑天鹅事件场景数据生成"""
        generator = MarketDataGenerator(test_config)

        data = generator.generate_scenario_data(
            symbol="BTCUSDT", scenario=ScenarioType.BLACK_SWAN, days=30
        )

        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0

        # 计算收益率
        returns = data["close"].pct_change().dropna()

        # 黑天鹅事件应该有更高的波动率
        volatility = returns.std()
        assert volatility > 0.001  # 应该有显著波动

    def test_generate_high_volatility_scenario(self, test_config):
        """测试高波动率场景数据生成"""
        generator = MarketDataGenerator(test_config)

        normal_data = generator.generate_scenario_data(
            symbol="BTCUSDT", scenario=ScenarioType.NORMAL, days=30
        )

        high_vol_data = generator.generate_scenario_data(
            symbol="BTCUSDT", scenario=ScenarioType.HIGH_VOLATILITY, days=30
        )

        normal_returns = normal_data["close"].pct_change().dropna()
        high_vol_returns = high_vol_data["close"].pct_change().dropna()

        # 高波动率场景应该有更高的标准差
        assert high_vol_returns.std() > normal_returns.std()


class TestOrderExecutionEngine:
    """订单执行引擎测试"""

    def test_execute_market_buy_order(self, test_config, sample_market_data):
        """测试市场买单执行"""
        engine = OrderExecutionEngine(test_config)

        # 获取当前市场状态
        current_data = sample_market_data.iloc[-1]

        result = engine.execute_order(
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=1.0,
            current_data=current_data,
        )

        assert result is not None
        assert result["executed_quantity"] == 1.0
        assert result["executed_price"] > 0
        assert result["slippage"] >= 0
        assert 0 <= result["fill_probability"] <= 1

    def test_execute_market_sell_order(self, test_config, sample_market_data):
        """测试市场卖单执行"""
        engine = OrderExecutionEngine(test_config)

        current_data = sample_market_data.iloc[-1]

        result = engine.execute_order(
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            quantity=1.0,
            current_data=current_data,
        )

        assert result is not None
        assert result["executed_quantity"] == 1.0
        assert result["executed_price"] > 0
        assert result["slippage"] >= 0

    def test_execute_limit_order(self, test_config, sample_market_data):
        """测试限价单执行"""
        engine = OrderExecutionEngine(test_config)

        current_data = sample_market_data.iloc[-1]
        limit_price = current_data["close"] * 0.99  # 低于市价的买单

        result = engine.execute_order(
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=1.0,
            current_data=current_data,
            limit_price=limit_price,
        )

        assert result is not None
        # 限价单可能不会完全成交
        assert 0 <= result["executed_quantity"] <= 1.0

    def test_calculate_slippage(self, test_config):
        """测试滑点计算"""
        engine = OrderExecutionEngine(test_config)

        # 测试买单滑点
        buy_slippage = engine.calculate_slippage(
            side=OrderSide.BUY, quantity=10.0, volatility=0.02, liquidity=1000.0
        )
        assert buy_slippage >= 0

        # 测试卖单滑点
        sell_slippage = engine.calculate_slippage(
            side=OrderSide.SELL, quantity=10.0, volatility=0.02, liquidity=1000.0
        )
        assert sell_slippage >= 0

        # 更大的订单应该有更高的滑点
        large_order_slippage = engine.calculate_slippage(
            side=OrderSide.BUY, quantity=100.0, volatility=0.02, liquidity=1000.0
        )
        assert large_order_slippage >= buy_slippage


class TestStrategyEngine:
    """策略引擎测试"""

    def test_generate_signals(self, test_config, sample_market_data):
        """测试信号生成"""
        engine = StrategyEngine(test_config)

        strategy_params = {
            "entry_threshold": 0.02,
            "exit_threshold": 0.01,
            "position_size": 0.1,
            "stop_loss": 0.05,
        }

        signals = engine.generate_signals(sample_market_data, strategy_params)

        assert isinstance(signals, pd.DataFrame)
        assert len(signals) == len(sample_market_data)
        assert "signal" in signals.columns
        assert "position_size" in signals.columns

        # 信号应该在 -1, 0, 1 之间
        assert signals["signal"].isin([-1, 0, 1]).all()

    def test_calculate_returns(self, test_config, sample_market_data):
        """测试收益率计算"""
        engine = StrategyEngine(test_config)

        # 创建简单的信号序列
        signals = pd.DataFrame(
            {
                "signal": [1, 1, 0, -1, -1, 0] * (len(sample_market_data) // 6 + 1),
                "position_size": [0.1] * len(sample_market_data),
            }
        )[: len(sample_market_data)]

        returns = engine.calculate_returns(sample_market_data, signals)

        assert isinstance(returns, pd.Series)
        assert len(returns) == len(sample_market_data)
        assert not returns.isna().all()

    def test_calculate_performance_metrics(self, test_config):
        """测试绩效指标计算"""
        engine = StrategyEngine(test_config)

        # 创建示例收益率序列
        returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.012])

        metrics = engine.calculate_performance_metrics(returns)

        assert isinstance(metrics, dict)
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "win_rate" in metrics
        assert "profit_factor" in metrics

        # 检查指标合理性
        assert isinstance(metrics["total_return"], float)
        assert isinstance(metrics["sharpe_ratio"], float)
        assert metrics["max_drawdown"] <= 0  # 最大回撤应该是负数或零
        assert 0 <= metrics["win_rate"] <= 1  # 胜率应该在0-1之间


class TestSimulationEngine:
    """仿真引擎测试"""

    @pytest.mark.asyncio
    async def test_run_simulation(self, simulation_engine, sample_simulation_request):
        """测试运行仿真"""
        with patch.object(
            simulation_engine.data_generator, "generate_scenario_data"
        ) as mock_generate:
            # 模拟市场数据
            mock_data = pd.DataFrame(
                {
                    "timestamp": pd.date_range("2024-01-01", periods=100, freq="1H"),
                    "open": np.random.uniform(49000, 51000, 100),
                    "high": np.random.uniform(49500, 51500, 100),
                    "low": np.random.uniform(48500, 50500, 100),
                    "close": np.random.uniform(49000, 51000, 100),
                    "volume": np.random.uniform(100, 1000, 100),
                    "bid": np.random.uniform(48900, 50900, 100),
                    "ask": np.random.uniform(49100, 51100, 100),
                    "bid_size": np.random.uniform(1, 10, 100),
                    "ask_size": np.random.uniform(1, 10, 100),
                }
            )
            mock_generate.return_value = mock_data

            result = await simulation_engine.run_simulation(sample_simulation_request)

            assert result is not None
            assert "simulation_id" in result
            assert "slippage" in result
            assert "fill_probability" in result
            assert "price_impact" in result
            assert "total_return" in result
            assert "max_drawdown" in result
            assert "sharpe_ratio" in result
            assert "execution_time" in result

            # 检查结果合理性
            assert result["slippage"] >= 0
            assert 0 <= result["fill_probability"] <= 1
            assert result["price_impact"] >= 0
            assert result["execution_time"] > 0

    def test_validate_request(self, simulation_engine):
        """测试请求验证"""
        # 有效请求
        valid_request = SimulationRequest(
            symbol="BTCUSDT",
            period="30d",
            scenario="normal",
            strategy_params={
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
        )

        # 应该不抛出异常
        simulation_engine.validate_request(valid_request)

        # 无效请求 - 缺少必要参数
        invalid_request = SimulationRequest(
            symbol="BTCUSDT", period="30d", scenario="normal", strategy_params={}
        )

        with pytest.raises(ValueError):
            simulation_engine.validate_request(invalid_request)

    def test_calculate_var(self, simulation_engine):
        """测试风险价值计算"""
        returns = pd.Series([0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02])

        var_95 = simulation_engine.calculate_var(returns, confidence_level=0.95)
        var_99 = simulation_engine.calculate_var(returns, confidence_level=0.99)

        assert isinstance(var_95, float)
        assert isinstance(var_99, float)
        assert var_95 <= 0  # VaR应该是负数
        assert var_99 <= 0
        assert var_99 <= var_95  # 99% VaR应该比95% VaR更保守

    def test_calculate_max_consecutive_loss(self, simulation_engine):
        """测试最大连续亏损计算"""
        returns = pd.Series([0.01, -0.02, -0.01, -0.005, 0.015, -0.01, 0.02])

        max_loss = simulation_engine.calculate_max_consecutive_loss(returns)

        assert isinstance(max_loss, float)
        assert max_loss <= 0  # 最大连续亏损应该是负数或零


@pytest.mark.integration
class TestSimulationEngineIntegration:
    """仿真引擎集成测试"""

    @pytest.mark.asyncio
    async def test_full_simulation_workflow(
        self, simulation_engine, sample_simulation_request
    ):
        """测试完整仿真工作流程"""
        # 这是一个较慢的集成测试
        result = await simulation_engine.run_simulation(sample_simulation_request)

        # 验证所有必要的输出字段
        required_fields = [
            "simulation_id",
            "slippage",
            "fill_probability",
            "price_impact",
            "total_return",
            "max_drawdown",
            "sharpe_ratio",
            "var_95",
            "var_99",
            "max_consecutive_loss",
            "win_rate",
            "profit_factor",
            "execution_time",
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # 验证数值合理性
        assert result["execution_time"] > 0
        assert 0 <= result["fill_probability"] <= 1
        assert result["slippage"] >= 0
        assert result["price_impact"] >= 0
        assert result["var_95"] <= 0
        assert result["var_99"] <= 0
        assert result["max_consecutive_loss"] <= 0
        assert 0 <= result["win_rate"] <= 1
        assert result["profit_factor"] >= 0
