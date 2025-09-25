#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 数据库管理
SQLite数据库连接和操作管理

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import aiosqlite
from loguru import logger

from src.core.config import settings
from src.models.simulation import (
    TaskStatus,
    ScenarioType,
    SimulationTask,
    SimulationResult,
    MarketData,
    CalibrationParams,
)


class DatabaseManager:
    """数据库管理器"""
    
    # 类级别的内存数据库连接，确保在测试中共享同一个连接
    _memory_connection = None
    _connection_lock = asyncio.Lock()

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_path
        self._connection_pool = None
        logger.info(f"数据库管理器初始化，数据库路径: {self.database_url}")

    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        if self.database_url == ':memory:':
            # 对于内存数据库，使用类级别的共享连接
            async with DatabaseManager._connection_lock:
                if DatabaseManager._memory_connection is None:
                    DatabaseManager._memory_connection = await aiosqlite.connect(self.database_url)
                    DatabaseManager._memory_connection.row_factory = aiosqlite.Row
                yield DatabaseManager._memory_connection
        else:
            async with aiosqlite.connect(self.database_url) as conn:
                conn.row_factory = aiosqlite.Row
                yield conn

    async def init_database(self):
        """初始化数据库表结构"""
        logger.info("开始初始化数据库表结构...")

        # 对于内存数据库，确保初始化类级别连接
        if self.database_url == ':memory:':
            async with DatabaseManager._connection_lock:
                if DatabaseManager._memory_connection is None:
                    DatabaseManager._memory_connection = await aiosqlite.connect(self.database_url)
                    DatabaseManager._memory_connection.row_factory = aiosqlite.Row
                await self._init_tables(DatabaseManager._memory_connection)
        else:
            async with self.get_connection() as conn:
                await self._init_tables(conn)

    async def _init_tables(self, conn):
        """初始化数据库表"""
        # 创建仿真任务表
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_tasks (
                task_id VARCHAR(50) PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                period VARCHAR(10) NOT NULL,
                scenario VARCHAR(30) NOT NULL,
                strategy_params TEXT NOT NULL,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
                error_message TEXT
            )
        """
        )

        # 创建仿真结果表
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_results (
                result_id VARCHAR(50) PRIMARY KEY,
                task_id VARCHAR(50) NOT NULL,
                slippage REAL NOT NULL,
                fill_probability REAL NOT NULL,
                price_impact REAL NOT NULL,
                total_return REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                sharpe_ratio REAL NOT NULL,
                report_path VARCHAR(255),
                execution_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES simulation_tasks(task_id)
            )
        """
        )

        # 创建市场数据表
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_data (
                data_id VARCHAR(50) PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume REAL NOT NULL,
                bid_price REAL,
                ask_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 创建校准参数表
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calibration_params (
                param_id VARCHAR(50) PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                scenario VARCHAR(30) NOT NULL,
                base_slippage REAL NOT NULL,
                volatility_factor REAL NOT NULL,
                liquidity_factor REAL NOT NULL,
                calibrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """
        )

        # 创建索引
        await self._create_indexes(conn)

        # 插入初始数据
        await self._insert_initial_data(conn)

        await conn.commit()
        logger.info("数据库表结构初始化完成")

    async def _create_indexes(self, conn):
        """创建数据库索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_symbol ON simulation_tasks(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_status ON simulation_tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_tasks_created_at ON simulation_tasks(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_results_task_id ON simulation_results(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_simulation_results_created_at ON simulation_results(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_calibration_params_symbol_scenario ON calibration_params(symbol, scenario)",
            "CREATE INDEX IF NOT EXISTS idx_calibration_params_active ON calibration_params(is_active)",
        ]

        for index_sql in indexes:
            await conn.execute(index_sql)

    async def _insert_initial_data(self, conn):
        """插入初始校准参数数据"""
        # 在测试环境中跳过初始数据插入
        if self.database_url == ":memory:":
            logger.debug("测试环境，跳过初始数据插入")
            return
            
        # 检查是否已有数据
        cursor = await conn.execute("SELECT COUNT(*) FROM calibration_params")
        count = (await cursor.fetchone())[0]

        if count == 0:
            initial_params = [
                ("cal_btcusdt_normal", "BTCUSDT", "normal", 0.001, 1.0, 1.0),
                ("cal_btcusdt_black_swan", "BTCUSDT", "black_swan", 0.005, 3.0, 0.3),
                (
                    "cal_btcusdt_high_volatility",
                    "BTCUSDT",
                    "high_volatility",
                    0.003,
                    2.0,
                    0.6,
                ),
                ("cal_ethusdt_normal", "ETHUSDT", "normal", 0.0012, 1.1, 0.9),
                ("cal_ethusdt_black_swan", "ETHUSDT", "black_swan", 0.006, 3.2, 0.25),
                (
                    "cal_ethusdt_high_volatility",
                    "ETHUSDT",
                    "high_volatility",
                    0.0035,
                    2.1,
                    0.55,
                ),
            ]

            await conn.executemany(
                """
                INSERT INTO calibration_params 
                (param_id, symbol, scenario, base_slippage, volatility_factor, liquidity_factor)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                initial_params,
            )

            logger.info("插入初始校准参数数据完成")

    async def save_simulation_task(self, task: SimulationTask) -> bool:
        """保存仿真任务"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO simulation_tasks 
                    (task_id, symbol, period, scenario, strategy_params, start_time, end_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.symbol,
                        task.period,
                        task.scenario.value if hasattr(task.scenario, 'value') else task.scenario,
                        json.dumps(task.strategy_params),
                        task.start_time,
                        task.end_time,
                        task.status.value if hasattr(task.status, 'value') else task.status,
                    ),
                )
                await conn.commit()
                logger.debug(f"保存仿真任务 {task.task_id} 成功")
                return True
        except Exception as e:
            logger.error(f"保存仿真任务失败: {e}")
            return False

    async def save_simulation_result(self, result: SimulationResult) -> bool:
        """保存仿真结果"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO simulation_results 
                    (result_id, task_id, slippage, fill_probability, price_impact, 
                     total_return, max_drawdown, sharpe_ratio, report_path, execution_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.result_id,
                        result.task_id,
                        result.slippage,
                        result.fill_probability,
                        result.price_impact,
                        result.total_return,
                        result.max_drawdown,
                        result.sharpe_ratio,
                        result.report_path,
                        result.execution_time,
                    ),
                )
                await conn.commit()
                logger.debug(f"保存仿真结果 {result.result_id} 成功")
                return True
        except Exception as e:
            logger.error(f"保存仿真结果失败: {e}")
            return False

    async def update_task_status(
        self, task_id: str, status: str, error_message: str = None
    ) -> bool:
        """更新任务状态"""
        try:
            async with self.get_connection() as conn:
                if status == "running":
                    await conn.execute(
                        "UPDATE simulation_tasks SET status = ?, started_at = ? WHERE task_id = ?",
                        (status, datetime.now(), task_id),
                    )
                elif status in ["completed", "failed"]:
                    await conn.execute(
                        "UPDATE simulation_tasks SET status = ?, completed_at = ?, error_message = ? WHERE task_id = ?",
                        (status, datetime.now(), error_message, task_id),
                    )
                else:
                    await conn.execute(
                        "UPDATE simulation_tasks SET status = ? WHERE task_id = ?",
                        (status, task_id),
                    )

                await conn.commit()
                logger.debug(f"更新任务 {task_id} 状态为 {status}")
                return True
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False

    async def get_calibration_params_by_symbol_and_scenario(
        self, symbol: str, scenario: str
    ) -> Optional[CalibrationParams]:
        """根据交易品种和场景获取校准参数"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT * FROM calibration_params 
                    WHERE symbol = ? AND scenario = ? AND is_active = TRUE
                    ORDER BY calibrated_at DESC LIMIT 1
                    """,
                    (symbol, scenario),
                )
                row = await cursor.fetchone()

                if row:
                    return CalibrationParams(
                        param_id=row["param_id"],
                        symbol=row["symbol"],
                        scenario=ScenarioType(row["scenario"]),
                        base_slippage=row["base_slippage"],
                        volatility_factor=row["volatility_factor"],
                        liquidity_factor=row["liquidity_factor"],
                        calibrated_at=row["calibrated_at"],
                        is_active=row["is_active"],
                    )
                return None
        except Exception as e:
            logger.error(f"获取校准参数失败: {e}")
            return None

    async def get_market_data(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> List[MarketData]:
        """获取市场数据"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT * FROM market_data 
                    WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                    """,
                    (symbol, start_time, end_time),
                )
                rows = await cursor.fetchall()

                return [
                    MarketData(
                        data_id=row["data_id"],
                        symbol=row["symbol"],
                        timestamp=row["timestamp"],
                        open_price=row["open_price"],
                        high_price=row["high_price"],
                        low_price=row["low_price"],
                        close_price=row["close_price"],
                        volume=row["volume"],
                        bid_price=row["bid_price"],
                        ask_price=row["ask_price"],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return []

    async def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            async with self.get_connection() as conn:
                # 总任务数
                cursor = await conn.execute("SELECT COUNT(*) FROM simulation_tasks")
                total_tasks = (await cursor.fetchone())[0]

                # 各状态任务数
                cursor = await conn.execute(
                    "SELECT status, COUNT(*) FROM simulation_tasks GROUP BY status"
                )
                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                # 平均执行时间
                cursor = await conn.execute(
                    "SELECT AVG(execution_time) FROM simulation_results WHERE execution_time IS NOT NULL"
                )
                avg_execution_time = (await cursor.fetchone())[0] or 0

                return {
                    "total_tasks": total_tasks,
                    "status_counts": status_counts,
                    "avg_execution_time": avg_execution_time,
                    "completed_tasks": status_counts.get("completed", 0),
                    "failed_tasks": status_counts.get("failed", 0),
                    "pending_tasks": status_counts.get("pending", 0),
                }
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}

    async def get_table_names(self) -> List[str]:
        """获取数据库表名列表"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取表名失败: {e}")
            return []

    async def save_calibration_params(self, params: CalibrationParams) -> bool:
        """保存校准参数"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO calibration_params 
                    (param_id, symbol, scenario, base_slippage, volatility_factor, 
                     liquidity_factor, calibrated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        params.param_id,
                        params.symbol,
                        params.scenario.value,
                        params.base_slippage,
                        params.volatility_factor,
                        params.liquidity_factor,
                        params.calibrated_at,
                        params.is_active,
                    ),
                )
                await conn.commit()
                logger.debug(f"保存校准参数 {params.param_id} 成功")
                return True
        except Exception as e:
            logger.error(f"保存校准参数失败: {e}")
            return False

    async def get_calibration_params(self) -> List[CalibrationParams]:
        """获取所有校准参数"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM calibration_params WHERE is_active = TRUE ORDER BY calibrated_at DESC"
                )
                rows = await cursor.fetchall()
                
                params_list = []
                for row in rows:
                    params = CalibrationParams(
                        param_id=row["param_id"],
                        symbol=row["symbol"],
                        scenario=ScenarioType(row["scenario"]),
                        base_slippage=row["base_slippage"],
                        volatility_factor=row["volatility_factor"],
                        liquidity_factor=row["liquidity_factor"],
                        calibrated_at=row["calibrated_at"],
                        is_active=row["is_active"],
                    )
                    params_list.append(params)
                
                return params_list
        except Exception as e:
            logger.error(f"获取校准参数失败: {e}")
            return []

    async def get_calibration_params_by_symbol(self, symbol: str) -> List[CalibrationParams]:
        """根据交易品种获取校准参数"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM calibration_params WHERE symbol = ? AND is_active = TRUE ORDER BY calibrated_at DESC",
                    (symbol,)
                )
                rows = await cursor.fetchall()
                
                params_list = []
                for row in rows:
                    params = CalibrationParams(
                        param_id=row["param_id"],
                        symbol=row["symbol"],
                        scenario=ScenarioType(row["scenario"]),
                        base_slippage=row["base_slippage"],
                        volatility_factor=row["volatility_factor"],
                        liquidity_factor=row["liquidity_factor"],
                        calibrated_at=row["calibrated_at"],
                        is_active=row["is_active"],
                    )
                    params_list.append(params)
                
                return params_list
        except Exception as e:
            logger.error(f"获取校准参数失败: {e}")
            return []

    async def update_calibration_params(self, params: CalibrationParams) -> bool:
        """更新校准参数"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE calibration_params 
                    SET symbol = ?, scenario = ?, base_slippage = ?, 
                        volatility_factor = ?, liquidity_factor = ?, 
                        calibrated_at = ?, is_active = ?
                    WHERE param_id = ?
                    """,
                    (
                        params.symbol,
                        params.scenario.value,
                        params.base_slippage,
                        params.volatility_factor,
                        params.liquidity_factor,
                        params.calibrated_at,
                        params.is_active,
                        params.param_id,
                    ),
                )
                await conn.commit()
                logger.debug(f"更新校准参数 {params.param_id} 成功")
                return True
        except Exception as e:
            logger.error(f"更新校准参数失败: {e}")
            return False

    async def delete_calibration_params(self, param_id: str) -> bool:
        """删除校准参数"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "DELETE FROM calibration_params WHERE param_id = ?",
                    (param_id,)
                )
                await conn.commit()
                logger.debug(f"删除校准参数 {param_id} 成功")
                return True
        except Exception as e:
            logger.error(f"删除校准参数失败: {e}")
            return False

    async def get_simulation_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取仿真任务"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM simulation_tasks WHERE task_id = ?",
                    (task_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return {
                        "task_id": row["task_id"],
                        "symbol": row["symbol"],
                        "period": row["period"],
                        "scenario": row["scenario"],
                        "strategy_params": json.loads(row["strategy_params"]) if row["strategy_params"] else {},
                        "start_time": row["start_time"],
                        "end_time": row["end_time"],
                        "status": row["status"],
                    }
                return None
        except Exception as e:
            logger.error(f"获取仿真任务失败: {e}")
            return None

    async def get_simulation_tasks(self) -> List[SimulationTask]:
        """获取所有仿真任务"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute("SELECT * FROM simulation_tasks ORDER BY start_time DESC")
                rows = await cursor.fetchall()
                
                tasks = []
                for row in rows:
                    task = SimulationTask(
                        task_id=row["task_id"],
                        symbol=row["symbol"],
                        period=row["period"],
                        scenario=row["scenario"],
                        strategy_params=json.loads(row["strategy_params"]) if row["strategy_params"] else {},
                        start_time=row["start_time"],
                        end_time=row["end_time"],
                        status=row["status"]
                    )
                    tasks.append(task)
                return tasks
        except Exception as e:
            logger.error(f"获取仿真任务列表失败: {e}")
            return []

    async def get_simulation_task_by_id(self, task_id: str) -> Optional[SimulationTask]:
        """根据ID获取仿真任务"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM simulation_tasks WHERE task_id = ?",
                    (task_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return SimulationTask(
                        task_id=row["task_id"],
                        symbol=row["symbol"],
                        period=row["period"],
                        scenario=row["scenario"],
                        strategy_params=json.loads(row["strategy_params"]) if row["strategy_params"] else {},
                        start_time=row["start_time"],
                        end_time=row["end_time"],
                        status=row["status"]
                    )
                return None
        except Exception as e:
            logger.error(f"获取仿真任务失败: {e}")
            return None

    async def update_simulation_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新仿真任务状态"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "UPDATE simulation_tasks SET status = ? WHERE task_id = ?",
                    (status.value, task_id)
                )
                await conn.commit()
                logger.debug(f"更新任务 {task_id} 状态为 {status.value}")
                return True
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False

    async def delete_simulation_task(self, task_id: str) -> bool:
        """删除仿真任务"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "DELETE FROM simulation_tasks WHERE task_id = ?",
                    (task_id,)
                )
                await conn.commit()
                logger.debug(f"删除任务 {task_id} 成功")
                return True
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False

    async def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """执行查询语句"""
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                return rows
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            from src.utils.exceptions import DatabaseError
            raise DatabaseError(f"查询执行失败: {e}")

    async def execute_transaction(self, queries: List[str]) -> bool:
        """执行事务"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("BEGIN")
                for query in queries:
                    await conn.execute(query)
                await conn.commit()
                return True
            except Exception as e:
                logger.error(f"执行事务失败: {e}")
                await conn.rollback()
                from src.utils.exceptions import DatabaseError
                raise DatabaseError(f"事务执行失败: {e}")

    async def close(self):
        """关闭数据库连接"""
        if DatabaseManager._memory_connection:
            await DatabaseManager._memory_connection.close()
            DatabaseManager._memory_connection = None
            logger.debug("内存数据库连接已关闭")
        else:
            logger.debug("数据库连接已关闭")


# 全局数据库管理器实例
_db_manager = None


async def get_database() -> DatabaseManager:
    """获取数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database():
    """初始化数据库"""
    db = await get_database()
    await db.init_database()
