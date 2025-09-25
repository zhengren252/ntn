# -*- coding: utf-8 -*-
"""
pytest fixtures for APIForge project
- Replace ZMQManager with DummyZMQManager to disable real ZeroMQ
- Provide mocked managers (Redis, SQLite, Auth, ZMQ) for tests
- Configure test client and event loop
"""
from typing import Any, Dict
import asyncio
import os
import sys
import types
import pytest
from unittest.mock import AsyncMock, Mock, patch

# 确保测试环境禁用真实ZeroMQ
os.environ.setdefault("DISABLE_ZMQ", "1")

# 若未安装 pyzmq，则注入最小桩模块，避免 import 错误
if 'zmq' not in sys.modules:
    zmq_module = types.ModuleType('zmq')
    sys.modules['zmq'] = zmq_module
    zmq_asyncio_module = types.ModuleType('zmq.asyncio')
    sys.modules['zmq.asyncio'] = zmq_asyncio_module
    setattr(zmq_module, 'asyncio', zmq_asyncio_module)

# 全局patch目标路径
ZMQ_MANAGER_PATH = "api_factory.core.zmq_manager.ZMQManager"
REDIS_MANAGER_PATH = "api_factory.core.redis_manager.RedisManager"
SQLITE_MANAGER_PATH = "api_factory.core.sqlite_manager.SQLiteManager"
AUTH_MANAGER_PATH = "api_factory.security.auth.AuthManager"


class DummyZMQManager:
    """Dummy manager to replace real ZMQManager during tests.

    - publish_message 为 Mock 对象，测试可设置 return_value/side_effect。
    - is_connected 为 Mock，可由测试设置连接状态。
    """

    def __init__(self, *args, **kwargs) -> None:
        self.connected = False
        self.published_messages: list[dict[str, Any]] = []

        # 可由测试覆盖返回值
        self.is_connected = Mock(return_value=False)

        # 使用 Mock 实现 publish_message，既能记录消息又能尊重 return_value/side_effect
        pub_mock = Mock()

        def _pub_side_effect(*args, **kwargs):
            # 支持位置/关键字两种调用方式
            if args and not kwargs:
                topic = args[0] if len(args) > 0 else None
                message = args[1] if len(args) > 1 else None
                tenant_id = args[2] if len(args) > 2 else None
            else:
                topic = kwargs.get('topic')
                message = kwargs.get('message')
                tenant_id = kwargs.get('tenant_id')
            self.published_messages.append({
                "topic": topic,
                "message": message,
                "tenant_id": tenant_id,
            })
            # 返回当前 Mock 的 return_value（允许测试动态覆盖）
            return pub_mock.return_value

        pub_mock.side_effect = _pub_side_effect
        self.publish_message = pub_mock

    def is_enabled(self) -> bool:
        return False

    def connect(self) -> None:
        self.connected = True
        # 同步更新 is_connected Mock 的返回值
        try:
            self.is_connected.return_value = True
        except Exception:
            pass

    def disconnect(self) -> None:
        self.connected = False
        try:
            self.is_connected.return_value = False
        except Exception:
            pass

    # 其他可能被 await 的方法保留为异步签名
    async def subscribe(self, topic: str):
        return None

    async def unsubscribe(self, topic: str):
        return None


# 在导入 app 前启动核心patch，确保 main 初始化使用替身
_patch_core_zmq = patch(ZMQ_MANAGER_PATH, DummyZMQManager)
_patched_core_zmq = _patch_core_zmq.start()
_patch_redis = patch(REDIS_MANAGER_PATH)
_patched_redis = _patch_redis.start()
_patch_sqlite = patch(SQLITE_MANAGER_PATH)
_patched_sqlite = _patch_sqlite.start()
_patch_auth = patch(AUTH_MANAGER_PATH)
_patched_auth = _patch_auth.start()

# 配置被patch后的实例默认行为
try:
    redis_instance = _patched_redis.return_value
    redis_instance.get_circuit_breaker = Mock(return_value={"state": "closed", "failure_count": 0})
    redis_instance.set_circuit_breaker = Mock(return_value=True)
    # 其他常用同步接口（根据需要逐步扩展）
    redis_instance.get_cache = Mock(return_value=None)
    redis_instance.set_cache = Mock(return_value=True)
except Exception:
    pass

try:
    sqlite_instance = _patched_sqlite.return_value
    sqlite_instance.query = Mock(return_value=[])
    sqlite_instance.execute = Mock(return_value=1)
except Exception:
    pass

try:
    auth_instance = _patched_auth.return_value
    auth_instance.verify_token = Mock(return_value={"user_id": "test_user", "username": "tester"})
    auth_instance.verify_api_key = Mock(return_value={"user_id": "test_user", "username": "tester"})
    # 异步方法（如存在）返回成功
    auth_instance.health_check = AsyncMock(return_value=True)
except Exception:
    pass

# 可选：补丁 main 模块命名空间中的 ZMQManager（若其使用 from-import）
try:
    from api_factory import main as _main
    _patch_main_zmq = patch.object(_main, 'ZMQManager', DummyZMQManager)
    _patched_main_zmq = _patch_main_zmq.start()
except Exception:
    _patched_main_zmq = None


@pytest.fixture(scope="session", autouse=True)
def _stop_global_patches():
    """会话结束时停止所有全局patch，避免对其他环境造成影响。"""
    yield
    for p in [
        _patch_core_zmq, _patch_redis, _patch_sqlite, _patch_auth,
    ]:
        try:
            p.stop()
        except Exception:
            pass
    try:
        if _patched_main_zmq is not None:
            _patched_main_zmq.stop()
    except Exception:
        pass


@pytest.fixture()
def mock_zmq_manager() -> DummyZMQManager:
    """Provide a fresh DummyZMQManager instance per test when needed."""
    return DummyZMQManager()


@pytest.fixture()
def mock_auth_manager() -> Mock:
    """Provide a Mocked AuthManager for tests to control auth behavior."""
    m = Mock()
    m.verify_token = Mock(return_value={"user_id": "test_user", "username": "tester", "roles": ["admin"]})
    m.check_permission = Mock(return_value=True)
    m.verify_api_key = Mock(return_value={"user_id": "test_user", "username": "tester"})
    return m


@pytest.fixture()
def valid_user_data() -> Dict[str, Any]:
    """Provide a standard valid user payload."""
    return {"user_id": "test_user", "username": "tester", "roles": ["admin"]}


@pytest.fixture()
def mock_redis_manager() -> Mock:
    """Provide a Mocked Redis manager for circuit breaker tests."""
    m = Mock()
    m.set_circuit_breaker = Mock(return_value=True)
    m.get_circuit_breaker = Mock(return_value={"state": "closed", "timestamp": "1970-01-01T00:00:00"})
    return m


@pytest.fixture()
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def client():
    from api_factory.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)
