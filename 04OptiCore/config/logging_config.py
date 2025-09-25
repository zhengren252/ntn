#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略优化模组日志配置
遵循三环境隔离规范，为不同环境配置不同的日志级别和输出方式
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import get_settings


def setup_logging():
    """
    设置日志配置

    根据当前环境（development/staging/production）配置不同的日志级别和输出方式
    - development: DEBUG级别，同时输出到控制台和文件
    - staging: INFO级别，主要输出到文件
    - production: WARNING级别，只输出到文件
    """
    settings = get_settings()

    # 创建日志目录
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # 获取日志级别
    log_level = getattr(logging, settings.log_level.upper())

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 添加文件处理器
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 在开发环境中添加控制台处理器
    if settings.is_development or settings.debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 设置第三方库的日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # 记录启动信息
    root_logger.info(
        f"日志系统初始化完成 - 环境: {settings.environment}, 级别: {settings.log_level}"
    )

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称，通常为模块名

    Returns:
        配置好的日志记录器实例
    """
    return logging.getLogger(name)
