# 三高规则引擎
# 实现高波动、高流动性、高相关性的筛选逻辑

import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from .base import BaseRule, MarketData, RuleResult, RuleValidator


class ThreeHighRules(BaseRule):
    """三高规则：高波动、高流动性、高相关性"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 提取配置参数
        self.volatility_threshold = config.get("volatility_threshold", 0.05)
        self.volume_threshold = config.get("volume_threshold", 1000000)
        self.correlation_threshold = config.get("correlation_threshold", 0.8)

        # 权重配置
        self.weight_volatility = config.get("weight_volatility", 0.4)
        self.weight_volume = config.get("weight_volume", 0.3)
        self.weight_correlation = config.get("weight_correlation", 0.3)

        # 验证权重总和
        total_weight = (
            self.weight_volatility + self.weight_volume + self.weight_correlation
        )
        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(
                "Weight sum is not 1.0, normalizing", total_weight=total_weight
            )
            # 归一化权重
            self.weight_volatility /= total_weight
            self.weight_volume /= total_weight
            self.weight_correlation /= total_weight

    def _validate_config(self) -> None:
        """验证配置参数"""
        required_fields = [
            "volatility_threshold",
            "volume_threshold",
            "correlation_threshold",
        ]

        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")

        # 验证阈值范围
        if not 0 < self.config["volatility_threshold"] < 1:
            raise ValueError("volatility_threshold must be between 0 and 1")

        if self.config["volume_threshold"] <= 0:
            raise ValueError("volume_threshold must be positive")

        if not 0 < self.config["correlation_threshold"] <= 1:
            raise ValueError("correlation_threshold must be between 0 and 1")

    def get_rule_type(self) -> str:
        """获取规则类型"""
        return "three_high"

    def apply(self, market_data: List[MarketData], **kwargs) -> List[RuleResult]:
        """应用三高规则

        Args:
            market_data: 市场数据列表
            **kwargs: 其他参数

        Returns:
            符合三高规则的结果列表
        """
        start_time = time.time()
        results = []

        if not market_data:
            self.logger.warning("No market data provided for three_high rules")
            return results

        # 验证和过滤数据
        valid_data = [
            data for data in market_data if RuleValidator.validate_market_data(data)
        ]

        if len(valid_data) < len(market_data):
            self.logger.warning(
                "Some market data failed validation",
                total_count=len(market_data),
                valid_count=len(valid_data),
            )

        # 计算市场基准指标
        market_metrics = self._calculate_market_metrics(valid_data)

        # 应用三高规则
        for data in valid_data:
            try:
                result = self._evaluate_symbol(data, market_metrics)
                if result and result.score >= self.get_min_score():
                    results.append(result)
            except Exception as e:
                self.logger.error(
                    "Error evaluating symbol", symbol=data.symbol, error=str(e)
                )

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        execution_time = time.time() - start_time
        self.log_rule_execution(len(valid_data), len(results), execution_time)

        return results

    def _calculate_market_metrics(
        self, market_data: List[MarketData]
    ) -> Dict[str, float]:
        """计算市场基准指标"""
        if not market_data:
            return {"avg_volatility": 0, "avg_volume": 0, "total_market_cap": 0}

        volatilities = [data.volatility_24h for data in market_data]
        volumes = [data.volume_24h for data in market_data]
        market_caps = [data.market_cap for data in market_data if data.market_cap]

        return {
            "avg_volatility": np.mean(volatilities) if volatilities else 0,
            "median_volatility": np.median(volatilities) if volatilities else 0,
            "avg_volume": np.mean(volumes) if volumes else 0,
            "median_volume": np.median(volumes) if volumes else 0,
            "total_market_cap": sum(market_caps) if market_caps else 0,
            "avg_market_cap": np.mean(market_caps) if market_caps else 0,
        }

    def _evaluate_symbol(
        self, data: MarketData, market_metrics: Dict[str, float]
    ) -> RuleResult:
        """评估单个交易对"""
        # 计算各项指标分数
        volatility_score = self._calculate_volatility_score(data, market_metrics)
        volume_score = self._calculate_volume_score(data, market_metrics)
        correlation_score = self._calculate_correlation_score(data, market_metrics)

        # 计算综合分数
        total_score = (
            volatility_score * self.weight_volatility
            + volume_score * self.weight_volume
            + correlation_score * self.weight_correlation
        )

        # 计算置信度
        confidence = self.calculate_confidence(total_score)

        # 生成原因说明
        reason = self._generate_reason(
            volatility_score, volume_score, correlation_score
        )

        # 详细信息
        details = {
            "volatility_24h": data.volatility_24h,
            "volume_24h": data.volume_24h,
            "market_cap": data.market_cap,
            "price_change_24h": data.price_change_24h,
            "scores": {
                "volatility": round(volatility_score, 2),
                "volume": round(volume_score, 2),
                "correlation": round(correlation_score, 2),
            },
            "weights": {
                "volatility": self.weight_volatility,
                "volume": self.weight_volume,
                "correlation": self.weight_correlation,
            },
            "thresholds": {
                "volatility_threshold": self.volatility_threshold,
                "volume_threshold": self.volume_threshold,
                "correlation_threshold": self.correlation_threshold,
            },
        }

        return RuleResult(
            symbol=data.symbol,
            rule_type=self.get_rule_type(),
            score=round(total_score, 2),
            confidence=round(confidence, 3),
            reason=reason,
            details=details,
            timestamp=datetime.now(),
        )

    def _calculate_volatility_score(
        self, data: MarketData, market_metrics: Dict[str, float]
    ) -> float:
        """计算波动率分数"""
        volatility = data.volatility_24h

        # 基础分数：是否超过阈值
        if volatility < self.volatility_threshold:
            return 0.0

        # 相对市场平均的表现
        avg_volatility = market_metrics.get("avg_volatility", 0)
        if avg_volatility > 0:
            relative_volatility = volatility / avg_volatility
        else:
            relative_volatility = 1.0

        # 分数计算：基础分50分，相对表现最多加50分
        base_score = 50.0
        relative_score = min(relative_volatility * 25, 50.0)  # 最多50分

        return base_score + relative_score

    def _calculate_volume_score(
        self, data: MarketData, market_metrics: Dict[str, float]
    ) -> float:
        """计算成交量分数"""
        volume = data.volume_24h

        # 基础分数：是否超过阈值
        if volume < self.volume_threshold:
            return 0.0

        # 相对市场平均的表现
        avg_volume = market_metrics.get("avg_volume", 0)
        if avg_volume > 0:
            relative_volume = volume / avg_volume
        else:
            relative_volume = 1.0

        # 分数计算：基础分50分，相对表现最多加50分
        base_score = 50.0
        relative_score = min(relative_volume * 25, 50.0)  # 最多50分

        return base_score + relative_score

    def _calculate_correlation_score(
        self, data: MarketData, market_metrics: Dict[str, float]
    ) -> float:
        """计算相关性分数

        注：这里简化实现，实际应该计算与主流币种的价格相关性
        目前基于市值和交易量的综合表现来评估
        """
        # 简化的相关性评估：基于市值占比和交易活跃度
        market_cap = data.market_cap or 0
        volume = data.volume_24h

        total_market_cap = market_metrics.get("total_market_cap", 0)
        avg_volume = market_metrics.get("avg_volume", 0)

        # 市值占比分数
        if total_market_cap > 0:
            market_cap_ratio = market_cap / total_market_cap
            market_cap_score = min(market_cap_ratio * 1000, 50.0)  # 归一化到50分
        else:
            market_cap_score = 25.0  # 默认分数

        # 交易活跃度分数
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            volume_activity_score = min(volume_ratio * 25, 50.0)  # 归一化到50分
        else:
            volume_activity_score = 25.0  # 默认分数

        # 综合相关性分数
        correlation_score = (market_cap_score + volume_activity_score) / 2

        # 应用相关性阈值
        normalized_correlation = correlation_score / 100.0  # 转换为0-1范围
        if normalized_correlation < self.correlation_threshold:
            return 0.0

        return correlation_score

    def _generate_reason(
        self, volatility_score: float, volume_score: float, correlation_score: float
    ) -> str:
        """生成评分原因"""
        reasons = []

        if volatility_score > 70:
            reasons.append("高波动率")
        elif volatility_score > 50:
            reasons.append("中等波动率")

        if volume_score > 70:
            reasons.append("高成交量")
        elif volume_score > 50:
            reasons.append("中等成交量")

        if correlation_score > 70:
            reasons.append("强市场相关性")
        elif correlation_score > 50:
            reasons.append("中等市场相关性")

        if not reasons:
            return "符合基础三高标准"

        return "、".join(reasons) + "表现突出"
