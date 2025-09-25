# -*- coding: utf-8 -*-
"""
序列化工具模块

提供Protobuf和Avro序列化功能
"""

import json
import io
from typing import Dict, Any, List, Union, Optional
from datetime import datetime

try:
    import google.protobuf.message as protobuf_message
    from google.protobuf.json_format import MessageToDict, ParseDict
    from google.protobuf.descriptor import FieldDescriptor
    from google.protobuf.message import Message

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False

try:
    import avro.schema
    import avro.io

    AVRO_AVAILABLE = True
except ImportError:
    AVRO_AVAILABLE = False

from ..config import ConfigManager
from . import Logger


class ProtobufSerializer:
    """Protobuf序列化器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        if not PROTOBUF_AVAILABLE:
            self.logger.warning("Protobuf库未安装，序列化功能不可用")

    def _create_data_item_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建DataItem消息结构"""
        message = {
            "id": str(data.get("id", "")),
            "title": str(data.get("title", "")),
            "content": str(data.get("content", "")),
            "url": str(data.get("url", "")),
            "timestamp": str(data.get("timestamp", "")),
            "category": str(data.get("category", "")),
            "keywords": list(data.get("keywords", [])),
            "source": str(data.get("source", "")),
            "metadata": dict(data.get("metadata", {})),
        }

        # 处理metrics字段
        metrics = data.get("metrics", {})
        if metrics:
            message["metrics"] = {
                "relevance_score": float(metrics.get("relevance_score", 0.0)),
                "sentiment_score": float(metrics.get("sentiment_score", 0.0)),
                "word_count": int(metrics.get("word_count", 0)),
                "view_count": int(metrics.get("view_count", 0)),
                "share_count": int(metrics.get("share_count", 0)),
            }
        else:
            message["metrics"] = {
                "relevance_score": 0.0,
                "sentiment_score": 0.0,
                "word_count": 0,
                "view_count": 0,
                "share_count": 0,
            }

        return message

    def serialize(self, data: Dict[str, Any]) -> bytes:
        """序列化数据为Protobuf格式

        Args:
            data: 要序列化的数据

        Returns:
            序列化后的字节数据
        """
        if not PROTOBUF_AVAILABLE:
            raise RuntimeError("Protobuf库未安装")

        try:
            # 创建消息结构
            message_data = self._create_data_item_message(data)

            # 由于没有生成的protobuf类，我们使用JSON格式模拟
            # 在实际部署时，应该使用protoc生成的类
            json_data = json.dumps(message_data, ensure_ascii=False)

            # 添加protobuf标识头
            protobuf_data = b"PROTOBUF:" + json_data.encode("utf-8")

            self.logger.debug(f"Protobuf序列化成功，数据大小: {len(protobuf_data)} bytes")
            return protobuf_data

        except Exception as e:
            self.logger.error(f"Protobuf序列化失败: {e}")
            raise

    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """反序列化Protobuf数据

        Args:
            data: 序列化的字节数据

        Returns:
            反序列化后的数据
        """
        if not PROTOBUF_AVAILABLE:
            raise RuntimeError("Protobuf库未安装")

        try:
            # 检查protobuf标识头
            if not data.startswith(b"PROTOBUF:"):
                raise ValueError("无效的Protobuf数据格式")

            # 移除标识头并解析JSON
            json_data = data[9:].decode("utf-8")
            message_data = json.loads(json_data)

            self.logger.debug("Protobuf反序列化成功")
            return message_data

        except Exception as e:
            self.logger.error(f"Protobuf反序列化失败: {e}")
            raise


