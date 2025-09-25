#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 异常处理
定义自定义异常类和错误处理机制

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union

from .logger import get_logger

logger = get_logger(__name__)


class MMSBaseException(Exception):
    """MMS基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        cause: Exception = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now()

        # 记录异常
        self._log_exception()

    def _log_exception(self):
        """记录异常信息"""
        logger.error(
            f"异常发生: {self.error_code} | 消息: {self.message} | "
            f"详情: {self.details} | 时间: {self.timestamp.isoformat()}"
        )

        if self.cause:
            logger.error(f"原因异常: {self.cause}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class ConfigurationError(MMSBaseException):
    """配置错误"""

    pass


class DatabaseError(MMSBaseException):
    """数据库错误"""

    pass


class SimulationError(MMSBaseException):
    """仿真错误"""

    pass


class ValidationError(MMSBaseException):
    """验证错误"""

    pass


class CacheError(MMSBaseException):
    """缓存错误"""

    pass


class NetworkError(MMSBaseException):
    """网络错误"""

    pass


class WorkerError(MMSBaseException):
    """工作进程错误"""

    pass


class LoadBalancerError(MMSBaseException):
    """负载均衡器错误"""

    pass


class DataError(MMSBaseException):
    """数据错误"""

    pass


class AuthenticationError(MMSBaseException):
    """认证错误"""

    pass


class AuthorizationError(MMSBaseException):
    """授权错误"""

    pass


class ResourceNotFoundError(MMSBaseException):
    """资源未找到错误"""

    pass


class ResourceConflictError(MMSBaseException):
    """资源冲突错误"""

    pass


class RateLimitError(MMSBaseException):
    """速率限制错误"""

    pass


class TimeoutError(MMSBaseException):
    """超时错误"""

    pass


class ServiceUnavailableError(MMSBaseException):
    """服务不可用错误"""

    pass


class ExternalServiceError(MMSBaseException):
    """外部服务错误"""

    pass


class ErrorHandler:
    """错误处理器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def handle_exception(
        self, exception: Exception, context: Dict[str, Any] = None, reraise: bool = True
    ) -> Optional[Dict[str, Any]]:
        """处理异常"""
        context = context or {}

        # 记录异常详情
        self._log_exception_details(exception, context)

        # 如果是MMS自定义异常，直接返回错误信息
        if isinstance(exception, MMSBaseException):
            error_info = exception.to_dict()
            error_info.update(context)

            if reraise:
                raise exception
            return error_info

        # 处理标准异常
        error_info = self._handle_standard_exception(exception, context)

        if reraise:
            raise exception
        return error_info

    def _log_exception_details(self, exception: Exception, context: Dict[str, Any]):
        """记录异常详情"""
        self.logger.error(
            f"异常处理: {type(exception).__name__} | "
            f"消息: {str(exception)} | "
            f"上下文: {context}"
        )

        # 记录堆栈跟踪
        self.logger.debug(f"堆栈跟踪:\n{traceback.format_exc()}")

    def _handle_standard_exception(
        self, exception: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理标准异常"""
        error_code = type(exception).__name__
        message = str(exception)

        # 根据异常类型进行特殊处理
        if isinstance(exception, ValueError):
            error_code = "VALIDATION_ERROR"
        elif isinstance(exception, KeyError):
            error_code = "KEY_ERROR"
        elif isinstance(exception, FileNotFoundError):
            error_code = "FILE_NOT_FOUND"
        elif isinstance(exception, PermissionError):
            error_code = "PERMISSION_DENIED"
        elif isinstance(exception, ConnectionError):
            error_code = "CONNECTION_ERROR"
        elif isinstance(exception, TimeoutError):
            error_code = "TIMEOUT_ERROR"

        return {
            "error_code": error_code,
            "message": message,
            "details": context,
            "timestamp": datetime.now().isoformat(),
            "exception_type": type(exception).__name__,
        }

    def create_error_response(
        self,
        exception: Exception,
        status_code: int = 500,
        include_traceback: bool = False,
    ) -> Dict[str, Any]:
        """创建错误响应"""
        error_info = self.handle_exception(exception, reraise=False)

        response = {"success": False, "error": error_info, "status_code": status_code}

        if include_traceback:
            response["traceback"] = traceback.format_exc()

        return response


class RetryHandler:
    """重试处理器"""

    def __init__(
        self, max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.logger = get_logger(self.__class__.__name__)

    async def retry_async(
        self, func, *args, retryable_exceptions: tuple = (Exception,), **kwargs
    ):
        """异步重试执行"""
        import asyncio

        last_exception = None
        current_delay = self.delay

        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except retryable_exceptions as e:
                last_exception = e

                if attempt < self.max_retries:
                    self.logger.warning(
                        f"第 {attempt + 1} 次尝试失败: {e}，{current_delay}秒后重试"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= self.backoff_factor
                else:
                    self.logger.error(f"重试 {self.max_retries} 次后仍然失败: {e}")
                    raise e

            except Exception as e:
                # 非可重试异常，直接抛出
                self.logger.error(f"遇到不可重试异常: {e}")
                raise e

        # 理论上不会到达这里
        if last_exception:
            raise last_exception

    def retry_sync(
        self, func, *args, retryable_exceptions: tuple = (Exception,), **kwargs
    ):
        """同步重试执行"""
        import time

        last_exception = None
        current_delay = self.delay

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except retryable_exceptions as e:
                last_exception = e

                if attempt < self.max_retries:
                    self.logger.warning(
                        f"第 {attempt + 1} 次尝试失败: {e}，{current_delay}秒后重试"
                    )
                    time.sleep(current_delay)
                    current_delay *= self.backoff_factor
                else:
                    self.logger.error(f"重试 {self.max_retries} 次后仍然失败: {e}")
                    raise e

            except Exception as e:
                # 非可重试异常，直接抛出
                self.logger.error(f"遇到不可重试异常: {e}")
                raise e

        # 理论上不会到达这里
        if last_exception:
            raise last_exception


class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

        self.logger = get_logger(self.__class__.__name__)

    def __call__(self, func):
        """装饰器模式"""
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self._call(func, *args, **kwargs)

        return wrapper

    def _call(self, func, *args, **kwargs):
        """执行函数调用"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("熔断器状态变更为 HALF_OPEN")
            else:
                raise ServiceUnavailableError(
                    "服务熔断中，请稍后重试",
                    error_code="CIRCUIT_BREAKER_OPEN",
                    details={
                        "failure_count": self.failure_count,
                        "last_failure_time": self.last_failure_time.isoformat()
                        if self.last_failure_time
                        else None,
                    },
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.last_failure_time is None:
            return True

        return (
            datetime.now() - self.last_failure_time
        ).total_seconds() >= self.recovery_timeout

    def _on_success(self):
        """成功时的处理"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            self.logger.info("熔断器状态变更为 CLOSED")

    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"熔断器状态变更为 OPEN，失败次数: {self.failure_count}")

    def reset(self):
        """重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        self.logger.info("熔断器已重置")

    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "recovery_timeout": self.recovery_timeout,
        }


# 全局错误处理器实例
error_handler = ErrorHandler()
retry_handler = RetryHandler()


# 装饰器函数
def handle_exceptions(reraise: bool = True, include_traceback: bool = False):
    """异常处理装饰器"""

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # 限制长度
                    "kwargs": str(kwargs)[:200],
                }

                if reraise:
                    error_handler.handle_exception(e, context, reraise=True)
                else:
                    return error_handler.create_error_response(
                        e, include_traceback=include_traceback
                    )

        return wrapper

    return decorator


def handle_async_exceptions(reraise: bool = True, include_traceback: bool = False):
    """异步异常处理装饰器"""

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # 限制长度
                    "kwargs": str(kwargs)[:200],
                }

                if reraise:
                    error_handler.handle_exception(e, context, reraise=True)
                else:
                    return error_handler.create_error_response(
                        e, include_traceback=include_traceback
                    )

        return wrapper

    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """重试装饰器"""

    def decorator(func):
        import functools

        retry_handler_local = RetryHandler(max_retries, delay, backoff_factor)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_handler_local.retry_async(
                func, *args, retryable_exceptions=retryable_exceptions, **kwargs
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return retry_handler_local.retry_sync(
                func, *args, retryable_exceptions=retryable_exceptions, **kwargs
            )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
