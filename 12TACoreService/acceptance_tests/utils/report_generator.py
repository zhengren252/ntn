# 测试报告生成器
# Test Report Generator

import os
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Template
from .test_models import TestReport, TestSuite, TestCase, TestStatus


class ReportGenerator:
    """测试报告生成器"""

    def __init__(self, report_dir: str = "./acceptance_tests/reports"):
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)

    def generate_html_report(
        self, test_results: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """生成HTML格式的测试报告"""

        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TACoreService 验收测试报告</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #007acc;
            padding-bottom: 20px;
        }
        .header h1 {
            color: #007acc;
            margin: 0;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .summary-card.success {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        }
        .summary-card.danger {
            background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
        }
        .summary-card h3 {
            margin: 0 0 10px 0;
            font-size: 2em;
        }
        .summary-card p {
            margin: 0;
            opacity: 0.9;
        }
        .test-suite {
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .suite-header {
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #ddd;
        }
        .suite-header h3 {
            margin: 0;
            color: #333;
        }
        .test-case {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }
        .test-case:last-child {
            border-bottom: none;
        }
        .test-case.pass {
            border-left: 4px solid #4CAF50;
            background-color: #f8fff8;
        }
        .test-case.fail {
            border-left: 4px solid #f44336;
            background-color: #fff8f8;
        }
        .test-case-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .test-case-title {
            font-weight: bold;
            color: #333;
        }
        .test-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .test-status.pass {
            background-color: #4CAF50;
            color: white;
        }
        .test-status.fail {
            background-color: #f44336;
            color: white;
        }
        .test-details {
            color: #666;
            font-size: 0.9em;
        }
        .verification-points {
            margin-top: 10px;
        }
        .verification-point {
            margin: 5px 0;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.85em;
        }
        .verification-point.pass {
            background-color: #e8f5e8;
            color: #2e7d32;
        }
        .verification-point.fail {
            background-color: #ffebee;
            color: #c62828;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TACoreService 验收测试报告</h1>
            <p>生成时间: {{ summary.timestamp }}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>{{ summary.total_tests }}</h3>
                <p>总测试数</p>
            </div>
            <div class="summary-card success">
                <h3>{{ summary.passed_tests }}</h3>
                <p>通过测试</p>
            </div>
            <div class="summary-card danger">
                <h3>{{ summary.failed_tests }}</h3>
                <p>失败测试</p>
            </div>
            <div class="summary-card">
                <h3>{{ "%.1f" | format(summary.success_rate) }}%</h3>
                <p>成功率</p>
            </div>
            <div class="summary-card">
                <h3>{{ "%.2f" | format(summary.total_duration) }}s</h3>
                <p>总耗时</p>
            </div>
        </div>
        
        {% for suite_name, suite_tests in test_results | groupby('suite_id') %}
        <div class="test-suite">
            <div class="suite-header">
                <h3>{{ suite_tests[0].suite_name }}</h3>
            </div>
            {% for test in suite_tests %}
            <div class="test-case {{ 'pass' if test.status == 'PASS' else 'fail' }}">
                <div class="test-case-header">
                    <div class="test-case-title">{{ test.title }}</div>
                    <div class="test-status {{ 'pass' if test.status == 'PASS' else 'fail' }}">
                        {{ test.status }}
                    </div>
                </div>
                <div class="test-details">
                    <p><strong>测试ID:</strong> {{ test.case_id }}</p>
                    <p><strong>执行时间:</strong> {{ "%.3f" | format(test.duration) }}s</p>
                    {% if test.error_message %}
                    <p><strong>错误信息:</strong> {{ test.error_message }}</p>
                    {% endif %}
                </div>
                {% if test.verification_results %}
                <div class="verification-points">
                    <strong>验证点:</strong>
                    {% for vp in test.verification_results %}
                    <div class="verification-point {{ 'pass' if vp.passed else 'fail' }}">
                        {{ '✓' if vp.passed else '✗' }} {{ vp.description }}
                        {% if vp.details %} - {{ vp.details }}{% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div class="footer">
            <p>TACoreService 验收测试套件 v1.0.0</p>
        </div>
    </div>
</body>
</html>
        """

        template = Template(html_template)
        html_content = template.render(test_results=test_results, summary=summary)

        # 保存HTML报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = os.path.join(
            self.report_dir, f"acceptance_test_report_{timestamp}.html"
        )

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_file

    def generate_json_report(
        self, test_results: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """生成JSON格式的测试报告"""

        report_data = {
            "report_info": {
                "title": "TACoreService 验收测试报告",
                "version": "1.0.0",
                "generated_at": datetime.now().isoformat(),
                "plan_id": "ACCEPTANCE-TEST-PLAN-M12-TACORESVC-V1.0",
            },
            "summary": summary,
            "test_results": test_results,
        }

        # 保存JSON报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(
            self.report_dir, f"acceptance_test_report_{timestamp}.json"
        )

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return json_file

    def generate_text_report(
        self, test_results: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """生成文本格式的测试报告"""

        lines = []
        lines.append("=" * 80)
        lines.append("TACoreService 验收测试报告")
        lines.append("=" * 80)
        lines.append(f"生成时间: {summary['timestamp']}")
        lines.append("")

        # 摘要信息
        lines.append("测试摘要:")
        lines.append("-" * 40)
        lines.append(f"总测试数: {summary['total_tests']}")
        lines.append(f"通过测试: {summary['passed_tests']}")
        lines.append(f"失败测试: {summary['failed_tests']}")
        lines.append(f"成功率: {summary['success_rate']:.1f}%")
        lines.append(f"总耗时: {summary['total_duration']:.2f}s")
        lines.append("")

        # 按测试套件分组
        suites = {}
        for test in test_results:
            suite_id = test["suite_id"]
            if suite_id not in suites:
                suites[suite_id] = []
            suites[suite_id].append(test)

        # 详细测试结果
        lines.append("详细测试结果:")
        lines.append("-" * 40)

        for suite_id, suite_tests in suites.items():
            lines.append(f"\n[{suite_id}] {suite_tests[0]['suite_name']}")
            lines.append("-" * 60)

            for test in suite_tests:
                status_symbol = "✓" if test["status"] == "PASS" else "✗"
                lines.append(f"{status_symbol} {test['case_id']}: {test['title']}")
                lines.append(f"   执行时间: {test['duration']:.3f}s")

                if test.get("error_message"):
                    lines.append(f"   错误: {test['error_message']}")

                if test.get("verification_results"):
                    lines.append("   验证点:")
                    for vp in test["verification_results"]:
                        vp_symbol = "✓" if vp["passed"] else "✗"
                        lines.append(f"     {vp_symbol} {vp['description']}")
                        if vp.get("details"):
                            lines.append(f"       {vp['details']}")
                lines.append("")

        lines.append("=" * 80)

        # 保存文本报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_file = os.path.join(
            self.report_dir, f"acceptance_test_report_{timestamp}.txt"
        )

        with open(text_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return text_file

    def generate_junit_xml_report(
        self, test_results: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """生成JUnit XML格式的测试报告"""

        # 创建根元素
        testsuites = ET.Element("testsuites")
        testsuites.set("name", "TACoreService Acceptance Tests")
        testsuites.set("tests", str(summary["total_tests"]))
        testsuites.set("failures", str(summary["failed_tests"]))
        testsuites.set("errors", "0")
        testsuites.set("time", str(summary["total_duration"]))
        testsuites.set("timestamp", datetime.now().isoformat())

        # 按测试套件分组
        suites = {}
        for test in test_results:
            suite_id = test["suite_id"]
            if suite_id not in suites:
                suites[suite_id] = []
            suites[suite_id].append(test)

        # 为每个测试套件创建testsuite元素
        for suite_id, suite_tests in suites.items():
            testsuite = ET.SubElement(testsuites, "testsuite")
            testsuite.set("name", suite_tests[0]["suite_name"])
            testsuite.set("tests", str(len(suite_tests)))

            suite_failures = len([t for t in suite_tests if t["status"] == "FAIL"])
            suite_duration = sum(t["duration"] for t in suite_tests)

            testsuite.set("failures", str(suite_failures))
            testsuite.set("errors", "0")
            testsuite.set("time", str(suite_duration))
            testsuite.set("package", f"tacoreservice.acceptance.{suite_id}")

            # 为每个测试用例创建testcase元素
            for test in suite_tests:
                testcase = ET.SubElement(testsuite, "testcase")
                testcase.set("name", test["title"])
                testcase.set(
                    "classname",
                    f"tacoreservice.acceptance.{suite_id}.{test['case_id']}",
                )
                testcase.set("time", str(test["duration"]))

                # 如果测试失败，添加failure元素
                if test["status"] == "FAIL":
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("message", test.get("error_message", "Test failed"))
                    failure.set("type", test.get("error_type", "AssertionError"))
                    failure.text = test.get("error_message", "Test failed")

                # 添加系统输出（验证点信息）
                if test.get("verification_results"):
                    system_out = ET.SubElement(testcase, "system-out")
                    verification_info = []
                    for vp in test["verification_results"]:
                        status = "PASS" if vp["passed"] else "FAIL"
                        verification_info.append(f"[{status}] {vp['description']}")
                        if vp.get("details"):
                            verification_info.append(f"  Details: {vp['details']}")
                    system_out.text = "\n".join(verification_info)

        # 保存XML文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml_file = os.path.join(
            self.report_dir, f"acceptance_test_report_{timestamp}.xml"
        )

        # 格式化XML
        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ", level=0)
        tree.write(xml_file, encoding="utf-8", xml_declaration=True)

        return xml_file

    def generate_csv_report(
        self, test_results: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> str:
        """生成CSV格式的测试结果摘要"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = os.path.join(
            self.report_dir, f"acceptance_test_summary_{timestamp}.csv"
        )

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # 写入标题行
            writer.writerow(
                [
                    "Test_ID",
                    "Test_Title",
                    "Suite_ID",
                    "Suite_Name",
                    "Status",
                    "Duration_Seconds",
                    "Start_Time",
                    "End_Time",
                    "Error_Message",
                    "Verification_Points_Total",
                    "Verification_Points_Passed",
                    "Success_Rate",
                ]
            )

            # 写入测试数据
            for test in test_results:
                verification_results = test.get("verification_results", [])
                total_vp = len(verification_results)
                passed_vp = len(
                    [vp for vp in verification_results if vp.get("passed", False)]
                )
                vp_success_rate = (passed_vp / total_vp * 100) if total_vp > 0 else 0

                writer.writerow(
                    [
                        test.get("case_id", ""),
                        test.get("title", ""),
                        test.get("suite_id", ""),
                        test.get("suite_name", ""),
                        test.get("status", ""),
                        test.get("duration", 0),
                        test.get("start_time", ""),
                        test.get("end_time", ""),
                        test.get("error_message", ""),
                        total_vp,
                        passed_vp,
                        f"{vp_success_rate:.1f}%",
                    ]
                )

        return csv_file

    def generate_detailed_json_report(self, test_report: TestReport) -> str:
        """生成详细的JSON格式测试报告（使用标准化数据模型）"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(
            self.report_dir, f"detailed_test_report_{timestamp}.json"
        )

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_report.to_dict(), f, indent=2, ensure_ascii=False)

        return json_file

    def generate_api_response(
        self,
        test_results: List[Dict[str, Any]],
        summary: Dict[str, Any],
        format_type: str = "json",
    ) -> Dict[str, Any]:
        """生成API响应格式的测试结果"""

        base_response = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {"summary": summary, "test_results": test_results},
            "metadata": {
                "format": format_type,
                "version": "1.0.0",
                "total_records": len(test_results),
            },
        }

        return base_response

    def generate_all_reports(
        self, test_results: List[Dict[str, Any]], summary: Dict[str, Any]
    ) -> Dict[str, str]:
        """生成所有格式的测试报告"""

        reports = {
            "html": self.generate_html_report(test_results, summary),
            "json": self.generate_json_report(test_results, summary),
            "text": self.generate_text_report(test_results, summary),
            "junit_xml": self.generate_junit_xml_report(test_results, summary),
            "csv": self.generate_csv_report(test_results, summary),
        }

        return reports

    def generate_reports_by_format(
        self,
        test_results: List[Dict[str, Any]],
        summary: Dict[str, Any],
        formats: List[str],
    ) -> Dict[str, str]:
        """根据指定格式生成测试报告"""

        available_formats = {
            "html": self.generate_html_report,
            "json": self.generate_json_report,
            "text": self.generate_text_report,
            "junit_xml": self.generate_junit_xml_report,
            "csv": self.generate_csv_report,
        }

        reports = {}
        for format_name in formats:
            if format_name in available_formats:
                reports[format_name] = available_formats[format_name](
                    test_results, summary
                )
            else:
                print(f"Warning: Unsupported format '{format_name}' requested")

        return reports
