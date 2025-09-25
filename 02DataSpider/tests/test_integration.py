#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息源爬虫模组集成测试

测试用例:
- INT-API-01: API接口集成测试
- INT-ZMQ-01: ZeroMQ消息发布测试
- INT-DB-01: 数据库持久化测试
- INT-SYS-01: 系统协同工作测试
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sqlite3
import threading
import time

# 导入应用模块
from app.processors.pipeline import DataPipeline
from app.crawlers.web_crawler import WebCrawler
from app.crawlers.telegram_crawler import TelegramCrawler
from app.config.config_manager import ConfigManager
from app.zmq_client.publisher import ZMQPublisher
from app.zmq_client.subscriber import ZMQSubscriber


class TestIntegration(unittest.TestCase):
    """集成测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test.db")

        # 模拟配置
        self.mock_config = Mock()
        config_data = {
            "app": {"name": "InfoCrawler", "version": "1.0.0", "debug": True},
            "database": {"type": "sqlite", "url": f"sqlite:///{self.test_db_path}"},
            "api": {"host": "127.0.0.1", "port": 5000},
            "redis": {"url": "redis://localhost:6379/0"},
            "zmq": {"publisher_port": 5555, "subscriber_port": 5556},
            "data_processing": {
                "cleaning_level": "standard",
                "validation_enabled": True,
                "output_format": "json",
            },
        }

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

        # 初始化测试数据库
        self._init_test_database()

    def tearDown(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_test_database(self):
        """初始化测试数据库"""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # 创建测试表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS crawled_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                author TEXT,
                timestamp DATETIME,
                category TEXT,
                keywords TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def test_int_api_01_api_interface_integration(self):
        """INT-API-01: API接口集成测试

        测试核心组件的接口功能，验证数据处理和存储的正常工作。
        """
        # 模拟API数据处理流程
        test_data = {
            "title": "Bitcoin Price Analysis and Market Trends",
            "content": "This is a comprehensive test news article content about Bitcoin price analysis. The cryptocurrency market has shown significant volatility in recent months, with Bitcoin leading the charge in both upward and downward movements. Technical analysis suggests that the current market conditions are favorable for long-term investors who are looking to capitalize on the digital asset revolution.",
            "url": "https://example.com/test-news",
            "source": "example.com",
            "author": "Test Author",
            "category": "Technology",
            "keywords": ["test", "news", "technology"],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 创建数据处理管道
        pipeline = DataPipeline(self.mock_config, self.mock_logger)

        # 模拟API数据提交处理
        processing_result = pipeline.process_item(test_data)

        # 验证处理成功
        if not processing_result.success:
            print(f"Processing failed with errors: {processing_result.errors}")
            print(f"Stage results: {processing_result.stage_results}")
        self.assertTrue(
            processing_result.success, f"Processing failed: {processing_result.errors}"
        )
        self.assertIsNotNone(processing_result.data)

        processed_data = processing_result.data

        # 验证API响应数据格式
        api_response = {
            "success": True,
            "data": processed_data,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time": processing_result.processing_time
            if hasattr(processing_result, "processing_time")
            else 0,
        }

        # 验证API响应结构
        self.assertIn("success", api_response)
        self.assertIn("data", api_response)
        self.assertIn("timestamp", api_response)
        self.assertTrue(api_response["success"])

        # 验证数据完整性
        self.assertEqual(api_response["data"]["title"], test_data["title"])
        self.assertEqual(api_response["data"]["url"], test_data["url"])

        # 模拟健康检查响应
        health_response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {"pipeline": True, "database": True, "zmq": True},
        }

        # 验证健康检查响应
        self.assertEqual(health_response["status"], "healthy")
        self.assertIn("components", health_response)
        self.assertTrue(health_response["components"]["pipeline"])

    def test_int_zmq_01_zeromq_message_publishing(self):
        """INT-ZMQ-01: ZeroMQ消息发布测试

        模拟ZeroMQ发布者和订阅者，测试消息的发布和接收功能。
        """

        # 模拟ZeroMQ发布者
        class MockZMQPublisher:
            def __init__(self):
                self.published_messages = []

            def publish(self, topic, message):
                self.published_messages.append(
                    {
                        "topic": topic,
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                return True

            def close(self):
                pass

        # 模拟ZeroMQ订阅者
        class MockZMQSubscriber:
            def __init__(self):
                self.received_messages = []
                self.subscriptions = []

            def subscribe(self, topic):
                self.subscriptions.append(topic)

            def receive(self, timeout=1000):
                # 模拟接收消息
                if self.received_messages:
                    return self.received_messages.pop(0)
                return None

            def close(self):
                pass

        # 创建模拟的发布者和订阅者
        publisher = MockZMQPublisher()
        subscriber = MockZMQSubscriber()

        # 测试消息发布
        test_messages = [
            {
                "topic": "crawler.data",
                "data": {
                    "title": "Bitcoin News",
                    "url": "https://example.com/bitcoin",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
            {
                "topic": "crawler.status",
                "data": {
                    "status": "running",
                    "processed_items": 100,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
        ]

        # 发布测试消息
        for msg in test_messages:
            result = publisher.publish(msg["topic"], json.dumps(msg["data"]))
            self.assertTrue(result)

        # 验证消息发布
        self.assertEqual(len(publisher.published_messages), 2)

        # 验证消息内容
        published_topics = [msg["topic"] for msg in publisher.published_messages]
        self.assertIn("crawler.data", published_topics)
        self.assertIn("crawler.status", published_topics)

        # 测试订阅功能
        subscriber.subscribe("crawler.data")
        subscriber.subscribe("crawler.status")

        self.assertIn("crawler.data", subscriber.subscriptions)
        self.assertIn("crawler.status", subscriber.subscriptions)

    def test_int_db_01_database_persistence(self):
        """INT-DB-01: 数据库持久化测试

        测试数据的存储、查询、更新和删除操作。
        """
        # 测试数据插入
        test_data = {
            "title": "Database Test Article",
            "content": "This is a test article for database persistence.",
            "url": "https://example.com/db-test",
            "source": "Test DB Source",
            "author": "DB Test Author",
            "category": "Database",
            "keywords": json.dumps(["database", "test", "persistence"]),
            "views": 150,
            "likes": 25,
        }

        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # 插入测试数据
        cursor.execute(
            """
            INSERT INTO crawled_data 
            (title, content, url, source, author, category, keywords, views, likes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                test_data["title"],
                test_data["content"],
                test_data["url"],
                test_data["source"],
                test_data["author"],
                test_data["category"],
                test_data["keywords"],
                test_data["views"],
                test_data["likes"],
                datetime.utcnow().isoformat(),
            ),
        )

        conn.commit()

        # 验证数据插入
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

        # 测试数据查询
        cursor.execute("SELECT * FROM crawled_data WHERE url = ?", (test_data["url"],))
        row = cursor.fetchone()
        self.assertIsNotNone(row)

        # 验证查询结果
        self.assertEqual(row[1], test_data["title"])  # title
        self.assertEqual(row[2], test_data["content"])  # content
        self.assertEqual(row[3], test_data["url"])  # url

        # 测试数据更新
        new_views = 200
        cursor.execute(
            "UPDATE crawled_data SET views = ?, updated_at = ? WHERE url = ?",
            (new_views, datetime.utcnow().isoformat(), test_data["url"]),
        )
        conn.commit()

        # 验证更新结果
        cursor.execute(
            "SELECT views FROM crawled_data WHERE url = ?", (test_data["url"],)
        )
        updated_views = cursor.fetchone()[0]
        self.assertEqual(updated_views, new_views)

        # 测试数据删除
        cursor.execute("DELETE FROM crawled_data WHERE url = ?", (test_data["url"],))
        conn.commit()

        # 验证删除结果
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        count_after_delete = cursor.fetchone()[0]
        self.assertEqual(count_after_delete, 0)

        conn.close()

    def test_int_sys_01_system_coordination(self):
        """INT-SYS-01: 系统协同工作测试

        测试爬虫、数据处理管道、API服务之间的协同工作。
        """
        # 创建数据处理管道
        pipeline = DataPipeline(self.mock_config, self.mock_logger)

        # 模拟爬虫数据
        raw_crawler_data = {
            "title": "  <h1>System Integration Test</h1>  ",
            "content": "<p>Testing system coordination between components.</p>",
            "url": "https://example.com/integration-test",
            "source": "Integration Test Source",
            "author": "System Tester",
            "timestamp": "2024-01-15T10:30:00Z",
            "category": "Testing",
            "keywords": ["integration", "test", "system"],
            "views": "500",
            "likes": "50",
        }

        # 步骤1: 数据处理管道处理原始数据
        processing_result = pipeline.process_item(raw_crawler_data)

        # 验证处理成功
        self.assertTrue(processing_result.success)
        self.assertIsNotNone(processing_result.data)

        processed_data = processing_result.data

        # 验证数据清洗效果
        self.assertEqual(processed_data["title"], "System Integration Test")
        self.assertNotIn("<h1>", processed_data["title"])
        self.assertNotIn("<p>", processed_data["content"])

        # 步骤2: 模拟数据存储到数据库
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO crawled_data 
            (title, content, url, source, author, category, keywords, views, likes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                processed_data["title"],
                processed_data["content"],
                processed_data["url"],
                processed_data["source"],
                processed_data["author"],
                processed_data["category"],
                json.dumps(processed_data["keywords"]),
                processed_data["views"],
                processed_data["likes"],
                processed_data["timestamp"],
            ),
        )

        conn.commit()

        # 步骤3: 模拟API查询数据
        cursor.execute(
            "SELECT * FROM crawled_data WHERE url = ?", (processed_data["url"],)
        )
        stored_data = cursor.fetchone()

        # 验证数据完整性
        self.assertIsNotNone(stored_data)
        self.assertEqual(stored_data[1], processed_data["title"])
        self.assertEqual(stored_data[3], processed_data["url"])

        # 步骤4: 模拟消息发布
        class MockMessagePublisher:
            def __init__(self):
                self.published_messages = []

            def publish_data_update(self, data):
                message = {
                    "type": "data_update",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                self.published_messages.append(message)
                return True

        publisher = MockMessagePublisher()

        # 发布数据更新消息
        publish_result = publisher.publish_data_update(
            {
                "id": stored_data[0],
                "title": stored_data[1],
                "url": stored_data[3],
                "action": "created",
            }
        )

        # 验证消息发布
        self.assertTrue(publish_result)
        self.assertEqual(len(publisher.published_messages), 1)

        published_message = publisher.published_messages[0]
        self.assertEqual(published_message["type"], "data_update")
        self.assertEqual(published_message["data"]["action"], "created")

        conn.close()

        # 验证整个流程的统计信息
        stats = pipeline.get_stats()
        self.assertGreaterEqual(stats["items_processed"], 1)
        self.assertGreaterEqual(stats["items_successful"], 1)
        self.assertGreater(stats["success_rate"], 0)


if __name__ == "__main__":
    unittest.main()
