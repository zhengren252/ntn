#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """应用设置"""
    
    # 基础配置
    app_name: str = "NTN Module"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # ZeroMQ配置
    zmq_port: int = 5555
    
    # 数据库配置
    database_url: Optional[str] = None
    
    # Redis配置
    redis_url: str = "redis://localhost:6379"
    
    # 日志配置
    log_level: str = "INFO"
    
    # API配置
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
