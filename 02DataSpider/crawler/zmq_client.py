# ZeroMQ通信客户端
# 严格遵循：系统级集成流程和通信协议规范

import zmq
import json
import time
from typing import Dict, Any, Optional, Callable
from loguru import logger
from .config_manager import config

SCHEMA_VERSION = "1.0"
ZMQ_TOPICS = {"crawler_news": "crawler.news", "system_status": "system.status"}


class ZMQClient:
    """ZeroMQ通信客户端 - 实现发布/订阅和请求/响应模式"""

    def __init__(self):
        self.context = zmq.Context()
        self.publisher = None
        self.subscriber = None
        self.requester = None
        self.responder = None

        # 获取配置
        self.zmq_config = config.get_zmq_config()
        self.publisher_port = self.zmq_config["publisher_port"]
        self.request_port = self.zmq_config["request_port"]
        self.topics = self.zmq_config["topics"]

        logger.info("ZeroMQ客户端初始化完成")

    def setup_publisher(self) -> None:
        """设置发布者"""
        if not self.publisher:
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(f"tcp://*:{self.publisher_port}")
            logger.info(f"发布者绑定到端口 {self.publisher_port}")

    def setup_subscriber(self, topics: list = None) -> None:
        """设置订阅者"""
        if not self.subscriber:
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(f"tcp://localhost:{self.publisher_port}")

            # 订阅指定主题
            topics = topics or list(self.topics.values())
            for topic in topics:
                self.subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
                logger.info(f"订阅主题: {topic}")

    def publish_message(self, topic: str, data: Dict[str, Any]) -> bool:
        """发布消息"""
        try:
            if not self.publisher:
                self.setup_publisher()

            message = {
                "topic": topic,
                "timestamp": time.time(),
                "schema_version": SCHEMA_VERSION,
                "data": data,
            }

            message_str = json.dumps(message, ensure_ascii=False)
            self.publisher.send_string(f"{topic} {message_str}")

            logger.debug(f"发布消息到主题 {topic}: {len(message_str)} 字节")
            return True

        except Exception as e:
            logger.error(f"发布消息失败: {e}")
            return False

    def receive_message(self, timeout: int = 1000) -> Optional[Dict[str, Any]]:
        """接收消息"""
        try:
            if not self.subscriber:
                logger.warning("订阅者未初始化")
                return None

            # 设置超时
            self.subscriber.setsockopt(zmq.RCVTIMEO, timeout)

            message = self.subscriber.recv_string()
            topic, data = message.split(" ", 1)

            return json.loads(data)

        except zmq.Again:
            # 超时
            return None
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
            return None

    def close(self):
        """关闭连接"""
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.requester:
            self.requester.close()
        if self.responder:
            self.responder.close()

        self.context.term()
        logger.info("ZeroMQ客户端已关闭")


# 全局客户端实例
zmq_client = ZMQClient()
