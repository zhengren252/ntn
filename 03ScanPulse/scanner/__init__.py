# 扫描器模组 - 主包初始化
# 模组三：扫描器 (Scanner Module)
# 核心设计理念：化整为零，分而治之的微服务架构

__version__ = "1.1.0"
__author__ = "NeuroTrade Nexus Team"
__description__ = "全市场扫描，识别并筛选符合预设规则的交易对，输出到预备池"

from .config import EnvironmentManager
from .core.scanner_controller import ScannerController
from .main import ScannerApplication

__all__ = ["ScannerApplication", "ScannerController", "EnvironmentManager"]
