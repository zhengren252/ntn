# 扫描器核心模块
# 实现扫描器的核心功能和控制逻辑

from .data_processor import DataProcessor
from .result_aggregator import ResultAggregator
from .scanner_controller import ScannerController
from .scanner_module import ScannerModule

__all__ = ["ScannerModule", "ScannerController", "DataProcessor", "ResultAggregator"]

__version__ = "1.0.0"
__author__ = "NeuroTrade Nexus Team"
__description__ = "扫描器核心模块 - 实现市场扫描和机会识别的核心逻辑"
