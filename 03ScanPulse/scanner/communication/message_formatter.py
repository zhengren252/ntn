# 消息格式化器
# 实现标准化的消息序列化和反序列化，遵循通信协议与接口规范

import json
import pickle
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class MessageType(Enum):
    """消息类型枚举"""

    SCAN_RESULT = "scan_result"
    OPPORTUNITY = "opportunity"
    NEWS_EVENT = "news_event"
    MARKET_DATA = "market_data"
    RULE_CONFIG = "rule_config"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


class SerializationFormat(Enum):
    """序列化格式枚举"""

    JSON = "json"
    PICKLE = "pickle"


@dataclass
class MessageHeader:
    """消息头部"""

    message_id: str
    message_type: str
    source: str
    timestamp: str
    schema_version: str = "1.1"
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class StandardMessage:
    """标准消息格式"""

    header: MessageHeader
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class MessageFormatter:
    """消息格式化器 - 实现标准化的消息处理"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # 配置参数
        self.default_format = SerializationFormat(config.get("default_format", "json"))
        self.schema_version = config.get("schema_version", "1.1")
        self.source_name = config.get("source_name", "scanner")
        self.enable_compression = config.get("enable_compression", False)
        self.max_message_size = config.get("max_message_size", 1024 * 1024)  # 1MB

        logger.info(
            "MessageFormatter initialized",
            default_format=self.default_format.value,
            schema_version=self.schema_version,
            source_name=self.source_name,
        )

    def create_scan_result_message(
        self,
        symbol: str,
        scan_result: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> StandardMessage:
        """创建扫描结果消息

        Args:
            symbol: 交易对符号
            scan_result: 扫描结果数据
            correlation_id: 关联ID

        Returns:
            标准消息对象
        """
        message_id = self._generate_message_id()

        header = MessageHeader(
            message_id=message_id,
            message_type=MessageType.SCAN_RESULT.value,
            source=self.source_name,
            timestamp=datetime.now().isoformat(),
            schema_version=self.schema_version,
            correlation_id=correlation_id,
        )

        payload = {
            "symbol": symbol,
            "scan_result": scan_result,
            "scan_timestamp": datetime.now().isoformat(),
        }

        metadata = {
            "symbol": symbol,
            "score": scan_result.get("score"),
            "rule_type": scan_result.get("rule_type"),
        }

        return StandardMessage(header=header, payload=payload, metadata=metadata)

    def create_opportunity_message(
        self, opportunity: Dict[str, Any], correlation_id: Optional[str] = None
    ) -> StandardMessage:
        """创建交易机会消息

        Args:
            opportunity: 交易机会数据
            correlation_id: 关联ID

        Returns:
            标准消息对象
        """
        message_id = self._generate_message_id()

        header = MessageHeader(
            message_id=message_id,
            message_type=MessageType.OPPORTUNITY.value,
            source=self.source_name,
            timestamp=datetime.now().isoformat(),
            schema_version=self.schema_version,
            correlation_id=correlation_id,
        )

        payload = {"opportunity": opportunity, "created_at": datetime.now().isoformat()}

        metadata = {
            "symbol": opportunity.get("symbol"),
            "type": opportunity.get("type"),
            "score": opportunity.get("score"),
            "priority": opportunity.get("priority", "normal"),
        }

        return StandardMessage(header=header, payload=payload, metadata=metadata)

    def create_news_event_message(
        self, news_event: Dict[str, Any], correlation_id: Optional[str] = None
    ) -> StandardMessage:
        """创建新闻事件消息

        Args:
            news_event: 新闻事件数据
            correlation_id: 关联ID

        Returns:
            标准消息对象
        """
        message_id = self._generate_message_id()

        header = MessageHeader(
            message_id=message_id,
            message_type=MessageType.NEWS_EVENT.value,
            source=self.source_name,
            timestamp=datetime.now().isoformat(),
            schema_version=self.schema_version,
            correlation_id=correlation_id,
        )

        payload = {"news_event": news_event, "processed_at": datetime.now().isoformat()}

        metadata = {
            "title": news_event.get("title", "")[:100],  # 截取前100字符
            "sentiment": news_event.get("sentiment"),
            "impact_score": news_event.get("impact_score"),
            "symbols": news_event.get("related_symbols", []),
        }

        return StandardMessage(header=header, payload=payload, metadata=metadata)

    def create_error_message(
        self,
        error_code: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> StandardMessage:
        """创建错误消息

        Args:
            error_code: 错误代码
            error_message: 错误消息
            error_details: 错误详情
            correlation_id: 关联ID

        Returns:
            标准消息对象
        """
        message_id = self._generate_message_id()

        header = MessageHeader(
            message_id=message_id,
            message_type=MessageType.ERROR.value,
            source=self.source_name,
            timestamp=datetime.now().isoformat(),
            schema_version=self.schema_version,
            correlation_id=correlation_id,
        )

        payload = {
            "error_code": error_code,
            "error_message": error_message,
            "error_details": error_details or {},
            "occurred_at": datetime.now().isoformat(),
        }

        metadata = {"error_code": error_code, "severity": "error"}

        return StandardMessage(header=header, payload=payload, metadata=metadata)

    def serialize_message(
        self,
        message: StandardMessage,
        format_type: Optional[SerializationFormat] = None,
    ) -> bytes:
        """序列化消息

        Args:
            message: 标准消息对象
            format_type: 序列化格式

        Returns:
            序列化后的字节数据
        """
        try:
            format_type = format_type or self.default_format

            # 转换为字典
            message_dict = {
                "header": asdict(message.header),
                "payload": message.payload,
                "metadata": message.metadata,
            }

            # 序列化
            if format_type == SerializationFormat.JSON:
                serialized_data = json.dumps(message_dict, ensure_ascii=False).encode(
                    "utf-8"
                )
            elif format_type == SerializationFormat.PICKLE:
                serialized_data = pickle.dumps(message_dict)
            else:
                raise ValueError(f"Unsupported serialization format: {format_type}")

            # 检查消息大小
            if len(serialized_data) > self.max_message_size:
                logger.warning(
                    "Message size exceeds limit",
                    size=len(serialized_data),
                    limit=self.max_message_size,
                    message_id=message.header.message_id,
                )

            logger.debug(
                "Message serialized",
                message_id=message.header.message_id,
                format=format_type.value,
                size=len(serialized_data),
            )

            return serialized_data

        except Exception as e:
            logger.error(
                "Failed to serialize message",
                message_id=message.header.message_id,
                error=str(e),
            )
            raise

    def deserialize_message(
        self, data: bytes, format_type: Optional[SerializationFormat] = None
    ) -> StandardMessage:
        """反序列化消息

        Args:
            data: 序列化的字节数据
            format_type: 序列化格式

        Returns:
            标准消息对象
        """
        try:
            format_type = format_type or self.default_format

            # 反序列化
            if format_type == SerializationFormat.JSON:
                message_dict = json.loads(data.decode("utf-8"))
            elif format_type == SerializationFormat.PICKLE:
                message_dict = pickle.loads(data)
            else:
                raise ValueError(f"Unsupported serialization format: {format_type}")

            # 构造消息对象
            header_dict = message_dict.get("header", {})
            header = MessageHeader(**header_dict)

            payload = message_dict.get("payload", {})
            metadata = message_dict.get("metadata")

            message = StandardMessage(header=header, payload=payload, metadata=metadata)

            logger.debug(
                "Message deserialized",
                message_id=header.message_id,
                format=format_type.value,
                message_type=header.message_type,
            )

            return message

        except Exception as e:
            logger.error("Failed to deserialize message", error=str(e))
            raise

    def serialize_to_json_string(self, message: StandardMessage) -> str:
        """序列化为JSON字符串

        Args:
            message: 标准消息对象

        Returns:
            JSON字符串
        """
        try:
            message_dict = {
                "header": asdict(message.header),
                "payload": message.payload,
                "metadata": message.metadata,
            }

            return json.dumps(message_dict, ensure_ascii=False)

        except Exception as e:
            logger.error(
                "Failed to serialize to JSON string",
                message_id=message.header.message_id,
                error=str(e),
            )
            raise

    def deserialize_from_json_string(self, json_string: str) -> StandardMessage:
        """从JSON字符串反序列化

        Args:
            json_string: JSON字符串

        Returns:
            标准消息对象
        """
        try:
            message_dict = json.loads(json_string)

            header_dict = message_dict.get("header", {})
            header = MessageHeader(**header_dict)

            payload = message_dict.get("payload", {})
            metadata = message_dict.get("metadata")

            return StandardMessage(header=header, payload=payload, metadata=metadata)

        except Exception as e:
            logger.error("Failed to deserialize from JSON string", error=str(e))
            raise

    def validate_message(self, message: StandardMessage) -> bool:
        """验证消息格式

        Args:
            message: 标准消息对象

        Returns:
            是否有效
        """
        try:
            # 验证必需字段
            if not message.header.message_id:
                logger.error("Message validation failed: missing message_id")
                return False

            if not message.header.message_type:
                logger.error("Message validation failed: missing message_type")
                return False

            if not message.header.source:
                logger.error("Message validation failed: missing source")
                return False

            if not message.header.timestamp:
                logger.error("Message validation failed: missing timestamp")
                return False

            # 验证消息类型
            try:
                MessageType(message.header.message_type)
            except ValueError:
                logger.error(
                    "Message validation failed: invalid message_type",
                    message_type=message.header.message_type,
                )
                return False

            # 验证时间戳格式
            try:
                datetime.fromisoformat(message.header.timestamp.replace("Z", "+00:00"))
            except ValueError:
                logger.error(
                    "Message validation failed: invalid timestamp format",
                    timestamp=message.header.timestamp,
                )
                return False

            return True

        except Exception as e:
            logger.error("Message validation error", error=str(e))
            return False

    def _generate_message_id(self) -> str:
        """生成消息ID

        Returns:
            唯一的消息ID
        """
        import uuid

        return f"{self.source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def get_message_stats(self, messages: list) -> Dict[str, Any]:
        """获取消息统计信息

        Args:
            messages: 消息列表

        Returns:
            统计信息字典
        """
        if not messages:
            return {"total_count": 0}

        try:
            stats = {
                "total_count": len(messages),
                "message_types": {},
                "sources": {},
                "avg_payload_size": 0,
                "time_range": {},
            }

            total_payload_size = 0
            timestamps = []

            for msg in messages:
                if isinstance(msg, StandardMessage):
                    # 统计消息类型
                    msg_type = msg.header.message_type
                    stats["message_types"][msg_type] = (
                        stats["message_types"].get(msg_type, 0) + 1
                    )

                    # 统计来源
                    source = msg.header.source
                    stats["sources"][source] = stats["sources"].get(source, 0) + 1

                    # 计算载荷大小
                    payload_size = len(json.dumps(msg.payload, ensure_ascii=False))
                    total_payload_size += payload_size

                    # 收集时间戳
                    timestamps.append(msg.header.timestamp)

            # 计算平均载荷大小
            if len(messages) > 0:
                stats["avg_payload_size"] = total_payload_size / len(messages)

            # 计算时间范围
            if timestamps:
                timestamps.sort()
                stats["time_range"] = {
                    "earliest": timestamps[0],
                    "latest": timestamps[-1],
                }

            return stats

        except Exception as e:
            logger.error("Failed to get message stats", error=str(e))
            return {"total_count": len(messages), "error": str(e)}
