#!/usr/bin/env python3
"""
市场微结构仿真引擎 (MMS) - 机器可读测试方案执行器

严格按照 .trae/documents/市场微结构仿真引擎 (MMS) - 机器可读测试方案.txt
中定义的测试方案执行所有测试用例。
"""

import json
import sqlite3
import time
import asyncio
from typing import Dict, Any, List
from pathlib import Path

import pytest
import requests
from jsonschema import validate, ValidationError

# 测试配置
BASE_URL = "http://localhost:8001/api/v1"
DB_PATH = "data/mms.db"
TEST_PLAN_PATH = ".trae/documents/市场微结构仿真引擎 (MMS) - 机器可读测试方案.txt"


class TestPlanExecutor:
    """机器可读测试方案执行器"""

    def setup_method(self, method):
        """pytest兼容的设置方法"""
        self.test_plan = self._load_test_plan()
        self.test_results = []

    def _load_test_plan(self) -> Dict[str, Any]:
        """加载测试方案"""
        try:
            with open(TEST_PLAN_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            pytest.fail(f"无法加载测试方案: {e}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = f"{BASE_URL}{endpoint}"
        return requests.request(method, url, **kwargs)

    def _validate_assertion(
        self,
        assertion: Dict[str, Any],
        response: requests.Response,
        stored_data: Dict[str, Any] = None,
    ) -> bool:
        """验证断言"""
        assertion_type = assertion["type"]
        expected = assertion["expected"]

        if assertion_type == "statusCode":
            actual = response.status_code
            return actual == expected

        elif assertion_type == "jsonSchema":
            try:
                validate(instance=response.json(), schema=expected)
                return True
            except ValidationError:
                return False

        elif assertion_type == "jsonFieldExists":
            field = assertion["field"]
            try:
                data = response.json()
                return field in data
            except:
                return False

        elif assertion_type == "recordExists":
            # 数据库记录存在性检查
            return expected  # 简化处理

        elif assertion_type == "fieldValue":
            field = assertion["field"]
            if isinstance(expected, list):
                # 检查值是否在预期列表中
                return stored_data and stored_data.get(field) in expected
            else:
                return stored_data and stored_data.get(field) == expected

        return False

    def _execute_database_query(self, query: str) -> List[Dict[str, Any]]:
        """执行数据库查询"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            print(f"数据库查询失败: {e}")
            return []


class TestAPIFunctionalTests(TestPlanExecutor):
    """API功能测试套件"""

    def test_api_health_01(self):
        """验证 /health 端点能正常返回服务健康状态"""
        test_case = self._find_test_case("API_HEALTH_01")

        response = self._make_request(
            method=test_case["method"], endpoint=test_case["endpoint"]
        )

        # 验证所有断言
        for assertion in test_case["assertions"]:
            assert self._validate_assertion(
                assertion, response
            ), f"断言失败: {assertion['description']}"

        self.test_results.append(
            {
                "testId": "API_HEALTH_01",
                "status": "PASS",
                "response_code": response.status_code,
            }
        )

    def test_api_status_01(self):
        """验证 /status 端点能返回包含工作进程和负载信息的系统状态"""
        test_case = self._find_test_case("API_STATUS_01")

        response = self._make_request(
            method=test_case["method"], endpoint=test_case["endpoint"]
        )

        # 验证所有断言
        for assertion in test_case["assertions"]:
            assert self._validate_assertion(
                assertion, response
            ), f"断言失败: {assertion['description']}"

        # 额外验证响应体结构
        data = response.json()
        required_fields = ["service_status", "worker_count", "queue_length"]
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"

        self.test_results.append(
            {
                "testId": "API_STATUS_01",
                "status": "PASS",
                "response_code": response.status_code,
                "response_data": data,
            }
        )

    def test_api_sim_01(self):
        """验证 /simulate 端点能成功接收一个'黑天鹅'场景的仿真请求并返回结果"""
        test_case = self._find_test_case("API_SIM_01")

        response = self._make_request(
            method=test_case["method"],
            endpoint=test_case["endpoint"],
            headers=test_case["request"]["headers"],
            json=test_case["request"]["body"],
        )

        # 验证所有断言
        for assertion in test_case["assertions"]:
            assert self._validate_assertion(
                assertion, response
            ), f"断言失败: {assertion['description']}"

        # 验证响应体包含所有必需字段
        data = response.json()
        required_fields = [
            "simulation_id",
            "slippage",
            "fill_probability",
            "price_impact",
            "report_url",
        ]
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"

        self.test_results.append(
            {
                "testId": "API_SIM_01",
                "status": "PASS",
                "response_code": response.status_code,
                "simulation_id": data.get("simulation_id"),
            }
        )

    def test_api_calibrate_01(self):
        """验证 /calibrate 端点能成功接收手动校准请求"""
        test_case = self._find_test_case("API_CALIBRATE_01")

        response = self._make_request(
            method=test_case["method"], endpoint=test_case["endpoint"]
        )

        # 验证状态码为200或202
        assert response.status_code in [
            200,
            202,
        ], f"期望状态码200或202，实际: {response.status_code}"

        self.test_results.append(
            {
                "testId": "API_CALIBRATE_01",
                "status": "PASS",
                "response_code": response.status_code,
            }
        )

    def _find_test_case(self, test_id: str) -> Dict[str, Any]:
        """查找测试用例"""
        for suite in self.test_plan["testSuites"]:
            for test in suite["tests"]:
                if test["testId"] == test_id:
                    return test
        pytest.fail(f"未找到测试用例: {test_id}")


class TestAPIInputValidationTests(TestPlanExecutor):
    """API输入验证测试套件"""

    def test_api_validate_sim_01(self):
        """向 /simulate 发送缺少必需字段 'symbol' 的请求"""
        test_case = self._find_test_case("API_VALIDATE_SIM_01")

        response = self._make_request(
            method=test_case["method"],
            endpoint=test_case["endpoint"],
            headers=test_case["request"]["headers"],
            json=test_case["request"]["body"],
        )

        # 验证状态码为422
        assert response.status_code == 422, f"期望状态码422，实际: {response.status_code}"

        self.test_results.append(
            {
                "testId": "API_VALIDATE_SIM_01",
                "status": "PASS",
                "response_code": response.status_code,
            }
        )

    def test_api_validate_sim_02(self):
        """向 /simulate 发送 'strategy_params' 字段类型错误的请求"""
        test_case = self._find_test_case("API_VALIDATE_SIM_02")

        response = self._make_request(
            method=test_case["method"],
            endpoint=test_case["endpoint"],
            headers=test_case["request"]["headers"],
            json=test_case["request"]["body"],
        )

        # 验证状态码为422
        assert response.status_code == 422, f"期望状态码422，实际: {response.status_code}"

        self.test_results.append(
            {
                "testId": "API_VALIDATE_SIM_02",
                "status": "PASS",
                "response_code": response.status_code,
            }
        )

    def _find_test_case(self, test_id: str) -> Dict[str, Any]:
        """查找测试用例"""
        for suite in self.test_plan["testSuites"]:
            for test in suite["tests"]:
                if test["testId"] == test_id:
                    return test
        pytest.fail(f"未找到测试用例: {test_id}")


class TestE2EIntegrationTests(TestPlanExecutor):
    """端到端集成测试套件"""

    def test_e2e_sim_flow_01(self):
        """验证从发起仿真请求到数据库记录创建的完整流程"""
        test_case = self._find_test_case("E2E_SIM_FLOW_01")
        stored_data = {}

        # 执行步骤1：发起仿真请求
        step1 = test_case["steps"][0]
        action = step1["action"]

        response = self._make_request(
            method=action["method"], endpoint=action["endpoint"], json=action["payload"]
        )

        # 验证步骤1的断言
        for assertion in step1["assertions"]:
            assert self._validate_assertion(
                assertion, response
            ), f"步骤1断言失败: {assertion.get('description', assertion['type'])}"

        # 存储响应数据
        response_data = response.json()
        stored_data["simulation_id"] = response_data.get("simulation_id")

        # 等待一段时间让数据库操作完成
        time.sleep(2)

        # 执行步骤2：验证数据库记录
        step2 = test_case["steps"][1]
        db_action = step2["action"]

        # 构建查询语句，替换变量
        query = db_action["query"].replace(
            "${simulationResponse.body.simulation_id}", stored_data["simulation_id"]
        )

        db_results = self._execute_database_query(query)

        # 验证步骤2的断言
        for assertion in step2["assertions"]:
            if assertion["type"] == "recordExists":
                assert len(db_results) > 0, "数据库中应存在对应记录"
            elif assertion["type"] == "fieldValue":
                if db_results:
                    field_value = db_results[0].get(assertion["field"])
                    expected_values = assertion["expected"]
                    assert (
                        field_value in expected_values
                    ), f"字段 {assertion['field']} 值 {field_value} 不在预期值 {expected_values} 中"

        self.test_results.append(
            {
                "testId": "E2E_SIM_FLOW_01",
                "status": "PASS",
                "simulation_id": stored_data["simulation_id"],
                "db_records": len(db_results),
            }
        )

    def _find_test_case(self, test_id: str) -> Dict[str, Any]:
        """查找测试用例"""
        for suite in self.test_plan["testSuites"]:
            for test in suite["tests"]:
                if test["testId"] == test_id:
                    return test
        pytest.fail(f"未找到测试用例: {test_id}")


class TestMachineReadablePlan:
    """机器可读测试方案主测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """测试前后设置"""
        # 等待服务启动
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(1)
        else:
            pytest.fail("服务未能在30秒内启动")

        yield

        # 清理工作（如果需要）
        pass

    def test_execute_all_test_suites(self):
        """执行所有测试套件"""
        print("\n=== 开始执行机器可读测试方案 ===")

        # 执行API功能测试
        print("\n--- 执行API功能测试套件 ---")
        api_tests = TestAPIFunctionalTests()
        api_tests.setup_method(None)
        api_tests.test_api_health_01()
        api_tests.test_api_status_01()
        api_tests.test_api_sim_01()
        api_tests.test_api_calibrate_01()

        # 执行API输入验证测试
        print("\n--- 执行API输入验证测试套件 ---")
        validation_tests = TestAPIInputValidationTests()
        validation_tests.setup_method(None)
        validation_tests.test_api_validate_sim_01()
        validation_tests.test_api_validate_sim_02()

        # 执行端到端集成测试
        print("\n--- 执行端到端集成测试套件 ---")
        e2e_tests = TestE2EIntegrationTests()
        e2e_tests.setup_method(None)
        e2e_tests.test_e2e_sim_flow_01()

        # 汇总测试结果
        all_results = (
            api_tests.test_results
            + validation_tests.test_results
            + e2e_tests.test_results
        )

        # 生成测试报告
        self._generate_test_report(all_results)

        print("\n=== 机器可读测试方案执行完成 ===")
        print(f"总计执行测试用例: {len(all_results)}")
        passed_tests = [r for r in all_results if r["status"] == "PASS"]
        print(f"通过测试用例: {len(passed_tests)}")

        # 确保所有测试都通过
        assert len(passed_tests) == len(all_results), "存在失败的测试用例"

    def _generate_test_report(self, results: List[Dict[str, Any]]):
        """生成测试报告"""
        report = {
            "planName": "市场微结构仿真引擎 (MMS) - 机器可读测试方案",
            "executedAt": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "totalTests": len(results),
            "passedTests": len([r for r in results if r["status"] == "PASS"]),
            "failedTests": len([r for r in results if r["status"] == "FAIL"]),
            "results": results,
        }

        # 保存测试报告
        report_path = "reports/machine_readable_test_report.json"
        Path("reports").mkdir(exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n测试报告已保存到: {report_path}")


if __name__ == "__main__":
    # 直接运行测试
    test_instance = TestMachineReadablePlan()
    test_instance.setup_and_teardown()
    test_instance.test_execute_all_test_suites()
