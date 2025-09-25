#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描器存储模块
提供Redis缓存和数据存储功能
"""

from .redis_client import RedisClient

__all__ = ["RedisClient"]
