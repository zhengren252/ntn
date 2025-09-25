#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroMQ通信客户端
支持PUB/SUB和REQ/REP通信模式
"""

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import zmq


class MessageType(Enum):
    """消息类型枚举"""

    SCAN_REQUEST = "scan_request"
    SCAN_RESULT = "scan_result"
    MARKET_DATA = "market_data"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"
    STATUS = "status"


@dataclass
class ZMQMessage:
    """ZMQ消息数据结构"""

    message_type: str
    timestamp: str
    data: Dict[str, Any]
    source: str = "scanner"
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZMQMessage":
        return cls(**data)


class ZMQPublisher:
    """ZeroMQ发布者"""

    def __init__(self, host: str = "localhost", port: int = 5556):
        self.host = host
        self.port = port
        self.context = None
        self.socket = None
        self.logger = logging.getLogger(__name__)
        self._running = False

    def connect(self) -> bool:
        """连接到ZMQ"""
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind(f"tcp://*:{self.port}")
            self._running = True
            self.logger.info(f"ZMQ Publisher connected on port {self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect ZMQ Publisher: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self._running = False
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        self.logger.info("ZMQ Publisher disconnected")

    def publish(self, topic: str, message: ZMQMessage) -> bool:
        """发布消息"""
        if not self._running or not self.socket:
            return False

        try:
            message_data = json.dumps(message.to_dict())
            self.socket.send_multipart([topic.encode(), message_data.encode()])
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            return False

    def publish_opportunity(self, opportunity_data: Dict[str, Any]) -> bool:
        """发布交易机会到scanner.pool.preliminary主题
        
        Args:
            opportunity_data: 交易机会数据
            
        Returns:
            是否发布成功
        """
        if not self._running or not self.socket:
            self.logger.error("Publisher not running")
            return False

        try:
            # 创建机会消息
            message = ZMQMessage(
                message_type=MessageType.SCAN_RESULT.value,
                timestamp=datetime.now().isoformat(),
                data=opportunity_data,
                source="scanner"
            )

            # 发布到scanner.pool.preliminary主题
            topic = "scanner.pool.preliminary"
            message_data = json.dumps(message.to_dict())
            self.socket.send_multipart([topic.encode(), message_data.encode()])
            
            self.logger.debug(f"Published opportunity for {opportunity_data.get('symbol', 'unknown')}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish opportunity: {e}")
            return False


class ZMQSubscriber:
    """ZeroMQ订阅者"""

    def __init__(self, host: str = "localhost", port: int = 5556):
        self.host = host
        self.port = port
        self.context = None
        self.socket = None
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._thread = None
        self._callbacks: Dict[str, Callable] = {}

    def connect(self) -> bool:
        """连接到ZMQ"""
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(f"tcp://{self.host}:{self.port}")
            self._running = True
            self.logger.info(f"ZMQ Subscriber connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect ZMQ Subscriber: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        self.logger.info("ZMQ Subscriber disconnected")

    def subscribe(self, topic: str, callback: Callable[[ZMQMessage], None]):
        """订阅主题"""
        if not self.socket:
            return False

        try:
            self.socket.setsockopt(zmq.SUBSCRIBE, topic.encode())
            self._callbacks[topic] = callback
            self.logger.info(f"Subscribed to topic: {topic}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to topic {topic}: {e}")
            return False

    def start_listening(self):
        """开始监听消息"""
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        self.logger.info("Started listening for messages")

    def _listen_loop(self):
        """消息监听循环"""
        while self._running:
            try:
                if self.socket.poll(timeout=1000):  # 1秒超时
                    topic, message_data = self.socket.recv_multipart(zmq.NOBLOCK)
                    topic_str = topic.decode()

                    if topic_str in self._callbacks:
                        try:
                            message_dict = json.loads(message_data.decode())
                            message = ZMQMessage.from_dict(message_dict)
                            self._callbacks[topic_str](message)
                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
            except zmq.Again:
                continue
            except Exception as e:
                self.logger.error(f"Error in listen loop: {e}")
                break


class ScannerZMQClient:
    """扫描器ZMQ客户端"""

    def __init__(
        self,
        req_host: str = "localhost",
        req_port: int = 5555,
        pub_host: str = "localhost",
        pub_port: int = 5556,
    ):
        self.req_host = req_host
        self.req_port = req_port
        self.pub_host = pub_host
        self.pub_port = pub_port

        self.context = None
        self.req_socket = None
        self.pub_socket = None
        self.logger = logging.getLogger(__name__)
        self._connected = False

    def connect(self) -> bool:
        """连接到ZMQ服务"""
        try:
            self.context = zmq.Context()
            
            # 初始化请求套接字
            self.req_socket = self.context.socket(zmq.REQ)
            self.req_socket.connect(f"tcp://{self.req_host}:{self.req_port}")
            self.req_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10秒超时
            
            # 初始化发布套接字
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.connect(f"tcp://{self.pub_host}:{self.pub_port}")
            
            self._connected = True
            self.logger.info(
                f"Scanner ZMQ Client connected to REQ:{self.req_host}:{self.req_port}, PUB:{self.pub_host}:{self.pub_port}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect Scanner ZMQ Client: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self._connected = False
        if self.req_socket:
            self.req_socket.close()
        if self.pub_socket:
            self.pub_socket.close()
        if self.context:
            self.context.term()
        self.logger.info("Scanner ZMQ Client disconnected")

    def send_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """发送请求"""
        if not self._connected or not self.req_socket:
            self.logger.error("Client not connected")
            return None

        try:
            request = {
                "method": method,
                "params": params or {},
                "timestamp": datetime.now().isoformat(),
                "id": str(int(time.time() * 1000)),
            }

            self.req_socket.send_json(request)
            response = self.req_socket.recv_json()
            return response

        except zmq.Again:
            self.logger.error("Request timeout")
            return None
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            return None

    def health_check(self) -> bool:
        """健康检查"""
        response = self.send_request("health_check")
        return response and response.get("status") == "success"

    def scan_market(self, symbols: List[str] = None) -> Optional[Dict[str, Any]]:
        """市场扫描"""
        params = {}
        if symbols:
            params["symbols"] = symbols
        return self.send_request("scan.market", params)

    def analyze_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """分析交易对"""
        return self.send_request("analyze.symbol", {"symbol": symbol})

    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据"""
        return self.send_request("get.market_data", {"symbol": symbol})

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    async def publish_scan_result(self, result: Dict[str, Any]) -> bool:
        """发布扫描结果到scanner.pool.preliminary主题
        
        Args:
            result: 扫描结果数据
            
        Returns:
            是否发布成功
        """
        if not self._connected or not self.pub_socket:
            self.logger.error("ZMQ client not connected for publishing")
            return False

        try:
            # 创建标准消息
            message = ZMQMessage(
                message_type=MessageType.SCAN_RESULT.value,
                timestamp=datetime.now().isoformat(),
                data=result,
                source="scanner"
            )

            # 发布到scanner.pool.preliminary主题
            topic = "scanner.pool.preliminary"
            message_data = json.dumps(message.to_dict())
            self.pub_socket.send_multipart([topic.encode(), message_data.encode()])
            
            self.logger.debug(f"Published scan result for {result.get('symbol', 'unknown')}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish scan result: {e}")
            return False

    async def publish_status_update(self, status_data: Dict[str, Any]) -> bool:
        """发布状态更新
        
        Args:
            status_data: 状态数据
            
        Returns:
            是否发布成功
        """
        if not self._connected or not self.pub_socket:
            self.logger.error("ZMQ client not connected for publishing")
            return False

        try:
            # 创建状态消息
            message = ZMQMessage(
                message_type=MessageType.STATUS.value,
                timestamp=datetime.now().isoformat(),
                data=status_data,
                source="scanner"
            )

            # 发布到scanner.status主题
            topic = "scanner.status"
            message_data = json.dumps(message.to_dict())
            self.pub_socket.send_multipart([topic.encode(), message_data.encode()])
            
            self.logger.debug("Published status update")
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish status update: {e}")
            return False
