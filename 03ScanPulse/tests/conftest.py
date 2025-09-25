#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03ScanPulse 测试配置文件
提供全局测试配置、fixtures和工具函数
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试标记定义
pytest_plugins = []


def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "performance: 性能测试标记")
    config.addinivalue_line("markers", "load: 负载测试标记")
    config.addinivalue_line("markers", "stability: 稳定性测试标记")
    config.addinivalue_line("markers", "stress: 压力测试标记")
    config.addinivalue_line("markers", "production: 生产环境验证标记")
    config.addinivalue_line("markers", "reporting: 测试报告分析标记")
    config.addinivalue_line("markers", "e2e: 端到端测试标记")
    config.addinivalue_line("markers", "slow: 慢速测试标记（运行时间>30秒）")
    config.addinivalue_line("markers", "network: 需要网络连接的测试")
    config.addinivalue_line("markers", "redis: 需要Redis服务的测试")
    config.addinivalue_line("markers", "zmq: 需要ZMQ的测试")


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def temp_dir():
    """临时目录fixture"""
    temp_path = Path(tempfile.mkdtemp(prefix="scanpulse_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_redis_client():
    """模拟Redis客户端"""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = False
    mock_client.keys.return_value = []
    mock_client.flushdb.return_value = True
    return mock_client


@pytest.fixture
def mock_zmq_context():
    """模拟ZMQ上下文"""
    mock_context = Mock()
    mock_socket = Mock()
    mock_socket.bind.return_value = None
    mock_socket.connect.return_value = None
    mock_socket.send_json.return_value = None
    mock_socket.recv_json.return_value = {"status": "ok"}
    mock_socket.close.return_value = None
    mock_context.socket.return_value = mock_socket
    return mock_context


@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 1000.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "high": 51000.0,
        "low": 49000.0,
        "open": 49500.0,
        "close": 50000.0,
        "change_percent": 1.01,
    }


@pytest.fixture
def sample_scan_result():
    """示例扫描结果"""
    return {
        "symbol": "BTCUSDT",
        "rule_name": "三高策略",
        "score": 85.5,
        "signals": [
            {"type": "volume_spike", "strength": 0.8},
            {"type": "price_momentum", "strength": 0.9},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {"processing_time": 0.05, "data_quality": "high"},
    }


@pytest.fixture
def performance_config():
    """性能测试配置"""
    return {
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 15,  # 使用测试数据库
            "decode_responses": True,
        },
        "zmq": {"publisher_port": 5555, "subscriber_port": 5556, "timeout": 1000},
        "scanner": {"batch_size": 100, "max_workers": 4, "timeout": 30},
        "thresholds": {
            "max_processing_time": 1.0,  # 秒
            "max_memory_usage": 500,  # MB
            "max_cpu_usage": 80,  # 百分比
            "min_throughput": 100,  # 每秒处理数
        },
    }


@pytest.fixture
def load_test_config():
    """负载测试配置"""
    return {
        "concurrent_users": 100,
        "test_duration": 60,  # 秒
        "ramp_up_time": 10,  # 秒
        "data_volume": 10000,  # 数据条数
        "batch_sizes": [10, 50, 100, 500],
        "memory_limit": 1024,  # MB
        "cpu_limit": 90,  # 百分比
        "network_timeout": 5,  # 秒
    }


@pytest.fixture
def stability_test_config():
    """稳定性测试配置"""
    return {
        "test_duration": 3600,  # 1小时（生产环境可设为24小时）
        "monitoring_interval": 60,  # 监控间隔（秒）
        "memory_threshold": 1024,  # 内存阈值（MB）
        "error_threshold": 0.01,  # 错误率阈值（1%）
        "recovery_timeout": 30,  # 恢复超时（秒）
        "resource_check_interval": 300,  # 资源检查间隔（秒）
    }


@pytest.fixture
def stress_test_config():
    """压力测试配置"""
    return {
        "cpu_stress_duration": 60,  # CPU压力测试时长
        "memory_stress_size": 512,  # 内存压力大小（MB）
        "disk_io_size": 1024,  # 磁盘IO大小（MB）
        "network_bandwidth": 100,  # 网络带宽（Mbps）
        "connection_pool_size": 100,  # 连接池大小
        "concurrent_operations": 50,  # 并发操作数
    }


@pytest.fixture
def production_test_config():
    """生产环境测试配置"""
    return {
        "data_sources": {
            "binance": {
                "enabled": True,
                "api_key": os.getenv("BINANCE_API_KEY", "test_key"),
                "secret_key": os.getenv("BINANCE_SECRET_KEY", "test_secret"),
            },
            "mock": {"enabled": True, "data_file": "mock_data.json"},
        },
        "environments": ["development", "staging", "production"],
        "security": {
            "enable_auth": True,
            "enable_encryption": True,
            "enable_rate_limiting": True,
        },
        "monitoring": {
            "enable_metrics": True,
            "enable_alerts": True,
            "alert_channels": ["email", "slack"],
        },
    }


@pytest.fixture
def reporting_config():
    """报告配置"""
    return {
        "output_dir": "test_reports",
        "formats": ["html", "json", "csv"],
        "include_charts": True,
        "include_trends": True,
        "baseline_file": "performance_baseline.json",
        "quality_gates": {
            "test_success_rate": 0.95,
            "code_coverage": 0.80,
            "performance_regression": 0.10,
        },
    }


# 测试数据生成器
class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_market_data(count=100, symbol="BTCUSDT"):
        """生成市场数据"""
        import random

        data = []
        base_price = 50000.0

        for i in range(count):
            price = base_price + random.uniform(-1000, 1000)
            data.append(
                {
                    "symbol": symbol,
                    "price": price,
                    "volume": random.uniform(100, 10000),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "high": price + random.uniform(0, 500),
                    "low": price - random.uniform(0, 500),
                    "open": price + random.uniform(-200, 200),
                    "close": price,
                    "change_percent": random.uniform(-5, 5),
                }
            )

        return data

    @staticmethod
    def generate_scan_results(count=50):
        """生成扫描结果"""
        import random

        results = []
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
        rules = ["三高策略", "黑马检测", "潜力挖掘", "动量突破", "成交量异动"]

        for i in range(count):
            results.append(
                {
                    "symbol": random.choice(symbols),
                    "rule_name": random.choice(rules),
                    "score": random.uniform(60, 100),
                    "signals": [
                        {"type": "volume_spike", "strength": random.uniform(0.5, 1.0)},
                        {
                            "type": "price_momentum",
                            "strength": random.uniform(0.5, 1.0),
                        },
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "processing_time": random.uniform(0.01, 0.1),
                        "data_quality": random.choice(["high", "medium", "low"]),
                    },
                }
            )

        return results


# 测试工具函数
def skip_if_no_redis():
    """如果没有Redis则跳过测试"""
    try:
        import redis

        client = redis.Redis(host="localhost", port=6379, db=15)
        client.ping()
        return False
    except Exception:
        return True


def skip_if_no_zmq():
    """如果没有ZMQ则跳过测试"""
    try:
        import zmq

        return False
    except ImportError:
        return True


def skip_if_no_network():
    """如果没有网络连接则跳过测试"""
    import socket

    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return False
    except OSError:
        return True


# 性能测试装饰器
def performance_test(max_time=None, max_memory=None):
    """性能测试装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            import psutil
            import os

            # 记录开始状态
            start_time = time.time()
            process = psutil.Process(os.getpid())
            start_memory = process.memory_info().rss / 1024 / 1024  # MB

            try:
                result = func(*args, **kwargs)

                # 检查性能指标
                end_time = time.time()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB

                execution_time = end_time - start_time
                memory_usage = end_memory - start_memory

                if max_time and execution_time > max_time:
                    pytest.fail(f"测试执行时间 {execution_time:.2f}s 超过限制 {max_time}s")

                if max_memory and memory_usage > max_memory:
                    pytest.fail(f"内存使用 {memory_usage:.2f}MB 超过限制 {max_memory}MB")

                return result

            except Exception as e:
                pytest.fail(f"性能测试失败: {str(e)}")

        return wrapper

    return decorator


# 清理函数
def cleanup_test_data():
    """清理测试数据"""
    # 清理Redis测试数据
    try:
        import redis

        client = redis.Redis(host="localhost", port=6379, db=15)
        client.flushdb()
    except Exception:
        pass

    # 清理临时文件
    temp_dirs = Path("/tmp").glob("scanpulse_test_*")
    for temp_dir in temp_dirs:
        if temp_dir.is_dir():
            shutil.rmtree(temp_dir, ignore_errors=True)


# 测试会话钩子
def pytest_sessionstart(session):
    """测试会话开始"""
    print("\n=== 03ScanPulse 测试会话开始 ===")
    cleanup_test_data()


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束"""
    cleanup_test_data()
    print("\n=== 03ScanPulse 测试会话结束 ===")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集项"""
    # 为慢速测试添加标记
    for item in items:
        if "stability" in item.keywords or "stress" in item.keywords:
            item.add_marker(pytest.mark.slow)

        # 为需要外部服务的测试添加跳过条件
        if "redis" in item.keywords and skip_if_no_redis():
            item.add_marker(pytest.mark.skip(reason="Redis服务不可用"))

        if "zmq" in item.keywords and skip_if_no_zmq():
            item.add_marker(pytest.mark.skip(reason="ZMQ库不可用"))

        if "network" in item.keywords and skip_if_no_network():
            item.add_marker(pytest.mark.skip(reason="网络连接不可用"))
