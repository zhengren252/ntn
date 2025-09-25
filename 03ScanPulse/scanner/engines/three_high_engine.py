# 三高规则引擎
# 实现高波动、高流动性、高相关性筛选逻辑

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from ..communication.redis_client import RedisClient
from ..utils.logger import get_logger


@dataclass
class ThreeHighResult:
    """三高分析结果"""

    triggered: bool
    score: float
    volatility_score: float
    volume_score: float
    correlation_score: float
    details: Dict[str, Any]
    timestamp: str


class ThreeHighEngine:
    """三高规则引擎

    实现高波动、高流动性、高相关性的市场筛选逻辑
    """

    def __init__(self, redis_client: RedisClient, config: Dict[str, Any]):
        self.redis_client = redis_client
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        # 配置参数
        self.volatility_threshold = config.get("volatility_threshold", 0.05)
        self.volume_threshold = config.get("volume_threshold", 1000000)
        self.correlation_threshold = config.get("correlation_threshold", 0.7)
        self.min_score = config.get("min_score", 0.6)
        self.lookback_period = config.get("lookback_period", 24)  # 小时

        # 权重配置
        self.weights = {
            "volatility": config.get("volatility_weight", 0.4),
            "volume": config.get("volume_weight", 0.3),
            "correlation": config.get("correlation_weight", 0.3),
        }

        self.logger.info(
            f"三高引擎初始化完成，阈值: 波动率={self.volatility_threshold}, "
            f"成交量={self.volume_threshold}, 相关性={self.correlation_threshold}"
        )

    async def analyze(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> ThreeHighResult:
        """分析交易对是否符合三高规则

        Args:
            symbol: 交易对符号
            market_data: 市场数据

        Returns:
            ThreeHighResult: 分析结果
        """
        try:
            self.logger.debug(f"开始分析交易对 {symbol} 的三高指标")

            # 计算各项指标
            volatility_score = await self._calculate_volatility_score(
                symbol, market_data
            )
            volume_score = await self._calculate_volume_score(symbol, market_data)
            correlation_score = await self._calculate_correlation_score(
                symbol, market_data
            )

            # 计算综合得分
            total_score = (
                volatility_score * self.weights["volatility"]
                + volume_score * self.weights["volume"]
                + correlation_score * self.weights["correlation"]
            )

            # 判断是否触发
            triggered = (
                volatility_score >= self.volatility_threshold
                and volume_score >= self.volume_threshold
                and correlation_score >= self.correlation_threshold
                and total_score >= self.min_score
            )

            # 构建详细信息
            details = {
                "symbol": symbol,
                "price": market_data.get("price", 0),
                "volume_24h": market_data.get("volume", 0),
                "change_24h": market_data.get("change_24h", 0),
                "market_cap": market_data.get("market_cap", 0),
                "technical_indicators": market_data.get("technical_indicators", {}),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "thresholds": {
                    "volatility": self.volatility_threshold,
                    "volume": self.volume_threshold,
                    "correlation": self.correlation_threshold,
                    "min_score": self.min_score,
                },
                "weights": self.weights,
            }

            result = ThreeHighResult(
                triggered=triggered,
                score=total_score,
                volatility_score=volatility_score,
                volume_score=volume_score,
                correlation_score=correlation_score,
                details=details,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # 记录结果
            if triggered:
                self.logger.info(
                    f"三高规则触发: {symbol}, 得分={total_score:.3f}, "
                    f"波动={volatility_score:.3f}, 成交量={volume_score:.3f}, "
                    f"相关性={correlation_score:.3f}"
                )
            else:
                self.logger.debug(f"三高规则未触发: {symbol}, 得分={total_score:.3f}")

            # 存储分析结果
            await self._store_analysis_result(symbol, result)

            return result

        except Exception as e:
            self.logger.error(f"分析交易对 {symbol} 时发生错误: {e}")
            return ThreeHighResult(
                triggered=False,
                score=0.0,
                volatility_score=0.0,
                volume_score=0.0,
                correlation_score=0.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def _calculate_volatility_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算波动率得分"""
        try:
            # 从技术指标中获取波动率
            technical_indicators = market_data.get("technical_indicators", {})
            current_volatility = technical_indicators.get("volatility", 0)

            if current_volatility == 0:
                # 如果没有技术指标，使用价格变化计算简单波动率
                change_24h = abs(market_data.get("change_24h", 0))
                current_volatility = change_24h

            # 获取历史波动率数据
            historical_data = await self.redis_client.get_historical_data(
                symbol, hours=self.lookback_period
            )

            if historical_data:
                # 计算历史波动率统计
                volatilities = [data.get("volatility", 0) for data in historical_data]
                volatilities = [v for v in volatilities if v > 0]  # 过滤无效数据

                if volatilities:
                    avg_volatility = np.mean(volatilities)
                    std_volatility = np.std(volatilities)

                    # 计算Z-score
                    if std_volatility > 0:
                        z_score = (current_volatility - avg_volatility) / std_volatility
                        # 将Z-score转换为0-1分数
                        volatility_score = min(max((z_score + 2) / 4, 0), 1)
                    else:
                        volatility_score = (
                            current_volatility / self.volatility_threshold
                        )
                else:
                    volatility_score = current_volatility / self.volatility_threshold
            else:
                # 没有历史数据时，直接与阈值比较
                volatility_score = current_volatility / self.volatility_threshold

            return min(volatility_score, 1.0)

        except Exception as e:
            self.logger.error(f"计算波动率得分时发生错误: {e}")
            return 0.0

    async def _calculate_volume_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算成交量得分"""
        try:
            current_volume = market_data.get("volume", 0)

            # 获取历史成交量数据
            historical_data = await self.redis_client.get_historical_data(
                symbol, hours=self.lookback_period
            )

            if historical_data:
                # 计算历史成交量统计
                volumes = [data.get("volume", 0) for data in historical_data]
                volumes = [v for v in volumes if v > 0]  # 过滤无效数据

                if volumes:
                    avg_volume = np.mean(volumes)

                    # 计算成交量倍数
                    if avg_volume > 0:
                        volume_multiplier = current_volume / avg_volume
                        # 将倍数转换为0-1分数
                        volume_score = min(volume_multiplier / 3, 1.0)
                    else:
                        volume_score = current_volume / self.volume_threshold
                else:
                    volume_score = current_volume / self.volume_threshold
            else:
                # 没有历史数据时，直接与阈值比较
                volume_score = current_volume / self.volume_threshold

            return min(volume_score, 1.0)

        except Exception as e:
            self.logger.error(f"计算成交量得分时发生错误: {e}")
            return 0.0

    async def _calculate_correlation_score(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> float:
        """计算市场相关性得分"""
        try:
            # 获取市场概览数据
            market_overview = await self.redis_client.get_market_overview()

            if not market_overview:
                self.logger.warning("无法获取市场概览数据，使用默认相关性得分")
                return 0.5

            # 获取主要市场指标
            btc_data = await self._get_reference_data("BTCUSDT")
            eth_data = await self._get_reference_data("ETHUSDT")

            if not btc_data and not eth_data:
                self.logger.warning("无法获取参考数据，使用默认相关性得分")
                return 0.5

            # 计算与主要币种的相关性
            correlations = []

            current_change = market_data.get("change_24h", 0)

            if btc_data:
                btc_change = btc_data.get("change_24h", 0)
                btc_correlation = self._calculate_price_correlation(
                    current_change, btc_change
                )
                correlations.append(btc_correlation)

            if eth_data:
                eth_change = eth_data.get("change_24h", 0)
                eth_correlation = self._calculate_price_correlation(
                    current_change, eth_change
                )
                correlations.append(eth_correlation)

            if correlations:
                # 使用最高相关性
                max_correlation = max(correlations)
                correlation_score = max_correlation
            else:
                correlation_score = 0.5

            return min(correlation_score, 1.0)

        except Exception as e:
            self.logger.error(f"计算相关性得分时发生错误: {e}")
            return 0.0

    def _calculate_price_correlation(self, change1: float, change2: float) -> float:
        """计算价格变化相关性"""
        try:
            # 简单的相关性计算：同向变化得分更高
            if change1 * change2 > 0:  # 同向
                # 计算变化幅度的相似性
                if change1 != 0 and change2 != 0:
                    ratio = min(abs(change1), abs(change2)) / max(
                        abs(change1), abs(change2)
                    )
                    correlation = 0.5 + 0.5 * ratio
                else:
                    correlation = 0.5
            else:  # 反向
                correlation = 0.3

            return correlation

        except Exception as e:
            self.logger.error(f"计算价格相关性时发生错误: {e}")
            return 0.0

    async def _get_reference_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取参考交易对数据"""
        try:
            # 从Redis获取最新数据
            data = await self.redis_client.get_scan_result(symbol)
            return data
        except Exception as e:
            self.logger.error(f"获取参考数据 {symbol} 时发生错误: {e}")
            return None

    async def _store_analysis_result(self, symbol: str, result: ThreeHighResult):
        """存储分析结果"""
        try:
            result_data = {
                "engine": "three_high",
                "symbol": symbol,
                "triggered": result.triggered,
                "score": result.score,
                "volatility_score": result.volatility_score,
                "volume_score": result.volume_score,
                "correlation_score": result.correlation_score,
                "details": result.details,
                "timestamp": result.timestamp,
            }

            # 存储到Redis
            await self.redis_client.set_scan_result(f"three_high_{symbol}", result_data)

            # 如果触发，存储到触发列表
            if result.triggered:
                await self.redis_client.add_to_triggered_list(
                    "three_high", symbol, result_data
                )

        except Exception as e:
            self.logger.error(f"存储分析结果时发生错误: {e}")

    async def get_triggered_symbols(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取触发三高规则的交易对列表"""
        try:
            return await self.redis_client.get_triggered_list("three_high", limit)
        except Exception as e:
            self.logger.error(f"获取触发列表时发生错误: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        try:
            stats = {
                "engine": "three_high",
                "config": self.config,
                "thresholds": {
                    "volatility": self.volatility_threshold,
                    "volume": self.volume_threshold,
                    "correlation": self.correlation_threshold,
                    "min_score": self.min_score,
                },
                "weights": self.weights,
                "lookback_period": self.lookback_period,
            }

            # 获取触发统计
            triggered_count = len(await self.get_triggered_symbols())
            stats["triggered_count"] = triggered_count

            return stats

        except Exception as e:
            self.logger.error(f"获取统计信息时发生错误: {e}")
            return {}

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        try:
            self.config.update(new_config)

            # 更新阈值
            self.volatility_threshold = self.config.get(
                "volatility_threshold", self.volatility_threshold
            )
            self.volume_threshold = self.config.get(
                "volume_threshold", self.volume_threshold
            )
            self.correlation_threshold = self.config.get(
                "correlation_threshold", self.correlation_threshold
            )
            self.min_score = self.config.get("min_score", self.min_score)

            # 更新权重
            if "volatility_weight" in new_config:
                self.weights["volatility"] = new_config["volatility_weight"]
            if "volume_weight" in new_config:
                self.weights["volume"] = new_config["volume_weight"]
            if "correlation_weight" in new_config:
                self.weights["correlation"] = new_config["correlation_weight"]

            self.logger.info(f"三高引擎配置已更新: {new_config}")

        except Exception as e:
            self.logger.error(f"更新配置时发生错误: {e}")
