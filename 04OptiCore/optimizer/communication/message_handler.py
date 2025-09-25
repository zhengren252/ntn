#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息处理器
NeuroTrade Nexus (NTN) - Message Handler

核心功能：
1. ZeroMQ消息路由和分发
2. 消息格式验证和转换
3. 消息队列管理
4. 异步消息处理
5. 消息持久化和恢复
6. 错误处理和重试机制

遵循NeuroTrade Nexus核心设计理念：
- 消息总线：统一的消息处理中心
- 异步处理：高性能的消息处理
- 可靠性：消息确认和重试机制
- 可扩展性：支持多种消息类型
"""

import asyncio
import gzip
import json
import logging
import pickle
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


@dataclass
class MessageHandlerConfig:
    """消息处理器配置"""

    max_queue_size: int = 10000
    batch_size: int = 100
    processing_timeout: int = 30
    cleanup_interval: int = 300
    enable_compression: bool = True
    compression_threshold: int = 1024


@dataclass
class MessageHandlerState:
    """消息处理器状态"""

    is_running: bool = False
    processing_task: Optional[asyncio.Task] = None
    cleanup_task: Optional[asyncio.Task] = None
    retry_task: Optional[asyncio.Task] = None
    shutdown_event: Optional[asyncio.Event] = None

    def __post_init__(self):
        if self.shutdown_event is None:
            self.shutdown_event = asyncio.Event()


class MessageType(Enum):
    """消息类型枚举"""

    TRADING_OPPORTUNITY = "trading_opportunity"
    STRATEGY_PACKAGE = "strategy_package"
    BACKTEST_REQUEST = "backtest_request"
    BACKTEST_RESULT = "backtest_result"
    OPTIMIZATION_REQUEST = "optimization_request"
    OPTIMIZATION_RESULT = "optimization_result"
    DECISION_REQUEST = "decision_request"
    DECISION_RESULT = "decision_result"
    HEALTH_CHECK = "health_check"
    ERROR_NOTIFICATION = "error_notification"
    SYSTEM_STATUS = "system_status"


class MessagePriority(Enum):
    """消息优先级枚举"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageStatus(Enum):
    """消息状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"


@dataclass
class Message:
    """消息数据结构"""

    message_id: str
    message_type: MessageType
    source: str
    destination: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.expires_at is None:
            # 默认消息有效期为1小时
            self.expires_at = self.timestamp + timedelta(hours=1)

    def is_expired(self) -> bool:
        """检查消息是否过期"""
        return datetime.now() > self.expires_at

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "source": self.source,
            "destination": self.destination,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "status": self.status.value,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息对象"""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            source=data["source"],
            destination=data["destination"],
            payload=data["payload"],
            priority=MessagePriority(data["priority"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            status=MessageStatus(data.get("status", "pending")),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
        )


@dataclass
class MessageHandlerStats:
    """消息处理器统计信息"""

    total_messages_received: int = 0
    total_messages_sent: int = 0
    total_messages_processed: int = 0
    total_messages_failed: int = 0
    total_messages_retried: int = 0
    total_messages_expired: int = 0
    average_processing_time: float = 0.0
    queue_size: int = 0
    active_handlers: int = 0
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class MessageHandler:
    """
    消息处理器

    负责整个策略优化模组的消息路由、处理和管理
    """

    def __init__(self, config: Dict[str, Any]):
        # 初始化配置
        self.config = MessageHandlerConfig(
            max_queue_size=config.get("max_queue_size", 10000),
            batch_size=config.get("batch_size", 100),
            processing_timeout=config.get("processing_timeout", 30),
            cleanup_interval=config.get("cleanup_interval", 300),
            enable_compression=config.get("enable_compression", True),
            compression_threshold=config.get("compression_threshold", 1024),
        )

        # 初始化状态
        self.state = MessageHandlerState()

        self.logger = logging.getLogger(__name__)

        # 消息队列（按优先级分组）
        self.message_queues = {
            MessagePriority.CRITICAL: deque(),
            MessagePriority.HIGH: deque(),
            MessagePriority.NORMAL: deque(),
            MessagePriority.LOW: deque(),
        }

        # 消息处理器注册表
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)

        # 消息状态跟踪
        self.pending_messages: Dict[str, Message] = {}
        self.processing_messages: Dict[str, Message] = {}
        self.completed_messages: Dict[str, Message] = {}
        self.failed_messages: Dict[str, Message] = {}

        # 重试队列
        self.retry_queue: deque = deque()

        # 统计信息
        self.stats = MessageHandlerStats()

        self.logger.info("消息处理器初始化完成")

    async def start(self):
        """
        启动消息处理器
        """
        if self.state.is_running:
            self.logger.warning("消息处理器已在运行")
            return

        self.state.is_running = True
        self.state.shutdown_event.clear()

        # 启动异步任务
        self.state.processing_task = asyncio.create_task(
            self._message_processing_loop()
        )
        self.state.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.state.retry_task = asyncio.create_task(self._retry_loop())

        self.logger.info("消息处理器已启动")

    async def stop(self):
        """
        停止消息处理器
        """
        if not self.state.is_running:
            return

        self.state.is_running = False
        self.state.shutdown_event.set()

        # 等待异步任务完成
        tasks = [
            self.state.processing_task,
            self.state.cleanup_task,
            self.state.retry_task,
        ]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.logger.info("消息处理器已停止")

    def register_handler(self, message_type: MessageType, handler: Callable):
        """
        注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[message_type].append(handler)
        self.logger.info(f"已注册 {message_type.value} 消息处理器")

    def unregister_handler(self, message_type: MessageType, handler: Callable):
        """
        取消注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        if handler in self.message_handlers[message_type]:
            self.message_handlers[message_type].remove(handler)
            self.logger.info(f"已取消注册 {message_type.value} 消息处理器")

    async def send_message(self, message: Message) -> bool:
        """
        发送消息

        Args:
            message: 要发送的消息

        Returns:
            bool: 发送是否成功
        """
        try:
            # 检查队列容量
            total_queue_size = sum(len(queue) for queue in self.message_queues.values())
            if total_queue_size >= self.config.max_queue_size:
                self.logger.warning(f"消息队列已满，丢弃消息: {message.message_id}")
                return False

            # 检查消息是否过期
            if message.is_expired():
                self.logger.warning(f"消息已过期，丢弃消息: {message.message_id}")
                self.stats.total_messages_expired += 1
                return False

            # 添加到相应优先级队列
            self.message_queues[message.priority].append(message)
            self.pending_messages[message.message_id] = message

            self.stats.total_messages_sent += 1
            self.stats.queue_size = total_queue_size + 1

            self.logger.debug(f"消息已加入队列: {message.message_id}")
            return True

        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False

    async def receive_message(
        self, raw_message: Union[str, bytes, Dict[str, Any]]
    ) -> bool:
        """
        接收消息

        Args:
            raw_message: 原始消息数据

        Returns:
            bool: 接收是否成功
        """
        try:
            # 解析消息
            message = await self._parse_message(raw_message)
            if not message:
                return False

            # 发送到处理队列
            success = await self.send_message(message)
            if success:
                self.stats.total_messages_received += 1

            return success

        except Exception as e:
            self.logger.error(f"接收消息失败: {e}")
            return False

    async def _parse_message(
        self, raw_message: Union[str, bytes, Dict[str, Any]]
    ) -> Optional[Message]:
        """
        解析原始消息

        Args:
            raw_message: 原始消息数据

        Returns:
            Optional[Message]: 解析后的消息对象
        """
        try:
            # 处理不同格式的输入
            if isinstance(raw_message, bytes):
                # 尝试解压缩
                if self.config.enable_compression and len(raw_message) > 10:
                    try:
                        raw_message = gzip.decompress(raw_message)
                    except gzip.BadGzipFile:
                        pass  # 不是压缩数据，继续处理

                # 尝试反序列化
                try:
                    data = pickle.loads(raw_message)
                except (pickle.UnpicklingError, pickle.PickleError):
                    data = json.loads(raw_message.decode("utf-8"))

            elif isinstance(raw_message, str):
                data = json.loads(raw_message)
            elif isinstance(raw_message, dict):
                data = raw_message
            else:
                self.logger.error(f"不支持的消息格式: {type(raw_message)}")
                return None

            # 验证消息格式
            if not self._validate_message_format(data):
                return None

            # 创建消息对象
            message = Message.from_dict(data)
            return message

        except Exception as e:
            self.logger.error(f"解析消息失败: {e}")
            return None

    def _validate_message_format(self, data: Dict[str, Any]) -> bool:
        """
        验证消息格式

        Args:
            data: 消息数据

        Returns:
            bool: 格式是否有效
        """
        required_fields = [
            "message_id",
            "message_type",
            "source",
            "destination",
            "payload",
        ]

        for field in required_fields:
            if field not in data:
                self.logger.error(f"消息缺少必需字段: {field}")
                return False

        # 验证消息类型
        try:
            MessageType(data["message_type"])
        except ValueError:
            self.logger.error(f"无效的消息类型: {data['message_type']}")
            return False

        return True

    async def _message_processing_loop(self):
        """
        消息处理循环
        """
        self.logger.info("消息处理循环已启动")

        while self.state.is_running:
            try:
                # 按优先级处理消息
                message = await self._get_next_message()
                if message:
                    await self._process_message(message)
                else:
                    # 没有消息时短暂休眠
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"消息处理循环错误: {e}")
                await asyncio.sleep(1)

        self.logger.info("消息处理循环已停止")

    async def _get_next_message(self) -> Optional[Message]:
        """
        获取下一个要处理的消息（按优先级）

        Returns:
            Optional[Message]: 下一个消息
        """
        # 按优先级顺序检查队列
        for priority in [
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW,
        ]:
            queue = self.message_queues[priority]
            if queue:
                message = queue.popleft()

                # 检查消息是否过期
                if message.is_expired():
                    self.logger.warning(f"消息已过期: {message.message_id}")
                    self._move_message_to_failed(message, "消息过期")
                    self.stats.total_messages_expired += 1
                    continue

                return message

        return None

    async def _process_message(self, message: Message):
        """
        处理单个消息

        Args:
            message: 要处理的消息
        """
        start_time = time.time()

        try:
            # 更新消息状态
            message.status = MessageStatus.PROCESSING
            self._move_message_to_processing(message)

            # 获取消息处理器
            handlers = self.message_handlers.get(message.message_type, [])
            if not handlers:
                self.logger.warning(f"没有找到 {message.message_type.value} 类型的处理器")
                self._move_message_to_failed(message, "没有找到处理器")
                return

            # 执行所有处理器
            success = True
            for handler in handlers:
                try:
                    # 设置处理超时
                    result = await asyncio.wait_for(
                        handler(message), timeout=self.config.processing_timeout
                    )

                    if result is False:
                        success = False
                        break

                except asyncio.TimeoutError:
                    self.logger.error(f"消息处理超时: {message.message_id}")
                    success = False
                    break
                except Exception as e:
                    self.logger.error(f"消息处理器执行失败: {e}")
                    success = False
                    break

            # 更新处理结果
            if success:
                message.status = MessageStatus.COMPLETED
                self._move_message_to_completed(message)
                self.stats.total_messages_processed += 1
            else:
                # 检查是否可以重试
                if message.can_retry():
                    message.retry_count += 1
                    message.status = MessageStatus.RETRY
                    self.retry_queue.append(message)
                    self.stats.total_messages_retried += 1
                    self.logger.info(
                        f"消息将重试: {message.message_id} (第{message.retry_count}次)"
                    )
                else:
                    self._move_message_to_failed(message, "处理失败且超过最大重试次数")

        except Exception as e:
            self.logger.error(f"处理消息时发生错误: {e}")
            self._move_message_to_failed(message, str(e))

        finally:
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_average_processing_time(processing_time)

    def _move_message_to_processing(self, message: Message):
        """
        将消息移动到处理中状态
        """
        if message.message_id in self.pending_messages:
            del self.pending_messages[message.message_id]
        self.processing_messages[message.message_id] = message

    def _move_message_to_completed(self, message: Message):
        """
        将消息移动到已完成状态
        """
        if message.message_id in self.processing_messages:
            del self.processing_messages[message.message_id]
        self.completed_messages[message.message_id] = message

    def _move_message_to_failed(self, message: Message, reason: str):
        """
        将消息移动到失败状态
        """
        message.status = MessageStatus.FAILED

        if message.message_id in self.pending_messages:
            del self.pending_messages[message.message_id]
        if message.message_id in self.processing_messages:
            del self.processing_messages[message.message_id]

        self.failed_messages[message.message_id] = message
        self.stats.total_messages_failed += 1

        self.logger.error(f"消息处理失败: {message.message_id}, 原因: {reason}")

    def _update_average_processing_time(self, processing_time: float):
        """
        更新平均处理时间
        """
        if self.stats.total_messages_processed == 0:
            self.stats.average_processing_time = processing_time
        else:
            # 使用指数移动平均
            alpha = 0.1
            self.stats.average_processing_time = (
                alpha * processing_time
                + (1 - alpha) * self.stats.average_processing_time
            )

    async def _retry_loop(self):
        """
        重试循环
        """
        self.logger.info("重试循环已启动")

        while self.state.is_running:
            try:
                if self.retry_queue:
                    message = self.retry_queue.popleft()

                    # 等待一段时间后重试（指数退避）
                    delay = min(2**message.retry_count, 60)  # 最大60秒
                    await asyncio.sleep(delay)

                    # 重新加入处理队列
                    await self.send_message(message)
                else:
                    await asyncio.sleep(5)  # 没有重试消息时休眠5秒

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"重试循环错误: {e}")
                await asyncio.sleep(1)

        self.logger.info("重试循环已停止")

    async def _cleanup_loop(self):
        """
        清理循环
        """
        self.logger.info("清理循环已启动")

        while self.state.is_running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_old_messages()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理循环错误: {e}")

        self.logger.info("清理循环已停止")

    async def _cleanup_old_messages(self):
        """
        清理过期消息
        """
        current_time = datetime.now()
        cleanup_threshold = current_time - timedelta(hours=1)  # 清理1小时前的消息

        # 清理已完成的消息
        completed_to_remove = []
        for message_id, message in self.completed_messages.items():
            if message.timestamp < cleanup_threshold:
                completed_to_remove.append(message_id)

        for message_id in completed_to_remove:
            del self.completed_messages[message_id]

        # 清理失败的消息
        failed_to_remove = []
        for message_id, message in self.failed_messages.items():
            if message.timestamp < cleanup_threshold:
                failed_to_remove.append(message_id)

        for message_id in failed_to_remove:
            del self.failed_messages[message_id]

        if completed_to_remove or failed_to_remove:
            self.logger.info(
                f"清理了 {len(completed_to_remove)} 个已完成消息和 {len(failed_to_remove)} 个失败消息"
            )

    async def serialize_message(self, message: Message) -> bytes:
        """
        序列化消息

        Args:
            message: 要序列化的消息

        Returns:
            bytes: 序列化后的数据
        """
        try:
            # 转换为字典
            data = message.to_dict()

            # 序列化
            serialized = pickle.dumps(data)

            # 压缩（如果启用且数据足够大）
            if (
                self.config.enable_compression
                and len(serialized) > self.config.compression_threshold
            ):
                serialized = gzip.compress(serialized)

            return serialized

        except Exception as e:
            self.logger.error(f"序列化消息失败: {e}")
            raise

    async def get_message_status(self, message_id: str) -> Optional[MessageStatus]:
        """
        获取消息状态

        Args:
            message_id: 消息ID

        Returns:
            Optional[MessageStatus]: 消息状态
        """
        # 检查各个状态字典
        if message_id in self.pending_messages:
            return MessageStatus.PENDING
        elif message_id in self.processing_messages:
            return MessageStatus.PROCESSING
        elif message_id in self.completed_messages:
            return MessageStatus.COMPLETED
        elif message_id in self.failed_messages:
            return MessageStatus.FAILED
        else:
            return None

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态

        Returns:
            Dict[str, Any]: 队列状态信息
        """
        return {
            "queue_sizes": {
                priority.name: len(queue)
                for priority, queue in self.message_queues.items()
            },
            "pending_messages": len(self.pending_messages),
            "processing_messages": len(self.processing_messages),
            "completed_messages": len(self.completed_messages),
            "failed_messages": len(self.failed_messages),
            "retry_queue_size": len(self.retry_queue),
            "total_handlers": sum(
                len(handlers) for handlers in self.message_handlers.values()
            ),
            "is_running": self.state.is_running,
        }

    async def get_statistics(self) -> MessageHandlerStats:
        """
        获取统计信息

        Returns:
            MessageHandlerStats: 统计信息
        """
        # 更新当前队列大小
        self.stats.queue_size = sum(
            len(queue) for queue in self.message_queues.values()
        )
        self.stats.active_handlers = sum(
            len(handlers) for handlers in self.message_handlers.values()
        )
        self.stats.last_updated = datetime.now()

        return self.stats

    async def create_message(
        self,
        message_type: MessageType,
        source: str,
        destination: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        expires_in_seconds: Optional[int] = None,
    ) -> Message:
        """
        创建消息

        Args:
            message_type: 消息类型
            source: 消息源
            destination: 消息目标
            payload: 消息载荷
            priority: 消息优先级
            correlation_id: 关联ID
            reply_to: 回复地址
            expires_in_seconds: 过期时间（秒）

        Returns:
            Message: 创建的消息
        """
        message_id = str(uuid.uuid4())

        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)

        return Message(
            message_id=message_id,
            message_type=message_type,
            source=source,
            destination=destination,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to,
            expires_at=expires_at,
        )

    async def cleanup(self):
        """
        清理资源
        """
        await self.stop()

        # 清理所有消息队列
        for queue in self.message_queues.values():
            queue.clear()

        self.pending_messages.clear()
        self.processing_messages.clear()
        self.completed_messages.clear()
        self.failed_messages.clear()
        self.retry_queue.clear()

        self.logger.info("消息处理器清理完成")


def create_message_handler(config: Dict[str, Any]) -> MessageHandler:
    """
    创建消息处理器实例

    Args:
        config: 配置字典

    Returns:
        MessageHandler: 消息处理器实例
    """
    return MessageHandler(config)
