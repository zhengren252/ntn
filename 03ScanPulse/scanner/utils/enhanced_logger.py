#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的错误处理和结构化日志记录系统
提供完整的日志管理、错误处理、性能监控和审计功能
严格遵循环境隔离和安全规范
"""

import logging
import logging.handlers
import re
import sys
import traceback

# import asyncio  # Unused
# import functools  # Unused
# import inspect  # Unused
# import json  # Unused
# import os  # Unused
# import time  # Unused
# from contextlib import contextmanager  # Unused
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import structlog


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEventType(Enum):
    """审计事件类型"""

    API_CALL = "api_call"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    SECURITY_EVENT = "security_event"
    PERFORMANCE_ALERT = "performance_alert"
    ERROR_EVENT = "error_event"


@dataclass
class ErrorStats:
    """错误统计信息"""

    error_type: str
    count: int = 0
    first_occurrence: Optional[datetime] = None
    last_occurrence: Optional[datetime] = None
    contexts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """性能指标"""

    operation: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    avg_time: float = 0.0
    last_execution: Optional[datetime] = None


class SensitiveDataFilter:
    """敏感数据过滤器"""

    def __init__(self, sensitive_fields: List[str]):
        self.sensitive_fields = [field.lower() for field in sensitive_fields]
        self.patterns = [
            re.compile(rf"\b{field}\b", re.IGNORECASE) for field in sensitive_fields
        ]

    def filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤字典中的敏感数据"""
        if not isinstance(data, dict):
            return data

        filtered = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                filtered[key] = "***FILTERED***"
            elif isinstance(value, dict):
                filtered[key] = self.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    self.filter_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        return filtered

    def filter_string(self, text: str) -> str:
        """过滤字符串中的敏感数据"""
        for pattern in self.patterns:
            text = pattern.sub(
                lambda m: m.group().split("=")[0] + "=***FILTERED***"
                if "=" in m.group()
                else "***FILTERED***",
                text,
            )
        return text


