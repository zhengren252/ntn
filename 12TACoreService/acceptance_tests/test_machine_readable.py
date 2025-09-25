#!/usr/bin/env python3
# 机器可读格式功能测试脚本
# Machine Readable Format Test Script

import os
import sys
import json
import xml.etree.ElementTree as ET
import csv
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.report_generator import ReportGenerator
from utils.test_models import (
    TestReport,
    TestSuite,
    TestCase,
    TestStatus,
    VerificationPoint,
)


def create_sample_test_data() -> Dict[str, Any]:
    """创建示例测试数据"""

    # 创建验证点
    vp1 = VerificationPoint(
        description="连接建立成功",
        passed=True,
        details="连接时间: 0.123s",
        expected="< 1s",
        actual="0.123s",
    )

    vp2 = VerificationPoint(description="响应格式正确", passed=True, details="JSON格式验证通过")

    vp3 = VerificationPoint(
        description="性能要求",
        passed=False,
        details="响应时间超出预期",
        expected="< 100ms",
        actual="150ms",
    )

    # 创建测试用例
    now = datetime.now()

    test_cases = [
        {
            "case_id": "ZMQ-001",
            "title": "ZeroMQ连接测试",
            "suite_id": "ZMQ_BUSINESS_API",
            "suite_name": "ZeroMQ业务API测试",
            "status": "PASS",
            "duration": 1.234,
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "verification_results": [vp1.to_dict(), vp2.to_dict()],
            "metadata": {"priority": "high", "category": "connectivity"},
        },
        {
            "case_id": "ZMQ-002",
            "title": "市场扫描API测试",
            "suite_id": "ZMQ_BUSINESS_API",
            "suite_name": "ZeroMQ业务API测试",
            "status": "FAIL",
            "duration": 2.567,
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "error_message": "响应时间超出预期",
            "error_type": "PerformanceError",
            "verification_results": [vp3.to_dict()],
            "metadata": {"priority": "medium", "category": "performance"},
        },
        {
            "case_id": "HTTP-001",
            "title": "健康检查API测试",
            "suite_id": "HTTP_MONITORING_API",
            "suite_name": "HTTP监控API测试",
            "status": "PASS",
            "duration": 0.456,
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "verification_results": [vp1.to_dict()],
            "metadata": {"priority": "high", "category": "monitoring"},
        },
    ]

    # 创建摘要
    summary = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": 3,
        "passed_tests": 2,
        "failed_tests": 1,
        "success_rate": 66.7,
        "total_duration": 4.257,
    }

    return {"summary": summary, "results": test_cases}


def test_json_format(generator: ReportGenerator, test_data: Dict[str, Any]) -> bool:
    """测试JSON格式生成"""
    print("测试JSON格式生成...")

    try:
        json_file = generator.generate_json_report(
            test_data["results"], test_data["summary"]
        )

        # 验证文件存在
        if not os.path.exists(json_file):
            print(f"❌ JSON文件未生成: {json_file}")
            return False

        # 验证JSON格式
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 检查必要字段
        required_fields = ["report_info", "summary", "test_results"]
        for field in required_fields:
            if field not in data:
                print(f"❌ JSON缺少必要字段: {field}")
                return False

        print(f"✅ JSON格式测试通过: {json_file}")
        return True

    except Exception as e:
        print(f"❌ JSON格式测试失败: {e}")
        return False


def test_junit_xml_format(
    generator: ReportGenerator, test_data: Dict[str, Any]
) -> bool:
    """测试JUnit XML格式生成"""
    print("测试JUnit XML格式生成...")

    try:
        xml_file = generator.generate_junit_xml_report(
            test_data["results"], test_data["summary"]
        )

        # 验证文件存在
        if not os.path.exists(xml_file):
            print(f"❌ XML文件未生成: {xml_file}")
            return False

        # 验证XML格式
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # 检查根元素
        if root.tag != "testsuites":
            print(f"❌ XML根元素错误: {root.tag}")
            return False

        # 检查必要属性
        required_attrs = ["tests", "failures", "time"]
        for attr in required_attrs:
            if attr not in root.attrib:
                print(f"❌ XML缺少必要属性: {attr}")
                return False

        # 检查测试套件
        testsuites = root.findall("testsuite")
        if len(testsuites) == 0:
            print("❌ XML中没有找到测试套件")
            return False

        print(f"✅ JUnit XML格式测试通过: {xml_file}")
        return True

    except Exception as e:
        print(f"❌ JUnit XML格式测试失败: {e}")
        return False


