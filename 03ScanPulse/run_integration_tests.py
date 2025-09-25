#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描器模组V3.5升级后集成测试执行脚本

自动化执行集成测试并生成详细报告
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """
    集成测试运行器
    """

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests" / "integration"
        self.reports_dir = self.project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.test_results = {
            "test_plan_id": "TEST-PLAN-M03-SCANNER-V1",
            "module_id": "03",
            "module_name": "扫描器 (Scanner Module)",
            "test_stage": "第三阶段 - 集成测试",
            "start_time": None,
            "end_time": None,
            "duration": None,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": str(self.project_root),
            },
            "test_cases": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "error": 0},
            "docker_services": [],
            "logs": [],
        }

    def check_prerequisites(self) -> bool:
        """
        检查测试前置条件
        """
        logger.info("检查测试前置条件...")

        # 检查Docker
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error("Docker未安装或不可用")
                return False
            logger.info(f"Docker版本: {result.stdout.strip()}")
        except Exception as e:
            logger.error(f"检查Docker失败: {e}")
            return False

        # 检查Docker Compose
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error("Docker Compose未安装或不可用")
                return False
            logger.info(f"Docker Compose版本: {result.stdout.strip()}")
        except Exception as e:
            logger.error(f"检查Docker Compose失败: {e}")
            return False

        # 检查docker-compose.system.yml文件
        compose_file = self.project_root / "docker-compose.system.yml"
        if not compose_file.exists():
            logger.error(f"Docker Compose配置文件不存在: {compose_file}")
            return False

        # 检查测试文件
        test_file = self.test_dir / "test_scanner_integration_v35.py"
        if not test_file.exists():
            logger.error(f"集成测试文件不存在: {test_file}")
            return False

        logger.info("前置条件检查通过")
        return True

    def cleanup_environment(self):
        """
        清理测试环境
        """
        logger.info("清理测试环境...")

        try:
            # 停止所有相关容器
            cmd = ["docker-compose", "-f", "docker-compose.system.yml", "down"]
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                logger.info("Docker服务停止成功")
            else:
                logger.warning(f"停止Docker服务时出现警告: {result.stderr}")

        except Exception as e:
            logger.warning(f"清理环境时发生异常: {e}")

    def run_pytest(self) -> Dict[str, Any]:
        """
        运行pytest集成测试
        """
        logger.info("开始运行集成测试...")

        # 构建pytest命令
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.test_dir / "test_scanner_integration_v35.py"),
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file={self.reports_dir / 'pytest_report.json'}",
            "--capture=no",
        ]

        # 设置环境变量
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)

        try:
            # 运行测试
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时
                env=env,
            )

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            logger.error("测试执行超时")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "测试执行超时",
                "success": False,
            }
        except Exception as e:
            logger.error(f"运行测试时发生异常: {e}")
            return {"returncode": -1, "stdout": "", "stderr": str(e), "success": False}

    def parse_pytest_results(self) -> bool:
        """
        解析pytest结果
        """
        pytest_report_file = self.reports_dir / "pytest_report.json"

        if not pytest_report_file.exists():
            logger.warning("pytest JSON报告文件不存在")
            return False

        try:
            with open(pytest_report_file, "r", encoding="utf-8") as f:
                pytest_data = json.load(f)

            # 解析测试结果
            summary = pytest_data.get("summary", {})
            self.test_results["summary"] = {
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "error": summary.get("error", 0),
            }

            # 解析测试用例
            tests = pytest_data.get("tests", [])
            for test in tests:
                test_case = {
                    "test_id": test.get("nodeid", ""),
                    "name": test.get("name", ""),
                    "outcome": test.get("outcome", ""),
                    "duration": test.get("duration", 0),
                    "setup_duration": test.get("setup", {}).get("duration", 0),
                    "teardown_duration": test.get("teardown", {}).get("duration", 0),
                }

                # 添加错误信息（如果有）
                if test.get("call", {}).get("longrepr"):
                    test_case["error_message"] = test["call"]["longrepr"]

                self.test_results["test_cases"].append(test_case)

            return True

        except Exception as e:
            logger.error(f"解析pytest结果失败: {e}")
            return False

    def generate_report(self) -> str:
        """
        生成测试报告
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"integration_test_report_{timestamp}.json"

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)

            logger.info(f"测试报告已生成: {report_file}")
            return str(report_file)

        except Exception as e:
            logger.error(f"生成测试报告失败: {e}")
            return ""

    def generate_summary_report(self) -> str:
        """
        生成简要测试报告
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.reports_dir / f"integration_test_summary_{timestamp}.md"

        try:
            summary = self.test_results["summary"]
            duration = self.test_results.get("duration", 0)

            content = f"""# 扫描器模组V3.5集成测试报告

## 测试概要

- **测试计划ID**: {self.test_results['test_plan_id']}
- **模组**: {self.test_results['module_name']}
- **测试阶段**: {self.test_results['test_stage']}
- **开始时间**: {self.test_results['start_time']}
- **结束时间**: {self.test_results['end_time']}
- **总耗时**: {duration:.2f}秒

## 测试结果统计

- **总测试数**: {summary['total']}
- **通过**: {summary['passed']} ✅
- **失败**: {summary['failed']} ❌
- **跳过**: {summary['skipped']} ⏭️
- **错误**: {summary['error']} 🚫

## 测试用例详情

"""

            for i, test_case in enumerate(self.test_results["test_cases"], 1):
                outcome_emoji = {
                    "passed": "✅",
                    "failed": "❌",
                    "skipped": "⏭️",
                    "error": "🚫",
                }.get(test_case["outcome"], "❓")

                content += f"""### {i}. {test_case['name']} {outcome_emoji}

- **状态**: {test_case['outcome']}
- **耗时**: {test_case['duration']:.3f}秒
"""

                if test_case.get("error_message"):
                    content += f"- **错误信息**: ```\n{test_case['error_message']}\n```\n"

                content += "\n"

            # 添加结论
            if summary["failed"] == 0 and summary["error"] == 0:
                content += "## 测试结论\n\n🎉 **所有集成测试通过！扫描器模组V3.5升级成功。**\n"
            else:
                content += "## 测试结论\n\n⚠️ **存在测试失败，需要进一步检查和修复。**\n"

            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"简要测试报告已生成: {summary_file}")
            return str(summary_file)

        except Exception as e:
            logger.error(f"生成简要测试报告失败: {e}")
            return ""

    def run(self) -> bool:
        """
        运行完整的集成测试流程
        """
        logger.info("开始执行扫描器模组V3.5集成测试")

        self.test_results["start_time"] = datetime.now().isoformat()
        start_time = time.time()

        try:
            # 1. 检查前置条件
            if not self.check_prerequisites():
                logger.error("前置条件检查失败，测试终止")
                return False

            # 2. 清理环境
            self.cleanup_environment()

            # 3. 运行测试
            pytest_result = self.run_pytest()

            # 4. 记录测试输出
            self.test_results["logs"].append(
                {"type": "pytest_stdout", "content": pytest_result["stdout"]}
            )

            if pytest_result["stderr"]:
                self.test_results["logs"].append(
                    {"type": "pytest_stderr", "content": pytest_result["stderr"]}
                )

            # 5. 解析结果
            self.parse_pytest_results()

            # 6. 记录结束时间
            self.test_results["end_time"] = datetime.now().isoformat()
            self.test_results["duration"] = time.time() - start_time

            # 7. 生成报告
            report_file = self.generate_report()
            summary_file = self.generate_summary_report()

            # 8. 输出结果
            summary = self.test_results["summary"]
            logger.info(f"集成测试完成:")
            logger.info(f"  总测试数: {summary['total']}")
            logger.info(f"  通过: {summary['passed']}")
            logger.info(f"  失败: {summary['failed']}")
            logger.info(f"  跳过: {summary['skipped']}")
            logger.info(f"  错误: {summary['error']}")
            logger.info(f"  耗时: {self.test_results['duration']:.2f}秒")

            if report_file:
                logger.info(f"详细报告: {report_file}")
            if summary_file:
                logger.info(f"简要报告: {summary_file}")

            return pytest_result["success"]

        except Exception as e:
            logger.error(f"执行集成测试时发生异常: {e}")
            return False

        finally:
            # 最终清理
            self.cleanup_environment()


def main():
    """
    主函数
    """
    runner = IntegrationTestRunner()
    success = runner.run()

    if success:
        logger.info("集成测试执行成功")
        sys.exit(0)
    else:
        logger.error("集成测试执行失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
