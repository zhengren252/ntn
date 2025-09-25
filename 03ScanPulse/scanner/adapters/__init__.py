# 适配器模块
# 实现与外部系统的集成，严格遵循系统级集成流程

from .adapter_manager import AdapterManager
from .api_factory_adapter import APIFactoryAdapter
from .base_adapter import AdapterConfig, BaseAdapter
from .trading_agents_cn_adapter import TACoreServiceAgent, TACoreServiceClient

__all__ = [
    "TACoreServiceAgent",
    "TACoreServiceClient",
    "APIFactoryAdapter",
    "BaseAdapter",
    "AdapterConfig",
    "AdapterManager",
]
