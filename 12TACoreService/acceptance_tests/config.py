# 验收测试配置文件
# Acceptance Test Configuration

import os
from typing import Dict, Any


class AcceptanceTestConfig:
    """验收测试配置类"""

    # 服务端点配置
    ZMQ_ENDPOINT = "tcp://localhost:5555"
    HTTP_ENDPOINT = "http://localhost:8080"
    ZMQ_TIMEOUT = 5000  # ZMQ请求超时时间（毫秒）
    HTTP_HOST = "localhost"  # HTTP服务主机地址
    HTTP_PORT = 8080  # HTTP服务端口
    HTTP_TIMEOUT = 30  # HTTP请求超时时间（秒）

    # 测试超时配置
    REQUEST_TIMEOUT = 30000  # 30秒
    CONNECTION_TIMEOUT = 5000  # 5秒
    RETRY_COUNT = 3

    # 数据库配置
    SQLITE_DB_PATH = "./data/tacoreservice.db"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6380  # 修正为Docker映射的端口
    REDIS_DB = 0

    # 测试数据配置
    TEST_SYMBOLS = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    TEST_MARKET_TYPES = ["stock", "crypto", "forex"]

    # 负载测试配置
    LOAD_TEST_DURATION = 30  # 秒
    CONCURRENT_REQUESTS = 20
    SCALE_TEST_WORKERS = [2, 4, 8]

    # 报告配置
    REPORT_DIR = "./acceptance_tests/reports"
    LOG_LEVEL = "INFO"

    @classmethod
    def get_test_request_data(cls) -> Dict[str, Any]:
        """获取测试请求数据模板"""
        return {
            "scan.market": {
                "method": "scan.market",
                "params": {
                    "market_type": "stock",
                    "symbols": cls.TEST_SYMBOLS[:2],
                    "filters": {"min_volume": 1000000},
                },
                "request_id": "test_scan_001",
            },
            "execute.order": {
                "method": "execute.order",
                "params": {
                    "symbol": "AAPL",
                    "action": "buy",
                    "quantity": 100,
                    "price": 150.00,
                },
                "request_id": "test_order_001",
            },
            "evaluate.risk": {
                "method": "evaluate.risk",
                "params": {
                    "portfolio": {
                        "total_value": 100000,
                        "positions": [
                            {"symbol": "AAPL", "quantity": 100, "value": 15000}
                        ],
                    },
                    "proposed_trade": {
                        "symbol": "GOOGL",
                        "action": "buy",
                        "quantity": 50,
                        "estimated_value": 75000,
                    },
                },
                "request_id": "test_risk_001",
            },
            "invalid.method": {
                "method": "invalid.method",
                "params": {},
                "request_id": "test_invalid_001",
            },
        }

    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        os.makedirs(cls.REPORT_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(cls.SQLITE_DB_PATH), exist_ok=True)
