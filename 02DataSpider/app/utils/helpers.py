#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助工具模块

提供日期处理、字符串处理等通用辅助功能
"""

import re
import html
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import Optional, Union, List, Dict, Any
from urllib.parse import urlparse, urljoin, quote, unquote
import hashlib
import json


class DateHelper:
    """日期时间辅助工具类"""

    # 常用日期格式
    COMMON_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]

    @classmethod
    def parse_datetime(cls, date_string: str) -> Optional[datetime]:
        """解析日期时间字符串

        Args:
            date_string: 日期时间字符串

        Returns:
            解析后的datetime对象，失败返回None
        """
        if not date_string or not isinstance(date_string, str):
            return None

        # 清理字符串
        date_string = date_string.strip()

        # 尝试各种格式
        for fmt in cls.COMMON_FORMATS:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue

        # 尝试ISO格式解析
        try:
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        except ValueError:
            pass

        return None

    @classmethod
    def to_utc(cls, dt: datetime) -> datetime:
        """转换为UTC时间

        Args:
            dt: 日期时间对象

        Returns:
            UTC时间
        """
        if dt.tzinfo is None:
            # 假设为本地时间
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def to_iso_string(cls, dt: datetime) -> str:
        """转换为ISO格式字符串

        Args:
            dt: 日期时间对象

        Returns:
            ISO格式字符串
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @classmethod
    def now_utc(cls) -> datetime:
        """获取当前UTC时间"""
        return datetime.now(timezone.utc)

    @classmethod
    def now_iso(cls) -> str:
        """获取当前UTC时间的ISO字符串"""
        return cls.to_iso_string(cls.now_utc())

    @classmethod
    def time_ago(cls, dt: datetime) -> str:
        """计算时间差描述

        Args:
            dt: 目标时间

        Returns:
            时间差描述（如"2小时前"）
        """
        now = cls.now_utc()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}天前"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}小时前"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes}分钟前"
        else:
            return "刚刚"

    @classmethod
    def is_recent(cls, dt: datetime, hours: int = 24) -> bool:
        """检查时间是否在指定小时内

        Args:
            dt: 目标时间
            hours: 小时数

        Returns:
            是否在指定时间内
        """
        now = cls.now_utc()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now - dt
        return diff.total_seconds() <= hours * 3600


