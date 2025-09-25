# 黑马监测器规则引擎
# 基于新闻事件和突发公告的交易机会检测

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseRule, MarketData, NewsEvent, RuleResult, RuleValidator


class BlackHorseDetector(BaseRule):
    """黑马监测器：检测基于新闻事件的突发交易机会"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 关键词配置
        self.keywords = config.get(
            "keywords",
            [
                "listing",
                "partnership",
                "upgrade",
                "mainnet",
                "launch",
                "integration",
                "announcement",
                "airdrop",
            ],
        )

        # 分数倍数
        self.score_multiplier = config.get("score_multiplier", 1.5)

        # 新闻有效期（秒）
        self.news_timeout = config.get("news_timeout", 3600)

        # 最小价格变化阈值
        self.min_price_change = config.get("min_price_change", 0.05)

        # 交易所权重
        self.exchange_weights = config.get(
            "exchange_weights",
            {
                "binance": 1.0,
                "coinbase": 0.9,
                "okx": 0.8,
                "huobi": 0.7,
                "kucoin": 0.6,
                "gate": 0.5,
            },
        )

        # 新闻类型权重
        self.news_type_weights = config.get(
            "news_type_weights",
            {
                "listing": 1.0,
                "partnership": 0.8,
                "upgrade": 0.7,
                "mainnet": 0.9,
                "integration": 0.6,
                "announcement": 0.5,
            },
        )

    def _validate_config(self) -> None:
        """验证配置参数"""
        if not isinstance(self.keywords, list) or not self.keywords:
            raise ValueError("keywords must be a non-empty list")

        if self.score_multiplier <= 0:
            raise ValueError("score_multiplier must be positive")

        if self.news_timeout <= 0:
            raise ValueError("news_timeout must be positive")

        if not 0 <= self.min_price_change <= 1:
            raise ValueError("min_price_change must be between 0 and 1")

    def get_rule_type(self) -> str:
        """获取规则类型"""
        return "black_horse"

    def apply(self, market_data: List[MarketData], **kwargs) -> List[RuleResult]:
        """应用黑马监测规则

        Args:
            market_data: 市场数据列表
            **kwargs: 其他参数，期望包含 news_events

        Returns:
            黑马检测结果列表
        """
        start_time = time.time()
        results = []

        # 获取新闻事件
        news_events = kwargs.get("news_events", [])
        if not news_events:
            self.logger.warning("No news events provided for black horse detection")
            return results

        # 验证和过滤数据
        valid_market_data = [
            data for data in market_data if RuleValidator.validate_market_data(data)
        ]
        valid_news_events = [
            event for event in news_events if RuleValidator.validate_news_event(event)
        ]

        if len(valid_market_data) < len(market_data):
            self.logger.warning(
                "Some market data failed validation",
                total_count=len(market_data),
                valid_count=len(valid_market_data),
            )

        if len(valid_news_events) < len(news_events):
            self.logger.warning(
                "Some news events failed validation",
                total_count=len(news_events),
                valid_count=len(valid_news_events),
            )

        # 过滤有效时间内的新闻
        recent_news = self._filter_recent_news(valid_news_events)

        if not recent_news:
            self.logger.info("No recent news events found")
            return results

        # 为每个市场数据匹配相关新闻
        for market_data_item in valid_market_data:
            try:
                related_news = self._find_related_news(market_data_item, recent_news)
                if related_news:
                    result = self._evaluate_black_horse_opportunity(
                        market_data_item, related_news
                    )
                    if result and result.score >= self.get_min_score():
                        results.append(result)
            except Exception as e:
                self.logger.error(
                    "Error evaluating black horse opportunity",
                    symbol=market_data_item.symbol,
                    error=str(e),
                )

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        execution_time = time.time() - start_time
        self.log_rule_execution(len(valid_market_data), len(results), execution_time)

        return results

    def _filter_recent_news(self, news_events: List[NewsEvent]) -> List[NewsEvent]:
        """过滤最近的新闻事件"""
        current_time = datetime.now()
        timeout_threshold = current_time - timedelta(seconds=self.news_timeout)

        recent_news = [
            event for event in news_events if event.timestamp >= timeout_threshold
        ]

        self.logger.info(
            "Filtered recent news events",
            total_events=len(news_events),
            recent_events=len(recent_news),
            timeout_hours=self.news_timeout / 3600,
        )

        return recent_news

    def _find_related_news(
        self, market_data: MarketData, news_events: List[NewsEvent]
    ) -> List[NewsEvent]:
        """查找与特定交易对相关的新闻"""
        symbol_base = market_data.symbol.split("/")[0].upper()  # 提取基础币种
        related_news = []

        for event in news_events:
            # 直接匹配交易对
            if event.symbol.upper() == symbol_base:
                related_news.append(event)
                continue

            # 内容关键词匹配
            if self._contains_relevant_keywords(event.content, symbol_base):
                related_news.append(event)

        return related_news

    def _contains_relevant_keywords(self, content: str, symbol: str) -> bool:
        """检查内容是否包含相关关键词"""
        content_lower = content.lower()
        symbol_lower = symbol.lower()

        # 检查是否包含币种名称
        if symbol_lower in content_lower:
            # 检查是否包含触发关键词
            for keyword in self.keywords:
                if keyword.lower() in content_lower:
                    return True

        return False

    def _evaluate_black_horse_opportunity(
        self, market_data: MarketData, related_news: List[NewsEvent]
    ) -> Optional[RuleResult]:
        """评估黑马机会"""
        # 计算新闻影响分数
        news_score = self._calculate_news_impact_score(related_news)

        # 计算市场反应分数
        market_reaction_score = self._calculate_market_reaction_score(market_data)

        # 计算时效性分数
        timing_score = self._calculate_timing_score(related_news)

        # 综合分数计算
        base_score = news_score * 0.5 + market_reaction_score * 0.3 + timing_score * 0.2
        final_score = base_score * self.score_multiplier

        # 计算置信度
        confidence = self.calculate_confidence(final_score)

        # 生成原因说明
        reason = self._generate_black_horse_reason(related_news, market_data)

        # 详细信息
        details = {
            "related_news_count": len(related_news),
            "news_events": [event.to_dict() for event in related_news[:3]],  # 最多显示3条新闻
            "market_data": market_data.to_dict(),
            "scores": {
                "news_impact": round(news_score, 2),
                "market_reaction": round(market_reaction_score, 2),
                "timing": round(timing_score, 2),
                "base_score": round(base_score, 2),
            },
            "multiplier": self.score_multiplier,
            "keywords_matched": self._get_matched_keywords(related_news),
        }

        return RuleResult(
            symbol=market_data.symbol,
            rule_type=self.get_rule_type(),
            score=round(final_score, 2),
            confidence=round(confidence, 3),
            reason=reason,
            details=details,
            timestamp=datetime.now(),
        )

    def _calculate_news_impact_score(self, news_events: List[NewsEvent]) -> float:
        """计算新闻影响分数"""
        if not news_events:
            return 0.0

        total_score = 0.0

        for event in news_events:
            # 基础分数
            base_score = 50.0

            # 交易所权重
            exchange_weight = self.exchange_weights.get(event.exchange.lower(), 0.3)

            # 新闻类型权重
            news_type_weight = self.news_type_weights.get(event.type.lower(), 0.5)

            # 新闻置信度
            confidence_weight = event.confidence

            # 计算单条新闻分数
            news_score = (
                base_score * exchange_weight * news_type_weight * confidence_weight
            )
            total_score += news_score

        # 多条新闻的协同效应（但有上限）
        synergy_factor = min(1.0 + (len(news_events) - 1) * 0.2, 2.0)

        return min(total_score * synergy_factor, 100.0)

    def _calculate_market_reaction_score(self, market_data: MarketData) -> float:
        """计算市场反应分数"""
        price_change = abs(market_data.price_change_24h)

        # 价格变化不足最小阈值
        if price_change < self.min_price_change:
            return 0.0

        # 基于价格变化幅度计算分数
        if price_change >= 0.5:  # 50%以上变化
            price_score = 100.0
        elif price_change >= 0.3:  # 30-50%变化
            price_score = 80.0
        elif price_change >= 0.15:  # 15-30%变化
            price_score = 60.0
        elif price_change >= 0.1:  # 10-15%变化
            price_score = 40.0
        else:  # 5-10%变化
            price_score = 20.0

        # 成交量因子
        volume_factor = min(market_data.volume_24h / 1000000, 2.0)  # 成交量越大，分数越高

        return min(price_score * volume_factor, 100.0)

    def _calculate_timing_score(self, news_events: List[NewsEvent]) -> float:
        """计算时效性分数"""
        if not news_events:
            return 0.0

        current_time = datetime.now()
        scores = []

        for event in news_events:
            # 计算新闻发布后的时间（小时）
            time_diff = (current_time - event.timestamp).total_seconds() / 3600

            # 时效性分数：越新的新闻分数越高
            if time_diff <= 1:  # 1小时内
                timing_score = 100.0
            elif time_diff <= 6:  # 6小时内
                timing_score = 80.0
            elif time_diff <= 12:  # 12小时内
                timing_score = 60.0
            elif time_diff <= 24:  # 24小时内
                timing_score = 40.0
            else:  # 超过24小时
                timing_score = 20.0

            scores.append(timing_score)

        # 返回最高时效性分数
        return max(scores) if scores else 0.0

    def _generate_black_horse_reason(
        self, news_events: List[NewsEvent], market_data: MarketData
    ) -> str:
        """生成黑马检测原因"""
        if not news_events:
            return "未发现相关新闻事件"

        # 提取主要新闻类型
        news_types = [event.type for event in news_events]
        main_type = max(set(news_types), key=news_types.count)

        # 提取主要交易所
        exchanges = [event.exchange for event in news_events]
        main_exchange = max(set(exchanges), key=exchanges.count)

        # 价格变化描述
        price_change = market_data.price_change_24h
        if price_change > 0:
            price_desc = f"上涨{price_change*100:.1f}%"
        else:
            price_desc = f"下跌{abs(price_change)*100:.1f}%"

        return (
            f"{main_exchange}发布{main_type}公告，价格{price_desc}，发现{len(news_events)}条相关新闻"
        )

    def _get_matched_keywords(self, news_events: List[NewsEvent]) -> List[str]:
        """获取匹配的关键词"""
        matched_keywords = set()

        for event in news_events:
            content_lower = event.content.lower()
            for keyword in self.keywords:
                if keyword.lower() in content_lower:
                    matched_keywords.add(keyword)

        return list(matched_keywords)
