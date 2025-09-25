# 配置管理器
# 严格遵循全局规范：数据隔离与环境管理规范

import os
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)


class ConfigManager:
    """配置管理器 - 负责环境隔离和配置文件管理"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = (
            Path(config_dir)
            if config_dir
            else Path(__file__).parent.parent.parent / "config"
        )
        self.app_env = os.getenv("APP_ENV", "development")
        self._config_cache: Dict[str, Any] = {}

        # 验证环境变量
        if self.app_env not in ["development", "staging", "production"]:
            raise ValueError(
                f"Invalid APP_ENV: {self.app_env}. Must be one of: development, staging, production"
            )

        logger.info(
            "ConfigManager initialized",
            app_env=self.app_env,
            config_dir=str(self.config_dir),
        )

    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """加载配置文件

        Args:
            force_reload: 是否强制重新加载配置

        Returns:
            完整的配置字典
        """
        if not force_reload and self._config_cache:
            return self._config_cache

        try:
            # 加载基础配置
            base_config = self._load_yaml_file("base.yaml")

            # 加载环境特定配置
            env_config = self._load_yaml_file(f"{self.app_env}.yaml")

            # 合并配置
            merged_config = self._merge_configs(base_config, env_config)

            # 注入环境变量
            merged_config = self._inject_env_vars(merged_config)

            self._config_cache = merged_config
            logger.info("Configuration loaded successfully", env=self.app_env)

            return merged_config

        except Exception as e:
            logger.error("Failed to load configuration", error=str(e), env=self.app_env)
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键，支持点分隔的嵌套键如 'redis.host'
            default: 默认值

        Returns:
            配置值
        """
        config = self.load_config()

        # 支持嵌套键访问
        keys = key.split(".")
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"

    def is_staging(self) -> bool:
        """是否为预生产环境"""
        return self.app_env == "staging"

    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        file_path = self.config_dir / filename

        if not file_path.exists():
            logger.warning("Config file not found", file=str(file_path))
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                return content or {}
        except Exception as e:
            logger.error("Failed to load YAML file", file=str(file_path), error=str(e))
            raise

    def _merge_configs(
        self, base: Dict[str, Any], env: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并基础配置和环境配置"""
        merged = base.copy()

        def deep_merge(target: Dict, source: Dict):
            for key, value in source.items():
                if (
                    key in target
                    and isinstance(target[key], dict)
                    and isinstance(value, dict)
                ):
                    deep_merge(target[key], value)
                else:
                    target[key] = value

        deep_merge(merged, env)
        return merged

    def _inject_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """注入环境变量

        支持的环境变量：
        - REDIS_HOST, REDIS_PORT, REDIS_DB
        - ZMQ_PUBLISHER_PORT, ZMQ_SUBSCRIBER_PORT
        - API_FACTORY_URL
        - LOG_LEVEL
        """
        # Redis配置注入
        if "redis" in config:
            config["redis"]["host"] = os.getenv(
                "REDIS_HOST", config["redis"].get("host", "localhost")
            )
            config["redis"]["port"] = int(
                os.getenv("REDIS_PORT", config["redis"].get("port", 6379))
            )
            config["redis"]["db"] = int(
                os.getenv("REDIS_DB", config["redis"].get("db", 0))
            )

        # ZeroMQ配置注入
        if "zmq" in config:
            config["zmq"]["publisher_port"] = int(
                os.getenv(
                    "ZMQ_PUBLISHER_PORT", config["zmq"].get("publisher_port", 5555)
                )
            )
            config["zmq"]["subscriber_port"] = int(
                os.getenv(
                    "ZMQ_SUBSCRIBER_PORT", config["zmq"].get("subscriber_port", 5556)
                )
            )

        # API工厂URL注入
        if "api_factory" not in config:
            config["api_factory"] = {}
        config["api_factory"]["url"] = os.getenv(
            "API_FACTORY_URL", config["api_factory"].get("url", "http://localhost:8000")
        )

        # 日志级别注入
        if "logging" in config:
            config["logging"]["level"] = os.getenv(
                "LOG_LEVEL", config["logging"].get("level", "INFO")
            )

        return config

    def validate_config(self) -> bool:
        """验证配置完整性"""
        try:
            config = self.load_config()

            # 必需的配置项检查
            required_sections = ["scanner", "rules", "zmq", "redis", "logging"]

            for section in required_sections:
                if section not in config:
                    logger.error("Missing required config section", section=section)
                    return False

            # 规则配置检查
            if "three_high" not in config["rules"]:
                logger.error("Missing three_high rules configuration")
                return False

            if "black_horse" not in config["rules"]:
                logger.error("Missing black_horse rules configuration")
                return False

            logger.info("Configuration validation passed")
            return True

        except Exception as e:
            logger.error("Configuration validation failed", error=str(e))
            return False
