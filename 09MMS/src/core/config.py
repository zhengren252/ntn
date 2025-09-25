#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 配置管理
基于Pydantic Settings的配置管理系统

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """数据库配置类"""
    database_url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600


class Settings(BaseSettings):
    """应用程序配置类"""

    # 基础配置
    APP_NAME: str = "市场微结构仿真引擎 (MMS)"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # 服务器配置
    HOST: str = Field(default="0.0.0.0", env="HOST")
    HTTP_PORT: int = Field(default=8000, env="HTTP_PORT")
    GRPC_PORT: int = Field(default=50051, env="GRPC_PORT")

    # ZeroMQ配置
    FRONTEND_PORT: int = Field(default=5555, env="FRONTEND_PORT")
    BACKEND_PORT: int = Field(default=5556, env="BACKEND_PORT")
    WORKER_COUNT: int = Field(default=4, env="WORKER_COUNT")

    # Redis配置
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")

    # 数据库配置
    DATABASE_URL: str = Field(default="sqlite:///./data/mms.db", env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")

    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="./logs/mms.log", env="LOG_FILE")
    LOG_ROTATION: str = Field(default="1 day", env="LOG_ROTATION")
    LOG_RETENTION: str = Field(default="30 days", env="LOG_RETENTION")

    # 安全配置
    SECRET_KEY: str = Field(
        default="mms-secret-key-change-in-production", env="SECRET_KEY"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS"
    )

    # 仿真引擎配置
    MAX_SIMULATION_TIME: int = Field(default=300, env="MAX_SIMULATION_TIME")  # 秒
    MAX_CONCURRENT_SIMULATIONS: int = Field(
        default=10, env="MAX_CONCURRENT_SIMULATIONS"
    )
    DEFAULT_SLIPPAGE: float = Field(default=0.001, env="DEFAULT_SLIPPAGE")
    DEFAULT_FILL_PROBABILITY: float = Field(
        default=0.95, env="DEFAULT_FILL_PROBABILITY"
    )

    # 数据源配置
    API_FACTORY_URL: str = Field(
        default="http://api-factory:8080", env="API_FACTORY_URL"
    )
    API_TIMEOUT: int = Field(default=30, env="API_TIMEOUT")

    # 报告配置
    REPORTS_DIR: str = Field(default="./reports", env="REPORTS_DIR")
    REPORT_BASE_URL: str = Field(
        default="http://mms:50051/reports", env="REPORT_BASE_URL"
    )

    # 监控配置
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")

    # 缓存配置
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 秒
    MARKET_DATA_CACHE_TTL: int = Field(default=300, env="MARKET_DATA_CACHE_TTL")  # 秒

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v):
        """验证应用环境"""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"APP_ENV must be one of {allowed_envs}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """验证日志级别"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of {allowed_levels}")
        return v.upper()

    @field_validator("WORKER_COUNT")
    @classmethod
    def validate_worker_count(cls, v):
        """验证工作进程数量"""
        if v < 1 or v > 20:
            raise ValueError("WORKER_COUNT must be between 1 and 20")
        return v

    @field_validator("DEFAULT_SLIPPAGE")
    @classmethod
    def validate_slippage(cls, v):
        """验证默认滑点"""
        if v < 0 or v > 0.1:
            raise ValueError("DEFAULT_SLIPPAGE must be between 0 and 0.1")
        return v

    @field_validator("DEFAULT_FILL_PROBABILITY")
    @classmethod
    def validate_fill_probability(cls, v):
        """验证默认成交概率"""
        if v < 0 or v > 1:
            raise ValueError("DEFAULT_FILL_PROBABILITY must be between 0 and 1")
        return v

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.APP_ENV == "production"

    @property
    def database_path(self) -> str:
        """获取数据库文件路径"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite:///", "")
        return ""

    def get_redis_config(self) -> dict:
        """获取Redis配置"""
        return {
            "url": self.REDIS_URL,
            "db": self.REDIS_DB,
            "password": self.REDIS_PASSWORD,
            "max_connections": self.REDIS_MAX_CONNECTIONS,
            "decode_responses": True,
        }

    def get_zmq_config(self) -> dict:
        """获取ZeroMQ配置"""
        return {
            "frontend_port": self.FRONTEND_PORT,
            "backend_port": self.BACKEND_PORT,
            "worker_count": self.WORKER_COUNT,
        }

    class Config:
        """Pydantic配置"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量


# 创建全局配置实例
settings = Settings()


# 环境特定配置
if settings.APP_ENV == "development":
    settings.DEBUG = True
    settings.LOG_LEVEL = "DEBUG"
    settings.DATABASE_ECHO = True
elif settings.APP_ENV == "production":
    settings.DEBUG = False
    settings.LOG_LEVEL = "INFO"
    settings.DATABASE_ECHO = False


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def create_directories():
    """创建必要的目录"""
    directories = [
        "./data",
        "./logs",
        "./reports",
        os.path.dirname(settings.LOG_FILE),
        os.path.dirname(settings.database_path) if settings.database_path else "./data",
    ]

    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


# 在导入时创建目录
create_directories()
