#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
潜力挖掘器规则引擎
发现低市值、低价格、高增长潜力的币种
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from .base import BaseRule, MarketData, RuleResult


@dataclass
class PotentialCriteria:
    """潜力币种筛选标准"""

    max_market_cap: float  # 最大市值（USDT）
    max_price: float  # 最大价格（USDT）
    min_volume_24h: float  # 最小24小时成交量
    min_price_change_7d: float  # 最小7日涨幅
    min_volume_growth_7d: float  # 最小7日成交量增长
    max_age_days: int  # 最大上市天数
    min_holders: int  # 最小持币地址数
    max_concentration: float  # 最大持币集中度


class PotentialFinder(BaseRule):
    """潜力挖掘器规则引擎"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)

        # 提取配置参数
        self.criteria = self._extract_criteria(config)
        self.score_weights = self._extract_score_weights(config)
        self.min_score = config.get("min_score", 60.0)
        self.enabled = config.get("enabled", True)

        # 验证配置
        self._validate_config(config)

    def _extract_criteria(self, config: Dict) -> PotentialCriteria:
        """提取筛选标准配置"""
        criteria_config = config.get("criteria", {})

        return PotentialCriteria(
            max_market_cap=criteria_config.get("max_market_cap", 100_000_000),  # 1亿USDT
            max_price=criteria_config.get("max_price", 1.0),  # 1 USDT
            min_volume_24h=criteria_config.get("min_volume_24h", 100_000),  # 10万USDT
            min_price_change_7d=criteria_config.get("min_price_change_7d", 0.1),  # 10%
            min_volume_growth_7d=criteria_config.get(
                "min_volume_growth_7d", 0.2
            ),  # 20%
            max_age_days=criteria_config.get("max_age_days", 365),  # 1年
            min_holders=criteria_config.get("min_holders", 1000),  # 1000个持币地址
            max_concentration=criteria_config.get("max_concentration", 0.5),  # 50%集中度
        )

    def _extract_score_weights(self, config: Dict) -> Dict[str, float]:
        """提取评分权重配置"""
        weights = config.get("score_weights", {})

        default_weights = {
            "market_cap": 0.2,  # 市值权重
            "price": 0.15,  # 价格权重
            "volume": 0.2,  # 成交量权重
            "growth": 0.25,  # 增长性权重
            "fundamentals": 0.2,  # 基本面权重
        }

        # 合并默认权重和用户配置
        result_weights = {**default_weights, **weights}

        # 验证权重总和
        total_weight = sum(result_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"权重总和不为1.0: {total_weight}，将进行归一化")
            # 归一化权重
            for key in result_weights:
                result_weights[key] /= total_weight

        return result_weights

    def _validate_config(self, config: Dict) -> None:
        """验证配置参数"""
        # 验证筛选标准
        if self.criteria.max_market_cap <= 0:
            raise ValueError("最大市值必须大于0")

        if self.criteria.max_price <= 0:
            raise ValueError("最大价格必须大于0")

        if self.criteria.min_volume_24h <= 0:
            raise ValueError("最小24小时成交量必须大于0")

        if not 0 <= self.criteria.max_concentration <= 1:
            raise ValueError("持币集中度必须在0-1之间")

        # 验证评分权重
        for weight_name, weight_value in self.score_weights.items():
            if not 0 <= weight_value <= 1:
                raise ValueError(f"权重 {weight_name} 必须在0-1之间")

    def get_rule_type(self) -> str:
        """获取规则类型"""
        return "potential_finder"

    def apply(self, market_data: List[MarketData], **kwargs) -> List[RuleResult]:
        """应用潜力挖掘规则"""
        if not self.is_enabled():
            self.logger.info("潜力挖掘器已禁用")
            return []

        self.logger.info(f"开始潜力挖掘，处理 {len(market_data)} 个交易对")

        results = []

        for data in market_data:
            try:
                # 基础筛选
                if not self._passes_basic_filter(data):
                    continue

                # 计算潜力评分
                score, details = self._calculate_potential_score(data)

                if score >= self.min_score:
                    reason = self._generate_reason(data, score, details)

                    result = RuleResult(
                        symbol=data.symbol,
                        score=score,
                        reason=reason,
                        rule_type=self.get_rule_type(),
                        timestamp=datetime.now(),
                        metadata={
                            "score_details": details,
                            "criteria_met": self._get_criteria_met(data),
                            "market_cap": data.market_cap,
                            "price": data.price,
                            "volume_24h": data.volume_24h,
                        },
                    )

                    results.append(result)

            except Exception as e:
                self.logger.error(f"处理交易对 {data.symbol} 时出错: {e}")
                continue

        # 按评分排序
        results.sort(key=lambda x: x.score, reverse=True)

        self.logger.info(f"潜力挖掘完成，发现 {len(results)} 个潜力币种")
        return results

    def _passes_basic_filter(self, data: MarketData) -> bool:
        """基础筛选条件"""
        # 检查必要数据
        if not all(
            [
                data.market_cap is not None,
                data.price is not None,
                data.volume_24h is not None,
            ]
        ):
            return False

        # 市值筛选
        if data.market_cap > self.criteria.max_market_cap:
            return False

        # 价格筛选
        if data.price > self.criteria.max_price:
            return False

        # 成交量筛选
        if data.volume_24h < self.criteria.min_volume_24h:
            return False

        return True

    def _calculate_potential_score(self, data: MarketData) -> Tuple[float, Dict]:
        """计算潜力评分"""
        details = {}

        # 1. 市值评分（越小越好）
        market_cap_score = self._calculate_market_cap_score(data.market_cap)
        details["market_cap_score"] = market_cap_score

        # 2. 价格评分（越小越好）
        price_score = self._calculate_price_score(data.price)
        details["price_score"] = price_score

        # 3. 成交量评分
        volume_score = self._calculate_volume_score(data)
        details["volume_score"] = volume_score

        # 4. 增长性评分
        growth_score = self._calculate_growth_score(data)
        details["growth_score"] = growth_score

        # 5. 基本面评分
        fundamentals_score = self._calculate_fundamentals_score(data)
        details["fundamentals_score"] = fundamentals_score

        # 加权计算总分
        total_score = (
            market_cap_score * self.score_weights["market_cap"]
            + price_score * self.score_weights["price"]
            + volume_score * self.score_weights["volume"]
            + growth_score * self.score_weights["growth"]
            + fundamentals_score * self.score_weights["fundamentals"]
        )

        details["total_score"] = total_score

        return total_score, details

    def _calculate_market_cap_score(self, market_cap: float) -> float:
        """计算市值评分（越小越好）"""
        if market_cap <= 1_000_000:  # 100万以下
            return 100.0
        elif market_cap <= 10_000_000:  # 1000万以下
            return 80.0
        elif market_cap <= 50_000_000:  # 5000万以下
            return 60.0
        elif market_cap <= 100_000_000:  # 1亿以下
            return 40.0
        else:
            return 20.0

    def _calculate_price_score(self, price: float) -> float:
        """计算价格评分（越小越好）"""
        if price <= 0.001:  # 0.001以下
            return 100.0
        elif price <= 0.01:  # 0.01以下
            return 80.0
        elif price <= 0.1:  # 0.1以下
            return 60.0
        elif price <= 1.0:  # 1.0以下
            return 40.0
        else:
            return 20.0

    def _calculate_volume_score(self, data: MarketData) -> float:
        """计算成交量评分"""
        volume_24h = data.volume_24h

        # 基础成交量评分
        if volume_24h >= 10_000_000:  # 1000万以上
            base_score = 100.0
        elif volume_24h >= 1_000_000:  # 100万以上
            base_score = 80.0
        elif volume_24h >= 500_000:  # 50万以上
            base_score = 60.0
        elif volume_24h >= 100_000:  # 10万以上
            base_score = 40.0
        else:
            base_score = 20.0

        # 成交量增长加分
        volume_growth = getattr(data, "volume_change_7d", 0)
        if volume_growth >= self.criteria.min_volume_growth_7d:
            growth_bonus = min(volume_growth * 50, 20)  # 最多加20分
            base_score += growth_bonus

        return min(base_score, 100.0)

    def _calculate_growth_score(self, data: MarketData) -> float:
        """计算增长性评分"""
        score = 0.0

        # 7日价格变化
        price_change_7d = getattr(data, "price_change_7d", 0)
        if price_change_7d >= 0.5:  # 50%以上
            score += 40.0
        elif price_change_7d >= 0.3:  # 30%以上
            score += 30.0
        elif price_change_7d >= self.criteria.min_price_change_7d:  # 10%以上
            score += 20.0

        # 30日价格变化
        price_change_30d = getattr(data, "price_change_30d", 0)
        if price_change_30d >= 1.0:  # 100%以上
            score += 30.0
        elif price_change_30d >= 0.5:  # 50%以上
            score += 20.0
        elif price_change_30d >= 0.2:  # 20%以上
            score += 10.0

        # 技术指标加分
        rsi = getattr(data, "rsi", 50)
        if 30 <= rsi <= 70:  # RSI在合理区间
            score += 15.0

        # 成交量趋势
        volume_trend = getattr(data, "volume_trend", 0)
        if volume_trend > 0:  # 成交量上升趋势
            score += 15.0

        return min(score, 100.0)

    def _calculate_fundamentals_score(self, data: MarketData) -> float:
        """计算基本面评分"""
        score = 50.0  # 基础分

        # 上市时间（新币种加分）
        listing_days = getattr(data, "listing_days", 365)
        if listing_days <= 30:  # 30天内
            score += 25.0
        elif listing_days <= 90:  # 90天内
            score += 15.0
        elif listing_days <= 180:  # 180天内
            score += 10.0

        # 持币地址数
        holders = getattr(data, "holders_count", 0)
        if holders >= self.criteria.min_holders:
            if holders >= 10000:
                score += 15.0
            elif holders >= 5000:
                score += 10.0
            else:
                score += 5.0

        # 持币集中度（越分散越好）
        concentration = getattr(data, "concentration", 0.5)
        if concentration <= 0.2:  # 20%以下
            score += 10.0
        elif concentration <= 0.3:  # 30%以下
            score += 5.0
        elif concentration > self.criteria.max_concentration:
            score -= 10.0  # 集中度过高扣分

        return min(score, 100.0)

    def _get_criteria_met(self, data: MarketData) -> List[str]:
        """获取满足的筛选条件"""
        criteria_met = []

        if data.market_cap <= self.criteria.max_market_cap:
            criteria_met.append(
                f"市值 {data.market_cap:,.0f} <= {self.criteria.max_market_cap:,.0f}"
            )

        if data.price <= self.criteria.max_price:
            criteria_met.append(f"价格 {data.price:.6f} <= {self.criteria.max_price}")

        if data.volume_24h >= self.criteria.min_volume_24h:
            criteria_met.append(
                f"24h成交量 {data.volume_24h:,.0f} >= {self.criteria.min_volume_24h:,.0f}"
            )

        price_change_7d = getattr(data, "price_change_7d", 0)
        if price_change_7d >= self.criteria.min_price_change_7d:
            criteria_met.append(
                f"7日涨幅 {price_change_7d:.1%} >= {self.criteria.min_price_change_7d:.1%}"
            )

        return criteria_met

    def _generate_reason(self, data: MarketData, score: float, details: Dict) -> str:
        """生成评分原因"""
        reasons = []

        # 主要优势
        if details["market_cap_score"] >= 80:
            reasons.append(f"低市值币种({data.market_cap:,.0f} USDT)")

        if details["price_score"] >= 80:
            reasons.append(f"低价格币种({data.price:.6f} USDT)")

        if details["growth_score"] >= 70:
            reasons.append("强劲增长趋势")

        if details["volume_score"] >= 70:
            reasons.append("活跃交易")

        if details["fundamentals_score"] >= 70:
            reasons.append("良好基本面")

        # 具体数据
        price_change_7d = getattr(data, "price_change_7d", 0)
        if price_change_7d > 0:
            reasons.append(f"7日涨幅{price_change_7d:.1%}")

        volume_growth = getattr(data, "volume_change_7d", 0)
        if volume_growth > 0:
            reasons.append(f"成交量增长{volume_growth:.1%}")

        reason_text = "、".join(reasons) if reasons else "综合评估"
        return f"潜力币种 (评分: {score:.1f}) - {reason_text}"