class StringHelper:
    """字符串处理辅助工具类"""

    # HTML标签正则表达式
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

    # 空白字符正则表达式
    WHITESPACE_PATTERN = re.compile(r"\s+")

    # URL正则表达式
    URL_PATTERN = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )

    # 邮箱正则表达式
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    @classmethod
    def clean_html(cls, text: str) -> str:
        """清理HTML标签

        Args:
            text: 包含HTML的文本

        Returns:
            清理后的纯文本
        """
        if not text:
            return ""

        # 解码HTML实体
        text = html.unescape(text)

        # 移除HTML标签
        text = cls.HTML_TAG_PATTERN.sub("", text)

        # 规范化空白字符
        text = cls.WHITESPACE_PATTERN.sub(" ", text)

        return text.strip()

    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """规范化空白字符

        Args:
            text: 输入文本

        Returns:
            规范化后的文本
        """
        if not text:
            return ""

        return cls.WHITESPACE_PATTERN.sub(" ", text).strip()

    @classmethod
    def truncate(cls, text: str, max_length: int, suffix: str = "...") -> str:
        """截断文本

        Args:
            text: 输入文本
            max_length: 最大长度
            suffix: 后缀

        Returns:
            截断后的文本
        """
        if not text or len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @classmethod
    def extract_urls(cls, text: str) -> List[str]:
        """提取文本中的URL

        Args:
            text: 输入文本

        Returns:
            URL列表
        """
        if not text:
            return []

        return cls.URL_PATTERN.findall(text)

    @classmethod
    def extract_emails(cls, text: str) -> List[str]:
        """提取文本中的邮箱地址

        Args:
            text: 输入文本

        Returns:
            邮箱地址列表
        """
        if not text:
            return []

        return cls.EMAIL_PATTERN.findall(text)

    @classmethod
    def normalize_url(cls, url: str, base_url: str = None) -> str:
        """规范化URL

        Args:
            url: 输入URL
            base_url: 基础URL（用于相对URL）

        Returns:
            规范化后的URL
        """
        if not url:
            return ""

        # 处理相对URL
        if base_url and not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)

        # 解析URL
        parsed = urlparse(url)

        # 规范化域名（转小写）
        netloc = parsed.netloc.lower()

        # 重构URL
        normalized = f"{parsed.scheme}://{netloc}{parsed.path}"

        if parsed.query:
            normalized += f"?{parsed.query}"

        return normalized

    @classmethod
    def clean_filename(cls, filename: str) -> str:
        """清理文件名中的非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        if not filename:
            return ""

        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, "_", filename)

        # 移除控制字符
        filename = "".join(char for char in filename if ord(char) >= 32)

        # 截断长度
        return cls.truncate(filename, 255, "")

    @classmethod
    def generate_hash(cls, text: str, algorithm: str = "md5") -> str:
        """生成文本哈希值

        Args:
            text: 输入文本
            algorithm: 哈希算法（md5, sha1, sha256）

        Returns:
            哈希值
        """
        if not text:
            return ""

        text_bytes = text.encode("utf-8")

        if algorithm == "md5":
            return hashlib.md5(text_bytes).hexdigest()
        elif algorithm == "sha1":
            return hashlib.sha1(text_bytes).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(text_bytes).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @classmethod
    def extract_keywords(
        cls, text: str, min_length: int = 2, max_count: int = 20
    ) -> List[str]:
        """提取关键词

        Args:
            text: 输入文本
            min_length: 最小关键词长度
            max_count: 最大关键词数量

        Returns:
            关键词列表
        """
        if not text:
            return []

        # 清理文本
        text = cls.clean_html(text).lower()

        # 分词（简单的空格分割）
        words = re.findall(r"\b\w+\b", text)

        # 过滤短词和常见停用词
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        keywords = []
        for word in words:
            if len(word) >= min_length and word not in stop_words:
                keywords.append(word)

        # 去重并限制数量
        keywords = list(dict.fromkeys(keywords))  # 保持顺序的去重
        return keywords[:max_count]

    @classmethod
    def similarity(cls, text1: str, text2: str) -> float:
        """计算文本相似度（简单的Jaccard相似度）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度（0-1之间）
        """
        if not text1 or not text2:
            return 0.0

        # 提取关键词集合
        keywords1 = set(cls.extract_keywords(text1))
        keywords2 = set(cls.extract_keywords(text2))

        if not keywords1 and not keywords2:
            return 1.0

        # 计算Jaccard相似度
        intersection = len(keywords1.intersection(keywords2))
        union = len(keywords1.union(keywords2))

        return intersection / union if union > 0 else 0.0

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """验证URL格式

        Args:
            url: 待验证的URL

        Returns:
            是否为有效URL
        """
        if not url:
            return False

        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """验证邮箱格式

        Args:
            email: 待验证的邮箱

        Returns:
            是否为有效邮箱
        """
        if not email:
            return False

        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def safe_json_loads(cls, json_str: str, default: Any = None) -> Any:
        """安全的JSON解析

        Args:
            json_str: JSON字符串
            default: 解析失败时的默认值

        Returns:
            解析结果或默认值
        """
        if not json_str:
            return default

        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default

    @classmethod
    def safe_json_dumps(cls, obj: Any, default: str = "{}") -> str:
        """安全的JSON序列化

        Args:
            obj: 待序列化的对象
            default: 序列化失败时的默认值

        Returns:
            JSON字符串或默认值
        """
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return default


if __name__ == "__main__":
    # 测试DateHelper
    print("=== DateHelper Tests ===")

    # 测试日期解析
    test_dates = [
        "2024-01-15 10:30:00",
        "2024-01-15T10:30:00Z",
        "15/01/2024 10:30:00",
        "2024-01-15",
    ]

    for date_str in test_dates:
        parsed = DateHelper.parse_datetime(date_str)
        print(f"Parse '{date_str}': {parsed}")

    # 测试时间转换
    now = DateHelper.now_utc()
    print(f"Now UTC: {now}")
    print(f"Now ISO: {DateHelper.now_iso()}")

    # 测试StringHelper
    print("\n=== StringHelper Tests ===")

    # 测试HTML清理
    html_text = '<p>This is <strong>bold</strong> text with <a href="#">link</a>.</p>'
    clean_text = StringHelper.clean_html(html_text)
    print(f"Clean HTML: '{clean_text}'")

    # 测试URL提取
    text_with_urls = "Visit https://example.com or http://test.org for more info."
    urls = StringHelper.extract_urls(text_with_urls)
    print(f"URLs: {urls}")

    # 测试关键词提取
    sample_text = "Bitcoin price analysis shows strong bullish momentum in cryptocurrency markets."
    keywords = StringHelper.extract_keywords(sample_text)
    print(f"Keywords: {keywords}")

    # 测试文本相似度
    text1 = "Bitcoin price is rising"
    text2 = "Bitcoin value is increasing"
    similarity = StringHelper.similarity(text1, text2)
    print(f"Similarity between '{text1}' and '{text2}': {similarity:.2f}")

    print("\nHelper tests completed")
