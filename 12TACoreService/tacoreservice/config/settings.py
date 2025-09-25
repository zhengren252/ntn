"""Configuration settings for TACoreService."""

import os
from typing import Optional
from pydantic import Field, ConfigDict

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings

    SettingsConfigDict = ConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Service Configuration
    service_name: str = "TACoreService"
    debug: bool = False

    # ZeroMQ Configuration
    zmq_frontend_port: int = 5555
    zmq_backend_port: int = 5556
    zmq_bind_address: str = "*"
    zmq_backend_host: str = "tacoreservice"

    # HTTP API Configuration
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    # Redis Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # SQLite Configuration
    sqlite_db_path: str = "data/tacoreservice.db"

    # Worker Configuration
    worker_count: int = 4
    worker_timeout: int = 30

    # TradingAgents-CN Configuration
    tradingagents_path: str = "./TradingAgents-CN"

    # Monitoring Configuration
    health_check_interval: int = 30
    metrics_retention_days: int = 7
    metrics_collection_interval: int = 5

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="", case_sensitive=False
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
