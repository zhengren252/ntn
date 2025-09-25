# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - ZeroMQ发布者客户端
负责crawler.news主题的消息发布和系统间通信
"""

import sys
import os
import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

import zmq
from zmq import Context, Socket

from ..config import ConfigManager
from ..utils import Logger


@dataclass
class NewsMessage:
    """新闻消息数据结构"""

    id: str
    title: str
    content: str
    source: str
    url: Optional[str]
    timestamp: str
    category: str
    sentiment: Optional[float]
    keywords: List[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsMessage":
        """从字典创建消息"""
        return cls(**data)


class ZMQPublisher:
    """ZeroMQ发布者客户端

    核心功能：
    1. 发布crawler.news主题消息
    2. 高性能异步通信
    3. 消息持久化和重试
    4. 连接管理和监控
    """

    def __init__(self, config: ConfigManager, logger: Logger = None):
        """初始化ZeroMQ发布者

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or Logger(config)

        # ZeroMQ配置
        self.zmq_config = config.get_zmq_config()
        self.host = self.zmq_config.get("publisher", {}).get("host", "127.0.0.1")
        self.port = self.zmq_config.get("publisher", {}).get("port", 5555)
        self.topic = self.zmq_config.get("publisher", {}).get("topic", "crawler.news")
        self.timeout = self.zmq_config.get("timeout", 5000)
        self.high_water_mark = self.zmq_config.get("high_water_mark", 1000)

        # ZeroMQ上下文和套接字
        self.context: Optional[Context] = None
        self.socket: Optional[Socket] = None

        # 连接状态
        self._connected = False
        self._running = False

        # 消息统计
        self.stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "bytes_sent": 0,
            "connection_errors": 0,
            "last_message_time": None,
        }

        # 线程锁
        self._lock = threading.Lock()

        # 消息队列（用于重试）
        self._message_queue: List[Dict[str, Any]] = []
        self._max_queue_size = 10000

        self.logger.info(f"ZeroMQ发布者初始化: {self.host}:{self.port}")

    def connect(self) -> bool:
        """连接到ZeroMQ服务器

        Returns:
            连接是否成功
        """
        try:
            with self._lock:
                if self._connected:
                    self.logger.warning("ZeroMQ发布者已连接")
                    return True

                # 创建ZeroMQ上下文
                self.context = zmq.Context()

                # 创建发布者套接字
                self.socket = self.context.socket(zmq.PUB)

                # 设置套接字选项
                self.socket.setsockopt(zmq.SNDHWM, self.high_water_mark)
                self.socket.setsockopt(zmq.SNDTIMEO, self.timeout)
                self.socket.setsockopt(zmq.LINGER, 1000)

                # 绑定到地址
                bind_address = f"tcp://{self.host}:{self.port}"
                self.socket.bind(bind_address)

                self._connected = True
                self._running = True

                self.logger.info(f"✓ ZeroMQ发布者连接成功: {bind_address}")
                return True

        except Exception as e:
            self.stats["connection_errors"] += 1
            self.logger.error(f"ZeroMQ发布者连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开ZeroMQ连接"""
        try:
            with self._lock:
                self._running = False

                if self.socket:
                    self.socket.close()
                    self.socket = None

                if self.context:
                    self.context.term()
                    self.context = None

                self._connected = False

                self.logger.info("✓ ZeroMQ发布者连接已断开")

        except Exception as e:
            self.logger.error(f"ZeroMQ发布者断开连接失败: {e}")

    def publish_message(self, message: NewsMessage, retry: bool = True) -> bool:
        """发布新闻消息

        Args:
            message: 新闻消息
            retry: 是否重试

        Returns:
            发布是否成功
        """
        if not self._connected:
            if not self.connect():
                return False

        try:
            # 构建消息
            topic_bytes = self.topic.encode("utf-8")
            message_data = message.to_dict()

            # 添加发布时间戳
            message_data["published_at"] = datetime.utcnow().isoformat()
            message_data["publisher"] = "ntn-crawler"

            message_bytes = json.dumps(message_data, ensure_ascii=False).encode("utf-8")

            # 发送消息
            with self._lock:
                if not self.socket:
                    raise RuntimeError("ZeroMQ套接字未初始化")

                self.socket.send_multipart([topic_bytes, message_bytes], zmq.NOBLOCK)

            # 更新统计
            self.stats["messages_sent"] += 1
            self.stats["bytes_sent"] += len(message_bytes)
            self.stats["last_message_time"] = datetime.utcnow().isoformat()

            self.logger.debug(
                f"消息发布成功: {message.id} | 主题: {self.topic} | "
                f"大小: {len(message_bytes)} bytes"
            )

            return True

        except zmq.Again:
            # 发送缓冲区满，加入重试队列
            if retry and len(self._message_queue) < self._max_queue_size:
                self._message_queue.append(message.to_dict())
                self.logger.warning(f"消息加入重试队列: {message.id}")
            else:
                self.stats["messages_failed"] += 1
                self.logger.error(f"消息发布失败（缓冲区满）: {message.id}")
            return False

        except Exception as e:
            self.stats["messages_failed"] += 1
            self.logger.error(f"消息发布失败: {message.id} | 错误: {e}")

            # 连接可能断开，尝试重连
            if "Connection refused" in str(e) or "Socket operation" in str(e):
                self._connected = False

            return False

    def publish_raw_data(self, data: Dict[str, Any]) -> bool:
        """发布原始数据

        Args:
            data: 原始数据字典

        Returns:
            发布是否成功
        """
        try:
            # 验证必需字段
            required_fields = ["id", "title", "content", "source", "timestamp"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"缺少必需字段: {field}")

            # 创建消息对象
            message = NewsMessage(
                id=data["id"],
                title=data["title"],
                content=data["content"],
                source=data["source"],
                url=data.get("url"),
                timestamp=data["timestamp"],
                category=data.get("category", "unknown"),
                sentiment=data.get("sentiment"),
                keywords=data.get("keywords", []),
                metadata=data.get("metadata", {}),
            )

            return self.publish_message(message)

        except Exception as e:
            self.logger.error(f"发布原始数据失败: {e}")
            return False

    def publish(self, topic: str, data: Any) -> bool:
        """兼容接口：发布任意payload，采用[topic,payload]双帧，并统一固定主题为self.topic（crawler.news）

        Args:
            topic: 外部传入的主题（将被忽略并统一为self.topic）
            data: 可为dict/list/str/bytes或拥有to_dict/to_json方法的对象

        Returns:
            发布是否成功
        """
        if not self._connected:
            if not self.connect():
                return False
        try:
            effective_topic = self.topic
            if topic and topic != self.topic:
                self.logger.warning(f"忽略外部topic '{topic}'，使用固定主题 '{self.topic}'")

            # 转换payload为bytes
            if isinstance(data, bytes):
                payload_bytes = data
            elif isinstance(data, str):
                payload_bytes = data.encode("utf-8")
            elif isinstance(data, (dict, list)):
                payload_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            else:
                if hasattr(data, "to_json"):
                    payload_bytes = data.to_json().encode("utf-8")
                elif hasattr(data, "to_dict"):
                    payload_bytes = json.dumps(data.to_dict(), ensure_ascii=False).encode("utf-8")
                else:
                    payload_bytes = json.dumps(
                        data,
                        default=lambda o: getattr(o, "__dict__", str(o)),
                        ensure_ascii=False,
                    ).encode("utf-8")

            topic_bytes = effective_topic.encode("utf-8")
            with self._lock:
                if not self.socket:
                    raise RuntimeError("ZeroMQ套接字未初始化")
                self.socket.send_multipart([topic_bytes, payload_bytes], zmq.NOBLOCK)

            self.stats["messages_sent"] += 1
            self.stats["bytes_sent"] += len(payload_bytes)
            self.stats["last_message_time"] = datetime.utcnow().isoformat()
            return True

        except zmq.Again:
            self.stats["messages_failed"] += 1
            self.logger.warning("消息发布失败：发送缓冲区满")
            return False
        except Exception as e:
            self.stats["messages_failed"] += 1
            self.logger.error(f"消息发布失败: {e}")
            if "Connection" in str(e) or "Socket operation" in str(e):
                self._connected = False
            return False

    def process_retry_queue(self) -> int:
        """处理重试队列

        Returns:
            成功重试的消息数量
        """
        if not self._message_queue:
            return 0

        success_count = 0
        failed_messages = []

        for message_data in self._message_queue:
            try:
                message = NewsMessage.from_dict(message_data)
                if self.publish_message(message, retry=False):
                    success_count += 1
                else:
                    failed_messages.append(message_data)
            except Exception as e:
                self.logger.error(f"重试消息失败: {e}")
                failed_messages.append(message_data)

        # 更新重试队列
        self._message_queue = failed_messages

        if success_count > 0:
            self.logger.info(f"重试队列处理完成: 成功 {success_count}, 失败 {len(failed_messages)}")

        return success_count

    def get_stats(self) -> Dict[str, Any]:
        """获取发布统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        stats.update(
            {
                "connected": self._connected,
                "running": self._running,
                "queue_size": len(self._message_queue),
                "host": self.host,
                "port": self.port,
                "topic": self.topic,
            }
        )
        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        status = "healthy" if self._connected and self._running else "unhealthy"

        return {
            "status": status,
            "connected": self._connected,
            "running": self._running,
            "messages_sent": self.stats["messages_sent"],
            "messages_failed": self.stats["messages_failed"],
            "connection_errors": self.stats["connection_errors"],
            "queue_size": len(self._message_queue),
            "last_message_time": self.stats["last_message_time"],
        }

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except:
            pass


if __name__ == "__main__":
    # 测试ZeroMQ发布者
    import uuid
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建发布者
    publisher = ZMQPublisher(config, logger)

    try:
        # 连接
        if publisher.connect():
            # 创建测试消息
            test_message = NewsMessage(
                id=str(uuid.uuid4()),
                title="测试新闻标题",
                content="这是一条测试新闻内容，用于验证ZeroMQ发布功能。",
                source="test_source",
                url="https://example.com/news/1",
                timestamp=datetime.utcnow().isoformat(),
                category="test",
                sentiment=0.5,
                keywords=["测试", "新闻", "ZeroMQ"],
                metadata={"test": True},
            )

            # 发布消息
            success = publisher.publish_message(test_message)
            print(f"消息发布结果: {success}")

            # 显示统计信息
            stats = publisher.get_stats()
            print(f"发布统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

            # 健康检查
            health = publisher.health_check()
            print(f"健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")

        else:
            print("发布者连接失败")

    finally:
        publisher.disconnect()
