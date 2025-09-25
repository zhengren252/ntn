# 扫描器主模块
# 实现市场扫描和机会识别的核心逻辑

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

from ..adapters import AdapterManager
from ..communication import CommunicationManager
from ..config import EnvironmentManager
from ..rules import RuleEngine, RuleResult

logger = structlog.get_logger(__name__)


class ScannerStatus(Enum):
    """扫描器状态枚举"""

    IDLE = "idle"
    SCANNING = "scanning"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ScanResult:
    """扫描结果数据类"""

    symbol: str
    timestamp: datetime
    rule_results: List[RuleResult]
    market_data: Dict[str, Any]
    news_events: List[Dict[str, Any]]
    overall_score: float
    confidence: float
    recommendation: str
    metadata: Dict[str, Any]


class ScannerModule:
    """扫描器主模块 - 核心扫描逻辑实现"""

    def __init__(
        self,
        config_manager: EnvironmentManager,
        adapter_manager: AdapterManager,
        communication_manager: CommunicationManager,
    ):
        self.config_manager = config_manager
        self.adapter_manager = adapter_manager
        self.communication_manager = communication_manager

        # 获取扫描器配置
        self.config = config_manager.get_config("scanner")

        # 初始化规则引擎
        self.rule_engine = RuleEngine(config_manager.get_config("rules"))

        # 扫描器状态
        self.status = ScannerStatus.IDLE
        self.is_running = False
        self.scan_task = None

        # 扫描配置
        self.scan_interval = self.config.get("scan_interval", 60)  # 秒
        self.batch_size = self.config.get("batch_size", 10)
        self.max_concurrent_scans = self.config.get("max_concurrent_scans", 5)

        # 统计信息
        self.stats = {
            "total_scans": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "opportunities_found": 0,
            "last_scan_time": None,
            "scan_duration_avg": 0.0,
            "uptime": None,
        }

        # 回调函数
        self.callbacks = {
            "on_scan_start": [],
            "on_scan_complete": [],
            "on_opportunity_found": [],
            "on_error": [],
        }

        logger.info("ScannerModule initialized", config=self.config)

    def add_callback(self, event: str, callback: Callable) -> None:
        """添加回调函数

        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
            logger.debug("Callback added", event=event)
        else:
            logger.warning("Unknown callback event", event=event)

    def start(self) -> bool:
        """启动扫描器

        Returns:
            是否启动成功
        """
        try:
            if self.is_running:
                logger.warning("Scanner is already running")
                return True

            # 检查依赖组件
            if not self._check_dependencies():
                logger.error("Dependencies check failed")
                return False

            # 启动扫描任务
            self.is_running = True
            self.status = ScannerStatus.SCANNING
            self.stats["uptime"] = datetime.now()

            # 创建异步扫描任务
            self.scan_task = asyncio.create_task(self._scan_loop())

            logger.info("Scanner started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start scanner", error=str(e))
            self.status = ScannerStatus.ERROR
            return False

    def stop(self) -> None:
        """停止扫描器"""
        try:
            if not self.is_running:
                logger.warning("Scanner is not running")
                return

            self.is_running = False
            self.status = ScannerStatus.STOPPED

            # 取消扫描任务
            if self.scan_task and not self.scan_task.done():
                self.scan_task.cancel()

            logger.info("Scanner stopped")

        except Exception as e:
            logger.error("Error stopping scanner", error=str(e))

    def pause(self) -> None:
        """暂停扫描器"""
        if self.status == ScannerStatus.SCANNING:
            self.status = ScannerStatus.PAUSED
            logger.info("Scanner paused")
        else:
            logger.warning("Scanner is not in scanning state", status=self.status.value)

    def resume(self) -> None:
        """恢复扫描器"""
        if self.status == ScannerStatus.PAUSED:
            self.status = ScannerStatus.SCANNING
            logger.info("Scanner resumed")
        else:
            logger.warning("Scanner is not in paused state", status=self.status.value)

    async def _scan_loop(self) -> None:
        """主扫描循环"""
        logger.info("Scanner loop started")

        while self.is_running:
            try:
                # 检查是否暂停
                if self.status == ScannerStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue

                # 执行扫描
                await self._execute_scan_cycle()

                # 等待下一次扫描
                await asyncio.sleep(self.scan_interval)

            except asyncio.CancelledError:
                logger.info("Scanner loop cancelled")
                break
            except Exception as e:
                logger.error("Error in scanner loop", error=str(e))
                self.status = ScannerStatus.ERROR
                self._trigger_callbacks("on_error", {"error": str(e)})

                # 错误恢复等待
                await asyncio.sleep(min(self.scan_interval, 30))
                self.status = ScannerStatus.SCANNING

        logger.info("Scanner loop ended")

    async def _execute_scan_cycle(self) -> None:
        """执行一次完整的扫描周期"""
        scan_start_time = datetime.now()

        try:
            # 触发扫描开始回调
            self._trigger_callbacks("on_scan_start", {"timestamp": scan_start_time})

            # 获取要扫描的交易对列表
            symbols = await self._get_scan_symbols()
            if not symbols:
                logger.warning("No symbols to scan")
                return

            logger.info("Starting scan cycle", symbols_count=len(symbols))

            # 批量扫描
            scan_results = []
            for i in range(0, len(symbols), self.batch_size):
                batch = symbols[i : i + self.batch_size]
                batch_results = await self._scan_batch(batch)
                scan_results.extend(batch_results)

            # 处理扫描结果
            opportunities = self._process_scan_results(scan_results)

            # 发布结果
            await self._publish_results(opportunities)

            # 更新统计信息
            scan_duration = (datetime.now() - scan_start_time).total_seconds()
            self._update_stats(scan_duration, len(opportunities))

            # 触发扫描完成回调
            self._trigger_callbacks(
                "on_scan_complete",
                {
                    "timestamp": datetime.now(),
                    "duration": scan_duration,
                    "symbols_scanned": len(symbols),
                    "opportunities_found": len(opportunities),
                },
            )

            logger.info(
                "Scan cycle completed",
                duration=scan_duration,
                symbols_scanned=len(symbols),
                opportunities_found=len(opportunities),
            )

        except Exception as e:
            logger.error("Error in scan cycle", error=str(e))
            self.stats["failed_scans"] += 1
            raise

    async def _get_scan_symbols(self) -> List[str]:
        """获取要扫描的交易对列表

        Returns:
            交易对符号列表
        """
        try:
            # 从TradingAgents适配器获取交易对列表
            trading_agents = self.adapter_manager.get_trading_agents_adapter()
            if trading_agents and trading_agents.is_connected():
                symbols = await asyncio.to_thread(trading_agents.get_symbols)
                if symbols:
                    # 过滤和排序
                    filtered_symbols = self._filter_symbols(symbols)
                    logger.debug(
                        "Symbols retrieved",
                        total=len(symbols),
                        filtered=len(filtered_symbols),
                    )
                    return filtered_symbols

            # Fallback到配置中的默认交易对
            default_symbols = self.config.get("default_symbols", [])
            logger.warning("Using default symbols", count=len(default_symbols))
            return default_symbols

        except Exception as e:
            logger.error("Error getting scan symbols", error=str(e))
            return []

    def _filter_symbols(self, symbols: List[str]) -> List[str]:
        """过滤交易对符号

        Args:
            symbols: 原始交易对列表

        Returns:
            过滤后的交易对列表
        """
        try:
            # 获取过滤配置
            filter_config = self.config.get("symbol_filter", {})

            # 包含列表
            include_patterns = filter_config.get("include", [])
            # 排除列表
            exclude_patterns = filter_config.get("exclude", [])
            # 最大数量
            max_symbols = filter_config.get("max_symbols", 100)

            filtered = []

            for symbol in symbols:
                # 检查排除模式
                if any(pattern in symbol for pattern in exclude_patterns):
                    continue

                # 检查包含模式（如果有的话）
                if include_patterns and not any(
                    pattern in symbol for pattern in include_patterns
                ):
                    continue

                filtered.append(symbol)

                # 检查最大数量限制
                if len(filtered) >= max_symbols:
                    break

            return filtered

        except Exception as e:
            logger.error("Error filtering symbols", error=str(e))
            return symbols[:100]  # 返回前100个作为fallback

    async def _scan_batch(self, symbols: List[str]) -> List[ScanResult]:
        """扫描一批交易对

        Args:
            symbols: 交易对符号列表

        Returns:
            扫描结果列表
        """
        try:
            # 创建并发任务
            semaphore = asyncio.Semaphore(self.max_concurrent_scans)
            tasks = [self._scan_symbol(symbol, semaphore) for symbol in symbols]

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤有效结果
            valid_results = []
            for result in results:
                if isinstance(result, ScanResult):
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    logger.warning("Scan task failed", error=str(result))

            return valid_results

        except Exception as e:
            logger.error("Error scanning batch", symbols=symbols, error=str(e))
            return []

    async def _scan_symbol(
        self, symbol: str, semaphore: asyncio.Semaphore
    ) -> Optional[ScanResult]:
        """扫描单个交易对

        Args:
            symbol: 交易对符号
            semaphore: 并发控制信号量

        Returns:
            扫描结果或None
        """
        async with semaphore:
            try:
                # 获取市场数据
                market_data = await asyncio.to_thread(
                    self.adapter_manager.get_market_data, symbol
                )

                if not market_data:
                    logger.debug("No market data available", symbol=symbol)
                    return None

                # 获取相关新闻事件
                news_events = await asyncio.to_thread(
                    self.adapter_manager.get_news_events, [symbol], 10, 24
                )

                # 执行规则引擎分析
                rule_results = await asyncio.to_thread(
                    self.rule_engine.evaluate_all, symbol, market_data, news_events
                )

                # 计算综合评分
                overall_score, confidence = self._calculate_overall_score(rule_results)

                # 生成推荐
                recommendation = self._generate_recommendation(
                    overall_score, confidence
                )

                # 创建扫描结果
                scan_result = ScanResult(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    rule_results=rule_results,
                    market_data=market_data,
                    news_events=news_events,
                    overall_score=overall_score,
                    confidence=confidence,
                    recommendation=recommendation,
                    metadata={
                        "scan_version": "1.0.0",
                        "rules_count": len(rule_results),
                        "news_count": len(news_events),
                    },
                )

                logger.debug(
                    "Symbol scanned",
                    symbol=symbol,
                    score=overall_score,
                    confidence=confidence,
                    recommendation=recommendation,
                )

                return scan_result

            except Exception as e:
                logger.error("Error scanning symbol", symbol=symbol, error=str(e))
                return None

    def _calculate_overall_score(
        self, rule_results: List[RuleResult]
    ) -> tuple[float, float]:
        """计算综合评分和置信度

        Args:
            rule_results: 规则结果列表

        Returns:
            (综合评分, 置信度)
        """
        if not rule_results:
            return 0.0, 0.0

        # 加权平均评分
        total_weight = sum(result.weight for result in rule_results)
        if total_weight == 0:
            return 0.0, 0.0

        weighted_score = (
            sum(result.score * result.weight for result in rule_results) / total_weight
        )

        # 置信度基于规则数量和一致性
        confidence = min(len(rule_results) / 5.0, 1.0)  # 最多5个规则达到满置信度

        # 考虑规则结果的一致性
        scores = [result.score for result in rule_results]
        if len(scores) > 1:
            score_variance = sum((s - weighted_score) ** 2 for s in scores) / len(
                scores
            )
            consistency_factor = max(0, 1 - score_variance)
            confidence *= consistency_factor

        return round(weighted_score, 4), round(confidence, 4)

    def _generate_recommendation(self, score: float, confidence: float) -> str:
        """生成交易推荐

        Args:
            score: 综合评分
            confidence: 置信度

        Returns:
            推荐字符串
        """
        # 获取推荐阈值配置
        thresholds = self.config.get(
            "recommendation_thresholds",
            {"strong_buy": 0.8, "buy": 0.6, "hold": 0.4, "sell": 0.2},
        )

        min_confidence = self.config.get("min_confidence", 0.5)

        # 如果置信度太低，返回观望
        if confidence < min_confidence:
            return "WATCH"

        # 根据评分生成推荐
        if score >= thresholds["strong_buy"]:
            return "STRONG_BUY"
        elif score >= thresholds["buy"]:
            return "BUY"
        elif score >= thresholds["hold"]:
            return "HOLD"
        elif score >= thresholds["sell"]:
            return "SELL"
        else:
            return "STRONG_SELL"

    def _process_scan_results(self, scan_results: List[ScanResult]) -> List[ScanResult]:
        """处理扫描结果，筛选出交易机会

        Args:
            scan_results: 扫描结果列表

        Returns:
            筛选后的交易机会列表
        """
        try:
            # 获取筛选配置
            filter_config = self.config.get("opportunity_filter", {})
            min_score = filter_config.get("min_score", 0.6)
            min_confidence = filter_config.get("min_confidence", 0.5)
            max_opportunities = filter_config.get("max_opportunities", 20)

            # 筛选机会
            opportunities = [
                result
                for result in scan_results
                if result.overall_score >= min_score
                and result.confidence >= min_confidence
            ]

            # 按评分排序
            opportunities.sort(
                key=lambda x: (x.overall_score, x.confidence), reverse=True
            )

            # 限制数量
            opportunities = opportunities[:max_opportunities]

            logger.info(
                "Opportunities filtered",
                total_scanned=len(scan_results),
                opportunities_found=len(opportunities),
            )

            return opportunities

        except Exception as e:
            logger.error("Error processing scan results", error=str(e))
            return []

    async def _publish_results(self, opportunities: List[ScanResult]) -> None:
        """发布扫描结果

        Args:
            opportunities: 交易机会列表
        """
        try:
            if not opportunities:
                return

            # 发布到ZeroMQ
            for opportunity in opportunities:
                await asyncio.to_thread(
                    self.communication_manager.publish_scan_result, opportunity.__dict__
                )

                # 缓存到Redis
                await asyncio.to_thread(
                    self.communication_manager.cache_scan_result,
                    opportunity.symbol,
                    opportunity.__dict__,
                )

                # 触发机会发现回调
                self._trigger_callbacks("on_opportunity_found", opportunity.__dict__)

            # 批量发布摘要
            summary = {
                "timestamp": datetime.now().isoformat(),
                "opportunities_count": len(opportunities),
                "top_opportunities": [
                    {
                        "symbol": opp.symbol,
                        "score": opp.overall_score,
                        "confidence": opp.confidence,
                        "recommendation": opp.recommendation,
                    }
                    for opp in opportunities[:5]
                ],
            }

            await asyncio.to_thread(
                self.communication_manager.publish_scan_summary, summary
            )

            logger.info("Results published", opportunities_count=len(opportunities))

        except Exception as e:
            logger.error("Error publishing results", error=str(e))

    def _trigger_callbacks(self, event: str, data: Any) -> None:
        """触发回调函数

        Args:
            event: 事件名称
            data: 事件数据
        """
        try:
            for callback in self.callbacks.get(event, []):
                try:
                    callback(data)
                except Exception as e:
                    logger.error("Callback execution failed", event=event, error=str(e))
        except Exception as e:
            logger.error("Error triggering callbacks", event=event, error=str(e))

    def _update_stats(self, scan_duration: float, opportunities_count: int) -> None:
        """更新统计信息

        Args:
            scan_duration: 扫描耗时
            opportunities_count: 发现的机会数量
        """
        self.stats["total_scans"] += 1
        self.stats["successful_scans"] += 1
        self.stats["opportunities_found"] += opportunities_count
        self.stats["last_scan_time"] = datetime.now().isoformat()

        # 更新平均扫描时间
        current_avg = self.stats["scan_duration_avg"]
        total_scans = self.stats["successful_scans"]
        self.stats["scan_duration_avg"] = (
            current_avg * (total_scans - 1) + scan_duration
        ) / total_scans

    def _check_dependencies(self) -> bool:
        """检查依赖组件状态

        Returns:
            是否所有依赖都正常
        """
        try:
            # 检查适配器管理器
            if not self.adapter_manager:
                logger.error("AdapterManager not available")
                return False

            # 检查通信管理器
            if not self.communication_manager:
                logger.error("CommunicationManager not available")
                return False

            # 检查规则引擎
            if not self.rule_engine:
                logger.error("RuleEngine not available")
                return False

            # 执行健康检查
            adapter_health = self.adapter_manager.health_check()
            if adapter_health["overall_status"] == "unhealthy":
                logger.warning("Some adapters are unhealthy", health=adapter_health)
                # 不阻止启动，但记录警告

            return True

        except Exception as e:
            logger.error("Dependencies check failed", error=str(e))
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取扫描器状态

        Returns:
            状态信息字典
        """
        return {
            "status": self.status.value,
            "is_running": self.is_running,
            "config": self.config,
            "stats": self.stats.copy(),
            "uptime_seconds": (
                (datetime.now() - self.stats["uptime"]).total_seconds()
                if self.stats["uptime"]
                else 0
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return self.stats.copy()
