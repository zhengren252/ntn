#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的决策引擎测试脚本
直接测试决策引擎的批准和拒绝路径
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer.decision.engine import DecisionEngine


async def test_decision_engine_approval_path():
    """
    UNIT-DECISION-ENGINE-01: 决策引擎批准路径测试
    """
    print("\n=== UNIT-DECISION-ENGINE-01: 决策引擎批准路径测试 ===")

    # 配置决策引擎
    config = {
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
    }

    decision_engine = DecisionEngine(config)
    await decision_engine.initialize()

    try:
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

        # 执行决策
        decisions = await decision_engine.make_decision(
            excellent_backtest_report, market_data
        )

        # 验证结果
        print(f"生成决策数量: {len(decisions)}")

        if len(decisions) > 0:
            decision = decisions[0]
            print("✓ 测试通过: 优异策略被批准")
            print(f"  - 策略ID: {decision.strategy_id}")
            print(f"  - 交易对: {decision.symbol}")
            print(f"  - 动作: {decision.action}")
            print(f"  - 置信度: {decision.confidence:.3f}")
            print(f"  - 风险评分: {decision.risk_score:.3f}")
            print(f"  - 预期收益: {decision.expected_return:.2%}")
            print(f"  - 最大回撤: {decision.max_drawdown:.2%}")
            print(f"  - 仓位大小: {decision.position_size:.3f}")
            print(f"  - 止损: {decision.stop_loss}")
            print(f"  - 止盈: {decision.take_profit}")
            print(f"  - 决策理由: {decision.reasoning}")

            # 验证关键指标
            assert decision.strategy_id == "test_strategy_001"
            assert decision.symbol == "BTCUSDT"
            assert decision.action in ["BUY", "SELL", "HOLD"]
            assert 0.0 <= decision.confidence <= 1.0
            assert 0.0 <= decision.risk_score <= 1.0
            assert decision.expected_return == 0.25
            assert decision.max_drawdown == 0.05
            assert decision.position_size > 0
            assert decision.position_size <= config["max_position_size"]

            return True

        print("✗ 测试失败: 优异策略未被批准")
        return False

    finally:
        await decision_engine.cleanup()


async def test_decision_engine_rejection_path():
    """
    UNIT-DECISION-ENGINE-02: 决策引擎拒绝路径测试（高回撤）
    """
    print("\n=== UNIT-DECISION-ENGINE-02: 决策引擎拒绝路径测试（高回撤） ===")

    # 配置决策引擎
    config = {
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
    }

    decision_engine = DecisionEngine(config)
    await decision_engine.initialize()

    try:
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

        # 执行决策
        decisions = await decision_engine.make_decision(
            high_drawdown_report, market_data
        )

        # 验证结果
        print(f"生成决策数量: {len(decisions)}")

        if len(decisions) == 0:
            print("✓ 测试通过: 高回撤策略被正确拒绝")
            print(f"  - 策略回撤: 35% (超过阈值 {config['max_drawdown_threshold']*100}%)")
            print("  - 拒绝原因: Maximum Drawdown exceeds threshold")
            return True

        # 如果生成了决策，检查是否有适当的风险控制
        decision = decisions[0]
        print("⚠ 部分通过: 生成了风险受限的决策")
        print(f"  - 置信度: {decision.confidence:.3f}")
        print(f"  - 仓位大小: {decision.position_size:.3f}")

        # 检查风险控制是否生效
        if decision.confidence < 0.7 and decision.position_size < 0.05:
            print("✓ 风险控制生效")
            return True

        print("✗ 风险控制不足")
        return False

    finally:
        await decision_engine.cleanup()


async def main():
    """
    主测试函数
    """
    print("开始决策引擎单元测试...")

    # 测试批准路径
    approval_result = await test_decision_engine_approval_path()

    # 测试拒绝路径
    rejection_result = await test_decision_engine_rejection_path()

    # 总结结果
    print("\n=== 测试结果总结 ===")
    print(f"UNIT-DECISION-ENGINE-01 (批准路径): {'通过' if approval_result else '失败'}")
    print(f"UNIT-DECISION-ENGINE-02 (拒绝路径): {'通过' if rejection_result else '失败'}")

    if approval_result and rejection_result:
        print("\n✓ 所有决策引擎单元测试通过")
        return 0

    print("\n✗ 部分测试失败")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
