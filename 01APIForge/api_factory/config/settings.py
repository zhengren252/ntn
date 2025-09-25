#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Factory Module - 配置管理
全局规范：三环境隔离、数据隔离、环境变量管理
"""

import os
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from datetime import datetime, timezone


class ZMQConfig(BaseSettings):
    """ZeroMQ配置 - 高并发通信"""

    publisher_port: int = Field(default=5555, json_schema_extra={"env": "ZMQ_PUBLISHER_PORT"})
    subscriber_port: int = Field(default=5556, json_schema_extra={"env": "ZMQ_SUBSCRIBER_PORT"})
    request_port: int = Field(default=5557, json_schema_extra={"env": "ZMQ_REQUEST_PORT"})
    reply_port: int = Field(default=5558, json_schema_extra={"env": "ZMQ_REPLY_PORT"})
    bind_address: str = Field(default="tcp://*", json_schema_extra={"env": "ZMQ_BIND_ADDRESS"})
    connect_address: str = Field(default="tcp://127.0.0.1", json_schema_extra={"env": "ZMQ_CONNECT_ADDRESS"})


class RedisConfig(BaseSettings):
    """Redis配置 - 缓存与消息队列"""
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 10


class SQLiteConfig(BaseSettings):
    """SQLite配置 - 本地数据存储"""

    database_path: str = Field(default="./data/api_factory.db", json_schema_extra={"env": "SQLITE_DB_PATH"})
    backup_path: str = Field(default="./data/backups", json_schema_extra={"env": "SQLITE_BACKUP_PATH"})


class SupabaseConfig(BaseSettings):
    """Supabase配置 - 云数据库"""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    url: str = Field(default="", json_schema_extra={"env": "SUPABASE_URL"})
    key: str = Field(default="", json_schema_extra={"env": "SUPABASE_ANON_KEY"})
    service_role_key: str = Field(default="", json_schema_extra={"env": "SUPABASE_SERVICE_ROLE_KEY"})
    table_name: str = Field(default="api_keys", json_schema_extra={"env": "SUPABASE_API_KEYS_TABLE"})


class AuthConfig(BaseSettings):
    """认证配置 - 安全管理"""

    secret_key: str = Field(
        default="your-secret-key-change-in-production", json_schema_extra={"env": "AUTH_SECRET_KEY"}
    )
    algorithm: str = Field(default="HS256", json_schema_extra={"env": "AUTH_ALGORITHM"})
    access_token_expire_minutes: int = Field(default=30, json_schema_extra={"env": "AUTH_ACCESS_TOKEN_EXPIRE"})
    refresh_token_expire_days: int = Field(default=7, json_schema_extra={"env": "AUTH_REFRESH_TOKEN_EXPIRE"})
    # 加密配置
    encryption_key: str = Field(default="", json_schema_extra={"env": "ENCRYPTION_KEY"})
    encryption_algorithm: str = Field(default="AES-256-GCM", json_schema_extra={"env": "ENCRYPTION_ALGORITHM"})


class APIConfig(BaseSettings):
    """API配置 - 限流和熔断"""

    rate_limit_per_minute: int = Field(default=60, json_schema_extra={"env": "API_RATE_LIMIT_PER_MINUTE"})
    circuit_breaker_threshold: int = Field(
        default=5, json_schema_extra={"env": "API_CIRCUIT_BREAKER_THRESHOLD"}
    )
    circuit_breaker_timeout: int = Field(default=60, json_schema_extra={"env": "API_CIRCUIT_BREAKER_TIMEOUT"})


class Settings(BaseSettings):
    """主配置类 - 三环境隔离"""

    # 基础配置
    app_name: str = Field(default="API Factory Module", json_schema_extra={"env": "APP_NAME"})
    environment: str = Field(default="development", json_schema_extra={"env": "ENVIRONMENT"})
    debug: bool = Field(default=True, json_schema_extra={"env": "DEBUG"})
    host: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})

    # 数据隔离配置
    data_isolation_enabled: bool = Field(default=True, json_schema_extra={"env": "DATA_ISOLATION_ENABLED"})
    tenant_id_header: str = Field(default="X-Tenant-ID", json_schema_extra={"env": "TENANT_ID_HEADER"})

    # 组件配置
    zmq_config: ZMQConfig = Field(default_factory=ZMQConfig)
    redis_config: RedisConfig = Field(default_factory=RedisConfig)
    sqlite_config: SQLiteConfig = Field(default_factory=SQLiteConfig)
    supabase_config: SupabaseConfig = Field(default_factory=SupabaseConfig)
    auth_config: AuthConfig = Field(default_factory=AuthConfig)
    api_config: APIConfig = Field(default_factory=APIConfig)

    # Docker配置
    docker_enabled: bool = Field(default=False, json_schema_extra={"env": "DOCKER_ENABLED"})
    docker_network: str = Field(default="api_factory_network", json_schema_extra={"env": "DOCKER_NETWORK"})

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # 忽略额外的环境变量
    )

    def get_environment_config(self) -> Dict[str, Any]:
        """获取环境特定配置"""
        if self.environment == "production":
            return {
                "debug": False,
                "log_level": "WARNING",
                "rate_limit_per_minute": 120,
                "circuit_breaker_threshold": 3,
            }
        elif self.environment == "staging":
            return {
                "debug": False,
                "log_level": "INFO",
                "rate_limit_per_minute": 100,
                "circuit_breaker_threshold": 4,
            }
        else:  # development
            return {
                "debug": True,
                "log_level": "DEBUG",
                "rate_limit_per_minute": 60,
                "circuit_breaker_threshold": 5,
            }

    def get_database_config(self) -> Dict[str, str]:
        """获取数据库配置 - 环境隔离"""
        base_path = self.sqlite_config.database_path
        if self.environment == "production":
            return {
                "database_path": base_path.replace(".db", "_prod.db"),
                "backup_enabled": True,
            }
        elif self.environment == "staging":
            return {
                "database_path": base_path.replace(".db", "_staging.db"),
                "backup_enabled": True,
            }
        else:
            return {
                "database_path": base_path.replace(".db", "_dev.db"),
                "backup_enabled": False,
            }

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置 - 环境隔离"""
        base_db = self.redis_config.db
        if self.environment == "production":
            return {**self.redis_config.model_dump(), "db": base_db + 0}
        elif self.environment == "staging":
            return {**self.redis_config.model_dump(), "db": base_db + 1}
        else:
            return {**self.redis_config.model_dump(), "db": base_db + 2}

    def get_current_timestamp(self) -> str:
        """获取当前时间戳 - ISO格式"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例 - 单例模式"""
    # 确保所有子配置类正确加载环境变量
    settings = Settings()
    
    # 重新初始化子配置以确保环境变量正确加载
    settings.zmq_config = ZMQConfig()
    settings.redis_config = RedisConfig()
    settings.sqlite_config = SQLiteConfig()
    settings.supabase_config = SupabaseConfig()
    settings.auth_config = AuthConfig()
    settings.api_config = APIConfig()
    
    return settings


# 环境变量模板
ENV_TEMPLATE = """
# API Factory Module 环境配置
# 三环境隔离：development/staging/production

# 基础配置
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# ZeroMQ配置
ZMQ_PUBLISHER_PORT=5555
ZMQ_SUBSCRIBER_PORT=5556
ZMQ_REQUEST_PORT=5557
ZMQ_REPLY_PORT=5558

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# SQLite配置
SQLITE_DB_PATH=./data/api_factory.db

# Supabase配置
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_API_KEYS_TABLE=api_keys

# 认证配置
AUTH_SECRET_KEY=your-secret-key-change-in-production
AUTH_ACCESS_TOKEN_EXPIRE=30
ENCRYPTION_KEY=your-32-byte-encryption-key-change-in-production
ENCRYPTION_ALGORITHM=AES-256-GCM

# API配置
API_RATE_LIMIT_PER_MINUTE=60
API_CIRCUIT_BREAKER_THRESHOLD=5

# 数据隔离
DATA_ISOLATION_ENABLED=true
TENANT_ID_HEADER=X-Tenant-ID

# Docker配置
DOCKER_ENABLED=false
DOCKER_NETWORK=api_factory_network
"""
