#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页爬虫单元测试

测试用例:
- UNIT-CRAWL-01: HTML内容解析
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from datetime import datetime

from app.crawlers.base_crawler import (
    BaseCrawler,
    CrawlRequest,
    CrawlResponse,
    CrawlResult,
)
from app.crawlers.web_crawler import WebCrawler


class TestWebCrawler(unittest.TestCase):
    """网页爬虫测试类"""

    def setUp(self):
        """测试前准备"""
        # 模拟配置
        self.mock_config = Mock()
        self.mock_config.get.return_value = {
            "web_crawler": {
                "timeout": 30,
                "max_retries": 3,
                "delay_between_requests": 1,
                "user_agent": "TestCrawler/1.0",
            }
        }

        # 模拟日志
        self.mock_logger = Mock()

        # 创建爬虫实例
        self.crawler = WebCrawler(self.mock_config, self.mock_logger)

    def test_unit_crawl_01_html_content_parsing(self):
        """UNIT-CRAWL-01: HTML内容解析

        Mock一个HTTP请求的响应，返回一个预设的HTML字符串。
        测试网页爬虫能否根据CSS选择器正确提取信息。
        """
        # 预设的HTML内容
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bitcoin Price Analysis</title>
            <meta name="description" content="Latest Bitcoin price analysis and market trends">
        </head>
        <body>
            <article class="news-article">
                <h1 class="article-title">Bitcoin Breaks $50,000 Resistance</h1>
                <div class="article-meta">
                    <span class="author">John Doe</span>
                    <time class="publish-date" datetime="2024-01-15T10:30:00Z">2024-01-15 10:30:00</time>
                    <span class="category">Cryptocurrency</span>
                </div>
                <div class="article-content">
                    <p>Bitcoin has successfully broken through the $50,000 resistance level today.</p>
                    <p>Market analysts are optimistic about the future price movements.</p>
                    <div class="tags">
                        <span class="tag">bitcoin</span>
                        <span class="tag">cryptocurrency</span>
                        <span class="tag">price</span>
                        <span class="tag">analysis</span>
                    </div>
                </div>
                <div class="article-stats">
                    <span class="views">1250</span>
                    <span class="likes">89</span>
                </div>
            </article>
        </body>
        </html>
        """

        # 模拟HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = test_html
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.url = "https://example.com/bitcoin-analysis"

        # 定义提取规则
        extraction_rules = {
            "title": "h1.article-title",
            "author": ".author",
            "publish_date": "time.publish-date",
            "category": ".category",
            "content": ".article-content p",
            "tags": ".tag",
            "views": ".views",
            "likes": ".likes",
        }

        # Mock requests.get方法
        with patch("requests.get", return_value=mock_response):
            # 执行内容解析
            result = self.crawler.parse_html_content(
                test_html, "https://example.com/bitcoin-analysis", extraction_rules
            )

            # 验证提取结果
            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)

            # 验证标题提取
            self.assertEqual(result["title"], "Bitcoin Breaks $50,000 Resistance")

            # 验证作者提取
            self.assertEqual(result["author"], "John Doe")

            # 验证发布时间提取
            self.assertEqual(result["publish_date"], "2024-01-15 10:30:00")

            # 验证分类提取
            self.assertEqual(result["category"], "Cryptocurrency")

            # 验证内容提取（多个段落）
            self.assertIsInstance(result["content"], list)
            self.assertEqual(len(result["content"]), 2)
            self.assertIn("Bitcoin has successfully broken", result["content"][0])
            self.assertIn("Market analysts are optimistic", result["content"][1])

            # 验证标签提取（多个标签）
            self.assertIsInstance(result["tags"], list)
            self.assertEqual(len(result["tags"]), 4)
            self.assertIn("bitcoin", result["tags"])
            self.assertIn("cryptocurrency", result["tags"])
            self.assertIn("price", result["tags"])
            self.assertIn("analysis", result["tags"])

            # 验证统计数据提取
            self.assertEqual(result["views"], "1250")
            self.assertEqual(result["likes"], "89")

    def test_html_parsing_with_missing_elements(self):
        """测试HTML解析时缺少某些元素的情况"""
        # 不完整的HTML内容
        incomplete_html = """
        <html>
        <body>
            <h1>Title Only</h1>
            <!-- 缺少其他元素 -->
        </body>
        </html>
        """

        extraction_rules = {
            "title": "h1",
            "author": ".author",  # 不存在
            "content": ".content",  # 不存在
            "tags": ".tag",  # 不存在
        }

        result = self.crawler.parse_html_content(
            incomplete_html, "https://example.com/incomplete", extraction_rules
        )

        # 验证存在的元素被正确提取
        self.assertEqual(result["title"], "Title Only")

        # 验证不存在的元素返回空值或空列表
        self.assertIn("author", result)
        self.assertIn("content", result)
        self.assertIn("tags", result)

    def test_html_parsing_with_invalid_selectors(self):
        """测试使用无效CSS选择器的情况"""
        test_html = "<html><body><h1>Test</h1></body></html>"

        # 无效的CSS选择器
        invalid_rules = {
            "title": "h1[invalid syntax",  # 语法错误
            "content": "::invalid-pseudo",  # 无效伪选择器
        }

        # 应该能够处理无效选择器而不崩溃
        result = self.crawler.parse_html_content(
            test_html, "https://example.com/test", invalid_rules
        )

        self.assertIsInstance(result, dict)

    def test_url_validation(self):
        """测试URL验证功能"""
        # 有效URL
        valid_urls = [
            "https://example.com",
            "http://news.site.com/article",
            "https://crypto.news/bitcoin-analysis?id=123",
        ]

        for url in valid_urls:
            self.assertTrue(self.crawler.is_valid_url(url))

        # 无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # 不支持的协议
            "",
            None,
            "javascript:alert(1)",  # 危险协议
        ]

        for url in invalid_urls:
            self.assertFalse(self.crawler.is_valid_url(url))

    @patch("app.crawlers.web_crawler.requests.get")
    def test_request_with_retry_mechanism(self, mock_get):
        """测试请求重试机制"""
        # 模拟前两次请求失败，第三次成功
        mock_get.side_effect = [
            Exception("Connection timeout"),
            Exception("Server error"),
            Mock(status_code=200, text="<html>Success</html>"),
        ]

        url = "https://example.com/test"
        result = self.crawler.fetch_page_with_retry(url, max_retries=3)

        # 验证重试了3次
        self.assertEqual(mock_get.call_count, 3)

        # 验证最终成功
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 200)

    @patch("app.crawlers.web_crawler.requests.get")
    def test_request_timeout_handling(self, mock_get):
        """测试请求超时处理"""
        # 模拟超时异常
        mock_get.side_effect = Exception("Request timeout")

        url = "https://example.com/timeout"
        result = self.crawler.fetch_page_with_retry(url, max_retries=2)

        # 验证超时后返回None
        self.assertIsNone(result)

        # 验证重试了指定次数
        self.assertEqual(mock_get.call_count, 2)

    def test_content_filtering(self):
        """测试内容过滤功能"""
        # 测试数据
        raw_content = {
            "title": "  Bitcoin Price Analysis  ",  # 需要去除空白
            "content": ["", "Valid content", "   ", "Another valid content"],  # 需要过滤空内容
            "tags": ["bitcoin", "", "crypto", "   ", "analysis"],  # 需要过滤空标签
            "author": None,  # 空值
            "views": "1250",
        }

        filtered_content = self.crawler.filter_extracted_content(raw_content)

        # 验证标题被正确清理
        self.assertEqual(filtered_content["title"], "Bitcoin Price Analysis")

        # 验证内容列表被正确过滤
        self.assertEqual(len(filtered_content["content"]), 2)
        self.assertNotIn("", filtered_content["content"])
        self.assertNotIn("   ", filtered_content["content"])

        # 验证标签被正确过滤
        self.assertEqual(len(filtered_content["tags"]), 3)
        self.assertIn("bitcoin", filtered_content["tags"])
        self.assertIn("crypto", filtered_content["tags"])
        self.assertIn("analysis", filtered_content["tags"])

        # 验证空值被处理
        self.assertNotIn("author", filtered_content)  # 或者设为默认值

        # 验证有效值被保留
        self.assertEqual(filtered_content["views"], "1250")


if __name__ == "__main__":
    unittest.main()
