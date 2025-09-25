#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TACoreService 单独测试脚本
专门测试 TACoreService 的功能和性能
"""

import zmq
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tacore_test")


class TACoreServiceTester:
    """TACoreService 测试器"""

    def __init__(self, service_url: str = "tcp://localhost:5555"):
        self.service_url = service_url
        self.context = None
        self.socket = None
        self.test_results = []

    def connect(self) -> bool:
        """连接到 TACoreService"""
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            self.socket.connect(self.service_url)
            logger.info(f"已连接到 TACoreService: {self.service_url}")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        logger.info("已断开连接")

    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并接收响应"""
        try:
            # 发送请求
            self.socket.send_json(request)

            # 接收响应
            response = self.socket.recv_json()
            return response
        except zmq.Again:
            logger.error("请求超时")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return {"error": str(e)}

    def test_health_check(self) -> bool:
        """测试健康检查"""
        logger.info("测试健康检查...")
        start_time = time.time()

        request = {"method": "health.check", "timestamp": datetime.now().isoformat()}

        response = self.send_request(request)
        duration = time.time() - start_time

        success = (
            response.get("status") == "success"
            and response.get("result", {}).get("status") == "healthy"
        )

        result = {
            "test_name": "health_check",
            "success": success,
            "duration": round(duration, 3),
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }

        self.test_results.append(result)

        if success:
            logger.info(f"✓ 健康检查通过 (响应时间: {duration:.3f}s)")
        else:
            logger.error(f"✗ 健康检查失败: {response}")

        return success

    def test_scan_market(self) -> bool:
        """测试市场扫描功能"""
        logger.info("测试市场扫描功能...")
        start_time = time.time()

        request = {
            "method": "scan.market",
            "params": {
                "market_type": "spot",
                "filters": {"min_volume": 1000000, "max_symbols": 10},
            },
            "timestamp": datetime.now().isoformat(),
        }

        response = self.send_request(request)
        duration = time.time() - start_time

        success = response.get("status") == "success" and "result" in response

        result = {
            "test_name": "scan_market",
            "success": success,
            "duration": round(duration, 3),
            "response_size": len(str(response)),
            "symbols_count": len(response.get("data", [])) if success else 0,
            "timestamp": datetime.now().isoformat(),
        }

        self.test_results.append(result)

        if success:
            symbols_count = len(response.get("data", []))
            logger.info(f"✓ 市场扫描成功 (找到 {symbols_count} 个交易对, 响应时间: {duration:.3f}s)")
        else:
            logger.error(f"✗ 市场扫描失败: {response}")

        return success

    def test_analyze_symbol(self) -> bool:
        """测试交易对分析功能"""
        logger.info("测试交易对分析功能...")
        start_time = time.time()

        request = {
            "method": "analyze.symbol",
            "params": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "analysis_type": "technical",
            },
            "timestamp": datetime.now().isoformat(),
        }

        response = self.send_request(request)
        duration = time.time() - start_time

        success = response.get("status") == "success" and "result" in response

        result = {
            "test_name": "analyze_symbol",
            "success": success,
            "duration": round(duration, 3),
            "symbol": "BTCUSDT",
            "analysis_data": response.get("data", {}) if success else None,
            "timestamp": datetime.now().isoformat(),
        }

        self.test_results.append(result)

        if success:
            logger.info(f"✓ 交易对分析成功 (BTCUSDT, 响应时间: {duration:.3f}s)")
        else:
            logger.error(f"✗ 交易对分析失败: {response}")

        return success

    def test_get_market_data(self) -> bool:
        """测试市场数据获取功能"""
        logger.info("测试市场数据获取功能...")
        start_time = time.time()

        request = {
            "method": "get.market_data",
            "params": {"symbol": "ETHUSDT", "interval": "1h", "limit": 100},
            "timestamp": datetime.now().isoformat(),
        }

        response = self.send_request(request)
        duration = time.time() - start_time

        success = response.get("status") == "success" and "result" in response

        result = {
            "test_name": "get_market_data",
            "success": success,
            "duration": round(duration, 3),
            "symbol": "ETHUSDT",
            "data_points": len(response.get("data", [])) if success else 0,
            "timestamp": datetime.now().isoformat(),
        }

        self.test_results.append(result)

        if success:
            data_points = len(response.get("data", []))
            logger.info(
                f"✓ 市场数据获取成功 (ETHUSDT, {data_points} 个数据点, 响应时间: {duration:.3f}s)"
            )
        else:
            logger.error(f"✗ 市场数据获取失败: {response}")

        return success

    def test_performance(self) -> Dict[str, Any]:
        """性能测试"""
        logger.info("开始性能测试...")

        # 连续发送多个请求测试性能
        request_count = 10
        successful_requests = 0
        total_time = 0

        for i in range(request_count):
            start_time = time.time()

            request = {
                "method": "health.check",
                "timestamp": datetime.now().isoformat(),
            }

            response = self.send_request(request)
            duration = time.time() - start_time
            total_time += duration

            if (
                response.get("status") == "success"
                and response.get("result", {}).get("status") == "healthy"
            ):
                successful_requests += 1

        avg_response_time = total_time / request_count
        success_rate = successful_requests / request_count

        performance_result = {
            "test_name": "performance_test",
            "total_requests": request_count,
            "successful_requests": successful_requests,
            "success_rate": round(success_rate * 100, 2),
            "average_response_time": round(avg_response_time, 3),
            "total_time": round(total_time, 3),
            "timestamp": datetime.now().isoformat(),
        }

        self.test_results.append(performance_result)

        logger.info(
            f"性能测试完成: 成功率 {success_rate*100:.1f}%, 平均响应时间 {avg_response_time:.3f}s"
        )

        return performance_result

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("开始 TACoreService 功能测试")
        logger.info("=" * 50)

        # 连接服务
        if not self.connect():
            return {
                "success": False,
                "error": "无法连接到 TACoreService",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # 运行各项测试
            tests = [
                self.test_health_check,
                self.test_scan_market,
                self.test_analyze_symbol,
                self.test_get_market_data,
            ]

            passed_tests = 0
            total_tests = len(tests)

            for test in tests:
                if test():
                    passed_tests += 1
                time.sleep(0.5)  # 测试间隔

            # 性能测试
            self.test_performance()

            # 生成测试报告
            test_summary = {
                "success": passed_tests == total_tests,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": round((passed_tests / total_tests) * 100, 2),
                "test_results": self.test_results,
                "timestamp": datetime.now().isoformat(),
                "service_url": self.service_url,
            }

            return test_summary

        finally:
            self.disconnect()

    def generate_report(self, results: Dict[str, Any]):
        """生成测试报告"""
        logger.info("\n" + "=" * 60)
        logger.info("TACoreService 测试报告")
        logger.info("=" * 60)

        if results.get("success"):
            logger.info(f"✓ 测试状态: 通过")
        else:
            logger.error(f"✗ 测试状态: 失败")

        logger.info(f"总测试数: {results.get('total_tests', 0)}")
        logger.info(f"通过测试: {results.get('passed_tests', 0)}")
        logger.info(f"失败测试: {results.get('failed_tests', 0)}")
        logger.info(f"成功率: {results.get('success_rate', 0)}%")
        logger.info(f"服务地址: {results.get('service_url', 'N/A')}")

        logger.info("\n详细测试结果:")
        for result in results.get("test_results", []):
            test_name = result.get("test_name", "Unknown")
            success = result.get("success", False)
            duration = result.get("duration", 0)

            status = "✓" if success else "✗"
            logger.info(f"{status} {test_name}: {duration}s")

        logger.info("=" * 60)


def main():
    """主函数"""
    tester = TACoreServiceTester()

    try:
        # 运行测试
        results = tester.run_all_tests()

        # 生成报告
        tester.generate_report(results)

        # 保存结果到文件
        with open("tacore-test-results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n测试结果已保存到: tacore-test-results.json")

        # 返回适当的退出码
        return 0 if results.get("success") else 1

    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
