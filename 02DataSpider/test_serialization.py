#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
序列化功能测试脚本

测试Protobuf和Avro序列化功能
"""

import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import ConfigManager
from app.utils import Logger
from app.utils.serializers import SerializationManager
from app.processors.data_formatter import DataFormatter, OutputFormat


def test_serialization():
    """测试序列化功能"""
    print("开始测试序列化功能...")

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建序列化管理器
    serialization_manager = SerializationManager(config, logger)

    # 测试数据
    test_data = {
        "id": "test_001",
        "title": "Bitcoin价格分析报告",
        "content": "比特币价格在过去24小时内出现了显著波动...",
        "url": "https://example.com/bitcoin-analysis",
        "timestamp": datetime.now().isoformat(),
        "category": "加密货币",
        "keywords": ["比特币", "价格分析", "加密货币", "投资"],
        "source": "财经新闻网",
        "metadata": {"author": "张三", "language": "zh-CN", "region": "CN"},
        "metrics": {
            "relevance_score": 0.95,
            "sentiment_score": 0.7,
            "word_count": 1500,
            "view_count": 2500,
            "share_count": 150,
        },
    }

    print(f"原始数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    print("\n" + "=" * 50)

    # 检查支持的格式
    supported_formats = serialization_manager.get_supported_formats()
    print(f"支持的序列化格式: {supported_formats}")

    # 测试Protobuf序列化
    if serialization_manager.is_format_available("protobuf"):
        print("\n测试Protobuf序列化...")
        try:
            # 序列化
            protobuf_data = serialization_manager.serialize(test_data, "protobuf")
            print(f"Protobuf序列化成功，数据大小: {len(protobuf_data)} bytes")

            # 反序列化
            deserialized_data = serialization_manager.deserialize(
                protobuf_data, "protobuf"
            )
            print(f"Protobuf反序列化成功")
            print(
                f"反序列化数据: {json.dumps(deserialized_data, ensure_ascii=False, indent=2)}"
            )

            # 验证数据一致性
            if deserialized_data["id"] == test_data["id"]:
                print("✓ Protobuf序列化/反序列化数据一致性验证通过")
            else:
                print("✗ Protobuf序列化/反序列化数据一致性验证失败")

        except Exception as e:
            print(f"✗ Protobuf序列化测试失败: {e}")
    else:
        print("\n⚠ Protobuf库未安装，跳过测试")

    # 测试Avro序列化
    if serialization_manager.is_format_available("avro"):
        print("\n测试Avro序列化...")
        try:
            # 序列化
            avro_data = serialization_manager.serialize(test_data, "avro")
            print(f"Avro序列化成功，数据大小: {len(avro_data)} bytes")

            # 反序列化
            deserialized_data = serialization_manager.deserialize(avro_data, "avro")
            print(f"Avro反序列化成功")
            print(
                f"反序列化数据: {json.dumps(deserialized_data, ensure_ascii=False, indent=2)}"
            )

            # 验证数据一致性
            if deserialized_data["id"] == test_data["id"]:
                print("✓ Avro序列化/反序列化数据一致性验证通过")
            else:
                print("✗ Avro序列化/反序列化数据一致性验证失败")

        except Exception as e:
            print(f"✗ Avro序列化测试失败: {e}")
    else:
        print("\n⚠ Avro库未安装，跳过测试")

    print("\n" + "=" * 50)
    print("序列化功能测试完成")


def test_data_formatter_with_serialization():
    """测试数据格式化器的序列化功能"""
    print("\n开始测试数据格式化器的序列化功能...")

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 测试数据
    test_data = {
        "title": "  以太坊价格预测  ",
        "content": "以太坊价格分析...   ",
        "url": "HTTP://EXAMPLE.COM/ETH",
        "timestamp": "2024-01-15T10:30:00Z",
        "category": "Crypto Currency",
        "keywords": ["以太坊", "ETH", "价格预测"],
        "source": "  区块链资讯  ",
        "metrics": {
            "relevance_score": 0.88,
            "sentiment_score": 0.6,
            "word_count": 800,
            "view_count": 1200,
            "share_count": 80,
        },
    }

    # 测试不同输出格式
    formats_to_test = [
        (OutputFormat.JSON, "JSON"),
        (OutputFormat.PROTOBUF, "Protobuf"),
        (OutputFormat.AVRO, "Avro"),
    ]

    for output_format, format_name in formats_to_test:
        print(f"\n测试{format_name}格式输出...")

        try:
            # 创建数据格式化器
            formatter = DataFormatter(config, logger)
            # 设置输出格式
            formatter.output_format = output_format

            # 格式化数据
            result = formatter.format_data(test_data)

            if result.success:
                print(f"✓ {format_name}格式化成功")
                print(f"应用规则: {result.applied_rules}")
                print(f"格式化时间: {result.formatting_time:.3f}s")

                # 显示输出数据类型和大小
                formatted_data = result.formatted_data
                if isinstance(formatted_data, bytes):
                    print(f"输出类型: bytes, 大小: {len(formatted_data)} bytes")
                elif isinstance(formatted_data, str):
                    print(f"输出类型: string, 长度: {len(formatted_data)} 字符")
                else:
                    print(f"输出类型: {type(formatted_data).__name__}")

            else:
                print(f"✗ {format_name}格式化失败")
                if result.errors:
                    print(f"错误: {result.errors}")

        except Exception as e:
            print(f"✗ {format_name}格式化测试异常: {e}")

    print("\n数据格式化器序列化功能测试完成")


if __name__ == "__main__":
    # 测试序列化功能
    test_serialization()

    # 测试数据格式化器的序列化功能
    test_data_formatter_with_serialization()

    print("\n所有测试完成！")
