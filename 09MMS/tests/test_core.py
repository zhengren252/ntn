#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 核心模块测试
测试核心功能模块

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.config import Settings, get_settings
from src.core.database import DatabaseManager
from src.core.simulation_engine import SimulationEngine
from src.core.cache import RedisCache, SimulationCache
from src.models.simulation import SimulationTask, TaskStatus, ScenarioType


class TestConfig:
    """配置模块测试"""

    def test_config_initialization(self, mock_config):
        """测试配置初始化"""
        assert mock_config.APP_ENV == "development"
        assert mock_config.LOG_LEVEL == "DEBUG"
        assert mock_config.DATABASE_URL == ":memory:"

    def test_get_settings(self, mock_config):
        """测试获取设置"""
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "APP_ENV")

    def test_database_config(self, mock_config):
        """测试数据库配置"""
        # Settings类没有get_database_config方法，直接测试属性
        assert mock_config.DATABASE_URL == ":memory:"
        assert hasattr(mock_config, "DATABASE_ECHO")

    def test_redis_config(self, mock_config):
        """测试Redis配置"""
        redis_config = mock_config.get_redis_config()
        assert isinstance(redis_config, dict)
        assert "url" in redis_config
        assert "db" in redis_config
        assert "password" in redis_config
        assert "max_connections" in redis_config
        assert "decode_responses" in redis_config
        assert redis_config["decode_responses"] is True

    def test_zmq_config(self, mock_config):
        """测试ZMQ配置"""
        zmq_config = mock_config.get_zmq_config()
        assert isinstance(zmq_config, dict)
        assert "frontend_port" in zmq_config
        assert "backend_port" in zmq_config
        assert zmq_config["frontend_port"] == 5555
        assert zmq_config["backend_port"] == 5556


class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """测试数据库初始化"""
        db = DatabaseManager(":memory:")
        await db.init_database()

        # 检查表是否创建
        tables = await db.get_table_names()
        expected_tables = [
            "simulation_tasks",
            "simulation_results",
            "market_data",
            "calibration_params",
        ]

        for table in expected_tables:
            assert table in tables

        await db.close()

    @pytest.mark.asyncio
    async def test_save_simulation_task(self, mock_database, sample_simulation_task):
        """测试保存仿真任务"""
        result = await mock_database.save_simulation_task(sample_simulation_task)
        assert result is True

        # 验证任务是否保存
        saved_task = await mock_database.get_simulation_task(sample_simulation_task.task_id)
        assert saved_task is not None
        assert saved_task["symbol"] == sample_simulation_task.symbol

    @pytest.mark.asyncio
    async def test_update_task_status(self, mock_database):
        """测试更新任务状态"""
        # 首先创建一个任务
        task = SimulationTask(
            task_id="test_task_002",
            symbol="AAPL",
            period="30d",
            scenario=ScenarioType.NORMAL,
            strategy_params={
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1
            },
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 31),
            status=TaskStatus.PENDING,
        )

        await mock_database.save_simulation_task(task)

        # 更新状态
        await mock_database.update_task_status("test_task_002", TaskStatus.RUNNING)

        # 验证状态更新
        updated_task = await mock_database.get_simulation_task("test_task_002")
        assert updated_task["status"] == TaskStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_get_calibration_params(
        self, mock_database, sample_calibration_params
    ):
        """测试获取校准参数"""
        # 插入校准参数
        params_dict = {
            "base_slippage": sample_calibration_params.base_slippage,
            "volatility_factor": sample_calibration_params.volatility_factor,
            "liquidity_factor": sample_calibration_params.liquidity_factor,
        }
        await mock_database.save_calibration_params(
            sample_calibration_params.symbol,
            sample_calibration_params.scenario,
            params_dict,
        )

        # 获取校准参数
        params = await mock_database.get_calibration_params(
            sample_calibration_params.symbol,
            sample_calibration_params.scenario,
        )

        assert params is not None
        assert params.symbol == sample_calibration_params.symbol

    @pytest.mark.asyncio
    async def test_get_task_statistics(self, mock_database):
        """测试获取任务统计"""
        stats = await mock_database.get_task_statistics()

        assert isinstance(stats, dict)
        assert "total_tasks" in stats
        assert "completed_tasks" in stats
        assert "failed_tasks" in stats
        assert "pending_tasks" in stats


