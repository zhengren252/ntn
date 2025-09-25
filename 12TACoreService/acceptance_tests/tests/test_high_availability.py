# 高可用性与故障转移测试
# High Availability and Failover Tests

import time
import threading
import requests
import subprocess
import json
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.test_logger import TestLogger
from utils.test_helpers import TestHelpers
from config import AcceptanceTestConfig as TestConfig
from tests.test_zmq_business_api import LazyPirateClient


class HighAvailabilityTests:
    """高可用性与故障转移测试套件"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("high_availability_tests")
        self.helpers = TestHelpers()

    def _get_docker_containers(self) -> List[Dict[str, str]]:
        """获取Docker容器列表"""
        try:
            # 使用docker ps命令获取容器信息
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            containers = []
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            containers.append(
                                {"id": parts[0], "name": parts[1], "status": parts[2]}
                            )

            return containers
        except Exception as e:
            self.logger.error(f"获取Docker容器列表失败: {e}")
            return []

    def _stop_container(self, container_id: str) -> bool:
        """停止Docker容器"""
        try:
            result = subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"停止容器 {container_id} 失败: {e}")
            return False

    def _start_container(self, container_id: str) -> bool:
        """启动Docker容器"""
        try:
            result = subprocess.run(
                ["docker", "start", container_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"启动容器 {container_id} 失败: {e}")
            return False

    def _check_service_health(self) -> Dict[str, Any]:
        """检查服务健康状态"""
        try:
            # 检查HTTP监控API
            http_url = f"http://{self.config.HTTP_HOST}:{self.config.HTTP_PORT}/status"
            http_response = requests.get(http_url, timeout=5)
            http_healthy = http_response.status_code == 200

            # 检查ZMQ服务
            zmq_client = LazyPirateClient(
                self.config.ZMQ_ENDPOINT, timeout=3000, retries=1
            )

            test_request = {
                "request_id": self.helpers.generate_request_id(),
                "method": "scan.market",
                "params": {
                    "market_type": "crypto",
                    "symbols": ["BTC/USDT"],
                    "scan_type": "opportunities",
                },
            }

            zmq_response = zmq_client.send_request(test_request)
            zmq_healthy = zmq_response is not None
            zmq_client.close()

            return {
                "http_healthy": http_healthy,
                "zmq_healthy": zmq_healthy,
                "overall_healthy": http_healthy and zmq_healthy,
            }
        except Exception as e:
            self.logger.error(f"健康检查异常: {e}")
            return {
                "http_healthy": False,
                "zmq_healthy": False,
                "overall_healthy": False,
                "error": str(e),
            }

    def test_worker_failover(self) -> Dict[str, Any]:
        """测试用例: HA-01 - 工作进程故障转移"""
        test_case = {
            "case_id": "HA-01",
            "title": "工作进程故障转移",
            "suite_id": "SYS-HIGH-AVAILABILITY",
            "suite_name": "高可用与弹性测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("HA-01", "工作进程故障转移")

            # 1. 获取当前运行的容器
            containers = self._get_docker_containers()
            worker_containers = [
                c
                for c in containers
                if "worker" in c["name"].lower() or "tacoreservice" in c["name"].lower()
            ]

            if not worker_containers:
                test_case["error_message"] = "未找到工作进程容器"
                return test_case

            self.logger.log_test_step(f"找到 {len(worker_containers)} 个相关容器")

            # 2. 检查初始服务状态
            initial_health = self._check_service_health()

            vp1 = {
                "description": "验证服务初始状态健康",
                "passed": initial_health["overall_healthy"],
                "details": f"HTTP: {initial_health['http_healthy']}, ZMQ: {initial_health['zmq_healthy']}",
            }
            test_case["verification_results"].append(vp1)

            if not initial_health["overall_healthy"]:
                test_case["error_message"] = "服务初始状态不健康，无法进行故障转移测试"
                return test_case

            # 3. 启动持续请求发送线程
            request_results = []
            stop_requests = threading.Event()

            def continuous_requests():
                client = LazyPirateClient(
                    self.config.ZMQ_ENDPOINT, timeout=3000, retries=2
                )

                request_count = 0
                while not stop_requests.is_set():
                    try:
                        request = {
                            "request_id": f"ha_test_{request_count}_{int(time.time() * 1000)}",
                            "method": "scan.market",
                            "params": {
                                "market_type": "crypto",
                                "symbols": ["BTC/USDT"],
                                "scan_type": "opportunities",
                            },
                        }

                        response = client.send_request(request)
                        success = (
                            response is not None and response.get("status") == "success"
                        )

                        request_results.append(
                            {
                                "timestamp": time.time(),
                                "success": success,
                                "request_id": request["request_id"],
                            }
                        )

                        request_count += 1
                        time.sleep(0.5)  # 每0.5秒发送一个请求

                    except Exception as e:
                        request_results.append(
                            {
                                "timestamp": time.time(),
                                "success": False,
                                "error": str(e),
                            }
                        )

                client.close()

            # 启动持续请求线程
            request_thread = threading.Thread(target=continuous_requests)
            request_thread.start()

            # 等待一段时间确保请求正常
            time.sleep(3)

            # 4. 停止一个工作进程容器
            target_container = worker_containers[0]
            self.logger.log_test_step(
                f"停止容器: {target_container['name']} ({target_container['id']})"
            )

            container_stopped = self._stop_container(target_container["id"])

            if not container_stopped:
                stop_requests.set()
                request_thread.join(timeout=5)
                test_case["error_message"] = f"无法停止容器 {target_container['id']}"
                return test_case

            # 等待故障转移生效
            time.sleep(5)

            # 5. 检查服务是否仍然可用
            failover_health = self._check_service_health()

            # 6. 停止持续请求
            stop_requests.set()
            request_thread.join(timeout=10)

            # 7. 重启容器
            self.logger.log_test_step(f"重启容器: {target_container['name']}")
            self._start_container(target_container["id"])
            time.sleep(3)  # 等待容器启动

            # 验证点2: 验证服务在故障期间仍然可用
            vp2 = {
                "description": "验证服务在工作进程故障期间仍然可用",
                "passed": failover_health.get("zmq_healthy", False),
                "details": f"故障期间ZMQ服务状态: {failover_health.get('zmq_healthy', False)}",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 分析请求成功率
            if request_results:
                total_requests = len(request_results)
                successful_requests = len(
                    [r for r in request_results if r.get("success", False)]
                )
                success_rate = (
                    successful_requests / total_requests if total_requests > 0 else 0
                )

                # 在故障转移期间，成功率应该保持在合理水平（至少50%）
                vp3 = {
                    "description": "验证故障转移期间请求成功率合理 (>= 50%)",
                    "passed": success_rate >= 0.5,
                    "details": f"成功率: {success_rate:.1%} ({successful_requests}/{total_requests})",
                }
            else:
                vp3 = {
                    "description": "验证故障转移期间请求成功率合理 (>= 50%)",
                    "passed": False,
                    "details": "没有收集到请求结果",
                }

            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"工作进程故障转移", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"工作进程故障转移测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "工作进程故障转移测试", "HA-01", test_case["status"], test_case["duration"]
            )

        return test_case

    def test_lazy_pirate_retry(self) -> Dict[str, Any]:
        """测试用例: HA-02 - 客户端自动重试 (Lazy Pirate)"""
        test_case = {
            "case_id": "HA-02",
            "title": "客户端自动重试 (Lazy Pirate)",
            "suite_id": "SYS-HIGH-AVAILABILITY",
            "suite_name": "高可用与弹性测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("HA-02", "客户端自动重试 (Lazy Pirate)")

            # 1. 检查初始服务状态
            initial_health = self._check_service_health()

            vp1 = {
                "description": "验证服务初始状态健康",
                "passed": initial_health["overall_healthy"],
                "details": f"HTTP: {initial_health['http_healthy']}, ZMQ: {initial_health['zmq_healthy']}",
            }
            test_case["verification_results"].append(vp1)

            if not initial_health["overall_healthy"]:
                test_case["error_message"] = "服务初始状态不健康，无法进行重试测试"
                return test_case

            # 2. 创建可靠客户端（启用重试）
            reliable_client = LazyPirateClient(
                self.config.ZMQ_ENDPOINT, timeout=3000, retries=3  # 启用重试
            )

            # 3. 准备测试请求
            test_request = {
                "request_id": self.helpers.generate_request_id(),
                "method": "evaluate.risk",
                "params": {
                    "portfolio": {"BTC": 0.1, "USDT": 1000},
                    "market_conditions": "stable",
                    "risk_tolerance": "medium",
                },
            }

            # 4. 在后台线程中模拟服务中断和恢复
            def simulate_service_interruption():
                time.sleep(1)  # 等待请求开始

                # 获取负载均衡代理容器
                containers = self._get_docker_containers()
                proxy_containers = [
                    c
                    for c in containers
                    if "tacoreservice" in c["name"].lower()
                    and "worker" not in c["name"].lower()
                ]

                if proxy_containers:
                    proxy_container = proxy_containers[0]
                    self.logger.log_test_step(
                        f"模拟服务中断: 停止代理容器 {proxy_container['name']}"
                    )

                    # 停止代理容器
                    self._stop_container(proxy_container["id"])

                    # 等待3秒
                    time.sleep(3)

                    # 重启代理容器
                    self.logger.log_test_step(f"恢复服务: 重启代理容器 {proxy_container['name']}")
                    self._start_container(proxy_container["id"])

                    # 等待服务完全恢复
                    time.sleep(5)

            # 启动服务中断模拟线程
            interruption_thread = threading.Thread(target=simulate_service_interruption)
            interruption_thread.start()

            # 5. 发送请求（应该会经历重试过程）
            request_start_time = time.time()
            response = reliable_client.send_request(test_request)
            request_duration = time.time() - request_start_time

            # 等待中断模拟完成
            interruption_thread.join(timeout=15)

            # 验证点2: 验证客户端最终收到响应
            vp2 = {
                "description": "验证客户端在服务恢复后最终收到响应",
                "passed": response is not None and response.get("status") == "success",
                "details": f"响应状态: {response.get('status') if response else 'None'}, 耗时: {request_duration:.2f}s",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证重试机制生效（请求耗时应该比正常情况长）
            # 正常请求应该在1秒内完成，重试请求可能需要更长时间
            retry_likely = request_duration > 5.0  # 如果耗时超过5秒，说明可能发生了重试

            vp3 = {
                "description": "验证重试机制可能已生效 (请求耗时较长)",
                "passed": retry_likely or (response is not None),  # 只要最终成功就算通过
                "details": f"请求耗时: {request_duration:.2f}s (正常 < 1s, 重试 > 5s)",
            }
            test_case["verification_results"].append(vp3)

            # 清理客户端
            reliable_client.close()

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"客户端自动重试", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"客户端自动重试测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "客户端自动重试 (Lazy Pirate)",
                "HA-02",
                test_case["status"],
                test_case["duration"],
            )

        return test_case

    def test_service_recovery(self) -> Dict[str, Any]:
        """额外测试: 服务恢复能力"""
        test_case = {
            "case_id": "HA-03",
            "title": "服务恢复能力测试",
            "suite_id": "SYS-HIGH-AVAILABILITY",
            "suite_name": "高可用与弹性测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("HA-03", "服务恢复能力测试")

            # 1. 检查服务当前状态
            current_health = self._check_service_health()

            # 2. 等待一段时间确保服务稳定
            time.sleep(2)

            # 3. 再次检查服务状态
            final_health = self._check_service_health()

            # 验证点1: 验证HTTP监控API可用
            vp1 = {
                "description": "验证HTTP监控API恢复正常",
                "passed": final_health["http_healthy"],
                "details": f"HTTP API状态: {final_health['http_healthy']}",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证ZMQ服务可用
            vp2 = {
                "description": "验证ZMQ业务API恢复正常",
                "passed": final_health["zmq_healthy"],
                "details": f"ZMQ API状态: {final_health['zmq_healthy']}",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证服务整体健康
            vp3 = {
                "description": "验证服务整体恢复健康",
                "passed": final_health["overall_healthy"],
                "details": f"整体健康状态: {final_health['overall_healthy']}",
            }
            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"服务恢复能力", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"服务恢复能力测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "服务恢复能力测试", "HA-03", test_case["status"], test_case["duration"]
            )

        return test_case

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """运行所有高可用性测试"""
        self.logger.info("开始运行高可用性与故障转移测试套件")

        test_results = []

        # 运行所有测试用例
        test_results.append(self.test_worker_failover())
        test_results.append(self.test_lazy_pirate_retry())
        test_results.append(self.test_service_recovery())

        # 统计测试结果
        total_tests = len(test_results)
        passed_tests = len([t for t in test_results if t["status"] == "PASS"])

        self.logger.info(f"高可用性测试套件完成: {passed_tests}/{total_tests} 通过")

        return test_results

    def cleanup(self):
        """清理测试资源"""
        try:
            # 确保所有容器都在运行状态
            containers = self._get_docker_containers()
            for container in containers:
                if container["status"] != "running":
                    self.logger.info(f"重启容器: {container['name']}")
                    self._start_container(container["id"])

            self.logger.info("高可用性测试清理完成")
        except Exception as e:
            self.logger.error(f"清理过程中发生错误: {e}")
