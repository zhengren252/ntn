#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 测试配置
Pytest配置和共享fixtures

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# 设置测试环境变量
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_URL"] = ":memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest_asyncio.fixture(scope="session")
async def shared_test_database():
    """会话级别的共享测试数据库"""
    from src.core.database import DatabaseManager
    
    # 创建数据库管理器实例，确保使用内存数据库
    db_manager = DatabaseManager(":memory:")
    
    # 初始化数据库表结构
    await db_manager.init_database()
    
    yield db_manager
    
    # 清理
    await db_manager.close()


@pytest_asyncio.fixture
async def init_test_database(shared_test_database):
    """初始化测试数据库（使用共享数据库）"""
    # 返回共享的数据库实例
    return shared_test_database


@pytest.fixture
def mock_config():
    """模拟配置"""
    from src.core.config import Settings

    # 创建测试配置实例
    test_settings = Settings(
        APP_ENV="development",  # 使用允许的环境值
        LOG_LEVEL="DEBUG",
        DATABASE_URL=":memory:",
        REDIS_URL="redis://localhost:6379/15",  # 使用测试数据库
        FRONTEND_PORT=5555,
        BACKEND_PORT=5556,
        CACHE_TTL=300,
        DEBUG=True
    )

    yield test_settings


@pytest_asyncio.fixture
async def real_database(init_test_database):
    """真实数据库实例（用于集成测试）"""
    return init_test_database


@pytest.fixture
def mock_database():
    """模拟数据库"""
    from src.core.database import DatabaseManager

    db = AsyncMock(spec=DatabaseManager)
    db.init_database.return_value = None
    db.close.return_value = None
    db.save_simulation_task.return_value = True
    db.get_simulation_task.return_value = {"symbol": "AAPL", "status": "pending"}
    db.update_task_status.return_value = True
    db.get_calibration_params.return_value = None
    db.get_task_statistics.return_value = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "pending_tasks": 0
    }
    db.get_table_names.return_value = [
        "simulation_tasks",
        "simulation_results", 
        "market_data",
        "calibration_params"
    ]

    return db


@pytest.fixture
def mock_redis():
    """模拟Redis"""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True  # 添加setex方法
    mock_redis.get.return_value = None
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    mock_redis.ttl.return_value = -1
    mock_redis.keys.return_value = []
    mock_redis.incrby.return_value = 1
    mock_redis.decrby.return_value = 0

    return mock_redis


@pytest.fixture
def mock_zmq_socket():
    """模拟ZMQ套接字"""
    mock_socket = MagicMock()
    mock_socket.bind.return_value = None
    mock_socket.connect.return_value = None
    mock_socket.send_json.return_value = None
    mock_socket.recv_json.return_value = {}
    mock_socket.send_string.return_value = None
    mock_socket.recv_string.return_value = ""
    mock_socket.close.return_value = None

    return mock_socket


@pytest.fixture
def mock_simulation_engine():
    """模拟仿真引擎"""
    from src.core.simulation_engine import SimulationEngine

    engine = AsyncMock(spec=SimulationEngine)
    engine.execute_simulation.return_value = {
        "simulation_id": "test_sim_001",
        "status": "completed",
        "results": {
            "total_return": 0.05,
            "sharpe_ratio": 1.2,
            "max_drawdown": 0.02,
            "win_rate": 0.65,
        },
        "execution_time": 1.5,
    }

    return engine


@pytest.fixture
def sample_simulation_request():
    """示例仿真请求"""
    from src.models.simulation import SimulationRequest, ScenarioType
    
    return SimulationRequest(
        symbol="AAPL",
        period="30d",
        scenario=ScenarioType.NORMAL,
        strategy_params={
            "entry_threshold": 0.02,
            "exit_threshold": 0.01,
            "position_size": 0.1,
            "spread": 0.01,
            "inventory_limit": 1000,
            "risk_aversion": 0.5
        },
        start_time="2024-01-01T00:00:00",
        end_time="2024-01-31T23:59:59"
    )


@pytest.fixture
def sample_simulation_task():
    """示例仿真任务"""
    from src.models.simulation import SimulationTask, ScenarioType, TaskStatus
    from datetime import datetime
    
    return SimulationTask(
        task_id="test_task_001",
        symbol="AAPL",
        period="30d",
        scenario=ScenarioType.NORMAL,
        strategy_params={
            "entry_threshold": 0.02,
            "exit_threshold": 0.01,
            "position_size": 0.1,
            "spread": 0.01,
            "inventory_limit": 1000,
            "risk_aversion": 0.5
        },
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        status=TaskStatus.PENDING
    )


@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return [
        {
            "timestamp": "2024-01-01T09:30:00",
            "symbol": "AAPL",
            "price": 150.0,
            "volume": 1000,
            "bid": 149.95,
            "ask": 150.05,
        },
        {
            "timestamp": "2024-01-01T09:31:00",
            "symbol": "AAPL",
            "price": 150.1,
            "volume": 1500,
            "bid": 150.05,
            "ask": 150.15,
        },
    ]


@pytest.fixture
def sample_calibration_params():
    """示例校准参数"""
    from src.models.simulation import CalibrationParams, ScenarioType
    from datetime import datetime
    
    return CalibrationParams(
        param_id="test_param_001",
        symbol="AAPL",
        scenario=ScenarioType.NORMAL,
        base_slippage=0.001,
        volatility_factor=1.2,
        liquidity_factor=0.8,
        calibrated_at=datetime(2024, 1, 1),
        is_active=True
    )


@pytest.fixture
async def mock_metrics_collector():
    """模拟指标收集器"""
    from src.utils.metrics import MetricsCollector

    collector = AsyncMock(spec=MetricsCollector)
    collector.record_counter.return_value = None
    collector.record_gauge.return_value = None
    collector.record_histogram.return_value = None
    collector.record_timer.return_value = None
    collector.get_all_metrics.return_value = {
        "counters": {},
        "gauges": {},
        "histograms": {},
        "timers": {},
        "summaries": {},
    }

    return collector


@pytest.fixture
def mock_logger():
    """模拟日志器"""
    logger = MagicMock()
    logger.info.return_value = None
    logger.warning.return_value = None
    logger.error.return_value = None
    logger.debug.return_value = None

    return logger


# 测试标记
pytest_plugins = []


def pytest_configure(config):
    """Pytest配置"""
    config.addinivalue_line("markers", "unit: 标记为单元测试")
    config.addinivalue_line("markers", "integration: 标记为集成测试")
    config.addinivalue_line("markers", "slow: 标记为慢速测试")
    config.addinivalue_line("markers", "redis: 需要Redis的测试")
    config.addinivalue_line("markers", "database: 需要数据库的测试")


def pytest_collection_modifyitems(config, items):
    """修改测试项目"""
    # 为没有标记的测试添加unit标记
    for item in items:
        if not any(
            mark.name in ["unit", "integration"] for mark in item.iter_markers()
        ):
            item.add_marker(pytest.mark.unit)
