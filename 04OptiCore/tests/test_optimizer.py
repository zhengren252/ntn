#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略优化模组综合测试
NeuroTrade Nexus (NTN) - Strategy Optimizer Module Tests

测试覆盖：
1. 策略优化模组整体功能测试
2. 模组间集成测试
3. 端到端工作流测试
4. 性能和稳定性测试
5. 错误处理和恢复测试
6. 配置和环境测试

遵循NeuroTrade Nexus测试规范：
- 独立测试：每个测试用例相互独立
- 确定性测试：使用固定随机种子确保结果可重现
- 完整覆盖：覆盖所有核心功能和边界情况
- 性能测试：验证系统性能指标
"""

import asyncio
import os
import shutil
import tempfile
import time
import unittest
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd

# 初始化日志系统
from config.logging_config import setup_logging
setup_logging()

# 设置测试环境
os.environ["NTN_ENVIRONMENT"] = "test"
os.environ["TESTING"] = "1"

from config.settings import get_settings
from database.models import (
    BacktestReport,
    OptimizationResult,
    OptimizationTask,
    Strategy,
)
from optimizer.backtester.engine import BacktestEngine
from optimizer.communication.zmq_client import MockZMQClient, ZMQClient
from optimizer.decision.engine import DecisionEngine

# 导入核心模块
from optimizer.main import StrategyOptimizationModule
from optimizer.optimization.genetic_optimizer import GeneticOptimizer
from optimizer.risk.manager import RiskManager
from optimizer.strategies.manager import StrategyManager
from optimizer.utils.data_validator import DataValidator

# 导入测试工具
from tests.test_utils import (
    DataGenerator,
    TestMetrics,
    async_test,
    mock_zmq_context,
    performance_test,
    temp_database,
)


class TestStrategyOptimizerModule(unittest.TestCase):
    """
    策略优化模组综合测试类

    测试整个策略优化模组的功能和集成
    """

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.data_generator = DataGenerator(seed=42)
        cls.test_config = {
            "environment": "test",
            "database": {
                "sqlite_path": ":memory:",
                "redis_host": "localhost",
                "redis_port": 6379,
                "redis_db": 15,  # 使用测试专用数据库
            },
            "zmq": {
                "subscriber_address": "tcp://localhost:5555",
                "publisher_address": "tcp://localhost:5556",
                "subscribe_topics": ["scanner.pool.preliminary"],
                "publish_topic": "optimizer.pool.trading",
            },
            "backtest": {
                "initial_capital": 10000.0,
                "commission_rate": 0.001,
                "max_concurrent_backtests": 2,
            },
            "optimization": {
                "population_size": 10,
                "max_generations": 5,
                "mutation_rate": 0.1,
                "crossover_rate": 0.8,
            },
            "risk": {
                "max_position_size": 0.3,
                "max_drawdown_threshold": 0.2,
                "min_sharpe_ratio": 0.5,
            },
        }

    def setUp(self):
        """每个测试用例的初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_optimizer.db")

        # 更新测试配置
        self.__class__.test_config["database"]["sqlite_path"] = self.test_db_path

        # 初始化测试数据
        self.test_market_data = self.data_generator.generate_market_data(
            symbol="BTCUSDT",
            start_date="2023-01-01",
            end_date="2023-03-31",
            frequency="D",
        )

        self.test_strategy_params = self.data_generator.generate_strategy_parameters(
            "ma_cross"
        )

    def tearDown(self):
        """每个测试用例的清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @async_test
    async def test_module_initialization(self):
        """
        测试策略优化模组初始化
        """
        # 创建策略优化模组
        optimizer_module = StrategyOptimizationModule()

        # 测试初始化
        await optimizer_module.initialize()

        # 验证组件初始化
        self.assertIsNotNone(optimizer_module.backtest_engine)
        self.assertIsNotNone(optimizer_module.genetic_optimizer)
        self.assertIsNotNone(optimizer_module.decision_engine)
        self.assertIsNotNone(optimizer_module.strategy_manager)
        self.assertIsNotNone(optimizer_module.risk_manager)
        self.assertIsNotNone(optimizer_module.data_validator)

        # 测试清理
        await optimizer_module.cleanup()

    @async_test
    async def test_end_to_end_optimization_workflow(self):
        """
        测试端到端优化工作流
        """
        # 创建模组实例
        optimizer_module = StrategyOptimizationModule()
        await optimizer_module.initialize()

        try:
            # 1. 注册策略
            from optimizer.strategies.manager import StrategyConfig

            # 创建正确格式的策略参数配置
            strategy_parameters = {
                "fast_period": {"type": "int", "min": 5, "max": 50, "default": 10},
                "slow_period": {"type": "int", "min": 10, "max": 200, "default": 30},
                "signal_threshold": {
                    "type": "float",
                    "min": 0.001,
                    "max": 0.05,
                    "default": 0.02,
                },
                "stop_loss": {
                    "type": "float",
                    "min": 0.01,
                    "max": 0.2,
                    "default": 0.03,
                },
                "take_profit": {
                    "type": "float",
                    "min": 0.02,
                    "max": 0.5,
                    "default": 0.06,
                },
            }

            strategy_config = StrategyConfig(
                strategy_id="test_ma_cross_001",
                name="test_ma_cross",
                version="1.0",
                description="测试移动平均交叉策略",
                parameters=strategy_parameters,
                risk_limits={
                    "max_drawdown": 0.10,
                    "max_position_size": 0.25,
                    "daily_loss_limit": 0.03,
                },
                performance_metrics={
                    "expected_return": 0.15,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": 0.06,
                    "win_rate": 0.58,
                },
            )

            strategy_id = await optimizer_module.strategy_manager.register_strategy(
                strategy_config
            )
            self.assertIsNotNone(strategy_id)

            # 为测试策略添加参数范围定义到遗传优化器
            optimizer_module.genetic_optimizer.param_ranges[strategy_id] = {
                "fast_period": {"min": 5, "max": 50, "type": "int"},
                "slow_period": {"min": 10, "max": 200, "type": "int"},
                "signal_threshold": {"min": 0.001, "max": 0.05, "type": "float"},
                "stop_loss": {"min": 0.01, "max": 0.2, "type": "float"},
                "take_profit": {"min": 0.02, "max": 0.5, "type": "float"},
            }

            # 2. 执行回测
            # BacktestEngine.run_backtest期望参数: (symbol, strategy_configs)
            strategy_configs = [
                {
                    "strategy_id": strategy_id,
                    "params": {
                        "fast_period": 10,
                        "slow_period": 20,
                        "signal_threshold": 0.02,
                    },
                }
            ]

            backtest_result = await optimizer_module.backtest_engine.run_backtest(
                "BTCUSDT", strategy_configs
            )

            self.assertIsNotNone(backtest_result)
            self.assertIn("regular_backtest", backtest_result)
            self.assertIn("stress_tests", backtest_result)
            self.assertIn("combined_metrics", backtest_result)

            # 检查常规回测结果结构
            regular_results = backtest_result["regular_backtest"]
            self.assertIsInstance(regular_results, dict)

            # 检查策略结果
            if strategy_id in regular_results:
                strategy_result = regular_results[strategy_id]
                self.assertIn("total_return", strategy_result)
                self.assertIn("sharpe_ratio", strategy_result)
                self.assertIn("max_drawdown", strategy_result)

            # 3. 参数优化
            optimization_result = await optimizer_module.genetic_optimizer.optimize(
                "BTCUSDT", backtest_result
            )

            self.assertIsNotNone(optimization_result)
            self.assertIn("params", optimization_result)
            self.assertIn("fitness", optimization_result)
            self.assertIn("strategy_id", optimization_result)

            # 4. 生成决策
            # DecisionEngine.make_decision期望的optimization_results格式是Dict[str, Any]
            # 其中键是symbol，值包含optimized_strategies
            # 需要确保optimization_result包含正确的结构
            optimized_strategy = {
                "strategy_id": optimization_result.get("strategy_id", strategy_id),
                "params": optimization_result.get("params", {}),
                "fitness": optimization_result.get("fitness", 0.0),
                "performance_metrics": optimization_result.get(
                    "performance_metrics", {}
                ),
            }

            optimization_results_dict = {
                "BTCUSDT": {"optimized_strategies": {strategy_id: optimized_strategy}}
            }

            market_data_dict = {
                "price_history": self.test_market_data["close"].tolist()[-20:],
                "volume_data": self.test_market_data["volume"].tolist()[-20:],
                "trend_indicators": {"trend_score": 0.05},
            }

            decisions = await optimizer_module.decision_engine.make_decision(
                optimization_results_dict, market_data_dict
            )

            self.assertIsInstance(decisions, list)
            if decisions:
                decision = decisions[0]
                self.assertIn("strategy_id", decision.__dict__)
                self.assertIn("action", decision.__dict__)
                self.assertIn("confidence", decision.__dict__)

        finally:
            await optimizer_module.cleanup()

    @async_test
    async def test_zmq_communication_integration(self):
        """
        测试ZeroMQ通信集成
        """
        # 使用模拟ZMQ客户端
        zmq_config = self.test_config["zmq"]
        zmq_client = MockZMQClient(zmq_config)

        await zmq_client.initialize()
        await zmq_client.start()

        try:
            # 测试消息处理器注册
            message_received = False

            async def test_message_handler(trading_opportunity):
                nonlocal message_received
                message_received = True
                self.assertIsNotNone(trading_opportunity)
                self.assertHasAttr(trading_opportunity, "symbol")
                self.assertHasAttr(trading_opportunity, "signal_type")

            zmq_client.register_handler(
                "scanner.pool.preliminary", test_message_handler
            )

            # 等待模拟消息
            await asyncio.sleep(2)

            # 验证消息接收
            self.assertTrue(message_received)

            # 测试策略包发布
            from optimizer.communication.zmq_client import StrategyPackage

            strategy_package = StrategyPackage(
                strategy_id="test_strategy",
                symbol="BTCUSDT",
                action="BUY",
                confidence=0.85,
                position_size=0.1,
                stop_loss=95.0,
                take_profit=105.0,
                parameters=self.test_strategy_params,
                risk_metrics={"max_drawdown": 0.05},
                timestamp=datetime.now().isoformat(),
            )

            await zmq_client.publish_strategy_package(strategy_package)

            # 验证发布统计
            stats = zmq_client.get_stats()
            self.assertGreater(stats["messages_sent"], 0)

        finally:
            await zmq_client.stop()

    @async_test
    async def test_data_validation_integration(self):
        """
        测试数据验证集成
        """
        data_validator = DataValidator(self.test_config.get("validation", {}))

        # 测试市场数据验证
        market_data_dict = {
            "prices": self.test_market_data["close"].tolist(),
            "volumes": self.test_market_data["volume"].tolist(),
            "timestamps": self.test_market_data["timestamp"]
            .dt.strftime("%Y-%m-%d")
            .tolist(),
        }

        validation_report = await data_validator.validate_market_data(market_data_dict)

        self.assertIsNotNone(validation_report)
        self.assertGreaterEqual(validation_report.quality_score, 0.0)
        self.assertLessEqual(validation_report.quality_score, 1.0)

        # 测试策略参数验证
        param_validation = await data_validator.validate_strategy_parameters(
            "ma_cross", self.test_strategy_params
        )

        self.assertIsNotNone(param_validation)

    @async_test
    async def test_risk_management_integration(self):
        """
        测试风险管理集成
        """
        risk_manager = RiskManager(self.test_config["risk"])
        await risk_manager.initialize()

        try:
            # 测试仓位检查
            position_check = await risk_manager.check_position_limits(
                symbol="BTCUSDT", proposed_size=0.2, current_portfolio={"BTCUSDT": 0.1}
            )

            self.assertIsInstance(position_check, dict)
            self.assertIn("approved", position_check)

            # 测试风险指标计算
            backtest_result = self.data_generator.generate_backtest_results()

            risk_metrics = await risk_manager.calculate_risk_metrics(backtest_result)

            self.assertIsNotNone(risk_metrics)
            self.assertIn("max_drawdown", risk_metrics)
            self.assertIn("var_95", risk_metrics)

        finally:
            await risk_manager.cleanup()

    @performance_test(max_time=30.0)
    @async_test
    async def test_performance_under_load(self):
        """
        测试负载下的性能
        """
        optimizer_module = StrategyOptimizationModule(self.test_config)
        await optimizer_module.initialize()

        try:
            # 并发执行多个回测任务
            tasks = []
            for i in range(5):
                strategy_config = {
                    "name": f"test_strategy_{i}",
                    "type": "ma_cross",
                    "parameters": self.data_generator.generate_strategy_parameters(
                        "ma_cross"
                    ),
                    "description": f"测试策略 {i}",
                }

                task = asyncio.create_task(
                    self._run_single_optimization(optimizer_module, strategy_config)
                )
                tasks.append(task)

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证结果
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertGreaterEqual(len(successful_results), 3)  # 至少60%成功率

        finally:
            await optimizer_module.cleanup()

    async def _run_single_optimization(self, optimizer_module, strategy_config):
        """
        运行单个优化任务
        """
        # 注册策略
        strategy_id = await optimizer_module.strategy_manager.register_strategy(
            strategy_config
        )

        # 执行回测 - 使用正确的BacktestEngine.run_backtest方法签名
        strategy_configs = [{
            "strategy_id": strategy_id,
            "params": strategy_config["parameters"]
        }]

        backtest_result = await optimizer_module.backtest_engine.run_backtest(
            "BTCUSDT", strategy_configs
        )

        return backtest_result

    @async_test
    async def test_error_handling_and_recovery(self):
        """
        测试错误处理和恢复
        """
        optimizer_module = StrategyOptimizationModule(self.test_config)
        await optimizer_module.initialize()

        try:
            # 测试无效策略参数处理
            invalid_strategy_config = {
                "name": "invalid_strategy",
                "type": "ma_cross",
                "parameters": {
                    "fast_period": -1,  # 无效参数
                    "slow_period": "invalid",  # 无效类型
                },
                "description": "无效策略测试",
            }

            # 测试负数参数
            exception_raised = False
            try:
                await optimizer_module.strategy_manager.register_strategy(
                    invalid_strategy_config
                )
            except (ValueError, TypeError) as e:
                exception_raised = True
                self.assertIn("不能为负数", str(e))
            
            self.assertTrue(exception_raised, "Expected ValueError for negative parameters")

            # 测试无效字符串参数
            invalid_string_config = {
                "name": "invalid_string_strategy",
                "type": "ma_cross",
                "parameters": {
                    "fast_period": 10,
                    "slow_period": "invalid",  # 无效字符串
                },
                "description": "无效字符串策略测试",
            }

            exception_raised = False
            try:
                await optimizer_module.strategy_manager.register_strategy(
                    invalid_string_config
                )
            except (ValueError, TypeError) as e:
                exception_raised = True
                self.assertIn("期望数字类型", str(e))
            
            self.assertTrue(exception_raised, "Expected ValueError for invalid string parameters")

            # 测试空数据处理 - 使用正确的BacktestEngine.run_backtest方法签名
            with self.assertRaises(Exception):
                # BacktestEngine.run_backtest的正确签名是 run_backtest(symbol, strategy_configs)
                empty_strategy_configs = []
                await optimizer_module.backtest_engine.run_backtest(
                    "BTCUSDT", empty_strategy_configs
                )

        finally:
            await optimizer_module.cleanup()

    def test_configuration_validation(self):
        """
        测试配置验证
        """
        # 测试有效配置
        valid_config = self.test_config.copy()
        optimizer_module = StrategyOptimizationModule(valid_config)
        self.assertIsNotNone(optimizer_module)

        # 测试无效配置
        invalid_configs = [
            {},  # 空配置
            {"environment": "invalid"},  # 无效环境
            {"database": {}},  # 缺少数据库配置
        ]

        for invalid_config in invalid_configs:
            with self.assertRaises(Exception):
                StrategyOptimizationModule(invalid_config)

    @async_test
    async def test_module_lifecycle(self):
        """
        测试模组生命周期管理
        """
        optimizer_module = StrategyOptimizationModule(self.test_config)

        # 测试初始化
        await optimizer_module.initialize()
        self.assertTrue(optimizer_module.is_initialized)

        # 测试运行状态
        self.assertTrue(optimizer_module.is_running)

        # 测试暂停和恢复
        await optimizer_module.pause()
        self.assertFalse(optimizer_module.is_running)

        await optimizer_module.resume()
        self.assertTrue(optimizer_module.is_running)

        # 测试清理
        await optimizer_module.cleanup()
        self.assertFalse(optimizer_module.is_initialized)
        self.assertFalse(optimizer_module.is_running)

    @async_test
    async def test_monitoring_and_metrics(self):
        """
        测试监控和指标收集
        """
        optimizer_module = StrategyOptimizationModule(self.test_config)
        await optimizer_module.initialize()

        try:
            # 获取系统指标
            metrics = await optimizer_module.get_system_metrics()

            self.assertIsInstance(metrics, dict)
            self.assertIn("uptime", metrics)
            self.assertIn("memory_usage", metrics)
            self.assertIn("cpu_usage", metrics)

            # 获取业务指标
            business_metrics = await optimizer_module.get_business_metrics()

            self.assertIsInstance(business_metrics, dict)
            self.assertIn("total_strategies", business_metrics)
            self.assertIn("total_backtests", business_metrics)
            self.assertIn("total_optimizations", business_metrics)

        finally:
            await optimizer_module.cleanup()


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
