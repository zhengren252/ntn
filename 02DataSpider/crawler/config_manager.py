# 配置管理器
# 严格遵循：数据隔离与环境管理规范 (V1.0)

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigManager:
    """配置管理器 - 实现三环境隔离和密钥注入"""

    def __init__(self):
        self.app_env = os.getenv("APP_ENV", "development")
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config = self._load_config()

        # 验证环境
        if self.app_env not in ["development", "staging", "production"]:
            raise ValueError(f"无效的环境变量 APP_ENV: {self.app_env}")

        logger.info(f"配置管理器初始化完成，当前环境: {self.app_env}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            # 加载基础配置
            base_config_path = self.config_dir / "base.yaml"
            with open(base_config_path, "r", encoding="utf-8") as f:
                base_config = yaml.safe_load(f)

            # 加载环境特定配置
            env_config_path = self.config_dir / f"{self.app_env}.yaml"
            if env_config_path.exists():
                with open(env_config_path, "r", encoding="utf-8") as f:
                    env_config = yaml.safe_load(f)
                # 合并配置
                base_config.update(env_config)

            # 注入环境变量
            self._inject_env_vars(base_config)

            return base_config

        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise

    def _inject_env_vars(self, config: Dict[str, Any]) -> None:
        """注入环境变量中的敏感信息"""
        # Telegram API配置
        if "telegram" in config:
            config["telegram"]["api_id"] = os.getenv("TELEGRAM_API_ID")
            config["telegram"]["api_hash"] = os.getenv("TELEGRAM_API_HASH")
            config["telegram"]["phone_number"] = os.getenv("TELEGRAM_PHONE")
            config["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")

        # Redis密码
        if "redis" in config:
            config["redis"]["password"] = os.getenv("REDIS_PASSWORD")

        # 代理配置
        proxy_urls = os.getenv("PROXY_URLS")
        if proxy_urls:
            config["scraper"]["proxy_urls"] = proxy_urls.split(",")

        # 告警Webhook
        webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        if webhook_url and "error_handling" in config:
            config["error_handling"]["alert_webhook_url"] = webhook_url

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_database_config(self) -> Dict[str, Any]:
        """获取当前环境的数据库配置"""
        sqlite_config = self.get("sqlite", {})
        db_files = sqlite_config.get("database_files", {})

        return {
            "sqlite_file": db_files.get(self.app_env, "data/default.db"),
            "redis_db": self.get(f"redis.db.{self.app_env}", 0),
            "redis_host": self.get("redis.host", "localhost"),
            "redis_port": self.get("redis.port", 6379),
            "redis_password": self.get("redis.password"),
        }

    def get_zmq_config(self) -> Dict[str, Any]:
        """获取ZeroMQ配置"""
        return {
            "publisher_port": self.get("zmq.publisher_port", 5555),
            "request_port": self.get("zmq.request_port", 5556),
            "topics": self.get("zmq.topics", {}),
        }

    def get_telegram_config(self) -> Dict[str, Any]:
        """获取Telegram配置"""
        return self.get("telegram", {})

    def get_scraper_config(self) -> Dict[str, Any]:
        """获取爬虫配置"""
        return self.get("scraper", {})

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.app_env == "development"

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.app_env == "production"

    def get_mock_data(self) -> Optional[Dict[str, Any]]:
        """获取Mock数据（仅开发环境）"""
        if self.is_development():
            return self.get("mock_data")
        return None

    def validate_config(self) -> bool:
        """验证配置完整性"""
        required_keys = [
            "module.id",
            "module.version",
            "zmq.publisher_port",
            "redis.host",
        ]

        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"缺少必需的配置项: {key}")
                return False

        # 生产环境额外验证
        if self.is_production():
            sensitive_keys = ["telegram.api_id", "telegram.api_hash"]
            for key in sensitive_keys:
                if not self.get(key):
                    logger.warning(f"生产环境缺少敏感配置: {key}")

        return True


# 全局配置实例
config = ConfigManager()