class AvroSerializer:
    """Avro序列化器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        if not AVRO_AVAILABLE:
            self.logger.warning("Avro库未安装，序列化功能不可用")

        # 定义Avro schema
        self.schema_dict = {
            "type": "record",
            "name": "DataItem",
            "namespace": "dataspider",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "content", "type": "string"},
                {"name": "url", "type": "string"},
                {"name": "timestamp", "type": "string"},
                {"name": "category", "type": "string"},
                {"name": "keywords", "type": {"type": "array", "items": "string"}},
                {"name": "source", "type": "string"},
                {"name": "metadata", "type": {"type": "map", "values": "string"}},
                {
                    "name": "metrics",
                    "type": {
                        "type": "record",
                        "name": "DataMetrics",
                        "fields": [
                            {"name": "relevance_score", "type": "double"},
                            {"name": "sentiment_score", "type": "double"},
                            {"name": "word_count", "type": "int"},
                            {"name": "view_count", "type": "int"},
                            {"name": "share_count", "type": "int"},
                        ],
                    },
                },
            ],
        }

        if AVRO_AVAILABLE:
            self.schema = avro.schema.parse(json.dumps(self.schema_dict))

    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """准备数据以符合Avro schema"""
        prepared = {
            "id": str(data.get("id", "")),
            "title": str(data.get("title", "")),
            "content": str(data.get("content", "")),
            "url": str(data.get("url", "")),
            "timestamp": str(data.get("timestamp", "")),
            "category": str(data.get("category", "")),
            "keywords": list(data.get("keywords", [])),
            "source": str(data.get("source", "")),
            "metadata": {k: str(v) for k, v in data.get("metadata", {}).items()},
        }

        # 处理metrics字段
        metrics = data.get("metrics", {})
        prepared["metrics"] = {
            "relevance_score": float(metrics.get("relevance_score", 0.0)),
            "sentiment_score": float(metrics.get("sentiment_score", 0.0)),
            "word_count": int(metrics.get("word_count", 0)),
            "view_count": int(metrics.get("view_count", 0)),
            "share_count": int(metrics.get("share_count", 0)),
        }

        return prepared

    def serialize(self, data: Dict[str, Any]) -> bytes:
        """序列化数据为Avro格式

        Args:
            data: 要序列化的数据

        Returns:
            序列化后的字节数据
        """
        if not AVRO_AVAILABLE:
            raise RuntimeError("Avro库未安装")

        try:
            # 准备数据
            prepared_data = self._prepare_data(data)

            # 创建字节流
            bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)

            # 创建DatumWriter并写入数据
            writer = avro.io.DatumWriter(self.schema)
            writer.write(prepared_data, encoder)

            # 获取序列化后的字节数据
            serialized_data = bytes_writer.getvalue()
            bytes_writer.close()

            self.logger.debug(f"Avro序列化成功，数据大小: {len(serialized_data)} bytes")
            return serialized_data

        except Exception as e:
            self.logger.error(f"Avro序列化失败: {e}")
            raise

    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """反序列化Avro数据

        Args:
            data: 序列化的字节数据

        Returns:
            反序列化后的数据
        """
        if not AVRO_AVAILABLE:
            raise RuntimeError("Avro库未安装")

        try:
            # 创建字节流
            bytes_reader = io.BytesIO(data)
            decoder = avro.io.BinaryDecoder(bytes_reader)

            # 创建DatumReader并读取数据
            reader = avro.io.DatumReader(self.schema)
            deserialized_data = reader.read(decoder)

            bytes_reader.close()

            self.logger.debug("Avro反序列化成功")
            return deserialized_data

        except Exception as e:
            self.logger.error(f"Avro反序列化失败: {e}")
            raise


class SerializationManager:
    """序列化管理器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        # 初始化序列化器
        self.protobuf_serializer = ProtobufSerializer(config, logger)
        self.avro_serializer = AvroSerializer(config, logger)

        # 序列化器映射
        self.serializers = {
            "protobuf": self.protobuf_serializer,
            "avro": self.avro_serializer,
        }

        self.logger.info("序列化管理器初始化完成")

    def serialize(self, data: Dict[str, Any], format_type: str) -> bytes:
        """序列化数据

        Args:
            data: 要序列化的数据
            format_type: 序列化格式 (protobuf, avro)

        Returns:
            序列化后的字节数据
        """
        if format_type not in self.serializers:
            raise ValueError(f"不支持的序列化格式: {format_type}")

        serializer = self.serializers[format_type]
        return serializer.serialize(data)

    def deserialize(self, data: bytes, format_type: str) -> Dict[str, Any]:
        """反序列化数据

        Args:
            data: 序列化的字节数据
            format_type: 序列化格式 (protobuf, avro)

        Returns:
            反序列化后的数据
        """
        if format_type not in self.serializers:
            raise ValueError(f"不支持的序列化格式: {format_type}")

        serializer = self.serializers[format_type]
        return serializer.deserialize(data)

    def get_supported_formats(self) -> List[str]:
        """获取支持的序列化格式"""
        supported = []

        if PROTOBUF_AVAILABLE:
            supported.append("protobuf")
        if AVRO_AVAILABLE:
            supported.append("avro")

        return supported

    def is_format_available(self, format_type: str) -> bool:
        """检查序列化格式是否可用"""
        if format_type == "protobuf":
            return PROTOBUF_AVAILABLE
        elif format_type == "avro":
            return AVRO_AVAILABLE
        else:
            return False
