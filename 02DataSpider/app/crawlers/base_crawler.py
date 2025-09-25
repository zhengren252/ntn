# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - 爬虫基础类
定义通用爬虫接口和反爬虫策略
"""

import sys
import os
import time
import random
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from enum import Enum
import os

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

from ..config import ConfigManager
from ..utils import Logger
from ..zmq_client import ZMQPublisher, NewsMessage


class CrawlerStatus(Enum):
    """爬虫状态枚举"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class RequestMethod(Enum):
    """请求方法枚举"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class CrawlRequest:
    """爬虫请求数据结构"""

    url: str
    method: RequestMethod = RequestMethod.GET
    headers: Dict[str, str] = None
    params: Dict[str, Any] = None
    data: Dict[str, Any] = None
    cookies: Dict[str, str] = None
    timeout: int = 30
    retries: int = 3
    priority: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.params is None:
            self.params = {}
        if self.data is None:
            self.data = {}
        if self.cookies is None:
            self.cookies = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CrawlResponse:
    """爬虫响应数据结构"""

    url: str
    status_code: int
    content: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    encoding: str
    response_time: float
    timestamp: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CrawlResult:
    """爬虫结果数据结构"""

    success: bool
    url: str
    data: List[Dict[str, Any]]
    error: Optional[str] = None
    response: Optional[CrawlResponse] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AntiSpiderStrategy:
    """反爬虫策略类"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger
        self.ua = UserAgent()

        # 反爬虫配置
        self.anti_spider_config = config.get_config("scrapy.anti_spider", {})
        # use_proxy: 环境变量优先，其次配置项，提供稳健布尔解析
        self.use_proxy = self._parse_bool(
            os.getenv("USE_PROXY", self.anti_spider_config.get("use_proxy", False))
        )
        self.min_delay = self.anti_spider_config.get("min_delay", 1)
        self.max_delay = self.anti_spider_config.get("max_delay", 5)
        self.user_agents = self.anti_spider_config.get("user_agents", [])
        # 同时兼容 proxy_list 与 proxies 两种键名
        self.proxy_list = self.anti_spider_config.get(
            "proxy_list", self.anti_spider_config.get("proxies", [])
        )

        # 请求历史记录
        self.request_history = {}
        self.last_request_time = {}

        self.logger.info("反爬虫策略初始化完成")

    @staticmethod
    def _parse_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return value != 0
        s = str(value).strip().lower()
        if s in ("1", "true", "t", "yes", "y", "on"):
            return True
        if s in ("0", "false", "f", "no", "n", "off", ""):
            return False
        return default

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        if self.user_agents:
            return random.choice(self.user_agents)

        try:
            return self.ua.random
        except Exception as e:
            self.logger.warning(f"获取随机User-Agent失败: {e}")
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """获取随机代理"""
        if not self.proxy_list:
            return None

        proxy = random.choice(self.proxy_list)
        return {"http": proxy, "https": proxy}

    def calculate_delay(self, domain: str) -> float:
        """计算请求延迟"""
        # 基础随机延迟
        base_delay = random.uniform(self.min_delay, self.max_delay)

        # 根据域名历史请求频率调整
        if domain in self.request_history:
            request_count = self.request_history[domain]
            # 请求越多，延迟越长
            frequency_factor = min(request_count / 100, 2.0)
            base_delay *= 1 + frequency_factor

        return base_delay

    def should_delay(self, domain: str) -> bool:
        """检查是否需要延迟"""
        if domain not in self.last_request_time:
            return False

        last_time = self.last_request_time[domain]
        time_diff = time.time() - last_time
        min_interval = self.min_delay

        return time_diff < min_interval

    def record_request(self, url: str) -> None:
        """记录请求历史"""
        domain = urlparse(url).netloc

        # 更新请求计数
        if domain not in self.request_history:
            self.request_history[domain] = 0
        self.request_history[domain] += 1

        # 更新最后请求时间
        self.last_request_time[domain] = time.time()

    def apply_delay(self, url: str) -> None:
        """应用延迟策略"""
        domain = urlparse(url).netloc

        if self.should_delay(domain):
            delay = self.calculate_delay(domain)
            self.logger.debug(f"应用延迟策略: {domain} | 延迟: {delay:.2f}s")
            time.sleep(delay)

    def prepare_headers(self, base_headers: Dict[str, str] = None) -> Dict[str, str]:
        """准备请求头"""
        headers = base_headers.copy() if base_headers else {}

        # 设置User-Agent
        if "User-Agent" not in headers:
            headers["User-Agent"] = self.get_random_user_agent()

        # 设置常见请求头
        default_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        for key, value in default_headers.items():
            if key not in headers:
                headers[key] = value

        return headers


