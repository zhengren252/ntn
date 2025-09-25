# 黑马检测器
# 检测具有突破潜力的交易对，集成新闻事件触发机制

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

from ..communication.redis_client import RedisClient
from ..utils.logger import get_logger


@dataclass
class BlackHorseResult:
    """黑马检测结果"""

    detected: bool
    confidence: float
    price_momentum_score: float
    volume_spike_score: float
    news_sentiment_score: float
    technical_score: float
    reasons: List[str]
    risk_level: str
    details: Dict[str, Any]
    timestamp: str


class BlackHorseDetector:
    """黑马检测器

    检测具有突破潜力的交易对，综合考虑：
    1. 价格动量突破
    2. 成交量异常放大
    3. 新闻事件催化
    4. 技术指标信号
    """

    def __init__(self, redis_client: RedisClient, config: Dict[str, Any]):
        self.redis_client = redis_client
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        # 配置参数
        self.price_change_threshold = config.get("price_change_threshold", 0.1)  # 10%
        self.volume_spike_threshold = config.get("volume_spike_threshold", 2.0)  # 2倍
        self.confidence_threshold = config.get("confidence_threshold", 0.8)
        self.news_weight = config.get("news_weight", 0.3)
        self.lookback_hours = config.get("lookback_hours", 24)

        # 权重配置
        self.weights = {
            "price_momentum": config.get("price_momentum_weight", 0.3),
            "volume_spike": config.get("volume_spike_weight", 0.25),
            "news_sentiment": config.get("news_sentiment_weight", 0.25),
            "technical": config.get("technical_weight", 0.2),
        }

        # 新闻关键词
        self.positive_keywords = {
            "listing": ["list", "listing", "上市", "上线"],
            "partnership": ["partner", "partnership", "collaboration", "合作", "伙伴"],
            "upgrade": ["upgrade", "update", "improvement", "升级", "更新"],
            "adoption": ["adopt", "adoption", "integration", "采用", "集成"],
            "investment": ["invest", "funding", "raise", "投资", "融资"],
            "breakthrough": ["breakthrough", "innovation", "突破", "创新"],
        }

        self.negative_keywords = {
            "hack": ["hack", "exploit", "breach", "黑客", "攻击"],
            "regulation": ["ban", "restrict", "regulation", "禁止", "限制"],
            "delisting": ["delist", "remove", "下架", "移除"],
            "lawsuit": ["lawsuit", "legal", "court", "诉讼", "法律"],
        }

        self.logger.info(
            f"黑马检测器初始化完成，阈值: 价格变化={self.price_change_threshold}, "
            f"成交量倍数={self.volume_spike_threshold}, 置信度={self.confidence_threshold}"
        )

    async def detect(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> BlackHorseResult:
        """检测交易对是否为黑马

        Args:
            symbol: 交易对符号
            market_data: 市场数据

        Returns:
            BlackHorseResult: 检测结果
        """
        try:
            self.logger.debug(f"开始检测交易对 {symbol} 的黑马特征")

            # 计算各项指标
            price_momentum_score = await self._calculate_price_momentum_score(
                symbol, market_data
            )
            volume_spike_score = await self._calculate_volume_spike_score(
                symbol, market_data
            )
            news_sentiment_score = await self._calculate_news_sentiment_score(
                symbol, market_data
            )
            technical_score = await self._calculate_technical_score(symbol, market_data)

            # 计算综合置信度
            confidence = (
                price_momentum_score * self.weights["price_momentum"]
                + volume_spike_score * self.weights["volume_spike"]
                + news_sentiment_score * self.weights["news_sentiment"]
                + technical_score * self.weights["technical"]
            )

            # 生成检测原因
            reasons = self._generate_reasons(
                price_momentum_score,
                volume_spike_score,
                news_sentiment_score,
                technical_score,
                market_data,
            )

            # 评估风险等级
            risk_level = self._assess_risk_level(confidence, market_data)

            # 判断是否检测到黑马
            detected = (
                confidence >= self.confidence_threshold
                and price_momentum_score > 0.6
                and volume_spike_score > 0.5
            )

            # 构建详细信息
            details = {
                "symbol": symbol,
                "price": market_data.get("price", 0),
                "volume_24h": market_data.get("volume", 0),
                "change_24h": market_data.get("change_24h", 0),
                "market_cap": market_data.get("market_cap", 0),
                "technical_indicators": market_data.get("technical_indicators", {}),
                "social_metrics": market_data.get("social_metrics", {}),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "thresholds": {
                    "price_change": self.price_change_threshold,
                    "volume_spike": self.volume_spike_threshold,
                    "confidence": self.confidence_threshold,
                },
                "weights": self.weights,
                "score_breakdown": {
                    "price_momentum": price_momentum_score,
                    "volume_spike": volume_spike_score,
                    "news_sentiment": news_sentiment_score,
                    "technical": technical_score,
                },
            }

            result = BlackHorseResult(
                detected=detected,
                confidence=confidence,
                price_momentum_score=price_momentum_score,
                volume_spike_score=volume_spike_score,
                news_sentiment_score=news_sentiment_score,
                technical_score=technical_score,
                reasons=reasons,
                risk_level=risk_level,
                details=details,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # 记录结果
            if detected:
                self.logger.info(
                    f"黑马检测触发: {symbol}, 置信度={confidence:.3f}, "
                    f"风险等级={risk_level}, 原因={reasons}"
                )
            else:
                self.logger.debug(f"黑马检测未触发: {symbol}, 置信度={confidence:.3f}")

            # 存储检测结果
            await self._store_detection_result(symbol, result)

            return result

        except Exception as e:
            self.logger.error(f"检测交易对 {symbol} 时发生错误: {e}")
            return BlackHorseResult(
                detected=False,
                confidence=0.0,
                price_momentum_score=0.0,
                volume_spike_score=0.0,
                news_sentiment_score=0.0,
                technical_score=0.0,
                reasons=[f"检测错误: {str(e)}"],
                risk_level="unknown",
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def _calculate_price_momentum_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算价格动量得分"""
        try:
            current_change = market_data.get("change_24h", 0)

            # 获取历史价格数据
            historical_data = await self.redis_client.get_historical_data(
                symbol, hours=self.lookback_hours
            )

            if historical_data and len(historical_data) > 1:
                # 计算历史价格变化统计
                price_changes = [data.get("change_24h", 0) for data in historical_data]
                price_changes = [c for c in price_changes if c != 0]  # 过滤无效数据

                if price_changes:
                    avg_change = np.mean(price_changes)
                    std_change = np.std(price_changes)

                    # 计算动量突破程度
                    if std_change > 0:
                        momentum_z_score = (current_change - avg_change) / std_change
                        # 将Z-score转换为0-1分数，正向突破得分更高
                        if current_change > 0:
                            momentum_score = min(max((momentum_z_score + 1) / 3, 0), 1)
                        else:
                            momentum_score = 0.1  # 负向变化得分很低
                    else:
                        momentum_score = (
                            abs(current_change) / self.price_change_threshold
                        )
                else:
                    momentum_score = abs(current_change) / self.price_change_threshold
            else:
                # 没有历史数据时，直接与阈值比较
                momentum_score = abs(current_change) / self.price_change_threshold

            # 正向变化加分
            if current_change > 0:
                momentum_score *= 1.2  # 20%加分

            return min(momentum_score, 1.0)

        except Exception as e:
            self.logger.error(f"计算价格动量得分时发生错误: {e}")
            return 0.0

    async def _calculate_volume_spike_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算成交量激增得分"""
        try:
            current_volume = market_data.get("volume", 0)

            # 获取历史成交量数据
            historical_data = await self.redis_client.get_historical_data(
                symbol, hours=self.lookback_hours
            )

            if historical_data:
                # 计算历史成交量平均值
                volumes = [data.get("volume", 0) for data in historical_data]
                volumes = [v for v in volumes if v > 0]  # 过滤无效数据

                if volumes:
                    avg_volume = np.mean(volumes)

                    if avg_volume > 0:
                        volume_multiplier = current_volume / avg_volume
                        # 将倍数转换为0-1分数
                        spike_score = min(
                            volume_multiplier / (self.volume_spike_threshold * 2), 1.0
                        )
                    else:
                        spike_score = 0.5
                else:
                    spike_score = 0.5
            else:
                # 没有历史数据时，使用技术指标中的成交量SMA
                technical_indicators = market_data.get("technical_indicators", {})
                volume_sma = technical_indicators.get("volume_sma", 0)

                if volume_sma > 0:
                    volume_multiplier = current_volume / volume_sma
                    spike_score = min(
                        volume_multiplier / (self.volume_spike_threshold * 2), 1.0
                    )
                else:
                    spike_score = 0.5

            return spike_score

        except Exception as e:
            self.logger.error(f"计算成交量激增得分时发生错误: {e}")
            return 0.0

    async def _calculate_news_sentiment_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算新闻情绪得分"""
        try:
            # 获取相关新闻事件
            news_events = await self.redis_client.get_news_events(
                symbol=symbol, hours=self.lookback_hours
            )

            if not news_events:
                # 如果没有新闻，检查市场数据中的情绪指标
                news_sentiment = market_data.get("news_sentiment", 0.5)
                return news_sentiment

            # 分析新闻情绪
            sentiment_scores = []
            impact_weights = []

            for news in news_events:
                # 获取新闻基本情绪
                base_sentiment = news.get("sentiment", 0.5)

                # 分析新闻内容关键词
                content = (
                    news.get("title", "") + " " + news.get("content", "")
                ).lower()
                keyword_sentiment = self._analyze_news_keywords(content)

                # 综合情绪得分
                combined_sentiment = (base_sentiment + keyword_sentiment) / 2

                # 获取影响权重
                impact_score = news.get("impact_score", 0.5)
                relevance = news.get("relevance", 0.5)
                weight = impact_score * relevance

                sentiment_scores.append(combined_sentiment)
                impact_weights.append(weight)

            if sentiment_scores:
                # 加权平均情绪得分
                if sum(impact_weights) > 0:
                    weighted_sentiment = np.average(
                        sentiment_scores, weights=impact_weights
                    )
                else:
                    weighted_sentiment = np.mean(sentiment_scores)

                return min(max(weighted_sentiment, 0), 1)
            else:
                return 0.5

        except Exception as e:
            self.logger.error(f"计算新闻情绪得分时发生错误: {e}")
            return 0.5

    def _analyze_news_keywords(self, content: str) -> float:
        """分析新闻关键词情绪"""
        try:
            positive_score = 0
            negative_score = 0

            # 检查正面关键词
            for category, keywords in self.positive_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in content:
                        if category in ["listing", "partnership", "investment"]:
                            positive_score += 0.3  # 高权重关键词
                        else:
                            positive_score += 0.2

            # 检查负面关键词
            for category, keywords in self.negative_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in content:
                        if category in ["hack", "delisting"]:
                            negative_score += 0.4  # 高权重负面关键词
                        else:
                            negative_score += 0.2

            # 计算净情绪得分
            net_sentiment = positive_score - negative_score

            # 转换为0-1分数
            sentiment_score = 0.5 + (net_sentiment / 2)

            return min(max(sentiment_score, 0), 1)

        except Exception as e:
            self.logger.error(f"分析新闻关键词时发生错误: {e}")
            return 0.5

    async def _calculate_technical_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算技术指标得分"""
        try:
            technical_indicators = market_data.get("technical_indicators", {})

            if not technical_indicators:
                return 0.5

            scores = []

            # RSI指标分析
            rsi = technical_indicators.get("rsi", 50)
            if 30 <= rsi <= 70:  # 正常范围
                rsi_score = 0.7
            elif rsi > 70:  # 超买
                rsi_score = 0.4
            else:  # 超卖，可能反弹
                rsi_score = 0.8
            scores.append(rsi_score)

            # 布林带分析
            price = market_data.get("price", 0)
            bollinger_upper = technical_indicators.get("bollinger_upper", 0)
            bollinger_lower = technical_indicators.get("bollinger_lower", 0)

            if bollinger_upper > 0 and bollinger_lower > 0:
                bollinger_position = (price - bollinger_lower) / (
                    bollinger_upper - bollinger_lower
                )
                if bollinger_position > 0.8:  # 接近上轨
                    bollinger_score = 0.9
                elif bollinger_position < 0.2:  # 接近下轨
                    bollinger_score = 0.8
                else:
                    bollinger_score = 0.6
                scores.append(bollinger_score)

            # 移动平均线分析
            price_sma_20 = technical_indicators.get("price_sma_20", 0)
            if price_sma_20 > 0:
                sma_ratio = price / price_sma_20
                if sma_ratio > 1.05:  # 价格明显高于20日均线
                    sma_score = 0.8
                elif sma_ratio > 1.02:
                    sma_score = 0.7
                else:
                    sma_score = 0.5
                scores.append(sma_score)

            # 社交指标分析
            social_metrics = market_data.get("social_metrics", {})
            if social_metrics:
                mentions = social_metrics.get("mentions", 0)
                sentiment_score = social_metrics.get("sentiment_score", 0.5)

                # 提及次数得分
                if mentions > 10000:
                    mention_score = 0.9
                elif mentions > 5000:
                    mention_score = 0.7
                elif mentions > 1000:
                    mention_score = 0.6
                else:
                    mention_score = 0.4

                # 综合社交得分
                social_score = (mention_score + sentiment_score) / 2
                scores.append(social_score)

            if scores:
                return np.mean(scores)
            else:
                return 0.5

        except Exception as e:
            self.logger.error(f"计算技术指标得分时发生错误: {e}")
            return 0.5

    def _generate_reasons(
        self,
        price_score: float,
        volume_score: float,
        news_score: float,
        technical_score: float,
        market_data: Dict[str, Any],
    ) -> List[str]:
        """生成检测原因"""
        reasons = []

        try:
            # 价格动量原因
            if price_score > 0.7:
                change_24h = market_data.get("change_24h", 0)
                reasons.append(f"强劲价格动量 (+{change_24h:.2%})")
            elif price_score > 0.5:
                reasons.append("适度价格上涨")

            # 成交量原因
            if volume_score > 0.8:
                reasons.append("成交量显著放大")
            elif volume_score > 0.6:
                reasons.append("成交量增加")

            # 新闻情绪原因
            if news_score > 0.7:
                reasons.append("正面新闻催化")
            elif news_score > 0.6:
                reasons.append("市场情绪积极")

            # 技术指标原因
            if technical_score > 0.7:
                reasons.append("技术指标强势")
            elif technical_score > 0.6:
                reasons.append("技术面支撑")

            # 特殊情况
            technical_indicators = market_data.get("technical_indicators", {})
            rsi = technical_indicators.get("rsi", 50)
            if rsi < 30:
                reasons.append("RSI超卖，可能反弹")

            if not reasons:
                reasons.append("综合指标显示潜在机会")

            return reasons

        except Exception as e:
            self.logger.error(f"生成检测原因时发生错误: {e}")
            return ["分析完成"]

    def _assess_risk_level(self, confidence: float, market_data: Dict[str, Any]) -> str:
        """评估风险等级"""
        try:
            # 基于置信度的基础风险评估
            if confidence >= 0.9:
                base_risk = "low"
            elif confidence >= 0.7:
                base_risk = "medium"
            else:
                base_risk = "high"

            # 考虑市值因素
            market_cap = market_data.get("market_cap", 0)
            if market_cap < 100000000:  # 小于1亿美元
                if base_risk == "low":
                    base_risk = "medium"
                elif base_risk == "medium":
                    base_risk = "high"

            # 考虑波动率因素
            technical_indicators = market_data.get("technical_indicators", {})
            volatility = technical_indicators.get("volatility", 0)
            if volatility > 0.2:  # 高波动率
                if base_risk == "low":
                    base_risk = "medium"
                elif base_risk == "medium":
                    base_risk = "high"

            return base_risk

        except Exception as e:
            self.logger.error(f"评估风险等级时发生错误: {e}")
            return "unknown"

    async def _store_detection_result(self, symbol: str, result: BlackHorseResult):
        """存储检测结果"""
        try:
            result_data = {
                "detector": "black_horse",
                "symbol": symbol,
                "detected": result.detected,
                "confidence": result.confidence,
                "price_momentum_score": result.price_momentum_score,
                "volume_spike_score": result.volume_spike_score,
                "news_sentiment_score": result.news_sentiment_score,
                "technical_score": result.technical_score,
                "reasons": result.reasons,
                "risk_level": result.risk_level,
                "details": result.details,
                "timestamp": result.timestamp,
            }

            # 存储到Redis
            await self.redis_client.set_scan_result(
                f"black_horse_{symbol}", result_data
            )

            # 如果检测到黑马，存储到检测列表
            if result.detected:
                await self.redis_client.add_to_triggered_list(
                    "black_horse", symbol, result_data
                )

        except Exception as e:
            self.logger.error(f"存储检测结果时发生错误: {e}")

    async def get_detected_symbols(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取检测到的黑马交易对列表"""
        try:
            return await self.redis_client.get_triggered_list("black_horse", limit)
        except Exception as e:
            self.logger.error(f"获取检测列表时发生错误: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """获取检测器统计信息"""
        try:
            stats = {
                "detector": "black_horse",
                "config": self.config,
                "thresholds": {
                    "price_change": self.price_change_threshold,
                    "volume_spike": self.volume_spike_threshold,
                    "confidence": self.confidence_threshold,
                },
                "weights": self.weights,
                "lookback_hours": self.lookback_hours,
            }

            # 获取检测统计
            detected_count = len(await self.get_detected_symbols())
            stats["detected_count"] = detected_count

            return stats

        except Exception as e:
            self.logger.error(f"获取统计信息时发生错误: {e}")
            return {}

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        try:
            self.config.update(new_config)

            # 更新阈值
            self.price_change_threshold = self.config.get(
                "price_change_threshold", self.price_change_threshold
            )
            self.volume_spike_threshold = self.config.get(
                "volume_spike_threshold", self.volume_spike_threshold
            )
            self.confidence_threshold = self.config.get(
                "confidence_threshold", self.confidence_threshold
            )

            # 更新权重
            for key in [
                "price_momentum_weight",
                "volume_spike_weight",
                "news_sentiment_weight",
                "technical_weight",
            ]:
                if key in new_config:
                    weight_key = key.replace("_weight", "")
                    self.weights[weight_key] = new_config[key]

            self.logger.info(f"黑马检测器配置已更新: {new_config}")

        except Exception as e:
            self.logger.error(f"更新配置时发生错误: {e}")
