# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - 网页爬虫实现
基于BaseCrawler的网页内容抓取器
"""

import sys
import os
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

from .base_crawler import (
    BaseCrawler,
    CrawlRequest,
    CrawlResponse,
    CrawlResult,
    CrawlerStatus,
    RequestMethod,
)
from ..config import ConfigManager
from ..utils import Logger
from ..zmq_client import ZMQPublisher, NewsMessage


class WebCrawler(BaseCrawler):
    """
    网页爬虫实现类
    负责抓取和解析网页内容
    """

    def __init__(
        self, config: ConfigManager, logger: Logger, zmq_publisher: ZMQPublisher = None
    ):
        super().__init__(config, logger, zmq_publisher)

        # 网页爬虫特定配置
        self.web_config = config.get_config("crawler.web", {})
        self.default_timeout = self.web_config.get("timeout", 30)
        self.max_retries = self.web_config.get("max_retries", 3)
        self.follow_redirects = self.web_config.get("follow_redirects", True)

        # CSS选择器配置
        self.selectors = self.web_config.get("selectors", {})

        self.logger.info("WebCrawler初始化完成")

    def crawl(
        self, url: str, selectors: Dict[str, str] = None, **kwargs
    ) -> CrawlResult:
        """
        爬取指定URL的内容

        Args:
            url: 目标URL
            selectors: CSS选择器字典
            **kwargs: 其他参数

        Returns:
            CrawlResult: 爬取结果
        """
        start_time = time.time()

        try:
            # 创建爬取请求
            request = CrawlRequest(
                url=url,
                method=RequestMethod.GET,
                timeout=kwargs.get("timeout", self.default_timeout),
                retries=kwargs.get("retries", self.max_retries),
            )

            # 执行请求
            response = self._make_request(request)
            if not response:
                return CrawlResult(
                    success=False,
                    url=url,
                    data=[],
                    error="请求失败",
                    processing_time=time.time() - start_time,
                )

            # 解析内容
            data = self._parse_content(response, selectors or self.selectors)

            # 创建结果
            result = CrawlResult(
                success=True,
                url=url,
                data=data,
                response=response,
                processing_time=time.time() - start_time,
            )

            # 发布消息
            if self.zmq_publisher and data:
                self._publish_data(data, url)

            self.logger.info(f"网页爬取完成: {url} | 数据条数: {len(data)}")
            return result

        except Exception as e:
            self.logger.error(f"网页爬取失败: {url} | 错误: {e}")
            return CrawlResult(
                success=False,
                url=url,
                data=[],
                error=str(e),
                processing_time=time.time() - start_time,
            )

    def _make_request(self, request: CrawlRequest) -> Optional[CrawlResponse]:
        """
        执行HTTP请求

        Args:
            request: 爬取请求

        Returns:
            CrawlResponse: 响应对象
        """
        try:
            # 应用反爬虫策略
            self.anti_spider.apply_delay(request.url)

            # 准备请求头
            headers = self.anti_spider.prepare_headers(request.headers)

            # 获取代理
            proxies = self.anti_spider.get_random_proxy()

            # 执行请求
            start_time = time.time()
            response = requests.get(
                request.url,
                headers=headers,
                params=request.params,
                cookies=request.cookies,
                timeout=request.timeout,
                proxies=proxies,
                allow_redirects=self.follow_redirects,
            )
            response_time = time.time() - start_time

            # 记录请求
            self.anti_spider.record_request(request.url)

            # 检查响应状态
            response.raise_for_status()

            # 创建响应对象
            crawl_response = CrawlResponse(
                url=response.url,
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                encoding=response.encoding or "utf-8",
                response_time=response_time,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

            return crawl_response

        except requests.RequestException as e:
            self.logger.error(f"HTTP请求失败: {request.url} | 错误: {e}")
            return None
        except Exception as e:
            self.logger.error(f"请求处理异常: {request.url} | 错误: {e}")
            return None

    def _parse_content(
        self, response: CrawlResponse, selectors: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        解析网页内容

        Args:
            response: HTTP响应
            selectors: CSS选择器字典

        Returns:
            List[Dict]: 解析后的数据列表
        """
        try:
            soup = BeautifulSoup(response.content, "html.parser")
            data_list = []

            # 如果没有选择器，返回基本信息
            if not selectors:
                return [
                    {
                        "url": response.url,
                        "title": soup.title.string if soup.title else "",
                        "content": soup.get_text()[:1000],  # 限制内容长度
                        "timestamp": response.timestamp,
                    }
                ]

            # 查找容器元素
            container_selector = selectors.get("container", "body")
            containers = soup.select(container_selector)

            if not containers:
                self.logger.warning(f"未找到容器元素: {container_selector}")
                return []

            # 解析每个容器
            for container in containers:
                item_data = {}

                # 提取各字段
                for field, selector in selectors.items():
                    if field == "container":
                        continue

                    elements = container.select(selector)
                    if elements:
                        if field.endswith("_list"):
                            # 列表字段
                            item_data[field] = [
                                elem.get_text().strip() for elem in elements
                            ]
                        elif field.endswith("_link"):
                            # 链接字段
                            item_data[field] = urljoin(
                                response.url, elements[0].get("href", "")
                            )
                        elif field.endswith("_image"):
                            # 图片字段
                            item_data[field] = urljoin(
                                response.url, elements[0].get("src", "")
                            )
                        else:
                            # 文本字段
                            item_data[field] = elements[0].get_text().strip()
                    else:
                        item_data[field] = ""

                # 添加元数据
                item_data.update(
                    {
                        "source_url": response.url,
                        "crawl_timestamp": response.timestamp,
                        "source_type": "web",
                    }
                )

                if item_data:
                    data_list.append(item_data)

            return data_list

        except Exception as e:
            self.logger.error(f"内容解析失败: {response.url} | 错误: {e}")
            return []

    def _publish_data(self, data: List[Dict[str, Any]], source_url: str) -> None:
        """
        发布爬取数据到ZMQ

        Args:
            data: 爬取的数据
            source_url: 数据源URL
        """
        try:
            for item in data:
                message = NewsMessage(
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    source=item.get("source", "web"),
                    url=source_url,
                    timestamp=item.get("crawl_timestamp", ""),
                    metadata=item,
                )

                self.zmq_publisher.publish_message(message)

        except Exception as e:
            self.logger.error(f"数据发布失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取爬虫状态

        Returns:
            Dict: 状态信息
        """
        return {
            "type": "web_crawler",
            "status": self.status.value,
            "config": self.web_config,
            "stats": {
                "requests_made": len(self.anti_spider.request_history),
                "domains_accessed": list(self.anti_spider.request_history.keys()),
            },
        }

    def validate_url(self, url: str) -> bool:
        """
        验证URL格式

        Args:
            url: 待验证的URL

        Returns:
            bool: 是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def get_start_urls(self) -> List[str]:
        """
        获取起始URL列表

        Returns:
            List[str]: 起始URL列表
        """
        # 从配置中获取起始URL
        start_urls = self.web_config.get("start_urls", [])
        return start_urls if isinstance(start_urls, list) else [start_urls]

    def parse_response(self, response: CrawlResponse) -> List[Dict[str, Any]]:
        """
        解析响应内容

        Args:
            response: 爬虫响应对象

        Returns:
            List[Dict[str, Any]]: 解析出的数据列表
        """
        return self._parse_content(response, self.selectors)

    def extract_links(self, response: CrawlResponse) -> List[str]:
        """
        提取页面中的所有链接

        Args:
            response: HTTP响应

        Returns:
            List[str]: 链接列表
        """
        try:
            soup = BeautifulSoup(response.content, "html.parser")
            links = []

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if response.url:
                    href = urljoin(response.url, href)

                if self.validate_url(href):
                    links.append(href)

            return list(set(links))  # 去重

        except Exception as e:
            self.logger.error(f"链接提取失败: {e}")
            return []

    def parse_html_content(
        self, html_content: str, url: str, extraction_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        解析HTML内容并根据规则提取数据

        Args:
            html_content: HTML内容字符串
            url: 页面URL
            extraction_rules: 提取规则字典

        Returns:
            Dict[str, Any]: 提取的数据
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            result = {}

            for field, selector in extraction_rules.items():
                try:
                    elements = soup.select(selector)

                    if not elements:
                        # 如果是列表字段，返回空列表；否则返回空字符串
                        if field.endswith("_list") or field in ["content", "tags"]:
                            result[field] = []
                        else:
                            result[field] = ""
                        continue

                    # 根据字段类型处理数据
                    if field in ["content", "tags"] or field.endswith("_list"):
                        # 列表字段：提取所有匹配元素的文本
                        result[field] = [
                            elem.get_text().strip()
                            for elem in elements
                            if elem.get_text().strip()
                        ]
                    elif field.endswith("_link"):
                        # 链接字段：提取href属性
                        result[field] = urljoin(url, elements[0].get("href", ""))
                    elif field.endswith("_image"):
                        # 图片字段：提取src属性
                        result[field] = urljoin(url, elements[0].get("src", ""))
                    else:
                        # 文本字段：提取第一个元素的文本
                        result[field] = elements[0].get_text().strip()

                except Exception as e:
                    self.logger.warning(f"提取字段 {field} 失败: {e}")
                    # 设置默认值
                    if field in ["content", "tags"] or field.endswith("_list"):
                        result[field] = []
                    else:
                        result[field] = ""

            return result

        except Exception as e:
            self.logger.error(f"HTML解析失败: {e}")
            return {}

    def is_valid_url(self, url: str) -> bool:
        """
        验证URL是否有效且安全

        Args:
            url: 待验证的URL

        Returns:
            bool: 是否有效
        """
        if not url or not isinstance(url, str):
            return False

        try:
            result = urlparse(url)

            # 检查协议
            if result.scheme not in ["http", "https"]:
                return False

            # 检查域名
            if not result.netloc:
                return False

            # 检查危险协议
            dangerous_schemes = ["javascript", "data", "vbscript"]
            if result.scheme.lower() in dangerous_schemes:
                return False

            return True

        except Exception:
            return False

    def fetch_page_with_retry(
        self, url: str, max_retries: int = 3, timeout: int = 30
    ) -> Optional[requests.Response]:
        """
        带重试机制的页面获取

        Args:
            url: 目标URL
            max_retries: 最大重试次数
            timeout: 超时时间

        Returns:
            响应对象或None
        """
        for attempt in range(max_retries):
            try:
                # 发起请求
                response = requests.get(
                    url, timeout=timeout, allow_redirects=self.follow_redirects
                )

                # 检查响应状态
                response.raise_for_status()

                self.logger.info(f"页面获取成功: {url} (尝试 {attempt + 1}/{max_retries})")
                return response

            except Exception as e:
                self.logger.warning(
                    f"页面获取失败 (尝试 {attempt + 1}/{max_retries}): {url} | 错误: {e}"
                )

                if attempt == max_retries - 1:
                    self.logger.error(f"页面获取最终失败: {url}")
                    return None

                # 重试前等待
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # 指数退避

        return None

    def filter_extracted_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤和清理提取的内容

        Args:
            content: 原始提取的内容

        Returns:
            Dict[str, Any]: 清理后的内容
        """
        filtered = {}

        for key, value in content.items():
            if value is None:
                continue  # 跳过None值

            if isinstance(value, str):
                # 字符串：去除首尾空白
                cleaned = value.strip()
                if cleaned:  # 只保留非空字符串
                    filtered[key] = cleaned

            elif isinstance(value, list):
                # 列表：过滤空值和空白字符串
                cleaned_list = []
                for item in value:
                    if isinstance(item, str):
                        cleaned_item = item.strip()
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    elif item is not None:
                        cleaned_list.append(item)

                if cleaned_list:  # 只保留非空列表
                    filtered[key] = cleaned_list

            else:
                # 其他类型：直接保留
                filtered[key] = value

        return filtered