class EnhancedErrorHandler:
    """增强的错误处理器"""

    def __init__(self, logger: structlog.BoundLogger, config: Dict[str, Any]):
        self.logger = logger
        self.config = config
        self.error_stats: Dict[str, ErrorStats] = {}
        self.max_error_count = config.get("max_error_count", 1000)
        self.stats_interval = config.get("error_stats_interval", 300)
        self.last_stats_report = datetime.now()

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = False,
        severity: LogLevel = LogLevel.ERROR,
    ) -> None:
        """处理异常"""
        error_type = type(exception).__name__
        error_message = str(exception)
        timestamp = datetime.now()

        # 更新错误统计
        if error_type not in self.error_stats:
            self.error_stats[error_type] = ErrorStats(
                error_type=error_type, first_occurrence=timestamp
            )

        stats = self.error_stats[error_type]
        stats.count += 1
        stats.last_occurrence = timestamp

        # 限制上下文存储数量
        if len(stats.contexts) < 10:
            stats.contexts.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "context": context or {},
                    "traceback": traceback.format_exc(),
                }
            )

        # 记录错误日志
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "error_count": stats.count,
            "first_occurrence": stats.first_occurrence.isoformat()
            if stats.first_occurrence
            else None,
            "traceback": traceback.format_exc(),
            "context": context or {},
        }

        if severity == LogLevel.CRITICAL:
            self.logger.critical("Critical exception occurred", **log_data)
        elif severity == LogLevel.ERROR:
            self.logger.error("Exception occurred", **log_data)
        else:
            self.logger.warning("Warning exception occurred", **log_data)

        # 定期报告错误统计
        if (timestamp - self.last_stats_report).seconds >= self.stats_interval:
            self._report_error_stats()
            self.last_stats_report = timestamp

        if reraise:
            raise exception

    def handle_warning(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """处理警告"""
        log_data = {"warning_message": message}
        if context:
            log_data.update(context)
        self.logger.warning(message, **log_data)

    def _report_error_stats(self) -> None:
        """报告错误统计"""
        total_errors = sum(stats.count for stats in self.error_stats.values())

        stats_summary = {
            "total_errors": total_errors,
            "unique_error_types": len(self.error_stats),
            "top_errors": sorted(
                [
                    (error_type, stats.count)
                    for error_type, stats in self.error_stats.items()
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }

        self.logger.info("Error statistics report", **stats_summary)

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            error_type: {
                "count": stats.count,
                "first_occurrence": stats.first_occurrence.isoformat()
                if stats.first_occurrence
                else None,
                "last_occurrence": stats.last_occurrence.isoformat()
                if stats.last_occurrence
                else None,
                "recent_contexts": stats.contexts[-3:],  # 最近3个上下文
            }
            for error_type, stats in self.error_stats.items()
        }


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, logger: structlog.BoundLogger, config: Dict[str, Any]):
        self.logger = logger
        self.config = config
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.slow_threshold = config.get("slow_threshold_seconds", 5.0)
        self.memory_check_interval = config.get("memory_check_interval", 60)
        self.last_memory_check = datetime.now()

    def log_execution_time(
        self, operation: str, duration: float, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录执行时间"""
        timestamp = datetime.now()

        # 更新性能指标
        if operation not in self.metrics:
            self.metrics[operation] = PerformanceMetrics(operation=operation)

        metrics = self.metrics[operation]
        metrics.count += 1
        metrics.total_time += duration
        metrics.min_time = min(metrics.min_time, duration)
        metrics.max_time = max(metrics.max_time, duration)
        metrics.avg_time = metrics.total_time / metrics.count
        metrics.last_execution = timestamp

        log_data = {
            "operation": operation,
            "duration_seconds": duration,
            "duration_ms": duration * 1000,
            "execution_count": metrics.count,
            "avg_duration": metrics.avg_time,
            "min_duration": metrics.min_time,
            "max_duration": metrics.max_time,
        }

        if context:
            log_data.update(context)

        # 根据执行时间选择日志级别
        if duration > self.slow_threshold:
            self.logger.warning("Slow operation detected", **log_data)
        elif duration > self.slow_threshold / 2:
            self.logger.info("Operation completed", **log_data)
        else:
            self.logger.debug("Operation completed", **log_data)

        # 定期检查内存使用
        if self.config.get("log_memory_usage", False):
            if (
                timestamp - self.last_memory_check
            ).seconds >= self.memory_check_interval:
                self._log_memory_usage()
                self.last_memory_check = timestamp

    def _log_memory_usage(self) -> None:
        """记录内存使用情况"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            memory_data = {
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(),
            }

            self.logger.info("System resource usage", **memory_data)
        except Exception as e:
            self.logger.warning("Failed to collect memory usage", error=str(e))

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            operation: {
                "count": metrics.count,
                "total_time": metrics.total_time,
                "avg_time": metrics.avg_time,
                "min_time": metrics.min_time,
                "max_time": metrics.max_time,
                "last_execution": metrics.last_execution.isoformat()
                if metrics.last_execution
                else None,
            }
            for operation, metrics in self.metrics.items()
        }


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, logger: structlog.BoundLogger, config: Dict[str, Any]):
        self.logger = logger
        self.config = config
        self.sensitive_filter = SensitiveDataFilter(config.get("sensitive_fields", []))

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        """记录API调用"""
        if not self.config.get("log_api_calls", False):
            return

        audit_data = {
            "audit_type": AuditEventType.API_CALL.value,
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.now().isoformat(),
        }

        if params:
            audit_data["params"] = self.sensitive_filter.filter_dict(params)
        if response_status:
            audit_data["response_status"] = response_status
        if duration:
            audit_data["duration_seconds"] = duration

        self.logger.info("API call audit", **audit_data)

    def log_data_access(
        self,
        resource: str,
        operation: str,
        user_id: Optional[str] = None,
        record_count: Optional[int] = None,
    ) -> None:
        """记录数据访问"""
        if not self.config.get("log_data_access", False):
            return

        audit_data = {
            "audit_type": AuditEventType.DATA_ACCESS.value,
            "resource": resource,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        }

        if user_id:
            audit_data["user_id"] = user_id
        if record_count:
            audit_data["record_count"] = record_count

        self.logger.info("Data access audit", **audit_data)

    def log_config_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        user_id: Optional[str] = None,
    ) -> None:
        """记录配置变更"""
        if not self.config.get("log_config_changes", False):
            return

        audit_data = {
            "audit_type": AuditEventType.CONFIG_CHANGE.value,
            "config_key": config_key,
            "old_value": self.sensitive_filter.filter_string(str(old_value)),
            "new_value": self.sensitive_filter.filter_string(str(new_value)),
            "timestamp": datetime.now().isoformat(),
        }

        if user_id:
            audit_data["user_id"] = user_id

        self.logger.warning("Configuration change audit", **audit_data)


