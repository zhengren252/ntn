#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 日志管理
提供统一的日志记录功能

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional
from pathlib import Path

from src.core.config import get_settings


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    def format(self, record):
        """格式化日志记录"""
        # 获取原始格式化结果
        log_message = super().format(record)

        # 添加颜色
        if record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            reset = self.COLORS["RESET"]
            log_message = f"{color}{log_message}{reset}"

        return log_message


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record):
        """格式化为结构化日志"""
        import json

        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class LoggerManager:
    """日志管理器"""

    _loggers = {}
    _initialized = False
    _config = None

    @classmethod
    def _get_config(cls):
        """获取配置实例"""
        if cls._config is None:
            cls._config = get_settings()
        return cls._config

    @classmethod
    def initialize(cls):
        """初始化日志系统"""
        if cls._initialized:
            return

        # 获取配置
        config = cls._get_config()

        # 创建日志目录
        log_file_path = Path(config.LOG_FILE)
        log_dir = log_file_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 设置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))

        # 清除现有处理器
        root_logger.handlers.clear()

        # 添加控制台处理器
        cls._add_console_handler(root_logger)

        # 添加文件处理器
        cls._add_file_handlers(root_logger)

        # 添加错误文件处理器
        cls._add_error_handler(root_logger)

        # 设置第三方库日志级别
        cls._configure_third_party_loggers()

        cls._initialized = True

        # 记录初始化完成
        logger = cls.get_logger("LoggerManager")
        logger.info("日志系统初始化完成")

    @classmethod
    def _add_console_handler(cls, logger):
        """添加控制台处理器"""
        config = cls._get_config()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper()))

        # 使用彩色格式化器
        log_format = getattr(config, "LOG_FORMAT", "standard")
        if log_format == "colored":
            formatter = ColoredFormatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    @classmethod
    def _add_file_handlers(cls, logger):
        """添加文件处理器"""
        config = cls._get_config()
        log_dir = Path(config.LOG_FILE).parent

        # 应用日志文件
        app_log_file = log_dir / "mms_app.log"
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        app_handler.setLevel(logging.INFO)

        # 调试日志文件
        debug_log_file = log_dir / "mms_debug.log"
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        debug_handler.setLevel(logging.DEBUG)

        # 设置格式化器
        log_format = getattr(config, "LOG_FORMAT", "standard")
        if log_format == "json":
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        app_handler.setFormatter(formatter)
        debug_handler.setFormatter(formatter)

        logger.addHandler(app_handler)
        logger.addHandler(debug_handler)

    @classmethod
    def _add_error_handler(cls, logger):
        """添加错误处理器"""
        config = cls._get_config()
        log_dir = Path(config.LOG_FILE).parent
        error_log_file = log_dir / "mms_error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)

        # 错误日志使用详细格式
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s\n%(pathname)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        error_handler.setFormatter(formatter)

        logger.addHandler(error_handler)

    @classmethod
    def _configure_third_party_loggers(cls):
        """配置第三方库日志级别"""
        # 设置第三方库日志级别
        third_party_loggers = {
            "uvicorn": logging.WARNING,
            "uvicorn.access": logging.WARNING,
            "fastapi": logging.WARNING,
            "redis": logging.WARNING,
            "zmq": logging.WARNING,
            "asyncio": logging.WARNING,
            "urllib3": logging.WARNING,
            "requests": logging.WARNING,
        }

        for logger_name, level in third_party_loggers.items():
            logging.getLogger(logger_name).setLevel(level)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取日志器"""
        if not cls._initialized:
            cls.initialize()

        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)

        return cls._loggers[name]

    @classmethod
    def set_level(cls, level: str):
        """设置日志级别"""
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"无效的日志级别: {level}")

        # 更新所有日志器的级别
        for logger in cls._loggers.values():
            logger.setLevel(numeric_level)

        # 更新根日志器级别
        logging.getLogger().setLevel(numeric_level)

    @classmethod
    def add_context(cls, logger_name: str, **context):
        """为日志器添加上下文信息"""
        logger = cls.get_logger(logger_name)

        # 创建适配器添加上下文
        class ContextAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                return (
                    f"[{', '.join(f'{k}={v}' for k, v in self.extra.items())}] {msg}",
                    kwargs,
                )

        return ContextAdapter(logger, context)


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger_name: str = "performance"):
        self.logger = get_logger(logger_name)

    def log_execution_time(self, operation: str, execution_time: float, **kwargs):
        """记录执行时间"""
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        message = f"操作: {operation} | 执行时间: {execution_time:.4f}s"
        if extra_info:
            message += f" | {extra_info}"

        self.logger.info(message)

    def log_memory_usage(self, operation: str, memory_mb: float):
        """记录内存使用"""
        self.logger.info(f"操作: {operation} | 内存使用: {memory_mb:.2f}MB")

    def log_api_request(
        self, endpoint: str, method: str, response_time: float, status_code: int
    ):
        """记录API请求"""
        self.logger.info(
            f"API请求: {method} {endpoint} | "
            f"响应时间: {response_time:.4f}s | "
            f"状态码: {status_code}"
        )


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, logger_name: str = "audit"):
        self.logger = get_logger(logger_name)

    def log_simulation_start(
        self, simulation_id: str, user_id: Optional[str] = None, **params
    ):
        """记录仿真开始"""
        message = f"仿真开始 | ID: {simulation_id}"
        if user_id:
            message += f" | 用户: {user_id}"
        if params:
            message += f" | 参数: {params}"

        self.logger.info(message)

    def log_simulation_complete(
        self, simulation_id: str, execution_time: float, success: bool
    ):
        """记录仿真完成"""
        status = "成功" if success else "失败"
        self.logger.info(
            f"仿真完成 | ID: {simulation_id} | "
            f"状态: {status} | 执行时间: {execution_time:.4f}s"
        )

    def log_parameter_change(
        self, parameter: str, old_value, new_value, user_id: Optional[str] = None
    ):
        """记录参数变更"""
        message = f"参数变更 | 参数: {parameter} | 旧值: {old_value} | 新值: {new_value}"
        if user_id:
            message += f" | 操作用户: {user_id}"

        self.logger.warning(message)


# 便捷函数
def get_logger(name: str) -> logging.Logger:
    """获取日志器的便捷函数"""
    return LoggerManager.get_logger(name)


def setup_logging(level: Optional[str] = None):
    """设置日志系统"""
    LoggerManager.initialize()
    if level:
        LoggerManager.set_level(level)


# 装饰器
def log_execution_time(logger_name: str = None):
    """记录函数执行时间的装饰器"""
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.4f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"函数 {func.__name__} 执行失败，耗时: {execution_time:.4f}s，错误: {e}"
                )
                raise

        return wrapper

    return decorator


def log_async_execution_time(logger_name: str = None):
    """记录异步函数执行时间的装饰器"""
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"异步函数 {func.__name__} 执行完成，耗时: {execution_time:.4f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"异步函数 {func.__name__} 执行失败，耗时: {execution_time:.4f}s，错误: {e}"
                )
                raise

        return wrapper

    return decorator


# 初始化日志系统
if not LoggerManager._initialized:
    LoggerManager.initialize()
