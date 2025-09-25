#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略优化模组设置文件
统一管理所有配置项，严格遵循三环境隔离规范
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """
    应用设置类

    严格遵循NeuroTrade Nexus核心设计理念：
    1. 三环境隔离 (development/staging/production)
    2. 数据隔离与环境管理
    3. 无硬编码配置
    4. 环境变量注入
    """

    # 环境配置
    environment: str = Field(default="development", env="NTN_ENVIRONMENT")
    debug: bool = Field(default=True, env="NTN_DEBUG")
    version: str = "1.0.0"

    # 服务配置
    host: str = Field(default="0.0.0.0", env="NTN_HOST")
    port: int = Field(default=8000, env="NTN_PORT")

    # ZeroMQ配置
    zmq_scanner_endpoint: str = Field(
        default="tcp://localhost:5555", env="NTN_ZMQ_SCANNER_ENDPOINT"
    )
    zmq_optimizer_endpoint: str = Field(
        default="tcp://localhost:5556", env="NTN_ZMQ_OPTIMIZER_ENDPOINT"
    )
    zmq_api_factory_endpoint: str = Field(
        default="tcp://localhost:5557", env="NTN_ZMQ_API_FACTORY_ENDPOINT"
    )
    
    # 外部服务端点配置
    api_forge_base_url: str = Field(
        default="http://localhost:8001", env="NTN_API_FORGE_BASE_URL"
    )
    api_forge_api_key: Optional[str] = Field(
        default=None, env="NTN_API_FORGE_API_KEY"
    )
    mms_base_url: str = Field(
        default="http://localhost:8002", env="NTN_MMS_BASE_URL"
    )
    mms_api_key: Optional[str] = Field(
        default=None, env="NTN_MMS_API_KEY"
    )

    # 数据库配置
    sqlite_url: str = Field(default="", env="NTN_SQLITE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", env="NTN_REDIS_URL")

    # API密钥配置
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")

    # 回测配置
    initial_capital: float = Field(default=100000.0, env="NTN_INITIAL_CAPITAL")
    commission_rate: float = Field(default=0.001, env="NTN_COMMISSION_RATE")
    max_concurrent_backtests: int = Field(default=4, env="NTN_MAX_CONCURRENT_BACKTESTS")

    # 优化配置
    genetic_population_size: int = Field(default=50, env="NTN_GENETIC_POPULATION_SIZE")
    genetic_generations: int = Field(default=20, env="NTN_GENETIC_GENERATIONS")
    max_optimization_time: int = Field(default=3600, env="NTN_MAX_OPTIMIZATION_TIME")

    # 风险控制配置
    max_drawdown_threshold: float = Field(
        default=0.05, env="NTN_MAX_DRAWDOWN_THRESHOLD"
    )
    min_sharpe_ratio: float = Field(default=1.0, env="NTN_MIN_SHARPE_RATIO")
    min_confidence_threshold: float = Field(
        default=0.6, env="NTN_MIN_CONFIDENCE_THRESHOLD"
    )

    # 日志配置
    log_level: str = Field(default="INFO", env="NTN_LOG_LEVEL")
    log_file: str = Field(default="", env="NTN_LOG_FILE")

    class Config:
        """Pydantic配置类，用于设置环境变量文件和编码选项。"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_environment_specific_defaults()

    def _setup_environment_specific_defaults(self):
        """根据环境设置特定的默认值"""
        if not self.sqlite_url:
            db_path = PROJECT_ROOT / "data" / self.environment / "optimizer.db"
            self.sqlite_url = f"sqlite:///{db_path}"

        if not self.log_file:
            log_path = PROJECT_ROOT / "logs" / self.environment / "optimizer.log"
            self.log_file = str(log_path)

        # 根据环境调整配置
        if self.environment == "development":
            self.debug = True
            self.log_level = "DEBUG"
            self.max_concurrent_backtests = 4
        elif self.environment == "staging":
            self.debug = False
            self.log_level = "INFO"
            self.max_concurrent_backtests = 8
        elif self.environment == "production":
            self.debug = False
            self.log_level = "WARNING"
            self.max_concurrent_backtests = 16

    @property
    def database_url(self) -> str:
        """获取数据库URL"""
        return self.sqlite_url

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"

    def get_data_path(self, filename: str) -> Path:
        """获取数据文件路径"""
        return PROJECT_ROOT / "data" / self.environment / filename

    def get_log_path(self, filename: str) -> Path:
        """获取日志文件路径"""
        return PROJECT_ROOT / "logs" / self.environment / filename

    def ensure_directories(self):
        """确保必要的目录存在"""
        # 为当前环境创建目录
        directories = [
            PROJECT_ROOT / "data" / self.environment,
            PROJECT_ROOT / "logs" / self.environment,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_all_environment_directories(self):
        """确保所有环境的目录都存在"""
        environments = ["development", "staging", "production", "test"]

        for env in environments:
            directories = [
                PROJECT_ROOT / "data" / env,
                PROJECT_ROOT / "logs" / env,
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

    def validate_environment_setup(self):
        """验证环境配置完整性"""
        required_dirs = [
            PROJECT_ROOT / "data" / self.environment,
            PROJECT_ROOT / "logs" / self.environment,
        ]

        missing_dirs = []
        for dir_path in required_dirs:
            if not dir_path.exists():
                missing_dirs.append(str(dir_path))

        if missing_dirs:
            raise EnvironmentError(f"Required directories missing: {missing_dirs}")

        return True


@lru_cache()
def get_settings() -> Settings:
    """获取设置实例（单例模式）"""
    settings = Settings()
    # 确保当前环境目录存在
    settings.ensure_directories()
    # 确保所有环境目录都存在（符合三环境隔离规范）
    settings.ensure_all_environment_directories()
    # 验证环境配置完整性
    settings.validate_environment_setup()
    return settings
