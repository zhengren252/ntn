# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - ZeroMQ消息处理器
统一处理消息路由、分发和业务逻辑
"""

import sys
import os
import json
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

from ..config import ConfigManager
from ..utils import Logger
from .publisher import NewsMessage


class MessageType(Enum):
    """消息类型枚举"""

    NEWS = "news"
    ALERT = "alert"
    SIGNAL = "signal"
    HEARTBEAT = "heartbeat"
    CONTROL = "control"


class MessagePriority(Enum):
    """消息优先级枚举"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ProcessingResult:
    """消息处理结果"""

    success: bool
    message_id: str
    processing_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseMessageHandler(ABC):
    """消息处理器基类"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger
        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "total_processing_time": 0.0,
            "last_processed_time": None,
        }

    @abstractmethod
    def can_handle(self, message: NewsMessage) -> bool:
        """检查是否可以处理该消息"""
        pass

    @abstractmethod
    def process(self, message: NewsMessage) -> ProcessingResult:
        """处理消息"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return self.stats.copy()


class NewsMessageHandler(BaseMessageHandler):
    """新闻消息处理器"""

    def can_handle(self, message: NewsMessage) -> bool:
        """检查是否为新闻消息"""
        return message.category in ["news", "financial", "crypto", "market"]

    def process(self, message: NewsMessage) -> ProcessingResult:
        """处理新闻消息"""
        start_time = time.time()

        try:
            # 验证消息内容
            if not self._validate_message(message):
                raise ValueError("消息验证失败")

            # 提取关键信息
            keywords = self._extract_keywords(message.content)
            sentiment = self._analyze_sentiment(message.content)

            # 更新消息
            message.keywords.extend(keywords)
            if message.sentiment is None:
                message.sentiment = sentiment

            # 存储到数据库
            self._store_message(message)

            # 更新统计
            processing_time = time.time() - start_time
            self.stats["messages_processed"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["last_processed_time"] = datetime.utcnow().isoformat()

            self.logger.info(
                f"新闻消息处理成功: {message.id} | "
                f"来源: {message.source} | "
                f"耗时: {processing_time:.3f}s"
            )

            return ProcessingResult(
                success=True,
                message_id=message.id,
                processing_time=processing_time,
                metadata={
                    "keywords_count": len(keywords),
                    "sentiment": sentiment,
                    "source": message.source,
                },
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.stats["messages_failed"] += 1

            self.logger.error(
                f"新闻消息处理失败: {message.id} | " f"错误: {e} | " f"耗时: {processing_time:.3f}s"
            )

            return ProcessingResult(
                success=False,
                message_id=message.id,
                processing_time=processing_time,
                error=str(e),
            )

    def _validate_message(self, message: NewsMessage) -> bool:
        """验证消息内容"""
        # 检查必需字段
        if not message.title or not message.content:
            return False

        # 检查内容长度
        if len(message.content) < 10 or len(message.content) > 100000:
            return False

        # 检查时间戳格式
        try:
            datetime.fromisoformat(message.timestamp.replace("Z", "+00:00"))
        except ValueError:
            return False

        return True

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（实际应用中可使用NLP库）
        financial_keywords = [
            "bitcoin",
            "ethereum",
            "crypto",
            "blockchain",
            "trading",
            "market",
            "price",
            "bull",
            "bear",
            "support",
            "resistance",
            "volume",
            "analysis",
            "forecast",
            "signal",
            "breakout",
        ]

        content_lower = content.lower()
        found_keywords = []

        for keyword in financial_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _analyze_sentiment(self, content: str) -> float:
        """分析情感倾向"""
        # 简单的情感分析（实际应用中可使用ML模型）
        positive_words = ["bull", "up", "rise", "gain", "profit", "good", "positive"]
        negative_words = ["bear", "down", "fall", "loss", "bad", "negative", "crash"]

        content_lower = content.lower()

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        total_count = positive_count + negative_count

        if total_count == 0:
            return 0.0  # 中性

        return (positive_count - negative_count) / total_count

    def _store_message(self, message: NewsMessage) -> None:
        """存储消息到数据库"""
        # 这里应该实现数据库存储逻辑
        # 暂时只记录日志
        self.logger.debug(f"存储消息: {message.id} | 标题: {message.title}")


class AlertMessageHandler(BaseMessageHandler):
    """告警消息处理器"""

    def can_handle(self, message: NewsMessage) -> bool:
        """检查是否为告警消息"""
        return message.category == "alert" or "alert" in message.keywords

    def process(self, message: NewsMessage) -> ProcessingResult:
        """处理告警消息"""
        start_time = time.time()

        try:
            # 确定告警级别
            priority = self._determine_priority(message)

            # 发送通知
            self._send_notification(message, priority)

            # 记录告警
            self._log_alert(message, priority)

            processing_time = time.time() - start_time
            self.stats["messages_processed"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["last_processed_time"] = datetime.utcnow().isoformat()

            self.logger.warning(
                f"告警消息处理: {message.id} | "
                f"优先级: {priority.name} | "
                f"耗时: {processing_time:.3f}s"
            )

            return ProcessingResult(
                success=True,
                message_id=message.id,
                processing_time=processing_time,
                metadata={"priority": priority.name, "alert_type": "market_alert"},
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.stats["messages_failed"] += 1

            self.logger.error(f"告警消息处理失败: {message.id} | 错误: {e}")

            return ProcessingResult(
                success=False,
                message_id=message.id,
                processing_time=processing_time,
                error=str(e),
            )

    def _determine_priority(self, message: NewsMessage) -> MessagePriority:
        """确定告警优先级"""
        content_lower = message.content.lower()

        if any(word in content_lower for word in ["crash", "emergency", "critical"]):
            return MessagePriority.CRITICAL
        elif any(word in content_lower for word in ["warning", "alert", "important"]):
            return MessagePriority.HIGH
        elif any(word in content_lower for word in ["notice", "update"]):
            return MessagePriority.NORMAL
        else:
            return MessagePriority.LOW

    def _send_notification(
        self, message: NewsMessage, priority: MessagePriority
    ) -> None:
        """发送通知"""
        # 这里应该实现通知发送逻辑（邮件、短信、Webhook等）
        self.logger.info(f"发送告警通知: {message.title} | 优先级: {priority.name}")

    def _log_alert(self, message: NewsMessage, priority: MessagePriority) -> None:
        """记录告警日志"""
        alert_log = {
            "id": message.id,
            "title": message.title,
            "source": message.source,
            "priority": priority.name,
            "timestamp": message.timestamp,
            "content_preview": message.content[:200],
        }

        self.logger.warning(f"告警记录: {json.dumps(alert_log, ensure_ascii=False)}")


class MessageHandler:
    """主消息处理器

    负责消息路由和分发到具体的处理器
    """

    def __init__(self, config: ConfigManager, logger: Logger = None):
        """初始化消息处理器

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or Logger(config)

        # 注册处理器
        self.handlers: List[BaseMessageHandler] = [
            NewsMessageHandler(config, self.logger),
            AlertMessageHandler(config, self.logger),
        ]

        # 统计信息
        self.stats = {
            "total_messages": 0,
            "successful_messages": 0,
            "failed_messages": 0,
            "unhandled_messages": 0,
            "total_processing_time": 0.0,
            "last_message_time": None,
        }

        self.logger.info(f"消息处理器初始化完成，注册 {len(self.handlers)} 个处理器")

    def handle_message(self, message: NewsMessage) -> ProcessingResult:
        """处理消息

        Args:
            message: 要处理的消息

        Returns:
            处理结果
        """
        start_time = time.time()
        self.stats["total_messages"] += 1
        self.stats["last_message_time"] = datetime.utcnow().isoformat()

        try:
            # 查找合适的处理器
            handler = self._find_handler(message)

            if handler:
                # 处理消息
                result = handler.process(message)

                # 更新统计
                processing_time = time.time() - start_time
                self.stats["total_processing_time"] += processing_time

                if result.success:
                    self.stats["successful_messages"] += 1
                else:
                    self.stats["failed_messages"] += 1

                return result
            else:
                # 没有找到合适的处理器
                self.stats["unhandled_messages"] += 1

                self.logger.warning(
                    f"未找到合适的处理器: {message.id} | "
                    f"类别: {message.category} | "
                    f"来源: {message.source}"
                )

                return ProcessingResult(
                    success=False,
                    message_id=message.id,
                    processing_time=time.time() - start_time,
                    error="未找到合适的处理器",
                )

        except Exception as e:
            processing_time = time.time() - start_time
            self.stats["failed_messages"] += 1
            self.stats["total_processing_time"] += processing_time

            self.logger.error(f"消息处理异常: {message.id} | 错误: {e}")

            return ProcessingResult(
                success=False,
                message_id=message.id,
                processing_time=processing_time,
                error=str(e),
            )

    def _find_handler(self, message: NewsMessage) -> Optional[BaseMessageHandler]:
        """查找合适的处理器

        Args:
            message: 消息对象

        Returns:
            合适的处理器或None
        """
        for handler in self.handlers:
            if handler.can_handle(message):
                return handler

        return None

    def register_handler(self, handler: BaseMessageHandler) -> None:
        """注册新的处理器

        Args:
            handler: 处理器实例
        """
        self.handlers.append(handler)
        self.logger.info(f"注册新处理器: {handler.__class__.__name__}")

    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()

        # 添加处理器统计
        handler_stats = {}
        for i, handler in enumerate(self.handlers):
            handler_name = handler.__class__.__name__
            handler_stats[handler_name] = handler.get_stats()

        stats["handlers"] = handler_stats
        stats["handler_count"] = len(self.handlers)

        # 计算平均处理时间
        if self.stats["total_messages"] > 0:
            stats["avg_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["total_messages"]
            )
        else:
            stats["avg_processing_time"] = 0.0

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        total_messages = self.stats["total_messages"]
        success_rate = 0.0

        if total_messages > 0:
            success_rate = self.stats["successful_messages"] / total_messages

        status = (
            "healthy"
            if success_rate >= 0.9
            else "degraded"
            if success_rate >= 0.7
            else "unhealthy"
        )

        return {
            "status": status,
            "success_rate": success_rate,
            "total_messages": total_messages,
            "successful_messages": self.stats["successful_messages"],
            "failed_messages": self.stats["failed_messages"],
            "unhandled_messages": self.stats["unhandled_messages"],
            "handler_count": len(self.handlers),
            "last_message_time": self.stats["last_message_time"],
        }


if __name__ == "__main__":
    # 测试消息处理器
    import uuid
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建消息处理器
    handler = MessageHandler(config, logger)

    # 创建测试消息
    test_messages = [
        NewsMessage(
            id=str(uuid.uuid4()),
            title="Bitcoin价格突破新高",
            content="比特币价格今日突破历史新高，市场情绪乐观，交易量大幅增加。",
            source="crypto_news",
            url="https://example.com/news/1",
            timestamp=datetime.utcnow().isoformat(),
            category="crypto",
            sentiment=None,
            keywords=["bitcoin", "price"],
            metadata={"test": True},
        ),
        NewsMessage(
            id=str(uuid.uuid4()),
            title="市场告警：异常波动",
            content="检测到市场异常波动，请注意风险控制。这是一个重要的告警信息。",
            source="alert_system",
            url=None,
            timestamp=datetime.utcnow().isoformat(),
            category="alert",
            sentiment=None,
            keywords=["alert", "warning"],
            metadata={"test": True},
        ),
    ]

    # 处理测试消息
    for message in test_messages:
        result = handler.handle_message(message)
        print(f"处理结果: {result.success} | 消息ID: {result.message_id}")
        if result.error:
            print(f"错误: {result.error}")

    # 显示统计信息
    stats = handler.get_stats()
    print(f"\n处理统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    # 健康检查
    health = handler.health_check()
    print(f"\n健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
