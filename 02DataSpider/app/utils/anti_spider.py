#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反爬虫工具模块

提供反爬虫检测和规避功能
"""

import random
import time
from typing import Dict, List, Optional, Any
from fake_useragent import UserAgent
import requests
from urllib.parse import urljoin, urlparse


class AntiSpiderUtils:
    """反爬虫工具类

    提供用户代理轮换、请求延迟、代理支持等反爬虫功能
    """

    def __init__(self, config: Optional[Any] = None):
        """初始化反爬虫工具

        Args:
            config: 配置管理器实例
        """
        self.config = config
        self.ua = UserAgent()

        # 获取反爬虫配置
        self.anti_spider_config = self._get_config()

        # 初始化用户代理池
        self.user_agents = self._init_user_agents()

        # 请求延迟配置
        self.min_delay = self.anti_spider_config.get("min_delay", 1)
        self.max_delay = self.anti_spider_config.get("max_delay", 3)

        # 代理配置
        self.proxies = self.anti_spider_config.get("proxies", [])
        self.current_proxy_index = 0

        # 请求统计
        self.request_count = 0
        self.last_request_time = 0

    def _get_config(self) -> Dict[str, Any]:
        """获取反爬虫配置"""
        if self.config and hasattr(self.config, "get"):
            return self.config.get("anti_spider", {})
        else:
            # 默认配置
            return {
                "min_delay": 1,
                "max_delay": 3,
                "user_agents": [],
                "proxies": [],
                "max_requests_per_minute": 30,
                "retry_attempts": 3,
                "timeout": 30,
            }

    def _init_user_agents(self) -> List[str]:
        """初始化用户代理池"""
        # 从配置获取自定义用户代理
        custom_agents = self.anti_spider_config.get("user_agents", [])

        # 默认用户代理池
        default_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59",
        ]

        # 合并自定义和默认用户代理
        agents = custom_agents + default_agents
        return list(set(agents))  # 去重

    def get_random_user_agent(self) -> str:
        """获取随机用户代理"""
        if self.user_agents:
            return random.choice(self.user_agents)
        else:
            # 使用fake_useragent生成
            try:
                return self.ua.random
            except Exception:
                # 如果fake_useragent失败，返回默认用户代理
                return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """获取随机代理"""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)

        return {"http": proxy, "https": proxy}

    def apply_delay(self):
        """应用随机延迟"""
        current_time = time.time()

        # 计算需要等待的时间
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            min_interval = 60.0 / self.anti_spider_config.get(
                "max_requests_per_minute", 30
            )

            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                time.sleep(wait_time)

        # 应用随机延迟
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

        self.last_request_time = time.time()
        self.request_count += 1

    def get_request_headers(
        self, referer: str = None, extra_headers: Dict[str, str] = None
    ) -> Dict[str, str]:
        """获取请求头

        Args:
            referer: 引用页面URL
            extra_headers: 额外的请求头

        Returns:
            完整的请求头字典
        """
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

        # 添加引用页面
        if referer:
            headers["Referer"] = referer

        # 添加额外请求头
        if extra_headers:
            headers.update(extra_headers)

        return headers

    def make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> requests.Response:
        """发起HTTP请求

        Args:
            url: 请求URL
            method: HTTP方法
            **kwargs: 其他requests参数

        Returns:
            响应对象
        """
        # 应用延迟
        self.apply_delay()

        # 设置默认参数
        request_kwargs = {
            "timeout": self.anti_spider_config.get("timeout", 30),
            "allow_redirects": True,
            "verify": True,
        }
        request_kwargs.update(kwargs)

        # 设置请求头
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = self.get_request_headers()

        # 设置代理
        if "proxies" not in request_kwargs:
            proxy = self.get_random_proxy()
            if proxy:
                request_kwargs["proxies"] = proxy

        # 发起请求
        response = requests.request(method, url, **request_kwargs)

        # 检查响应状态
        response.raise_for_status()

        return response

    def make_request_with_retry(
        self, url: str, method: str = "GET", **kwargs
    ) -> Optional[requests.Response]:
        """带重试的HTTP请求

        Args:
            url: 请求URL
            method: HTTP方法
            **kwargs: 其他requests参数

        Returns:
            响应对象或None（如果所有重试都失败）
        """
        retry_attempts = self.anti_spider_config.get("retry_attempts", 3)

        for attempt in range(retry_attempts):
            try:
                return self.make_request(url, method, **kwargs)
            except Exception as e:
                if attempt == retry_attempts - 1:
                    # 最后一次尝试失败
                    raise e
                else:
                    # 等待后重试
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    time.sleep(wait_time)

        return None

    def is_blocked(self, response: requests.Response) -> bool:
        """检测是否被反爬虫系统阻止

        Args:
            response: HTTP响应对象

        Returns:
            是否被阻止
        """
        # 检查状态码
        blocked_status_codes = [403, 429, 503]
        if response.status_code in blocked_status_codes:
            return True

        # 检查响应内容中的阻止标识
        content = response.text.lower()
        blocked_keywords = [
            "access denied",
            "blocked",
            "captcha",
            "robot",
            "bot detected",
            "rate limit",
            "too many requests",
            "cloudflare",
        ]

        for keyword in blocked_keywords:
            if keyword in content:
                return True

        return False

    def get_session(self) -> requests.Session:
        """获取配置好的Session对象"""
        session = requests.Session()

        # 设置默认请求头
        session.headers.update(self.get_request_headers())

        # 设置代理
        proxy = self.get_random_proxy()
        if proxy:
            session.proxies.update(proxy)

        return session

    def reset_stats(self):
        """重置统计信息"""
        self.request_count = 0
        self.last_request_time = 0
        self.current_proxy_index = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        current_time = time.time()
        uptime = (
            current_time - (self.last_request_time - self.request_count * 2)
            if self.last_request_time > 0
            else 0
        )

        return {
            "request_count": self.request_count,
            "uptime_seconds": uptime,
            "requests_per_minute": self.request_count / (uptime / 60)
            if uptime > 0
            else 0,
            "user_agents_count": len(self.user_agents),
            "proxies_count": len(self.proxies),
            "current_proxy_index": self.current_proxy_index,
        }


if __name__ == "__main__":
    # 测试反爬虫工具
    utils = AntiSpiderUtils()

    print("User Agent:", utils.get_random_user_agent())
    print("Headers:", utils.get_request_headers())
    print("Stats:", utils.get_stats())

    # 测试请求（注释掉以避免实际网络请求）
    # try:
    #     response = utils.make_request_with_retry('https://httpbin.org/user-agent')
    #     print("Response:", response.json())
    # except Exception as e:
    #     print("Request failed:", e)

    print("AntiSpiderUtils test completed")