def test_csv_format(generator: ReportGenerator, test_data: Dict[str, Any]) -> bool:
    """测试CSV格式生成"""
    print("测试CSV格式生成...")

    try:
        csv_file = generator.generate_csv_report(
            test_data["results"], test_data["summary"]
        )

        # 验证文件存在
        if not os.path.exists(csv_file):
            print(f"❌ CSV文件未生成: {csv_file}")
            return False

        # 验证CSV格式
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

            # 检查必要列
            required_columns = ["Test_ID", "Test_Title", "Status", "Duration_Seconds"]
            for col in required_columns:
                if col not in headers:
                    print(f"❌ CSV缺少必要列: {col}")
                    return False

            # 检查数据行数
            rows = list(reader)
            if len(rows) != len(test_data["results"]):
                print(f"❌ CSV数据行数不匹配: {len(rows)} vs {len(test_data['results'])}")
                return False

        print(f"✅ CSV格式测试通过: {csv_file}")
        return True

    except Exception as e:
        print(f"❌ CSV格式测试失败: {e}")
        return False


def test_api_response_format(
    generator: ReportGenerator, test_data: Dict[str, Any]
) -> bool:
    """测试API响应格式"""
    print("测试API响应格式...")

    try:
        api_response = generator.generate_api_response(
            test_data["results"], test_data["summary"]
        )

        # 检查必要字段
        required_fields = ["status", "timestamp", "data", "metadata"]
        for field in required_fields:
            if field not in api_response:
                print(f"❌ API响应缺少必要字段: {field}")
                return False

        # 检查数据结构
        data = api_response["data"]
        if "summary" not in data or "test_results" not in data:
            print("❌ API响应数据结构错误")
            return False

        # 检查状态
        if api_response["status"] != "success":
            print(f"❌ API响应状态错误: {api_response['status']}")
            return False

        print("✅ API响应格式测试通过")
        return True

    except Exception as e:
        print(f"❌ API响应格式测试失败: {e}")
        return False


def test_format_selection(
    generator: ReportGenerator, test_data: Dict[str, Any]
) -> bool:
    """测试格式选择功能"""
    print("测试格式选择功能...")

    try:
        # 测试选择特定格式
        selected_formats = ["json", "csv"]
        reports = generator.generate_reports_by_format(
            test_data["results"], test_data["summary"], selected_formats
        )

        # 检查返回的格式
        if set(reports.keys()) != set(selected_formats):
            print(f"❌ 格式选择错误: {list(reports.keys())} vs {selected_formats}")
            return False

        # 验证文件存在
        for format_name, file_path in reports.items():
            if not os.path.exists(file_path):
                print(f"❌ 选择格式文件未生成: {format_name} - {file_path}")
                return False

        print("✅ 格式选择功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 格式选择功能测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("TACoreService 机器可读格式功能测试")
    print("=" * 60)

    # 创建报告生成器
    generator = ReportGenerator("./test_reports")

    # 创建测试数据
    test_data = create_sample_test_data()

    # 运行测试
    tests = [
        ("JSON格式", test_json_format),
        ("JUnit XML格式", test_junit_xml_format),
        ("CSV格式", test_csv_format),
        ("API响应格式", test_api_response_format),
        ("格式选择功能", test_format_selection),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n[{passed + 1}/{total}] {test_name}")
        if test_func(generator, test_data):
            passed += 1
        else:
            print(f"❌ {test_name} 测试失败")

    print("\n" + "=" * 60)
    print(f"测试完成: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试都通过了！")
        return 0
    else:
        print(f"⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
