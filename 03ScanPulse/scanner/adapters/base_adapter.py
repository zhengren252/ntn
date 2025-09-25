# 适配器基类
# 定义统一的适配器接口，遵循系统级集成流程

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AdapterConfig:
    """适配器配置"""

    name: str
    enabled: bool = True
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    mock_mode: bool = False
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class AdapterStatus:
    """适配器状态"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    MOCK = "mock"


class BaseAdapter(ABC):
    """适配器基类 - 定义统一的适配器接口"""

    def __init__(self, config: AdapterConfig):
        self.config = config
        self.status = AdapterStatus.DISCONNECTED
        self.last_error: Optional[str] = None
        self.connection_time: Optional[datetime] = None

        # 统计信息
        self.stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "last_request_time": None,
            "avg_response_time": 0.0,
            "total_response_time": 0.0,
        }

        logger.info(
            "Adapter initialized",
            adapter_name=self.config.name,
            enabled=self.config.enabled,
            mock_mode=self.config.mock_mode,
        )

    @abstractmethod
    def connect(self) -> bool:
        """建立连接

        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        pass

    @abstractmethod
    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据

        Args:
            symbol: 交易对符号

        Returns:
            市场数据或None
        """
        pass

    def is_connected(self) -> bool:
        """检查是否已连接

        Returns:
            是否已连接
        """
        return self.status in [AdapterStatus.CONNECTED, AdapterStatus.MOCK]

    def is_enabled(self) -> bool:
        """检查是否启用

        Returns:
            是否启用
        """
        return self.config.enabled

    def get_status(self) -> Dict[str, Any]:
        """获取适配器状态

        Returns:
            状态信息字典
        """
        return {
            "name": self.config.name,
            "status": self.status,
            "enabled": self.config.enabled,
            "mock_mode": self.config.mock_mode,
            "connected": self.is_connected(),
            "last_error": self.last_error,
            "connection_time": self.connection_time.isoformat()
            if self.connection_time
            else None,
            "stats": self.stats.copy(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()

        # 计算成功率
        if stats["requests_total"] > 0:
            stats["success_rate"] = stats["requests_success"] / stats["requests_total"]
            stats["failure_rate"] = stats["requests_failed"] / stats["requests_total"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0

        return stats

    def _update_stats(self, success: bool, response_time: float) -> None:
        """更新统计信息

        Args:
            success: 是否成功
            response_time: 响应时间（秒）
        """
        self.stats["requests_total"] += 1
        self.stats["last_request_time"] = datetime.now().isoformat()

        if success:
            self.stats["requests_success"] += 1
        else:
            self.stats["requests_failed"] += 1

        # 更新平均响应时间
        self.stats["total_response_time"] += response_time
        self.stats["avg_response_time"] = (
            self.stats["total_response_time"] / self.stats["requests_total"]
        )

    def _set_status(self, status: str, error: Optional[str] = None) -> None:
        """设置适配器状态

        Args:
            status: 新状态
            error: 错误信息（可选）
        """
        old_status = self.status
        self.status = status

        if error:
            self.last_error = error
        elif status == AdapterStatus.CONNECTED:
            self.last_error = None
            self.connection_time = datetime.now()

        if old_status != status:
            logger.info(
                "Adapter status changed",
                adapter_name=self.config.name,
                old_status=old_status,
                new_status=status,
                error=error,
            )

    def _execute_with_retry(self, func, *args, **kwargs):
        """带重试的执行函数

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        import time

        last_exception = None

        for attempt in range(self.config.retry_count + 1):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                response_time = time.time() - start_time

                self._update_stats(True, response_time)
                return result

            except Exception as e:
                last_exception = e
                response_time = time.time() - start_time
                self._update_stats(False, response_time)

                if attempt < self.config.retry_count:
                    logger.warning(
                        "Adapter request failed, retrying",
                        adapter_name=self.config.name,
                        attempt=attempt + 1,
                        max_attempts=self.config.retry_count + 1,
                        error=str(e),
                    )
                    time.sleep(self.config.retry_delay * (attempt + 1))  # 指数退避
                else:
                    logger.error(
                        "Adapter request failed after all retries",
                        adapter_name=self.config.name,
                        total_attempts=self.config.retry_count + 1,
                        error=str(e),
                    )

        # 所有重试都失败了
        if last_exception:
            raise last_exception

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "last_request_time": None,
            "avg_response_time": 0.0,
            "total_response_time": 0.0,
        }

        logger.info("Adapter stats reset", adapter_name=self.config.name)

    def __enter__(self):
        if self.config.enabled:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self.config.name}, status={self.status})"
        )

    def __repr__(self) -> str:
        return self.__str__()
