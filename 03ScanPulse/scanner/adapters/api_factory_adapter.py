# API工厂适配器
# 实现与API工厂的集成，获取新闻数据和市场数据

import hashlib
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
import structlog

from .base_adapter import AdapterConfig, AdapterStatus, BaseAdapter

logger = structlog.get_logger(__name__)


class APIFactoryAdapter(BaseAdapter):
    """API工厂适配器 - 集成多种数据源API"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)

        # API工厂配置
        self.base_url = self.config.config.get("base_url", "http://localhost:9000")
        self.api_key = self.config.config.get("api_key", "")
        self.timeout = self.config.timeout

        # API端点配置
        self.endpoints = {
            "news": f"{self.base_url}/api/news",
            "market_data": f"{self.base_url}/api/market",
            "sentiment": f"{self.base_url}/api/sentiment",
            "health": f"{self.base_url}/api/health",
        }

        # 数据源配置
        self.data_sources = self.config.config.get(
            "data_sources",
            {
                "news": ["coindesk", "cointelegraph", "cryptonews"],
                "market": ["binance", "coinbase", "kraken"],
            },
        )

        # 请求会话
        self.session = None

        # 缓存
        self.cache = {}
        self.cache_ttl = {
            "news": self.config.config.get("news_cache_ttl", 300),  # 新闻缓存5分钟
            "market": self.config.config.get("market_cache_ttl", 60),  # 市场数据缓存1分钟
            "sentiment": self.config.config.get(
                "sentiment_cache_ttl", 180
            ),  # 情感分析缓存3分钟
        }

        logger.info(
            "APIFactoryAdapter initialized",
            base_url=self.base_url,
            data_sources=self.data_sources,
            mock_mode=self.config.mock_mode,
        )

    def connect(self) -> bool:
        """建立与API工厂的连接

        Returns:
            是否连接成功
        """
        try:
            if not self.config.enabled:
                logger.info("APIFactoryAdapter disabled")
                return False

            if self.config.mock_mode:
                self._set_status(AdapterStatus.MOCK)
                logger.info("APIFactoryAdapter connected in mock mode")
                return True

            self._set_status(AdapterStatus.CONNECTING)

            # 创建请求会话
            self.session = requests.Session()

            # 设置请求头
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ScanPulse-Scanner/1.0",
            }

            if self.api_key:
                headers["X-API-Key"] = self.api_key

            self.session.headers.update(headers)

            # 测试连接
            if self.health_check():
                self._set_status(AdapterStatus.CONNECTED)
                logger.info("APIFactoryAdapter connected successfully")
                return True
            else:
                self._set_status(AdapterStatus.ERROR, "Health check failed")
                return False

        except Exception as e:
            error_msg = f"Failed to connect to API Factory: {str(e)}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            logger.error("APIFactoryAdapter connection failed", error=str(e))
            return False

    def disconnect(self) -> None:
        """断开连接"""
        try:
            if self.session:
                self.session.close()
                self.session = None

            self._set_status(AdapterStatus.DISCONNECTED)
            logger.info("APIFactoryAdapter disconnected")

        except Exception as e:
            logger.error("Error disconnecting APIFactoryAdapter", error=str(e))

    def health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        try:
            if self.config.mock_mode:
                return True

            if not self.session:
                return False

            response = self.session.get(self.endpoints["health"], timeout=self.timeout)

            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("status") == "healthy"

            return False

        except Exception as e:
            logger.error("APIFactoryAdapter health check failed", error=str(e))
            return False

    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据

        Args:
            symbol: 交易对符号

        Returns:
            市场数据或None
        """
        try:
            if not self.is_connected():
                logger.error("APIFactoryAdapter not connected")
                return None

            if self.config.mock_mode:
                return self._get_mock_market_data(symbol)

            # 检查缓存
            cache_key = f"market_{symbol}"
            cached_data = self._get_from_cache(cache_key, "market")
            if cached_data:
                return cached_data

            # 从API获取数据
            market_data = self._execute_with_retry(self._fetch_market_data, symbol)

            if market_data:
                # 缓存数据
                self._set_cache(cache_key, market_data, "market")

                logger.debug(
                    "Market data retrieved from API Factory",
                    symbol=symbol,
                    price=market_data.get("price"),
                    volume=market_data.get("volume"),
                )

            return market_data

        except Exception as e:
            logger.error(
                "Failed to get market data from API Factory",
                symbol=symbol,
                error=str(e),
            )
            return None

    def get_news_events(
        self, symbols: Optional[List[str]] = None, limit: int = 50, hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """获取新闻事件

        Args:
            symbols: 相关交易对符号列表
            limit: 最大返回数量
            hours_back: 获取多少小时前的新闻

        Returns:
            新闻事件列表
        """
        try:
            if not self.is_connected():
                logger.error("APIFactoryAdapter not connected")
                return []

            if self.config.mock_mode:
                return self._get_mock_news_events(symbols, limit)

            # 检查缓存
            cache_key = f"news_{symbols}_{limit}_{hours_back}"
            cached_data = self._get_from_cache(cache_key, "news")
            if cached_data:
                return cached_data

            # 从API获取数据
            news_events = self._execute_with_retry(
                self._fetch_news_events, symbols, limit, hours_back
            )

            if news_events:
                # 缓存数据
                self._set_cache(cache_key, news_events, "news")

                logger.debug(
                    "News events retrieved from API Factory",
                    count=len(news_events),
                    symbols=symbols,
                )

            return news_events or []

        except Exception as e:
            logger.error("Failed to get news events from API Factory", error=str(e))
            return []

    def get_sentiment_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """获取情感分析结果

        Args:
            text: 要分析的文本

        Returns:
            情感分析结果或None
        """
        try:
            if not self.is_connected():
                logger.error("APIFactoryAdapter not connected")
                return None

            if self.config.mock_mode:
                return self._get_mock_sentiment_analysis(text)

            # 检查缓存
            text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
            cache_key = f"sentiment_{text_hash}"
            cached_data = self._get_from_cache(cache_key, "sentiment")
            if cached_data:
                return cached_data

            # 从API获取数据
            sentiment = self._execute_with_retry(self._fetch_sentiment_analysis, text)

            if sentiment:
                # 缓存数据
                self._set_cache(cache_key, sentiment, "sentiment")

                logger.debug(
                    "Sentiment analysis retrieved",
                    sentiment=sentiment.get("sentiment"),
                    score=sentiment.get("score"),
                )

            return sentiment

        except Exception as e:
            logger.error("Failed to get sentiment analysis", error=str(e))
            return None

    def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """从API获取市场数据"""
        params = {
            "symbol": symbol,
            "sources": ",".join(self.data_sources.get("market", [])),
        }

        response = self.session.get(
            self.endpoints["market_data"], params=params, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def _fetch_news_events(
        self, symbols: Optional[List[str]], limit: int, hours_back: int
    ) -> List[Dict[str, Any]]:
        """从API获取新闻事件"""
        params = {
            "limit": limit,
            "hours_back": hours_back,
            "sources": ",".join(self.data_sources.get("news", [])),
        }

        if symbols:
            params["symbols"] = ",".join(symbols)

        response = self.session.get(
            self.endpoints["news"], params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data.get("news", [])

    def _fetch_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """从API获取情感分析"""
        data = {"text": text}

        response = self.session.post(
            self.endpoints["sentiment"], json=data, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def _get_mock_market_data(self, symbol: str) -> Dict[str, Any]:
        """获取模拟市场数据"""

        base_price = 100.0
        if "BTC" in symbol.upper():
            base_price = 50000.0
        elif "ETH" in symbol.upper():
            base_price = 3000.0

        price = base_price * (1 + random.uniform(-0.05, 0.05))
        volume = random.uniform(1000, 10000)

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "volume": round(volume, 2),
            "high_24h": round(price * 1.02, 2),
            "low_24h": round(price * 0.98, 2),
            "change_24h": round(random.uniform(-5, 5), 2),
            "change_percent_24h": round(random.uniform(-5, 5), 2),
            "timestamp": datetime.now().isoformat(),
            "source": "api_factory_mock",
            "data_sources": self.data_sources.get("market", []),
        }

    def _get_mock_news_events(
        self, symbols: Optional[List[str]], limit: int
    ) -> List[Dict[str, Any]]:
        """获取模拟新闻事件"""

        news_templates = [
            "Bitcoin reaches new all-time high amid institutional adoption",
            "Ethereum upgrade shows promising results for scalability",
            "Major cryptocurrency exchange announces new trading pairs",
            "Regulatory clarity brings positive sentiment to crypto markets",
            "DeFi protocol launches innovative yield farming mechanism",
            "Central bank digital currency pilot program shows progress",
            "Cryptocurrency adoption grows in emerging markets",
            "Blockchain technology finds new applications in supply chain",
            "NFT marketplace reports record trading volumes",
            "Stablecoin usage increases in cross-border payments",
        ]

        sentiments = ["positive", "negative", "neutral"]

        news_events = []
        for i in range(min(limit, len(news_templates))):
            sentiment = random.choice(sentiments)
            impact_score = random.uniform(0.1, 0.9)

            event = {
                "id": f"mock_news_{i}",
                "title": news_templates[i],
                "content": f"This is mock news content for {news_templates[i]}",
                "source": random.choice(self.data_sources.get("news", ["mock_source"])),
                "published_at": (
                    datetime.now() - timedelta(hours=random.randint(1, 24))
                ).isoformat(),
                "sentiment": sentiment,
                "sentiment_score": round(random.uniform(-1, 1), 2),
                "impact_score": round(impact_score, 2),
                "related_symbols": symbols[:3] if symbols else ["BTCUSDT", "ETHUSDT"],
                "url": f"https://mock-news.com/article/{i}",
                "tags": ["cryptocurrency", "blockchain", "trading"],
            }
            news_events.append(event)

        return news_events

    def _get_mock_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """获取模拟情感分析"""

        sentiments = ["positive", "negative", "neutral"]
        sentiment = random.choice(sentiments)

        # 根据文本内容调整情感倾向
        positive_words = ["good", "great", "excellent", "bullish", "up", "rise", "gain"]
        negative_words = ["bad", "terrible", "bearish", "down", "fall", "loss", "crash"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            sentiment = "positive"
            score = random.uniform(0.1, 0.9)
        elif negative_count > positive_count:
            sentiment = "negative"
            score = random.uniform(-0.9, -0.1)
        else:
            sentiment = "neutral"
            score = random.uniform(-0.2, 0.2)

        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "keywords": ["crypto", "trading", "market"],
            "processed_at": datetime.now().isoformat(),
        }

    def _get_from_cache(self, key: str, cache_type: str) -> Optional[Any]:
        """从缓存获取数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            ttl = self.cache_ttl.get(cache_type, 60)
            if time.time() - timestamp < ttl:
                return data
            else:
                # 缓存过期，删除
                del self.cache[key]
        return None

    def _set_cache(self, key: str, data: Any, cache_type: str) -> None:
        """设置缓存数据"""
        self.cache[key] = (data, time.time())

        # 清理过期缓存
        if len(self.cache) > 200:  # 限制缓存大小
            self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, (data, timestamp) in self.cache.items():
            # 根据缓存类型确定TTL
            max_ttl = max(self.cache_ttl.values())
            if current_time - timestamp >= max_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        logger.debug("API Factory cache cleaned up", expired_count=len(expired_keys))

    def get_data_sources_status(self) -> Dict[str, Any]:
        """获取数据源状态

        Returns:
            数据源状态信息
        """
        try:
            if self.config.mock_mode:
                return {
                    "mock_mode": True,
                    "news_sources": {
                        source: "healthy"
                        for source in self.data_sources.get("news", [])
                    },
                    "market_sources": {
                        source: "healthy"
                        for source in self.data_sources.get("market", [])
                    },
                }

            # 在实际实现中，这里会检查各个数据源的状态
            return {
                "mock_mode": False,
                "news_sources": {
                    source: "unknown" for source in self.data_sources.get("news", [])
                },
                "market_sources": {
                    source: "unknown" for source in self.data_sources.get("market", [])
                },
            }

        except Exception as e:
            logger.error("Failed to get data sources status", error=str(e))
            return {"error": str(e)}
