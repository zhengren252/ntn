#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 数据库初始化脚本
用于创建数据库表结构和初始化数据

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.core.database import DatabaseManager, SimulationTask, CalibrationParams
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""

    def __init__(self, config_path: str = None):
        self.config = Config(config_path)
        self.db_manager = None

    async def initialize(self):
        """初始化数据库管理器"""
        try:
            self.db_manager = DatabaseManager(self.config.get_database_config())
            await self.db_manager.initialize()
            logger.info("数据库管理器初始化成功")
        except Exception as e:
            logger.error(f"数据库管理器初始化失败: {e}")
            raise

    async def create_tables(self, force: bool = False):
        """创建数据库表"""
        logger.info("开始创建数据库表...")

        try:
            # 检查数据库文件是否存在
            db_path = self.config.DATABASE_PATH
            if os.path.exists(db_path) and not force:
                logger.warning(f"数据库文件已存在: {db_path}")
                response = input("是否要重新创建数据库？这将删除所有现有数据 (y/N): ")
                if response.lower() != "y":
                    logger.info("取消数据库创建")
                    return False

            # 删除现有数据库文件（如果存在）
            if os.path.exists(db_path) and force:
                os.remove(db_path)
                logger.info(f"已删除现有数据库文件: {db_path}")

            # 确保数据目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            # 重新初始化数据库管理器
            if self.db_manager:
                await self.db_manager.close()

            await self.initialize()

            # 创建表结构
            await self._create_simulation_tasks_table()
            await self._create_calibration_params_table()
            await self._create_system_logs_table()
            await self._create_performance_metrics_table()

            logger.info("数据库表创建完成")
            return True

        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise

    async def _create_simulation_tasks_table(self):
        """创建仿真任务表"""
        sql = """
        CREATE TABLE IF NOT EXISTS simulation_tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            parameters TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_id TEXT,
            priority INTEGER DEFAULT 1,
            timeout INTEGER DEFAULT 300,
            result TEXT,
            error TEXT,
            execution_time REAL,
            worker_id TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3
        )
        """

        await self.db_manager.execute_query(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_status ON simulation_tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_created_at ON simulation_tasks(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_user_id ON simulation_tasks(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_priority ON simulation_tasks(priority)",
        ]

        for index_sql in indexes:
            await self.db_manager.execute_query(index_sql)

        logger.info("仿真任务表创建完成")

    async def _create_calibration_params_table(self):
        """创建校准参数表"""
        sql = """
        CREATE TABLE IF NOT EXISTS calibration_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            parameters TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            calibration_method TEXT DEFAULT 'maximum_likelihood',
            score REAL,
            version TEXT DEFAULT '1.0.0',
            is_active BOOLEAN DEFAULT 1,
            UNIQUE(ticker, date, version)
        )
        """

        await self.db_manager.execute_query(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_calibration_params_ticker ON calibration_params(ticker)",
            "CREATE INDEX IF NOT EXISTS idx_calibration_params_date ON calibration_params(date)",
            "CREATE INDEX IF NOT EXISTS idx_calibration_params_score ON calibration_params(score)",
            "CREATE INDEX IF NOT EXISTS idx_calibration_params_active ON calibration_params(is_active)",
        ]

        for index_sql in indexes:
            await self.db_manager.execute_query(index_sql)

        logger.info("校准参数表创建完成")

    async def _create_system_logs_table(self):
        """创建系统日志表"""
        sql = """
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            logger_name TEXT NOT NULL,
            message TEXT NOT NULL,
            module TEXT,
            function TEXT,
            line_number INTEGER,
            exception_info TEXT,
            extra_data TEXT
        )
        """

        await self.db_manager.execute_query(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_logger ON system_logs(logger_name)",
        ]

        for index_sql in indexes:
            await self.db_manager.execute_query(index_sql)

        logger.info("系统日志表创建完成")

    async def _create_performance_metrics_table(self):
        """创建性能指标表"""
        sql = """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            tags TEXT,
            description TEXT
        )
        """

        await self.db_manager.execute_query(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type)",
        ]

        for index_sql in indexes:
            await self.db_manager.execute_query(index_sql)

        logger.info("性能指标表创建完成")

    async def insert_sample_data(self):
        """插入示例数据"""
        logger.info("开始插入示例数据...")

        try:
            # 插入示例校准参数
            await self._insert_sample_calibration_params()

            # 插入示例仿真任务
            await self._insert_sample_simulation_tasks()

            logger.info("示例数据插入完成")

        except Exception as e:
            logger.error(f"插入示例数据失败: {e}")
            raise

    async def _insert_sample_calibration_params(self):
        """插入示例校准参数"""
        sample_params = [
            {
                "ticker": "AAPL",
                "date": "2024-01-15",
                "parameters": {
                    "price_impact": 0.0025,
                    "order_arrival_rate": 5.2,
                    "cancellation_rate": 3.1,
                    "volatility": 0.015,
                    "bid_ask_spread": 0.03,
                },
                "calibration_method": "maximum_likelihood",
                "score": 0.92,
                "version": "1.0.0",
            },
            {
                "ticker": "GOOGL",
                "date": "2024-01-15",
                "parameters": {
                    "price_impact": 0.0035,
                    "order_arrival_rate": 4.8,
                    "cancellation_rate": 2.9,
                    "volatility": 0.018,
                    "bid_ask_spread": 0.04,
                },
                "calibration_method": "maximum_likelihood",
                "score": 0.89,
                "version": "1.0.0",
            },
            {
                "ticker": "MSFT",
                "date": "2024-01-15",
                "parameters": {
                    "price_impact": 0.0028,
                    "order_arrival_rate": 5.5,
                    "cancellation_rate": 3.3,
                    "volatility": 0.016,
                    "bid_ask_spread": 0.025,
                },
                "calibration_method": "maximum_likelihood",
                "score": 0.94,
                "version": "1.0.0",
            },
        ]

        for params_data in sample_params:
            calibration_params = CalibrationParams(
                ticker=params_data["ticker"],
                date=params_data["date"],
                parameters=params_data["parameters"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                calibration_method=params_data["calibration_method"],
                score=params_data["score"],
                version=params_data["version"],
            )

            await self.db_manager.save_calibration_params(calibration_params)

        logger.info(f"插入了 {len(sample_params)} 个示例校准参数")

    async def _insert_sample_simulation_tasks(self):
        """插入示例仿真任务"""
        sample_tasks = [
            {
                "task_id": "demo_task_001",
                "status": "completed",
                "parameters": {
                    "ticker": "AAPL",
                    "date": "2024-01-15",
                    "time_window": ["09:30:00", "16:00:00"],
                    "market_depth": 10,
                    "mm_strategy": "adaptive",
                    "mm_params": {
                        "spread": 0.05,
                        "inventory_limit": 1000,
                        "risk_aversion": 0.1,
                    },
                    "arb_strategy": "statistical",
                    "arb_params": {
                        "threshold": 0.02,
                        "holding_period": 5,
                        "max_positions": 10,
                    },
                },
                "user_id": "demo_user",
                "priority": 1,
                "result": {
                    "simulation_id": "demo_task_001",
                    "status": "completed",
                    "execution_time": 45.2,
                    "total_trades": 1250,
                    "mm_trades": 800,
                    "arb_trades": 450,
                    "total_pnl": 15420.50,
                    "mm_pnl": 8950.30,
                    "arb_pnl": 6470.20,
                    "sharpe_ratio": 1.85,
                    "max_drawdown": 0.08,
                    "win_rate": 0.67,
                },
            },
            {
                "task_id": "demo_task_002",
                "status": "pending",
                "parameters": {
                    "ticker": "GOOGL",
                    "date": "2024-01-16",
                    "time_window": ["09:30:00", "16:00:00"],
                    "market_depth": 15,
                    "mm_strategy": "fixed",
                    "mm_params": {
                        "spread": 0.08,
                        "inventory_limit": 500,
                        "risk_aversion": 0.15,
                    },
                    "arb_strategy": "pairs",
                    "arb_params": {
                        "threshold": 0.025,
                        "holding_period": 8,
                        "max_positions": 5,
                    },
                },
                "user_id": "demo_user",
                "priority": 2,
            },
        ]

        for task_data in sample_tasks:
            simulation_task = SimulationTask(
                task_id=task_data["task_id"],
                status=task_data["status"],
                parameters=task_data["parameters"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_id=task_data["user_id"],
                priority=task_data["priority"],
                timeout=300,
                result=task_data.get("result"),
            )

            await self.db_manager.save_simulation_task(simulation_task)

        logger.info(f"插入了 {len(sample_tasks)} 个示例仿真任务")

    async def verify_database(self):
        """验证数据库结构和数据"""
        logger.info("开始验证数据库...")

        try:
            # 检查表是否存在
            tables_to_check = [
                "simulation_tasks",
                "calibration_params",
                "system_logs",
                "performance_metrics",
            ]

            for table_name in tables_to_check:
                result = await self.db_manager.execute_query(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                )

                if result:
                    logger.info(f"✓ 表 {table_name} 存在")

                    # 检查表中的记录数
                    count_result = await self.db_manager.execute_query(
                        f"SELECT COUNT(*) FROM {table_name}"
                    )
                    count = count_result[0][0] if count_result else 0
                    logger.info(f"  记录数: {count}")
                else:
                    logger.error(f"✗ 表 {table_name} 不存在")

            # 检查索引
            indexes_result = await self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )

            if indexes_result:
                index_count = len(indexes_result)
                logger.info(f"✓ 创建了 {index_count} 个索引")

            logger.info("数据库验证完成")
            return True

        except Exception as e:
            logger.error(f"数据库验证失败: {e}")
            return False

    async def cleanup(self):
        """清理资源"""
        if self.db_manager:
            await self.db_manager.close()
            logger.info("数据库连接已关闭")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="市场微结构仿真引擎数据库初始化工具")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--force", action="store_true", help="强制重新创建数据库")
    parser.add_argument("--no-sample-data", action="store_true", help="不插入示例数据")
    parser.add_argument("--verify-only", action="store_true", help="仅验证数据库")

    args = parser.parse_args()

    # 创建数据库初始化器
    initializer = DatabaseInitializer(config_path=args.config)

    try:
        # 初始化数据库管理器
        await initializer.initialize()

        if args.verify_only:
            # 仅验证数据库
            success = await initializer.verify_database()
            return 0 if success else 1

        # 创建数据库表
        success = await initializer.create_tables(force=args.force)
        if not success:
            return 1

        # 插入示例数据（如果需要）
        if not args.no_sample_data:
            await initializer.insert_sample_data()

        # 验证数据库
        await initializer.verify_database()

        logger.info("数据库初始化完成")
        return 0

    except KeyboardInterrupt:
        logger.info("操作被中断")
        return 0
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return 1
    finally:
        await initializer.cleanup()


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
