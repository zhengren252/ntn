# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus (NTN) - 信息源爬虫模组
模组二：Info Crawler Module

核心设计理念：
- 微服务架构
- ZeroMQ消息总线通信
- 三环境严格隔离
- Docker容器化部署
- 数据质量保证

技术栈：Python + Scrapy + Telethon + ZeroMQ + Redis + SQLite
"""

__version__ = "1.0.0"
__author__ = "NeuroTrade Nexus Team"
__description__ = "信息源爬虫模组 - 从无API信息源抓取数据并通过ZeroMQ分发"

# 模块导入
from .config import ConfigManager
from .zmq_client import ZMQPublisher
from .utils import Logger, DataValidator

__all__ = ["ConfigManager", "ZMQPublisher", "Logger", "DataValidator"]
