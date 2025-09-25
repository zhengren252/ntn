# 统一日志管理器
# 实现结构化日志记录和错误处理
# 严格遵循环境隔离和日志规范

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog


class StructuredLogger:
    """结构化日志管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger_name = config.get("name", "scanner")
        self.log_level = config.get("level", "INFO")
        self.log_format = config.get("format", "json")

        # 文件日志配置
        self.file_config = config.get("file", {})
        self.console_config = config.get("console", {})

        # 初始化日志系统
        self._setup_structlog()
        self._setup_standard_logging()

        self.logger = structlog.get_logger(self.logger_name)

    def _setup_structlog(self) -> None:
        """配置structlog"""
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        # 根据格式选择处理器
        if self.log_format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=self.console_config.get("colorize", False)
                )
            )

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _setup_standard_logging(self) -> None:
        """配置标准logging"""
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper()))

        # 清除现有处理器
        root_logger.handlers.clear()

        # 设置控制台处理器
        if self.console_config.get("enabled", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level.upper()))

            if self.log_format == "json":
                console_formatter = JsonFormatter()
            else:
                console_formatter = (
                    ColoredFormatter()
                    if self.console_config.get("colorize", False)
                    else StandardFormatter()
                )

            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # 设置文件处理器
        if self.file_config.get("enabled", True):
            log_file_path = Path(self.file_config.get("path", "logs/scanner.log"))
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用RotatingFileHandler
            max_size = self._parse_size(self.file_config.get("max_size", "10MB"))
            backup_count = self.file_config.get("backup_count", 5)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, self.log_level.upper()))

            # 文件日志始终使用JSON格式
            file_formatter = JsonFormatter()
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串"""
        size_str = size_str.upper()
        if size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        """获取日志记录器"""
        if name:
            return structlog.get_logger(name)
        return self.logger


class JsonFormatter(logging.Formatter):
    """JSON格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        formatted_time = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        log_message = (
            f"{color}[{formatted_time}] {record.levelname:8s}{reset} "
            f"{record.name}:{record.funcName}:{record.lineno} - {record.getMessage()}"
        )

        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


class StandardFormatter(logging.Formatter):
    """标准格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        formatted_time = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        log_message = (
            f"[{formatted_time}] {record.levelname:8s} "
            f"{record.name}:{record.funcName}:{record.lineno} - {record.getMessage()}"
        )

        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


class ErrorHandler:
    """错误处理器"""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self.error_counts = {}
        self.last_errors = {}

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = False,
    ) -> None:
        """处理异常

        Args:
            exception: 异常对象
            context: 上下文信息
            reraise: 是否重新抛出异常
        """
        error_type = type(exception).__name__
        error_message = str(exception)

        # 统计错误次数
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_errors[error_type] = {
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        }

        # 记录错误日志
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "error_count": self.error_counts[error_type],
            "traceback": traceback.format_exc(),
        }

        if context:
            log_data.update(context)

        self.logger.error("Exception occurred", **log_data)

        if reraise:
            raise exception

    def handle_warning(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """处理警告

        Args:
            message: 警告消息
            context: 上下文信息
        """
        log_data = {"warning_message": message}
        if context:
            log_data.update(context)

        self.logger.warning(message, **log_data)

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计

        Returns:
            错误统计信息
        """
        return {
            "error_counts": self.error_counts.copy(),
            "last_errors": self.last_errors.copy(),
            "total_errors": sum(self.error_counts.values()),
        }


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self.performance_data = {}

    def log_execution_time(
        self, operation: str, duration: float, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录执行时间

        Args:
            operation: 操作名称
            duration: 执行时间（秒）
            context: 上下文信息
        """
        log_data = {
            "operation": operation,
            "duration_seconds": duration,
            "duration_ms": duration * 1000,
        }

        if context:
            log_data.update(context)

        # 记录性能统计
        if operation not in self.performance_data:
            self.performance_data[operation] = {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
            }

        stats = self.performance_data[operation]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        stats["avg_time"] = stats["total_time"] / stats["count"]

        log_data["performance_stats"] = stats.copy()

        # 根据执行时间选择日志级别
        if duration > 10:  # 超过10秒
            self.logger.warning("Slow operation detected", **log_data)
        elif duration > 5:  # 超过5秒
            self.logger.info("Operation completed", **log_data)
        else:
            self.logger.debug("Operation completed", **log_data)

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计

        Returns:
            性能统计信息
        """
        return self.performance_data.copy()


# 全局日志管理器
_logger_manager = None
_error_handler = None
_performance_logger = None


def setup_logging(config: Dict[str, Any]) -> None:
    """设置日志系统

    Args:
        config: 日志配置
    """
    global _logger_manager, _error_handler, _performance_logger

    _logger_manager = StructuredLogger(config)
    logger = _logger_manager.get_logger()

    _error_handler = ErrorHandler(logger)
    _performance_logger = PerformanceLogger(logger)

    logger.info("Logging system initialized", config=config)


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    if _logger_manager is None:
        # 使用默认配置
        default_config = {
            "name": "scanner",
            "level": "INFO",
            "format": "json",
            "console": {"enabled": True, "colorize": False},
            "file": {"enabled": False},
        }
        setup_logging(default_config)

    return _logger_manager.get_logger(name)


def get_error_handler() -> ErrorHandler:
    """获取错误处理器

    Returns:
        错误处理器实例
    """
    if _error_handler is None:
        logger = get_logger()
        return ErrorHandler(logger)
    return _error_handler


def get_performance_logger() -> PerformanceLogger:
    """获取性能日志记录器

    Returns:
        性能日志记录器实例
    """
    if _performance_logger is None:
        logger = get_logger()
        return PerformanceLogger(logger)
    return _performance_logger


# 装饰器
def log_execution_time(operation_name: Optional[str] = None):
    """记录函数执行时间的装饰器

    Args:
        operation_name: 操作名称，默认使用函数名
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            import time

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                perf_logger = get_performance_logger()
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                perf_logger.log_execution_time(op_name, duration)

                return result
            except Exception as e:
                duration = time.time() - start_time

                error_handler = get_error_handler()
                error_handler.handle_exception(
                    e,
                    context={
                        "function": f"{func.__module__}.{func.__name__}",
                        "duration": duration,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                    reraise=True,
                )

        return wrapper

    return decorator


def handle_exceptions(reraise: bool = True):
    """处理异常的装饰器

    Args:
        reraise: 是否重新抛出异常
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                error_handler.handle_exception(
                    e,
                    context={
                        "function": f"{func.__module__}.{func.__name__}",
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                    reraise=reraise,
                )

                if not reraise:
                    return None

        return wrapper

    return decorator
