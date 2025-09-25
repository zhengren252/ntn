#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest配置文件

提供测试夹具和通用测试配置
"""

import asyncio
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.redis_manager import RedisManager
from app.core.zmq_manager import ZMQManager


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """模拟设置"""
    settings = MagicMock()
    settings.environment = "test"
    settings.redis_host = "localhost"
    settings.redis_port = 6379
    settings.redis_db = 1
    settings.zmq_pub_port = 5555
    settings.zmq_sub_ports = [5556, 5557]
    settings.zmq_dealer_port = 5558
    settings.zmq_router_port = 5559
    return settings


@pytest.fixture
def mock_redis_manager():
    """模拟Redis管理器"""
    redis_manager = AsyncMock(spec=RedisManager)
    redis_manager.get_bull_bear_index.return_value = {"index": 80, "timestamp": "2024-01-01T00:00:00"}
    redis_manager.get_system_status.return_value = {"status": "healthy"}
    redis_manager.set_module_status = AsyncMock()
    redis_manager.set_risk_alert = AsyncMock()
    return redis_manager


@pytest.fixture
def mock_zmq_manager():
    """模拟ZMQ管理器"""
    zmq_manager = AsyncMock(spec=ZMQManager)
    zmq_manager.running = True
    zmq_manager.publish_message = AsyncMock()
    zmq_manager.broadcast_command = AsyncMock()
    zmq_manager.send_command = AsyncMock()
    return zmq_manager


@pytest.fixture
def mock_zmq_publisher():
    """模拟ZMQ发布器"""
    publisher = AsyncMock()
    publisher.send_multipart = AsyncMock()
    return publisher


@pytest.fixture
def mock_zmq_subscriber():
    """模拟ZMQ订阅器"""
    subscriber = AsyncMock()
    subscriber.recv_multipart = AsyncMock()
    return subscriber