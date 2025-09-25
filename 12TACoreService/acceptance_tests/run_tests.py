#!/usr/bin/env python3
# 验收测试运行器
# Acceptance Test Runner

import os
import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AcceptanceTestConfig as TestConfig
from utils.test_logger import TestLogger
from utils.test_helpers import TestHelpers
from utils.report_generator import ReportGenerator
from tests import (
    ZMQBusinessAPITests,
    HTTPMonitoringAPITests,
    LoadBalancingTests,
    HighAvailabilityTests,
    DataPersistenceTests,
)


class AcceptanceTestRunner:
    """验收测试运行器"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("acceptance_test_runner")
        self.helpers = TestHelpers()
        self.report_generator = ReportGenerator()

        # 确保报告目录存在
        os.makedirs(self.config.REPORT_DIR, exist_ok=True)

    def run_test_suite(self, suite_name: str, test_suite_class) -> List[Dict[str, Any]]:
        """运行单个测试套件"""
        self.logger.info(f"开始运行测试套件: {suite_name}")

        try:
            # 创建测试套件实例
            test_suite = test_suite_class()

            # 运行所有测试
            results = test_suite.run_all_tests()

            # 清理资源
            if hasattr(test_suite, "cleanup"):
                test_suite.cleanup()

            self.logger.info(f"测试套件 {suite_name} 完成，共 {len(results)} 个测试用例")
            return results

        except Exception as e:
            self.logger.error(f"测试套件 {suite_name} 运行异常: {e}")
            return [
                {
                    "case_id": f"{suite_name}-ERROR",
                    "title": f"{suite_name} 套件运行异常",
                    "suite_id": suite_name,
                    "suite_name": suite_name,
                    "status": "FAIL",
                    "duration": 0,
                    "verification_results": [],
                    "error_message": str(e),
                }
            ]

    def run_all_tests(self, selected_suites: List[str] = None) -> Dict[str, Any]:
        """运行所有验收测试"""

        # 定义所有测试套件
        test_suites = {
            "ZMQ_BUSINESS_API": ("ZeroMQ业务API测试", ZMQBusinessAPITests),
            "HTTP_MONITORING_API": ("HTTP监控API测试", HTTPMonitoringAPITests),
            "LOAD_BALANCING": ("负载均衡与可扩展性测试", LoadBalancingTests),
            "HIGH_AVAILABILITY": ("高可用性与故障转移测试", HighAvailabilityTests),
            "DATA_PERSISTENCE": ("数据持久化验证测试", DataPersistenceTests),
        }

        # 如果指定了特定套件，只运行这些套件
        if selected_suites:
            test_suites = {k: v for k, v in test_suites.items() if k in selected_suites}

        self.logger.info("=" * 80)
        self.logger.info("TACoreService 验收测试开始")
        self.logger.info(f"测试计划ID: ACCEPTANCE-TEST-PLAN-M12-TACORESVC-V1.0")
        self.logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"将运行 {len(test_suites)} 个测试套件")
        self.logger.info("=" * 80)

        overall_start_time = time.time()
        all_results = []

        # 运行每个测试套件
        for suite_id, (suite_name, suite_class) in test_suites.items():
            suite_results = self.run_test_suite(suite_name, suite_class)
            all_results.extend(suite_results)

            # 在套件之间添加短暂延迟
            time.sleep(1)

        overall_duration = time.time() - overall_start_time

        # 计算测试摘要
        summary = self._calculate_summary(all_results, overall_duration)

        self.logger.info("=" * 80)
        self.logger.info("TACoreService 验收测试完成")
        self.logger.info(f"总耗时: {overall_duration:.2f}s")
        self.logger.info(f"总测试数: {summary['total_tests']}")
        self.logger.info(f"通过测试: {summary['passed_tests']}")
        self.logger.info(f"失败测试: {summary['failed_tests']}")
        self.logger.info(f"成功率: {summary['success_rate']:.1f}%")
        self.logger.info("=" * 80)

        return {"summary": summary, "results": all_results}

    def _calculate_summary(
        self, results: List[Dict[str, Any]], total_duration: float
    ) -> Dict[str, Any]:
        """计算测试摘要"""
        total_tests = len(results)
        passed_tests = len([r for r in results if r["status"] == "PASS"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "total_duration": total_duration,
        }

    def generate_reports(
        self, test_data: Dict[str, Any], formats: List[str] = None
    ) -> Dict[str, str]:
        """生成测试报告"""
        self.logger.info("生成测试报告...")

        try:
            if formats:
                # 生成指定格式的报告
                report_files = self.report_generator.generate_reports_by_format(
                    test_data["results"], test_data["summary"], formats
                )
            else:
                # 生成所有格式的报告
                report_files = self.report_generator.generate_all_reports(
                    test_data["results"], test_data["summary"]
                )

            self.logger.info("测试报告生成完成:")
            for format_type, file_path in report_files.items():
                self.logger.info(f"  {format_type.upper()}: {file_path}")

            return report_files

        except Exception as e:
            self.logger.error(f"生成测试报告失败: {e}")
            return {}

    def generate_api_response(
        self, test_data: Dict[str, Any], format_type: str = "json"
    ) -> Dict[str, Any]:
        """生成API响应格式的测试结果"""
        return self.report_generator.generate_api_response(
            test_data["results"], test_data["summary"], format_type
        )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TACoreService 验收测试运行器")
    parser.add_argument(
        "--suites",
        nargs="*",
        choices=[
            "ZMQ_BUSINESS_API",
            "HTTP_MONITORING_API",
            "LOAD_BALANCING",
            "HIGH_AVAILABILITY",
            "DATA_PERSISTENCE",
        ],
        help="指定要运行的测试套件（默认运行所有套件）",
    )
    parser.add_argument("--no-reports", action="store_true", help="不生成测试报告")
    parser.add_argument(
        "--formats",
        nargs="*",
        choices=["html", "json", "text", "junit_xml", "csv"],
        help="指定报告输出格式（默认生成所有格式）",
    )
    parser.add_argument("--api-output", action="store_true", help="以API响应格式输出测试结果到控制台")
    parser.add_argument("--output-file", type=str, help="将API响应格式的结果保存到指定文件")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")

    args = parser.parse_args()

    # 创建测试运行器
    runner = AcceptanceTestRunner()

    try:
        # 运行测试
        test_data = runner.run_all_tests(args.suites)

        # 处理API输出
        if args.api_output or args.output_file:
            api_response = runner.generate_api_response(test_data)

            if args.api_output:
                import json

                print("\n=== API响应格式输出 ===")
                print(json.dumps(api_response, indent=2, ensure_ascii=False))

            if args.output_file:
                import json

                with open(args.output_file, "w", encoding="utf-8") as f:
                    json.dump(api_response, f, indent=2, ensure_ascii=False)
                print(f"\nAPI响应格式结果已保存到: {args.output_file}")

        # 生成报告
        if not args.no_reports:
            report_files = runner.generate_reports(test_data, args.formats)

            if report_files:
                print("\n测试报告已生成:")
                for format_type, file_path in report_files.items():
                    print(f"  {format_type.upper()}: {file_path}")

        # 根据测试结果设置退出码
        if test_data["summary"]["failed_tests"] > 0:
            print(f"\n测试失败: {test_data['summary']['failed_tests']} 个测试用例未通过")
            sys.exit(1)
        else:
            print("\n所有测试都通过了！")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n测试运行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
