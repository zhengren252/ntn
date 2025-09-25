#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram监听器单元测试

测试用例:
- UNIT-CRAWL-02: 关键词过滤
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime

from app.crawlers.telegram_crawler import TelegramCrawler


class TestTelegramCrawler(unittest.TestCase):
    """Telegram爬虫测试类"""

    def setUp(self):
        """测试前准备"""
        # 模拟配置
        self.mock_config = Mock()

        # 设置telegram配置
        telegram_config = {
            "api_id": "12345",
            "api_hash": "test_hash",
            "phone": "+1234567890",
            "keywords": ["listing", "binance", "coinbase", "trading", "pump"],
            "channels": ["@crypto_news", "@trading_signals"],
            "filter_enabled": True,
        }

        # 配置mock的get_config方法
        def mock_get_config(key, default=None):
            if key == "telegram":
                return telegram_config
            elif key.startswith("telegram."):
                sub_key = key.split(".", 1)[1]
                return telegram_config.get(sub_key, default)
            return default

        self.mock_config.get_config = mock_get_config

        # 模拟日志
        self.mock_logger = Mock()

        # 创建Telegram爬虫实例
        self.crawler = TelegramCrawler(self.mock_config, self.mock_logger)

    def test_unit_crawl_02_keyword_filtering(self):
        """UNIT-CRAWL-02: 关键词过滤

        Mock一个Telethon客户端，模拟接收多条Telegram消息，
        部分消息包含预设的关键词（如 'listing'）。
        验证只有包含关键词的消息被处理，其他消息被忽略。
        """
        # 模拟Telegram消息
        mock_messages = [
            # 包含关键词的消息 - 应该被处理
            Mock(
                id=1,
                text="🚀 BREAKING: Coinbase announces new listing for XYZ token!",
                date=datetime(2024, 1, 15, 10, 30, 0),
                sender_id=12345,
                chat_id=67890,
                views=1250,
            ),
            # 不包含关键词的消息 - 应该被忽略
            Mock(
                id=2,
                text="Good morning everyone! How are you today?",
                date=datetime(2024, 1, 15, 10, 31, 0),
                sender_id=12346,
                chat_id=67890,
                views=89,
            ),
            # 包含关键词的消息 - 应该被处理
            Mock(
                id=3,
                text="Binance trading volume hits new record high 📈",
                date=datetime(2024, 1, 15, 10, 32, 0),
                sender_id=12347,
                chat_id=67890,
                views=2100,
            ),
            # 包含关键词的消息 - 应该被处理
            Mock(
                id=4,
                text="Major pump expected for BTC after recent news",
                date=datetime(2024, 1, 15, 10, 33, 0),
                sender_id=12348,
                chat_id=67890,
                views=567,
            ),
            # 不包含关键词的消息 - 应该被忽略
            Mock(
                id=5,
                text="Weather is nice today, perfect for a walk",
                date=datetime(2024, 1, 15, 10, 34, 0),
                sender_id=12349,
                chat_id=67890,
                views=23,
            ),
            # 包含关键词的消息（大小写不敏感）- 应该被处理
            Mock(
                id=6,
                text="TRADING signals for today: BUY ETH",
                date=datetime(2024, 1, 15, 10, 35, 0),
                sender_id=12350,
                chat_id=67890,
                views=890,
            ),
        ]

        # 预期被处理的消息ID（包含关键词的消息）
        expected_processed_ids = [1, 3, 4, 6]

        # 执行关键词过滤测试
        processed_messages = []
        ignored_messages = []

        for message in mock_messages:
            if self.crawler.should_process_message(message):
                processed_messages.append(message)
            else:
                ignored_messages.append(message)

        # 验证过滤结果
        # 应该有4条消息被处理
        self.assertEqual(len(processed_messages), 4)

        # 应该有2条消息被忽略
        self.assertEqual(len(ignored_messages), 2)

        # 验证被处理的消息ID正确
        processed_ids = [msg.id for msg in processed_messages]
        self.assertEqual(sorted(processed_ids), sorted(expected_processed_ids))

        # 验证被忽略的消息ID正确
        ignored_ids = [msg.id for msg in ignored_messages]
        self.assertEqual(sorted(ignored_ids), [2, 5])

        # 验证具体的关键词匹配
        # 消息1包含"listing"和"coinbase"
        msg1 = next(msg for msg in processed_messages if msg.id == 1)
        matched_keywords = self.crawler.extract_keywords_from_message(msg1)
        self.assertIn("listing", matched_keywords)
        self.assertIn("coinbase", matched_keywords)

        # 消息3包含"binance"和"trading"
        msg3 = next(msg for msg in processed_messages if msg.id == 3)
        matched_keywords = self.crawler.extract_keywords_from_message(msg3)
        self.assertIn("binance", matched_keywords)
        self.assertIn("trading", matched_keywords)

        # 消息4包含"pump"
        msg4 = next(msg for msg in processed_messages if msg.id == 4)
        matched_keywords = self.crawler.extract_keywords_from_message(msg4)
        self.assertIn("pump", matched_keywords)

        # 消息6包含"trading"（大小写不敏感）
        msg6 = next(msg for msg in processed_messages if msg.id == 6)
        matched_keywords = self.crawler.extract_keywords_from_message(msg6)
        self.assertIn("trading", matched_keywords)

    def test_keyword_extraction_case_insensitive(self):
        """测试关键词提取的大小写不敏感性"""
        test_cases = [
            {
                "text": "BINANCE listing announcement",
                "expected": ["binance", "listing"],
            },
            {
                "text": "Trading signals for COINBASE",
                "expected": ["trading", "coinbase"],
            },
            {"text": "Pump and dump warning", "expected": ["pump"]},
            {"text": "No relevant keywords here", "expected": []},
        ]

        for case in test_cases:
            mock_message = Mock(text=case["text"])
            keywords = self.crawler.extract_keywords_from_message(mock_message)

            for expected_keyword in case["expected"]:
                self.assertIn(
                    expected_keyword,
                    keywords,
                    f"Expected '{expected_keyword}' in keywords for text: '{case['text']}'",
                )

    def test_message_filtering_with_disabled_filter(self):
        """测试禁用过滤器时的行为"""
        # 创建新的配置，禁用关键词过滤
        telegram_config_no_filter = {
            "api_id": "12345",
            "api_hash": "test_hash",
            "phone": "+1234567890",
            "keywords": [],  # 空关键词列表
            "channels": ["@crypto_news", "@trading_signals"],
            "filter_enabled": False,
        }

        # 创建新的mock配置
        mock_config_no_filter = Mock()

        def mock_get_config_no_filter(key, default=None):
            if key == "telegram":
                return telegram_config_no_filter
            elif key.startswith("telegram."):
                sub_key = key.split(".", 1)[1]
                return telegram_config_no_filter.get(sub_key, default)
            return default

        mock_config_no_filter.get_config = mock_get_config_no_filter

        # 重新创建爬虫实例
        crawler_no_filter = TelegramCrawler(mock_config_no_filter, self.mock_logger)

        # 测试消息（不包含关键词）
        test_message = Mock(
            id=1, text="This message has no relevant keywords", date=datetime.now()
        )

        # 当没有关键词配置时，所有消息都应该被处理
        self.assertTrue(crawler_no_filter.should_process_message(test_message))

    def test_empty_message_handling(self):
        """测试空消息的处理"""
        empty_messages = [
            Mock(id=1, text="", date=datetime.now()),  # 空文本
            Mock(id=2, text=None, date=datetime.now()),  # None文本
            Mock(id=3, text="   ", date=datetime.now()),  # 只有空白字符
        ]

        for message in empty_messages:
            # 空消息应该被忽略
            self.assertFalse(self.crawler.should_process_message(message))

    def test_keyword_boundary_matching(self):
        """测试关键词边界匹配（避免部分匹配）"""
        test_cases = [
            {
                "text": "This is about trading strategies",
                "should_match": True,  # 完整的"trading"关键词
                "expected_keywords": ["trading"],
            },
            {
                "text": "We are upgrading our system",
                "should_match": False,  # "trading"只是"upgrading"的一部分
                "expected_keywords": [],
            },
            {
                "text": "Binance exchange is popular",
                "should_match": True,  # 完整的"binance"关键词
                "expected_keywords": ["binance"],
            },
            {
                "text": "The turbinance of the market",
                "should_match": False,  # "binance"只是"turbinance"的一部分
                "expected_keywords": [],
            },
        ]

        for case in test_cases:
            mock_message = Mock(text=case["text"])

            # 测试是否应该处理消息
            should_process = self.crawler.should_process_message(mock_message)
            self.assertEqual(
                should_process,
                case["should_match"],
                f"Message '{case['text']}' should_match={case['should_match']}",
            )

            # 测试提取的关键词
            if case["should_match"]:
                keywords = self.crawler.extract_keywords_from_message(mock_message)
                for expected_keyword in case["expected_keywords"]:
                    self.assertIn(expected_keyword, keywords)

    def test_message_data_extraction(self):
        """测试消息数据提取功能"""
        mock_message = Mock(
            id=12345,
            text="🚀 Coinbase listing announcement for XYZ token!",
            date=datetime(2024, 1, 15, 10, 30, 0),
            sender_id=67890,
            chat_id=11111,
            views=1250,
            forwards=89,
        )

        # 模拟频道信息
        mock_chat = Mock(id=11111, title="Crypto News Channel", username="crypto_news")

        extracted_data = self.crawler.extract_message_data(mock_message, mock_chat)

        # 验证提取的数据
        self.assertEqual(extracted_data["message_id"], 12345)
        self.assertEqual(
            extracted_data["text"], "🚀 Coinbase listing announcement for XYZ token!"
        )
        self.assertEqual(extracted_data["timestamp"], datetime(2024, 1, 15, 10, 30, 0))
        self.assertEqual(extracted_data["sender_id"], 67890)
        self.assertEqual(extracted_data["chat_id"], 11111)
        self.assertEqual(extracted_data["chat_title"], "Crypto News Channel")
        self.assertEqual(extracted_data["chat_username"], "crypto_news")
        self.assertEqual(extracted_data["views"], 1250)
        self.assertEqual(extracted_data["forwards"], 89)

        # 验证关键词提取
        self.assertIn("keywords", extracted_data)
        self.assertIn("coinbase", extracted_data["keywords"])
        self.assertIn("listing", extracted_data["keywords"])

    @patch("telethon.TelegramClient")
    async def test_client_connection_handling(self, mock_client_class):
        """测试Telegram客户端连接处理"""
        # 模拟客户端实例
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # 测试连接成功
        mock_client.connect.return_value = True
        mock_client.is_user_authorized.return_value = True

        success = await self.crawler.connect_client()
        self.assertTrue(success)

        # 验证客户端方法被调用
        mock_client.connect.assert_called_once()
        mock_client.is_user_authorized.assert_called_once()

    @patch("telethon.TelegramClient")
    async def test_client_connection_failure(self, mock_client_class):
        """测试Telegram客户端连接失败"""
        # 模拟客户端实例
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # 测试连接失败
        mock_client.connect.side_effect = Exception("Connection failed")

        success = await self.crawler.connect_client()
        self.assertFalse(success)

        # 验证错误被记录
        self.mock_logger.error.assert_called()


if __name__ == "__main__":
    # 运行异步测试需要特殊处理
    unittest.main()