class BaseCrawler(ABC):
    """爬虫基础类

    定义所有爬虫的通用接口和功能
    """

    def __init__(
        self,
        config: ConfigManager,
        logger: Logger = None,
        publisher: ZMQPublisher = None,
    ):
        """初始化爬虫

        Args:
            config: 配置管理器
            logger: 日志记录器
            publisher: ZMQ发布器
        """
        self.config = config
        self.logger = logger or Logger(config)
        self.publisher = publisher

        # 爬虫状态
        self.status = CrawlerStatus.IDLE
        self.start_time = None
        self.stop_time = None

        # 统计信息
        self.stats = {
            "requests_made": 0,
            "requests_successful": 0,
            "requests_failed": 0,
            "items_scraped": 0,
            "total_processing_time": 0.0,
            "last_activity_time": None,
        }

        # 反爬虫策略
        self.anti_spider = AntiSpiderStrategy(config, self.logger)

        # 请求会话
        self.session = requests.Session()
        # 禁用对环境变量代理的信任，避免容器级 HTTP(S)_PROXY 影响
        self.session.trust_env = False

        # 爬虫配置
        self.crawler_config = config.get_config("scrapy", {})
        self.concurrent_requests = self.crawler_config.get("concurrent_requests", 1)
        self.download_timeout = self.crawler_config.get("download_timeout", 30)

        self.logger.info(f"{self.__class__.__name__} 初始化完成")

    @abstractmethod
    def get_start_urls(self) -> List[str]:
        """获取起始URL列表

        Returns:
            起始URL列表
        """
        pass

    @abstractmethod
    def parse_response(self, response: CrawlResponse) -> List[Dict[str, Any]]:
        """解析响应内容

        Args:
            response: 爬虫响应对象

        Returns:
            解析出的数据列表
        """
        pass

    @abstractmethod
    def extract_links(self, response: CrawlResponse) -> List[str]:
        """提取页面链接

        Args:
            response: 爬虫响应对象

        Returns:
            提取的链接列表
        """
        pass

    def make_request(self, request: CrawlRequest) -> CrawlResponse:
        """发起HTTP请求

        Args:
            request: 爬虫请求对象

        Returns:
            爬虫响应对象
        """
        start_time = time.time()

        try:
            # 应用反爬虫策略
            self.anti_spider.apply_delay(request.url)

            # 准备请求头
            headers = self.anti_spider.prepare_headers(request.headers)

            # 获取代理（仅当 use_proxy 为 True 时注入）
            proxies = None
            if getattr(self.anti_spider, "use_proxy", False):
                proxies = self.anti_spider.get_random_proxy()

            # 发起请求
            response = self.session.request(
                method=request.method.value,
                url=request.url,
                headers=headers,
                params=request.params,
                data=request.data,
                cookies=request.cookies,
                proxies=proxies,
                timeout=request.timeout,
                allow_redirects=True,
            )

            # 记录请求历史
            self.anti_spider.record_request(request.url)

            # 更新统计
            self.stats["requests_made"] += 1
            self.stats["requests_successful"] += 1
            self.stats["last_activity_time"] = datetime.utcnow().isoformat()

            # 构建响应对象
            response_time = time.time() - start_time

            crawl_response = CrawlResponse(
                url=response.url,
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                encoding=response.encoding or "utf-8",
                response_time=response_time,
                timestamp=datetime.utcnow().isoformat(),
                metadata={
                    "request_method": request.method.value,
                    "proxy_used": bool(proxies),
                },
            )

            self.logger.debug(
                f"请求成功: {request.url} | "
                f"状态码: {response.status_code} | "
                f"耗时: {response_time:.3f}s"
            )

            return crawl_response

        except Exception as e:
            response_time = time.time() - start_time

            # 更新统计
            self.stats["requests_made"] += 1
            self.stats["requests_failed"] += 1

            self.logger.error(
                f"请求失败: {request.url} | " f"错误: {e} | " f"耗时: {response_time:.3f}s"
            )

            raise

    def crawl_url(self, url: str, **kwargs) -> CrawlResult:
        """爬取单个URL

        Args:
            url: 要爬取的URL
            **kwargs: 额外的请求参数

        Returns:
            爬取结果
        """
        start_time = time.time()

        try:
            # 创建请求对象
            request = CrawlRequest(url=url, **kwargs)

            # 发起请求
            response = self.make_request(request)

            # 解析响应
            data = self.parse_response(response)

            # 更新统计
            self.stats["items_scraped"] += len(data)
            processing_time = time.time() - start_time
            self.stats["total_processing_time"] += processing_time

            self.logger.info(
                f"爬取完成: {url} | " f"数据条数: {len(data)} | " f"耗时: {processing_time:.3f}s"
            )

            return CrawlResult(
                success=True,
                url=url,
                data=data,
                response=response,
                processing_time=processing_time,
                metadata={
                    "items_count": len(data),
                    "response_size": len(response.content),
                },
            )

        except Exception as e:
            processing_time = time.time() - start_time

            self.logger.error(f"爬取失败: {url} | 错误: {e}")

            return CrawlResult(
                success=False,
                url=url,
                data=[],
                error=str(e),
                processing_time=processing_time,
            )

    def start_crawling(self) -> None:
        """开始爬取"""
        if self.status == CrawlerStatus.RUNNING:
            self.logger.warning("爬虫已在运行中")
            return

        self.status = CrawlerStatus.RUNNING
        self.start_time = datetime.utcnow()

        self.logger.info(f"{self.__class__.__name__} 开始爬取")

        try:
            # 获取起始URL
            start_urls = self.get_start_urls()

            if not start_urls:
                self.logger.warning("没有找到起始URL")
                return

            # 爬取每个URL
            for url in start_urls:
                if self.status != CrawlerStatus.RUNNING:
                    break

                result = self.crawl_url(url)

                if result.success and result.data:
                    # 发布数据到ZMQ
                    self._publish_data(result.data, url)

        except Exception as e:
            self.status = CrawlerStatus.ERROR
            self.logger.error(f"爬取过程异常: {e}")
        finally:
            if self.status == CrawlerStatus.RUNNING:
                self.status = CrawlerStatus.IDLE

            self.stop_time = datetime.utcnow()
            self.logger.info(f"{self.__class__.__name__} 爬取结束")

    def stop_crawling(self) -> None:
        """停止爬取"""
        if self.status == CrawlerStatus.RUNNING:
            self.status = CrawlerStatus.STOPPED
            self.logger.info(f"{self.__class__.__name__} 停止爬取")

    def pause_crawling(self) -> None:
        """暂停爬取"""
        if self.status == CrawlerStatus.RUNNING:
            self.status = CrawlerStatus.PAUSED
            self.logger.info(f"{self.__class__.__name__} 暂停爬取")

    def resume_crawling(self) -> None:
        """恢复爬取"""
        if self.status == CrawlerStatus.PAUSED:
            self.status = CrawlerStatus.RUNNING
            self.logger.info(f"{self.__class__.__name__} 恢复爬取")

    def _publish_data(self, data: List[Dict[str, Any]], source_url: str) -> None:
        """发布数据到ZMQ

        Args:
            data: 要发布的数据列表
            source_url: 数据来源URL
        """
        if not self.publisher:
            return

        try:
            for item in data:
                # 创建新闻消息
                message = NewsMessage(
                    id=self._generate_message_id(item, source_url),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    source=self.__class__.__name__,
                    url=item.get("url", source_url),
                    timestamp=item.get("timestamp", datetime.utcnow().isoformat()),
                    category=item.get("category", "news"),
                    sentiment=item.get("sentiment"),
                    keywords=item.get("keywords", []),
                    metadata={
                        "crawler": self.__class__.__name__,
                        "source_url": source_url,
                        **item.get("metadata", {}),
                    },
                )

                # 发布消息
                self.publisher.publish_message(message)

        except Exception as e:
            self.logger.error(f"发布数据失败: {e}")

    def _generate_message_id(self, item: Dict[str, Any], source_url: str) -> str:
        """生成消息ID

        Args:
            item: 数据项
            source_url: 来源URL

        Returns:
            消息ID
        """
        # 使用标题、URL和时间戳生成唯一ID
        content = f"{item.get('title', '')}{source_url}{item.get('timestamp', '')}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        stats.update(
            {
                "status": self.status.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "stop_time": self.stop_time.isoformat() if self.stop_time else None,
                "crawler_name": self.__class__.__name__,
            }
        )

        # 计算成功率
        if stats["requests_made"] > 0:
            stats["success_rate"] = (
                stats["requests_successful"] / stats["requests_made"]
            )
        else:
            stats["success_rate"] = 0.0

        # 计算平均处理时间
        if stats["requests_successful"] > 0:
            stats["avg_processing_time"] = (
                stats["total_processing_time"] / stats["requests_successful"]
            )
        else:
            stats["avg_processing_time"] = 0.0

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        stats = self.get_stats()

        # 判断健康状态
        if self.status == CrawlerStatus.ERROR:
            status = "unhealthy"
        elif self.status == CrawlerStatus.RUNNING:
            status = "healthy"
        elif stats["success_rate"] >= 0.8:
            status = "healthy"
        elif stats["success_rate"] >= 0.5:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "crawler_status": self.status.value,
            "success_rate": stats["success_rate"],
            "requests_made": stats["requests_made"],
            "items_scraped": stats["items_scraped"],
            "last_activity_time": stats["last_activity_time"],
        }

    def __del__(self):
        """析构函数"""
        if hasattr(self, "session"):
            self.session.close()


if __name__ == "__main__":
    # 测试基础爬虫类
    from ..config import ConfigManager
    from ..utils import Logger

    class TestCrawler(BaseCrawler):
        """测试爬虫"""

        def get_start_urls(self) -> List[str]:
            return ["https://httpbin.org/html"]

        def parse_response(self, response: CrawlResponse) -> List[Dict[str, Any]]:
            soup = BeautifulSoup(response.content, "html.parser")
            title = soup.find("title")

            return [
                {
                    "title": title.text if title else "No Title",
                    "content": response.content[:200],
                    "url": response.url,
                    "timestamp": response.timestamp,
                }
            ]

        def extract_links(self, response: CrawlResponse) -> List[str]:
            soup = BeautifulSoup(response.content, "html.parser")
            links = []

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("http"):
                    links.append(href)
                else:
                    links.append(urljoin(response.url, href))

            return links

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建测试爬虫
    crawler = TestCrawler(config, logger)

    # 测试爬取
    print("开始测试爬虫...")
    crawler.start_crawling()

    # 显示统计信息
    stats = crawler.get_stats()
    print(f"爬虫统计: {stats}")

    # 健康检查
    health = crawler.health_check()
    print(f"健康状态: {health}")
