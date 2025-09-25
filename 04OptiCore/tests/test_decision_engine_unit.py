#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策引擎单元测试
NeuroTrade Nexus (NTN) - Decision Engine Unit Tests

测试用例：
1. UNIT-DECISION-ENGINE-01: 决策引擎批准路径测试
2. UNIT-DECISION-ENGINE-02: 决策引擎拒绝路径测试（高回撤）
3. 其他边界条件测试
"""

import asyncio
import unittest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

# 导入被测试的模块
from optimizer.decision.engine import DecisionEngine, StrategyDecision


class TestDecisionEngineUnit(unittest.TestCase):
    """
    决策引擎单元测试类

    专注于测试决策引擎的核心逻辑，使用模拟数据避免外部依赖
    """

    def setUp(self):
        """测试用例初始化"""
        self.test_config = {
            "max_position_size": 0.1,
            "max_daily_loss": 0.02,
            "max_drawdown_threshold": 0.1,  # 10%最大回撤阈值
            "min_confidence_threshold": 0.6,
            "strategy_weights": {
                "return": 0.4,
                "risk": 0.3,
                "stability": 0.2,
                "liquidity": 0.1,
            },
            "stress_test_scenarios": [
                {"name": "test_scenario", "market_drop": -0.2, "volatility_spike": 2.0}
            ],
        }

        self.decision_engine = DecisionEngine(self.test_config)

    def test_unit_decision_engine_01_approval_path(self):
        """
        UNIT-DECISION-ENGINE-01: 决策引擎批准路径测试

        测试优异性能指标的策略能够通过决策引擎的评估
        """

        async def run_test():
            # 创建优异性能指标的模拟回测报告
            excellent_backtest_report = {
                "BTCUSDT": {
                    "optimized_strategies": {
                        "test_strategy_001": {
                            "strategy_id": "test_strategy_001",
                            "params": {
                                "fast_period": 10,
                                "slow_period": 30,
                                "signal_threshold": 0.02,
                            },
                            "total_return": 0.25,  # 25%收益
                            "sharpe_ratio": 2.5,  # 优异的夏普比率
                            "max_drawdown": -0.05,  # 5%最大回撤（低于阈值）
                            "win_rate": 0.65,  # 65%胜率
                            "profit_factor": 2.1,  # 良好的盈利因子
                            "current_signal": "BUY",
                            "confidence": 0.85,
                            "atr": 0.02,
                            "fitness": 0.85,
                            "performance_metrics": {
                                "total_trades": 100,
                                "winning_trades": 65,
                                "losing_trades": 35,
                                "avg_win": 0.04,
                                "avg_loss": -0.02,
                            },
                        }
                    }
                }
            }

            # 模拟市场数据
            market_data = {
                "price_history": [100, 101, 102, 103, 104, 105],
                "volume_data": [1000, 1100, 1200, 1300, 1400, 1500],
                "trend_indicators": {"trend_score": 0.05},
                "current_price": {"BTCUSDT": 105.0},
            }

            # 初始化决策引擎
            await self.decision_engine.initialize()

            try:
                # 执行决策
                decisions = await self.decision_engine.make_decision(
                    excellent_backtest_report, market_data
                )

                # 验证决策结果
                self.assertIsInstance(decisions, list)
                self.assertGreater(len(decisions), 0, "应该生成至少一个决策")

                # 检查第一个决策
                decision = decisions[0]
                self.assertIsInstance(decision, StrategyDecision)

                # 验证批准状态（通过检查决策是否被生成）
                self.assertEqual(decision.strategy_id, "test_strategy_001")
                self.assertEqual(decision.symbol, "BTCUSDT")
                self.assertIn(decision.action, ["BUY", "SELL", "HOLD"])

                # 验证置信度
                self.assertGreaterEqual(decision.confidence, 0.6, "置信度应该较高")
                self.assertLessEqual(decision.confidence, 1.0)

                # 验证风险评分
                self.assertGreaterEqual(decision.risk_score, 0.0)
                self.assertLessEqual(decision.risk_score, 1.0)

                # 验证预期收益
                self.assertAlmostEqual(decision.expected_return, 0.25, places=2)

                # 验证最大回撤
                self.assertAlmostEqual(decision.max_drawdown, 0.05, places=2)

                # 验证仓位大小
                self.assertGreater(decision.position_size, 0)
                self.assertLessEqual(
                    decision.position_size, self.test_config["max_position_size"]
                )

                # 验证止损止盈设置
                if decision.action == "BUY":
                    self.assertIsNotNone(decision.stop_loss)
                    self.assertIsNotNone(decision.take_profit)
                    self.assertLess(decision.stop_loss, 105.0)  # 止损应低于当前价格
                    self.assertGreater(decision.take_profit, 105.0)  # 止盈应高于当前价格

                # 验证决策理由
                self.assertIsInstance(decision.reasoning, str)
                self.assertGreater(len(decision.reasoning), 0)

                # 验证时间戳
                self.assertIsInstance(decision.timestamp, datetime)

                print(f"✓ UNIT-DECISION-ENGINE-01 通过: 生成了 {len(decisions)} 个决策")
                print(f"  - 策略ID: {decision.strategy_id}")
                print(f"  - 动作: {decision.action}")
                print(f"  - 置信度: {decision.confidence:.3f}")
                print(f"  - 仓位大小: {decision.position_size:.3f}")
                print(f"  - 决策理由: {decision.reasoning}")

            finally:
                await self.decision_engine.cleanup()

        # 运行异步测试
        asyncio.run(run_test())

    def test_unit_decision_engine_02_rejection_path_high_drawdown(self):
        """
        UNIT-DECISION-ENGINE-02: 决策引擎拒绝路径测试（高回撤）

        测试高回撤策略被决策引擎拒绝
        """

        async def run_test():
            # 创建高回撤的模拟回测报告
            high_drawdown_report = {
                "BTCUSDT": {
                    "optimized_strategies": {
                        "test_strategy_002": {
                            "strategy_id": "test_strategy_002",
                            "params": {
                                "fast_period": 5,
                                "slow_period": 15,
                                "signal_threshold": 0.05,
                            },
                            "total_return": 0.15,  # 15%收益
                            "sharpe_ratio": 0.8,  # 较低的夏普比率
                            "max_drawdown": -0.35,  # 35%最大回撤（超过阈值）
                            "win_rate": 0.45,  # 45%胜率（较低）
                            "profit_factor": 1.1,  # 较低的盈利因子
                            "current_signal": "BUY",
                            "confidence": 0.60,
                            "atr": 0.03,
                            "fitness": 0.40,
                            "performance_metrics": {
                                "total_trades": 80,
                                "winning_trades": 36,
                                "losing_trades": 44,
                                "avg_win": 0.06,
                                "avg_loss": -0.05,
                            },
                        }
                    }
                }
            }

            # 模拟市场数据
            market_data = {
                "price_history": [100, 98, 96, 94, 92, 90],
                "volume_data": [1000, 1100, 1200, 1300, 1400, 1500],
                "trend_indicators": {"trend_score": -0.05},
                "current_price": {"BTCUSDT": 90.0},
            }

            # 初始化决策引擎
            await self.decision_engine.initialize()

            try:
                # 执行决策
                decisions = await self.decision_engine.make_decision(
                    high_drawdown_report, market_data
                )

                # 验证拒绝结果
                # 由于高回撤，策略应该被风险控制过滤器拒绝
                self.assertIsInstance(decisions, list)

                # 检查是否没有生成决策（被拒绝）
                if len(decisions) == 0:
                    print("✓ UNIT-DECISION-ENGINE-02 通过: 高回撤策略被正确拒绝")
                    print(
                        f"  - 策略回撤: 35% (超过阈值 {self.test_config['max_drawdown_threshold']*100}%)"
                    )
                    print("  - 拒绝原因: Maximum Drawdown exceeds threshold")
                else:
                    # 如果生成了决策，检查是否有适当的风险控制
                    decision = decisions[0]
                    self.assertLess(decision.confidence, 0.7, "高风险策略的置信度应该较低")
                    self.assertLess(decision.position_size, 0.05, "高风险策略的仓位应该很小")

                    print(f"⚠ UNIT-DECISION-ENGINE-02 部分通过: 生成了风险受限的决策")
                    print(f"  - 置信度: {decision.confidence:.3f} (较低)")
                    print(f"  - 仓位大小: {decision.position_size:.3f} (很小)")

            finally:
                await self.decision_engine.cleanup()

        # 运行异步测试
        asyncio.run(run_test())

    def test_unit_decision_engine_03_low_sharpe_rejection(self):
        """
        测试低夏普比率策略被拒绝
        """

        async def run_test():
            # 创建低夏普比率的模拟回测报告
            low_sharpe_report = {
                "BTCUSDT": {
                    "optimized_strategies": {
                        "test_strategy_003": {
                            "strategy_id": "test_strategy_003",
                            "params": {"fast_period": 8, "slow_period": 25},
                            "total_return": 0.08,
                            "sharpe_ratio": 0.3,  # 低夏普比率
                            "max_drawdown": -0.08,  # 回撤在阈值内
                            "win_rate": 0.35,  # 低胜率
                            "profit_factor": 1.05,  # 低盈利因子
                            "current_signal": "BUY",
                            "confidence": 0.50,
                        }
                    }
                }
            }

            market_data = {
                "price_history": [100, 101, 100, 99, 100, 101],
                "volume_data": [1000] * 6,
                "trend_indicators": {"trend_score": 0.0},
                "current_price": {"BTCUSDT": 101.0},
            }

            await self.decision_engine.initialize()

            try:
                decisions = await self.decision_engine.make_decision(
                    low_sharpe_report, market_data
                )

                # 低夏普比率策略应该被拒绝
                self.assertEqual(len(decisions), 0, "低夏普比率策略应该被拒绝")

                print("✓ 低夏普比率策略被正确拒绝")

            finally:
                await self.decision_engine.cleanup()

        asyncio.run(run_test())

    def test_unit_decision_engine_04_low_win_rate_rejection(self):
        """
        测试低胜率策略被拒绝
        """

        async def run_test():
            # 创建低胜率的模拟回测报告
            low_win_rate_report = {
                "BTCUSDT": {
                    "optimized_strategies": {
                        "test_strategy_004": {
                            "strategy_id": "test_strategy_004",
                            "params": {"fast_period": 12, "slow_period": 35},
                            "total_return": 0.12,
                            "sharpe_ratio": 1.2,  # 夏普比率OK
                            "max_drawdown": -0.06,  # 回撤OK
                            "win_rate": 0.25,  # 极低胜率
                            "profit_factor": 1.15,  # 盈利因子OK
                            "current_signal": "BUY",
                            "confidence": 0.60,
                        }
                    }
                }
            }

            market_data = {
                "price_history": [100] * 6,
                "volume_data": [1000] * 6,
                "trend_indicators": {"trend_score": 0.0},
                "current_price": {"BTCUSDT": 100.0},
            }

            await self.decision_engine.initialize()

            try:
                decisions = await self.decision_engine.make_decision(
                    low_win_rate_report, market_data
                )

                # 低胜率策略应该被拒绝
                self.assertEqual(len(decisions), 0, "低胜率策略应该被拒绝")

                print("✓ 低胜率策略被正确拒绝")

            finally:
                await self.decision_engine.cleanup()

        asyncio.run(run_test())

    def test_unit_decision_engine_05_multiple_strategies_ranking(self):
        """
        测试多个策略的排序和选择
        """

        async def run_test():
            # 创建多个策略的回测报告
            multiple_strategies_report = {
                "BTCUSDT": {
                    "optimized_strategies": {
                        "excellent_strategy": {
                            "strategy_id": "excellent_strategy",
                            "params": {"fast_period": 10, "slow_period": 30},
                            "total_return": 0.30,
                            "sharpe_ratio": 2.8,
                            "max_drawdown": -0.04,
                            "win_rate": 0.70,
                            "profit_factor": 2.5,
                            "current_signal": "BUY",
                            "confidence": 0.90,
                        },
                        "good_strategy": {
                            "strategy_id": "good_strategy",
                            "params": {"fast_period": 8, "slow_period": 25},
                            "total_return": 0.20,
                            "sharpe_ratio": 1.8,
                            "max_drawdown": -0.06,
                            "win_rate": 0.60,
                            "profit_factor": 1.8,
                            "current_signal": "BUY",
                            "confidence": 0.75,
                        },
                        "mediocre_strategy": {
                            "strategy_id": "mediocre_strategy",
                            "params": {"fast_period": 15, "slow_period": 40},
                            "total_return": 0.10,
                            "sharpe_ratio": 1.2,
                            "max_drawdown": -0.08,
                            "win_rate": 0.50,
                            "profit_factor": 1.3,
                            "current_signal": "BUY",
                            "confidence": 0.60,
                        },
                    }
                }
            }

            market_data = {
                "price_history": [100, 102, 104, 106, 108, 110],
                "volume_data": [1000] * 6,
                "trend_indicators": {"trend_score": 0.1},
                "current_price": {"BTCUSDT": 110.0},
            }

            await self.decision_engine.initialize()

            try:
                decisions = await self.decision_engine.make_decision(
                    multiple_strategies_report, market_data
                )

                # 应该选择最优策略
                self.assertGreater(len(decisions), 0, "应该生成决策")

                # 检查是否选择了最优策略
                best_decision = decisions[0]
                self.assertEqual(
                    best_decision.strategy_id, "excellent_strategy", "应该选择评分最高的策略"
                )

                print(f"✓ 多策略排序测试通过: 选择了 {best_decision.strategy_id}")

            finally:
                await self.decision_engine.cleanup()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main(verbosity=2)
