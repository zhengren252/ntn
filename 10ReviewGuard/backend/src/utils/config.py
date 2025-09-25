#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - 配置管理
"""

import os
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    """应用配置"""
    
    # 数据库配置
    database_url: str = "sqlite:///reviewguard.db"
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # ZeroMQ配置
    zmq_sub_endpoint: str = "tcp://localhost:5555"  # 订阅optimizer.pool.trading
    zmq_pub_endpoint: str = "tcp://*:5556"          # 发布review.pool.approved
    
    # JWT配置
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24小时
    
    # 服务器配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False
    
    # 审核配置
    auto_review_enabled: bool = True
    manual_review_timeout_hours: int = 24
    max_pending_reviews: int = 1000
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    def __post_init__(self):
        """从环境变量加载配置"""
        # 数据库配置
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        
        # Redis配置
        self.redis_host = os.getenv("REDIS_HOST", self.redis_host)
        self.redis_port = int(os.getenv("REDIS_PORT", self.redis_port))
        self.redis_password = os.getenv("REDIS_PASSWORD", self.redis_password)
        self.redis_db = int(os.getenv("REDIS_DB", self.redis_db))
        
        # ZeroMQ配置
        self.zmq_sub_endpoint = os.getenv("ZMQ_SUB_ENDPOINT", self.zmq_sub_endpoint)
        self.zmq_pub_endpoint = os.getenv("ZMQ_PUB_ENDPOINT", self.zmq_pub_endpoint)
        
        # JWT配置
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", self.jwt_secret_key)
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", self.jwt_algorithm)
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", self.jwt_expire_minutes))
        
        # 服务器配置
        self.server_host = os.getenv("SERVER_HOST", self.server_host)
        self.server_port = int(os.getenv("SERVER_PORT", self.server_port))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # 审核配置
        self.auto_review_enabled = os.getenv("AUTO_REVIEW_ENABLED", "true").lower() == "true"
        self.manual_review_timeout_hours = int(os.getenv("MANUAL_REVIEW_TIMEOUT_HOURS", self.manual_review_timeout_hours))
        self.max_pending_reviews = int(os.getenv("MAX_PENDING_REVIEWS", self.max_pending_reviews))
        
        # 日志配置
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_file = os.getenv("LOG_FILE", self.log_file)


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()


# 环境变量配置示例
ENV_EXAMPLE = """
# ReviewGuard 环境变量配置示例

# 数据库配置
DATABASE_URL=sqlite:///reviewguard.db

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# ZeroMQ配置
ZMQ_SUB_ENDPOINT=tcp://localhost:5555
ZMQ_PUB_ENDPOINT=tcp://*:5556

# JWT配置
JWT_SECRET_KEY=your-very-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false

# 审核配置
AUTO_REVIEW_ENABLED=true
MANUAL_REVIEW_TIMEOUT_HOURS=24
MAX_PENDING_REVIEWS=1000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=
"""


def create_env_file(file_path: str = ".env"):
    """创建环境变量配置文件"""
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(ENV_EXAMPLE)
        print(f"Environment file created: {file_path}")
    else:
        print(f"Environment file already exists: {file_path}")


if __name__ == "__main__":
    # 创建示例配置文件
    create_env_file()
    
    # 显示当前配置
    settings = get_settings()
    print("Current settings:")
    print(f"Database URL: {settings.database_url}")
    print(f"Redis: {settings.redis_host}:{settings.redis_port}")
    print(f"ZMQ SUB: {settings.zmq_sub_endpoint}")
    print(f"ZMQ PUB: {settings.zmq_pub_endpoint}")
    print(f"Server: {settings.server_host}:{settings.server_port}")