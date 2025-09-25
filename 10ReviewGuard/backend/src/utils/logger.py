#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReviewGuard人工审核模组 - 日志配置
"""

import os
import logging
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大字节数
        backup_count: 备份文件数量
    
    Returns:
        配置好的日志记录器
    """
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建轮转文件处理器
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 防止日志重复
    logger.propagate = False
    
    return logger


def get_default_logger() -> logging.Logger:
    """
    获取默认日志记录器
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE")
    
    return setup_logger(
        "reviewguard",
        level=log_level,
        log_file=log_file
    )


class LoggerMixin:
    """
    日志记录器混入类
    """
    
    @property
    def logger(self) -> logging.Logger:
        """
        获取类专用的日志记录器
        """
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__name__
            module_name = self.__class__.__module__
            logger_name = f"{module_name}.{class_name}"
            
            log_level = os.getenv("LOG_LEVEL", "INFO")
            log_file = os.getenv("LOG_FILE")
            
            self._logger = setup_logger(
                logger_name,
                level=log_level,
                log_file=log_file
            )
        
        return self._logger


def log_function_call(func):
    """
    函数调用日志装饰器
    """
    def wrapper(*args, **kwargs):
        logger = get_default_logger()
        func_name = func.__name__
        
        # 记录函数调用
        logger.debug(f"Calling function: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Function {func_name} failed with error: {e}")
            raise
    
    return wrapper


def log_async_function_call(func):
    """
    异步函数调用日志装饰器
    """
    async def wrapper(*args, **kwargs):
        logger = get_default_logger()
        func_name = func.__name__
        
        # 记录函数调用
        logger.debug(f"Calling async function: {func_name}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async function {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Async function {func_name} failed with error: {e}")
            raise
    
    return wrapper


if __name__ == "__main__":
    # 测试日志配置
    logger = setup_logger("test", level="DEBUG")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # 测试文件日志
    file_logger = setup_logger(
        "test_file",
        level="INFO",
        log_file="test.log"
    )
    
    file_logger.info("This message will be written to file")
    
    print("Logger test completed")