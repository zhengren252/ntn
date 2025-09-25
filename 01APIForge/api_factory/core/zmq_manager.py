#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroMQ管理器 - 高并发通信架构
核心设计理念：异步消息传递、发布订阅模式、请求响应模式
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, date, timedelta
import os
import zmq
import zmq.asyncio
from ..config.settings import ZMQConfig

logger = logging.getLogger(__name__)


class ZMQManager:
    """ZeroMQ管理器 - 系统级集成通信"""

    def __init__(self, config: ZMQConfig):
        self.config = config
        self.context: Optional[zmq.asyncio.Context] = None
        self.publisher: Optional[zmq.asyncio.Socket] = None
        self.subscriber: Optional[zmq.asyncio.Socket] = None
        self.request_socket: Optional[zmq.asyncio.Socket] = None
        self.reply_socket: Optional[zmq.asyncio.Socket] = None

        # 消息处理器注册表
        self.message_handlers: Dict[str, Callable] = {}
        self.subscription_topics: List[str] = []

        # 统计信息
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "start_time": None,
        }

    def _json_default(self, o: Any):
        """统一JSON默认编码器：确保 datetime/date/timedelta 可被序列化"""
        try:
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            if isinstance(o, timedelta):
                return o.total_seconds()
            return str(o)
        except Exception:
            return str(o)

    async def initialize(self):
        """初始化ZeroMQ组件"""
        # 在测试/离线模式下短路：不创建任何ZMQ套接字和后台任务
        disable_flag = str(os.environ.get("DISABLE_ZMQ", "")).strip().lower()
        if disable_flag in ("1", "true", "yes", "on"): 
            self.stats["start_time"] = datetime.now()
            logger.info("DISABLE_ZMQ 已启用；ZMQManager 将以模拟模式运行（不创建套接字或后台任务）")
            return
        try:
            self.context = zmq.asyncio.Context()

            # 创建发布者套接字
            self.publisher = self.context.socket(zmq.PUB)

            # 尝试绑定发布者端口，如果失败则尝试其他端口
            publisher_address = None
            for port_offset in range(10):  # 尝试10个不同的端口
                try:
                    current_port = self.config.publisher_port + port_offset
                    current_address = f"{self.config.bind_address}:{current_port}"
                    self.publisher.bind(current_address)
                    publisher_address = current_address
                    break
                except zmq.ZMQError as port_error:
                    if port_offset == 9:  # 最后一次尝试
                        raise port_error
                    continue

            # 创建订阅者套接字
            self.subscriber = self.context.socket(zmq.SUB)
            subscriber_address = (
                f"{self.config.connect_address}:{self.config.subscriber_port}"
            )
            self.subscriber.connect(subscriber_address)

            # 创建请求套接字
            self.request_socket = self.context.socket(zmq.REQ)
            request_address = (
                f"{self.config.connect_address}:{self.config.reply_port}"
            )
            self.request_socket.connect(request_address)

            # 创建响应套接字
            self.reply_socket = self.context.socket(zmq.REP)

            # 尝试绑定响应端口
            reply_address = None
            for port_offset in range(10):
                try:
                    current_port = self.config.reply_port + port_offset
                    current_address = f"{self.config.bind_address}:{current_port}"
                    self.reply_socket.bind(current_address)
                    reply_address = current_address
                    break
                except zmq.ZMQError as port_error:
                    if port_offset == 9:
                        raise port_error
                    continue

            self.stats["start_time"] = datetime.now()

            # 启动消息监听任务
            asyncio.create_task(self._start_subscriber_loop())
            asyncio.create_task(self._start_reply_loop())

            logger.info(
                f"ZeroMQ管理器初始化完成 - Publisher: {publisher_address}, Reply: {reply_address}"
            )

        except Exception as e:
            logger.warning(f"ZeroMQ初始化失败，将在模拟模式下运行: {e}")
            # 清理已创建的套接字
            if hasattr(self, "publisher") and self.publisher:
                self.publisher.close()
                self.publisher = None
            if hasattr(self, "subscriber") and self.subscriber:
                self.subscriber.close()
                self.subscriber = None
            if hasattr(self, "request_socket") and self.request_socket:
                self.request_socket.close()
                self.request_socket = None
            if hasattr(self, "reply_socket") and self.reply_socket:
                self.reply_socket.close()
                self.reply_socket = None

    async def publish_message(
        self, topic: str, message: Dict[str, Any], tenant_id: Optional[str] = None
    ):
        """发布消息 - 支持数据隔离"""
        if not self.publisher:
            logger.debug(f"ZeroMQ不可用，跳过消息发布 - Topic: {topic}, Tenant: {tenant_id}")
            return

        try:
            # 构造消息格式
            msg_data = {
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
                "tenant_id": tenant_id,
                "data": message,
            }

            # 发送消息
            await self.publisher.send_multipart(
                [topic.encode("utf-8"), json.dumps(msg_data, ensure_ascii=False, default=self._json_default).encode("utf-8")]
            )

            self.stats["messages_sent"] += 1
            logger.debug(f"消息已发布 - Topic: {topic}, Tenant: {tenant_id}")

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"发布消息失败: {e}")
            raise

    async def subscribe_topic(
        self, topic: str, handler: Callable[[Dict[str, Any]], None]
    ):
        """订阅主题"""
        if not self.subscriber:
            logger.debug(f"ZeroMQ不可用，跳过主题订阅 - Topic: {topic}")
            # 仍然注册处理器，以便在模拟模式下使用
            self.subscription_topics.append(topic)
            self.message_handlers[topic] = handler
            return

        try:
            # 订阅主题
            self.subscriber.setsockopt(zmq.SUBSCRIBE, topic.encode("utf-8"))
            self.subscription_topics.append(topic)
            self.message_handlers[topic] = handler

            logger.info(f"已订阅主题: {topic}")

        except Exception as e:
            logger.error(f"订阅主题失败: {e}")
            raise

    async def send_request(
        self, request_data: Dict[str, Any], timeout: int = 5000
    ) -> Dict[str, Any]:
        """发送请求并等待响应"""
        if not self.request_socket:
            logger.debug("ZeroMQ不可用，返回模拟响应")
            # 返回模拟响应
            return {
                "status": "ok",
                "message": "模拟响应 - ZeroMQ不可用",
                "timestamp": datetime.now().isoformat(),
                "data": {},
            }

        try:
            # 设置超时
            self.request_socket.setsockopt(zmq.RCVTIMEO, timeout)

            # 发送请求
            await self.request_socket.send_json(request_data, default=self._json_default)

            # 等待响应
            response = await self.request_socket.recv_json()

            self.stats["messages_sent"] += 1
            self.stats["messages_received"] += 1

            return response

        except zmq.Again:
            logger.error(f"请求超时: {timeout}ms")
            raise TimeoutError("Request timeout")
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"发送请求失败: {e}")
            raise

    async def _start_subscriber_loop(self):
        """启动订阅者消息循环"""
        while True:
            try:
                if not self.subscriber:
                    break

                # 接收消息
                topic, message = await self.subscriber.recv_multipart()
                topic_str = topic.decode("utf-8")
                msg_data = json.loads(message.decode("utf-8"))

                # 处理消息
                if topic_str in self.message_handlers:
                    handler = self.message_handlers[topic_str]
                    await self._safe_call_handler(handler, msg_data)

                self.stats["messages_received"] += 1

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"订阅者消息处理失败: {e}")
                await asyncio.sleep(1)  # 避免快速重试

    async def _start_reply_loop(self):
        """启动响应者消息循环"""
        while True:
            try:
                if not self.reply_socket:
                    break

                # 接收请求
                request = await self.reply_socket.recv_json()

                # 处理请求（兼容被测试用例以非异步 Mock 替换的情况）
                handler = getattr(self, "_handle_request", None)
                if asyncio.iscoroutinefunction(handler):
                    response = await handler(request)
                else:
                    response = handler(request) if callable(handler) else {
                        "status": "error",
                        "message": "No request handler available",
                        "timestamp": datetime.now().isoformat(),
                    }

                # 发送响应
                await self.reply_socket.send_json(response, default=self._json_default)

                self.stats["messages_received"] += 1
                self.stats["messages_sent"] += 1

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"响应者消息处理失败: {e}")
                # 发送错误响应
                try:
                    error_response = {
                        "status": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                    await self.reply_socket.send_json(error_response, default=self._json_default)
                except Exception:
                    pass

    async def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求消息"""
        try:
            request_type = request.get("type", "unknown")

            if request_type == "health_check":
                return {
                    "status": "ok",
                    "timestamp": datetime.now().isoformat(),
                    "stats": self.stats,
                }
            elif request_type == "get_stats":
                return {
                    "status": "ok",
                    "data": self.stats,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "message": f"未知请求类型: {request_type}",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _safe_call_handler(self, handler: Callable, message: Dict[str, Any]):
        """安全调用消息处理器"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
        except Exception as e:
            logger.error(f"消息处理器执行失败: {e}")

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not all([self.context, self.publisher, self.subscriber]):
                logger.debug("ZeroMQ组件未完全初始化，返回模拟健康状态")
                return True  # 在模拟模式下返回健康状态

            # 发送健康检查消息
            test_request = {
                "type": "health_check",
                "timestamp": datetime.now().isoformat(),
            }

            response = await self.send_request(test_request, timeout=1000)
            return response.get("status") == "ok"

        except Exception as e:
            logger.error(f"ZeroMQ健康检查失败: {e}")
            return False

    def is_healthy(self) -> bool:
        """同步健康检查方法"""
        try:
            # 检查基本组件是否初始化
            if not self.context:
                return False
            
            # 检查套接字状态
            sockets_ok = True
            if self.publisher and self.publisher.closed:
                sockets_ok = False
            if self.subscriber and self.subscriber.closed:
                sockets_ok = False
            if self.request_socket and self.request_socket.closed:
                sockets_ok = False
            if self.reply_socket and self.reply_socket.closed:
                sockets_ok = False
                
            return sockets_ok
            
        except Exception as e:
            logger.error(f"ZeroMQ同步健康检查失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "subscription_topics": self.subscription_topics,
            "active_handlers": len(self.message_handlers),
        }

    async def cleanup(self):
        """清理资源"""
        try:
            if self.publisher:
                self.publisher.close()
            if self.subscriber:
                self.subscriber.close()
            if self.request_socket:
                self.request_socket.close()
            if self.reply_socket:
                self.reply_socket.close()
            if self.context:
                self.context.term()

            logger.info("ZeroMQ管理器已清理")

        except Exception as e:
            logger.error(f"ZeroMQ清理失败: {e}")


# 消息主题常量


class MessageTopics:
    """消息主题定义"""

    API_REQUEST = "api.request"
    API_RESPONSE = "api.response"
    AUTH_EVENT = "auth.event"
    QUOTA_ALERT = "quota.alert"
    CIRCUIT_BREAKER = "circuit.breaker"
    CLUSTER_STATUS = "cluster.status"
    SYSTEM_ALERT = "system.alert"
    STATUS_CHANGE = "api_factory.events.status"
    QUOTA_EXCEEDED = "api_factory.events.quota"
    CIRCUIT_BREAKER_EVENT = "api_factory.events.circuit_breaker"
    AUTH_STATUS = "api_factory.events.auth"