class TestSimulationEngine:
    """仿真引擎测试"""

    @pytest.mark.asyncio
    async def test_engine_initialization(self, mock_database):
        """测试引擎初始化"""
        engine = SimulationEngine(mock_database)
        assert engine.db == mock_database
        assert engine.max_concurrent_tasks > 0

    @pytest.mark.asyncio
    async def test_execute_simulation(self, mock_database, sample_simulation_request):
        """测试执行仿真"""
        engine = SimulationEngine(mock_database)

        # 模拟市场数据生成
        with patch.object(engine, "_generate_market_data") as mock_generate:
            mock_generate.return_value = [
                {"timestamp": datetime.now(), "price": 150.0, "volume": 1000}
            ]

            result = await engine.execute_simulation(sample_simulation_request)

            assert "simulation_id" in result
            assert "results" in result
            assert "execution_time" in result
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_market_making_strategy(self, mock_database):
        """测试做市商策略"""
        engine = SimulationEngine(mock_database)

        market_data = [
            {
                "timestamp": datetime.now(),
                "price": 150.0,
                "volume": 1000,
                "bid": 149.95,
                "ask": 150.05,
            }
        ]

        params = {"spread": 0.01, "inventory_limit": 1000}

        result = await engine._simulate_market_making(market_data, params)

        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "win_rate" in result

    @pytest.mark.asyncio
    async def test_arbitrage_strategy(self, mock_database):
        """测试套利策略"""
        engine = SimulationEngine(mock_database)

        market_data = [{"timestamp": datetime.now(), "price": 150.0, "volume": 1000}]

        params = {"threshold": 0.005, "max_position": 1000}

        result = await engine._simulate_arbitrage(market_data, params)

        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "win_rate" in result

    @pytest.mark.asyncio
    async def test_get_task_status(self, mock_database):
        """测试获取任务状态"""
        engine = SimulationEngine(mock_database)

        # 测试不存在的任务
        status = await engine.get_task_status("nonexistent_task")
        assert status is None

    @pytest.mark.asyncio
    async def test_cancel_task(self, mock_database):
        """测试取消任务"""
        engine = SimulationEngine(mock_database)

        # 测试取消不存在的任务
        result = await engine.cancel_task("nonexistent_task")
        assert result is False


class TestRedisCache:
    """Redis缓存测试"""

    @pytest.mark.asyncio
    async def test_cache_initialization(self, mock_redis):
        """测试缓存初始化"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis

            cache = RedisCache()
            await cache.connect()

            assert cache.connected is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_and_get(self, mock_redis):
        """测试设置和获取缓存"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis
            mock_redis.get.return_value = '{"test": "value"}'

            cache = RedisCache()
            cache.redis_client = mock_redis
            cache.connected = True

            # 测试设置
            result = await cache.set("test_key", {"test": "value"})
            assert result is True

            # 测试获取
            value = await cache.get("test_key")
            assert value == {"test": "value"}

    @pytest.mark.asyncio
    async def test_delete(self, mock_redis):
        """测试删除缓存"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis
            mock_redis.delete.return_value = 1

            cache = RedisCache()
            cache.redis_client = mock_redis
            cache.connected = True

            result = await cache.delete("test_key")
            assert result is True

    @pytest.mark.asyncio
    async def test_exists(self, mock_redis):
        """测试检查缓存存在性"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis
            mock_redis.exists.return_value = 1

            cache = RedisCache()
            cache.redis_client = mock_redis
            cache.connected = True

            result = await cache.exists("test_key")
            assert result is True


class TestSimulationCache:
    """仿真缓存测试"""

    @pytest.mark.asyncio
    async def test_cache_simulation_result(self, mock_redis):
        """测试缓存仿真结果"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis

            redis_cache = RedisCache()
            redis_cache.redis_client = mock_redis
            redis_cache.connected = True

            sim_cache = SimulationCache(redis_cache)

            result = {"total_return": 0.05, "sharpe_ratio": 1.2}

            success = await sim_cache.cache_simulation_result("test_task", result)
            assert success is True

    @pytest.mark.asyncio
    async def test_get_simulation_result(self, mock_redis):
        """测试获取缓存的仿真结果"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis
            mock_redis.get.return_value = {
                "result": {"total_return": 0.05},
                "task_id": "test_task",
            }

            redis_cache = RedisCache()
            redis_cache.redis_client = mock_redis
            redis_cache.connected = True

            sim_cache = SimulationCache(redis_cache)

            result = await sim_cache.get_simulation_result("test_task")
            assert result is not None

    @pytest.mark.asyncio
    async def test_cache_market_data(self, mock_redis, sample_market_data):
        """测试缓存市场数据"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis

            redis_cache = RedisCache()
            redis_cache.redis_client = mock_redis
            redis_cache.connected = True

            sim_cache = SimulationCache(redis_cache)

            success = await sim_cache.cache_market_data(
                "AAPL", "1min", sample_market_data
            )
            assert success is True

    @pytest.mark.asyncio
    async def test_increment_task_counter(self, mock_redis):
        """测试递增任务计数器"""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis
            mock_redis.incrby.return_value = 5

            redis_cache = RedisCache()
            redis_cache.redis_client = mock_redis
            redis_cache.connected = True

            sim_cache = SimulationCache(redis_cache)

            count = await sim_cache.increment_task_counter("completed")
            assert count == 5


if __name__ == "__main__":
    pytest.main([__file__])
