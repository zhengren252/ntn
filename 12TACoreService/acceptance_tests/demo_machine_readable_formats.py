#!/usr/bin/env python3
# 机器可读格式演示脚本
# Machine Readable Formats Demo Script

import os
import sys
import json
import xml.etree.ElementTree as ET
import csv
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.report_generator import ReportGenerator
from utils.test_models import VerificationPoint


def create_demo_test_data():
    """创建演示测试数据"""

    # 创建验证点
    vp1 = VerificationPoint(
        description="API响应时间检查",
        passed=True,
        details="响应时间: 45ms",
        expected="< 100ms",
        actual="45ms",
    )

    vp2 = VerificationPoint(description="数据格式验证", passed=True, details="JSON格式正确")

    vp3 = VerificationPoint(
        description="连接稳定性测试",
        passed=False,
        details="连接在第3次尝试时失败",
        expected="连接成功",
        actual="连接超时",
    )

    # 创建测试用例数据
    now = datetime.now()

    test_cases = [
        {
            "case_id": "DEMO-001",
            "title": "API基础功能测试",
            "suite_id": "DEMO_SUITE",
            "suite_name": "演示测试套件",
            "status": "PASS",
            "duration": 1.234,
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "verification_results": [vp1.to_dict(), vp2.to_dict()],
            "metadata": {"priority": "high", "category": "functional"},
        },
        {
            "case_id": "DEMO-002",
            "title": "连接稳定性测试",
            "suite_id": "DEMO_SUITE",
            "suite_name": "演示测试套件",
            "status": "FAIL",
            "duration": 2.567,
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "error_message": "连接超时",
            "error_type": "ConnectionError",
            "verification_results": [vp3.to_dict()],
            "metadata": {"priority": "medium", "category": "stability"},
        },
    ]

    # 创建摘要
    summary = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": 2,
        "passed_tests": 1,
        "failed_tests": 1,
        "success_rate": 50.0,
        "total_duration": 3.801,
    }

    return {"summary": summary, "results": test_cases}


def demo_json_format(generator, test_data):
    """演示JSON格式的使用"""
    print("\n=== JSON格式演示 ===")

    # 生成JSON报告
    json_file = generator.generate_json_report(
        test_data["results"], test_data["summary"]
    )

    print(f"JSON报告已生成: {json_file}")

    # 读取并展示JSON内容的关键部分
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\nJSON报告结构:")
    print(f"- 报告信息: {data['report_info']['title']}")
    print(
        f"- 测试摘要: {data['summary']['total_tests']} 个测试，成功率 {data['summary']['success_rate']}%"
    )
    print(f"- 测试结果: {len(data['test_results'])} 个详细测试用例")

    # 展示如何程序化处理JSON数据
    print("\n程序化处理示例:")
    for test in data["test_results"]:
        status_icon = "✅" if test["status"] == "PASS" else "❌"
        print(f"{status_icon} {test['case_id']}: {test['title']} ({test['duration']}s)")

    return json_file


def demo_junit_xml_format(generator, test_data):
    """演示JUnit XML格式的使用"""
    print("\n=== JUnit XML格式演示 ===")

    # 生成JUnit XML报告
    xml_file = generator.generate_junit_xml_report(
        test_data["results"], test_data["summary"]
    )

    print(f"JUnit XML报告已生成: {xml_file}")

    # 解析并展示XML内容
    tree = ET.parse(xml_file)
    root = tree.getroot()

    print("\nJUnit XML报告结构:")
    print(f"- 根元素: {root.tag}")
    print(f"- 总测试数: {root.get('tests')}")
    print(f"- 失败数: {root.get('failures')}")
    print(f"- 总耗时: {root.get('time')}s")

    print("\n测试套件详情:")
    for testsuite in root.findall("testsuite"):
        print(f"- 套件: {testsuite.get('name')}")
        print(f"  测试数: {testsuite.get('tests')}, 失败数: {testsuite.get('failures')}")

        for testcase in testsuite.findall("testcase"):
            status = "PASS" if testcase.find("failure") is None else "FAIL"
            status_icon = "✅" if status == "PASS" else "❌"
            print(f"  {status_icon} {testcase.get('name')} ({testcase.get('time')}s)")

    print("\nCI/CD集成说明:")
    print("- 此XML格式兼容Jenkins、GitLab CI、GitHub Actions等CI/CD系统")
    print("- 可直接用于测试结果展示和趋势分析")

    return xml_file


