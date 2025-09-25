#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工具模块
NeuroTrade Nexus (NTN) - Test Utilities

提供测试中常用的工具函数和辅助类

核心功能：
1. 数据生成工具
2. 性能测试工具
3. 模拟对象工具
4. 断言工具
5. 测试装饰器
6. 环境管理工具

遵循NeuroTrade Nexus核心设计理念：
- 可重用性：提供通用测试工具
- 一致性：统一的测试标准
- 可维护性：易于扩展和修改
- 隔离性：测试间相互独立
"""

import asyncio
import functools
import gzip
import logging
import pickle
import random
import shutil
import sqlite3
import string
import tempfile
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd

# 配置测试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# 测试装饰器
def async_test(func):
    """异步测试装饰器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(func(*args, **kwargs))
        finally:
            loop.close()

    return wrapper


def performance_test(max_time: float = 10.0, max_memory: int = 100 * 1024 * 1024):
    """性能测试装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            import psutil

            process = psutil.Process()
            start_time = time.time()
            start_memory = process.memory_info().rss

            try:
                result = func(*args, **kwargs)

                end_time = time.time()
                end_memory = process.memory_info().rss

                execution_time = end_time - start_time
                memory_usage = end_memory - start_memory

                if execution_time > max_time:
                    raise AssertionError(
                        f"测试执行时间超限: {execution_time:.2f}s > {max_time}s"
                    )

                if memory_usage > max_memory:
                    raise AssertionError(
                        f"测试内存使用超限: {memory_usage} bytes > {max_memory} bytes"
                    )

                logger.info(
                    f"性能测试通过 - 时间: {execution_time:.2f}s, 内存: {memory_usage} bytes"
                )
                return result

            except Exception as e:
                logger.error("性能测试失败: %s", e)
                raise

        return wrapper

    return decorator


@contextmanager
def temp_database(db_type: str = "sqlite"):
    """临时数据库上下文管理器"""
    if db_type == "sqlite":
        temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = temp_file.name
        temp_file.close()

        try:
            yield db_path
        finally:
            if Path(db_path).exists():
                Path(db_path).unlink()
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


@contextmanager
def mock_zmq_context():
    """模拟ZMQ上下文管理器"""
    mock_context = Mock()
    mock_socket = Mock()
    mock_context.socket.return_value = mock_socket

    yield mock_context, mock_socket


class TestDataType(Enum):
    """测试数据类型枚举"""

    MARKET_DATA = "market_data"
    STRATEGY_PARAMS = "strategy_params"
    BACKTEST_RESULTS = "backtest_results"
    OPTIMIZATION_RESULTS = "optimization_results"
    TRADING_SIGNALS = "trading_signals"
    RISK_METRICS = "risk_metrics"


@dataclass
class TestMetrics:
    """测试指标"""

    execution_time: float
    memory_usage: int
    cpu_usage: float
    success_rate: float
    error_count: int
    warning_count: int


class DataGenerator:
    """测试数据生成器"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)

    def generate_market_data(
        self,
        symbol: str = "BTCUSDT",
        start_date: str = "2023-01-01",
        end_date: str = "2023-12-31",
        frequency: str = "D",
        initial_price: float = 100.0,
        volatility: float = 0.02,
    ) -> pd.DataFrame:
        """
        生成模拟市场数据

        Args:
            symbol: 交易对符号
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率 (D=日, H=小时, T=分钟)
            initial_price: 初始价格
            volatility: 波动率

        Returns:
            pd.DataFrame: 市场数据
        """
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)

        # 生成价格序列（几何布朗运动）
        returns = np.random.normal(0.001, volatility, len(dates))
        prices = [initial_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        # 生成OHLCV数据
        data = []
        for i, (date, close_price) in enumerate(zip(dates, prices)):
            # 生成开盘价
            if i == 0:
                open_price = close_price
            else:
                open_price = prices[i - 1] * (1 + np.random.normal(0, volatility / 4))

            # 生成高低价
            high_factor = 1 + abs(np.random.normal(0, volatility / 2))
            low_factor = 1 - abs(np.random.normal(0, volatility / 2))

            high = max(open_price, close_price) * high_factor
            low = min(open_price, close_price) * low_factor

            # 生成成交量
            base_volume = 1000000
            volume_factor = np.random.lognormal(0, 0.5)
            volume = int(base_volume * volume_factor)

            data.append(
                {
                    "timestamp": date,
                    "symbol": symbol,
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close_price, 2),
                    "volume": volume,
                }
            )

        return pd.DataFrame(data)

    def generate_strategy_parameters(self, strategy_type: str) -> Dict[str, Any]:
        """
        生成策略参数

        Args:
            strategy_type: 策略类型

        Returns:
            Dict[str, Any]: 策略参数
        """
        if strategy_type == "ma_cross":
            return {
                "fast_period": random.randint(5, 15),
                "slow_period": random.randint(20, 50),
                "signal_threshold": round(random.uniform(0.001, 0.02), 4),
            }
        elif strategy_type == "rsi_mean_reversion":
            return {
                "rsi_period": random.randint(10, 20),
                "oversold": random.randint(20, 35),
                "overbought": random.randint(65, 80),
                "exit_threshold": random.randint(45, 55),
            }
        elif strategy_type == "bollinger_bands":
            return {
                "period": random.randint(15, 25),
                "std_dev": round(random.uniform(1.5, 2.5), 1),
                "entry_threshold": round(random.uniform(0.01, 0.03), 3),
            }
        else:
            return {
                "param1": random.uniform(0.1, 1.0),
                "param2": random.randint(1, 100),
                "param3": random.choice([True, False]),
            }

    def generate_backtest_results(
        self,
        strategy_name: str = "TestStrategy",
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
    ) -> Dict[str, Any]:
        """
        生成回测结果

        Args:
            strategy_name: 策略名称
            symbol: 交易对
            initial_capital: 初始资金

        Returns:
            Dict[str, Any]: 回测结果
        """
        # 生成随机但合理的回测指标
        total_return = random.uniform(-0.3, 0.8)  # -30% to 80%
        final_capital = initial_capital * (1 + total_return)

        sharpe_ratio = random.uniform(-1.0, 3.0)
        max_drawdown = random.uniform(0.05, 0.4)
        win_rate = random.uniform(0.3, 0.7)
        profit_factor = random.uniform(0.8, 2.5)
        total_trades = random.randint(50, 500)

        return {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return": round(total_return, 4),
            "sharpe_ratio": round(sharpe_ratio, 3),
            "max_drawdown": round(max_drawdown, 3),
            "win_rate": round(win_rate, 3),
            "profit_factor": round(profit_factor, 3),
            "total_trades": total_trades,
            "avg_trade_return": round(total_return / total_trades, 6),
            "volatility": round(random.uniform(0.1, 0.5), 3),
            "calmar_ratio": round(
                total_return / max_drawdown if max_drawdown > 0 else 0, 3
            ),
        }

    def generate_trading_signals(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        生成交易信号

        Args:
            count: 信号数量

        Returns:
            List[Dict[str, Any]]: 交易信号列表
        """
        signals = []
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
        strategies = ["MA_Cross", "RSI_Mean_Reversion", "Bollinger_Bands"]
        signal_types = ["BUY", "SELL", "HOLD"]

        for i in range(count):
            signal = {
                "id": i + 1,
                "timestamp": datetime.now()
                - timedelta(minutes=random.randint(0, 1440)),
                "symbol": random.choice(symbols),
                "strategy": random.choice(strategies),
                "signal_type": random.choice(signal_types),
                "confidence": round(random.uniform(0.5, 1.0), 3),
                "price": round(random.uniform(1000, 50000), 2),
                "volume": random.randint(100, 10000),
                "metadata": {
                    "indicator_value": round(random.uniform(0, 100), 2),
                    "trend": random.choice(["UP", "DOWN", "SIDEWAYS"]),
                    "volatility": round(random.uniform(0.1, 0.5), 3),
                },
            }
            signals.append(signal)

        return signals

    def generate_optimization_results(
        self, generations: int = 10, population_size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        生成优化结果

        Args:
            generations: 代数
            population_size: 种群大小

        Returns:
            List[Dict[str, Any]]: 优化结果列表
        """
        results = []

        for gen in range(generations):
            for ind in range(population_size):
                # 模拟适应度随代数提升
                base_fitness = random.uniform(0.1, 0.8)
                generation_bonus = gen * 0.02
                fitness = min(base_fitness + generation_bonus, 1.0)

                result = {
                    "generation": gen,
                    "individual_id": ind,
                    "parameters": self.generate_strategy_parameters("ma_cross"),
                    "fitness_score": round(fitness, 4),
                    "metrics": self.generate_backtest_results(),
                    "timestamp": datetime.now()
                    - timedelta(hours=random.randint(0, 24)),
                }
                results.append(result)

        return results


class MockFactory:
    """模拟对象工厂"""

    @staticmethod
    def create_mock_zmq_client() -> Mock:
        """创建模拟ZMQ客户端"""
        mock_client = Mock()
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock(return_value=True)
        mock_client.subscribe = AsyncMock(return_value=True)
        mock_client.publish = AsyncMock(return_value=True)
        mock_client.is_connected = True
        mock_client.get_stats = Mock(
            return_value={
                "messages_received": 100,
                "messages_sent": 50,
                "connection_status": "connected",
                "last_heartbeat": datetime.now().isoformat(),
            }
        )
        return mock_client

    @staticmethod
    def create_mock_database() -> Mock:
        """创建模拟数据库"""
        mock_db = Mock()
        mock_db.connect = AsyncMock(return_value=True)
        mock_db.disconnect = AsyncMock(return_value=True)
        mock_db.execute = AsyncMock(return_value=True)
        mock_db.fetch_one = AsyncMock(return_value={"id": 1, "name": "test"})
        mock_db.fetch_all = AsyncMock(return_value=[{"id": 1, "name": "test"}])
        mock_db.insert = AsyncMock(return_value=1)
        mock_db.update = AsyncMock(return_value=True)
        mock_db.delete = AsyncMock(return_value=True)
        return mock_db

    @staticmethod
    def create_mock_redis() -> Mock:
        """创建模拟Redis客户端"""
        mock_redis = Mock()
        mock_redis.ping = Mock(return_value=True)
        mock_redis.get = Mock(return_value=None)
        mock_redis.set = Mock(return_value=True)
        mock_redis.delete = Mock(return_value=1)
        mock_redis.exists = Mock(return_value=False)
        mock_redis.expire = Mock(return_value=True)
        mock_redis.flushdb = Mock(return_value=True)
        mock_redis.keys = Mock(return_value=[])
        return mock_redis

    @staticmethod
    def create_mock_backtest_engine() -> Mock:
        """创建模拟回测引擎"""
        mock_engine = Mock()
        mock_engine.initialize = AsyncMock(return_value=True)
        mock_engine.cleanup = AsyncMock(return_value=True)
        mock_engine.run_backtest = AsyncMock(
            return_value={
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08,
                "win_rate": 0.65,
            }
        )
        mock_engine.get_performance_metrics = AsyncMock(
            return_value={
                "total_trades": 100,
                "profit_factor": 1.5,
                "avg_trade_return": 0.0015,
            }
        )
        return mock_engine

    @staticmethod
    def create_mock_genetic_optimizer() -> Mock:
        """创建模拟遗传算法优化器"""
        mock_optimizer = Mock()
        mock_optimizer.initialize = AsyncMock(return_value=True)
        mock_optimizer.cleanup = AsyncMock(return_value=True)
        mock_optimizer.optimize = AsyncMock(
            return_value={
                "best_parameters": {"fast_period": 10, "slow_period": 20},
                "best_fitness": 0.85,
                "generations": 50,
                "convergence_generation": 35,
            }
        )
        mock_optimizer.get_population = AsyncMock(return_value=[])
        mock_optimizer.get_statistics = AsyncMock(
            return_value={
                "current_generation": 50,
                "best_fitness": 0.85,
                "average_fitness": 0.65,
                "diversity_score": 0.3,
            }
        )
        return mock_optimizer


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_snapshots = []
        self.cpu_snapshots = []

    def start(self):
        """开始性能监控"""
        import psutil

        self.start_time = time.time()
        self.memory_snapshots = [psutil.Process().memory_info().rss]
        self.cpu_snapshots = [psutil.cpu_percent()]

    def stop(self):
        """停止性能监控"""
        import psutil

        self.end_time = time.time()
        self.memory_snapshots.append(psutil.Process().memory_info().rss)
        self.cpu_snapshots.append(psutil.cpu_percent())

    def get_metrics(self) -> TestMetrics:
        """获取性能指标"""
        execution_time = self.end_time - self.start_time if self.end_time else 0
        memory_usage = max(self.memory_snapshots) - min(self.memory_snapshots)
        cpu_usage = sum(self.cpu_snapshots) / len(self.cpu_snapshots)

        return TestMetrics(
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            success_rate=1.0,  # 需要外部设置
            error_count=0,  # 需要外部设置
            warning_count=0,  # 需要外部设置
        )


# 测试装饰器
def timeout(seconds: int):
    """超时装饰器"""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(
                    f"Function {func.__name__} timed out after {seconds} seconds"
                )

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # 取消超时
                return result
            except TimeoutError:
                raise
            finally:
                signal.alarm(0)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def performance_test(max_time: float = 1.0, max_memory: int = 100 * 1024 * 1024):
    """性能测试装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = PerformanceProfiler()
            profiler.start()

            try:
                result = func(*args, **kwargs)
                profiler.stop()

                metrics = profiler.get_metrics()

                # 检查性能指标
                assert (
                    metrics.execution_time <= max_time
                ), f"执行时间 {metrics.execution_time:.2f}s 超过限制 {max_time}s"
                assert (
                    metrics.memory_usage <= max_memory
                ), f"内存使用 {metrics.memory_usage} bytes 超过限制 {max_memory} bytes"

                return result

            except Exception as e:
                profiler.stop()
                raise e

        return wrapper

    return decorator


# 上下文管理器
@contextmanager
def temporary_directory() -> Generator[Path, None, None]:
    """临时目录上下文管理器"""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@contextmanager
def temporary_database() -> Generator[str, None, None]:
    """临时数据库上下文管理器"""
    with temporary_directory() as temp_dir:
        db_path = temp_dir / "test.db"

        # 创建数据库
        conn = sqlite3.connect(str(db_path))
        conn.close()

        try:
            yield str(db_path)
        finally:
            if db_path.exists():
                db_path.unlink()


@asynccontextmanager
async def async_temporary_directory() -> AsyncGenerator[Path, None]:
    """异步临时目录上下文管理器"""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        yield temp_dir
    finally:
        await asyncio.get_event_loop().run_in_executor(
            None, shutil.rmtree, temp_dir, True
        )


@contextmanager
def environment_variables(**env_vars):
    """环境变量上下文管理器"""
    import os

    original_env = {}

    # 保存原始环境变量
    for key in env_vars:
        if key in os.environ:
            original_env[key] = os.environ[key]

    # 设置新环境变量
    os.environ.update(env_vars)

    try:
        yield
    finally:
        # 恢复原始环境变量
        for key in env_vars:
            if key in original_env:
                os.environ[key] = original_env[key]
            else:
                os.environ.pop(key, None)


# 断言工具
def assert_dataframe_equal(
    df1: pd.DataFrame, df2: pd.DataFrame, check_dtype: bool = True
):
    """断言DataFrame相等"""
    pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype)


def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]):
    """断言字典包含指定键值对"""
    for key, value in expected.items():
        assert key in actual, f"缺少键: {key}"
        assert actual[key] == value, f"键 {key} 的值不匹配: 期望 {value}, 实际 {actual[key]}"


def assert_list_contains_type(lst: List[Any], expected_type: type):
    """断言列表包含指定类型的元素"""
    assert all(
        isinstance(item, expected_type) for item in lst
    ), f"列表包含非 {expected_type.__name__} 类型的元素"


def assert_performance_metrics(
    metrics: Dict[str, float],
    min_return: float = 0.0,
    min_sharpe: float = 0.5,
    max_drawdown: float = 0.2,
):
    """断言性能指标"""
    assert (
        metrics.get("total_return", -1) >= min_return
    ), f"总收益率 {metrics.get('total_return')} 低于最小要求 {min_return}"
    assert (
        metrics.get("sharpe_ratio", 0) >= min_sharpe
    ), f"夏普比率 {metrics.get('sharpe_ratio')} 低于最小要求 {min_sharpe}"
    assert (
        metrics.get("max_drawdown", 1) <= max_drawdown
    ), f"最大回撤 {metrics.get('max_drawdown')} 超过最大限制 {max_drawdown}"


# 工具函数
def generate_random_string(length: int = 10) -> str:
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_id() -> str:
    """生成随机ID"""
    import uuid

    return str(uuid.uuid4())


def wait_for_condition(
    condition: Callable[[], bool], timeout: float = 10.0, interval: float = 0.1
) -> bool:
    """等待条件满足"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)

    return False


async def async_wait_for_condition(
    condition: Callable[[], bool], timeout: float = 10.0, interval: float = 0.1
) -> bool:
    """异步等待条件满足"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition():
            return True
        await asyncio.sleep(interval)

    return False


def serialize_test_data(data: Any, file_path: Path, compress: bool = True):
    """序列化测试数据"""
    serialized = pickle.dumps(data)

    if compress:
        serialized = gzip.compress(serialized)

    with open(file_path, "wb") as f:
        f.write(serialized)


def deserialize_test_data(file_path: Path, compressed: bool = True) -> Any:
    """反序列化测试数据"""
    with open(file_path, "rb") as f:
        data = f.read()

    if compressed:
        data = gzip.decompress(data)

    return pickle.loads(data)


def create_test_config(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """创建测试配置"""
    base_config = {
        "environment": "test",
        "debug": True,
        "testing": True,
        "database": {"path": ":memory:", "echo": False},
        "redis": {"host": "localhost", "port": 6379, "db": 15},
        "zmq": {"subscriber_port": 5555, "publisher_port": 5556},
        "logging": {"level": "DEBUG"},
    }

    if overrides:
        base_config.update(overrides)

    return base_config


def cleanup_test_files(pattern: str = "test_*", directory: Path = None):
    """清理测试文件"""
    if directory is None:
        directory = Path.cwd()

    for file_path in directory.glob(pattern):
        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            shutil.rmtree(file_path, ignore_errors=True)


# 测试数据验证
def validate_market_data(data: pd.DataFrame) -> bool:
    """验证市场数据格式"""
    required_columns = ["timestamp", "open", "high", "low", "close", "volume"]

    # 检查必需列
    if not all(col in data.columns for col in required_columns):
        return False

    # 检查数据类型
    if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
        return False

    # 检查价格逻辑
    price_valid = (
        (data["high"] >= data["low"])
        & (data["high"] >= data["open"])
        & (data["high"] >= data["close"])
        & (data["low"] <= data["open"])
        & (data["low"] <= data["close"])
    ).all()

    return price_valid


def validate_strategy_parameters(params: Dict[str, Any], strategy_type: str) -> bool:
    """验证策略参数"""
    if strategy_type == "ma_cross":
        required_keys = ["fast_period", "slow_period"]
        return all(key in params for key in required_keys)
    elif strategy_type == "rsi_mean_reversion":
        required_keys = ["rsi_period", "oversold", "overbought"]
        return all(key in params for key in required_keys)
    elif strategy_type == "bollinger_bands":
        required_keys = ["period", "std_dev"]
        return all(key in params for key in required_keys)
    else:
        return True  # 未知策略类型，假设有效


def validate_backtest_results(results: Dict[str, Any]) -> bool:
    """验证回测结果"""
    required_keys = [
        "total_return",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
        "total_trades",
    ]

    # 检查必需键
    if not all(key in results for key in required_keys):
        return False

    # 检查数值范围
    if results["max_drawdown"] < 0 or results["max_drawdown"] > 1:
        return False

    if results["win_rate"] < 0 or results["win_rate"] > 1:
        return False

    if results["total_trades"] < 0:
        return False

    return True


# 导出所有工具
__all__ = [
    "TestDataType",
    "TestMetrics",
    "DataGenerator",
    "MockFactory",
    "PerformanceProfiler",
    "timeout",
    "retry",
    "performance_test",
    "temporary_directory",
    "temporary_database",
    "async_temporary_directory",
    "environment_variables",
    "assert_dataframe_equal",
    "assert_dict_contains",
    "assert_list_contains_type",
    "assert_performance_metrics",
    "generate_random_string",
    "generate_random_id",
    "wait_for_condition",
    "async_wait_for_condition",
    "serialize_test_data",
    "deserialize_test_data",
    "create_test_config",
    "cleanup_test_files",
    "validate_market_data",
    "validate_strategy_parameters",
    "validate_backtest_results",
]
