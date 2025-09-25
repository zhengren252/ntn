import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tacoreservice.config import Settings
from tacoreservice.core.database import DatabaseManager
from tacoreservice.monitoring.logger import ServiceLogger


@pytest.fixture(scope="session")
def test_settings():
    """测试配置"""
    return Settings(
        service_name="TACoreService-Test",
        debug=True,
        zmq_frontend_port=15555,
        zmq_backend_port=15556,
        zmq_bind_address="127.0.0.1",
        http_host="127.0.0.1",
        http_port=18080,
        redis_host="localhost",
        redis_port=6379,
        redis_db=1,  # 使用不同的数据库
        sqlite_db_path=":memory:",  # 使用内存数据库
        worker_count=2,
        worker_timeout=10,
        tradingagents_path="./test_tradingagents",
        health_check_interval=5,
        metrics_retention_days=7,
    )


@pytest.fixture
def temp_dir():
    """临时目录"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_database(test_settings, temp_dir):
    """测试数据库"""
    db_path = temp_dir / "test.db"

    # 临时修改设置中的数据库路径
    original_path = test_settings.sqlite_db_path
    test_settings.sqlite_db_path = str(db_path)

    # 使用patch来模拟get_settings返回测试设置
    with patch("tacoreservice.core.database.get_settings", return_value=test_settings):
        db_manager = DatabaseManager()

        yield db_manager

        # 恢复原始路径
        test_settings.sqlite_db_path = original_path


@pytest.fixture
def mock_zmq_context():
    """模拟ZeroMQ上下文"""
    with patch("zmq.Context") as mock_context:
        mock_socket = Mock()
        mock_context.return_value.socket.return_value = mock_socket
        yield mock_context, mock_socket


@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    with patch("redis.Redis") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_tradingagents():
    """模拟TradingAgents-CN"""
    mock_components = {
        "market_scanner": Mock(),
        "order_executor": Mock(),
        "risk_evaluator": Mock(),
        "stock_analyzer": Mock(),
        "market_data_provider": Mock(),
    }

    # 设置默认返回值
    mock_components["market_scanner"].scan_market.return_value = {
        "stocks": ["AAPL", "GOOGL", "MSFT"],
        "count": 3,
    }

    mock_components["order_executor"].execute_order.return_value = {
        "order_id": "TEST123",
        "status": "FILLED",
        "executed_price": 150.0,
    }

    mock_components["risk_evaluator"].evaluate_risk.return_value = {
        "var": 0.05,
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.15,
    }

    mock_components["stock_analyzer"].analyze_stock.return_value = {
        "sma": 150.0,
        "rsi": 65.0,
        "macd": 2.5,
    }

    mock_components["market_data_provider"].get_market_data.return_value = {
        "AAPL": {"price": 150.0, "volume": 1000000, "change": 2.5},
        "GOOGL": {"price": 2500.0, "volume": 500000, "change": -1.2},
    }

    yield mock_components


@pytest.fixture
def sample_request():
    """示例请求数据"""
    return {
        "method": "health.check",
        "parameters": {},
        "request_id": "test_request_123",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_response():
    """示例响应数据"""
    return {
        "status": "success",
        "data": {"health": "ok"},
        "error": None,
        "request_id": "test_request_123",
        "timestamp": "2024-01-01T00:00:01Z",
        "response_time": 0.001,
    }


@pytest.fixture(autouse=True)
def setup_test_environment(test_settings):
    """设置测试环境"""
    # 设置环境变量
    os.environ.update(
        {
            "SERVICE_NAME": test_settings.service_name,
            "DEBUG": str(test_settings.debug),
            "ZMQ_FRONTEND_PORT": str(test_settings.zmq_frontend_port),
            "ZMQ_BACKEND_PORT": str(test_settings.zmq_backend_port),
            "HTTP_PORT": str(test_settings.http_port),
            "SQLITE_DB_PATH": test_settings.sqlite_db_path,
            "WORKER_COUNT": str(test_settings.worker_count),
        }
    )

    yield

    # 清理环境变量
    test_env_vars = [
        "SERVICE_NAME",
        "DEBUG",
        "ZMQ_FRONTEND_PORT",
        "ZMQ_BACKEND_PORT",
        "HTTP_PORT",
        "SQLITE_DB_PATH",
        "WORKER_COUNT",
    ]

    for var in test_env_vars:
        os.environ.pop(var, None)


@pytest.fixture
def logger():
    """测试日志器"""
    return ServiceLogger.get_logger("test")


# 测试标记
pytest_plugins = []


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "performance: 性能测试")
    config.addinivalue_line("markers", "slow: 慢速测试")


def pytest_collection_modifyitems(config, items):
    """修改测试项目"""
    # 为没有标记的测试添加unit标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)
