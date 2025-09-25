# 适配器管理器
# 统一管理所有适配器，实现系统级集成流程

from datetime import datetime
from typing import Any, Dict, List, Optional, Type

import structlog

from .api_factory_adapter import APIFactoryAdapter
from .base_adapter import AdapterConfig, AdapterStatus, BaseAdapter
from .trading_agents_cn_adapter import TACoreServiceAgent, TACoreServiceClient

logger = structlog.get_logger(__name__)


class AdapterManager:
    """适配器管理器 - 统一管理所有外部系统适配器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.adapters: Dict[str, BaseAdapter] = {}
        self.is_initialized = False

        # 适配器类型映射
        self.adapter_types: Dict[str, Type[BaseAdapter]] = {
            "api_factory": APIFactoryAdapter,
        }

        # TACoreService客户端
        self.tacore_client: Optional[TACoreServiceClient] = None
        self.tacore_agent: Optional[TACoreServiceAgent] = None

        # 统计信息
        self.stats = {
            "total_adapters": 0,
            "connected_adapters": 0,
            "failed_adapters": 0,
            "initialization_time": None,
        }

        logger.info("AdapterManager initialized")

    def initialize(self) -> bool:
        """初始化所有适配器

        Returns:
            是否初始化成功
        """
        try:
            if self.is_initialized:
                logger.warning("AdapterManager already initialized")
                return True

            start_time = datetime.now()

            # 初始化各个适配器
            adapters_config = self.config.get("adapters", {})

            for adapter_name, adapter_config in adapters_config.items():
                if not self._initialize_adapter(adapter_name, adapter_config):
                    logger.error(
                        "Failed to initialize adapter", adapter_name=adapter_name
                    )
                    # 继续初始化其他适配器，不因为一个失败而停止

            self.is_initialized = True
            self.stats["initialization_time"] = (
                datetime.now() - start_time
            ).total_seconds()
            self._update_stats()

            logger.info(
                "AdapterManager initialization completed",
                total_adapters=self.stats["total_adapters"],
                connected_adapters=self.stats["connected_adapters"],
                failed_adapters=self.stats["failed_adapters"],
            )

            return True

        except Exception as e:
            logger.error("Failed to initialize AdapterManager", error=str(e))
            return False

    def _initialize_adapter(
        self, adapter_name: str, adapter_config: Dict[str, Any]
    ) -> bool:
        """初始化单个适配器

        Args:
            adapter_name: 适配器名称
            adapter_config: 适配器配置

        Returns:
            是否初始化成功
        """
        try:
            # 获取适配器类型
            adapter_type = adapter_config.get("type")
            if not adapter_type or adapter_type not in self.adapter_types:
                logger.error(
                    "Unknown adapter type",
                    adapter_name=adapter_name,
                    adapter_type=adapter_type,
                    available_types=list(self.adapter_types.keys()),
                )
                return False

            # 创建适配器配置
            config = AdapterConfig(
                name=adapter_name,
                enabled=adapter_config.get("enabled", True),
                timeout=adapter_config.get("timeout", 30),
                retry_count=adapter_config.get("retry_count", 3),
                retry_delay=adapter_config.get("retry_delay", 1.0),
                mock_mode=adapter_config.get("mock_mode", False),
                config=adapter_config.get("config", {}),
            )

            # 创建适配器实例
            adapter_class = self.adapter_types[adapter_type]
            adapter = adapter_class(config)

            # 连接适配器
            if config.enabled:
                if adapter.connect():
                    logger.info(
                        "Adapter connected successfully", adapter_name=adapter_name
                    )
                else:
                    logger.warning(
                        "Adapter connection failed", adapter_name=adapter_name
                    )
            else:
                logger.info(
                    "Adapter disabled, skipping connection", adapter_name=adapter_name
                )

            # 注册适配器
            self.adapters[adapter_name] = adapter

            return True

        except Exception as e:
            logger.error(
                "Failed to initialize adapter", adapter_name=adapter_name, error=str(e)
            )
            return False

    def get_adapter(self, adapter_name: str) -> Optional[BaseAdapter]:
        """获取指定适配器

        Args:
            adapter_name: 适配器名称

        Returns:
            适配器实例或None
        """
        return self.adapters.get(adapter_name)

    def get_trading_agents_adapter(self) -> Optional[TACoreServiceAgent]:
        """获取TradingAgents适配器（现在使用TACoreService）

        Returns:
            TACoreService代理或None
        """
        if not self.tacore_agent:
            # 初始化TACoreService客户端和代理
            tacore_config = self.config.get("tacore_service", {})
            if tacore_config.get("enabled", False):
                self.tacore_client = TACoreServiceClient(
                    server_address=tacore_config.get(
                        "server_address", "tcp://localhost:5555"
                    ),
                    timeout=tacore_config.get("timeout", 15000),
                    retry_attempts=tacore_config.get("retry_attempts", 3),
                    retry_delay=tacore_config.get("retry_delay", 1000),
                )
                self.tacore_agent = TACoreServiceAgent(self.tacore_client)
                logger.info("TACoreService agent initialized")

        return self.tacore_agent

    def get_api_factory_adapter(self) -> Optional[APIFactoryAdapter]:
        """获取API工厂适配器

        Returns:
            API工厂适配器或None
        """
        adapter = self.get_adapter("api_factory")
        if isinstance(adapter, APIFactoryAdapter):
            return adapter
        return None

    def get_tacore_service_adapter(self) -> Optional[TACoreServiceAgent]:
        """获取TACoreService适配器

        Returns:
            TACoreService代理或None
        """
        return self.get_trading_agents_adapter()

    def get_market_data(
        self, symbol: str, preferred_adapter: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取市场数据（支持多适配器fallback）

        Args:
            symbol: 交易对符号
            preferred_adapter: 首选适配器名称

        Returns:
            市场数据或None
        """
        try:
            # 尝试首选适配器
            if preferred_adapter and preferred_adapter in self.adapters:
                adapter = self.adapters[preferred_adapter]
                if adapter.is_connected():
                    data = adapter.get_market_data(symbol)
                    if data:
                        logger.debug(
                            "Market data retrieved from preferred adapter",
                            symbol=symbol,
                            adapter=preferred_adapter,
                        )
                        return data

            # Fallback到其他可用适配器
            for adapter_name, adapter in self.adapters.items():
                if adapter_name == preferred_adapter:
                    continue  # 已经尝试过了

                if adapter.is_connected() and hasattr(adapter, "get_market_data"):
                    try:
                        data = adapter.get_market_data(symbol)
                        if data:
                            logger.debug(
                                "Market data retrieved from fallback adapter",
                                symbol=symbol,
                                adapter=adapter_name,
                            )
                            return data
                    except Exception as e:
                        logger.warning(
                            "Failed to get market data from adapter",
                            symbol=symbol,
                            adapter=adapter_name,
                            error=str(e),
                        )
                        continue

            logger.warning("No adapter could provide market data", symbol=symbol)
            return None

        except Exception as e:
            logger.error("Error getting market data", symbol=symbol, error=str(e))
            return None

    def get_news_events(
        self, symbols: Optional[List[str]] = None, limit: int = 50, hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """获取新闻事件

        Args:
            symbols: 相关交易对符号列表
            limit: 最大返回数量
            hours_back: 获取多少小时前的新闻

        Returns:
            新闻事件列表
        """
        try:
            # 优先使用API工厂适配器获取新闻
            api_factory = self.get_api_factory_adapter()
            if api_factory and api_factory.is_connected():
                news_events = api_factory.get_news_events(symbols, limit, hours_back)
                if news_events:
                    logger.debug(
                        "News events retrieved from API Factory",
                        count=len(news_events),
                        symbols=symbols,
                    )
                    return news_events

            # Fallback到其他适配器（如果有的话）
            for adapter_name, adapter in self.adapters.items():
                if adapter.is_connected() and hasattr(adapter, "get_news_events"):
                    try:
                        news_events = adapter.get_news_events(
                            symbols, limit, hours_back
                        )
                        if news_events:
                            logger.debug(
                                "News events retrieved from fallback adapter",
                                count=len(news_events),
                                adapter=adapter_name,
                            )
                            return news_events
                    except Exception as e:
                        logger.warning(
                            "Failed to get news events from adapter",
                            adapter=adapter_name,
                            error=str(e),
                        )
                        continue

            logger.warning("No adapter could provide news events")
            return []

        except Exception as e:
            logger.error("Error getting news events", error=str(e))
            return []

    def health_check(self) -> Dict[str, Any]:
        """执行所有适配器的健康检查

        Returns:
            健康检查结果
        """
        try:
            health_status = {
                "overall_status": "healthy",
                "adapters": {},
                "summary": {
                    "total": len(self.adapters),
                    "healthy": 0,
                    "unhealthy": 0,
                    "disabled": 0,
                },
            }

            for adapter_name, adapter in self.adapters.items():
                try:
                    if not adapter.is_enabled():
                        status = "disabled"
                        health_status["summary"]["disabled"] += 1
                    elif adapter.health_check():
                        status = "healthy"
                        health_status["summary"]["healthy"] += 1
                    else:
                        status = "unhealthy"
                        health_status["summary"]["unhealthy"] += 1
                        health_status["overall_status"] = "degraded"

                    health_status["adapters"][adapter_name] = {
                        "status": status,
                        "details": adapter.get_status(),
                    }

                except Exception as e:
                    health_status["adapters"][adapter_name] = {
                        "status": "error",
                        "error": str(e),
                    }
                    health_status["summary"]["unhealthy"] += 1
                    health_status["overall_status"] = "degraded"

            # 如果所有适配器都不健康，则整体状态为不健康
            if (
                health_status["summary"]["healthy"] == 0
                and health_status["summary"]["total"] > 0
            ):
                health_status["overall_status"] = "unhealthy"

            return health_status

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"overall_status": "error", "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器管理器统计信息

        Returns:
            统计信息字典
        """
        self._update_stats()

        stats = self.stats.copy()

        # 添加各个适配器的统计信息
        stats["adapters"] = {}
        for adapter_name, adapter in self.adapters.items():
            stats["adapters"][adapter_name] = adapter.get_stats()

        return stats

    def _update_stats(self) -> None:
        """更新统计信息"""
        self.stats["total_adapters"] = len(self.adapters)
        self.stats["connected_adapters"] = sum(
            1 for adapter in self.adapters.values() if adapter.is_connected()
        )
        self.stats["failed_adapters"] = sum(
            1
            for adapter in self.adapters.values()
            if adapter.status == AdapterStatus.ERROR
        )

    def reconnect_failed_adapters(self) -> int:
        """重连失败的适配器

        Returns:
            成功重连的适配器数量
        """
        reconnected_count = 0

        for adapter_name, adapter in self.adapters.items():
            if adapter.status == AdapterStatus.ERROR and adapter.is_enabled():
                try:
                    logger.info(
                        "Attempting to reconnect adapter", adapter_name=adapter_name
                    )
                    if adapter.connect():
                        reconnected_count += 1
                        logger.info(
                            "Adapter reconnected successfully",
                            adapter_name=adapter_name,
                        )
                    else:
                        logger.warning(
                            "Adapter reconnection failed", adapter_name=adapter_name
                        )
                except Exception as e:
                    logger.error(
                        "Error reconnecting adapter",
                        adapter_name=adapter_name,
                        error=str(e),
                    )

        if reconnected_count > 0:
            self._update_stats()
            logger.info(
                "Adapter reconnection completed", reconnected_count=reconnected_count
            )

        return reconnected_count

    def shutdown(self) -> None:
        """关闭所有适配器"""
        try:
            logger.info("Shutting down AdapterManager")

            for adapter_name, adapter in self.adapters.items():
                try:
                    adapter.disconnect()
                    logger.debug("Adapter disconnected", adapter_name=adapter_name)
                except Exception as e:
                    logger.error(
                        "Error disconnecting adapter",
                        adapter_name=adapter_name,
                        error=str(e),
                    )

            self.adapters.clear()
            self.is_initialized = False

            logger.info("AdapterManager shutdown completed")

        except Exception as e:
            logger.error("Error during AdapterManager shutdown", error=str(e))

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
