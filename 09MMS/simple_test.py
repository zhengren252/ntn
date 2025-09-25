#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的API测试脚本
"""

import requests
import json
import time

BASE_URL = "http://localhost:8001/api/v1"


def test_health():
    """测试健康检查端点"""
    print("\n=== 测试健康检查端点 ===")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_status():
    """测试状态端点"""
    print("\n=== 测试状态端点 ===")
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_simulate():
    """测试仿真端点"""
    print("\n=== 测试仿真端点 ===")
    try:
        payload = {
            "symbol": "BTCUSDT",
            "period": "30d",
            "scenario": "normal",
            "strategy_params": {
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
            },
        }

        response = requests.post(
            f"{BASE_URL}/simulate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    """主测试函数"""
    print("开始执行简化API测试...")

    results = []

    # 测试健康检查
    results.append(("健康检查", test_health()))

    # 测试状态
    results.append(("状态查询", test_status()))

    # 测试仿真
    results.append(("仿真请求", test_simulate()))

    # 汇总结果
    print("\n=== 测试结果汇总 ===")
    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("🎉 所有测试都通过了！")
        return True
    else:
        print("❌ 部分测试失败")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
