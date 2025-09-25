# -*- coding: utf-8 -*-
"""
爬虫模块
包含Scrapy网页爬虫和Telethon Telegram监听器
"""

from .scrapy_crawler import ScrapyCrawler
from .telegram_crawler import TelegramCrawler
from .base_crawler import BaseCrawler
from .web_crawler import WebCrawler

__all__ = ["ScrapyCrawler", "TelegramCrawler", "BaseCrawler", "WebCrawler"]