def demo_csv_format(generator, test_data):
    """演示CSV格式的使用"""
    print("\n=== CSV格式演示 ===")

    # 生成CSV报告
    csv_file = generator.generate_csv_report(test_data["results"], test_data["summary"])

    print(f"CSV报告已生成: {csv_file}")

    # 读取并展示CSV内容
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print("\nCSV报告结构:")
    print(f"- 列数: {len(rows[0].keys())}")
    print(f"- 数据行数: {len(rows)}")
    print(f"- 主要列: {', '.join(list(rows[0].keys())[:5])}...")

    print("\n数据示例:")
    for row in rows:
        status_icon = "✅" if row["Status"] == "PASS" else "❌"
        print(
            f"{status_icon} {row['Test_ID']}: {row['Test_Title']} - {row['Duration_Seconds']}s"
        )

    print("\n数据分析应用:")
    print("- 可导入Excel进行数据透视表分析")
    print("- 适合生成测试趋势图表")
    print("- 便于与其他数据分析工具集成")

    return csv_file


def demo_api_response_format(generator, test_data):
    """演示API响应格式的使用"""
    print("\n=== API响应格式演示 ===")

    # 生成API响应格式
    api_response = generator.generate_api_response(
        test_data["results"], test_data["summary"]
    )

    print("API响应格式结构:")
    print(f"- 状态: {api_response['status']}")
    print(f"- 时间戳: {api_response['timestamp']}")
    print(f"- 数据记录数: {api_response['metadata']['total_records']}")

    # 展示API响应的JSON格式
    print("\nAPI响应示例 (前50个字符):")
    api_json = json.dumps(api_response, indent=2, ensure_ascii=False)
    print(api_json[:200] + "...")

    print("\nAPI集成应用:")
    print("- 可直接用于REST API响应")
    print("- 支持前端应用实时获取测试结果")
    print("- 便于与监控系统集成")

    return api_response


def demo_format_selection(generator, test_data):
    """演示格式选择功能"""
    print("\n=== 格式选择功能演示 ===")

    # 选择特定格式
    selected_formats = ["json", "csv"]
    reports = generator.generate_reports_by_format(
        test_data["results"], test_data["summary"], selected_formats
    )

    print(f"选择的格式: {selected_formats}")
    print("生成的报告:")
    for format_name, file_path in reports.items():
        print(f"- {format_name.upper()}: {file_path}")

    # 生成所有格式
    print("\n生成所有格式:")
    all_reports = generator.generate_all_reports(
        test_data["results"], test_data["summary"]
    )

    for format_name, file_path in all_reports.items():
        print(f"- {format_name.upper()}: {file_path}")

    return reports


def main():
    """主演示函数"""
    print("=" * 80)
    print("TACoreService 机器可读格式演示")
    print("=" * 80)

    # 创建报告生成器
    generator = ReportGenerator("./demo_reports")

    # 创建演示数据
    test_data = create_demo_test_data()

    print("\n演示数据概览:")
    print(f"- 测试套件: {test_data['results'][0]['suite_name']}")
    print(f"- 测试用例数: {test_data['summary']['total_tests']}")
    print(f"- 成功率: {test_data['summary']['success_rate']}%")

    # 演示各种格式
    demos = [
        ("JSON格式", demo_json_format),
        ("JUnit XML格式", demo_junit_xml_format),
        ("CSV格式", demo_csv_format),
        ("API响应格式", demo_api_response_format),
        ("格式选择功能", demo_format_selection),
    ]

    generated_files = []

    for demo_name, demo_func in demos:
        try:
            result = demo_func(generator, test_data)
            if isinstance(result, str) and os.path.exists(result):
                generated_files.append(result)
            elif isinstance(result, dict):
                generated_files.extend(
                    [
                        f
                        for f in result.values()
                        if isinstance(f, str) and os.path.exists(f)
                    ]
                )
        except Exception as e:
            print(f"❌ {demo_name} 演示失败: {e}")

    print("\n" + "=" * 80)
    print("演示总结")
    print("=" * 80)

    print("\n支持的机器可读格式:")
    print("1. JSON - 结构化数据，便于程序处理")
    print("2. JUnit XML - CI/CD系统兼容格式")
    print("3. CSV - 表格数据，便于数据分析")
    print("4. API响应 - REST API集成格式")

    print("\n应用场景:")
    print("- 自动化测试报告生成")
    print("- CI/CD流水线集成")
    print("- 测试数据分析和可视化")
    print("- 第三方系统集成")

    if generated_files:
        print(f"\n本次演示生成了 {len(set(generated_files))} 个报告文件")
        print("文件位置: ./demo_reports/ 目录")

    print("\n🎉 机器可读格式演示完成！")


if __name__ == "__main__":
    main()
