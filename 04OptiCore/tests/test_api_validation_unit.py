#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus (NTN) - API输入验证单元测试

测试用例：
- UNIT-API-01: 测试API输入验证失败场景
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# 导入API应用
from api.app import app


class TestAPIValidationUnit:
    """
    API输入验证单元测试类
    """

    def setup_method(self):
        """测试方法设置"""
        self.client = TestClient(app)

    def test_unit_api_01_missing_required_field(self):
        """
        UNIT-API-01: 测试API输入验证失败场景 - 缺少必需字段strategy_id

        测试步骤：
        1. Mock API的依赖服务
        2. 向 POST /api/backtest/start 端点发送缺少strategy_id字段的请求
        3. 验证返回422状态码和相应错误信息
        """
        print("\n=== 开始执行 UNIT-API-01: API输入验证失败测试 ===")

        # Mock依赖服务
        with patch("api.app.backtest_engine") as mock_engine:
            mock_engine.return_value = Mock()

            # 准备缺少必需字段的请求数据
            invalid_request = {
                "symbol": "BTC/USDT",
                # 故意缺少strategy_configs字段
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_capital": 10000,
            }

            print(f"发送无效请求: {json.dumps(invalid_request, indent=2)}")

            # 发送请求
            response = self.client.post("/api/backtest/start", json=invalid_request)

            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

            # 验证响应状态码
            assert response.status_code == 422, f"期望状态码422，实际得到{response.status_code}"

            # 验证响应内容
            response_data = response.json()
            assert "detail" in response_data, "响应中应包含detail字段"

            # 验证错误信息包含字段缺失信息
            detail = response_data["detail"]
            if isinstance(detail, list) and len(detail) > 0:
                error_msg = str(detail[0])
                assert (
                    "field required" in error_msg.lower()
                    or "strategy_configs" in error_msg
                ), f"错误信息应包含字段缺失信息，实际: {error_msg}"
            else:
                error_msg = str(detail)
                assert (
                    "field required" in error_msg.lower()
                    or "strategy_configs" in error_msg
                ), f"错误信息应包含字段缺失信息，实际: {error_msg}"

            print("✅ UNIT-API-01 测试通过：API正确返回422状态码和字段缺失错误")

    def test_unit_api_02_invalid_field_type(self):
        """
        UNIT-API-02: 测试API输入验证失败场景 - 字段类型错误

        测试步骤：
        1. Mock API的依赖服务
        2. 向 POST /api/backtest/start 端点发送字段类型错误的请求
        3. 验证返回422状态码和相应错误信息
        """
        print("\n=== 开始执行 UNIT-API-02: API字段类型验证测试 ===")

        # Mock依赖服务
        with patch("api.app.backtest_engine") as mock_engine:
            mock_engine.return_value = Mock()

            # 准备字段类型错误的请求数据
            invalid_request = {
                "symbol": "BTC/USDT",
                "strategy_configs": "invalid_type",  # 应该是列表，但传入字符串
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_capital": "invalid_number",  # 应该是数字，但传入字符串
            }

            print(f"发送类型错误请求: {json.dumps(invalid_request, indent=2)}")

            # 发送请求
            response = self.client.post("/api/backtest/start", json=invalid_request)

            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

            # 验证响应状态码
            assert response.status_code == 422, f"期望状态码422，实际得到{response.status_code}"

            # 验证响应内容
            response_data = response.json()
            assert "detail" in response_data, "响应中应包含detail字段"

            print("✅ UNIT-API-02 测试通过：API正确返回422状态码和类型错误信息")

    def test_unit_api_03_empty_request_body(self):
        """
        UNIT-API-03: 测试API输入验证失败场景 - 空请求体

        测试步骤：
        1. Mock API的依赖服务
        2. 向 POST /api/backtest/start 端点发送空请求体
        3. 验证返回422状态码和相应错误信息
        """
        print("\n=== 开始执行 UNIT-API-03: API空请求体验证测试 ===")

        # Mock依赖服务
        with patch("api.app.backtest_engine") as mock_engine:
            mock_engine.return_value = Mock()

            print("发送空请求体")

            # 发送空请求
            response = self.client.post("/api/backtest/start", json={})

            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

            # 验证响应状态码
            assert response.status_code == 422, f"期望状态码422，实际得到{response.status_code}"

            # 验证响应内容
            response_data = response.json()
            assert "detail" in response_data, "响应中应包含detail字段"

            print("✅ UNIT-API-03 测试通过：API正确返回422状态码和空请求体错误")


def run_api_validation_tests():
    """
    运行API输入验证测试
    """
    print("\n" + "=" * 60)
    print("开始执行API输入验证单元测试")
    print("=" * 60)

    test_instance = TestAPIValidationUnit()

    try:
        # 执行测试用例
        test_instance.setup_method()
        test_instance.test_unit_api_01_missing_required_field()

        test_instance.setup_method()
        test_instance.test_unit_api_02_invalid_field_type()

        test_instance.setup_method()
        test_instance.test_unit_api_03_empty_request_body()

        print("\n" + "=" * 60)
        print("✅ 所有API输入验证单元测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ API输入验证测试失败: {e}")
        raise


if __name__ == "__main__":
    run_api_validation_tests()