class EnhancedLoggerManager:
    """增强的日志管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger_name = config.get("name", "scanner")
        self.log_level = config.get("level", "INFO")
        self.log_format = config.get("format", "json")

        # 初始化过滤器
        filter_config = config.get("filters", {})
        self.sensitive_filter = SensitiveDataFilter(
            filter_config.get("sensitive_fields", [])
        )
        self.exclude_loggers = filter_config.get("exclude_loggers", [])
        self.exclude_patterns = [
            re.compile(pattern) for pattern in filter_config.get("exclude_patterns", [])
        ]

        # 初始化日志系统
        self._setup_structlog()
        self._setup_standard_logging()

        # 获取主日志记录器
        self.logger = structlog.get_logger(self.logger_name)

        # 初始化子组件
        error_config = config.get("error_handling", {})
        performance_config = config.get("performance", {})
        audit_config = config.get("audit", {})

        self.error_handler = EnhancedErrorHandler(self.logger, error_config)
        self.performance_monitor = PerformanceMonitor(self.logger, performance_config)
        self.audit_logger = AuditLogger(self.logger, audit_config)

        self.logger.info(
            "Enhanced logging system initialized", config=self._sanitize_config(config)
        )

    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """清理配置中的敏感信息"""
        return self.sensitive_filter.filter_dict(config)

    def _setup_structlog(self) -> None:
        """配置structlog"""
        processors = [
            self._filter_processor,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        # 添加调用者信息
        if self.config.get("structured", {}).get("include_caller", False):
            processors.append(
                structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                        structlog.processors.CallsiteParameter.LINENO,
                    ]
                )
            )

        # 根据格式选择处理器
        if self.log_format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            console_config = self.config.get("console", {})
            processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=console_config.get("colorize", False)
                )
            )

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _filter_processor(self, logger, method_name, event_dict):
        """过滤处理器"""
        # 过滤排除的日志记录器
        logger_name = event_dict.get("logger", "")
        if any(excluded in logger_name for excluded in self.exclude_loggers):
            raise structlog.DropEvent

        # 过滤排除的消息模式
        message = event_dict.get("event", "")
        if any(pattern.match(message) for pattern in self.exclude_patterns):
            raise structlog.DropEvent

        # 过滤敏感数据
        for key, value in event_dict.items():
            if isinstance(value, dict):
                event_dict[key] = self.sensitive_filter.filter_dict(value)
            elif isinstance(value, str):
                event_dict[key] = self.sensitive_filter.filter_string(value)

        return event_dict

    def _setup_standard_logging(self) -> None:
        """配置标准logging"""
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper()))

        # 清除现有处理器
        root_logger.handlers.clear()

        # 设置控制台处理器
        console_config = self.config.get("console", {})
        if console_config.get("enabled", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_level = console_config.get("level", self.log_level)
            console_handler.setLevel(getattr(logging, console_level.upper()))

            if self.log_format == "json":
                console_formatter = self._create_json_formatter()
            else:
                console_formatter = self._create_console_formatter(
                    console_config.get("colorize", False)
                )

            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # 设置文件处理器
        file_config = self.config.get("file", {})
        if file_config.get("enabled", False):
            log_file_path = Path(file_config.get("path", "logs/scanner.log"))
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # 选择处理器类型
            rotation = file_config.get("rotation", "size")
            if rotation == "time":
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    log_file_path,
                    when="midnight",
                    interval=1,
                    backupCount=file_config.get("backup_count", 7),
                    encoding="utf-8",
                )
            else:
                max_size = self._parse_size(file_config.get("max_size", "10MB"))
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file_path,
                    maxBytes=max_size,
                    backupCount=file_config.get("backup_count", 5),
                    encoding="utf-8",
                )

            file_level = file_config.get("level", self.log_level)
            file_handler.setLevel(getattr(logging, file_level.upper()))

            # 文件日志始终使用JSON格式
            file_formatter = self._create_json_formatter()
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.upper().strip()

        # 定义单位映射
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

        # 提取数字和单位
        import re

        match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Z]*)$", size_str)
        if not match:
            raise ValueError(f"Invalid size format: {size_str}")

        number, unit = match.groups()
        number = float(number)

        # 默认单位为字节
        if not unit:
            unit = "B"

        if unit not in units:
            raise ValueError(f"Unknown size unit: {unit}")

        return int(number * units[unit])

    def _create_json_formatter(self) -> logging.Formatter:
        """创建JSON格式化器"""
        return logging.Formatter("%(message)s")

    def _create_console_formatter(self, colorize: bool = False) -> logging.Formatter:
        """创建控制台格式化器"""
        if colorize:
            return logging.Formatter(
                "\033[36m%(asctime)s\033[0m - \033[32m%(name)s\033[0m - \033[33m%(levelname)s\033[0m - %(message)s"
            )
        else:
            return logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

    def get_logger(self, name: str = None) -> structlog.BoundLogger:
        """获取日志记录器"""
        if name:
            return structlog.get_logger(name)
        return self.logger

    def get_error_handler(self) -> EnhancedErrorHandler:
        """获取错误处理器"""
        return self.error_handler

    def get_performance_monitor(self) -> PerformanceMonitor:
        """获取性能监控器"""
        return self.performance_monitor

    def get_audit_logger(self) -> AuditLogger:
        """获取审计日志记录器"""
        return self.audit_logger


def setup_logger(config: Dict[str, Any]) -> EnhancedLoggerManager:
    """设置增强日志系统"""
    return EnhancedLoggerManager(config)
