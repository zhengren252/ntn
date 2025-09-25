import os
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体驱动交易系统 V3.5 升级后回归测试
基于回归测试清单执行自动化测试
"""

import zmq
import json
import time
import threading
import statistics
from datetime import datetime
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed


class RegressionTester:
    def __init__(self, service_endpoint: str = "tcp://localhost:5555"):
        self.service_endpoint = service_endpoint
        self.test_results = []
        self.performance_data = []
        self.start_time = None
        self.end_time = None

    def create_connection(self) -> zmq.Socket:
        """创建ZMQ连接"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        socket.setsockopt(zmq.SNDTIMEO, 5000)
        socket.connect(self.service_endpoint)
        return socket

    def send_request(
        self, socket: zmq.Socket, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送请求并测量响应时间"""
        request_id = int(time.time() * 1000000)  # 微秒级ID
        request = {"id": request_id, "method": method, "params": params or {}}

        start_time = time.time()
        try:
            socket.send_json(request)
            response = socket.recv_json()
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            # 记录性能数据
            self.performance_data.append(
                {
                    "method": method,
                    "response_time_ms": response_time,
                    "timestamp": datetime.now().isoformat(),
                    "success": "result" in response,
                }
            )

            return response
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            self.performance_data.append(
                {
                    "method": method,
                    "response_time_ms": response_time,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e),
                }
            )

            return {"error": str(e)}

    def test_data_flow_integrity(self) -> Dict[str, Any]:
        """第一部分：数据链路测试"""
        print("\n🔄 执行数据链路测试...")

        socket = self.create_connection()
        test_results = []

        try:
            # 1. 系统健康检查
            print("  1.1 系统健康检查...")
            response = self.send_request(socket, "system.health")
            health_ok = (
                "result" in response and response["result"].get("status") == "healthy"
            )
            test_results.append(
                {"test": "system_health", "passed": health_ok, "response": response}
            )

            if not health_ok:
                print("  ❌ 系统健康检查失败，停止数据链路测试")
                return {
                    "status": "failed",
                    "reason": "system_unhealthy",
                    "results": test_results,
                }

            # 2. 市场扫描
            print("  1.2 市场扫描测试...")
            scan_params = {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "indicators": ["RSI", "MACD"],
            }
            scan_response = self.send_request(socket, "scan.market", scan_params)
            scan_ok = "result" in scan_response and "signals" in scan_response["result"]
            test_results.append(
                {"test": "market_scan", "passed": scan_ok, "response": scan_response}
            )

            # 3. 交易执行
            print("  1.3 交易执行测试...")
            trade_params = {
                "symbol": "BTCUSDT",
                "side": "buy",
                "amount": 0.001,
                "price": 45000,
                "type": "limit",
            }
            trade_response = self.send_request(socket, "trade.execute", trade_params)
            trade_ok = (
                "result" in trade_response and "order_id" in trade_response["result"]
            )
            test_results.append(
                {
                    "test": "trade_execute",
                    "passed": trade_ok,
                    "response": trade_response,
                }
            )

            # 4. 风险评估
            print("  1.4 风险评估测试...")
            risk_params = {
                "portfolio": {"BTCUSDT": {"amount": 0.5, "value": 22500}},
                "market_conditions": "volatile",
            }
            risk_response = self.send_request(socket, "risk.assess", risk_params)
            risk_ok = (
                "result" in risk_response and "risk_score" in risk_response["result"]
            )
            test_results.append(
                {"test": "risk_assess", "passed": risk_ok, "response": risk_response}
            )

            # 5. 资金分配
            print("  1.5 资金分配测试...")
            fund_params = {
                "total_capital": 100000,
                "risk_tolerance": "medium",
                "strategies": ["momentum"],
            }
            fund_response = self.send_request(socket, "fund.allocate", fund_params)
            fund_ok = (
                "result" in fund_response and "allocation" in fund_response["result"]
            )
            test_results.append(
                {"test": "fund_allocate", "passed": fund_ok, "response": fund_response}
            )

            passed_count = sum(1 for result in test_results if result["passed"])
            total_count = len(test_results)

            print(f"  ✅ 数据链路测试完成: {passed_count}/{total_count} 通过")

            return {
                "status": "passed" if passed_count == total_count else "partial",
                "passed": passed_count,
                "total": total_count,
                "results": test_results,
            }

        finally:
            socket.close()

    def test_interface_response(self) -> Dict[str, Any]:
        """第二部分：接口响应测试"""
        print("\n📡 执行接口响应测试...")

        socket = self.create_connection()
        test_results = []

        try:
            # 测试各种请求类型
            test_cases = [
                ("system.health", {}),
                ("scan.market", {"symbol": "ETHUSDT", "timeframe": "5m"}),
                ("trade.execute", {"symbol": "ETHUSDT", "side": "sell", "amount": 0.1}),
                ("risk.assess", {"portfolio": {}}),
                ("fund.allocate", {"total_capital": 50000}),
            ]

            for i, (method, params) in enumerate(test_cases, 1):
                print(f"  2.{i} 测试 {method}...")
                response = self.send_request(socket, method, params)

                # 检查响应格式
                has_id = "id" in response
                has_result_or_error = "result" in response or "error" in response

                test_results.append(
                    {
                        "test": f"interface_{method.replace('.', '_')}",
                        "passed": has_id and has_result_or_error,
                        "response_format_ok": has_id and has_result_or_error,
                        "response": response,
                    }
                )

            # 测试错误处理
            print("  2.6 测试错误处理...")
            error_response = self.send_request(socket, "invalid.method", {})
            error_ok = "error" in error_response
            test_results.append(
                {
                    "test": "error_handling",
                    "passed": error_ok,
                    "response": error_response,
                }
            )

            passed_count = sum(1 for result in test_results if result["passed"])
            total_count = len(test_results)

            print(f"  ✅ 接口响应测试完成: {passed_count}/{total_count} 通过")

            return {
                "status": "passed" if passed_count == total_count else "partial",
                "passed": passed_count,
                "total": total_count,
                "results": test_results,
            }

        finally:
            socket.close()

    def test_performance(self) -> Dict[str, Any]:
        """第四部分：性能测试"""
        print("\n⚡ 执行性能测试...")

        # 清空之前的性能数据
        self.performance_data = []

        # 单线程性能测试
        socket = self.create_connection()

        try:
            print("  4.1 单请求性能测试...")
            for i in range(10):
                self.send_request(socket, "system.health")
                self.send_request(socket, "scan.market", {"symbol": "BTCUSDT"})
                time.sleep(0.1)

        finally:
            socket.close()

        # 并发性能测试
        print("  4.2 并发性能测试...")

        def concurrent_request(thread_id):
            socket = self.create_connection()
            try:
                for i in range(5):
                    self.send_request(socket, "system.health")
                    time.sleep(0.05)
                return f"Thread {thread_id} completed"
            finally:
                socket.close()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_request, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        # 分析性能数据
        if self.performance_data:
            response_times = [
                data["response_time_ms"]
                for data in self.performance_data
                if data["success"]
            ]

            if response_times:
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)

                performance_ok = avg_response_time < 1000  # 平均响应时间小于1秒

                print(f"  📊 性能统计:")
                print(f"     平均响应时间: {avg_response_time:.2f}ms")
                print(f"     最大响应时间: {max_response_time:.2f}ms")
                print(f"     最小响应时间: {min_response_time:.2f}ms")
                print(f"     总请求数: {len(self.performance_data)}")
                print(
                    f"     成功率: {len(response_times)/len(self.performance_data)*100:.1f}%"
                )

                return {
                    "status": "passed" if performance_ok else "failed",
                    "avg_response_time_ms": avg_response_time,
                    "max_response_time_ms": max_response_time,
                    "min_response_time_ms": min_response_time,
                    "total_requests": len(self.performance_data),
                    "success_rate": len(response_times)
                    / len(self.performance_data)
                    * 100,
                    "performance_ok": performance_ok,
                }

        return {"status": "failed", "reason": "no_performance_data"}

    def test_stability(self) -> Dict[str, Any]:
        """第五部分：稳定性测试（简化版）"""
        print("\n🛡️ 执行稳定性测试...")

        test_results = []

        # 连续请求测试
        print("  5.1 连续请求稳定性测试...")
        socket = self.create_connection()

        try:
            success_count = 0
            total_requests = 50

            for i in range(total_requests):
                response = self.send_request(socket, "system.health")
                if "result" in response:
                    success_count += 1
                time.sleep(0.1)

            stability_ok = success_count / total_requests > 0.95  # 95%成功率

            test_results.append(
                {
                    "test": "continuous_requests",
                    "passed": stability_ok,
                    "success_rate": success_count / total_requests * 100,
                    "total_requests": total_requests,
                }
            )

            print(
                f"     连续请求成功率: {success_count}/{total_requests} ({success_count/total_requests*100:.1f}%)"
            )

        finally:
            socket.close()

        # 错误恢复测试
        print("  5.2 错误恢复测试...")
        socket = self.create_connection()

        try:
            # 发送错误请求
            error_response = self.send_request(socket, "invalid.method")

            # 发送正常请求验证恢复
            normal_response = self.send_request(socket, "system.health")

            recovery_ok = "error" in error_response and "result" in normal_response

            test_results.append(
                {
                    "test": "error_recovery",
                    "passed": recovery_ok,
                    "error_handled": "error" in error_response,
                    "recovery_successful": "result" in normal_response,
                }
            )

            print(f"     错误恢复测试: {'✅ 通过' if recovery_ok else '❌ 失败'}")

        finally:
            socket.close()

        passed_count = sum(1 for result in test_results if result["passed"])
        total_count = len(test_results)

        print(f"  ✅ 稳定性测试完成: {passed_count}/{total_count} 通过")

        return {
            "status": "passed" if passed_count == total_count else "partial",
            "passed": passed_count,
            "total": total_count,
            "results": test_results,
        }

    def run_full_regression_test(self) -> Dict[str, Any]:
        """运行完整的回归测试"""
        print("🚀 开始AI智能体驱动交易系统V3.5回归测试")
        print("=" * 60)
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.start_time = time.time()

        # 执行各项测试
        test_sections = [
            ("数据链路测试", self.test_data_flow_integrity),
            ("接口响应测试", self.test_interface_response),
            ("性能测试", self.test_performance),
            ("稳定性测试", self.test_stability),
        ]

        section_results = []

        for section_name, test_func in test_sections:
            try:
                print(f"\n📋 执行 {section_name}...")
                result = test_func()
                result["section"] = section_name
                section_results.append(result)

                if result["status"] == "passed":
                    print(f"✅ {section_name} 全部通过")
                elif result["status"] == "partial":
                    print(f"⚠️ {section_name} 部分通过")
                else:
                    print(f"❌ {section_name} 失败")

            except Exception as e:
                print(f"❌ {section_name} 执行异常: {e}")
                section_results.append(
                    {"section": section_name, "status": "error", "error": str(e)}
                )

        self.end_time = time.time()
        test_duration = self.end_time - self.start_time

        # 生成测试报告
        print("\n" + "=" * 60)
        print("📊 回归测试结果汇总")
        print("=" * 60)

        total_passed = 0
        total_tests = 0

        for result in section_results:
            section = result["section"]
            status = result["status"]

            if "passed" in result and "total" in result:
                passed = result["passed"]
                total = result["total"]
                total_passed += passed
                total_tests += total
                print(
                    f"{section:20} | {passed:2}/{total:2} | {status:8} | {passed/total*100:5.1f}%"
                )
            else:
                print(f"{section:20} | --/-- | {status:8} | -----%")

        overall_success_rate = (
            (total_passed / total_tests * 100) if total_tests > 0 else 0
        )

        print("-" * 60)
        print(
            f"{'总计':20} | {total_passed:2}/{total_tests:2} | {'':8} | {overall_success_rate:5.1f}%"
        )
        print(f"测试耗时: {test_duration:.2f}秒")
        print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 判断整体测试结果
        if overall_success_rate >= 95:
            overall_status = "passed"
            print("\n🎉 回归测试通过！系统升级成功，建议投入生产使用。")
        elif overall_success_rate >= 80:
            overall_status = "partial"
            print("\n⚠️ 回归测试部分通过，需解决部分问题后投产。")
        else:
            overall_status = "failed"
            print("\n❌ 回归测试失败，需要重新评估和修复。")

        return {
            "overall_status": overall_status,
            "success_rate": overall_success_rate,
            "total_passed": total_passed,
            "total_tests": total_tests,
            "test_duration_seconds": test_duration,
            "section_results": section_results,
            "performance_data": self.performance_data,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
        }


def main():
    """主函数"""
    tester = RegressionTester()

    try:
        result = tester.run_full_regression_test()

        # 保存测试报告
        report_filename = (
            f"regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n📄 测试报告已保存到: {report_filename}")

        return result["overall_status"] == "passed"

    except KeyboardInterrupt:
        print("\n用户中断测试")
        return False
    except Exception as e:
        print(f"\n测试过程中出现异常: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
