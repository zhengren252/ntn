# 负载均衡与可扩展性测试
# Load Balancing and Scalability Tests

import zmq
import json
import time
import threading
import concurrent.futures
from collections import defaultdict, Counter
from typing import Dict, Any, List, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.test_logger import TestLogger
from utils.test_helpers import TestHelpers
from config import AcceptanceTestConfig as TestConfig
from tests.test_zmq_business_api import LazyPirateClient


class LoadBalancingTests:
    """负载均衡与可扩展性测试套件"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("load_balancing_tests")
        self.helpers = TestHelpers()

    def _send_concurrent_requests(
        self, num_requests: int, request_template: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """并发发送多个请求"""
        results = []

        def send_single_request(request_id: str) -> Dict[str, Any]:
            client = LazyPirateClient(
                self.config.ZMQ_ENDPOINT,
                timeout=self.config.ZMQ_TIMEOUT,
                retries=1,  # 减少重试次数以加快测试
            )

            try:
                request = request_template.copy()
                request["request_id"] = request_id

                start_time = time.time()
                response = client.send_request(request)
                end_time = time.time()

                return {
                    "request_id": request_id,
                    "response": response,
                    "duration": end_time - start_time,
                    "success": response is not None
                    and response.get("status") == "success",
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "response": None,
                    "duration": 0,
                    "success": False,
                    "error": str(e),
                }
            finally:
                client.close()

        # 使用线程池并发发送请求
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(num_requests, 10)
        ) as executor:
            futures = []
            for i in range(num_requests):
                request_id = f"load_test_{i}_{int(time.time() * 1000)}"
                future = executor.submit(send_single_request, request_id)
                futures.append(future)

            # 收集结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"并发请求异常: {e}")
                    results.append(
                        {
                            "request_id": "unknown",
                            "response": None,
                            "duration": 0,
                            "success": False,
                            "error": str(e),
                        }
                    )

        return results

    def test_request_distribution(self) -> Dict[str, Any]:
        """测试用例: LB-01 - 请求分发验证"""
        test_case = {
            "case_id": "LB-01",
            "title": "请求分发验证",
            "suite_id": "PERF-LOAD-BALANCING",
            "suite_name": "负载均衡与可扩展性测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("LB-01", "请求分发验证")

            # 准备测试请求模板
            request_template = {
                "method": "scan.market",
                "params": {
                    "market_type": "crypto",
                    "symbols": ["BTC/USDT"],
                    "scan_type": "opportunities",
                },
            }

            # 并发发送20个请求
            num_requests = 20
            self.logger.log_test_step(f"并发发送 {num_requests} 个请求")

            results = self._send_concurrent_requests(num_requests, request_template)

            # 验证点1: 验证大部分请求成功
            successful_requests = [r for r in results if r["success"]]
            success_rate = len(successful_requests) / len(results) if results else 0

            vp1 = {
                "description": "验证大部分请求成功 (成功率 >= 80%)",
                "passed": success_rate >= 0.8,
                "details": f"成功率: {success_rate:.1%} ({len(successful_requests)}/{len(results)})",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 分析响应时间分布（检查是否有负载均衡效果）
            if successful_requests:
                durations = [r["duration"] for r in successful_requests]
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)

                # 如果有负载均衡，响应时间应该相对稳定
                duration_variance = max_duration - min_duration
                reasonable_variance = duration_variance < (
                    avg_duration * 2
                )  # 方差不应超过平均值的2倍

                vp2 = {
                    "description": "验证响应时间分布合理 (表明负载均衡有效)",
                    "passed": reasonable_variance,
                    "details": f"平均: {avg_duration:.3f}s, 最大: {max_duration:.3f}s, 最小: {min_duration:.3f}s, 方差: {duration_variance:.3f}s",
                }
            else:
                vp2 = {
                    "description": "验证响应时间分布合理 (表明负载均衡有效)",
                    "passed": False,
                    "details": "没有成功的请求，无法分析响应时间",
                }

            test_case["verification_results"].append(vp2)

            # 验证点3: 检查请求ID的唯一性（确保没有重复处理）
            response_request_ids = []
            for r in successful_requests:
                if r["response"] and "request_id" in r["response"]:
                    response_request_ids.append(r["response"]["request_id"])

            unique_ids = len(set(response_request_ids))
            all_unique = unique_ids == len(response_request_ids)

            vp3 = {
                "description": "验证请求ID唯一性 (无重复处理)",
                "passed": all_unique,
                "details": f"唯一ID数: {unique_ids}, 总响应数: {len(response_request_ids)}",
            }
            test_case["verification_results"].append(vp3)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"请求分发验证", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"请求分发验证异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "请求分发验证", "LB-01", test_case["status"], test_case["duration"]
            )

        return test_case

    def test_horizontal_scaling(self) -> Dict[str, Any]:
        """测试用例: SCALE-01 - 水平扩展能力验证"""
        test_case = {
            "case_id": "SCALE-01",
            "title": "水平扩展能力验证",
            "suite_id": "PERF-LOAD-BALANCING",
            "suite_name": "负载均衡与可扩展性测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("SCALE-01", "水平扩展能力验证")

            # 准备测试请求模板
            request_template = {
                "method": "evaluate.risk",
                "params": {
                    "portfolio": {"BTC": 0.1, "ETH": 1.0, "USDT": 5000},
                    "market_conditions": "volatile",
                    "risk_tolerance": "medium",
                },
            }

            # 执行压力测试（模拟不同worker数量的性能）
            test_duration = 15  # 15秒测试时间

            self.logger.log_test_step(f"执行 {test_duration} 秒压力测试")

            # 记录开始时间
            test_start = time.time()
            successful_requests = 0
            total_requests = 0

            # 持续发送请求直到测试时间结束
            while time.time() - test_start < test_duration:
                batch_size = 5  # 每批发送5个请求
                batch_results = self._send_concurrent_requests(
                    batch_size, request_template
                )

                total_requests += len(batch_results)
                successful_requests += len([r for r in batch_results if r["success"]])

                # 短暂休息避免过度负载
                time.sleep(0.1)

            actual_duration = time.time() - test_start
            throughput = (
                successful_requests / actual_duration if actual_duration > 0 else 0
            )

            # 验证点1: 验证系统能够处理持续负载
            vp1 = {
                "description": "验证系统能够处理持续负载",
                "passed": successful_requests > 0,
                "details": f"成功处理 {successful_requests}/{total_requests} 个请求",
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证吞吐量合理
            min_expected_throughput = 1.0  # 至少每秒1个请求
            vp2 = {
                "description": f"验证吞吐量合理 (>= {min_expected_throughput} req/s)",
                "passed": throughput >= min_expected_throughput,
                "details": f"实际吞吐量: {throughput:.2f} req/s",
            }
            test_case["verification_results"].append(vp2)

            # 验证点3: 验证成功率
            success_rate = (
                successful_requests / total_requests if total_requests > 0 else 0
            )
            vp3 = {
                "description": "验证成功率合理 (>= 70%)",
                "passed": success_rate >= 0.7,
                "details": f"成功率: {success_rate:.1%}",
            }
            test_case["verification_results"].append(vp3)

            # 注意：由于这是单一测试环境，我们无法真正测试水平扩展
            # 这里主要验证系统在负载下的稳定性
            self.logger.log_test_step("注意: 真正的水平扩展测试需要修改docker-compose.yml中的replicas设置")

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"水平扩展能力验证", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"水平扩展能力验证异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "水平扩展能力验证", "SCALE-01", test_case["status"], test_case["duration"]
            )

        return test_case

    def test_performance_under_load(self) -> Dict[str, Any]:
        """额外测试: 负载下的性能表现"""
        test_case = {
            "case_id": "PERF-01",
            "title": "负载下的性能表现",
            "suite_id": "PERF-LOAD-BALANCING",
            "suite_name": "负载均衡与可扩展性测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("PERF-01", "负载下的性能表现")

            # 测试不同类型的请求
            test_scenarios = [
                {
                    "name": "轻量级请求 (scan.market)",
                    "request": {
                        "method": "scan.market",
                        "params": {
                            "market_type": "crypto",
                            "symbols": ["BTC/USDT"],
                            "scan_type": "opportunities",
                        },
                    },
                    "count": 10,
                },
                {
                    "name": "中等复杂度请求 (evaluate.risk)",
                    "request": {
                        "method": "evaluate.risk",
                        "params": {
                            "portfolio": {"BTC": 0.1, "USDT": 1000},
                            "market_conditions": "stable",
                            "risk_tolerance": "low",
                        },
                    },
                    "count": 8,
                },
            ]

            scenario_results = []

            for scenario in test_scenarios:
                self.logger.log_test_step(f"测试场景: {scenario['name']}")

                scenario_start = time.time()
                results = self._send_concurrent_requests(
                    scenario["count"], scenario["request"]
                )
                scenario_duration = time.time() - scenario_start

                successful = [r for r in results if r["success"]]
                success_rate = len(successful) / len(results) if results else 0

                if successful:
                    avg_response_time = sum(r["duration"] for r in successful) / len(
                        successful
                    )
                    throughput = len(successful) / scenario_duration
                else:
                    avg_response_time = 0
                    throughput = 0

                scenario_results.append(
                    {
                        "name": scenario["name"],
                        "success_rate": success_rate,
                        "avg_response_time": avg_response_time,
                        "throughput": throughput,
                        "total_requests": len(results),
                    }
                )

            # 验证点1: 验证所有场景的成功率
            overall_success = all(sr["success_rate"] >= 0.7 for sr in scenario_results)
            success_details = "; ".join(
                [f"{sr['name']}: {sr['success_rate']:.1%}" for sr in scenario_results]
            )

            vp1 = {
                "description": "验证所有测试场景的成功率 (>= 70%)",
                "passed": overall_success,
                "details": success_details,
            }
            test_case["verification_results"].append(vp1)

            # 验证点2: 验证响应时间合理
            reasonable_response_times = all(
                sr["avg_response_time"] < 10.0
                for sr in scenario_results
                if sr["avg_response_time"] > 0
            )
            response_details = "; ".join(
                [
                    f"{sr['name']}: {sr['avg_response_time']:.3f}s"
                    for sr in scenario_results
                ]
            )

            vp2 = {
                "description": "验证平均响应时间合理 (< 10s)",
                "passed": reasonable_response_times,
                "details": response_details,
            }
            test_case["verification_results"].append(vp2)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"负载下的性能表现", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"负载下的性能表现异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "负载下的性能表现", "PERF-01", test_case["status"], test_case["duration"]
            )

        return test_case

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """运行所有负载均衡和可扩展性测试"""
        self.logger.info("开始运行负载均衡与可扩展性测试套件")

        test_results = []

        # 运行所有测试用例
        test_results.append(self.test_request_distribution())
        test_results.append(self.test_horizontal_scaling())
        test_results.append(self.test_performance_under_load())

        self.logger.info(f"负载均衡与可扩展性测试套件完成，共运行 {len(test_results)} 个测试用例")

        return test_results

    def cleanup(self):
        """清理测试资源"""
        try:
            self.logger.info("开始清理负载均衡测试资源")

            # 等待所有正在进行的请求完成
            time.sleep(2)

            # 清理可能的ZMQ连接
            # 注意：由于测试中使用的是临时客户端连接，通常会自动清理
            # 这里主要是确保没有遗留的连接或资源

            self.logger.info("负载均衡测试资源清理完成")

        except Exception as e:
            self.logger.error(f"清理负载均衡测试资源时发生异常: {e}")
