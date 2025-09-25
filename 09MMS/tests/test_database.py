#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 数据库模块测试
测试数据库连接、查询和事务处理

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import pytest
import sqlite3
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from src.core.database import DatabaseManager
from src.models.simulation import SimulationTask, CalibrationParams, TaskStatus, ScenarioType
from src.utils.exceptions import DatabaseError


@pytest.fixture
def mock_db_config():
    """模拟数据库配置"""
    return {
        "db_path": ":memory:",
        "pool_size": 5,
        "timeout": 30,
        "isolation_level": "IMMEDIATE",
    }


@pytest.fixture
def sample_simulation_task():
    """示例仿真任务"""
    return SimulationTask(
        task_id="sim_123",
        symbol="AAPL",
        period="1d",
        scenario=ScenarioType.NORMAL,
        strategy_params={
            "entry_threshold": 0.02,
            "exit_threshold": 0.01,
            "position_size": 0.1,
            "spread": 0.05,
            "inventory_limit": 1000,
            "risk_aversion": 0.1,
        },
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        status=TaskStatus.PENDING,
    )


@pytest.fixture
def sample_calibration_params():
    """示例校准参数"""
    return CalibrationParams(
        param_id="cal_123",
        symbol="AAPL",
        scenario=ScenarioType.NORMAL,
        base_slippage=0.001,
        volatility_factor=1.2,
        liquidity_factor=0.8,
        calibrated_at=datetime.now(),
        is_active=True,
    )


