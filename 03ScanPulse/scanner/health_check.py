# 健康检查模块
# 监控系统各组件状态，确保服务可用性
# 严格遵循微服务架构和监控规范

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from scanner.communication.redis_client import RedisClient
from scanner.config.env_manager import get_env_manager

# 暂时注释掉有问题的导入，等待ZMQ客户端实现完成
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.utils.logger import get_error_handler, get_logger

logger = get_logger(__name__)
error_handler = get_error_handler()


class HealthStatus(Enum):
    """健康状态枚举"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth:
    """组件健康状态"""

    def __init__(self, name: str, status: HealthStatus = HealthStatus.UNKNOWN):
        self.name = name
        self.status = status
        self.last_check = None
        self.error_message = None
        self.response_time = None
        self.metadata = {}

    def update(
        self,
        status: HealthStatus,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """更新健康状态"""
        self.status = status
        self.last_check = datetime.now()
        self.response_time = response_time
        self.error_message = error_message
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "response_time_ms": self.response_time * 1000
            if self.response_time
            else None,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.env_manager = get_env_manager()
        self.components: Dict[str, ComponentHealth] = {}
        self.check_interval = 30  # 默认30秒检查间隔
        self.timeout = 10  # 默认10秒超时
        self.is_running = False

        # 初始化组件
        self._initialize_components()

        logger.info("HealthChecker initialized")

    def _initialize_components(self) -> None:
        """初始化组件列表"""
        components = [
            "redis",
            "zmq_publisher",
            "zmq_subscriber",
            "zmq_request",
            "zmq_reply",
            "config",
            "disk_space",
            "memory",
        ]

        for component in components:
            self.components[component] = ComponentHealth(component)

    async def check_redis_health(self) -> ComponentHealth:
        """检查Redis健康状态"""
        component = self.components["redis"]
        start_time = time.time()

        try:
            redis_config = self.env_manager.get_redis_config()
            redis_client = RedisClient(redis_config)

            # 尝试连接
            if redis_client.connect():
                # 执行ping命令
                if redis_client.health_check():
                    # 获取统计信息
                    stats = redis_client.get_stats()
                    response_time = time.time() - start_time

                    component.update(
                        HealthStatus.HEALTHY,
                        response_time=response_time,
                        metadata={
                            "memory_usage": stats.get("memory_usage", "N/A"),
                            "key_count": stats.get("key_count", 0),
                            "hit_rate": stats.get("hit_rate", 0.0),
                        },
                    )
                else:
                    component.update(
                        HealthStatus.UNHEALTHY, error_message="Redis ping failed"
                    )

                redis_client.disconnect()
            else:
                component.update(
                    HealthStatus.UNHEALTHY, error_message="Failed to connect to Redis"
                )

        except Exception as e:
            error_handler.handle_exception(e, context={"component": "redis"})
            component.update(HealthStatus.UNHEALTHY, error_message=str(e))

        return component

    async def check_zmq_health(
        self, component_name: str, zmq_type: str
    ) -> ComponentHealth:
        """检查ZeroMQ组件健康状态"""
        component = self.components[component_name]
        start_time = time.time()

        try:
            zmq_client = ScannerZMQClient()

            # 根据类型检查不同的ZMQ组件
            if zmq_type == "publisher":
                success = await self._check_zmq_publisher(zmq_client)
            elif zmq_type == "subscriber":
                success = await self._check_zmq_subscriber(zmq_client)
            elif zmq_type == "request":
                success = await self._check_zmq_request(zmq_client)
            elif zmq_type == "reply":
                success = await self._check_zmq_reply(zmq_client)
            else:
                success = False

            response_time = time.time() - start_time

            if success:
                component.update(
                    HealthStatus.HEALTHY,
                    response_time=response_time,
                    metadata={"zmq_type": zmq_type},
                )
            else:
                component.update(
                    HealthStatus.UNHEALTHY, error_message=f"ZMQ {zmq_type} check failed"
                )

            zmq_client.disconnect()

        except Exception as e:
            error_handler.handle_exception(e, context={"component": component_name})
            component.update(HealthStatus.UNHEALTHY, error_message=str(e))

        return component

    async def _check_zmq_publisher(self, zmq_client) -> bool:  # ZMQClient类型暂时移除
        """检查ZMQ发布者"""
        try:
            zmq_client.start()
            await asyncio.sleep(0.1)  # 等待启动
            return zmq_client.is_running
        except Exception:
            return False

    async def _check_zmq_subscriber(self, zmq_client) -> bool:  # ZMQClient类型暂时移除
        """检查ZMQ订阅者"""
        try:
            zmq_client.start()
            await asyncio.sleep(0.1)  # 等待启动
            return zmq_client.is_running
        except Exception:
            return False

    async def _check_zmq_request(self, zmq_client) -> bool:  # ZMQClient类型暂时移除
        """检查ZMQ请求客户端"""
        try:
            zmq_client.start()
            await asyncio.sleep(0.1)  # 等待启动
            return zmq_client.is_running
        except Exception:
            return False

    async def _check_zmq_reply(self, zmq_client) -> bool:  # ZMQClient类型暂时移除
        """检查ZMQ回复服务器"""
        try:
            zmq_client.start()
            await asyncio.sleep(0.1)  # 等待启动
            return zmq_client.is_running
        except Exception:
            return False

    async def check_config_health(self) -> ComponentHealth:
        """检查配置健康状态"""
        component = self.components["config"]
        start_time = time.time()

        try:
            # 验证配置
            validation_result = self.env_manager.validate_config()
            response_time = time.time() - start_time

            if validation_result["valid"]:
                status = HealthStatus.HEALTHY
                if validation_result["warnings"]:
                    status = HealthStatus.DEGRADED

                component.update(
                    status,
                    response_time=response_time,
                    metadata={
                        "environment": self.env_manager.get_environment().value,
                        "warnings_count": len(validation_result["warnings"]),
                        "warnings": validation_result["warnings"],
                    },
                )
            else:
                component.update(
                    HealthStatus.UNHEALTHY,
                    error_message=f"Config validation failed: {validation_result['errors']}",
                    metadata={"errors": validation_result["errors"]},
                )

        except Exception as e:
            error_handler.handle_exception(e, context={"component": "config"})
            component.update(HealthStatus.UNHEALTHY, error_message=str(e))

        return component

    async def check_disk_space(self) -> ComponentHealth:
        """检查磁盘空间"""
        component = self.components["disk_space"]
        start_time = time.time()

        try:
            import shutil

            # 检查当前目录磁盘空间
            total, used, free = shutil.disk_usage(".")

            # 计算使用率
            usage_percent = (used / total) * 100
            free_gb = free / (1024**3)

            response_time = time.time() - start_time

            # 根据使用率确定状态
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                error_message = f"Disk usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                error_message = f"Disk usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                error_message = None

            component.update(
                status,
                response_time=response_time,
                error_message=error_message,
                metadata={
                    "usage_percent": round(usage_percent, 1),
                    "free_gb": round(free_gb, 1),
                    "total_gb": round(total / (1024**3), 1),
                },
            )

        except Exception as e:
            error_handler.handle_exception(e, context={"component": "disk_space"})
            component.update(HealthStatus.UNHEALTHY, error_message=str(e))

        return component

    async def check_memory_usage(self) -> ComponentHealth:
        """检查内存使用情况"""
        component = self.components["memory"]
        start_time = time.time()

        try:
            import psutil

            # 获取内存信息
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            available_gb = memory.available / (1024**3)

            response_time = time.time() - start_time

            # 根据使用率确定状态
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                error_message = f"Memory usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                error_message = f"Memory usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                error_message = None

            component.update(
                status,
                response_time=response_time,
                error_message=error_message,
                metadata={
                    "usage_percent": round(usage_percent, 1),
                    "available_gb": round(available_gb, 1),
                    "total_gb": round(memory.total / (1024**3), 1),
                },
            )

        except ImportError:
            # psutil未安装，跳过内存检查
            component.update(
                HealthStatus.UNKNOWN,
                error_message="psutil not available for memory monitoring",
            )
        except Exception as e:
            error_handler.handle_exception(e, context={"component": "memory"})
            component.update(HealthStatus.UNHEALTHY, error_message=str(e))

        return component

    async def check_all_components(self) -> Dict[str, ComponentHealth]:
        """检查所有组件"""
        logger.info("Starting health check for all components")

        # 并发检查所有组件
        tasks = [
            self.check_redis_health(),
            self.check_zmq_health("zmq_publisher", "publisher"),
            self.check_zmq_health("zmq_subscriber", "subscriber"),
            self.check_zmq_health("zmq_request", "request"),
            self.check_zmq_health("zmq_reply", "reply"),
            self.check_config_health(),
            self.check_disk_space(),
            self.check_memory_usage(),
        ]

        try:
            # 设置超时
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Health check timeout", timeout=self.timeout)

        logger.info("Health check completed")
        return self.components

    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self.components:
            return HealthStatus.UNKNOWN

        statuses = [comp.status for comp in self.components.values()]

        # 如果有任何组件不健康，整体状态为不健康
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY

        # 如果有任何组件降级，整体状态为降级
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # 如果所有组件都健康，整体状态为健康
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        overall_status = self.get_overall_status()

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "components": {
                name: comp.to_dict() for name, comp in self.components.items()
            },
            "summary": {
                "total_components": len(self.components),
                "healthy_components": len(
                    [
                        c
                        for c in self.components.values()
                        if c.status == HealthStatus.HEALTHY
                    ]
                ),
                "degraded_components": len(
                    [
                        c
                        for c in self.components.values()
                        if c.status == HealthStatus.DEGRADED
                    ]
                ),
                "unhealthy_components": len(
                    [
                        c
                        for c in self.components.values()
                        if c.status == HealthStatus.UNHEALTHY
                    ]
                ),
                "unknown_components": len(
                    [
                        c
                        for c in self.components.values()
                        if c.status == HealthStatus.UNKNOWN
                    ]
                ),
            },
        }

    async def start_monitoring(self) -> None:
        """开始监控"""
        if self.is_running:
            logger.warning("Health monitoring already running")
            return

        self.is_running = True
        logger.info("Starting health monitoring", interval=self.check_interval)

        while self.is_running:
            try:
                await self.check_all_components()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                error_handler.handle_exception(
                    e, context={"component": "health_monitor"}
                )
                await asyncio.sleep(5)  # 错误时短暂等待

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_running = False
        logger.info("Health monitoring stopped")


# 全局健康检查器实例
_health_checker = None


def get_health_checker() -> HealthChecker:
    """获取健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def check_health() -> bool:
    """快速健康检查（用于Docker健康检查）"""
    try:
        health_checker = get_health_checker()

        # 运行异步健康检查
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(health_checker.check_all_components())
            overall_status = health_checker.get_overall_status()
            return overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        finally:
            loop.close()

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return False


async def async_check_health() -> Dict[str, Any]:
    """异步健康检查"""
    health_checker = get_health_checker()
    await health_checker.check_all_components()
    return health_checker.get_health_report()
