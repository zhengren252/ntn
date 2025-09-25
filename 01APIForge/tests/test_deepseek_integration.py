#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek LLM API 集成测试
测试与DeepSeek API的真实通信能力
"""

import json
import time
import requests
import os
from typing import Dict, Any


class DeepSeekIntegrationTester:
    """DeepSeek API集成测试器"""

    def __init__(self):
        self.api_key = os.getenv(
            "DEEPSEEK_API_KEY", "sk-f442d2f7e74842ba93f347998d07761e"
        )
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.test_results = []

    def log_test_result(self, case_id: str, title: str, status: str, details: str = ""):
        """记录测试结果"""
        result = {
            "case_id": case_id,
            "title": title,
            "status": status,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.test_results.append(result)
        print(f"[{status}] {case_id}: {title}")
        if details:
            print(f"    Details: {details}")

    def test_api_credentials(self) -> bool:
        """测试API凭证配置"""
        if not self.api_key or self.api_key == "test-api-key":
            self.log_test_result(
                "DEEPSEEK-CRED-01", "API凭证检查", "FAIL", "DeepSeek API Key未正确配置"
            )
            return False

        self.log_test_result(
            "DEEPSEEK-CRED-01", "API凭证检查", "PASS", f"API Key已配置: {self.api_key[:10]}..."
        )
        return True

    def test_chat_completion(self) -> bool:
        """测试聊天完成API"""
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello! This is a test message for API Factory integration testing. Please respond with a simple greeting.",
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.7,
            }

            print(f"发送请求到: {url}")
            print(f"使用模型: {self.model}")

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()

                # 验证响应格式
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    content = message.get("content", "")

                    if content:
                        self.log_test_result(
                            "DEEPSEEK-CHAT-01",
                            "聊天完成API测试",
                            "PASS",
                            f"成功获取回复: {content[:100]}...",
                        )
                        return True
                    else:
                        self.log_test_result(
                            "DEEPSEEK-CHAT-01", "聊天完成API测试", "FAIL", "响应中没有内容"
                        )
                        return False
                else:
                    self.log_test_result(
                        "DEEPSEEK-CHAT-01", "聊天完成API测试", "FAIL", f"响应格式不正确: {result}"
                    )
                    return False
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.log_test_result("DEEPSEEK-CHAT-01", "聊天完成API测试", "FAIL", error_msg)
                return False

        except requests.exceptions.Timeout:
            self.log_test_result("DEEPSEEK-CHAT-01", "聊天完成API测试", "FAIL", "请求超时")
            return False
        except Exception as e:
            self.log_test_result(
                "DEEPSEEK-CHAT-01", "聊天完成API测试", "FAIL", f"异常: {str(e)}"
            )
            return False

    def test_model_list(self) -> bool:
        """测试模型列表API（如果可用）"""
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if "data" in result:
                    models = result["data"]
                    self.log_test_result(
                        "DEEPSEEK-MODELS-01",
                        "模型列表API测试",
                        "PASS",
                        f"成功获取 {len(models)} 个模型",
                    )
                    return True
                else:
                    self.log_test_result(
                        "DEEPSEEK-MODELS-01", "模型列表API测试", "FAIL", "响应格式不正确"
                    )
                    return False
            elif response.status_code == 404:
                self.log_test_result(
                    "DEEPSEEK-MODELS-01", "模型列表API测试", "SKIP", "模型列表API不可用"
                )
                return True  # 不是必需的API
            else:
                self.log_test_result(
                    "DEEPSEEK-MODELS-01",
                    "模型列表API测试",
                    "FAIL",
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test_result(
                "DEEPSEEK-MODELS-01", "模型列表API测试", "FAIL", f"异常: {str(e)}"
            )
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有DeepSeek集成测试"""
        print("\n=== DeepSeek LLM API 集成测试 ===")
        print("目标: 验证与DeepSeek API的通信能力")
        print("=" * 40)

        # 检查API凭证
        if not self.test_api_credentials():
            return {
                "status": "FAILED",
                "reason": "API凭证未正确配置",
                "results": self.test_results,
            }

        # 运行测试用例
        tests = [
            ("聊天完成API测试", self.test_chat_completion),
            ("模型列表API测试", self.test_model_list),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n运行测试: {test_name}")
            if test_func():
                passed += 1

        # 生成测试报告
        success_rate = (passed / total) * 100
        status = "PASSED" if passed == total else "PARTIAL" if passed > 0 else "FAILED"

        print(f"\n=== DeepSeek测试结果 ===")
        print(f"通过: {passed}/{total} ({success_rate:.1f}%)")
        print(f"状态: {status}")

        return {
            "status": status,
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "results": self.test_results,
        }

    def save_report(self, results: Dict[str, Any]):
        """保存测试报告"""
        report_file = "deepseek_integration_test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nDeepSeek测试报告已保存: {report_file}")


def main():
    """主函数"""
    tester = DeepSeekIntegrationTester()
    results = tester.run_all_tests()
    tester.save_report(results)

    # 返回适当的退出码
    if results["status"] == "FAILED":
        return False
    else:
        return True


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
