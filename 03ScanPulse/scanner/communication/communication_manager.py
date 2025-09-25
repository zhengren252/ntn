# 通信管理器
# 统一管理ZeroMQ和Redis通信，实现系统级集成流程

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import structlog

from .message_formatter import MessageFormatter
from .redis_client import RedisClient
from .zmq_client import ZMQPublisher, ZMQSubscriber

logger = structlog.get_logger(__name__)


class CommunicationManager:
    """通信管理器 - 统一管理所有通信组件"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_initialized = False
        self.is_running = False

        # 通信组件
        self.zmq_publisher: Optional[ZMQPublisher] = None
        self.zmq_subscriber: Optional[ZMQSubscriber] = None
        self.redis_client: Optional[RedisClient] = None
        self.message_formatter: Optional[MessageFormatter] = None

        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}

        # 统计信息
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "start_time": None,
        }

        logger.info("CommunicationManager initialized")

    def initialize(self) -> bool:
        """初始化所有通信组件

        Returns:
            是否初始化成功
        """
        try:
            if self.is_initialized:
                logger.warning("CommunicationManager already initialized")
                return True

            # 初始化消息格式化器
            formatter_config = self.config.get("message_formatter", {})
            self.message_formatter = MessageFormatter(formatter_config)

            # 初始化Redis客户端
            redis_config = self.config.get("redis", {})
            self.redis_client = RedisClient(redis_config)
            if not self.redis_client.connect():
                logger.error("Failed to connect to Redis")
                return False

            # 初始化ZMQ发布者
            zmq_config = self.config.get("zmq", {})
            publisher_config = zmq_config.get("publisher", {})
            self.zmq_publisher = ZMQPublisher(publisher_config)
            if not self.zmq_publisher.connect():
                logger.error("Failed to connect ZMQ Publisher")
                return False

            # 初始化ZMQ订阅者
            subscriber_config = zmq_config.get("subscriber", {})
            self.zmq_subscriber = ZMQSubscriber(subscriber_config)
            if not self.zmq_subscriber.connect():
                logger.error("Failed to connect ZMQ Subscriber")
                return False

            # 注册默认消息处理器
            self._register_default_handlers()

            self.is_initialized = True
            self.stats["start_time"] = datetime.now().isoformat()

            logger.info("CommunicationManager initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize CommunicationManager", error=str(e))
            self.shutdown()
            return False

    def start(self) -> bool:
        """启动通信服务

        Returns:
            是否启动成功
        """
        try:
            if not self.is_initialized:
                logger.error("CommunicationManager not initialized")
                return False

            if self.is_running:
                logger.warning("CommunicationManager already running")
                return True

            # 启动ZMQ订阅者监听
            if self.zmq_subscriber:
                if not self.zmq_subscriber.start_listening():
                    logger.error("Failed to start ZMQ Subscriber")
                    return False

            self.is_running = True
            logger.info("CommunicationManager started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start CommunicationManager", error=str(e))
            return False

    def stop(self) -> None:
        """停止通信服务"""
        try:
            if not self.is_running:
                return

            # 停止ZMQ订阅者
            if self.zmq_subscriber:
                self.zmq_subscriber.stop_listening()

            self.is_running = False
            logger.info("CommunicationManager stopped")

        except Exception as e:
            logger.error("Error stopping CommunicationManager", error=str(e))

    def shutdown(self) -> None:
        """关闭所有通信组件"""
        try:
            self.stop()

            # 断开所有连接
            if self.zmq_publisher:
                self.zmq_publisher.disconnect()
                self.zmq_publisher = None

            if self.zmq_subscriber:
                self.zmq_subscriber.disconnect()
                self.zmq_subscriber = None

            if self.redis_client:
                self.redis_client.disconnect()
                self.redis_client = None

            self.is_initialized = False
            logger.info("CommunicationManager shutdown completed")

        except Exception as e:
            logger.error("Error during CommunicationManager shutdown", error=str(e))

    def publish_scan_result(self, symbol: str, scan_result: Dict[str, Any]) -> bool:
        """发布扫描结果

        Args:
            symbol: 交易对符号
            scan_result: 扫描结果

        Returns:
            是否发布成功
        """
        try:
            if (
                not self.is_running
                or not self.zmq_publisher
                or not self.message_formatter
            ):
                logger.error("CommunicationManager not ready for publishing")
                return False

            # 创建标准消息
            message = self.message_formatter.create_scan_result_message(
                symbol, scan_result
            )

            # 验证消息
            if not self.message_formatter.validate_message(message):
                logger.error("Invalid scan result message", symbol=symbol)
                return False

            # 发布到ZMQ
            opportunity_data = {
                "symbol": symbol,
                "type": scan_result.get("rule_type", "unknown"),
                "score": scan_result.get("score", 0),
                "details": scan_result,
                "message_id": message.header.message_id,
                "timestamp": message.header.timestamp,
            }

            success = self.zmq_publisher.publish_opportunity(opportunity_data)

            if success:
                # 缓存到Redis
                if self.redis_client:
                    self.redis_client.set_scan_result(symbol, scan_result)

                self.stats["messages_sent"] += 1
                logger.debug(
                    "Scan result published",
                    symbol=symbol,
                    score=scan_result.get("score"),
                    message_id=message.header.message_id,
                )
            else:
                self.stats["errors"] += 1

            return success

        except Exception as e:
            logger.error("Failed to publish scan result", symbol=symbol, error=str(e))
            self.stats["errors"] += 1
            return False

    def publish_batch_results(self, results: List[Dict[str, Any]]) -> int:
        """批量发布扫描结果

        Args:
            results: 扫描结果列表，每个结果包含symbol和scan_result

        Returns:
            成功发布的数量
        """
        if not results:
            return 0

        success_count = 0
        for result in results:
            symbol = result.get("symbol")
            scan_result = result.get("scan_result")

            if symbol and scan_result:
                if self.publish_scan_result(symbol, scan_result):
                    success_count += 1

        logger.info(
            "Batch publish completed",
            total_count=len(results),
            success_count=success_count,
            failure_count=len(results) - success_count,
        )

        return success_count

    def cache_market_data(self, symbol: str, market_data: Dict[str, Any]) -> bool:
        """缓存市场数据

        Args:
            symbol: 交易对符号
            market_data: 市场数据

        Returns:
            是否缓存成功
        """
        try:
            if not self.redis_client:
                logger.error("Redis client not available")
                return False

            return self.redis_client.set_market_data(symbol, market_data)

        except Exception as e:
            logger.error("Failed to cache market data", symbol=symbol, error=str(e))
            return False

    def get_cached_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取缓存的市场数据

        Args:
            symbol: 交易对符号

        Returns:
            市场数据或None
        """
        try:
            if not self.redis_client:
                logger.error("Redis client not available")
                return None

            return self.redis_client.get_market_data(symbol)

        except Exception as e:
            logger.error(
                "Failed to get cached market data", symbol=symbol, error=str(e)
            )
            return None

    def cache_news_events(self, events: List[Dict[str, Any]]) -> bool:
        """缓存新闻事件

        Args:
            events: 新闻事件列表

        Returns:
            是否缓存成功
        """
        try:
            if not self.redis_client:
                logger.error("Redis client not available")
                return False

            return self.redis_client.cache_news_events(events)

        except Exception as e:
            logger.error("Failed to cache news events", error=str(e))
            return False

    def get_cached_news_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取缓存的新闻事件

        Args:
            limit: 最大返回数量

        Returns:
            新闻事件列表
        """
        try:
            if not self.redis_client:
                logger.error("Redis client not available")
                return []

            return self.redis_client.get_cached_news_events(limit)

        except Exception as e:
            logger.error("Failed to get cached news events", error=str(e))
            return []

    def add_message_handler(
        self, topic: str, handler: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """添加消息处理器

        Args:
            topic: 主题名称
            handler: 处理函数
        """
        self.message_handlers[topic] = handler

        # 注册到ZMQ订阅者
        if self.zmq_subscriber:
            self.zmq_subscriber.add_message_handler(
                topic, self._wrap_message_handler(handler)
            )

        logger.debug("Message handler added", topic=topic)

    def _register_default_handlers(self) -> None:
        """注册默认消息处理器"""

        # 新闻事件处理器
        def handle_news_event(topic: str, message: Dict[str, Any]) -> None:
            try:
                logger.debug(
                    "News event received",
                    topic=topic,
                    title=message.get("title", "")[:50],
                )

                # 缓存新闻事件
                if self.redis_client:
                    self.redis_client.cache_news_events([message])

                self.stats["messages_received"] += 1

            except Exception as e:
                logger.error("Error handling news event", error=str(e))
                self.stats["errors"] += 1

        # 注册处理器
        self.add_message_handler("crawler.news", handle_news_event)

    def _wrap_message_handler(self, handler: Callable) -> Callable:
        """包装消息处理器，添加统计和错误处理

        Args:
            handler: 原始处理器

        Returns:
            包装后的处理器
        """

        def wrapped_handler(topic: str, message: Dict[str, Any]) -> None:
            try:
                handler(topic, message)
            except Exception as e:
                logger.error("Error in message handler", topic=topic, error=str(e))
                self.stats["errors"] += 1

        return wrapped_handler

    def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        try:
            health_status = {
                "overall_status": "healthy",
                "is_initialized": self.is_initialized,
                "is_running": self.is_running,
                "components": {},
                "stats": self.stats.copy(),
            }

            # 检查Redis
            if self.redis_client:
                redis_healthy = self.redis_client.health_check()
                health_status["components"]["redis"] = {
                    "status": "healthy" if redis_healthy else "unhealthy",
                    "connected": self.redis_client.is_connected,
                }
                if not redis_healthy:
                    health_status["overall_status"] = "degraded"
            else:
                health_status["components"]["redis"] = {"status": "not_initialized"}
                health_status["overall_status"] = "degraded"

            # 检查ZMQ发布者
            if self.zmq_publisher:
                health_status["components"]["zmq_publisher"] = {
                    "status": "healthy"
                    if self.zmq_publisher.is_connected
                    else "unhealthy",
                    "connected": self.zmq_publisher.is_connected,
                }
                if not self.zmq_publisher.is_connected:
                    health_status["overall_status"] = "degraded"
            else:
                health_status["components"]["zmq_publisher"] = {
                    "status": "not_initialized"
                }
                health_status["overall_status"] = "degraded"

            # 检查ZMQ订阅者
            if self.zmq_subscriber:
                health_status["components"]["zmq_subscriber"] = {
                    "status": "healthy"
                    if self.zmq_subscriber.is_connected
                    else "unhealthy",
                    "connected": self.zmq_subscriber.is_connected,
                    "listening": self.zmq_subscriber.is_running,
                }
                if not self.zmq_subscriber.is_connected:
                    health_status["overall_status"] = "degraded"
            else:
                health_status["components"]["zmq_subscriber"] = {
                    "status": "not_initialized"
                }
                health_status["overall_status"] = "degraded"

            return health_status

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "is_initialized": self.is_initialized,
                "is_running": self.is_running,
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()

        # 添加运行时间
        if stats.get("start_time"):
            try:
                start_time = datetime.fromisoformat(stats["start_time"])
                uptime_seconds = (datetime.now() - start_time).total_seconds()
                stats["uptime_seconds"] = uptime_seconds
                stats["uptime_hours"] = uptime_seconds / 3600
            except Exception:
                pass

        # 添加组件统计
        if self.redis_client:
            stats["redis_stats"] = self.redis_client.get_stats()

        return stats

    def __enter__(self):
        self.initialize()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
