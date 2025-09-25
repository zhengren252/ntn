# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - Scrapy网页爬虫引擎
实现新闻网站和金融数据源的专业爬取
"""

import sys
import os
import re
import json
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

import requests
from bs4 import BeautifulSoup, Tag
from lxml import html

from ..config import ConfigManager
from ..utils import Logger
from ..zmq_client import ZMQPublisher
from .base_crawler import BaseCrawler, CrawlResponse, CrawlRequest, RequestMethod


@dataclass
class NewsItem:
    """新闻数据项"""

    title: str
    content: str
    url: str
    timestamp: str
    author: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = None
    summary: Optional[str] = None
    image_url: Optional[str] = None
    source_name: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class NewsExtractor:
    """新闻内容提取器"""

    def __init__(self, logger: Logger):
        self.logger = logger

        # 常见新闻网站的选择器配置
        self.site_configs = {
            "coindesk.com": {
                "title": "h1.at-headline",
                "content": ".at-content-wrapper .at-text",
                "author": ".author-name",
                "timestamp": "time",
                "category": ".breadcrumb a",
            },
            "cointelegraph.com": {
                "title": "h1",
                "content": ".post-content",
                "author": ".post-meta__author",
                "timestamp": ".post-meta__publish-date",
                "category": ".breadcrumbs a",
            },
            "reuters.com": {
                "title": "h1[data-testid='Heading']",
                "content": "[data-testid='paragraph']",
                "author": "[data-testid='Author']",
                "timestamp": "time",
                "category": ".breadcrumb-item",
            },
            "bloomberg.com": {
                "title": "h1",
                "content": ".body-content p",
                "author": ".author",
                "timestamp": "time",
                "category": ".breadcrumb a",
            },
            "default": {
                "title": "h1, .title, .headline, [class*='title'], [class*='headline']",
                "content": ".content, .article-content, .post-content, [class*='content'], p",
                "author": ".author, .byline, [class*='author'], [class*='byline']",
                "timestamp": "time, .date, .timestamp, [class*='date'], [class*='time']",
                "category": ".category, .tag, [class*='category'], [class*='tag']",
            },
        }

    def extract_news_item(self, response: CrawlResponse) -> Optional[NewsItem]:
        """从响应中提取新闻项

        Args:
            response: 爬虫响应对象

        Returns:
            提取的新闻项或None
        """
        try:
            soup = BeautifulSoup(response.content, "html.parser")
            domain = urlparse(response.url).netloc

            # 获取站点配置
            config = self._get_site_config(domain)

            # 提取各个字段
            title = self._extract_title(soup, config)
            content = self._extract_content(soup, config)
            author = self._extract_author(soup, config)
            timestamp = self._extract_timestamp(soup, config, response.timestamp)
            category = self._extract_category(soup, config)
            tags = self._extract_tags(soup)
            summary = self._extract_summary(content)
            image_url = self._extract_image(soup, response.url)

            # 验证必需字段
            if not title or not content:
                self.logger.warning(f"缺少必需字段: {response.url}")
                return None

            # 清理和格式化内容
            title = self._clean_text(title)
            content = self._clean_text(content)

            if len(content) < 50:  # 内容太短，可能不是有效新闻
                self.logger.warning(f"内容太短: {response.url}")
                return None

            return NewsItem(
                title=title,
                content=content,
                url=response.url,
                timestamp=timestamp,
                author=author,
                category=category,
                tags=tags,
                summary=summary,
                image_url=image_url,
                source_name=domain,
            )

        except Exception as e:
            self.logger.error(f"提取新闻失败: {response.url} | 错误: {e}")
            return None

    def _get_site_config(self, domain: str) -> Dict[str, str]:
        """获取站点配置"""
        for site_domain, config in self.site_configs.items():
            if site_domain in domain:
                return config
        return self.site_configs["default"]

    def _extract_title(
        self, soup: BeautifulSoup, config: Dict[str, str]
    ) -> Optional[str]:
        """提取标题"""
        selectors = config.get("title", "").split(", ")

        for selector in selectors:
            if not selector.strip():
                continue

            element = soup.select_one(selector.strip())
            if element:
                return element.get_text(strip=True)

        # 备用方案：从meta标签提取
        meta_title = soup.find("meta", property="og:title")
        if meta_title:
            return meta_title.get("content", "").strip()

        # 最后备用：页面title
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        return None

    def _extract_content(
        self, soup: BeautifulSoup, config: Dict[str, str]
    ) -> Optional[str]:
        """提取正文内容"""
        selectors = config.get("content", "").split(", ")

        for selector in selectors:
            if not selector.strip():
                continue

            elements = soup.select(selector.strip())
            if elements:
                # 合并所有匹配元素的文本
                content_parts = []
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 20:  # 过滤太短的文本
                        content_parts.append(text)

                if content_parts:
                    return "\n\n".join(content_parts)

        # 备用方案：提取所有段落
        paragraphs = soup.find_all("p")
        if paragraphs:
            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    content_parts.append(text)

            if content_parts:
                return "\n\n".join(content_parts)

        return None

    def _extract_author(
        self, soup: BeautifulSoup, config: Dict[str, str]
    ) -> Optional[str]:
        """提取作者"""
        selectors = config.get("author", "").split(", ")

        for selector in selectors:
            if not selector.strip():
                continue

            element = soup.select_one(selector.strip())
            if element:
                author = element.get_text(strip=True)
                if author and len(author) < 100:  # 作者名不应该太长
                    return author

        # 备用方案：从meta标签提取
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            return meta_author.get("content", "").strip()

        return None

    def _extract_timestamp(
        self, soup: BeautifulSoup, config: Dict[str, str], fallback: str
    ) -> str:
        """提取时间戳"""
        selectors = config.get("timestamp", "").split(", ")

        for selector in selectors:
            if not selector.strip():
                continue

            element = soup.select_one(selector.strip())
            if element:
                # 尝试从datetime属性获取
                datetime_attr = element.get("datetime")
                if datetime_attr:
                    return self._normalize_timestamp(datetime_attr)

                # 从文本内容获取
                text = element.get_text(strip=True)
                if text:
                    normalized = self._normalize_timestamp(text)
                    if normalized:
                        return normalized

        # 备用方案：从meta标签提取
        meta_time = soup.find("meta", property="article:published_time")
        if meta_time:
            return self._normalize_timestamp(meta_time.get("content", ""))

        # 使用fallback时间戳
        return fallback

    def _extract_category(
        self, soup: BeautifulSoup, config: Dict[str, str]
    ) -> Optional[str]:
        """提取分类"""
        selectors = config.get("category", "").split(", ")

        for selector in selectors:
            if not selector.strip():
                continue

            elements = soup.select(selector.strip())
            if elements:
                categories = []
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and text.lower() not in ["home", "news", "首页", "新闻"]:
                        categories.append(text)

                if categories:
                    return categories[-1]  # 返回最后一个（通常是最具体的）

        return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """提取标签"""
        tags = set()

        # 从meta keywords提取
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            keywords = meta_keywords.get("content", "")
            for keyword in keywords.split(","):
                keyword = keyword.strip()
                if keyword:
                    tags.add(keyword)

        # 从标签元素提取
        tag_selectors = [".tag", ".tags", "[class*='tag']", ".label", ".labels"]
        for selector in tag_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) < 50:
                    tags.add(text)

        return list(tags)

    def _extract_summary(self, content: str) -> Optional[str]:
        """提取摘要"""
        if not content:
            return None

        # 取前200个字符作为摘要
        sentences = content.split("。")
        summary = ""

        for sentence in sentences:
            if len(summary + sentence) <= 200:
                summary += sentence + "。"
            else:
                break

        return summary.strip() if summary else content[:200] + "..."

    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """提取主图片"""
        # 从meta标签提取
        meta_image = soup.find("meta", property="og:image")
        if meta_image:
            image_url = meta_image.get("content", "")
            if image_url:
                return urljoin(base_url, image_url)

        # 从文章内容中提取第一张图片
        img_tags = soup.find_all("img")
        for img in img_tags:
            src = img.get("src")
            if src and not src.startswith("data:"):
                return urljoin(base_url, src)

        return None

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""

        # 移除多余的空白字符
        text = re.sub(r"\s+", " ", text)

        # 移除特殊字符
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        return text.strip()

    def _normalize_timestamp(self, timestamp_str: str) -> Optional[str]:
        """标准化时间戳"""
        if not timestamp_str:
            return None

        # 常见时间格式
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str.strip(), fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        # 尝试解析相对时间
        relative_patterns = [
            (
                r"(\d+)\s*小时前",
                lambda m: datetime.utcnow() - timedelta(hours=int(m.group(1))),
            ),
            (
                r"(\d+)\s*分钟前",
                lambda m: datetime.utcnow() - timedelta(minutes=int(m.group(1))),
            ),
            (
                r"(\d+)\s*天前",
                lambda m: datetime.utcnow() - timedelta(days=int(m.group(1))),
            ),
            (
                r"(\d+)\s*hours?\s*ago",
                lambda m: datetime.utcnow() - timedelta(hours=int(m.group(1))),
            ),
            (
                r"(\d+)\s*minutes?\s*ago",
                lambda m: datetime.utcnow() - timedelta(minutes=int(m.group(1))),
            ),
            (
                r"(\d+)\s*days?\s*ago",
                lambda m: datetime.utcnow() - timedelta(days=int(m.group(1))),
            ),
        ]

        for pattern, calc_func in relative_patterns:
            match = re.search(pattern, timestamp_str, re.IGNORECASE)
            if match:
                dt = calc_func(match)
                return dt.isoformat() + "Z"

        return None


class ScrapyCrawler(BaseCrawler):
    """Scrapy网页爬虫

    专门用于爬取新闻网站和金融数据源
    """

    def __init__(
        self,
        config: ConfigManager,
        logger: Logger = None,
        publisher: ZMQPublisher = None,
    ):
        """初始化Scrapy爬虫

        Args:
            config: 配置管理器
            logger: 日志记录器
            publisher: ZMQ发布器
        """
        super().__init__(config, logger, publisher)

        # 新闻提取器
        self.news_extractor = NewsExtractor(self.logger)

        # 爬虫特定配置
        self.scrapy_config = config.get_config("scrapy", {})
        self.target_sites = self.scrapy_config.get("target_sites", [])
        self.max_pages_per_site = self.scrapy_config.get("max_pages_per_site", 10)
        self.follow_links = self.scrapy_config.get("follow_links", True)

        # 已访问URL集合（避免重复爬取）
        self.visited_urls: Set[str] = set()

        # URL队列
        self.url_queue: List[str] = []

        self.logger.info(f"Scrapy爬虫初始化完成，目标站点: {len(self.target_sites)}")

    def get_start_urls(self) -> List[str]:
        """获取起始URL列表

        Returns:
            起始URL列表
        """
        start_urls = []

        # 从配置中获取目标站点
        for site_config in self.target_sites:
            if isinstance(site_config, str):
                start_urls.append(site_config)
            elif isinstance(site_config, dict):
                url = site_config.get("url")
                if url:
                    start_urls.append(url)

        # 默认新闻站点（如果配置为空）
        if not start_urls:
            default_sites = [
                "https://www.coindesk.com/",
                "https://cointelegraph.com/",
                "https://www.reuters.com/technology/",
                "https://www.bloomberg.com/crypto",
            ]
            start_urls.extend(default_sites)

        self.logger.info(f"获取到 {len(start_urls)} 个起始URL")
        return start_urls

    def parse_response(self, response: CrawlResponse) -> List[Dict[str, Any]]:
        """解析响应内容

        Args:
            response: 爬虫响应对象

        Returns:
            解析出的数据列表
        """
        data = []

        try:
            # 检查是否为新闻详情页
            if self._is_article_page(response):
                # 提取新闻内容
                news_item = self.news_extractor.extract_news_item(response)
                if news_item:
                    data.append(
                        {
                            "title": news_item.title,
                            "content": news_item.content,
                            "url": news_item.url,
                            "timestamp": news_item.timestamp,
                            "author": news_item.author,
                            "category": news_item.category or "news",
                            "tags": news_item.tags,
                            "summary": news_item.summary,
                            "image_url": news_item.image_url,
                            "source_name": news_item.source_name,
                            "keywords": self._extract_keywords(news_item.content),
                            "sentiment": None,  # 将在后续处理中分析
                            "metadata": {
                                "crawler_type": "scrapy",
                                "extraction_time": datetime.utcnow().isoformat(),
                                "content_length": len(news_item.content),
                            },
                        }
                    )

            # 如果启用了链接跟踪，提取更多链接
            if self.follow_links:
                links = self.extract_links(response)
                self._add_links_to_queue(links)

        except Exception as e:
            self.logger.error(f"解析响应失败: {response.url} | 错误: {e}")

        return data

    def extract_links(self, response: CrawlResponse) -> List[str]:
        """提取页面链接

        Args:
            response: 爬虫响应对象

        Returns:
            提取的链接列表
        """
        links = []

        try:
            soup = BeautifulSoup(response.content, "html.parser")
            domain = urlparse(response.url).netloc

            # 查找所有链接
            for link in soup.find_all("a", href=True):
                href = link["href"]

                # 转换为绝对URL
                if href.startswith("http"):
                    full_url = href
                else:
                    full_url = urljoin(response.url, href)

                # 过滤链接
                if self._should_follow_link(full_url, domain):
                    links.append(full_url)

            self.logger.debug(f"从 {response.url} 提取到 {len(links)} 个链接")

        except Exception as e:
            self.logger.error(f"提取链接失败: {response.url} | 错误: {e}")

        return links

    def start_crawling(self) -> None:
        """开始爬取（重写以支持链接跟踪）"""
        if self.status.value == "running":
            self.logger.warning("爬虫已在运行中")
            return

        self.status = type(self.status)("running")
        self.start_time = datetime.utcnow()

        self.logger.info(f"{self.__class__.__name__} 开始爬取")

        try:
            # 获取起始URL并添加到队列
            start_urls = self.get_start_urls()
            self.url_queue.extend(start_urls)

            # 处理URL队列
            while self.url_queue and self.status.value == "running":
                url = self.url_queue.pop(0)

                # 检查是否已访问
                if url in self.visited_urls:
                    continue

                # 检查每个站点的页面限制
                domain = urlparse(url).netloc
                domain_count = sum(
                    1
                    for visited_url in self.visited_urls
                    if urlparse(visited_url).netloc == domain
                )

                if domain_count >= self.max_pages_per_site:
                    self.logger.debug(f"站点 {domain} 已达到页面限制: {self.max_pages_per_site}")
                    continue

                # 爬取URL
                result = self.crawl_url(url)
                self.visited_urls.add(url)

                if result.success and result.data:
                    # 发布数据到ZMQ
                    self._publish_data(result.data, url)

                # 控制爬取速度
                time.sleep(0.5)

        except Exception as e:
            self.status = type(self.status)("error")
            self.logger.error(f"爬取过程异常: {e}")
        finally:
            if self.status.value == "running":
                self.status = type(self.status)("idle")

            self.stop_time = datetime.utcnow()
            self.logger.info(
                f"{self.__class__.__name__} 爬取结束 | "
                f"访问页面: {len(self.visited_urls)} | "
                f"队列剩余: {len(self.url_queue)}"
            )

    def _is_article_page(self, response: CrawlResponse) -> bool:
        """判断是否为文章详情页

        Args:
            response: 爬虫响应对象

        Returns:
            是否为文章页面
        """
        # 通过URL模式判断
        url_patterns = [
            r"/article/",
            r"/news/",
            r"/post/",
            r"/\d{4}/\d{2}/\d{2}/",  # 日期格式
            r"/[a-zA-Z0-9-]+/$",  # 文章slug
        ]

        for pattern in url_patterns:
            if re.search(pattern, response.url):
                return True

        # 通过内容特征判断
        try:
            soup = BeautifulSoup(response.content, "html.parser")

            # 检查是否有文章结构
            article_indicators = [
                soup.find("article"),
                soup.find(attrs={"class": re.compile(r"article|post|content")}),
                soup.find("h1") and len(soup.find_all("p")) > 3,
            ]

            return any(article_indicators)

        except Exception:
            return False

    def _should_follow_link(self, url: str, base_domain: str) -> bool:
        """判断是否应该跟踪链接

        Args:
            url: 链接URL
            base_domain: 基础域名

        Returns:
            是否应该跟踪
        """
        try:
            parsed = urlparse(url)

            # 只跟踪同域名链接
            if parsed.netloc != base_domain:
                return False

            # 过滤不需要的链接
            exclude_patterns = [
                r"\.(jpg|jpeg|png|gif|pdf|doc|docx|zip)$",
                r"/tag/",
                r"/category/",
                r"/author/",
                r"/search",
                r"/login",
                r"/register",
                r"/contact",
                r"/about",
                r"#",
                r"javascript:",
                r"mailto:",
            ]

            for pattern in exclude_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False

            # 检查是否已访问
            if url in self.visited_urls:
                return False

            # 检查是否已在队列中
            if url in self.url_queue:
                return False

            return True

        except Exception:
            return False

    def _add_links_to_queue(self, links: List[str]) -> None:
        """添加链接到队列

        Args:
            links: 链接列表
        """
        added_count = 0

        for link in links:
            if link not in self.url_queue and link not in self.visited_urls:
                self.url_queue.append(link)
                added_count += 1

        if added_count > 0:
            self.logger.debug(f"添加 {added_count} 个链接到队列，队列总数: {len(self.url_queue)}")

    def _extract_keywords(self, content: str) -> List[str]:
        """从内容中提取关键词

        Args:
            content: 文本内容

        Returns:
            关键词列表
        """
        if not content:
            return []

        # 金融和加密货币相关关键词
        financial_keywords = [
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "crypto",
            "cryptocurrency",
            "blockchain",
            "defi",
            "nft",
            "trading",
            "market",
            "price",
            "bull",
            "bear",
            "support",
            "resistance",
            "volume",
            "analysis",
            "forecast",
            "signal",
            "breakout",
            "rally",
            "correction",
            "investment",
            "portfolio",
            "risk",
            "return",
            "yield",
            "stock",
            "bond",
            "commodity",
            "forex",
            "futures",
            "options",
        ]

        content_lower = content.lower()
        found_keywords = []

        for keyword in financial_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)

        return found_keywords

    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息（扩展版本）

        Returns:
            统计信息字典
        """
        stats = super().get_stats()

        # 添加Scrapy特定统计
        stats.update(
            {
                "visited_urls_count": len(self.visited_urls),
                "queue_size": len(self.url_queue),
                "target_sites_count": len(self.target_sites),
                "max_pages_per_site": self.max_pages_per_site,
                "follow_links_enabled": self.follow_links,
            }
        )

        return stats


if __name__ == "__main__":
    # 测试Scrapy爬虫
    from ..config import ConfigManager
    from ..utils import Logger
    from ..zmq_client import ZMQPublisher

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建ZMQ发布器（可选）
    try:
        publisher = ZMQPublisher(config, logger)
    except Exception as e:
        logger.warning(f"无法创建ZMQ发布器: {e}")
        publisher = None

    # 创建Scrapy爬虫
    crawler = ScrapyCrawler(config, logger, publisher)

    # 测试爬取
    print("开始测试Scrapy爬虫...")
    crawler.start_crawling()

    # 显示统计信息
    stats = crawler.get_stats()
    print(f"\n爬虫统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    # 健康检查
    health = crawler.health_check()
    print(f"\n健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