class TestDatabaseManager:
    """数据库管理器测试类"""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_db_config):
        """测试数据库管理器初始化"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 验证表创建
            mock_connect.assert_called()

    @pytest.mark.asyncio
    async def test_get_connection(self, mock_db_config):
        """测试获取数据库连接"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_connect.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 获取连接
            async with db_manager.get_connection() as conn:
                assert conn is not None

    @pytest.mark.asyncio
    async def test_close_connections(self, mock_db_config):
        """测试关闭数据库连接"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_connect.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 测试连接上下文管理器
            async with db_manager.get_connection() as conn:
                assert conn is not None

    @pytest.mark.asyncio
    async def test_execute_query(self, mock_db_config):
        """测试执行查询"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_conn.execute.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [(1, "test")]
            
            # 设置async context manager
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_connect.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 执行查询
            result = await db_manager.execute_query("SELECT * FROM test")

            assert result == [(1, "test")]
            mock_conn.execute.assert_called_once_with("SELECT * FROM test", ())

    @pytest.mark.asyncio
    async def test_execute_query_with_error(self, mock_db_config):
        """测试查询执行错误处理"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = sqlite3.Error("Database error")
            
            # 设置async context manager
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_connect.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 执行查询并捕获异常
            with pytest.raises(DatabaseError):
                await db_manager.execute_query("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_execute_transaction(self, mock_db_config):
        """测试事务执行"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            
            # 设置async context manager
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_connect.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 执行事务
            queries = [
                "INSERT INTO test (name) VALUES ('test1')",
                "INSERT INTO test (name) VALUES ('test2')",
            ]
            await db_manager.execute_transaction(queries)

            # 验证事务执行
            assert mock_conn.execute.call_count == len(queries) + 1  # +1 for BEGIN
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_transaction_with_error(self, mock_db_config):
        """测试事务执行错误处理"""
        with patch("src.core.database.aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = sqlite3.Error("Database error")
            
            # 设置async context manager
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_connect.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager(mock_db_config["db_path"])
            await db_manager.init_database()

            # 执行事务并捕获异常
            queries = ["INSERT INTO test (name) VALUES ('test1')"]
            with pytest.raises(DatabaseError):
                await db_manager.execute_transaction(queries)

            # 验证回滚
            mock_conn.rollback.assert_called_once()


class TestSimulationTaskOperations:
    """仿真任务操作测试类"""

    @pytest.mark.asyncio
    async def test_save_simulation_task(self, sample_simulation_task):
        """测试保存仿真任务"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存任务
        await db_manager.save_simulation_task(sample_simulation_task)

        # 验证任务已保存
        tasks = await db_manager.get_simulation_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == sample_simulation_task.task_id

    @pytest.mark.asyncio
    async def test_get_simulation_task_by_id(self, sample_simulation_task):
        """测试根据ID获取仿真任务"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存任务
        await db_manager.save_simulation_task(sample_simulation_task)

        # 获取任务
        task = await db_manager.get_simulation_task_by_id(sample_simulation_task.task_id)
        assert task is not None
        assert task.task_id == sample_simulation_task.task_id
        assert task.symbol == sample_simulation_task.symbol

    @pytest.mark.asyncio
    async def test_update_simulation_task_status(self, sample_simulation_task):
        """测试更新仿真任务状态"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存任务
        await db_manager.save_simulation_task(sample_simulation_task)

        # 更新状态
        await db_manager.update_simulation_task_status(
            sample_simulation_task.task_id, TaskStatus.RUNNING
        )

        # 验证状态已更新
        task = await db_manager.get_simulation_task_by_id(sample_simulation_task.task_id)
        assert task.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_delete_simulation_task(self, sample_simulation_task):
        """测试删除仿真任务"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存任务
        await db_manager.save_simulation_task(sample_simulation_task)

        # 删除任务
        await db_manager.delete_simulation_task(sample_simulation_task.task_id)

        # 验证任务已删除
        task = await db_manager.get_simulation_task_by_id(sample_simulation_task.task_id)
        assert task is None


class TestCalibrationParamsOperations:
    """校准参数操作测试类"""

    @pytest.mark.asyncio
    async def test_save_calibration_params(self, sample_calibration_params):
        """测试保存校准参数"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存参数
        await db_manager.save_calibration_params(sample_calibration_params)

        # 验证参数已保存
        params = await db_manager.get_calibration_params()
        assert len(params) == 1
        assert params[0].param_id == sample_calibration_params.param_id

    @pytest.mark.asyncio
    async def test_get_calibration_params_by_symbol(self, sample_calibration_params):
        """测试根据交易品种获取校准参数"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存参数
        await db_manager.save_calibration_params(sample_calibration_params)

        # 获取参数
        params = await db_manager.get_calibration_params_by_symbol(
            sample_calibration_params.symbol
        )
        assert len(params) == 1
        assert params[0].symbol == sample_calibration_params.symbol

    @pytest.mark.asyncio
    async def test_update_calibration_params(self, sample_calibration_params):
        """测试更新校准参数"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存参数
        await db_manager.save_calibration_params(sample_calibration_params)

        # 更新参数
        sample_calibration_params.base_slippage = 0.002
        await db_manager.update_calibration_params(sample_calibration_params)

        # 验证参数已更新
        params = await db_manager.get_calibration_params_by_symbol(
            sample_calibration_params.symbol
        )
        assert params[0].base_slippage == 0.002

    @pytest.mark.asyncio
    async def test_delete_calibration_params(self, sample_calibration_params):
        """测试删除校准参数"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 保存参数
        await db_manager.save_calibration_params(sample_calibration_params)

        # 删除参数
        await db_manager.delete_calibration_params(sample_calibration_params.param_id)

        # 验证参数已删除
        params = await db_manager.get_calibration_params()
        assert len(params) == 0


class TestDatabaseIntegration:
    """数据库集成测试类"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, sample_simulation_task, sample_calibration_params):
        """测试完整工作流程"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 1. 保存校准参数
        await db_manager.save_calibration_params(sample_calibration_params)

        # 2. 保存仿真任务
        await db_manager.save_simulation_task(sample_simulation_task)

        # 3. 更新任务状态
        await db_manager.update_simulation_task_status(
            sample_simulation_task.task_id, TaskStatus.RUNNING
        )

        # 4. 验证数据一致性
        task = await db_manager.get_simulation_task_by_id(sample_simulation_task.task_id)
        params = await db_manager.get_calibration_params_by_symbol(
            sample_calibration_params.symbol
        )

        assert task.status == TaskStatus.RUNNING
        assert len(params) == 1
        assert params[0].symbol == task.symbol

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, sample_simulation_task):
        """测试并发操作"""
        db_manager = DatabaseManager(":memory:")
        await db_manager.init_database()

        # 创建多个任务
        tasks = []
        for i in range(5):
            task = SimulationTask(
                task_id=f"sim_{i}",
                symbol="AAPL",
                period="1d",
                scenario=ScenarioType.NORMAL,
                strategy_params={
                    "entry_threshold": 0.02,
                    "exit_threshold": 0.01,
                    "position_size": 0.1,
                },
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
                status=TaskStatus.PENDING,
            )
            tasks.append(task)

        # 并发保存任务
        import asyncio
        await asyncio.gather(*[db_manager.save_simulation_task(task) for task in tasks])

        # 验证所有任务已保存
        saved_tasks = await db_manager.get_simulation_tasks()
        assert len(saved_tasks) == 5
