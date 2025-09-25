"""配置管理器模块

提供多环境配置加载、环境变量替换、配置验证等功能。
支持开发、测试、生产环境的配置管理。
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from .environment import EnvironmentConfig, Environment


class ConfigManager:
    """配置管理器

    负责加载和管理应用程序配置，支持多环境配置和环境变量替换。
    """

    def __init__(
        self, environment: Optional[str] = None, config_dir: Optional[Path] = None
    ):
        """初始化配置管理器

        Args:
            environment: 环境名称 (development/staging/production)
            config_dir: 配置文件目录
        """
        # 环境配置
        self.env_config = EnvironmentConfig(environment)
        self.environment = self.env_config.environment.value

        # 配置目录
        if config_dir is None:
            # 默认配置目录为当前文件所在目录
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = Path(config_dir)

        if not self.config_dir.exists():
            raise FileNotFoundError(f"配置目录不存在: {self.config_dir}\n" f"请确保配置目录存在")

        # 配置缓存
        self._config_cache: Dict[str, Any] = {}
        self._loaded = False

        # 加载配置
        self._load_config()

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置数据（用于测试兼容性）"""
        return self._config_cache

    def _load_config(self) -> None:
        """加载配置文件"""
        config_file = self.env_config.get_config_file_path()

        if not config_file.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {config_file}\n" f"请确保存在 {config_file.name} 配置文件"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            # 替换环境变量
            self._config_cache = self._replace_env_vars(raw_config)
            self._loaded = True

            print(f"✓ 配置加载成功: {self.environment} 环境")

        except yaml.YAMLError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"配置加载失败: {e}")

    def _replace_env_vars(self, config: Any) -> Any:
        """递归替换配置中的环境变量

        支持格式：${VAR_NAME} 或 ${VAR_NAME:default_value}
        """
        if config is None:
            return None
        elif isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif (
            isinstance(config, str) and config.startswith("${") and config.endswith("}")
        ):
            # 提取环境变量名和默认值
            var_expr = config[2:-1]  # 移除 ${ 和 }

            if ":" in var_expr:
                var_name, default_value = var_expr.split(":", 1)
                has_default = True
            else:
                var_name, default_value = var_expr, None
                has_default = False

            # 获取环境变量值
            env_value = os.getenv(var_name.strip())
            if env_value is not None and str(env_value) != "":
                return env_value
            elif has_default:
                # 如果有冒号分隔符，说明提供了默认值（即使是空字符串）
                return default_value if default_value is not None else ""
            else:
                # 降级处理：未设置且无默认值时返回空字符串并提示警告，避免在可选模块导致启动失败
                print(f"⚠️  环境变量 {var_name} 未设置且无默认值，已降级为空字符串。若该变量为必需项，请在环境中显式设置。")
                return ""
        else:
            return config

    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key_path: 配置键路径，支持点号分隔 (如: 'zmq.publisher.host')
            default: 默认值

        Returns:
            配置值
        """
        if not self._loaded:
            raise RuntimeError("配置未加载")

        keys = key_path.split(".")
        value = self._config_cache

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_config(self, key_path: str, default: Any = None) -> Any:
        """获取配置值（兼容性方法）

        Args:
            key_path: 配置键路径
            default: 默认值

        Returns:
            配置值
        """
        return self.get(key_path, default)

    def get_zmq_config(self) -> Dict[str, Any]:
        """获取ZeroMQ配置"""
        return self.get("zmq", {})

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        return self.get("redis", {})

    def get_sqlite_config(self) -> Dict[str, Any]:
        """获取SQLite配置"""
        return self.get("sqlite", {})

    def get_scrapy_config(self) -> Dict[str, Any]:
        """获取Scrapy配置"""
        return self.get("scrapy", {})

    def get_telegram_config(self) -> Dict[str, Any]:
        """获取Telegram配置"""
        return self.get("telegram", {})

    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.get("api", {})

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get("logging", {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self.get("monitoring", {})

    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.get("security", {})

    def get_data_processing_config(self) -> Dict[str, Any]:
        """获取数据处理配置"""
        return self.get("data_processing", {})

    def is_debug(self) -> bool:
        """是否为调试模式"""
        return self.get("debug", False)

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == Environment.DEVELOPMENT.value

    def is_staging(self) -> bool:
        """是否为测试环境"""
        return self.environment == Environment.STAGING.value

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == Environment.PRODUCTION.value

    def validate_config(self) -> bool:
        """验证配置完整性

        Returns:
            配置是否有效
        """
        required_sections = [
            "zmq",
            "redis",
            "sqlite",
            "scrapy",
            "telegram",
            "api",
            "logging",
        ]

        missing_sections = []
        for section in required_sections:
            if self.get(section) is None:
                missing_sections.append(section)

        if missing_sections:
            print(f"⚠️  缺少配置节: {', '.join(missing_sections)}")
            return False

        print("✓ 配置验证通过")
        return True

    def reload_config(self) -> None:
        """重新加载配置"""
        self._config_cache.clear()
        self._loaded = False
        self._load_config()
        print("✓ 配置重新加载完成")

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config_cache.copy()

    def __str__(self) -> str:
        """字符串表示"""
        return f"ConfigManager(environment={self.environment}, loaded={self._loaded})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"ConfigManager("
            f"environment='{self.environment}', "
            f"config_file='{self.env_config.get_config_file_path().name}', "
            f"loaded={self._loaded}"
            f")"
        )


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(environment: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例（单例模式）

    Args:
        environment: 环境名称

    Returns:
        配置管理器实例
    """
    global _config_manager

    if _config_manager is None or (
        environment and _config_manager.environment != environment
    ):
        _config_manager = ConfigManager(environment)

    return _config_manager


def reset_config_manager() -> None:
    """重置配置管理器（主要用于测试）"""
    global _config_manager
    _config_manager = None
