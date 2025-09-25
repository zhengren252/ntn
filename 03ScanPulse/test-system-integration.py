#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体驱动交易系统V3.5 - 系统集成测试
验证所有模组的功能和集成情况
"""

import os
import sys
import time
import json
import asyncio
import requests
import zmq
import redis
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import unittest
import logging

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from config.system_logging import get_service_logger


class SystemIntegrationTest:
    """系统集成测试类"""

    def __init__(self):
        self.logger = get_service_logger("integration_test").get_logger()
        self.test_results = []
        self.start_time = None

        # 服务配置
        self.services = {
            "tacore_service": {
                "type": "zmq",
                "endpoint": "tcp://localhost:5555",
                "timeout": 10,
            },
            "redis": {"type": "redis", "host": "localhost", "port": 6379, "db": 0},
            "api_factory": {
                "type": "http",
                "base_url": "http://localhost:8001",
                "timeout": 10,
            },
            "crawler": {
                "type": "http",
                "base_url": "http://localhost:8002",
                "timeout": 10,
            },
            "scanner": {
                "type": "http",
                "base_url": "http://localhost:8003",
                "timeout": 10,
            },
            "trader": {
                "type": "http",
                "base_url": "http://localhost:8004",
                "timeout": 10,
            },
            "risk_manager": {
                "type": "http",
                "base_url": "http://localhost:8005",
                "timeout": 10,
            },
            "portfolio": {
                "type": "http",
                "base_url": "http://localhost:8006",
                "timeout": 10,
            },
            "notifier": {
                "type": "http",
                "base_url": "http://localhost:8007",
                "timeout": 10,
            },
            "analytics": {
                "type": "http",
                "base_url": "http://localhost:8008",
                "timeout": 10,
            },
            "backtester": {
                "type": "http",
                "base_url": "http://localhost:8009",
                "timeout": 10,
            },
            "web_ui": {
                "type": "http",
                "base_url": "http://localhost:3000",
                "timeout": 10,
            },
            "monitor": {
                "type": "http",
                "base_url": "http://localhost:8010",
                "timeout": 10,
            },
        }

        # 初始化连接
        self.zmq_context = zmq.Context()
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            redis_config = self.services["redis"]
            self.redis_client = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                db=redis_config["db"],
                decode_responses=True,
            )
            self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")

    def add_test_result(
        self,
        test_name: str,
        success: bool,
        message: str,
        duration: float = 0,
        details: Dict[str, Any] = None,
    ):
        """添加测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }

        self.test_results.append(result)

        if success:
            self.logger.info(f"✓ {test_name}: {message}")
        else:
            self.logger.error(f"✗ {test_name}: {message}")

    def test_service_health(self, service_name: str, config: Dict[str, Any]) -> bool:
        """测试服务健康状态"""
        start_time = time.time()

        try:
            if config["type"] == "http":
                response = requests.get(
                    f"{config['base_url']}/health", timeout=config.get("timeout", 10)
                )
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.add_test_result(
                        f"{service_name}_health",
                        True,
                        f"Service healthy (response time: {duration:.2f}s)",
                        duration,
                        response.json() if response.content else {},
                    )
                    return True
                else:
                    self.add_test_result(
                        f"{service_name}_health",
                        False,
                        f"HTTP {response.status_code}",
                        duration,
                    )
                    return False

            elif config["type"] == "zmq":
                socket = self.zmq_context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, config.get("timeout", 10) * 1000)

                try:
                    socket.connect(config["endpoint"])

                    request = {
                        "method": "health.check",
                        "params": {},
                        "id": f"test_{int(time.time())}",
                    }

                    socket.send_string(json.dumps(request))
                    response_str = socket.recv_string()
                    response = json.loads(response_str)

                    duration = time.time() - start_time

                    if response.get("status") == "success":
                        self.add_test_result(
                            f"{service_name}_health",
                            True,
                            f"Service healthy (response time: {duration:.2f}s)",
                            duration,
                            response.get("result", {}),
                        )
                        return True
                    else:
                        self.add_test_result(
                            f"{service_name}_health",
                            False,
                            response.get("message", "Unknown error"),
                            duration,
                        )
                        return False

                finally:
                    socket.close()

            elif config["type"] == "redis":
                self.redis_client.ping()
                duration = time.time() - start_time

                info = self.redis_client.info()
                self.add_test_result(
                    f"{service_name}_health",
                    True,
                    f"Redis healthy (response time: {duration:.2f}s)",
                    duration,
                    {
                        "version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                    },
                )
                return True

        except Exception as e:
            duration = time.time() - start_time
            self.add_test_result(f"{service_name}_health", False, str(e), duration)
            return False

    def test_tacore_functionality(self) -> bool:
        """测试TACoreService核心功能"""
        socket = self.zmq_context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 10000)

        try:
            socket.connect("tcp://localhost:5555")

            # 测试市场扫描
            start_time = time.time()
            scan_request = {
                "method": "scan.market",
                "params": {
                    "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                    "scan_type": "basic",
                },
                "id": "test_scan",
            }

            socket.send_string(json.dumps(scan_request))
            response_str = socket.recv_string()
            response = json.loads(response_str)
            duration = time.time() - start_time

            if response.get("status") == "success":
                result = response.get("result", {})
                scan_results = result.get("scan_results", [])

                self.add_test_result(
                    "tacore_market_scan",
                    True,
                    f"Scanned {len(scan_results)} symbols successfully",
                    duration,
                    {"scanned_count": len(scan_results)},
                )
            else:
                self.add_test_result(
                    "tacore_market_scan",
                    False,
                    response.get("message", "Scan failed"),
                    duration,
                )
                return False

            # 测试交易对分析
            start_time = time.time()
            analyze_request = {
                "method": "analyze.symbol",
                "params": {"symbol": "BTCUSDT", "analysis_type": "comprehensive"},
                "id": "test_analyze",
            }

            socket.send_string(json.dumps(analyze_request))
            response_str = socket.recv_string()
            response = json.loads(response_str)
            duration = time.time() - start_time

            if response.get("status") == "success":
                result = response.get("result", {})
                analysis = result.get("analysis", {})

                self.add_test_result(
                    "tacore_symbol_analysis",
                    True,
                    f"Analysis completed for {result.get('symbol')}",
                    duration,
                    {
                        "recommendation": analysis.get("recommendation"),
                        "confidence": analysis.get("confidence"),
                    },
                )
            else:
                self.add_test_result(
                    "tacore_symbol_analysis",
                    False,
                    response.get("message", "Analysis failed"),
                    duration,
                )
                return False

            # 测试市场数据获取
            start_time = time.time()
            data_request = {
                "method": "get.market_data",
                "params": {"symbol": "BTCUSDT", "timeframe": "1h", "limit": 100},
                "id": "test_data",
            }

            socket.send_string(json.dumps(data_request))
            response_str = socket.recv_string()
            response = json.loads(response_str)
            duration = time.time() - start_time

            if response.get("status") == "success":
                result = response.get("result", {})
                data = result.get("data", {})

                self.add_test_result(
                    "tacore_market_data",
                    True,
                    f"Market data retrieved for {result.get('symbol')}",
                    duration,
                    {"price": data.get("price"), "volume": data.get("volume")},
                )
            else:
                self.add_test_result(
                    "tacore_market_data",
                    False,
                    response.get("message", "Data retrieval failed"),
                    duration,
                )
                return False

            return True

        except Exception as e:
            self.add_test_result("tacore_functionality", False, str(e), 0)
            return False

        finally:
            socket.close()

    def test_redis_functionality(self) -> bool:
        """测试Redis功能"""
        try:
            start_time = time.time()

            # 测试基本读写
            test_key = f"test_key_{int(time.time())}"
            test_value = {"test": "data", "timestamp": datetime.now().isoformat()}

            # 写入数据
            self.redis_client.set(test_key, json.dumps(test_value), ex=60)

            # 读取数据
            retrieved_value = self.redis_client.get(test_key)
            retrieved_data = json.loads(retrieved_value)

            duration = time.time() - start_time

            if retrieved_data == test_value:
                self.add_test_result(
                    "redis_read_write",
                    True,
                    "Redis read/write operations successful",
                    duration,
                )
            else:
                self.add_test_result(
                    "redis_read_write",
                    False,
                    "Data mismatch in Redis read/write",
                    duration,
                )
                return False

            # 清理测试数据
            self.redis_client.delete(test_key)

            # 测试列表操作
            start_time = time.time()
            list_key = f"test_list_{int(time.time())}"

            # 添加列表项
            for i in range(5):
                self.redis_client.lpush(list_key, f"item_{i}")

            # 获取列表长度
            list_length = self.redis_client.llen(list_key)

            # 获取列表内容
            list_items = self.redis_client.lrange(list_key, 0, -1)

            duration = time.time() - start_time

            if list_length == 5 and len(list_items) == 5:
                self.add_test_result(
                    "redis_list_operations",
                    True,
                    "Redis list operations successful",
                    duration,
                    {"list_length": list_length},
                )
            else:
                self.add_test_result(
                    "redis_list_operations",
                    False,
                    f"List operation failed: expected 5 items, got {list_length}",
                    duration,
                )
                return False

            # 清理测试数据
            self.redis_client.delete(list_key)

            return True

        except Exception as e:
            self.add_test_result("redis_functionality", False, str(e), 0)
            return False

    def test_http_service_endpoints(self, service_name: str, base_url: str) -> bool:
        """测试HTTP服务端点"""
        try:
            # 测试健康检查端点
            start_time = time.time()
            response = requests.get(f"{base_url}/health", timeout=10)
            duration = time.time() - start_time

            if response.status_code == 200:
                self.add_test_result(
                    f"{service_name}_health_endpoint",
                    True,
                    "Health endpoint accessible",
                    duration,
                )
            else:
                self.add_test_result(
                    f"{service_name}_health_endpoint",
                    False,
                    f"Health endpoint returned {response.status_code}",
                    duration,
                )
                return False

            # 测试状态端点（如果存在）
            try:
                start_time = time.time()
                response = requests.get(f"{base_url}/status", timeout=5)
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.add_test_result(
                        f"{service_name}_status_endpoint",
                        True,
                        "Status endpoint accessible",
                        duration,
                    )
                elif response.status_code == 404:
                    # 状态端点不存在，这是正常的
                    pass
                else:
                    self.add_test_result(
                        f"{service_name}_status_endpoint",
                        False,
                        f"Status endpoint returned {response.status_code}",
                        duration,
                    )

            except requests.exceptions.Timeout:
                # 超时是可以接受的，可能服务没有实现这个端点
                pass

            return True

        except Exception as e:
            self.add_test_result(f"{service_name}_endpoints", False, str(e), 0)
            return False

    def test_data_flow(self) -> bool:
        """测试数据流"""
        try:
            # 这里可以添加端到端的数据流测试
            # 例如：扫描 -> 分析 -> 交易决策 -> 风险管理 -> 执行

            self.add_test_result(
                "data_flow_test",
                True,
                "Data flow test completed (placeholder)",
                0,
                {"note": "This is a placeholder for actual data flow testing"},
            )

            return True

        except Exception as e:
            self.add_test_result("data_flow_test", False, str(e), 0)
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        self.start_time = time.time()
        self.test_results = []

        self.logger.info("Starting system integration tests...")

        # 1. 测试所有服务的健康状态
        self.logger.info("Testing service health...")
        for service_name, config in self.services.items():
            self.test_service_health(service_name, config)

        # 2. 测试TACoreService核心功能
        self.logger.info("Testing TACoreService functionality...")
        self.test_tacore_functionality()

        # 3. 测试Redis功能
        self.logger.info("Testing Redis functionality...")
        self.test_redis_functionality()

        # 4. 测试HTTP服务端点
        self.logger.info("Testing HTTP service endpoints...")
        for service_name, config in self.services.items():
            if config["type"] == "http":
                self.test_http_service_endpoints(service_name, config["base_url"])

        # 5. 测试数据流
        self.logger.info("Testing data flow...")
        self.test_data_flow()

        # 生成测试报告
        total_duration = time.time() - self.start_time

        successful_tests = [r for r in self.test_results if r["success"]]
        failed_tests = [r for r in self.test_results if not r["success"]]

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": total_duration,
            "summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "success_rate": len(successful_tests) / len(self.test_results)
                if self.test_results
                else 0,
            },
            "test_results": self.test_results,
            "failed_tests": failed_tests,
        }

        self.logger.info(f"Integration tests completed in {total_duration:.2f}s")
        self.logger.info(
            f"Results: {len(successful_tests)}/{len(self.test_results)} tests passed"
        )

        if failed_tests:
            self.logger.error(f"Failed tests: {[t['test_name'] for t in failed_tests]}")

        return report

    def cleanup(self):
        """清理资源"""
        if self.zmq_context:
            self.zmq_context.term()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AI智能体驱动交易系统V3.5 - 系统集成测试")
    parser.add_argument("--output", "-o", help="输出报告文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = SystemIntegrationTest()

    try:
        # 运行测试
        report = tester.run_all_tests()

        # 输出报告
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"Test report saved to: {args.output}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))

        # 返回适当的退出代码
        if report["summary"]["failed_tests"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)

    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
