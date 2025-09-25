#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统级日志配置
为所有模组提供统一的日志配置和管理
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class SystemLoggerConfig:
    """系统日志配置管理器"""

    def __init__(self, service_name: str, log_dir: str = None):
        self.service_name = service_name
        self.log_dir = Path(log_dir or "logs")
        self.log_dir.mkdir(exist_ok=True)

        # 创建服务专用日志目录
        self.service_log_dir = self.log_dir / service_name
        self.service_log_dir.mkdir(exist_ok=True)

    def get_log_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "json": {"()": "config.system_logging.JSONFormatter"},
                "simple": {"format": "%(levelname)s - %(message)s"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "detailed",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "json",
                    "filename": str(self.service_log_dir / f"{self.service_name}.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf8",
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "json",
                    "filename": str(
                        self.service_log_dir / f"{self.service_name}_error.log"
                    ),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 3,
                    "encoding": "utf8",
                },
                "performance_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "json",
                    "filename": str(
                        self.service_log_dir / f"{self.service_name}_performance.log"
                    ),
                    "maxBytes": 5242880,  # 5MB
                    "backupCount": 3,
                    "encoding": "utf8",
                },
            },
            "loggers": {
                "": {  # root logger
                    "level": "INFO",
                    "handlers": ["console", "file", "error_file"],
                },
                "performance": {
                    "level": "INFO",
                    "handlers": ["performance_file"],
                    "propagate": False,
                },
                "zmq": {"level": "WARNING", "propagate": True},
                "urllib3": {"level": "WARNING", "propagate": True},
                "requests": {"level": "WARNING", "propagate": True},
            },
        }


class JSONFormatter(logging.Formatter):
    """JSON格式化器"""

    def format(self, record):
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
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "service_name"):
            log_entry["service_name"] = record.service_name

        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation

        if hasattr(record, "duration"):
            log_entry["duration"] = record.duration

        # 添加自定义字段
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ] and not key.startswith("_"):
                if isinstance(value, (str, int, float, bool, list, dict)):
                    log_entry[key] = value
                else:
                    log_entry[key] = str(value)

        return json.dumps(log_entry, ensure_ascii=False)


class ServiceLogger:
    """服务日志记录器"""

    def __init__(self, service_name: str, log_dir: str = None):
        self.service_name = service_name
        self.config = SystemLoggerConfig(service_name, log_dir)
        self.logger = None
        self.performance_logger = None
        self._setup_logging()

    def _setup_logging(self):
        """设置日志记录"""
        import logging.config

        config = self.config.get_log_config()
        logging.config.dictConfig(config)

        self.logger = logging.getLogger(self.service_name)
        self.performance_logger = logging.getLogger("performance")

        # 添加服务名称到所有日志记录
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.service_name = self.service_name
            return record

        logging.setLogRecordFactory(record_factory)

    def get_logger(self, name: str = None) -> logging.Logger:
        """获取日志记录器"""
        if name:
            return logging.getLogger(f"{self.service_name}.{name}")
        return self.logger

    def get_performance_logger(self) -> logging.Logger:
        """获取性能日志记录器"""
        return self.performance_logger

    def log_startup(self, config: Dict[str, Any] = None):
        """记录服务启动日志"""
        self.logger.info(
            f"Service {self.service_name} starting up",
            extra={"event": "service_startup", "config": config or {}},
        )

    def log_shutdown(self, reason: str = None):
        """记录服务关闭日志"""
        self.logger.info(
            f"Service {self.service_name} shutting down",
            extra={"event": "service_shutdown", "reason": reason or "Normal shutdown"},
        )

    def log_health_check(self, status: str, details: Dict[str, Any] = None):
        """记录健康检查日志"""
        self.logger.info(
            f"Health check: {status}",
            extra={"event": "health_check", "status": status, "details": details or {}},
        )

    def log_performance(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        details: Dict[str, Any] = None,
    ):
        """记录性能日志"""
        self.performance_logger.info(
            f"Performance: {operation}",
            extra={
                "operation": operation,
                "duration": duration,
                "success": success,
                "details": details or {},
            },
        )

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """记录错误日志"""
        self.logger.error(
            f"Error occurred: {str(error)}",
            exc_info=True,
            extra={
                "event": "error",
                "error_type": error.__class__.__name__,
                "context": context or {},
            },
        )


# 全局日志管理器
_loggers: Dict[str, ServiceLogger] = {}


def get_service_logger(service_name: str, log_dir: str = None) -> ServiceLogger:
    """获取服务日志记录器（单例模式）"""
    if service_name not in _loggers:
        _loggers[service_name] = ServiceLogger(service_name, log_dir)
    return _loggers[service_name]


def setup_module_logging(module_name: str, log_level: str = "INFO") -> logging.Logger:
    """为模组设置日志记录"""
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 如果没有处理器，添加控制台处理器
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# 性能监控装饰器
def performance_monitor(operation_name: str = None):
    """性能监控装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            operation = operation_name or f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                # 记录性能日志
                perf_logger = logging.getLogger("performance")
                perf_logger.info(
                    f"Operation completed: {operation}",
                    extra={
                        "operation": operation,
                        "duration": duration,
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()

                # 记录失败的性能日志
                perf_logger = logging.getLogger("performance")
                perf_logger.error(
                    f"Operation failed: {operation}",
                    extra={
                        "operation": operation,
                        "duration": duration,
                        "success": False,
                        "error": str(e),
                    },
                )

                raise

        return wrapper

    return decorator


# 请求上下文日志装饰器
def log_request_context(request_id_key: str = "request_id"):
    """请求上下文日志装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 尝试从参数中获取request_id
            request_id = kwargs.get(request_id_key)
            if not request_id and args:
                # 尝试从第一个参数（通常是self）的属性中获取
                if hasattr(args[0], request_id_key):
                    request_id = getattr(args[0], request_id_key)

            # 设置日志上下文
            old_factory = logging.getLogRecordFactory()

            def record_factory(*record_args, **record_kwargs):
                record = old_factory(*record_args, **record_kwargs)
                if request_id:
                    record.request_id = request_id
                return record

            logging.setLogRecordFactory(record_factory)

            try:
                return func(*args, **kwargs)
            finally:
                # 恢复原始工厂
                logging.setLogRecordFactory(old_factory)

        return wrapper

    return decorator
