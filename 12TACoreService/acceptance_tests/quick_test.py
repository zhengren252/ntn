#!/usr/bin/env python3
# 快速测试脚本
# Quick Test Script

import os
import sys
import time
import subprocess
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AcceptanceTestConfig as TestConfig
from utils.test_logger import TestLogger
from tests.test_zmq_business_api import ZMQBusinessAPITests
from tests.test_http_monitoring_api import HTTPMonitoringAPITests


class QuickTestRunner:
    """快速测试运行器 - 用于基本功能验证"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("quick_test")

    def check_service_status(self) -> bool:
        """检查服务状态"""
        self.logger.info("检查TACoreService服务状态...")

        try:
            # 检查HTTP监控API
            http_tests = HTTPMonitoringAPITests()
            status_result = http_tests.test_service_status()

            if status_result["status"] == "PASS":
                self.logger.info("✓ HTTP监控API正常")
            else:
                self.logger.error("✗ HTTP监控API异常")
                return False

            # 检查ZMQ业务API
            zmq_tests = ZMQBusinessAPITests()
            scan_result = zmq_tests.test_scan_market_success()

            if scan_result["status"] == "PASS":
                self.logger.info("✓ ZMQ业务API正常")
            else:
                self.logger.error("✗ ZMQ业务API异常")
                return False

            return True

        except Exception as e:
            self.logger.error(f"服务状态检查失败: {e}")
            return False

    def run_basic_tests(self) -> bool:
        """运行基本功能测试"""
        self.logger.info("运行基本功能测试...")

        try:
            # ZMQ API基本测试
            zmq_tests = ZMQBusinessAPITests()
            zmq_results = [
                zmq_tests.test_scan_market_success(),
                zmq_tests.test_execute_order_success(),
                zmq_tests.test_evaluate_risk_success(),
                zmq_tests.test_invalid_method(),
            ]

            # HTTP API基本测试
            http_tests = HTTPMonitoringAPITests()
            http_results = [
                http_tests.test_service_status(),
                http_tests.test_workers_list(),
                http_tests.test_logs_retrieval(),
            ]

            all_results = zmq_results + http_results
            passed_tests = len([r for r in all_results if r["status"] == "PASS"])
            total_tests = len(all_results)

            self.logger.info(f"基本测试完成: {passed_tests}/{total_tests} 通过")

            if passed_tests == total_tests:
                self.logger.info("✓ 所有基本测试通过")
                return True
            else:
                self.logger.error(f"✗ {total_tests - passed_tests} 个测试失败")
                return False

        except Exception as e:
            self.logger.error(f"基本测试运行失败: {e}")
            return False

    def check_docker_services(self) -> bool:
        """检查Docker服务状态"""
        self.logger.info("检查Docker服务状态...")

        try:
            # 检查Docker Compose服务
            result = subprocess.run(
                ["docker-compose", "ps", "--services", "--filter", "status=running"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                running_services = (
                    result.stdout.strip().split("\n") if result.stdout.strip() else []
                )
                self.logger.info(
                    f"运行中的服务: {', '.join(running_services) if running_services else '无'}"
                )

                # 检查关键服务
                required_services = ["tacoreservice", "redis", "worker"]
                missing_services = []

                for service in required_services:
                    if not any(
                        service in running_service
                        for running_service in running_services
                    ):
                        missing_services.append(service)

                if missing_services:
                    self.logger.error(f"缺少关键服务: {', '.join(missing_services)}")
                    return False
                else:
                    self.logger.info("✓ 所有关键服务正在运行")
                    return True
            else:
                self.logger.error(f"Docker Compose检查失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Docker服务检查超时")
            return False
        except Exception as e:
            self.logger.error(f"Docker服务检查异常: {e}")
            return False

    def run_quick_test(self) -> bool:
        """运行快速测试"""
        self.logger.info("=" * 60)
        self.logger.info("TACoreService 快速测试")
        self.logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)

        start_time = time.time()

        # 1. 检查Docker服务
        if not self.check_docker_services():
            self.logger.error("Docker服务检查失败，请确保服务正在运行")
            return False

        # 等待服务启动
        self.logger.info("等待服务完全启动...")
        time.sleep(3)

        # 2. 检查服务状态
        if not self.check_service_status():
            self.logger.error("服务状态检查失败")
            return False

        # 3. 运行基本测试
        if not self.run_basic_tests():
            self.logger.error("基本功能测试失败")
            return False

        duration = time.time() - start_time

        self.logger.info("=" * 60)
        self.logger.info("快速测试完成")
        self.logger.info(f"总耗时: {duration:.2f}s")
        self.logger.info("✓ TACoreService 基本功能正常")
        self.logger.info("=" * 60)

        return True


def main():
    """主函数"""
    runner = QuickTestRunner()

    try:
        success = runner.run_quick_test()

        if success:
            print("\n✓ 快速测试通过！服务运行正常。")
            print("如需完整测试，请运行: python run_tests.py")
            sys.exit(0)
        else:
            print("\n✗ 快速测试失败！请检查服务状态。")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n快速测试异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
