# 结果聚合器
# 负责汇总和分析扫描结果，生成综合报告

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class AggregationPeriod(Enum):
    """聚合周期枚举"""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class TrendDirection(Enum):
    """趋势方向枚举"""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


@dataclass
class MarketSummary:
    """市场摘要"""

    timestamp: datetime
    total_symbols: int
    active_symbols: int
    top_gainers: List[Dict[str, Any]] = field(default_factory=list)
    top_losers: List[Dict[str, Any]] = field(default_factory=list)
    highest_volume: List[Dict[str, Any]] = field(default_factory=list)
    market_trend: TrendDirection = TrendDirection.NEUTRAL
    average_change: float = 0.0
    total_volume: float = 0.0
    volatility_index: float = 0.0


@dataclass
class OpportunityReport:
    """机会报告"""

    timestamp: datetime
    period: AggregationPeriod
    total_opportunities: int
    high_confidence_opportunities: int
    opportunities_by_category: Dict[str, int] = field(default_factory=dict)
    top_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    average_score: float = 0.0
    trend_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标"""

    timestamp: datetime
    scan_frequency: float  # 扫描频率（次/小时）
    average_scan_duration: float  # 平均扫描时长（秒）
    opportunity_discovery_rate: float  # 机会发现率（%）
    data_quality_score: float  # 数据质量分数
    system_uptime: float  # 系统运行时间（小时）
    error_rate: float  # 错误率（%）
    processing_efficiency: float  # 处理效率


class ResultAggregator:
    """结果聚合器 - 汇总和分析扫描结果"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # 聚合配置
        self.aggregation_config = config.get("aggregation", {})
        self.retention_config = config.get("retention", {})

        # 数据存储
        self.scan_results_history: List[Dict[str, Any]] = []
        self.market_summaries: List[MarketSummary] = []
        self.opportunity_reports: List[OpportunityReport] = []
        self.performance_metrics: List[PerformanceMetrics] = []

        # 统计信息
        self.stats = {
            "total_results_processed": 0,
            "total_opportunities_found": 0,
            "total_summaries_generated": 0,
            "last_aggregation_time": None,
            "data_retention_days": self.retention_config.get("days", 7),
        }

        logger.info("ResultAggregator initialized", config=config)

    def add_scan_results(self, scan_results: List[Dict[str, Any]]) -> None:
        """添加扫描结果

        Args:
            scan_results: 扫描结果列表
        """
        try:
            if not scan_results:
                return

            # 添加时间戳
            timestamp = datetime.now()
            for result in scan_results:
                result["aggregation_timestamp"] = timestamp

            # 存储结果
            self.scan_results_history.extend(scan_results)

            # 更新统计
            self.stats["total_results_processed"] += len(scan_results)
            self.stats["total_opportunities_found"] += len(
                [
                    r
                    for r in scan_results
                    if r.get("overall_score", 0)
                    >= self.config.get("opportunity_threshold", 0.6)
                ]
            )

            # 清理过期数据
            self._cleanup_old_data()

            logger.debug(
                "Scan results added",
                count=len(scan_results),
                total_stored=len(self.scan_results_history),
            )

        except Exception as e:
            logger.error("Error adding scan results", error=str(e))

    def generate_market_summary(
        self, period: AggregationPeriod = AggregationPeriod.HOUR
    ) -> Optional[MarketSummary]:
        """生成市场摘要

        Args:
            period: 聚合周期

        Returns:
            市场摘要或None
        """
        try:
            # 获取指定周期内的数据
            cutoff_time = self._get_cutoff_time(period)
            recent_results = [
                result
                for result in self.scan_results_history
                if result.get("aggregation_timestamp", datetime.min) >= cutoff_time
            ]

            if not recent_results:
                logger.warning("No recent results for market summary")
                return None

            # 按交易对分组
            symbols_data = self._group_by_symbol(recent_results)

            # 计算市场指标
            summary = MarketSummary(
                timestamp=datetime.now(),
                total_symbols=len(symbols_data),
                active_symbols=len(
                    [s for s in symbols_data.values() if s.get("volume", 0) > 0]
                ),
            )

            # 计算涨跌幅排行
            summary.top_gainers = self._get_top_performers(
                symbols_data, "change_percent_24h", True
            )[:10]
            summary.top_losers = self._get_top_performers(
                symbols_data, "change_percent_24h", False
            )[:10]

            # 计算成交量排行
            summary.highest_volume = self._get_top_performers(
                symbols_data, "volume_24h", True
            )[:10]

            # 计算市场趋势
            summary.market_trend = self._calculate_market_trend(symbols_data)

            # 计算平均变化和总成交量
            changes = [
                data.get("change_percent_24h", 0) for data in symbols_data.values()
            ]
            volumes = [data.get("volume_24h", 0) for data in symbols_data.values()]

            summary.average_change = statistics.mean(changes) if changes else 0.0
            summary.total_volume = sum(volumes)

            # 计算波动率指数
            summary.volatility_index = self._calculate_volatility_index(changes)

            # 存储摘要
            self.market_summaries.append(summary)
            self.stats["total_summaries_generated"] += 1
            self.stats["last_aggregation_time"] = datetime.now().isoformat()

            logger.info(
                "Market summary generated",
                period=period.value,
                total_symbols=summary.total_symbols,
                market_trend=summary.market_trend.value,
                average_change=summary.average_change,
            )

            return summary

        except Exception as e:
            logger.error("Error generating market summary", error=str(e))
            return None

    def generate_opportunity_report(
        self, period: AggregationPeriod = AggregationPeriod.HOUR
    ) -> Optional[OpportunityReport]:
        """生成机会报告

        Args:
            period: 聚合周期

        Returns:
            机会报告或None
        """
        try:
            # 获取指定周期内的机会
            cutoff_time = self._get_cutoff_time(period)
            opportunity_threshold = self.config.get("opportunity_threshold", 0.6)
            confidence_threshold = self.config.get("high_confidence_threshold", 0.8)

            opportunities = [
                result
                for result in self.scan_results_history
                if (
                    result.get("aggregation_timestamp", datetime.min) >= cutoff_time
                    and result.get("overall_score", 0) >= opportunity_threshold
                )
            ]

            if not opportunities:
                logger.info("No opportunities found for report")
                return OpportunityReport(
                    timestamp=datetime.now(),
                    period=period,
                    total_opportunities=0,
                    high_confidence_opportunities=0,
                )

            # 创建报告
            report = OpportunityReport(
                timestamp=datetime.now(),
                period=period,
                total_opportunities=len(opportunities),
                high_confidence_opportunities=len(
                    [
                        opp
                        for opp in opportunities
                        if opp.get("confidence", 0) >= confidence_threshold
                    ]
                ),
            )

            # 按类别分组
            report.opportunities_by_category = self._categorize_opportunities(
                opportunities
            )

            # 获取顶级机会
            report.top_opportunities = sorted(
                opportunities,
                key=lambda x: (x.get("overall_score", 0), x.get("confidence", 0)),
                reverse=True,
            )[:20]

            # 计算成功率（需要历史数据支持）
            report.success_rate = self._calculate_success_rate(opportunities)

            # 计算平均分数
            scores = [opp.get("overall_score", 0) for opp in opportunities]
            report.average_score = statistics.mean(scores) if scores else 0.0

            # 趋势分析
            report.trend_analysis = self._analyze_opportunity_trends(
                opportunities, period
            )

            # 存储报告
            self.opportunity_reports.append(report)

            logger.info(
                "Opportunity report generated",
                period=period.value,
                total_opportunities=report.total_opportunities,
                high_confidence=report.high_confidence_opportunities,
                average_score=report.average_score,
            )

            return report

        except Exception as e:
            logger.error("Error generating opportunity report", error=str(e))
            return None

    def generate_performance_metrics(
        self, period: AggregationPeriod = AggregationPeriod.HOUR
    ) -> Optional[PerformanceMetrics]:
        """生成性能指标

        Args:
            period: 聚合周期

        Returns:
            性能指标或None
        """
        try:
            cutoff_time = self._get_cutoff_time(period)
            recent_results = [
                result
                for result in self.scan_results_history
                if result.get("aggregation_timestamp", datetime.min) >= cutoff_time
            ]

            # 计算时间范围
            time_range_hours = self._get_period_hours(period)

            # 计算指标
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                scan_frequency=len(recent_results) / time_range_hours
                if time_range_hours > 0
                else 0,
                average_scan_duration=self._calculate_average_scan_duration(
                    recent_results
                ),
                opportunity_discovery_rate=self._calculate_discovery_rate(
                    recent_results
                ),
                data_quality_score=self._calculate_data_quality_score(recent_results),
                system_uptime=time_range_hours,  # 简化计算
                error_rate=self._calculate_error_rate(recent_results),
                processing_efficiency=self._calculate_processing_efficiency(
                    recent_results
                ),
            )

            # 存储指标
            self.performance_metrics.append(metrics)

            logger.info(
                "Performance metrics generated",
                period=period.value,
                scan_frequency=metrics.scan_frequency,
                discovery_rate=metrics.opportunity_discovery_rate,
                data_quality=metrics.data_quality_score,
            )

            return metrics

        except Exception as e:
            logger.error("Error generating performance metrics", error=str(e))
            return None

    def get_trend_analysis(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """获取特定交易对的趋势分析

        Args:
            symbol: 交易对符号
            days: 分析天数

        Returns:
            趋势分析结果
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            symbol_results = [
                result
                for result in self.scan_results_history
                if (
                    result.get("symbol") == symbol
                    and result.get("aggregation_timestamp", datetime.min) >= cutoff_time
                )
            ]

            if not symbol_results:
                return {"error": "No data available for symbol"}

            # 按时间排序
            symbol_results.sort(
                key=lambda x: x.get("aggregation_timestamp", datetime.min)
            )

            # 计算趋势指标
            scores = [r.get("overall_score", 0) for r in symbol_results]
            prices = [r.get("price", 0) for r in symbol_results if r.get("price")]
            volumes = [
                r.get("volume_24h", 0) for r in symbol_results if r.get("volume_24h")
            ]

            analysis = {
                "symbol": symbol,
                "period_days": days,
                "data_points": len(symbol_results),
                "score_trend": self._calculate_trend(scores),
                "price_trend": self._calculate_trend(prices) if prices else None,
                "volume_trend": self._calculate_trend(volumes) if volumes else None,
                "average_score": statistics.mean(scores) if scores else 0,
                "score_volatility": statistics.stdev(scores) if len(scores) > 1 else 0,
                "recent_performance": {
                    "last_score": scores[-1] if scores else 0,
                    "last_price": prices[-1] if prices else 0,
                    "score_change": scores[-1] - scores[0] if len(scores) > 1 else 0,
                },
                "recommendations": self._generate_symbol_recommendations(
                    symbol_results
                ),
            }

            return analysis

        except Exception as e:
            logger.error("Error in trend analysis", symbol=symbol, error=str(e))
            return {"error": str(e)}

    def _group_by_symbol(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """按交易对分组结果"""
        grouped = {}

        for result in results:
            symbol = result.get("symbol")
            if not symbol:
                continue

            if symbol not in grouped:
                grouped[symbol] = result.copy()
            else:
                # 使用最新的数据
                if result.get("timestamp", datetime.min) > grouped[symbol].get(
                    "timestamp", datetime.min
                ):
                    grouped[symbol] = result.copy()

        return grouped

    def _get_top_performers(
        self,
        symbols_data: Dict[str, Dict[str, Any]],
        metric: str,
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """获取表现最佳的交易对"""
        try:
            performers = []

            for symbol, data in symbols_data.items():
                value = data.get(metric, 0)
                if value is not None:
                    performers.append(
                        {
                            "symbol": symbol,
                            "value": value,
                            "price": data.get("price", 0),
                            "volume_24h": data.get("volume_24h", 0),
                            "overall_score": data.get("overall_score", 0),
                        }
                    )

            # 排序
            performers.sort(key=lambda x: x["value"], reverse=not ascending)

            return performers

        except Exception as e:
            logger.error("Error getting top performers", metric=metric, error=str(e))
            return []

    def _calculate_market_trend(
        self, symbols_data: Dict[str, Dict[str, Any]]
    ) -> TrendDirection:
        """计算市场趋势"""
        try:
            changes = [
                data.get("change_percent_24h", 0) for data in symbols_data.values()
            ]

            if not changes:
                return TrendDirection.NEUTRAL

            positive_count = len([c for c in changes if c > 0])
            total_count = len(changes)

            positive_ratio = positive_count / total_count
            average_change = statistics.mean(changes)
            volatility = statistics.stdev(changes) if len(changes) > 1 else 0

            # 判断趋势
            if volatility > 10:  # 高波动
                return TrendDirection.VOLATILE
            elif positive_ratio > 0.6 and average_change > 2:
                return TrendDirection.BULLISH
            elif positive_ratio < 0.4 and average_change < -2:
                return TrendDirection.BEARISH
            else:
                return TrendDirection.NEUTRAL

        except Exception as e:
            logger.error("Error calculating market trend", error=str(e))
            return TrendDirection.NEUTRAL

    def _calculate_volatility_index(self, changes: List[float]) -> float:
        """计算波动率指数"""
        try:
            if len(changes) < 2:
                return 0.0

            # 使用标准差作为波动率指标
            volatility = statistics.stdev(changes)

            # 标准化到0-100范围
            normalized_volatility = min(volatility * 2, 100)

            return round(normalized_volatility, 2)

        except Exception:
            return 0.0

    def _categorize_opportunities(
        self, opportunities: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """按类别分组机会"""
        categories = {}

        for opp in opportunities:
            recommendation = opp.get("recommendation", "UNKNOWN")
            categories[recommendation] = categories.get(recommendation, 0) + 1

            # 按分数范围分类
            score = opp.get("overall_score", 0)
            if score >= 0.9:
                categories["EXCELLENT"] = categories.get("EXCELLENT", 0) + 1
            elif score >= 0.8:
                categories["VERY_GOOD"] = categories.get("VERY_GOOD", 0) + 1
            elif score >= 0.7:
                categories["GOOD"] = categories.get("GOOD", 0) + 1
            else:
                categories["MODERATE"] = categories.get("MODERATE", 0) + 1

        return categories

    def _calculate_success_rate(self, opportunities: List[Dict[str, Any]]) -> float:
        """计算成功率（简化实现）"""
        # 这里需要实际的交易结果数据来计算真实的成功率
        # 目前返回基于置信度的估算值
        try:
            if not opportunities:
                return 0.0

            confidences = [opp.get("confidence", 0) for opp in opportunities]
            average_confidence = statistics.mean(confidences)

            # 简化的成功率估算
            estimated_success_rate = average_confidence * 0.8  # 保守估计

            return round(estimated_success_rate, 3)

        except Exception:
            return 0.0

    def _analyze_opportunity_trends(
        self, opportunities: List[Dict[str, Any]], period: AggregationPeriod
    ) -> Dict[str, Any]:
        """分析机会趋势"""
        try:
            # 按时间分组
            time_groups = self._group_by_time(opportunities, period)

            # 计算趋势
            counts = [len(group) for group in time_groups.values()]
            scores = []

            for group in time_groups.values():
                if group:
                    group_scores = [opp.get("overall_score", 0) for opp in group]
                    scores.append(statistics.mean(group_scores))
                else:
                    scores.append(0)

            return {
                "opportunity_count_trend": self._calculate_trend(counts),
                "average_score_trend": self._calculate_trend(scores),
                "peak_period": max(
                    time_groups.keys(), key=lambda k: len(time_groups[k])
                )
                if time_groups
                else None,
                "total_periods": len(time_groups),
                "consistency_score": 1
                - (statistics.stdev(counts) / statistics.mean(counts))
                if counts and statistics.mean(counts) > 0
                else 0,
            }

        except Exception as e:
            logger.error("Error analyzing opportunity trends", error=str(e))
            return {}

    def _group_by_time(
        self, opportunities: List[Dict[str, Any]], period: AggregationPeriod
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按时间分组机会"""
        groups = {}

        for opp in opportunities:
            timestamp = opp.get("aggregation_timestamp", datetime.now())

            # 根据周期确定分组键
            if period == AggregationPeriod.MINUTE:
                key = timestamp.strftime("%Y-%m-%d %H:%M")
            elif period == AggregationPeriod.HOUR:
                key = timestamp.strftime("%Y-%m-%d %H")
            elif period == AggregationPeriod.DAY:
                key = timestamp.strftime("%Y-%m-%d")
            else:  # WEEK
                key = f"{timestamp.year}-W{timestamp.isocalendar()[1]}"

            if key not in groups:
                groups[key] = []
            groups[key].append(opp)

        return groups

    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势方向"""
        if len(values) < 2:
            return "insufficient_data"

        try:
            # 简单的线性趋势计算
            x = list(range(len(values)))
            n = len(values)

            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(xi * xi for xi in x)

            # 计算斜率
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

            if slope > 0.1:
                return "increasing"
            elif slope < -0.1:
                return "decreasing"
            else:
                return "stable"

        except Exception:
            return "unknown"

    def _calculate_average_scan_duration(self, results: List[Dict[str, Any]]) -> float:
        """计算平均扫描时长"""
        # 这里需要实际的扫描时长数据
        # 目前返回估算值
        return 5.0  # 假设平均5秒

    def _calculate_discovery_rate(self, results: List[Dict[str, Any]]) -> float:
        """计算机会发现率"""
        if not results:
            return 0.0

        opportunity_threshold = self.config.get("opportunity_threshold", 0.6)
        opportunities = [
            r for r in results if r.get("overall_score", 0) >= opportunity_threshold
        ]

        return (len(opportunities) / len(results)) * 100

    def _calculate_data_quality_score(self, results: List[Dict[str, Any]]) -> float:
        """计算数据质量分数"""
        if not results:
            return 0.0

        # 基于验证结果计算质量分数
        quality_scores = []

        for result in results:
            validation_result = result.get("validation_result")
            if validation_result:
                quality = validation_result.get("quality", "fair")
                if quality == "excellent":
                    quality_scores.append(1.0)
                elif quality == "good":
                    quality_scores.append(0.8)
                elif quality == "fair":
                    quality_scores.append(0.6)
                elif quality == "poor":
                    quality_scores.append(0.4)
                else:
                    quality_scores.append(0.2)
            else:
                quality_scores.append(0.7)  # 默认分数

        return statistics.mean(quality_scores) * 100 if quality_scores else 70.0

    def _calculate_error_rate(self, results: List[Dict[str, Any]]) -> float:
        """计算错误率"""
        if not results:
            return 0.0

        error_count = len(
            [r for r in results if r.get("error") or r.get("validation_failed")]
        )
        return (error_count / len(results)) * 100

    def _calculate_processing_efficiency(self, results: List[Dict[str, Any]]) -> float:
        """计算处理效率"""
        if not results:
            return 0.0

        # 基于数据完整性和处理速度的综合指标
        complete_results = len([r for r in results if self._is_complete_result(r)])
        completeness_ratio = complete_results / len(results)

        # 简化的效率计算
        return completeness_ratio * 100

    def _is_complete_result(self, result: Dict[str, Any]) -> bool:
        """检查结果是否完整"""
        required_fields = ["symbol", "overall_score", "confidence", "recommendation"]
        return all(
            field in result and result[field] is not None for field in required_fields
        )

    def _generate_symbol_recommendations(
        self, symbol_results: List[Dict[str, Any]]
    ) -> List[str]:
        """生成交易对推荐"""
        recommendations = []

        if not symbol_results:
            return recommendations

        # 获取最新结果
        latest_result = max(
            symbol_results, key=lambda x: x.get("timestamp", datetime.min)
        )
        latest_score = latest_result.get("overall_score", 0)
        latest_confidence = latest_result.get("confidence", 0)

        # 计算趋势
        scores = [r.get("overall_score", 0) for r in symbol_results]
        score_trend = self._calculate_trend(scores)

        # 生成推荐
        if latest_score >= 0.8 and latest_confidence >= 0.7:
            if score_trend == "increasing":
                recommendations.append("Strong upward momentum - Consider buying")
            else:
                recommendations.append("High score but stable trend - Monitor closely")
        elif latest_score >= 0.6:
            if score_trend == "increasing":
                recommendations.append("Improving trend - Potential opportunity")
            else:
                recommendations.append("Moderate score - Wait for better entry")
        else:
            if score_trend == "decreasing":
                recommendations.append("Declining trend - Avoid or consider shorting")
            else:
                recommendations.append("Low score - Not recommended")

        return recommendations

    def _get_cutoff_time(self, period: AggregationPeriod) -> datetime:
        """获取周期截止时间"""
        now = datetime.now()

        if period == AggregationPeriod.MINUTE:
            return now - timedelta(minutes=1)
        elif period == AggregationPeriod.HOUR:
            return now - timedelta(hours=1)
        elif period == AggregationPeriod.DAY:
            return now - timedelta(days=1)
        else:  # WEEK
            return now - timedelta(weeks=1)

    def _get_period_hours(self, period: AggregationPeriod) -> float:
        """获取周期小时数"""
        if period == AggregationPeriod.MINUTE:
            return 1 / 60
        elif period == AggregationPeriod.HOUR:
            return 1
        elif period == AggregationPeriod.DAY:
            return 24
        else:  # WEEK
            return 168

    def _cleanup_old_data(self) -> None:
        """清理过期数据"""
        try:
            retention_days = self.stats["data_retention_days"]
            cutoff_time = datetime.now() - timedelta(days=retention_days)

            # 清理扫描结果
            original_count = len(self.scan_results_history)
            self.scan_results_history = [
                result
                for result in self.scan_results_history
                if result.get("aggregation_timestamp", datetime.now()) >= cutoff_time
            ]

            # 清理摘要和报告
            self.market_summaries = [
                summary
                for summary in self.market_summaries
                if summary.timestamp >= cutoff_time
            ]

            self.opportunity_reports = [
                report
                for report in self.opportunity_reports
                if report.timestamp >= cutoff_time
            ]

            self.performance_metrics = [
                metrics
                for metrics in self.performance_metrics
                if metrics.timestamp >= cutoff_time
            ]

            cleaned_count = original_count - len(self.scan_results_history)
            if cleaned_count > 0:
                logger.info("Old data cleaned up", cleaned_records=cleaned_count)

        except Exception as e:
            logger.error("Error cleaning up old data", error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        stats.update(
            {
                "current_data_points": len(self.scan_results_history),
                "market_summaries_count": len(self.market_summaries),
                "opportunity_reports_count": len(self.opportunity_reports),
                "performance_metrics_count": len(self.performance_metrics),
            }
        )
        return stats

    def export_data(self, format_type: str = "json") -> Dict[str, Any]:
        """导出聚合数据

        Args:
            format_type: 导出格式

        Returns:
            导出的数据
        """
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "format": format_type,
                "stats": self.get_stats(),
                "market_summaries": [
                    summary.__dict__ for summary in self.market_summaries[-10:]
                ],
                "opportunity_reports": [
                    report.__dict__ for report in self.opportunity_reports[-10:]
                ],
                "performance_metrics": [
                    metrics.__dict__ for metrics in self.performance_metrics[-10:]
                ],
            }

            logger.info("Data exported", format=format_type)
            return export_data

        except Exception as e:
            logger.error("Error exporting data", error=str(e))
            return {"error": str(e)}
