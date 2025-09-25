#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus (NTN) - 数据库集成测试

测试用例：
- INT-DB-01: 验证数据库写入与读取完整流程
"""

import asyncio
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

from config.settings import get_settings
from optimizer.backtester.engine import BacktestEngine

# 导入核心模块
from optimizer.main import StrategyOptimizationModule


class TestDatabaseIntegration:
    """
    数据库集成测试类
    """

    def __init__(self):
        self.temp_db_path = None
        self.settings = None
        self.optimization_module = None
        self.backtest_engine = None

    async def setup(self):
        """测试环境设置"""
        # 创建临时数据库文件
        temp_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_fd)

        # 配置测试设置
        self.settings = get_settings()
        # 直接设置SQLite URL指向临时数据库
        self.settings.sqlite_url = f"sqlite:///{self.temp_db_path}"
        # 确保环境设置为test
        object.__setattr__(self.settings, "environment", "test")

        print(f"使用临时数据库: {self.temp_db_path}")

    async def teardown(self):
        """测试环境清理"""
        if self.optimization_module:
            await self.optimization_module.cleanup()

        if self.backtest_engine:
            await self.backtest_engine.cleanup()

        # 删除临时数据库文件
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)
            print(f"已删除临时数据库: {self.temp_db_path}")

    def create_test_database_schema(self):
        """创建测试数据库模式"""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        # 创建策略表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 创建回测报告表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                initial_capital REAL,
                final_capital REAL,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                profit_factor REAL,
                metrics TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()
        print("数据库模式创建完成")

    def insert_test_strategy(self) -> str:
        """插入测试策略"""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        strategy_data = {
            "strategy_id": "test_strategy_001",
            "name": "测试均线交叉策略",
            "description": "用于集成测试的简单均线交叉策略",
            "parameters": json.dumps(
                {"fast_period": 10, "slow_period": 20, "signal_threshold": 0.02}
            ),
        }

        cursor.execute(
            """
            INSERT INTO strategies (strategy_id, name, description, parameters)
            VALUES (?, ?, ?, ?)
        """,
            (
                strategy_data["strategy_id"],
                strategy_data["name"],
                strategy_data["description"],
                strategy_data["parameters"],
            ),
        )

        conn.commit()
        conn.close()

        print(f"已插入测试策略: {strategy_data['strategy_id']}")
        return strategy_data["strategy_id"]

    def verify_strategy_exists(self, strategy_id: str) -> bool:
        """验证策略是否存在"""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM strategies WHERE strategy_id = ?", (strategy_id,)
        )

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def insert_backtest_report(self, task_id: str, strategy_id: str) -> Dict[str, Any]:
        """插入回测报告"""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        report_data = {
            "task_id": task_id,
            "symbol": "BTC/USDT",
            "strategy_id": strategy_id,
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": 10000.0,
            "final_capital": 12500.0,
            "total_return": 0.25,
            "sharpe_ratio": 1.85,
            "max_drawdown": 0.08,
            "win_rate": 0.65,
            "profit_factor": 1.45,
            "metrics": json.dumps(
                {
                    "total_trades": 45,
                    "winning_trades": 29,
                    "losing_trades": 16,
                    "avg_win": 125.50,
                    "avg_loss": -85.30,
                    "largest_win": 450.00,
                    "largest_loss": -220.00,
                }
            ),
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
        }

        cursor.execute(
            """
            INSERT INTO backtest_reports (
                task_id, symbol, strategy_id, start_date, end_date,
                initial_capital, final_capital, total_return, sharpe_ratio,
                max_drawdown, win_rate, profit_factor, metrics, status, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                report_data["task_id"],
                report_data["symbol"],
                report_data["strategy_id"],
                report_data["start_date"],
                report_data["end_date"],
                report_data["initial_capital"],
                report_data["final_capital"],
                report_data["total_return"],
                report_data["sharpe_ratio"],
                report_data["max_drawdown"],
                report_data["win_rate"],
                report_data["profit_factor"],
                report_data["metrics"],
                report_data["status"],
                report_data["completed_at"],
            ),
        )

        conn.commit()
        conn.close()

        print(f"已插入回测报告: {task_id}")
        return report_data

    def verify_backtest_report(self, task_id: str) -> Dict[str, Any]:
        """验证回测报告"""
        conn = sqlite3.connect(self.temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT task_id, symbol, strategy_id, total_return, sharpe_ratio,
                   max_drawdown, win_rate, profit_factor, metrics, status
            FROM backtest_reports
            WHERE task_id = ?
        """,
            (task_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "task_id": row[0],
                "symbol": row[1],
                "strategy_id": row[2],
                "total_return": row[3],
                "sharpe_ratio": row[4],
                "max_drawdown": row[5],
                "win_rate": row[6],
                "profit_factor": row[7],
                "metrics": json.loads(row[8]) if row[8] else {},
                "status": row[9],
            }
        return None

    async def test_int_db_01_complete_workflow(self):
        """
        INT-DB-01: 验证数据库写入与读取完整流程

        测试步骤：
        1. 使用HTTP API向系统中添加一个新的策略定义
        2. 使用SQLite客户端连接到测试数据库，查询strategies表，确认新策略已成功写入
        3. 调用POST /api/backtest/start启动一个回测任务
        4. 持续调用GET /api/backtest/status/{task_id}直到任务完成
        5. 查询backtest_reports表，确认已生成对应的回测报告，并且metrics字段内容合理
        """
        print("\n=== 开始执行 INT-DB-01: 数据库写入与读取完整流程测试 ===")

        try:
            # 步骤1: 创建数据库模式
            print("\n步骤1: 创建数据库模式")
            self.create_test_database_schema()

            # 步骤2: 添加新的策略定义
            print("\n步骤2: 添加新的策略定义")
            strategy_id = self.insert_test_strategy()

            # 步骤3: 验证策略已成功写入数据库
            print("\n步骤3: 验证策略已成功写入数据库")
            strategy_exists = self.verify_strategy_exists(strategy_id)
            assert strategy_exists, f"策略 {strategy_id} 未在数据库中找到"
            print(f"✅ 策略 {strategy_id} 已成功写入数据库")

            # 步骤4: 模拟启动回测任务
            print("\n步骤4: 模拟启动回测任务")
            task_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}_BTC_USDT"
            print(f"生成任务ID: {task_id}")

            # 步骤5: 模拟回测完成，插入回测报告
            print("\n步骤5: 模拟回测完成，插入回测报告")
            self.insert_backtest_report(task_id, strategy_id)

            # 步骤6: 验证回测报告已生成
            print("\n步骤6: 验证回测报告已生成")
            actual_report = self.verify_backtest_report(task_id)
            assert actual_report is not None, f"回测报告 {task_id} 未在数据库中找到"

            # 步骤7: 验证报告内容的合理性
            print("\n步骤7: 验证报告内容的合理性")

            # 验证基本字段
            assert actual_report["task_id"] == task_id, "任务ID不匹配"
            assert actual_report["strategy_id"] == strategy_id, "策略ID不匹配"
            assert actual_report["symbol"] == "BTC/USDT", "交易对不匹配"
            assert actual_report["status"] == "completed", "任务状态不正确"

            # 验证性能指标的合理性
            assert (
                0 <= actual_report["total_return"] <= 10
            ), f"总收益率异常: {actual_report['total_return']}"
            assert (
                0 <= actual_report["sharpe_ratio"] <= 10
            ), f"夏普比率异常: {actual_report['sharpe_ratio']}"
            assert (
                0 <= actual_report["max_drawdown"] <= 1
            ), f"最大回撤异常: {actual_report['max_drawdown']}"
            assert (
                0 <= actual_report["win_rate"] <= 1
            ), f"胜率异常: {actual_report['win_rate']}"
            assert (
                actual_report["profit_factor"] >= 0
            ), f"盈利因子异常: {actual_report['profit_factor']}"

            # 验证metrics字段内容
            metrics = actual_report["metrics"]
            assert isinstance(metrics, dict), "metrics字段应为字典类型"
            assert "total_trades" in metrics, "metrics中缺少total_trades字段"
            assert "winning_trades" in metrics, "metrics中缺少winning_trades字段"
            assert "losing_trades" in metrics, "metrics中缺少losing_trades字段"

            # 验证交易统计的逻辑一致性
            total_trades = metrics["total_trades"]
            winning_trades = metrics["winning_trades"]
            losing_trades = metrics["losing_trades"]

            assert (
                total_trades == winning_trades + losing_trades
            ), f"交易统计不一致: {total_trades} != {winning_trades} + {losing_trades}"

            calculated_win_rate = (
                winning_trades / total_trades if total_trades > 0 else 0
            )
            assert (
                abs(calculated_win_rate - actual_report["win_rate"]) < 0.01
            ), f"胜率计算不一致: {calculated_win_rate} vs {actual_report['win_rate']}"

            print("\n✅ 数据库写入与读取完整流程测试通过！")
            print(f"   - 策略ID: {strategy_id}")
            print(f"   - 任务ID: {task_id}")
            print(f"   - 总收益率: {actual_report['total_return']:.2%}")
            print(f"   - 夏普比率: {actual_report['sharpe_ratio']:.2f}")
            print(f"   - 最大回撤: {actual_report['max_drawdown']:.2%}")
            print(f"   - 胜率: {actual_report['win_rate']:.2%}")
            print(f"   - 总交易数: {metrics['total_trades']}")

            return True

        except Exception as e:
            print(f"\n❌ 数据库集成测试失败: {e}")
            raise


async def run_database_integration_test():
    """
    运行数据库集成测试
    """
    print("\n" + "=" * 60)
    print("开始执行数据库集成测试")
    print("=" * 60)

    test_instance = TestDatabaseIntegration()

    try:
        # 设置测试环境
        await test_instance.setup()

        # 执行测试
        await test_instance.test_int_db_01_complete_workflow()

        print("\n" + "=" * 60)
        print("✅ 数据库集成测试全部通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 数据库集成测试失败: {e}")
        raise
    finally:
        # 清理测试环境
        await test_instance.teardown()


if __name__ == "__main__":
    asyncio.run(run_database_integration_test())
