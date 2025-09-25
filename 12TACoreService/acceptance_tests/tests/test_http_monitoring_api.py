# HTTP监控API测试
# HTTP Monitoring API Tests

import requests
import time
import json
from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.test_logger import TestLogger
from utils.test_helpers import TestHelpers
from config import AcceptanceTestConfig as TestConfig


class HTTPMonitoringAPITests:
    """HTTP监控API测试套件"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("http_monitoring_api_tests")
        self.helpers = TestHelpers()
        self.base_url = f"http://{self.config.HTTP_HOST}:{self.config.HTTP_PORT}"
        self.session = requests.Session()
        self.session.timeout = self.config.HTTP_TIMEOUT

    def test_get_status(self) -> Dict[str, Any]:
        """测试用例: HTTP-API-01 - GET /status 服务状态接口"""
        test_case = {
            "case_id": "HTTP-API-01",
            "title": "GET /status - 服务状态接口",
            "suite_id": "API-HTTP-MONITORING",
            "suite_name": "监控管理API测试 (HTTP)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("HTTP-API-01", "GET /status - 服务状态接口")

            # 发送GET请求到/api/status端点
            url = f"{self.base_url}/api/status"
            response = self.session.get(url)

            # 验证点1: 验证HTTP状态码为 200 OK
            vp1 = {
                "description": "验证HTTP状态码为 200 OK",
                "passed": response.status_code == 200,
                "details": f"实际状态码: {response.status_code}",
            }
            test_case["verification_results"].append(vp1)

            # 解析响应JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                test_case["error_message"] = f"响应不是有效的JSON: {e}"
                return test_case

            # 验证点2: 验证响应JSON体中包含关键字段
            required_fields = ["service_name", "status", "uptime"]
            missing_fields = []
            for field in required_fields:
                if field not in response_data:
                    missing_fields.append(field)

            vp2 = {
                "description": "验证响应JSON体中包含关键字段",
                "passed": len(missing_fields) == 0,
                "details": f"缺失字段: {missing_fields}" if missing_fields else "所有必需字段都存在",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证字段类型和值的合理性
            type_checks = []

            # service_name应该是字符串
            service_name = response_data.get("service_name")
            if isinstance(service_name, str):
                type_checks.append(f"service_name: {service_name} (字符串)")
            else:
                type_checks.append(
                    f"service_name: {service_name} (类型错误: {type(service_name).__name__})"
                )

            # status应该是字符串
            status = response_data.get("status")
            if isinstance(status, str):
                type_checks.append(f"status: {status} (字符串)")
            else:
                type_checks.append(f"status: {status} (类型错误: {type(status).__name__})")

            # uptime应该是非负数字
            uptime = response_data.get("uptime")
            if isinstance(uptime, (int, float)) and uptime >= 0:
                type_checks.append(f"uptime: {uptime} (有效)")
            else:
                type_checks.append(f"uptime: {uptime} (无效)")

            all_types_valid = all(
                "有效" in check or "字符串" in check for check in type_checks
            )
            vp3 = {
                "description": "验证字段类型和值的合理性",
                "passed": all_types_valid,
                "details": "; ".join(type_checks),
            }
            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"GET /status测试", all_passed)

        except requests.exceptions.RequestException as e:
            test_case["error_message"] = f"HTTP请求异常: {e}"
            self.logger.error(f"GET /status测试HTTP异常: {e}")
        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"GET /status测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "GET /status - 服务状态接口",
                "HTTP-API-01",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_get_workers(self) -> Dict[str, Any]:
        """测试用例: HTTP-API-02 - GET /workers 工作进程列表接口"""
        test_case = {
            "case_id": "HTTP-API-02",
            "title": "GET /workers - 工作进程列表接口",
            "suite_id": "API-HTTP-MONITORING",
            "suite_name": "监控管理API测试 (HTTP)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("HTTP-API-02", "GET /workers - 工作进程列表接口")

            # 发送GET请求到/api/workers端点
            url = f"{self.base_url}/api/workers"
            response = self.session.get(url)

            # 验证点1: 验证HTTP状态码为 200 OK
            vp1 = {
                "description": "验证HTTP状态码为 200 OK",
                "passed": response.status_code == 200,
                "details": f"实际状态码: {response.status_code}",
            }
            test_case["verification_results"].append(vp1)

            # 解析响应JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                test_case["error_message"] = f"响应不是有效的JSON: {e}"
                return test_case

            # 验证点2: 验证响应JSON体是一个数组
            vp2 = {
                "description": "验证响应JSON体是一个数组",
                "passed": isinstance(response_data, list),
                "details": f"响应类型: {type(response_data).__name__}, 长度: {len(response_data) if isinstance(response_data, list) else 'N/A'}",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证数组中每个对象的结构都符合规格
            if isinstance(response_data, list) and len(response_data) > 0:
                required_worker_fields = ["worker_id", "status"]
                structure_valid = True
                structure_details = []

                for i, worker in enumerate(response_data):
                    if not isinstance(worker, dict):
                        structure_valid = False
                        structure_details.append(f"Worker {i}: 不是字典对象")
                        continue

                    missing_fields = []
                    for field in required_worker_fields:
                        if field not in worker:
                            missing_fields.append(field)

                    if missing_fields:
                        structure_valid = False
                        structure_details.append(f"Worker {i}: 缺失字段 {missing_fields}")
                    else:
                        structure_details.append(
                            f"Worker {i}: 结构正确 (ID: {worker.get('worker_id')}, 状态: {worker.get('status')})"
                        )

                vp3 = {
                    "description": "验证数组中每个对象的结构都符合规格",
                    "passed": structure_valid,
                    "details": "; ".join(structure_details[:3]),  # 只显示前3个worker的详情
                }
            else:
                vp3 = {
                    "description": "验证数组中每个对象的结构都符合规格",
                    "passed": True,  # 空数组也是有效的
                    "details": "工作进程列表为空",
                }

            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"GET /workers测试", all_passed)

        except requests.exceptions.RequestException as e:
            test_case["error_message"] = f"HTTP请求异常: {e}"
            self.logger.error(f"GET /workers测试HTTP异常: {e}")
        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"GET /workers测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "GET /workers - 工作进程列表接口",
                "HTTP-API-02",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_get_logs(self) -> Dict[str, Any]:
        """测试用例: HTTP-API-03 - GET /logs 日志获取接口"""
        test_case = {
            "case_id": "HTTP-API-03",
            "title": "GET /logs - 日志获取接口",
            "suite_id": "API-HTTP-MONITORING",
            "suite_name": "监控管理API测试 (HTTP)",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("HTTP-API-03", "GET /logs - 日志获取接口")

            # 发送GET请求到/api/requests端点，带查询参数
            url = f"{self.base_url}/api/requests"
            params = {"limit": 50, "level": "INFO"}
            response = self.session.get(url, params=params)

            # 验证点1: 验证HTTP状态码为 200 OK
            vp1 = {
                "description": "验证HTTP状态码为 200 OK",
                "passed": response.status_code == 200,
                "details": f"实际状态码: {response.status_code}",
            }
            test_case["verification_results"].append(vp1)

            # 解析响应JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                test_case["error_message"] = f"响应不是有效的JSON: {e}"
                return test_case

            # 验证点2: 验证返回的日志条数不超过50条
            logs = (
                response_data.get("logs", [])
                if isinstance(response_data, dict)
                else response_data
            )
            if not isinstance(logs, list):
                logs = []

            vp2 = {
                "description": "验证返回的日志条数不超过50条",
                "passed": len(logs) <= 50,
                "details": f"实际日志条数: {len(logs)}",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证返回的日志级别均为INFO或更高级别
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            level_hierarchy = {
                "DEBUG": 0,
                "INFO": 1,
                "WARNING": 2,
                "ERROR": 3,
                "CRITICAL": 4,
            }
            min_level = level_hierarchy.get("INFO", 1)

            level_check_passed = True
            level_details = []

            for i, log_entry in enumerate(logs[:10]):  # 只检查前10条日志
                if isinstance(log_entry, dict):
                    log_level = log_entry.get("level", "UNKNOWN")
                    entry_level = level_hierarchy.get(log_level, -1)

                    if entry_level >= min_level:
                        level_details.append(f"日志{i+1}: {log_level} (有效)")
                    else:
                        level_check_passed = False
                        level_details.append(f"日志{i+1}: {log_level} (级别过低)")
                else:
                    level_details.append(f"日志{i+1}: 格式错误")

            vp3 = {
                "description": "验证返回的日志级别均为INFO或更高级别",
                "passed": level_check_passed,
                "details": "; ".join(level_details) if level_details else "无日志数据",
            }
            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"GET /logs测试", all_passed)

        except requests.exceptions.RequestException as e:
            test_case["error_message"] = f"HTTP请求异常: {e}"
            self.logger.error(f"GET /logs测试HTTP异常: {e}")
        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"GET /logs测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "GET /logs - 日志获取接口",
                "HTTP-API-03",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_service_status(self) -> Dict[str, Any]:
        """简单的服务状态检查"""
        try:
            url = f"{self.base_url}/api/status"
            response = self.session.get(url)
            status = "PASS" if response.status_code == 200 else "FAIL"
            return {"status": status}
        except Exception as e:
            self.logger.error(f"服务状态检查失败: {e}")
            return {"status": "FAIL"}

    def test_workers_list(self) -> Dict[str, Any]:
        """工作进程列表检查"""
        try:
            url = f"{self.base_url}/api/workers"
            response = self.session.get(url)
            status = "PASS" if response.status_code == 200 else "FAIL"
            return {"status": status}
        except Exception as e:
            self.logger.error(f"工作进程列表检查失败: {e}")
            return {"status": "FAIL"}

    def test_logs_retrieval(self) -> Dict[str, Any]:
        """日志获取检查"""
        try:
            url = f"{self.base_url}/api/requests"
            response = self.session.get(url)
            status = "PASS" if response.status_code == 200 else "FAIL"
            return {"status": status}
        except Exception as e:
            self.logger.error(f"日志获取检查失败: {e}")
            return {"status": "FAIL"}

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """运行所有HTTP监控API测试"""
        self.logger.info("开始运行HTTP监控API测试套件")

        test_results = []

        # 运行所有测试用例
        test_results.append(self.test_get_status())
        test_results.append(self.test_get_workers())
        test_results.append(self.test_get_logs())

        self.logger.info(f"HTTP监控API测试套件完成，共运行 {len(test_results)} 个测试用例")

        return test_results

    def cleanup(self):
        """清理资源"""
        self.session.close()
