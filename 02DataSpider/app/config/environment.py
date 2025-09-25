# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - 环境配置管理
提供环境检测、验证和切换功能
"""

import os
import sys
from enum import Enum
from typing import Dict, List, Union, Optional
from pathlib import Path

# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)


class Environment(Enum):
    """环境枚举"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, env_str: str) -> "Environment":
        """从字符串创建环境枚举"""
        env_map = {
            "dev": cls.DEVELOPMENT,
            "development": cls.DEVELOPMENT,
            "test": cls.STAGING,
            "staging": cls.STAGING,
            "prod": cls.PRODUCTION,
            "production": cls.PRODUCTION,
        }

        env_str = env_str.lower().strip()
        if env_str in env_map:
            return env_map[env_str]

        raise ValueError(f"无效的环境名称: {env_str}\n" f"支持的环境: {list(env_map.keys())}")

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self == Environment.DEVELOPMENT

    def is_staging(self) -> bool:
        """是否为测试环境"""
        return self == Environment.STAGING

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self == Environment.PRODUCTION


class EnvironmentConfig:
    """环境配置类

    提供环境相关的配置和验证功能
    """

    def __init__(self, environment: Union[Environment, str] = None):
        """初始化环境配置

        Args:
            environment: 环境枚举或字符串，默认从环境变量获取
        """
        if isinstance(environment, str):
            self.environment = Environment.from_string(environment)
        elif isinstance(environment, Environment):
            self.environment = environment
        else:
            self.environment = self._detect_environment()
        self.project_root = Path(__file__).parent.parent.parent

        # 环境特定配置
        self._env_configs = {
            Environment.DEVELOPMENT: {
                "debug": True,
                "log_level": "DEBUG",
                "auto_reload": True,
                "strict_validation": False,
                "performance_monitoring": False,
                "security_checks": False,
            },
            Environment.STAGING: {
                "debug": False,
                "log_level": "INFO",
                "auto_reload": False,
                "strict_validation": True,
                "performance_monitoring": True,
                "security_checks": True,
            },
            Environment.PRODUCTION: {
                "debug": False,
                "log_level": "WARNING",
                "auto_reload": False,
                "strict_validation": True,
                "performance_monitoring": True,
                "security_checks": True,
            },
        }

    def _detect_environment(self) -> Environment:
        """自动检测运行环境"""
        # 从环境变量检测
        env_var = os.getenv("NTN_ENV", "development")

        try:
            return Environment.from_string(env_var)
        except ValueError:
            print(f"⚠️  无效的环境变量 NTN_ENV={env_var}，使用默认开发环境")
            return Environment.DEVELOPMENT

    def get_config(self, key: str, default=None):
        """获取环境特定配置

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        env_config = self._env_configs.get(self.environment, {})
        return env_config.get(key, default)

    def is_debug(self) -> bool:
        """是否启用调试模式"""
        return self.get_config("debug", False)

    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.get_config("log_level", "INFO")

    def is_auto_reload_enabled(self) -> bool:
        """是否启用自动重载"""
        return self.get_config("auto_reload", False)

    def is_strict_validation_enabled(self) -> bool:
        """是否启用严格验证"""
        return self.get_config("strict_validation", True)

    def is_performance_monitoring_enabled(self) -> bool:
        """是否启用性能监控"""
        return self.get_config("performance_monitoring", False)

    def is_security_checks_enabled(self) -> bool:
        """是否启用安全检查"""
        return self.get_config("security_checks", False)

    def get_data_dir(self) -> Path:
        """获取数据目录"""
        data_dir = self.project_root / "data"

        # 为不同环境创建独立的数据目录
        env_data_dir = data_dir / self.environment.value
        env_data_dir.mkdir(parents=True, exist_ok=True)

        return env_data_dir

    def get_log_dir(self) -> Path:
        """获取日志目录"""
        log_dir = self.project_root / "logs"

        # 为不同环境创建独立的日志目录
        env_log_dir = log_dir / self.environment.value
        env_log_dir.mkdir(parents=True, exist_ok=True)

        return env_log_dir

    def get_config_file_path(self) -> Path:
        """获取配置文件路径"""
        config_dir = self.project_root / "config"
        return config_dir / f"{self.environment.value}.yml"

    def validate_environment(self) -> List[str]:
        """验证环境配置

        Returns:
            验证错误列表
        """
        errors = []

        # 检查配置文件是否存在
        config_file = self.get_config_file_path()
        if not config_file.exists():
            errors.append(f"配置文件不存在: {config_file}")

        # 检查数据目录权限
        data_dir = self.get_data_dir()
        if not os.access(data_dir, os.W_OK):
            errors.append(f"数据目录无写权限: {data_dir}")

        # 检查日志目录权限
        log_dir = self.get_log_dir()
        if not os.access(log_dir, os.W_OK):
            errors.append(f"日志目录无写权限: {log_dir}")

        # 生产环境特殊检查
        if self.environment.is_production():
            # 始终要求的敏感环境变量
            required_env_vars = [
                "REDIS_PASSWORD",
                "API_SECRET_KEY",
            ]
            for var in required_env_vars:
                if not os.getenv(var):
                    errors.append(f"生产环境缺少必需的环境变量: {var}")

            # 仅在启用 Telegram 时，才要求其凭证存在
            tg_enabled = os.getenv("TELEGRAM_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
            if tg_enabled:
                for var in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH"):
                    if not os.getenv(var):
                        errors.append(f"生产环境缺少必需的环境变量: {var}")

        return errors

    def setup_environment(self) -> None:
        """设置环境"""
        # 设置环境变量
        os.environ["NTN_ENV"] = self.environment.value

        # 创建必要的目录
        self.get_data_dir()
        self.get_log_dir()

        # 设置Python路径
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))

        print(f"✓ 环境设置完成: {self.environment.value}")

    def get_environment_info(self) -> Dict[str, any]:
        """获取环境信息"""
        return {
            "environment": self.environment.value,
            "debug": self.is_debug(),
            "log_level": self.get_log_level(),
            "auto_reload": self.is_auto_reload_enabled(),
            "strict_validation": self.is_strict_validation_enabled(),
            "performance_monitoring": self.is_performance_monitoring_enabled(),
            "security_checks": self.is_security_checks_enabled(),
            "data_dir": str(self.get_data_dir()),
            "log_dir": str(self.get_log_dir()),
            "config_file": str(self.get_config_file_path()),
            "project_root": str(self.project_root),
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"EnvironmentConfig(environment={self.environment.value})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"EnvironmentConfig("
            f"environment={self.environment.value}, "
            f"debug={self.is_debug()}, "
            f"log_level={self.get_log_level()}"
            f")"
        )


def get_current_environment() -> Environment:
    """获取当前环境"""
    env_config = EnvironmentConfig()
    return env_config.environment


def is_development() -> bool:
    """是否为开发环境"""
    return get_current_environment().is_development()


def is_staging() -> bool:
    """是否为测试环境"""
    return get_current_environment().is_staging()


def is_production() -> bool:
    """是否为生产环境"""
    return get_current_environment().is_production()


if __name__ == "__main__":
    # 测试环境配置
    import json

    env_config = EnvironmentConfig()

    print(f"当前环境: {env_config}")
    print(f"环境信息:")
    print(json.dumps(env_config.get_environment_info(), indent=2, ensure_ascii=False))

    # 验证环境
    errors = env_config.validate_environment()
    if errors:
        print(f"\n⚠️  环境验证失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"\n✓ 环境验证通过")

    # 设置环境
    env_config.setup_environment()
