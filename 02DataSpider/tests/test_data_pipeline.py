#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理管道单元测试

测试用例:
- UNIT-PROC-01: 数据清洗与格式化
"""

import unittest
from unittest.mock import Mock, patch
import json
from datetime import datetime

from app.processors.pipeline import DataPipeline, ProcessingConfig, ProcessingMode
from app.processors.data_cleaner import DataCleaner
from app.processors.data_formatter import DataFormatter
from app.processors.data_validator import DataValidator


class TestDataPipeline(unittest.TestCase):
    """数据处理管道测试类"""

    def setUp(self):
        """测试前准备"""
        # 模拟配置
        self.mock_config = Mock()

        # 设置配置数据
        config_data = {
            "data_processing": {
                "cleaning_level": "standard",
                "validation_enabled": True,
                "output_format": "json",
                "max_workers": 4,
            },
            "processors": {
                "validation": {
                    "url_timeout": 5,
                    "max_title_length": 200,
                    "max_content_length": 50000,
                    "min_content_length": 10,
                    "allowed_domains": ["example.com", "test.com"],
                }
            },
        }

        # 配置mock方法
        def mock_get_config(key, default=None):
            keys = key.split(".")
            value = config_data
            try:
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default

        self.mock_config.get_config = mock_get_config
        self.mock_config.get.return_value = config_data

        # 模拟日志
        self.mock_logger = Mock()

        # 创建数据处理管道实例
        self.pipeline = DataPipeline(self.mock_config, self.mock_logger)

    def test_unit_proc_01_data_cleaning_and_formatting(self):
        """UNIT-PROC-01: 数据清洗与格式化

        输入一条包含多余HTML标签和非标准格式的原始数据。
        验证输出的JSON数据结构清晰，多余标签被移除，
        数据格式符合crawled_data表的设计。
        """
        # 包含多余HTML标签和非标准格式的原始数据
        raw_data = {
            "title": "  <h1>Bitcoin Price <strong>Analysis</strong></h1>  ",
            "content": """<div class="content">
                <p>Bitcoin has <em>successfully</em> broken through the <b>$50,000</b> resistance level.</p>
                <p>Market analysts are <span style="color: red;">optimistic</span> about future movements.</p>
                <script>alert('xss');</script>
                <style>.hidden { display: none; }</style>
            </div>""",
            "url": "HTTP://EXAMPLE.COM:443/NEWS/BITCOIN-ANALYSIS?UTM_SOURCE=TWITTER",
            "timestamp": "2024-01-15T10:30:00.000Z",
            "category": "  Crypto Currency  ",
            "keywords": [
                "Bitcoin",
                "PRICE",
                "analysis",
                "bitcoin",
                "",
                "   ",
                "CRYPTOCURRENCY",
            ],
            "source": "  <span>Example News</span>  ",
            "author": '<a href="/author/john">John Doe</a>',
            "views": "1,250",
            "likes": "89.0",
            "extra_html": '<img src="malicious.jpg" onerror="alert(1)">',
            "empty_field": "",
            "null_field": None,
            "whitespace_field": "   ",
        }

        # 执行数据处理
        result = self.pipeline.process_item(raw_data)

        # 验证处理成功
        self.assertTrue(result.success, f"Processing failed: {result.errors}")
        self.assertIsNotNone(result.data)

        processed_data = result.data

        # 验证HTML标签被正确移除
        self.assertEqual(processed_data["title"], "Bitcoin Price Analysis")
        self.assertNotIn("<h1>", processed_data["title"])
        self.assertNotIn("<strong>", processed_data["title"])

        # 验证内容中的HTML标签被移除，但保留文本内容
        content = processed_data["content"]
        self.assertNotIn("<div>", content)
        self.assertNotIn("<p>", content)
        self.assertNotIn("<em>", content)
        self.assertNotIn("<b>", content)
        self.assertNotIn("<span>", content)
        self.assertNotIn("<script>", content)  # 危险标签被移除
        self.assertNotIn("<style>", content)  # 样式标签被移除

        # 验证文本内容被保留
        self.assertIn("Bitcoin has successfully broken", content)
        self.assertIn("$50,000", content)
        self.assertIn("Market analysts are optimistic", content)

        # 验证URL被标准化
        self.assertEqual(
            processed_data["url"],
            "http://example.com:443/news/bitcoin-analysis?utm_source=twitter",
        )

        # 验证时间戳格式化
        self.assertIsInstance(processed_data["timestamp"], str)
        # 验证时间戳可以被解析
        datetime.fromisoformat(processed_data["timestamp"].replace("Z", "+00:00"))

        # 验证分类被清理
        self.assertEqual(processed_data["category"], "Crypto Currency")

        # 验证关键词被去重、清理和标准化
        keywords = processed_data["keywords"]
        self.assertIsInstance(keywords, list)
        self.assertIn("bitcoin", keywords)  # 去重后只保留一个
        self.assertIn("price", keywords)  # 转换为小写
        self.assertIn("analysis", keywords)
        self.assertIn("cryptocurrency", keywords)  # 转换为小写
        self.assertNotIn("", keywords)  # 空字符串被移除
        self.assertNotIn("   ", keywords)  # 空白字符串被移除

        # 验证来源被清理
        self.assertEqual(processed_data["source"], "Example News")
        self.assertNotIn("<span>", processed_data["source"])

        # 验证作者被清理
        self.assertEqual(processed_data["author"], "John Doe")
        self.assertNotIn("<a href=", processed_data["author"])

        # 验证数值字段被标准化
        self.assertEqual(processed_data["views"], 1250)  # 移除逗号并转换为整数
        self.assertEqual(processed_data["likes"], 89)  # 移除小数点并转换为整数

        # 验证危险内容被移除
        self.assertNotIn("extra_html", processed_data)  # 包含危险内容的字段被移除

        # 验证空字段被处理
        self.assertNotIn("empty_field", processed_data)  # 空字符串字段被移除
        self.assertNotIn("null_field", processed_data)  # None字段被移除
        self.assertNotIn("whitespace_field", processed_data)  # 空白字符串字段被移除

        # 验证数据结构符合crawled_data表设计
        required_fields = ["title", "content", "url", "timestamp", "source"]
        for field in required_fields:
            self.assertIn(field, processed_data, f"Required field '{field}' missing")

        # 验证数据类型正确
        self.assertIsInstance(processed_data["title"], str)
        self.assertIsInstance(processed_data["content"], str)
        self.assertIsInstance(processed_data["url"], str)
        self.assertIsInstance(processed_data["timestamp"], str)
        self.assertIsInstance(processed_data["keywords"], list)

        # 验证处理元数据
        self.assertIn("metadata", processed_data)
        metadata = processed_data["metadata"]
        self.assertIn("processed_at", metadata)
        self.assertIn("pipeline_version", metadata)
        self.assertIn("processing_stages", metadata)

    def test_data_validation_with_invalid_data(self):
        """测试无效数据的验证处理"""
        # 无效数据
        invalid_data = {
            "title": "",  # 空标题
            "content": "x",  # 内容过短
            "url": "not-a-valid-url",  # 无效URL
            "timestamp": "invalid-timestamp",  # 无效时间戳
            "keywords": "not a list",  # 错误的数据类型
            "views": "not a number",  # 无效数值
        }

        result = self.pipeline.process_item(invalid_data)

        # 验证处理失败或有警告
        if not result.success:
            self.assertGreater(len(result.errors), 0)
        else:
            # 如果处理成功，应该有警告或数据被修正
            self.assertGreater(len(result.warnings), 0)

    def test_batch_processing_sequential(self):
        """测试顺序批量处理"""
        # 测试数据批次
        test_batch = [
            {
                "title": "Bitcoin News 1",
                "content": "This is a valid content for Bitcoin news article.",
                "url": "https://example.com/1",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "example.com",
            },
            {
                "title": "Ethereum News 2",
                "content": "This is a valid content for Ethereum news article.",
                "url": "https://example.com/2",
                "timestamp": "2024-01-15T10:31:00Z",
                "source": "example.com",
            },
            {
                "title": "Invalid News",
                "content": "",  # 无效内容
                "url": "invalid-url",
                "timestamp": "invalid-time",
                "source": "invalid.com",
            },
        ]

        # 配置顺序处理
        config = ProcessingConfig(
            processing_mode=ProcessingMode.SEQUENTIAL, max_workers=1
        )

        batch_result = self.pipeline.process_batch(test_batch, config)

        # 验证批量处理结果
        self.assertEqual(batch_result.total_items, 3)
        self.assertGreaterEqual(batch_result.successful_items, 2)  # 至少2个成功
        self.assertLessEqual(batch_result.failed_items, 1)  # 最多1个失败

        # 验证处理结果
        self.assertEqual(len(batch_result.results), 3)

    def test_batch_processing_parallel(self):
        """测试并行批量处理"""
        # 测试数据批次
        test_batch = [
            {
                "title": f"News {i}",
                "content": f"This is a valid content for news article number {i}.",
                "url": f"https://example.com/{i}",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "example.com",
            }
            for i in range(5)
        ]

        # 配置并行处理
        config = ProcessingConfig(
            processing_mode=ProcessingMode.PARALLEL, max_workers=3
        )

        batch_result = self.pipeline.process_batch(test_batch, config)

        # 验证批量处理结果
        self.assertEqual(batch_result.total_items, 5)
        self.assertEqual(batch_result.successful_items, 5)  # 所有应该成功
        self.assertEqual(batch_result.failed_items, 0)

        # 验证处理时间（并行应该更快）
        self.assertGreater(batch_result.processing_time, 0)

    def test_processing_hooks(self):
        """测试处理钩子功能"""

        # 添加前置处理钩子
        def pre_hook(data):
            data["processed_by"] = "test_pipeline"
            data["pre_hook_timestamp"] = datetime.utcnow().isoformat()
            return data

        # 添加后置处理钩子
        def post_hook(result):
            if result.data:
                result.data["post_hook_timestamp"] = datetime.utcnow().isoformat()
                result.data["final_processing"] = True
            return result

        self.pipeline.add_pre_processing_hook(pre_hook)
        self.pipeline.add_post_processing_hook(post_hook)

        # 测试数据
        test_data = {
            "title": "Test News",
            "content": "Test content",
            "url": "https://example.com/test",
            "timestamp": "2024-01-15T10:30:00Z",
            "source": "example.com",
        }

        result = self.pipeline.process_item(test_data)

        # 验证钩子被执行
        self.assertTrue(result.success)
        self.assertIn("processed_by", result.data)
        self.assertEqual(result.data["processed_by"], "test_pipeline")
        self.assertIn("pre_hook_timestamp", result.data)
        self.assertIn("post_hook_timestamp", result.data)
        self.assertTrue(result.data["final_processing"])

    def test_pipeline_statistics(self):
        """测试管道统计功能"""
        # 处理一些测试数据
        test_data_list = [
            {
                "title": "Valid News 1",
                "content": "This is a valid content for the first news article.",
                "url": "https://example.com/1",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "example.com",
            },
            {
                "title": "Valid News 2",
                "content": "This is a valid content for the second news article.",
                "url": "https://example.com/2",
                "timestamp": "2024-01-15T10:31:00Z",
                "source": "example.com",
            },
            {
                "title": "",  # 无效数据
                "content": "",
                "url": "invalid",
                "timestamp": "invalid",
                "source": "invalid.com",
            },
        ]

        # 处理数据
        for data in test_data_list:
            self.pipeline.process_item(data)

        # 获取统计信息
        stats = self.pipeline.get_stats()

        # 验证统计信息
        self.assertGreaterEqual(stats["items_processed"], 3)
        self.assertGreaterEqual(stats["items_successful"], 2)
        self.assertIn("success_rate", stats)
        self.assertIn("avg_processing_time", stats)
        self.assertIn("component_stats", stats)

        # 验证组件统计
        self.assertIn("cleaner", stats["component_stats"])
        self.assertIn("validator", stats["component_stats"])
        self.assertIn("formatter", stats["component_stats"])

    def test_pipeline_health_check(self):
        """测试管道健康检查"""
        # 处理一些成功的数据以建立健康状态
        for i in range(10):
            test_data = {
                "title": f"News {i}",
                "content": f"This is a valid content for news article number {i}.",
                "url": f"https://example.com/{i}",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "example.com",
            }
            self.pipeline.process_item(test_data)

        # 执行健康检查
        health = self.pipeline.health_check()

        # 验证健康检查结果
        self.assertIn("status", health)
        self.assertIn(health["status"], ["healthy", "degraded", "unhealthy"])
        self.assertIn("success_rate", health)
        self.assertIn("items_processed", health)
        self.assertIn("component_health", health)

        # 验证组件健康状态
        component_health = health["component_health"]
        self.assertIn("cleaner", component_health)
        self.assertIn("validator", component_health)
        self.assertIn("formatter", component_health)


if __name__ == "__main__":
    unittest.main()
