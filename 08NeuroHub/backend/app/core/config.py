"""总控模块核心配置

核心配置模块

严格按照数据隔离与环境管理规范V1.0实现：
- 三环境隔离：development, staging, production
- 严禁硬编码敏感信息
- 分环境配置文件
- 密钥通过环境变量注入
"""

import os
import yaml
from typing import Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类 - 支持YAML配置文件和环境隔离"""

    # 应用基础配置
    app_name: str = Field(
        default="NeuroTrade Nexus - Master Control Module"
    )
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True)

    # 数据库配置 - 按环境隔离
    database_url: str = Field(default="")

    # Redis配置 - 按环境隔离
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(
        default=None, env="REDIS_PASSWORD"
    )

    # ZeroMQ配置 - 按环境隔离端口
    zmq_pub_port: int = Field(default=5555, env="ZMQ_PUB_PORT")
    zmq_sub_port: int = Field(default=5556, env="ZMQ_SUB_PORT")
    zmq_router_port: int = Field(default=5557, env="ZMQ_ROUTER_PORT")
    zmq_dealer_port: int = Field(default=5558, env="ZMQ_DEALER_PORT")

    # API配置
    api_v1_prefix: str = Field(default="/api/v1")
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )

    # 安全配置
    access_token_expire_minutes: int = Field(default=30)

    # API密钥 - 通过环境变量注入
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    api_key: Optional[str] = Field(default=None, env="API_KEY")

    # 日志配置
    log_level: str = Field(default="DEBUG")
    log_file: str = Field(default="logs/master_control.log")

    # 动态配置存储
    _config_data: Dict[str, Any] = {}

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_environment_config()
        self._validate_environment()

    def _load_environment_config(self):
        """加载环境特定配置"""
        config_file = f"config/{self.app_env}.yaml"
        base_config_file = "config/base.yaml"

        # 加载基础配置
        if os.path.exists(base_config_file):
            with open(base_config_file, 'r', encoding='utf-8') as f:
                base_config = yaml.safe_load(f)
                self._apply_config(base_config)

        # 加载环境特定配置
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                env_config = yaml.safe_load(f)
                self._apply_config(env_config)

        # 设置环境特定的数据库路径
        if not self.database_url:
            db_name = f"{self.app_env}.db"
            self.database_url = f"sqlite:///data/{db_name}"

        # 设置环境特定的Redis数据库
        if self.app_env == "development":
            self.redis_db = 0
            self.debug = True
            self.log_level = "DEBUG"
            # 开发环境ZMQ端口基础值
            self.zmq_pub_port = 5755
            self.zmq_sub_port = 5756
            self.zmq_router_port = 5757
            self.zmq_dealer_port = 5758
        elif self.app_env == "staging":
            self.redis_db = 1
            self.debug = False
            self.log_level = "INFO"
            # 测试环境ZMQ端口基础值
            self.zmq_pub_port = 5655
            self.zmq_sub_port = 5656
            self.zmq_router_port = 5657
            self.zmq_dealer_port = 5658
        elif self.app_env == "production":
            self.redis_db = 2
            self.debug = False
            self.log_level = "INFO"
            # 生产环境ZMQ端口基础值
            self.zmq_pub_port = 5555
            self.zmq_sub_port = 5556
            self.zmq_router_port = 5557
            self.zmq_dealer_port = 5558

    def _apply_config(self, config: dict):
        """应用配置字典到设置"""
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _validate_environment(self):
        """验证环境配置"""
        valid_envs = ["development", "staging", "production"]
        if self.app_env not in valid_envs:
            raise ValueError(
                f"无效的环境配置: {self.app_env}，必须是: {valid_envs}"
            )

        # 生产环境必须配置密钥
        if self.app_env == "production":
            if self.secret_key == "dev-secret-key":
                raise ValueError("生产环境必须配置SECRET_KEY环境变量")
            if not self.api_key:
                raise ValueError("生产环境必须配置API_KEY环境变量")

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"

    @property
    def is_staging(self) -> bool:
        """是否为测试环境"""
        return self.app_env == "staging"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"

    @property
    def database_path(self) -> str:
        """数据库文件路径"""
        return self.database_url.replace('sqlite:///', '')

    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_mock_data_enabled(self) -> bool:
        """是否启用模拟数据 - 仅限开发环境"""
        return self.app_env == "development"

    @property
    def zmq_module_ports(self) -> dict:
        """各模组ZMQ端口配置"""
        base_port = self.zmq_pub_port
        return {
            "master_control": base_port,
            "data_collection": base_port + 10,
            "signal_generation": base_port + 20,
            "execution_engine": base_port + 30,
            "risk_management": base_port + 40,
            "performance_analysis": base_port + 50,
            "market_analysis": base_port + 60
        }

    @property
    def zmq_sub_ports(self) -> list:
        """ZMQ订阅端口列表 - 连接到其他模组的发布端口"""
        ports = []
        for module, base_port in self.zmq_module_ports.items():
            if module != "master_control":  # 不连接自己
                ports.append(base_port)  # 其他模组的发布端口
        return ports

    @property
    def zmq_module_configs(self) -> dict:
        """各模组完整ZMQ配置"""
        configs = {}
        for module, base_port in self.zmq_module_ports.items():
            configs[module] = {
                "pub_port": base_port,
                "sub_port": base_port + 1,
                "router_port": base_port + 2,
                "dealer_port": base_port + 3
            }
        return configs


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()


# 导出配置实例
settings = get_settings()