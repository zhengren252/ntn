# 潜力挖掘器
# 发现低市值低价格但具有增长潜力的币种

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from ..communication.redis_client import RedisClient
from ..utils.logger import get_logger


@dataclass
class PotentialResult:
    """潜力挖掘结果"""

    has_potential: bool
    potential_score: float
    market_cap_score: float
    price_score: float
    growth_score: float
    fundamentals_score: float
    risk_score: float
    reasons: List[str]
    category: str
    details: Dict[str, Any]
    timestamp: str


class PotentialFinder:
    """潜力挖掘器

    发现低市值低价格但具有增长潜力的币种，综合考虑：
    1. 市值规模（偏好小市值）
    2. 价格水平（偏好低价格）
    3. 增长趋势（技术和基本面）
    4. 基本面质量
    5. 风险评估
    """

    def __init__(self, redis_client: RedisClient, config: Dict[str, Any]):
        self.redis_client = redis_client
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        # 配置参数
        self.max_market_cap = config.get("max_market_cap", 500000000)  # 5亿美元
        self.max_price = config.get("max_price", 1.0)  # 1美元
        self.min_volume = config.get("min_volume", 100000)  # 10万美元日交易量
        self.potential_threshold = config.get("potential_threshold", 0.7)
        self.lookback_days = config.get("lookback_days", 30)

        # 权重配置
        self.weights = {
            "market_cap": config.get("market_cap_weight", 0.25),
            "price": config.get("price_weight", 0.2),
            "growth": config.get("growth_weight", 0.25),
            "fundamentals": config.get("fundamentals_weight", 0.2),
            "risk": config.get("risk_weight", 0.1),
        }

        # 分类标准
        self.categories = {
            "micro_cap": {"max_market_cap": 50000000, "max_price": 0.1},  # 微市值
            "small_cap": {"max_market_cap": 200000000, "max_price": 0.5},  # 小市值
            "low_price": {"max_market_cap": 500000000, "max_price": 1.0},  # 低价格
        }

        # 基本面指标权重
        self.fundamental_weights = {
            "development_activity": 0.3,
            "community_strength": 0.25,
            "partnership_quality": 0.2,
            "technology_innovation": 0.15,
            "tokenomics": 0.1,
        }

        self.logger.info(
            f"潜力挖掘器初始化完成，最大市值={self.max_market_cap}, 最大价格={self.max_price}, 最小成交量={self.min_volume}"
        )

    async def analyze(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> PotentialResult:
        """分析交易对的增长潜力

        Args:
            symbol: 交易对符号
            market_data: 市场数据

        Returns:
            PotentialResult: 潜力分析结果
        """
        try:
            self.logger.debug(f"开始分析交易对 {symbol} 的增长潜力")

            # 预筛选：基本条件检查
            if not await self._meets_basic_criteria(symbol, market_data):
                return self._create_negative_result(symbol, "不符合基本筛选条件")

            # 计算各项得分
            market_cap_score = self._calculate_market_cap_score(market_data)
            price_score = self._calculate_price_score(market_data)
            growth_score = await self._calculate_growth_score(symbol, market_data)
            fundamentals_score = await self._calculate_fundamentals_score(
                symbol, market_data
            )
            risk_score = await self._calculate_risk_score(symbol, market_data)

            # 计算综合潜力得分
            potential_score = (
                market_cap_score * self.weights["market_cap"]
                + price_score * self.weights["price"]
                + growth_score * self.weights["growth"]
                + fundamentals_score * self.weights["fundamentals"]
                + (1 - risk_score) * self.weights["risk"]  # 风险越低得分越高
            )

            # 生成分析原因
            reasons = self._generate_reasons(
                market_cap_score,
                price_score,
                growth_score,
                fundamentals_score,
                risk_score,
                market_data,
            )

            # 确定分类
            category = self._determine_category(market_data)

            # 判断是否具有潜力
            has_potential = (
                potential_score >= self.potential_threshold
                and growth_score > 0.5
                and fundamentals_score > 0.4
                and risk_score < 0.8
            )

            # 构建详细信息
            details = {
                "symbol": symbol,
                "market_cap": market_data.get("market_cap", 0),
                "price": market_data.get("price", 0),
                "volume_24h": market_data.get("volume", 0),
                "change_24h": market_data.get("change_24h", 0),
                "change_7d": market_data.get("change_7d", 0),
                "change_30d": market_data.get("change_30d", 0),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "criteria": {
                    "max_market_cap": self.max_market_cap,
                    "max_price": self.max_price,
                    "min_volume": self.min_volume,
                    "potential_threshold": self.potential_threshold,
                },
                "weights": self.weights,
                "score_breakdown": {
                    "market_cap": market_cap_score,
                    "price": price_score,
                    "growth": growth_score,
                    "fundamentals": fundamentals_score,
                    "risk": risk_score,
                },
                "technical_indicators": market_data.get("technical_indicators", {}),
                "fundamental_metrics": market_data.get("fundamental_metrics", {}),
                "social_metrics": market_data.get("social_metrics", {}),
            }

            result = PotentialResult(
                has_potential=has_potential,
                potential_score=potential_score,
                market_cap_score=market_cap_score,
                price_score=price_score,
                growth_score=growth_score,
                fundamentals_score=fundamentals_score,
                risk_score=risk_score,
                reasons=reasons,
                category=category,
                details=details,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # 记录结果
            if has_potential:
                self.logger.info(
                    f"发现潜力币种: {symbol}, 潜力得分={potential_score:.3f}, 分类={category}, 原因={reasons}"
                )
            else:
                self.logger.debug(f"潜力分析未通过: {symbol}, 潜力得分={potential_score:.3f}")

            # 存储分析结果
            await self._store_analysis_result(symbol, result)

            return result

        except Exception as e:
            self.logger.error(f"分析交易对 {symbol} 时发生错误: {e}")
            return self._create_error_result(symbol, str(e))

    async def _meets_basic_criteria(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> bool:
        """检查是否符合基本筛选条件"""
        try:
            market_cap = market_data.get("market_cap", 0)
            price = market_data.get("price", 0)
            volume = market_data.get("volume", 0)

            # 基本条件检查
            if market_cap <= 0 or market_cap > self.max_market_cap:
                self.logger.debug(f"{symbol} 市值不符合条件: {market_cap}")
                return False

            if price <= 0 or price > self.max_price:
                self.logger.debug(f"{symbol} 价格不符合条件: {price}")
                return False

            if volume < self.min_volume:
                self.logger.debug(f"{symbol} 成交量不符合条件: {volume}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"检查基本条件时发生错误: {e}")
            return False

    def _calculate_market_cap_score(self, market_data: Dict[str, Any]) -> float:
        """计算市值得分（市值越小得分越高）"""
        try:
            market_cap = market_data.get("market_cap", 0)

            if market_cap <= 0:
                return 0.0

            # 使用对数缩放，市值越小得分越高
            if market_cap <= 10000000:  # 1000万以下
                score = 1.0
            elif market_cap <= 50000000:  # 5000万以下
                score = 0.9
            elif market_cap <= 100000000:  # 1亿以下
                score = 0.8
            elif market_cap <= 200000000:  # 2亿以下
                score = 0.6
            elif market_cap <= 500000000:  # 5亿以下
                score = 0.4
            else:
                score = 0.2

            return score

        except Exception as e:
            self.logger.error(f"计算市值得分时发生错误: {e}")
            return 0.0

    def _calculate_price_score(self, market_data: Dict[str, Any]) -> float:
        """计算价格得分（价格越低得分越高）"""
        try:
            price = market_data.get("price", 0)

            if price <= 0:
                return 0.0

            # 价格区间得分
            if price <= 0.001:  # 0.001以下
                score = 1.0
            elif price <= 0.01:  # 0.01以下
                score = 0.9
            elif price <= 0.1:  # 0.1以下
                score = 0.8
            elif price <= 0.5:  # 0.5以下
                score = 0.6
            elif price <= 1.0:  # 1.0以下
                score = 0.4
            else:
                score = 0.2

            return score

        except Exception as e:
            self.logger.error(f"计算价格得分时发生错误: {e}")
            return 0.0

    async def _calculate_growth_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算增长得分"""
        try:
            # 获取历史价格数据
            historical_data = await self.redis_client.get_historical_data(
                symbol, hours=self.lookback_days * 24
            )

            scores = []

            # 短期增长（7天）
            change_7d = market_data.get("change_7d", 0)
            if change_7d > 0.2:  # 20%以上
                short_term_score = 0.9
            elif change_7d > 0.1:  # 10%以上
                short_term_score = 0.7
            elif change_7d > 0:
                short_term_score = 0.6
            else:
                short_term_score = 0.3
            scores.append(short_term_score)

            # 中期增长（30天）
            change_30d = market_data.get("change_30d", 0)
            if change_30d > 0.5:  # 50%以上
                medium_term_score = 0.9
            elif change_30d > 0.2:  # 20%以上
                medium_term_score = 0.7
            elif change_30d > 0:
                medium_term_score = 0.6
            else:
                medium_term_score = 0.3
            scores.append(medium_term_score)

            # 成交量增长趋势
            if historical_data and len(historical_data) > 7:
                recent_volumes = [d.get("volume", 0) for d in historical_data[-7:]]
                earlier_volumes = [d.get("volume", 0) for d in historical_data[-14:-7]]

                if recent_volumes and earlier_volumes:
                    recent_avg = np.mean(recent_volumes)
                    earlier_avg = np.mean(earlier_volumes)

                    if earlier_avg > 0:
                        volume_growth = (recent_avg - earlier_avg) / earlier_avg
                        if volume_growth > 0.5:
                            volume_score = 0.9
                        elif volume_growth > 0.2:
                            volume_score = 0.7
                        elif volume_growth > 0:
                            volume_score = 0.6
                        else:
                            volume_score = 0.4
                        scores.append(volume_score)

            # 技术指标趋势
            technical_indicators = market_data.get("technical_indicators", {})
            if technical_indicators:
                # RSI趋势
                rsi = technical_indicators.get("rsi", 50)
                if 40 <= rsi <= 60:  # 健康范围
                    rsi_score = 0.8
                elif 30 <= rsi < 40:  # 可能反弹
                    rsi_score = 0.7
                else:
                    rsi_score = 0.5
                scores.append(rsi_score)

                # 移动平均线趋势
                price = market_data.get("price", 0)
                sma_20 = technical_indicators.get("price_sma_20", 0)
                if sma_20 > 0 and price > sma_20 * 1.05:  # 价格高于20日均线5%
                    ma_score = 0.8
                elif sma_20 > 0 and price > sma_20:
                    ma_score = 0.6
                else:
                    ma_score = 0.4
                scores.append(ma_score)

            return np.mean(scores) if scores else 0.5

        except Exception as e:
            self.logger.error(f"计算增长得分时发生错误: {e}")
            return 0.5

    async def _calculate_fundamentals_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算基本面得分"""
        try:
            fundamental_metrics = market_data.get("fundamental_metrics", {})
            social_metrics = market_data.get("social_metrics", {})

            scores = {}

            # 开发活动得分
            github_commits = fundamental_metrics.get("github_commits", 0)
            if github_commits > 100:
                scores["development_activity"] = 0.9
            elif github_commits > 50:
                scores["development_activity"] = 0.7
            elif github_commits > 10:
                scores["development_activity"] = 0.5
            else:
                scores["development_activity"] = 0.3

            # 社区强度得分
            twitter_followers = social_metrics.get("twitter_followers", 0)
            telegram_members = social_metrics.get("telegram_members", 0)
            community_size = twitter_followers + telegram_members

            if community_size > 100000:
                scores["community_strength"] = 0.9
            elif community_size > 50000:
                scores["community_strength"] = 0.7
            elif community_size > 10000:
                scores["community_strength"] = 0.5
            else:
                scores["community_strength"] = 0.3

            # 合作伙伴质量得分
            partnerships = fundamental_metrics.get("partnerships", [])
            if len(partnerships) > 5:
                scores["partnership_quality"] = 0.8
            elif len(partnerships) > 2:
                scores["partnership_quality"] = 0.6
            elif len(partnerships) > 0:
                scores["partnership_quality"] = 0.4
            else:
                scores["partnership_quality"] = 0.2

            # 技术创新得分
            innovation_score = fundamental_metrics.get("innovation_score", 0.5)
            scores["technology_innovation"] = min(max(innovation_score, 0), 1)

            # 代币经济学得分
            total_supply = fundamental_metrics.get("total_supply", 0)
            circulating_supply = fundamental_metrics.get("circulating_supply", 0)

            if total_supply > 0 and circulating_supply > 0:
                circulation_ratio = circulating_supply / total_supply
                if 0.6 <= circulation_ratio <= 0.9:  # 健康的流通比例
                    scores["tokenomics"] = 0.8
                elif 0.4 <= circulation_ratio < 0.6:
                    scores["tokenomics"] = 0.6
                else:
                    scores["tokenomics"] = 0.4
            else:
                scores["tokenomics"] = 0.5

            # 计算加权平均得分
            weighted_score = 0
            total_weight = 0

            for metric, weight in self.fundamental_weights.items():
                if metric in scores:
                    weighted_score += scores[metric] * weight
                    total_weight += weight

            if total_weight > 0:
                return weighted_score / total_weight
            else:
                return 0.5

        except Exception as e:
            self.logger.error(f"计算基本面得分时发生错误: {e}")
            return 0.5

    async def _calculate_risk_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算风险得分（得分越高风险越大）"""
        try:
            risk_factors = []

            # 波动率风险
            technical_indicators = market_data.get("technical_indicators", {})
            volatility = technical_indicators.get("volatility", 0)
            if volatility > 0.5:  # 高波动率
                risk_factors.append(0.8)
            elif volatility > 0.3:
                risk_factors.append(0.6)
            else:
                risk_factors.append(0.3)

            # 流动性风险
            volume = market_data.get("volume", 0)
            market_cap = market_data.get("market_cap", 0)
            if market_cap > 0:
                volume_ratio = volume / market_cap
                if volume_ratio < 0.01:  # 低流动性
                    risk_factors.append(0.8)
                elif volume_ratio < 0.05:
                    risk_factors.append(0.6)
                else:
                    risk_factors.append(0.3)

            # 市值风险（市值越小风险越大）
            market_cap = market_data.get("market_cap", 0)
            if market_cap < 10000000:  # 1000万以下
                risk_factors.append(0.9)
            elif market_cap < 50000000:  # 5000万以下
                risk_factors.append(0.7)
            elif market_cap < 100000000:  # 1亿以下
                risk_factors.append(0.5)
            else:
                risk_factors.append(0.3)

            # 技术风险
            fundamental_metrics = market_data.get("fundamental_metrics", {})
            security_score = fundamental_metrics.get("security_score", 0.5)
            risk_factors.append(1 - security_score)  # 安全性越低风险越高

            # 监管风险
            regulatory_risk = fundamental_metrics.get("regulatory_risk", 0.5)
            risk_factors.append(regulatory_risk)

            return np.mean(risk_factors) if risk_factors else 0.5

        except Exception as e:
            self.logger.error(f"计算风险得分时发生错误: {e}")
            return 0.5

    def _generate_reasons(
        self,
        market_cap_score: float,
        price_score: float,
        growth_score: float,
        fundamentals_score: float,
        risk_score: float,
        market_data: Dict[str, Any],
    ) -> List[str]:
        """生成分析原因"""
        reasons = []

        try:
            # 市值优势
            if market_cap_score > 0.8:
                market_cap = market_data.get("market_cap", 0)
                reasons.append(f"超低市值 (${market_cap/1000000:.1f}M)")
            elif market_cap_score > 0.6:
                reasons.append("小市值优势")

            # 价格优势
            if price_score > 0.8:
                price = market_data.get("price", 0)
                reasons.append(f"超低价格 (${price:.4f})")
            elif price_score > 0.6:
                reasons.append("低价格优势")

            # 增长潜力
            if growth_score > 0.7:
                reasons.append("强劲增长趋势")
            elif growth_score > 0.6:
                reasons.append("积极增长信号")

            # 基本面质量
            if fundamentals_score > 0.7:
                reasons.append("优质基本面")
            elif fundamentals_score > 0.5:
                reasons.append("基本面支撑")

            # 风险评估
            if risk_score < 0.4:
                reasons.append("风险可控")
            elif risk_score < 0.6:
                reasons.append("中等风险")
            else:
                reasons.append("高风险项目")

            # 特殊优势
            change_7d = market_data.get("change_7d", 0)
            if change_7d > 0.3:
                reasons.append(f"近期强势 (+{change_7d:.1%})")

            fundamental_metrics = market_data.get("fundamental_metrics", {})
            github_commits = fundamental_metrics.get("github_commits", 0)
            if github_commits > 100:
                reasons.append("活跃开发")

            if not reasons:
                reasons.append("综合指标显示潜力")

            return reasons

        except Exception as e:
            self.logger.error(f"生成分析原因时发生错误: {e}")
            return ["分析完成"]

    def _determine_category(self, market_data: Dict[str, Any]) -> str:
        """确定币种分类"""
        try:
            market_cap = market_data.get("market_cap", 0)
            price = market_data.get("price", 0)

            for category, criteria in self.categories.items():
                if (
                    market_cap <= criteria["max_market_cap"]
                    and price <= criteria["max_price"]
                ):
                    return category

            return "other"

        except Exception as e:
            self.logger.error(f"确定分类时发生错误: {e}")
            return "unknown"

    def _create_negative_result(self, symbol: str, reason: str) -> PotentialResult:
        """创建负面结果"""
        return PotentialResult(
            has_potential=False,
            potential_score=0.0,
            market_cap_score=0.0,
            price_score=0.0,
            growth_score=0.0,
            fundamentals_score=0.0,
            risk_score=1.0,
            reasons=[reason],
            category="excluded",
            details={"symbol": symbol, "exclusion_reason": reason},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _create_error_result(self, symbol: str, error: str) -> PotentialResult:
        """创建错误结果"""
        return PotentialResult(
            has_potential=False,
            potential_score=0.0,
            market_cap_score=0.0,
            price_score=0.0,
            growth_score=0.0,
            fundamentals_score=0.0,
            risk_score=1.0,
            reasons=[f"分析错误: {error}"],
            category="error",
            details={"symbol": symbol, "error": error},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _store_analysis_result(self, symbol: str, result: PotentialResult):
        """存储分析结果"""
        try:
            result_data = {
                "analyzer": "potential_finder",
                "symbol": symbol,
                "has_potential": result.has_potential,
                "potential_score": result.potential_score,
                "market_cap_score": result.market_cap_score,
                "price_score": result.price_score,
                "growth_score": result.growth_score,
                "fundamentals_score": result.fundamentals_score,
                "risk_score": result.risk_score,
                "reasons": result.reasons,
                "category": result.category,
                "details": result.details,
                "timestamp": result.timestamp,
            }

            # 存储到Redis
            await self.redis_client.set_scan_result(f"potential_{symbol}", result_data)

            # 如果发现潜力，存储到潜力列表
            if result.has_potential:
                await self.redis_client.add_to_triggered_list(
                    "potential", symbol, result_data
                )

        except Exception as e:
            self.logger.error(f"存储分析结果时发生错误: {e}")

    async def get_potential_symbols(
        self, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取具有潜力的交易对列表"""
        try:
            all_results = await self.redis_client.get_triggered_list(
                "potential", limit * 2
            )

            if category:
                # 按分类过滤
                filtered_results = [
                    result
                    for result in all_results
                    if result.get("category") == category
                ]
                return filtered_results[:limit]
            else:
                return all_results[:limit]

        except Exception as e:
            self.logger.error(f"获取潜力列表时发生错误: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """获取分析器统计信息"""
        try:
            stats = {
                "analyzer": "potential_finder",
                "config": self.config,
                "criteria": {
                    "max_market_cap": self.max_market_cap,
                    "max_price": self.max_price,
                    "min_volume": self.min_volume,
                    "potential_threshold": self.potential_threshold,
                },
                "weights": self.weights,
                "categories": self.categories,
                "lookback_days": self.lookback_days,
            }

            # 获取各分类统计
            category_stats = {}
            for category in self.categories.keys():
                potential_symbols = await self.get_potential_symbols(category)
                category_stats[category] = len(potential_symbols)

            stats["category_counts"] = category_stats
            stats["total_potential_count"] = sum(category_stats.values())

            return stats

        except Exception as e:
            self.logger.error(f"获取统计信息时发生错误: {e}")
            return {}

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        try:
            self.config.update(new_config)

            # 更新筛选条件
            self.max_market_cap = self.config.get("max_market_cap", self.max_market_cap)
            self.max_price = self.config.get("max_price", self.max_price)
            self.min_volume = self.config.get("min_volume", self.min_volume)
            self.potential_threshold = self.config.get(
                "potential_threshold", self.potential_threshold
            )

            # 更新权重
            for key in [
                "market_cap_weight",
                "price_weight",
                "growth_weight",
                "fundamentals_weight",
                "risk_weight",
            ]:
                if key in new_config:
                    weight_key = key.replace("_weight", "")
                    self.weights[weight_key] = new_config[key]

            self.logger.info(f"潜力挖掘器配置已更新: {new_config}")

        except Exception as e:
            self.logger.error(f"更新配置时发生错误: {e}")
