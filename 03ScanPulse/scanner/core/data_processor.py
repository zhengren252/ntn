# 数据处理器
# 负责处理和验证市场数据、新闻事件等

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# import numpy as np  # Unused
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class DataQuality(Enum):
    """数据质量等级"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"


@dataclass
class DataValidationResult:
    """数据验证结果"""

    is_valid: bool
    quality: DataQuality
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


@dataclass
class ProcessedMarketData:
    """处理后的市场数据"""

    symbol: str
    timestamp: datetime
    price: float
    volume: float
    change_24h: float
    change_percent_24h: float
    market_cap: Optional[float]
    volume_24h: float
    high_24h: float
    low_24h: float

    # 技术指标
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    sma_20: Optional[float] = None
    ema_12: Optional[float] = None

    # 数据质量
    validation_result: Optional[DataValidationResult] = None


@dataclass
class ProcessedNewsEvent:
    """处理后的新闻事件"""

    id: str
    title: str
    content: str
    source: str
    timestamp: datetime
    symbols: List[str]
    sentiment_score: float
    impact_score: float
    categories: List[str]
    keywords: List[str]
    validation_result: Optional[DataValidationResult] = None


class DataProcessor:
    """数据处理器 - 处理和验证各种数据"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # 数据质量配置
        self.quality_config = config.get("data_quality", {})
        self.validation_config = config.get("validation", {})

        # 技术指标配置
        self.indicators_config = config.get("technical_indicators", {})

        # 统计信息
        self.stats = {
            "processed_market_data": 0,
            "processed_news_events": 0,
            "validation_failures": 0,
            "quality_issues": 0,
            "last_processing_time": None,
        }

        logger.info("DataProcessor initialized", config=config)

    def process_market_data(
        self, raw_data: Dict[str, Any], symbol: str
    ) -> Optional[ProcessedMarketData]:
        """处理市场数据

        Args:
            raw_data: 原始市场数据
            symbol: 交易对符号

        Returns:
            处理后的市场数据或None
        """
        try:
            # 验证原始数据
            validation_result = self._validate_market_data(raw_data, symbol)

            if not validation_result.is_valid:
                logger.warning(
                    "Market data validation failed",
                    symbol=symbol,
                    issues=validation_result.issues,
                )
                self.stats["validation_failures"] += 1
                return None

            # 提取基础数据
            processed_data = ProcessedMarketData(
                symbol=symbol,
                timestamp=self._parse_timestamp(
                    raw_data.get("timestamp", datetime.now())
                ),
                price=float(raw_data.get("price", 0)),
                volume=float(raw_data.get("volume", 0)),
                change_24h=float(raw_data.get("change_24h", 0)),
                change_percent_24h=float(raw_data.get("change_percent_24h", 0)),
                market_cap=self._safe_float(raw_data.get("market_cap")),
                volume_24h=float(raw_data.get("volume_24h", 0)),
                high_24h=float(raw_data.get("high_24h", 0)),
                low_24h=float(raw_data.get("low_24h", 0)),
                validation_result=validation_result,
            )

            # 计算技术指标（如果有历史数据）
            if "historical_data" in raw_data:
                self._calculate_technical_indicators(
                    processed_data, raw_data["historical_data"]
                )

            # 数据清理和标准化
            self._normalize_market_data(processed_data)

            self.stats["processed_market_data"] += 1
            self.stats["last_processing_time"] = datetime.now().isoformat()

            logger.debug(
                "Market data processed",
                symbol=symbol,
                price=processed_data.price,
                quality=validation_result.quality.value,
            )

            return processed_data

        except Exception as e:
            logger.error("Error processing market data", symbol=symbol, error=str(e))
            self.stats["validation_failures"] += 1
            return None

    def process_news_event(
        self, raw_event: Dict[str, Any]
    ) -> Optional[ProcessedNewsEvent]:
        """处理新闻事件

        Args:
            raw_event: 原始新闻事件数据

        Returns:
            处理后的新闻事件或None
        """
        try:
            # 验证原始数据
            validation_result = self._validate_news_event(raw_event)

            if not validation_result.is_valid:
                logger.warning(
                    "News event validation failed",
                    event_id=raw_event.get("id"),
                    issues=validation_result.issues,
                )
                self.stats["validation_failures"] += 1
                return None

            # 提取和处理数据
            processed_event = ProcessedNewsEvent(
                id=str(raw_event.get("id", "")),
                title=self._clean_text(raw_event.get("title", "")),
                content=self._clean_text(raw_event.get("content", "")),
                source=str(raw_event.get("source", "unknown")),
                timestamp=self._parse_timestamp(
                    raw_event.get("timestamp", datetime.now())
                ),
                symbols=self._extract_symbols(raw_event),
                sentiment_score=self._calculate_sentiment_score(raw_event),
                impact_score=self._calculate_impact_score(raw_event),
                categories=self._extract_categories(raw_event),
                keywords=self._extract_keywords(raw_event),
                validation_result=validation_result,
            )

            self.stats["processed_news_events"] += 1
            self.stats["last_processing_time"] = datetime.now().isoformat()

            logger.debug(
                "News event processed",
                event_id=processed_event.id,
                symbols=processed_event.symbols,
                sentiment=processed_event.sentiment_score,
                impact=processed_event.impact_score,
            )

            return processed_event

        except Exception as e:
            logger.error("Error processing news event", error=str(e))
            self.stats["validation_failures"] += 1
            return None

    def batch_process_market_data(
        self, raw_data_list: List[Dict[str, Any]]
    ) -> List[ProcessedMarketData]:
        """批量处理市场数据

        Args:
            raw_data_list: 原始市场数据列表

        Returns:
            处理后的市场数据列表
        """
        processed_data = []

        for raw_data in raw_data_list:
            symbol = raw_data.get("symbol", "UNKNOWN")
            processed = self.process_market_data(raw_data, symbol)
            if processed:
                processed_data.append(processed)

        logger.info(
            "Batch market data processing completed",
            total=len(raw_data_list),
            processed=len(processed_data),
            failed=len(raw_data_list) - len(processed_data),
        )

        return processed_data

    def batch_process_news_events(
        self, raw_events_list: List[Dict[str, Any]]
    ) -> List[ProcessedNewsEvent]:
        """批量处理新闻事件

        Args:
            raw_events_list: 原始新闻事件列表

        Returns:
            处理后的新闻事件列表
        """
        processed_events = []

        for raw_event in raw_events_list:
            processed = self.process_news_event(raw_event)
            if processed:
                processed_events.append(processed)

        logger.info(
            "Batch news events processing completed",
            total=len(raw_events_list),
            processed=len(processed_events),
            failed=len(raw_events_list) - len(processed_events),
        )

        return processed_events

    def _validate_market_data(
        self, data: Dict[str, Any], symbol: str
    ) -> DataValidationResult:
        """验证市场数据

        Args:
            data: 市场数据
            symbol: 交易对符号

        Returns:
            验证结果
        """
        issues = []
        warnings = []
        quality = DataQuality.EXCELLENT

        # 必需字段检查
        required_fields = ["price", "volume", "timestamp"]
        for field in required_fields:
            if field not in data or data[field] is None:
                issues.append(f"Missing required field: {field}")

        # 数据类型和范围检查
        try:
            price = float(data.get("price", 0))
            if price <= 0:
                issues.append("Price must be positive")
            elif price > 1000000:  # 异常高价格
                warnings.append("Unusually high price detected")
                quality = DataQuality.FAIR
        except (ValueError, TypeError):
            issues.append("Invalid price format")

        try:
            volume = float(data.get("volume", 0))
            if volume < 0:
                issues.append("Volume cannot be negative")
            elif volume == 0:
                warnings.append("Zero volume detected")
                quality = DataQuality.GOOD
        except (ValueError, TypeError):
            issues.append("Invalid volume format")

        # 时间戳检查
        try:
            timestamp = self._parse_timestamp(data.get("timestamp"))
            now = datetime.now()
            if timestamp > now + timedelta(minutes=5):  # 未来时间
                warnings.append("Future timestamp detected")
                quality = DataQuality.FAIR
            elif timestamp < now - timedelta(days=7):  # 过旧数据
                warnings.append("Old timestamp detected")
                quality = DataQuality.GOOD
        except Exception:
            issues.append("Invalid timestamp format")

        # 24小时变化检查
        try:
            change_percent = float(data.get("change_percent_24h", 0))
            if abs(change_percent) > 100:  # 超过100%的变化
                warnings.append("Extreme price change detected")
                quality = DataQuality.FAIR
        except (ValueError, TypeError):
            warnings.append("Invalid change percentage format")

        # 确定最终质量等级
        if issues:
            quality = DataQuality.INVALID
        elif len(warnings) > 3:
            quality = DataQuality.POOR
        elif len(warnings) > 1:
            quality = DataQuality.FAIR

        return DataValidationResult(
            is_valid=len(issues) == 0,
            quality=quality,
            issues=issues,
            warnings=warnings,
            metadata={
                "symbol": symbol,
                "validation_time": datetime.now().isoformat(),
                "data_fields": list(data.keys()),
            },
        )

    def _validate_news_event(self, event: Dict[str, Any]) -> DataValidationResult:
        """验证新闻事件

        Args:
            event: 新闻事件数据

        Returns:
            验证结果
        """
        issues = []
        warnings = []
        quality = DataQuality.EXCELLENT

        # 必需字段检查
        required_fields = ["title", "content", "timestamp"]
        for field in required_fields:
            if field not in event or not event[field]:
                issues.append(f"Missing required field: {field}")

        # 内容质量检查
        title = str(event.get("title", ""))
        content = str(event.get("content", ""))

        if len(title) < 10:
            warnings.append("Title too short")
            quality = DataQuality.GOOD
        elif len(title) > 200:
            warnings.append("Title too long")
            quality = DataQuality.FAIR

        if len(content) < 50:
            warnings.append("Content too short")
            quality = DataQuality.FAIR
        elif len(content) > 10000:
            warnings.append("Content too long")
            quality = DataQuality.GOOD

        # 时间戳检查
        try:
            timestamp = self._parse_timestamp(event.get("timestamp"))
            now = datetime.now()
            if timestamp > now + timedelta(minutes=5):
                warnings.append("Future timestamp detected")
                quality = DataQuality.FAIR
            elif timestamp < now - timedelta(days=30):
                warnings.append("Very old news event")
                quality = DataQuality.GOOD
        except Exception:
            issues.append("Invalid timestamp format")

        # 来源检查
        source = str(event.get("source", ""))
        if not source or source == "unknown":
            warnings.append("Unknown or missing source")
            quality = DataQuality.FAIR

        # 确定最终质量等级
        if issues:
            quality = DataQuality.INVALID
        elif len(warnings) > 3:
            quality = DataQuality.POOR
        elif len(warnings) > 1:
            quality = DataQuality.FAIR

        return DataValidationResult(
            is_valid=len(issues) == 0,
            quality=quality,
            issues=issues,
            warnings=warnings,
            metadata={
                "validation_time": datetime.now().isoformat(),
                "title_length": len(title),
                "content_length": len(content),
                "source": source,
            },
        )

    def _calculate_technical_indicators(
        self, processed_data: ProcessedMarketData, historical_data: List[Dict[str, Any]]
    ) -> None:
        """计算技术指标

        Args:
            processed_data: 处理后的市场数据
            historical_data: 历史数据
        """
        try:
            if not historical_data or len(historical_data) < 20:
                logger.debug(
                    "Insufficient historical data for technical indicators",
                    symbol=processed_data.symbol,
                )
                return

            # 转换为DataFrame
            df = pd.DataFrame(historical_data)
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

            # 计算RSI
            processed_data.rsi = self._calculate_rsi(df["close"])

            # 计算MACD
            processed_data.macd = self._calculate_macd(df["close"])

            # 计算布林带
            bb_upper, bb_lower = self._calculate_bollinger_bands(df["close"])
            processed_data.bollinger_upper = bb_upper
            processed_data.bollinger_lower = bb_lower

            # 计算移动平均线
            processed_data.sma_20 = self._calculate_sma(df["close"], 20)
            processed_data.ema_12 = self._calculate_ema(df["close"], 12)

            logger.debug(
                "Technical indicators calculated",
                symbol=processed_data.symbol,
                rsi=processed_data.rsi,
                macd=processed_data.macd,
            )

        except Exception as e:
            logger.warning(
                "Error calculating technical indicators",
                symbol=processed_data.symbol,
                error=str(e),
            )

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """计算RSI指标"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        except Exception:
            return None

    def _calculate_macd(
        self, prices: pd.Series, fast: int = 12, slow: int = 26
    ) -> Optional[float]:
        """计算MACD指标"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            return float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else None
        except Exception:
            return None

    def _calculate_bollinger_bands(
        self, prices: pd.Series, period: int = 20, std_dev: int = 2
    ) -> tuple[Optional[float], Optional[float]]:
        """计算布林带"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            return (
                float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None,
                float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None,
            )
        except Exception:
            return None, None

    def _calculate_sma(self, prices: pd.Series, period: int) -> Optional[float]:
        """计算简单移动平均线"""
        try:
            sma = prices.rolling(window=period).mean()
            return float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None
        except Exception:
            return None

    def _calculate_ema(self, prices: pd.Series, period: int) -> Optional[float]:
        """计算指数移动平均线"""
        try:
            ema = prices.ewm(span=period).mean()
            return float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None
        except Exception:
            return None

    def _normalize_market_data(self, data: ProcessedMarketData) -> None:
        """标准化市场数据

        Args:
            data: 市场数据
        """
        try:
            # 价格精度标准化
            data.price = round(data.price, 8)

            # 百分比标准化
            data.change_percent_24h = round(data.change_percent_24h, 2)

            # 技术指标精度标准化
            if data.rsi is not None:
                data.rsi = round(data.rsi, 2)
            if data.macd is not None:
                data.macd = round(data.macd, 6)

        except Exception as e:
            logger.warning(
                "Error normalizing market data", symbol=data.symbol, error=str(e)
            )

    def _extract_symbols(self, event: Dict[str, Any]) -> List[str]:
        """从新闻事件中提取相关交易对符号"""
        symbols = []

        # 从明确的symbols字段提取
        if "symbols" in event:
            symbols.extend(event["symbols"])

        # 从标题和内容中提取（简单的关键词匹配）
        text = f"{event.get('title', '')} {event.get('content', '')}".upper()

        # 常见的加密货币符号
        common_symbols = [
            "BTC",
            "ETH",
            "BNB",
            "ADA",
            "DOT",
            "LINK",
            "XRP",
            "LTC",
            "BCH",
            "UNI",
        ]
        for symbol in common_symbols:
            if symbol in text and symbol not in symbols:
                symbols.append(symbol)

        return list(set(symbols))  # 去重

    def _calculate_sentiment_score(self, event: Dict[str, Any]) -> float:
        """计算情感分数"""
        # 如果已有情感分数，直接使用
        if "sentiment_score" in event:
            try:
                return float(event["sentiment_score"])
            except (ValueError, TypeError):
                pass

        # 简单的关键词情感分析
        text = f"{event.get('title', '')} {event.get('content', '')}".lower()

        positive_keywords = [
            "bullish",
            "positive",
            "growth",
            "increase",
            "rise",
            "gain",
            "profit",
            "success",
        ]
        negative_keywords = [
            "bearish",
            "negative",
            "decline",
            "decrease",
            "fall",
            "loss",
            "crash",
            "failure",
        ]

        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)

        if positive_count + negative_count == 0:
            return 0.0  # 中性

        # 计算情感分数 (-1 到 1)
        sentiment = (positive_count - negative_count) / (
            positive_count + negative_count
        )
        return round(sentiment, 3)

    def _calculate_impact_score(self, event: Dict[str, Any]) -> float:
        """计算影响分数"""
        # 如果已有影响分数，直接使用
        if "impact_score" in event:
            try:
                return float(event["impact_score"])
            except (ValueError, TypeError):
                pass

        # 基于来源、内容长度等计算影响分数
        score = 0.5  # 基础分数

        # 来源权重
        source = event.get("source", "").lower()
        if "reuters" in source or "bloomberg" in source:
            score += 0.3
        elif "coindesk" in source or "cointelegraph" in source:
            score += 0.2
        elif "twitter" in source or "reddit" in source:
            score += 0.1

        # 内容长度影响
        content_length = len(event.get("content", ""))
        if content_length > 1000:
            score += 0.2
        elif content_length > 500:
            score += 0.1

        # 关键词影响
        text = f"{event.get('title', '')} {event.get('content', '')}".lower()
        high_impact_keywords = [
            "regulation",
            "ban",
            "adoption",
            "partnership",
            "listing",
            "delisting",
        ]
        impact_count = sum(1 for keyword in high_impact_keywords if keyword in text)
        score += impact_count * 0.1

        return min(round(score, 3), 1.0)  # 限制在0-1范围内

    def _extract_categories(self, event: Dict[str, Any]) -> List[str]:
        """提取新闻事件分类"""
        categories = []

        # 从明确的categories字段提取
        if "categories" in event:
            categories.extend(event["categories"])

        # 基于关键词分类
        text = f"{event.get('title', '')} {event.get('content', '')}".lower()

        category_keywords = {
            "regulation": ["regulation", "regulatory", "sec", "cftc", "government"],
            "technology": ["blockchain", "smart contract", "defi", "nft", "protocol"],
            "market": ["price", "trading", "volume", "market cap", "exchange"],
            "partnership": ["partnership", "collaboration", "integration", "alliance"],
            "adoption": ["adoption", "mainstream", "institutional", "corporate"],
        }

        for category, keywords in category_keywords.items():
            if (
                any(keyword in text for keyword in keywords)
                and category not in categories
            ):
                categories.append(category)

        return categories

    def _extract_keywords(self, event: Dict[str, Any]) -> List[str]:
        """提取关键词"""
        # 如果已有关键词，直接使用
        if "keywords" in event:
            return event["keywords"]

        # 简单的关键词提取（基于常见的加密货币术语）
        text = f"{event.get('title', '')} {event.get('content', '')}".lower()

        crypto_keywords = [
            "bitcoin",
            "ethereum",
            "blockchain",
            "cryptocurrency",
            "defi",
            "nft",
            "smart contract",
            "mining",
            "staking",
            "yield farming",
            "liquidity",
            "exchange",
            "wallet",
            "token",
            "coin",
            "altcoin",
            "bull market",
            "bear market",
        ]

        found_keywords = [keyword for keyword in crypto_keywords if keyword in text]
        return found_keywords[:10]  # 限制关键词数量

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""

        # 移除多余的空白字符
        text = " ".join(text.split())

        # 移除特殊字符（保留基本标点）
        import re

        text = re.sub(r"[^\w\s.,!?;:()-]", "", text)

        return text.strip()

    def _parse_timestamp(self, timestamp: Union[str, datetime, int, float]) -> datetime:
        """解析时间戳"""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            # 尝试多种格式
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp, fmt)
                except ValueError:
                    continue

            # 如果都失败了，返回当前时间
            logger.warning(
                "Failed to parse timestamp, using current time", timestamp=timestamp
            )
            return datetime.now()
        else:
            return datetime.now()

    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return self.stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "processed_market_data": 0,
            "processed_news_events": 0,
            "validation_failures": 0,
            "quality_issues": 0,
            "last_processing_time": None,
        }
        logger.info("Statistics reset")
