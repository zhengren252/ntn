# -*- coding: utf-8 -*-
"""
数据验证器模块

实现数据验证功能，包括市场数据验证、策略参数验证、回测结果验证等，
确保数据质量和系统稳定性。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd


@dataclass
class ValidationReport:
    """
    验证报告数据类
    """

    is_valid: bool
    quality_score: float
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    timestamp: str


class DataValidator:
    """
    数据验证器

    提供市场数据、策略参数、回测结果等各类数据的验证功能
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化数据验证器

        Args:
            config: 验证配置
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # 验证阈值配置
        self.thresholds = {
            "min_data_points": self.config.get("min_data_points", 100),
            "max_missing_ratio": self.config.get("max_missing_ratio", 0.05),
            "min_quality_score": self.config.get("min_quality_score", 0.7),
            "max_outlier_ratio": self.config.get("max_outlier_ratio", 0.1),
            "min_price_variance": self.config.get("min_price_variance", 1e-6),
        }

        # 策略参数验证规则
        self.strategy_param_rules = {
            "ma_cross": {
                "short_window": {"type": int, "min": 1, "max": 100},
                "long_window": {"type": int, "min": 2, "max": 500},
                "signal_threshold": {"type": float, "min": 0.0, "max": 1.0},
            },
            "rsi": {
                "period": {"type": int, "min": 2, "max": 100},
                "overbought": {"type": float, "min": 50, "max": 100},
                "oversold": {"type": float, "min": 0, "max": 50},
            },
            "bollinger_bands": {
                "period": {"type": int, "min": 2, "max": 100},
                "std_dev": {"type": float, "min": 0.5, "max": 5.0},
            },
        }

    async def validate_market_data(
        self, market_data: Dict[str, Any]
    ) -> ValidationReport:
        """
        验证市场数据

        Args:
            market_data: 市场数据字典，包含prices, volumes, timestamps等

        Returns:
            ValidationReport: 验证报告
        """
        errors = []
        warnings = []
        metrics = {}

        try:
            # 检查必需字段
            required_fields = ["prices", "volumes", "timestamps"]
            for field in required_fields:
                if field not in market_data:
                    errors.append(f"缺少必需字段: {field}")

            if errors:
                return ValidationReport(
                    is_valid=False,
                    quality_score=0.0,
                    errors=errors,
                    warnings=warnings,
                    metrics=metrics,
                    timestamp=datetime.now().isoformat(),
                )

            # 转换为numpy数组进行验证
            prices = np.array(market_data["prices"])
            volumes = np.array(market_data["volumes"])
            timestamps = market_data["timestamps"]

            # 数据点数量检查
            data_points = len(prices)
            metrics["data_points"] = data_points

            if data_points < self.thresholds["min_data_points"]:
                warnings.append(
                    f"数据点数量不足: {data_points} < {self.thresholds['min_data_points']}"
                )

            # 缺失值检查
            missing_prices = np.isnan(prices).sum()
            missing_volumes = np.isnan(volumes).sum()
            missing_ratio = (missing_prices + missing_volumes) / (2 * data_points)

            metrics["missing_ratio"] = missing_ratio

            if missing_ratio > self.thresholds["max_missing_ratio"]:
                errors.append(
                    f"缺失值比例过高: {missing_ratio:.3f} > {self.thresholds['max_missing_ratio']}"
                )

            # 价格数据质量检查
            if len(prices) > 0:
                # 检查负价格
                negative_prices = (prices <= 0).sum()
                if negative_prices > 0:
                    errors.append(f"发现 {negative_prices} 个非正价格")

                # 检查价格方差
                price_variance = np.var(prices[~np.isnan(prices)])
                metrics["price_variance"] = price_variance

                if price_variance < self.thresholds["min_price_variance"]:
                    warnings.append(f"价格方差过小: {price_variance:.6f}")

                # 检查异常值
                valid_prices = prices[~np.isnan(prices)]
                if len(valid_prices) > 0:
                    q1, q3 = np.percentile(valid_prices, [25, 75])
                    iqr = q3 - q1
                    outlier_threshold_low = q1 - 1.5 * iqr
                    outlier_threshold_high = q3 + 1.5 * iqr

                    outliers = (
                        (valid_prices < outlier_threshold_low)
                        | (valid_prices > outlier_threshold_high)
                    ).sum()
                    outlier_ratio = outliers / len(valid_prices)

                    metrics["outlier_ratio"] = outlier_ratio

                    if outlier_ratio > self.thresholds["max_outlier_ratio"]:
                        warnings.append(f"异常值比例过高: {outlier_ratio:.3f}")

            # 成交量数据质量检查
            if len(volumes) > 0:
                negative_volumes = (volumes < 0).sum()
                if negative_volumes > 0:
                    errors.append(f"发现 {negative_volumes} 个负成交量")

            # 时间戳连续性检查
            if len(timestamps) > 1:
                try:
                    # 尝试解析时间戳
                    parsed_timestamps = [
                        datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if isinstance(ts, str)
                        else ts
                        for ts in timestamps
                    ]

                    # 检查时间顺序
                    time_diffs = []
                    for i in range(1, len(parsed_timestamps)):
                        diff = (
                            parsed_timestamps[i] - parsed_timestamps[i - 1]
                        ).total_seconds()
                        time_diffs.append(diff)

                    if any(diff <= 0 for diff in time_diffs):
                        errors.append("时间戳顺序错误")

                    # 检查时间间隔一致性
                    if len(time_diffs) > 0:
                        avg_interval = np.mean(time_diffs)
                        interval_std = np.std(time_diffs)
                        metrics["avg_time_interval"] = avg_interval
                        metrics["time_interval_std"] = interval_std

                        if interval_std > avg_interval * 0.5:  # 标准差超过平均值的50%
                            warnings.append("时间间隔不一致")

                except Exception as e:
                    errors.append(f"时间戳解析错误: {str(e)}")

            # 计算质量分数
            quality_score = self._calculate_quality_score(metrics, errors, warnings)

            is_valid = (
                len(errors) == 0
                and quality_score >= self.thresholds["min_quality_score"]
            )

            return ValidationReport(
                is_valid=is_valid,
                quality_score=quality_score,
                errors=errors,
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error("市场数据验证失败: %s", e)
            return ValidationReport(
                is_valid=False,
                quality_score=0.0,
                errors=[f"验证过程异常: {str(e)}"],
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

    async def validate_strategy_parameters(
        self, strategy_type: str, parameters: Dict[str, Any]
    ) -> ValidationReport:
        """
        验证策略参数

        Args:
            strategy_type: 策略类型
            parameters: 策略参数字典

        Returns:
            ValidationReport: 验证报告
        """
        errors = []
        warnings = []
        metrics = {}

        try:
            # 检查策略类型是否支持
            if strategy_type not in self.strategy_param_rules:
                errors.append(f"不支持的策略类型: {strategy_type}")
                return ValidationReport(
                    is_valid=False,
                    quality_score=0.0,
                    errors=errors,
                    warnings=warnings,
                    metrics=metrics,
                    timestamp=datetime.now().isoformat(),
                )

            rules = self.strategy_param_rules[strategy_type]

            # 检查必需参数
            for param_name, rule in rules.items():
                if param_name not in parameters:
                    errors.append(f"缺少必需参数: {param_name}")
                    continue

                value = parameters[param_name]

                # 类型检查
                expected_type = rule["type"]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"参数 {param_name} 类型错误: "
                        f"期望 {expected_type.__name__}, "
                        f"实际 {type(value).__name__}"
                    )
                    continue

                # 范围检查
                if "min" in rule and value < rule["min"]:
                    errors.append(f"参数 {param_name} 值过小: {value} < {rule['min']}")

                if "max" in rule and value > rule["max"]:
                    errors.append(f"参数 {param_name} 值过大: {value} > {rule['max']}")

            # 策略特定的逻辑检查
            if strategy_type == "ma_cross":
                if "short_window" in parameters and "long_window" in parameters:
                    if parameters["short_window"] >= parameters["long_window"]:
                        errors.append("短期窗口必须小于长期窗口")

            elif strategy_type == "rsi":
                if "overbought" in parameters and "oversold" in parameters:
                    if parameters["oversold"] >= parameters["overbought"]:
                        errors.append("超卖阈值必须小于超买阈值")

            # 记录参数统计
            metrics["parameter_count"] = len(parameters)
            metrics["strategy_type"] = strategy_type

            # 计算质量分数
            quality_score = (
                1.0 if len(errors) == 0 else 0.5 if len(warnings) == 0 else 0.0
            )

            is_valid = len(errors) == 0

            return ValidationReport(
                is_valid=is_valid,
                quality_score=quality_score,
                errors=errors,
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"策略参数验证失败: {e}")
            return ValidationReport(
                is_valid=False,
                quality_score=0.0,
                errors=[f"验证过程异常: {str(e)}"],
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

    async def validate_backtest_results(
        self, results: Dict[str, Any]
    ) -> ValidationReport:
        """
        验证回测结果

        Args:
            results: 回测结果字典

        Returns:
            ValidationReport: 验证报告
        """
        errors = []
        warnings = []
        metrics = {}

        try:
            # 检查必需字段
            required_fields = ["returns", "positions", "trades"]
            for field in required_fields:
                if field not in results:
                    errors.append(f"缺少必需字段: {field}")

            if errors:
                return ValidationReport(
                    is_valid=False,
                    quality_score=0.0,
                    errors=errors,
                    warnings=warnings,
                    metrics=metrics,
                    timestamp=datetime.now().isoformat(),
                )

            # 验证收益率数据
            returns = results.get("returns", [])
            if isinstance(returns, list) and len(returns) > 0:
                returns_array = np.array(returns)

                # 检查异常收益率
                extreme_returns = np.abs(returns_array) > 0.5  # 50%以上的单日收益率
                if extreme_returns.any():
                    warnings.append(f"发现 {extreme_returns.sum()} 个极端收益率")

                # 计算基本统计指标
                metrics["total_return"] = np.sum(returns_array)
                metrics["volatility"] = np.std(returns_array)
                metrics["sharpe_ratio"] = (
                    np.mean(returns_array) / np.std(returns_array)
                    if np.std(returns_array) > 0
                    else 0
                )

            # 验证交易数据
            trades = results.get("trades", [])
            if isinstance(trades, list):
                metrics["trade_count"] = len(trades)

                if len(trades) == 0:
                    warnings.append("没有交易记录")
                elif len(trades) < 10:
                    warnings.append("交易次数过少，可能影响统计显著性")

            # 验证仓位数据
            positions = results.get("positions", [])
            if isinstance(positions, list):
                metrics["position_count"] = len(positions)

            # 计算质量分数
            quality_score = self._calculate_quality_score(metrics, errors, warnings)

            is_valid = len(errors) == 0

            return ValidationReport(
                is_valid=is_valid,
                quality_score=quality_score,
                errors=errors,
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"回测结果验证失败: {e}")
            return ValidationReport(
                is_valid=False,
                quality_score=0.0,
                errors=[f"验证过程异常: {str(e)}"],
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

    def _calculate_quality_score(
        self, metrics: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> float:
        """
        计算数据质量分数

        Args:
            metrics: 指标字典
            errors: 错误列表
            warnings: 警告列表

        Returns:
            float: 质量分数 (0.0 - 1.0)
        """
        if len(errors) > 0:
            return 0.0

        base_score = 1.0

        # 根据警告数量扣分
        warning_penalty = min(0.1 * len(warnings), 0.5)
        base_score -= warning_penalty

        # 根据具体指标调整分数
        if "missing_ratio" in metrics:
            missing_ratio = metrics["missing_ratio"]
            if missing_ratio > 0:
                base_score -= min(missing_ratio * 2, 0.3)

        if "outlier_ratio" in metrics:
            outlier_ratio = metrics["outlier_ratio"]
            if outlier_ratio > self.thresholds["max_outlier_ratio"]:
                base_score -= min(
                    (outlier_ratio - self.thresholds["max_outlier_ratio"]) * 2, 0.2
                )

        return max(0.0, min(1.0, base_score))

    async def validate_portfolio_data(
        self, portfolio: Dict[str, Any]
    ) -> ValidationReport:
        """
        验证投资组合数据

        Args:
            portfolio: 投资组合数据

        Returns:
            ValidationReport: 验证报告
        """
        errors = []
        warnings = []
        metrics = {}

        try:
            # 检查必需字段
            required_fields = ["positions", "total_value", "cash"]
            for field in required_fields:
                if field not in portfolio:
                    errors.append(f"缺少必需字段: {field}")

            if "positions" in portfolio:
                positions = portfolio["positions"]
                if isinstance(positions, dict):
                    # 检查仓位权重
                    total_weight = sum(
                        pos.get("weight", 0) for pos in positions.values()
                    )
                    metrics["total_weight"] = total_weight

                    if abs(total_weight - 1.0) > 0.01:  # 允许1%的误差
                        warnings.append(f"仓位权重总和异常: {total_weight:.3f}")

                    # 检查单个仓位大小
                    max_position = max(
                        (pos.get("weight", 0) for pos in positions.values()), default=0
                    )
                    metrics["max_position_weight"] = max_position

                    if max_position > 0.5:  # 单个仓位超过50%
                        warnings.append(f"单个仓位过大: {max_position:.3f}")

            quality_score = self._calculate_quality_score(metrics, errors, warnings)
            is_valid = len(errors) == 0

            return ValidationReport(
                is_valid=is_valid,
                quality_score=quality_score,
                errors=errors,
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"投资组合数据验证失败: {e}")
            return ValidationReport(
                is_valid=False,
                quality_score=0.0,
                errors=[f"验证过程异常: {str(e)}"],
                warnings=warnings,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
            )
