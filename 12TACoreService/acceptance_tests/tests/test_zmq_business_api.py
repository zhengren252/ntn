# ZeroMQ业务API测试
# ZeroMQ Business API Tests

import zmq
import json
import time
import uuid
from typing import Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.test_logger import TestLogger
from utils.test_helpers import TestHelpers
from config import AcceptanceTestConfig as TestConfig


class LazyPirateClient:
    """实现Lazy Pirate Pattern的可靠ZMQ客户端"""

    def __init__(self, server_endpoint: str, timeout: int = 5000, retries: int = 3):
        self.server_endpoint = server_endpoint
        self.timeout = timeout
        self.retries = retries
        self.context = zmq.Context()
        self.socket = None
        self.logger = TestLogger("lazy_pirate_client")

    def _create_socket(self):
        """创建新的socket连接"""
        if self.socket:
            self.socket.close()

        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.server_endpoint)

    def send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送请求并处理重试逻辑"""
        request_json = json.dumps(request)

        for attempt in range(self.retries):
            self.logger.log_test_step(
                f"发送请求 (尝试 {attempt + 1}/{self.retries}): {request['method']}"
            )

            # 创建新的socket连接
            self._create_socket()

            # 发送请求
            self.socket.send_string(request_json)

            # 等待响应
            poller = zmq.Poller()
            poller.register(self.socket, zmq.POLLIN)

            if poller.poll(self.timeout):
                # 收到响应 - REQ socket接收多帧消息时只需要最后一帧
                try:
                    # REQ socket会自动处理多帧消息，只返回数据帧
                    response_json = self.socket.recv_string()
                    response = json.loads(response_json)
                    self.logger.log_test_step(
                        f"收到响应: {response.get('status', 'unknown')}"
                    )
                    return response
                except json.JSONDecodeError as e:
                    self.logger.log_test_step(f"JSON解析错误: {e}")
                    # 如果是多帧消息，尝试接收所有帧
                    try:
                        parts = self.socket.recv_multipart()
                        # 通常数据在最后一帧
                        response_json = parts[-1].decode("utf-8")
                        response = json.loads(response_json)
                        self.logger.log_test_step(
                            f"收到多帧响应: {response.get('status', 'unknown')}"
                        )
                        return response
                    except Exception as e2:
                        self.logger.log_test_step(f"多帧消息解析错误: {e2}")
                        return None
            else:
                # 超时
                self.logger.log_test_step(f"请求超时 (尝试 {attempt + 1})")
                self.socket.close()

                if attempt < self.retries - 1:
                    self.logger.log_test_step("准备重试...")
                    time.sleep(1)  # 等待1秒后重试

        self.logger.error(f"所有重试都失败了，放弃请求: {request['method']}")
        return None

    def close(self):
        """关闭连接"""
        if self.socket:
            self.socket.close()
        self.context.term()


class ZMQBusinessAPITests:
    """ZeroMQ业务API测试套件"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("zmq_business_api_tests")
        self.helpers = TestHelpers()
        self.client = LazyPirateClient(
            self.config.ZMQ_ENDPOINT, timeout=self.config.ZMQ_TIMEOUT, retries=3
        )

    def test_scan_market_success(self) -> Dict[str, Any]:
        """测试用例: ZMQ-API-01 - scan.market 成功路径"""
        test_case = {
            "case_id": "ZMQ-API-01",
            "title": "scan.market - 成功路径",
            "suite_id": "API-ZMQ-BUSINESS",
            "suite_name": "核心业务API测试 (ZeroMQ)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("ZMQ-API-01", "scan.market - 成功路径")

            # 准备请求数据
            request_id = self.helpers.generate_request_id()
            request = {
                "request_id": request_id,
                "method": "scan.market",
                "params": {
                    "market_type": "crypto",
                    "symbols": ["BTC/USDT", "ETH/USDT"],
                    "scan_type": "opportunities",
                },
            }

            # 发送请求
            response = self.client.send_request(request)

            if response is None:
                test_case["error_message"] = "请求超时或连接失败"
                return test_case

            # 验证点1: 验证响应中的 status 字段为 'success'
            vp1 = {
                "description": "验证响应中的 status 字段为 'success'",
                "passed": response.get("status") == "success",
                "details": f"实际状态: {response.get('status')}",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证响应中的 request_id 与请求的ID匹配
            vp2 = {
                "description": "验证响应中的 request_id 与请求的ID匹配",
                "passed": response.get("request_id") == request_id,
                "details": f"请求ID: {request_id}, 响应ID: {response.get('request_id')}",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证响应中的 opportunities 字段是一个数组
            opportunities = response.get("data", {}).get("opportunities")
            vp3 = {
                "description": "验证响应中的 opportunities 字段是一个数组",
                "passed": isinstance(opportunities, list),
                "details": f"opportunities类型: {type(opportunities).__name__}, 长度: {len(opportunities) if isinstance(opportunities, list) else 'N/A'}",
            }
            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"scan.market测试", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"scan.market测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "scan.market - 成功路径",
                "ZMQ-API-01",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_execute_order_success(self) -> Dict[str, Any]:
        """测试用例: ZMQ-API-02 - execute.order 成功路径"""
        test_case = {
            "case_id": "ZMQ-API-02",
            "title": "execute.order - 成功路径",
            "suite_id": "API-ZMQ-BUSINESS",
            "suite_name": "核心业务API测试 (ZeroMQ)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("ZMQ-API-02", "execute.order - 成功路径")

            # 准备请求数据
            request_id = self.helpers.generate_request_id()
            request = {
                "request_id": request_id,
                "method": "execute.order",
                "params": {
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "amount": 0.001,
                    "price": 50000,
                    "order_type": "limit",
                },
            }

            # 发送请求
            response = self.client.send_request(request)

            if response is None:
                test_case["error_message"] = "请求超时或连接失败"
                return test_case

            # 验证点1: 验证响应中的 status 字段为 'success'
            vp1 = {
                "description": "验证响应中的 status 字段为 'success'",
                "passed": response.get("status") == "success",
                "details": f"实际状态: {response.get('status')}",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证响应中的 order_id 字段是一个非空字符串
            order_id = response.get("data", {}).get("order_id")
            vp2 = {
                "description": "验证响应中的 order_id 字段是一个非空字符串",
                "passed": isinstance(order_id, str) and len(order_id) > 0,
                "details": f"order_id: {order_id}, 类型: {type(order_id).__name__}",
            }
            test_case["verification_results"].append(vp2)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"execute.order测试", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"execute.order测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "execute.order - 成功路径",
                "ZMQ-API-02",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_evaluate_risk_success(self) -> Dict[str, Any]:
        """测试用例: ZMQ-API-03 - evaluate.risk 成功路径"""
        test_case = {
            "case_id": "ZMQ-API-03",
            "title": "evaluate.risk - 成功路径",
            "suite_id": "API-ZMQ-BUSINESS",
            "suite_name": "核心业务API测试 (ZeroMQ)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("ZMQ-API-03", "evaluate.risk - 成功路径")

            # 准备请求数据
            request_id = self.helpers.generate_request_id()
            request = {
                "request_id": request_id,
                "method": "evaluate.risk",
                "params": {
                    "portfolio": {"BTC": 0.5, "ETH": 2.0, "USDT": 10000},
                    "market_conditions": "volatile",
                    "risk_tolerance": "medium",
                },
            }

            # 发送请求
            response = self.client.send_request(request)

            if response is None:
                test_case["error_message"] = "请求超时或连接失败"
                return test_case

            # 验证点1: 验证响应中的 risk_score 是一个数字
            risk_score = response.get("data", {}).get("risk_score")
            vp1 = {
                "description": "验证响应中的 risk_score 是一个数字",
                "passed": isinstance(risk_score, (int, float)),
                "details": f"risk_score: {risk_score}, 类型: {type(risk_score).__name__}",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证响应中的 risk_level 是 'low', 'medium', 'high' 之一
            risk_level = response.get("data", {}).get("risk_level")
            valid_levels = ["low", "medium", "high"]
            vp2 = {
                "description": "验证响应中的 risk_level 是 'low', 'medium', 'high' 之一",
                "passed": risk_level in valid_levels,
                "details": f"risk_level: {risk_level}, 有效值: {valid_levels}",
            }
            test_case["verification_results"].append(vp2)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"evaluate.risk测试", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"evaluate.risk测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "evaluate.risk - 成功路径",
                "ZMQ-API-03",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_invalid_method(self) -> Dict[str, Any]:
        """测试用例: ZMQ-API-04 - 无效方法测试"""
        test_case = {
            "case_id": "ZMQ-API-04",
            "title": "无效方法测试",
            "suite_id": "API-ZMQ-BUSINESS",
            "suite_name": "核心业务API测试 (ZeroMQ)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("ZMQ-API-04", "无效方法测试")

            # 准备请求数据
            request_id = self.helpers.generate_request_id()
            request = {
                "request_id": request_id,
                "method": "invalid.method",
                "params": {},
            }

            # 发送请求
            response = self.client.send_request(request)

            if response is None:
                test_case["error_message"] = "请求超时或连接失败"
                return test_case

            # 验证点1: 验证响应中的 status 字段为 'error'
            vp1 = {
                "description": "验证响应中的 status 字段为 'error'",
                "passed": response.get("status") == "error",
                "details": f"实际状态: {response.get('status')}",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证响应的错误信息中包含 'Unsupported method' 或类似错误码
            error_field = response.get("error", "")
            # Handle both string and dict error formats
            if isinstance(error_field, dict):
                error_message = error_field.get("message", "")
                error_code = error_field.get("code", "")
            else:
                error_message = str(error_field)
                error_code = ""

            contains_unsupported = (
                "Unsupported method" in error_message
                or "UNKNOWN_ACTION" in error_message
                or "unknown" in error_message.lower()
                or "invalid" in error_message.lower()
            )
            vp2 = {
                "description": "验证响应的错误信息中包含 'Unsupported method' 或类似错误码",
                "passed": contains_unsupported,
                "details": f"错误信息: {error_message}, 错误码: {error_code}",
            }
            test_case["verification_results"].append(vp2)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"invalid.method测试", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"invalid.method测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "无效方法测试", "ZMQ-API-04", test_case["status"], test_case["duration"]
            )

        return test_case

    def run_all_tests(self) -> list:
        """运行所有ZeroMQ业务API测试"""
        self.logger.info("开始运行ZeroMQ业务API测试套件")

        test_results = []

        # 运行所有测试用例
        test_results.append(self.test_scan_market_success())
        test_results.append(self.test_execute_order_success())
        test_results.append(self.test_evaluate_risk_success())
        test_results.append(self.test_invalid_method())

        self.logger.info(f"ZeroMQ业务API测试套件完成，共运行 {len(test_results)} 个测试用例")

        return test_results

    def cleanup(self):
        """清理资源"""
        self.client.close()


# Pytest兼容的测试函数
def test_scan_market_success():
    """pytest兼容的scan.market测试"""
    test_suite = ZMQBusinessAPITests()
    try:
        result = test_suite.test_scan_market_success()
        assert (
            result["status"] == "PASS"
        ), f"测试失败: {result.get('error_message', 'Unknown error')}"
    finally:
        test_suite.cleanup()


def test_execute_order_success():
    """pytest兼容的execute.order测试"""
    test_suite = ZMQBusinessAPITests()
    try:
        result = test_suite.test_execute_order_success()
        assert (
            result["status"] == "PASS"
        ), f"测试失败: {result.get('error_message', 'Unknown error')}"
    finally:
        test_suite.cleanup()


def test_evaluate_risk_success():
    """pytest兼容的evaluate.risk测试"""
    test_suite = ZMQBusinessAPITests()
    try:
        result = test_suite.test_evaluate_risk_success()
        assert (
            result["status"] == "PASS"
        ), f"测试失败: {result.get('error_message', 'Unknown error')}"
    finally:
        test_suite.cleanup()


def test_invalid_method():
    """pytest兼容的invalid.method测试"""
    test_suite = ZMQBusinessAPITests()
    try:
        result = test_suite.test_invalid_method()
        assert (
            result["status"] == "PASS"
        ), f"测试失败: {result.get('error_message', 'Unknown error')}"
    finally:
        test_suite.cleanup()
