# 配置管理模块
# 严格遵循全局规范：数据隔离与环境管理规范 (V1.0)

from .env_manager import EnvironmentManager, get_env_manager

__all__ = ["EnvironmentManager", "get_env_manager"]
