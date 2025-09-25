# ZeroMQ客户端单元测试
# 测试ZeroMQ通信协议实现

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.communication.zmq_client import (
    ScannerZMQClient,
    ZMQMessage,
    MessageType,
    ZMQPublisher,
    ZMQSubscriber,
)


class TestZMQMessage:
    """ZMQ消息测试类"""

    @pytest.mark.unit
    def test_message_creation(self):
        """测试消息创建"""
        message = ZMQMessage(
            message_id="test_123",
            message_type=MessageType.SCAN_REQUEST,
            topic="test.topic",
            payload={"symbol": "BTCUSDT"},
            timestamp=datetime.now().isoformat(),
            source="test_client",
        )

        assert message.message_type == MessageType.SCAN_REQUEST
        assert message.payload == {"symbol": "BTCUSDT"}
        assert message.source == "test_client"
        assert message.message_id == "test_123"
        assert message.timestamp is not None

    @pytest.mark.unit
    def test_message_serialization(self):
        """测试消息序列化"""
        message = ZMQMessage(
            message_id="test_123",
            message_type=MessageType.SCAN_RESULT,
            topic="scan.result",
            payload={"symbol": "BTCUSDT", "score": 0.85},
            timestamp=datetime.now().isoformat(),
            source="scanner",
        )

        message_dict = message.to_dict()
        assert isinstance(message_dict, dict)
        assert message_dict["message_type"] == MessageType.SCAN_RESULT.value
        assert message_dict["payload"]["symbol"] == "BTCUSDT"
        assert message_dict["source"] == "scanner"

    @pytest.mark.unit
    def test_message_deserialization(self):
        """测试消息反序列化"""
        message_dict = {
            "message_id": "test_123",
            "message_type": "scan_request",
            "topic": "test.topic",
            "payload": {"status": "running"},
            "timestamp": "2024-01-01T12:00:00Z",
            "source": "scanner",
        }

        message = ZMQMessage.from_dict(message_dict)

        assert message.message_id == "test_123"
        assert message.message_type == MessageType.SCAN_REQUEST
        assert message.payload == {"status": "running"}
        assert message.source == "scanner"


class TestScannerZMQClient:
    """扫描器ZMQ客户端测试"""

    @pytest.fixture
    def zmq_client(self):
        """ZMQ客户端实例"""
        return ScannerZMQClient()

    @pytest.mark.unit
    def test_client_initialization(self):
        """测试客户端初始化"""
        client = ScannerZMQClient()

        assert client.req_host == "localhost"
        assert client.req_port == 5555
        assert client.pub_host == "localhost"
        assert client.pub_port == 5556
        assert client._connected is False
        assert client.context is None

    @pytest.mark.unit
    def test_client_connect(self, zmq_client):
        """测试客户端连接"""
        # 由于实际连接需要ZMQ服务器，这里只测试方法存在
        assert hasattr(zmq_client, "connect")
        assert callable(getattr(zmq_client, "connect"))

    @pytest.mark.unit
    def test_client_disconnect(self, zmq_client):
        """测试客户端断开连接"""
        # 测试断开连接方法存在
        assert hasattr(zmq_client, "disconnect")
        assert callable(getattr(zmq_client, "disconnect"))


class TestZMQPublisher:
    """ZMQ发布者测试类"""

    @pytest.fixture
    def publisher(self):
        """发布者实例"""
        return ZMQPublisher()

    @pytest.mark.unit
    def test_publisher_initialization(self):
        """测试发布者初始化"""
        publisher = ZMQPublisher()

        assert publisher.host == "localhost"
        assert publisher.port == 5556
        assert publisher.context is None
        assert publisher.socket is None
        assert publisher._running is False

    @pytest.mark.unit
    @patch("zmq.Context")
    def test_publisher_connect(self, mock_context_class, publisher):
        """测试发布者连接"""
        mock_context = MagicMock()
        mock_socket = MagicMock()
        mock_context.socket.return_value = mock_socket
        mock_context_class.return_value = mock_context

        result = publisher.connect()

        assert result is True
        assert publisher._running is True
        mock_socket.bind.assert_called_once()

    @pytest.mark.unit
    def test_publish_message(self, publisher):
        """测试发布消息"""
        publisher._running = True
        publisher.socket = MagicMock()

        message = ZMQMessage(
            message_type="test",
            timestamp="2024-01-01T12:00:00Z",
            data={"symbol": "BTCUSDT"},
            source="scanner",
        )

        result = publisher.publish("test.topic", message)

        assert result is True
        publisher.socket.send_multipart.assert_called_once()


class TestZMQSubscriber:
    """ZMQ订阅者测试类"""

    @pytest.fixture
    def subscriber(self):
        """订阅者实例"""
        return ZMQSubscriber()

    @pytest.mark.unit
    def test_subscriber_initialization(self):
        """测试订阅者初始化"""
        subscriber = ZMQSubscriber()

        assert subscriber.host == "localhost"
        assert subscriber.port == 5557
        assert subscriber.context is None
        assert subscriber.socket is None
        assert subscriber._running is False

    @pytest.mark.unit
    def test_subscriber_connect(self, subscriber):
        """测试订阅者连接"""
        # 由于实际连接需要ZMQ服务器，这里只测试方法存在
        assert hasattr(subscriber, "connect")
        assert callable(getattr(subscriber, "connect"))


class TestScannerZMQClient:
    """扫描器ZMQ客户端测试类"""

    @pytest.fixture
    def scanner_client(self):
        """扫描器客户端实例"""
        return ScannerZMQClient()

    @pytest.mark.unit
    def test_scanner_client_initialization(self):
        """测试扫描器客户端初始化"""
        client = ScannerZMQClient()

        assert client.req_host == "localhost"
        assert client.req_port == 5555
        assert client.pub_host == "localhost"
        assert client.pub_port == 5556
        assert client._connected is False
        assert client.context is None

    @pytest.mark.unit
    def test_scanner_client_connect(self, scanner_client):
        """测试扫描器客户端连接"""
        # 由于实际连接需要ZMQ服务器，这里只测试方法存在
        assert hasattr(scanner_client, "connect")
        assert callable(getattr(scanner_client, "connect"))

    @pytest.mark.unit
    def test_scanner_client_disconnect(self, scanner_client):
        """测试扫描器客户端断开连接"""
        assert hasattr(scanner_client, "disconnect")
        assert callable(getattr(scanner_client, "disconnect"))

    @pytest.mark.unit
    def test_health_check(self, scanner_client):
        """测试健康检查"""
        assert hasattr(scanner_client, "health_check")
        assert callable(getattr(scanner_client, "health_check"))

    @pytest.mark.unit
    def test_scan_market(self, scanner_client):
        """测试市场扫描"""
        assert hasattr(scanner_client, "scan_market")
        assert callable(getattr(scanner_client, "scan_market"))

    @pytest.mark.unit
    def test_analyze_symbol(self, scanner_client):
        """测试分析交易对"""
        assert hasattr(scanner_client, "analyze_symbol")
        assert callable(getattr(scanner_client, "analyze_symbol"))

    @pytest.mark.unit
    def test_is_connected(self, scanner_client):
        """测试连接状态检查"""
        assert hasattr(scanner_client, "is_connected")
        assert callable(getattr(scanner_client, "is_connected"))
        # 初始状态应该是未连接
        assert scanner_client.is_connected() is False
