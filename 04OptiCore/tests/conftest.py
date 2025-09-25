#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置文件
NeuroTrade Nexus (NTN) - Test Configuration

提供所有测试的共享fixtures和配置

核心功能：
1. 测试环境配置
2. 数据库测试fixtures
3. 缓存测试fixtures
4. 模拟数据生成
5. 异步测试支持
6. 测试隔离和清理

遵循NeuroTrade Nexus核心设计理念：
- 环境隔离：测试环境独立配置
- 数据隔离：每个测试使用独立数据
- 可重复性：测试结果可重现
- 清理机制：测试后自动清理资源
"""

import asyncio
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
import redis

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from config.config import Config
from config.settings import get_settings
from optimizer.backtester.engine import BacktestEngine
from optimizer.communication.message_handler import (
    MessageHandler,
    MessagePriority,
    MessageType,
)
from optimizer.communication.zmq_client import ZMQClient
from optimizer.decision.engine import DecisionEngine
from optimizer.optimization.genetic_optimizer import GeneticOptimizer
from optimizer.risk.manager import RiskManager
from optimizer.utils.data_validator import DataValidator

# 设置测试环境
os.environ["NTN_ENVIRONMENT"] = "test"
os.environ["TESTING"] = "1"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """测试配置fixture"""
    return {
        "environment": "test",
        "debug": True,
        "testing": True,
        "database": {"path": ":memory:", "echo": False},  # 使用内存数据库
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 15,  # 使用专用测试数据库
            "decode_responses": True,
        },
        "zmq": {"subscriber_port": 5555, "publisher_port": 5556, "timeout": 1000},
        "backtest": {"max_concurrent": 2, "timeout": 30, "cache_size": 100},
        "optimization": {
            "population_size": 20,
            "generations": 10,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "timeout": 60,
        },
        "risk": {
            "max_position_size": 0.1,
            "max_daily_loss": 0.02,
            "max_drawdown": 0.15,
            "min_confidence": 0.6,
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    }


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """临时目录fixture"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_database(temp_dir: Path) -> Generator[str, None, None]:
    """测试数据库fixture"""
    db_path = temp_dir / "test.db"

    # 创建测试数据库
    conn = sqlite3.connect(str(db_path))

    # 创建测试表
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            parameters TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS backtest_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            symbol TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            initial_capital REAL NOT NULL,
            final_capital REAL NOT NULL,
            total_return REAL NOT NULL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            win_rate REAL,
            profit_factor REAL,
            total_trades INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies (id)
        );
        
        CREATE TABLE IF NOT EXISTS optimization_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            symbol TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            parameter_ranges TEXT NOT NULL,
            optimization_target TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            progress REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies (id)
        );
        
        CREATE TABLE IF NOT EXISTS optimization_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            generation INTEGER NOT NULL,
            individual_id INTEGER NOT NULL,
            parameters TEXT NOT NULL,
            fitness_score REAL NOT NULL,
            metrics TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES optimization_tasks (id)
        );
        
        CREATE TABLE IF NOT EXISTS strategy_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            symbol TEXT NOT NULL,
            parameters TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            risk_score REAL NOT NULL,
            expected_return REAL,
            max_drawdown REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies (id)
        );
        
        -- 插入测试数据
        INSERT INTO strategies (name, description, parameters) VALUES 
        ('MA_Cross', '移动平均交叉策略', '{"fast_period": 10, "slow_period": 20}'),
        ('RSI_Mean_Reversion', 'RSI均值回归策略', '{"rsi_period": 14, "oversold": 30, "overbought": 70}'),
        ('Bollinger_Bands', '布林带策略', '{"period": 20, "std_dev": 2}');
    """
    )

    conn.commit()
    conn.close()

    yield str(db_path)

    # 清理
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_redis():
    """测试Redis连接fixture"""
    try:
        r = redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
        r.ping()  # 测试连接

        # 清理测试数据库
        r.flushdb()

        yield r

        # 测试后清理
        r.flushdb()
        r.close()
    except redis.ConnectionError:
        # Redis不可用时使用模拟对象
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.flushdb.return_value = True
        yield mock_redis


@pytest.fixture
def sample_market_data() -> pd.DataFrame:
    """生成样本市场数据"""
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
    np.random.seed(42)  # 确保可重现性

    # 生成模拟价格数据
    initial_price = 100.0
    returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
    prices = [initial_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    # 生成OHLCV数据
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i - 1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000000, 10000000)

        data.append(
            {
                "timestamp": date,
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close_price, 2),
                "volume": volume,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def sample_strategy_parameters() -> Dict[str, Any]:
    """样本策略参数"""
    return {
        "ma_cross": {"fast_period": 10, "slow_period": 20, "signal_threshold": 0.01},
        "rsi_mean_reversion": {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "exit_threshold": 50,
        },
        "bollinger_bands": {"period": 20, "std_dev": 2, "entry_threshold": 0.02},
    }


@pytest.fixture
def mock_zmq_client():
    """模拟ZMQ客户端"""
    mock_client = Mock(spec=ZMQClient)
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.disconnect = AsyncMock(return_value=True)
    mock_client.subscribe = AsyncMock(return_value=True)
    mock_client.publish = AsyncMock(return_value=True)
    mock_client.is_connected = True
    mock_client.get_stats = Mock(
        return_value={
            "messages_received": 0,
            "messages_sent": 0,
            "connection_status": "connected",
        }
    )
    return mock_client


@pytest.fixture
async def backtest_engine(
    test_config: Dict[str, Any], test_database: str
) -> AsyncGenerator[BacktestEngine, None]:
    """回测引擎fixture"""
    config = test_config.copy()
    config["database"]["path"] = test_database

    engine = BacktestEngine(config)
    await engine.initialize()

    yield engine

    await engine.cleanup()


@pytest.fixture
async def genetic_optimizer(
    test_config: Dict[str, Any]
) -> AsyncGenerator[GeneticOptimizer, None]:
    """遗传算法优化器fixture"""
    optimizer = GeneticOptimizer(test_config["optimization"])
    await optimizer.initialize()

    yield optimizer

    await optimizer.cleanup()


@pytest.fixture
async def decision_engine(
    test_config: Dict[str, Any], test_database: str
) -> AsyncGenerator[DecisionEngine, None]:
    """决策引擎fixture"""
    config = test_config.copy()
    config["database"]["path"] = test_database

    engine = DecisionEngine(config)
    await engine.initialize()

    yield engine

    await engine.cleanup()


@pytest.fixture
async def message_handler(
    test_config: Dict[str, Any]
) -> AsyncGenerator[MessageHandler, None]:
    """消息处理器fixture"""
    handler = MessageHandler(test_config)
    await handler.start()

    yield handler

    await handler.cleanup()


@pytest.fixture
async def risk_manager(
    test_config: Dict[str, Any]
) -> AsyncGenerator[RiskManager, None]:
    """风险管理器fixture"""
    manager = RiskManager(test_config["risk"])
    await manager.initialize()

    yield manager

    await manager.cleanup()


@pytest.fixture
def data_validator(test_config: Dict[str, Any]) -> DataValidator:
    """数据验证器fixture"""
    return DataValidator(test_config)


@pytest.fixture
def sample_trading_opportunity() -> Dict[str, Any]:
    """样本交易机会数据"""
    return {
        "symbol": "BTCUSDT",
        "strategy": "MA_Cross",
        "signal": "BUY",
        "confidence": 0.85,
        "price": 45000.0,
        "timestamp": datetime.now().isoformat(),
        "metadata": {"fast_ma": 44800.0, "slow_ma": 44500.0, "volume": 1500000},
    }


@pytest.fixture
def sample_strategy_package() -> Dict[str, Any]:
    """样本策略包数据"""
    return {
        "strategy_id": 1,
        "symbol": "BTCUSDT",
        "parameters": {"fast_period": 10, "slow_period": 20, "signal_threshold": 0.01},
        "confidence_score": 0.85,
        "risk_score": 0.3,
        "expected_return": 0.15,
        "max_drawdown": 0.08,
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_external_apis():
    """模拟外部API"""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": {}}

        mock_get.return_value = mock_response
        mock_post.return_value = mock_response

        yield {"get": mock_get, "post": mock_post, "response": mock_response}


@pytest.fixture(autouse=True)
def setup_test_environment(test_config: Dict[str, Any]):
    """自动设置测试环境"""
    # 设置环境变量
    original_env = os.environ.copy()

    os.environ.update(
        {
            "NTN_ENVIRONMENT": "test",
            "TESTING": "1",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_PATH": ":memory:",
            "REDIS_DB": "15",
        }
    )

    yield

    # 恢复原始环境变量
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def performance_monitor():
    """性能监控fixture"""
    import threading
    import time

    import psutil

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.start_memory = None
            self.end_memory = None
            self.peak_memory = None
            self.monitoring = False
            self.monitor_thread = None

        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss
            self.peak_memory = self.start_memory
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_memory)
            self.monitor_thread.start()

        def stop(self):
            self.end_time = time.time()
            self.end_memory = psutil.Process().memory_info().rss
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()

        def _monitor_memory(self):
            while self.monitoring:
                current_memory = psutil.Process().memory_info().rss
                self.peak_memory = max(self.peak_memory, current_memory)
                time.sleep(0.1)

        def get_stats(self):
            return {
                "duration": self.end_time - self.start_time if self.end_time else None,
                "memory_start": self.start_memory,
                "memory_end": self.end_memory,
                "memory_peak": self.peak_memory,
                "memory_delta": self.end_memory - self.start_memory
                if self.end_memory
                else None,
            }

    return PerformanceMonitor()


# 测试标记
pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


# 测试钩子函数
def pytest_configure(config):
    """Pytest配置钩子"""
    # 创建测试日志目录
    log_dir = Path("tests/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 设置测试标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为慢速测试添加标记
    slow_marker = pytest.mark.slow
    for item in items:
        if (
            "slow" in item.nodeid
            or "stress" in item.nodeid
            or "performance" in item.nodeid
        ):
            item.add_marker(slow_marker)


def pytest_runtest_setup(item):
    """测试运行前设置"""
    # 跳过需要外部依赖的测试（如果依赖不可用）
    if "redis" in item.fixturenames:
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=15)
            r.ping()
        except (ImportError, redis.ConnectionError):
            pytest.skip("Redis not available")

    if "real" in item.keywords:
        if os.environ.get("NTN_ENVIRONMENT") != "test":
            pytest.skip("Real environment tests only run in test environment")


def pytest_runtest_teardown(item, nextitem):
    """测试运行后清理"""
    # 清理异步任务
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                if not task.done():
                    task.cancel()
    except RuntimeError:
        pass  # 没有事件循环


# 自定义断言
def assert_performance(
    duration: float, max_duration: float, memory_delta: int, max_memory_delta: int
):
    """性能断言"""
    assert duration <= max_duration, f"执行时间 {duration:.2f}s 超过限制 {max_duration}s"
    assert (
        memory_delta <= max_memory_delta
    ), f"内存增长 {memory_delta} bytes 超过限制 {max_memory_delta} bytes"


def assert_data_quality(
    data: pd.DataFrame, min_rows: int = 1, required_columns: list = None
):
    """数据质量断言"""
    assert len(data) >= min_rows, f"数据行数 {len(data)} 少于最小要求 {min_rows}"

    if required_columns:
        missing_columns = set(required_columns) - set(data.columns)
        assert not missing_columns, f"缺少必需列: {missing_columns}"

    # 检查空值
    null_counts = data.isnull().sum()
    assert null_counts.sum() == 0, f"数据包含空值: {null_counts[null_counts > 0].to_dict()}"


def assert_strategy_performance(
    metrics: Dict[str, float], min_sharpe: float = 0.5, max_drawdown: float = 0.2
):
    """策略性能断言"""
    assert (
        metrics.get("sharpe_ratio", 0) >= min_sharpe
    ), f"夏普比率 {metrics.get('sharpe_ratio')} 低于最小要求 {min_sharpe}"
    assert (
        metrics.get("max_drawdown", 1) <= max_drawdown
    ), f"最大回撤 {metrics.get('max_drawdown')} 超过最大限制 {max_drawdown}"
    assert metrics.get("total_return", -1) > 0, f"总收益率 {metrics.get('total_return')} 为负"
