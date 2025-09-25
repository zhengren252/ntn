# 规则引擎基类
# 定义统一的规则接口和数据结构

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RuleResult:
    """规则执行结果"""

    symbol: str
    rule_type: str
    score: float
    confidence: float
    reason: str
    details: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "rule_type": self.rule_type,
            "score": self.score,
            "confidence": self.confidence,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "schema_version": "1.1",
        }


@dataclass
class MarketData:
    """市场数据结构"""

    symbol: str
    price: float
    volume_24h: float
    market_cap: Optional[float]
    price_change_24h: float
    price_change_7d: Optional[float]
    high_24h: float
    low_24h: float
    timestamp: datetime

    @property
    def volatility_24h(self) -> float:
        """计算24小时波动率"""
        if self.high_24h > 0 and self.low_24h > 0:
            return (self.high_24h - self.low_24h) / self.low_24h
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap,
            "price_change_24h": self.price_change_24h,
            "price_change_7d": self.price_change_7d,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volatility_24h": self.volatility_24h,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class NewsEvent:
    """新闻事件数据结构"""

    event_id: str
    type: str
    exchange: str
    symbol: str
    content: str
    source_url: str
    timestamp: datetime
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_id": self.event_id,
            "type": self.type,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "content": self.content,
            "source_url": self.source_url,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "schema_version": "1.0",
        }


class BaseRule(ABC):
    """规则基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """验证配置参数"""
        pass

    @abstractmethod
    def apply(self, market_data: List[MarketData], **kwargs) -> List[RuleResult]:
        """应用规则

        Args:
            market_data: 市场数据列表
            **kwargs: 其他参数（如新闻数据等）

        Returns:
            规则结果列表
        """
        pass

    @abstractmethod
    def get_rule_type(self) -> str:
        """获取规则类型"""
        pass

    def is_enabled(self) -> bool:
        """检查规则是否启用"""
        return self.config.get("enabled", True)

    def get_min_score(self) -> float:
        """获取最低分数阈值"""
        return self.config.get("min_score", 0.0)

    def filter_by_score(self, results: List[RuleResult]) -> List[RuleResult]:
        """按分数过滤结果"""
        min_score = self.get_min_score()
        filtered = [r for r in results if r.score >= min_score]

        if len(filtered) < len(results):
            self.logger.info(
                "Filtered results by score",
                rule_type=self.get_rule_type(),
                original_count=len(results),
                filtered_count=len(filtered),
                min_score=min_score,
            )

        return filtered

    def calculate_confidence(self, score: float, max_score: float = 100.0) -> float:
        """计算置信度

        Args:
            score: 当前分数
            max_score: 最大分数

        Returns:
            置信度 (0.0-1.0)
        """
        return min(score / max_score, 1.0)

    def log_rule_execution(
        self, input_count: int, output_count: int, execution_time: float
    ) -> None:
        """记录规则执行日志"""
        self.logger.info(
            "Rule execution completed",
            rule_type=self.get_rule_type(),
            input_count=input_count,
            output_count=output_count,
            execution_time_ms=round(execution_time * 1000, 2),
            success_rate=round(output_count / input_count * 100, 2)
            if input_count > 0
            else 0,
        )


class RuleValidator:
    """规则验证器"""

    @staticmethod
    def validate_market_data(data: MarketData) -> bool:
        """验证市场数据"""
        try:
            # 基本字段检查
            if not data.symbol or data.price <= 0:
                return False

            # 数值范围检查
            if data.volume_24h < 0 or abs(data.price_change_24h) > 1.0:  # 价格变化不超过100%
                return False

            # 时间戳检查
            if not data.timestamp:
                return False

            return True

        except Exception as e:
            logger.error(
                "Market data validation failed", error=str(e), symbol=data.symbol
            )
            return False

    @staticmethod
    def validate_news_event(event: NewsEvent) -> bool:
        """验证新闻事件"""
        try:
            # 基本字段检查
            if not all([event.event_id, event.type, event.symbol, event.content]):
                return False

            # 置信度检查
            if not 0.0 <= event.confidence <= 1.0:
                return False

            # 时间戳检查
            if not event.timestamp:
                return False

            return True

        except Exception as e:
            logger.error(
                "News event validation failed", error=str(e), event_id=event.event_id
            )
            return False

    @staticmethod
    def validate_rule_result(result: RuleResult) -> bool:
        """验证规则结果"""
        try:
            # 基本字段检查
            if not all([result.symbol, result.rule_type, result.reason]):
                return False

            # 分数和置信度检查
            if result.score < 0 or not 0.0 <= result.confidence <= 1.0:
                return False

            # 时间戳检查
            if not result.timestamp:
                return False

            return True

        except Exception as e:
            logger.error(
                "Rule result validation failed", error=str(e), symbol=result.symbol
            )
            return False
