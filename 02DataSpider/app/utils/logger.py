#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志记录器模块

提供统一的日志记录功能，支持多种输出格式和级别
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
import json


class Logger:
    """统一日志记录器

    提供结构化日志记录，支持文件和控制台输出
    """

    def __init__(self, config: Optional[Any] = None, name: str = None):
        """初始化日志记录器

        Args:
            config: 配置管理器实例
            name: 日志记录器名称
        """
        self.config = config
        self.name = name or __name__
        self.logger = logging.getLogger(self.name)

        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        # 获取日志配置
        log_config = self._get_log_config()

        # 设置日志级别
        level = getattr(logging, log_config.get("level", "INFO").upper())
        self.logger.setLevel(level)

        # 创建格式化器
        formatter = self._create_formatter(log_config)

        # 添加控制台处理器
        if log_config.get("console", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(level)
            self.logger.addHandler(console_handler)

        # 添加文件处理器
        if log_config.get("file", True):
            file_handler = self._create_file_handler(log_config, formatter)
            if file_handler:
                self.logger.addHandler(file_handler)

        # 防止日志传播到根记录器
        self.logger.propagate = False

    def _get_log_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        if self.config and hasattr(self.config, "get_logging_config"):
            return self.config.get_logging_config()
        elif self.config and hasattr(self.config, "get"):
            return self.config.get("logging", {})
        else:
            # 默认配置
            return {
                "level": "INFO",
                "console": True,
                "file": True,
                "file_path": "logs/app.log",
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            }

    def _create_formatter(self, log_config: Dict[str, Any]) -> logging.Formatter:
        """创建日志格式化器"""
        log_format = log_config.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        return logging.Formatter(log_format)

    def _create_file_handler(
        self, log_config: Dict[str, Any], formatter: logging.Formatter
    ) -> Optional[logging.Handler]:
        """创建文件处理器"""
        try:
            # 获取日志文件路径
            file_path = log_config.get("file_path", "logs/app.log")

            # 确保日志目录存在
            log_dir = Path(file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            # 创建轮转文件处理器
            max_size = log_config.get("max_file_size", 10 * 1024 * 1024)  # 10MB
            backup_count = log_config.get("backup_count", 5)

            file_handler = logging.handlers.RotatingFileHandler(
                file_path, maxBytes=max_size, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)

            return file_handler

        except Exception as e:
            print(f"Failed to create file handler: {e}")
            return None

    def debug(self, message: str, extra: Dict[str, Any] = None):
        """记录调试信息"""
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, extra: Dict[str, Any] = None):
        """记录信息"""
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, extra: Dict[str, Any] = None):
        """记录警告"""
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, extra: Dict[str, Any] = None, exc_info: bool = False):
        """记录错误"""
        self._log(logging.ERROR, message, extra, exc_info=exc_info)

    def critical(
        self, message: str, extra: Dict[str, Any] = None, exc_info: bool = False
    ):
        """记录严重错误"""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info)

    def exception(self, message: str, extra: Dict[str, Any] = None):
        """记录异常信息（自动包含异常堆栈）"""
        self._log(logging.ERROR, message, extra, exc_info=True)

    def _log(
        self,
        level: int,
        message: str,
        extra: Dict[str, Any] = None,
        exc_info: bool = False,
    ):
        """内部日志记录方法"""
        # 构建日志消息
        if extra:
            # 如果有额外信息，将其格式化为JSON
            try:
                extra_str = json.dumps(extra, ensure_ascii=False, default=str)
                message = f"{message} | Extra: {extra_str}"
            except Exception:
                message = f"{message} | Extra: {str(extra)}"

        # 记录日志
        self.logger.log(level, message, exc_info=exc_info)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        user_id: str = None,
    ):
        """记录HTTP请求日志"""
        extra = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time": response_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if user_id:
            extra["user_id"] = user_id

        self.info(f"HTTP {method} {path} - {status_code} ({response_time:.3f}s)", extra)

    def log_crawler_activity(
        self,
        crawler_type: str,
        url: str,
        status: str,
        items_count: int = 0,
        error: str = None,
    ):
        """记录爬虫活动日志"""
        extra = {
            "crawler_type": crawler_type,
            "url": url,
            "status": status,
            "items_count": items_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if error:
            extra["error"] = error

        if status == "success":
            self.info(
                f"Crawler {crawler_type} - {url} - {status} ({items_count} items)",
                extra,
            )
        else:
            self.error(f"Crawler {crawler_type} - {url} - {status}", extra)

    def log_data_processing(
        self,
        stage: str,
        input_count: int,
        output_count: int,
        processing_time: float,
        errors: list = None,
    ):
        """记录数据处理日志"""
        extra = {
            "stage": stage,
            "input_count": input_count,
            "output_count": output_count,
            "processing_time": processing_time,
            "success_rate": output_count / input_count if input_count > 0 else 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if errors:
            extra["errors"] = errors

        self.info(
            f"Data processing {stage} - {input_count} -> {output_count} ({processing_time:.3f}s)",
            extra,
        )

    def log_zmq_message(
        self,
        topic: str,
        message_id: str,
        action: str,
        status: str = "success",
        error: str = None,
    ):
        """记录ZeroMQ消息日志"""
        extra = {
            "topic": topic,
            "message_id": message_id,
            "action": action,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if error:
            extra["error"] = error

        if status == "success":
            self.info(f"ZMQ {action} - {topic} - {message_id}", extra)
        else:
            self.error(f"ZMQ {action} failed - {topic} - {message_id}", extra)

    def set_level(self, level: Union[str, int]):
        """设置日志级别"""
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        self.logger.setLevel(level)

        # 同时设置所有处理器的级别
        for handler in self.logger.handlers:
            handler.setLevel(level)

    def get_logger(self) -> logging.Logger:
        """获取底层的logging.Logger实例"""
        return self.logger

    @classmethod
    def get_instance(cls, name: str = None, config: Any = None) -> "Logger":
        """获取Logger实例（单例模式）"""
        if not hasattr(cls, "_instances"):
            cls._instances = {}

        key = name or "default"
        if key not in cls._instances:
            cls._instances[key] = cls(config, name)

        return cls._instances[key]


# 便捷函数
def get_logger(name: str = None, config: Any = None) -> Logger:
    """获取日志记录器实例"""
    return Logger.get_instance(name, config)


# 模块级别的默认日志记录器
default_logger = Logger()


if __name__ == "__main__":
    # 测试日志记录器
    logger = Logger()

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # 测试带额外信息的日志
    logger.info("User login", {"user_id": "12345", "ip": "192.168.1.1"})

    # 测试专用日志方法
    logger.log_request("GET", "/api/data", 200, 0.123, "user123")
    logger.log_crawler_activity("web", "https://example.com", "success", 10)
    logger.log_data_processing("cleaning", 100, 95, 2.5)
    logger.log_zmq_message("crawler.news", "msg123", "publish")

    print("Logger test completed")
