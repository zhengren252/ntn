#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX交易所API集成测试
验证与OKX交易所的实际连接和API调用
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OKXAPIClient:
    """OKX API客户端"""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        base_url: str = "https://www.okx.com",
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.base_url = base_url

    def _generate_signature(
        self, timestamp: str, method: str, request_path: str, body: str = ""
    ) -> str:
        """生成OKX API签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding="utf8"),
            bytes(message, encoding="utf-8"),
            digestmod=hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode()

    def _get_headers(
        self, method: str, request_path: str, body: str = ""
    ) -> Dict[str, str]:
        """获取请求头"""
        timestamp = datetime.utcnow().isoformat()[:-3] + "Z"
        signature = self._generate_signature(timestamp, method, request_path, body)

        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        request_path = "/api/v5/account/balance"
        headers = self._get_headers("GET", request_path)

        response = requests.get(
            f"{self.base_url}{request_path}", headers=headers, timeout=30
        )

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else response.text,
        }

    def get_instruments(self, inst_type: str = "SPOT") -> Dict[str, Any]:
        """获取交易产品信息"""
        request_path = f"/api/v5/public/instruments?instType={inst_type}"

        response = requests.get(f"{self.base_url}{request_path}", timeout=30)

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else response.text,
        }

    def place_test_order(
        self, symbol: str = "BTC-USDT", side: str = "buy", size: str = "0.001"
    ) -> Dict[str, Any]:
        """下测试订单（极小金额）"""
        request_path = "/api/v5/trade/order"

        order_data = {
            "instId": symbol,
            "tdMode": "cash",  # 现金交易
            "side": side,
            "ordType": "market",  # 市价单
            "sz": size,
        }

        body = json.dumps(order_data)
        headers = self._get_headers("POST", request_path, body)

        response = requests.post(
            f"{self.base_url}{request_path}", headers=headers, data=body, timeout=30
        )

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else response.text,
            "order_data": order_data,
        }


class OKXIntegrationTester:
    """OKX集成测试器"""

    def __init__(self):
        self.api_key = os.getenv("OKX_API_KEY", "")
        self.secret_key = os.getenv("OKX_SECRET_KEY", "")
        self.passphrase = os.getenv("OKX_PASSPHRASE", "test-passphrase")
        self.base_url = os.getenv("OKX_BASE_URL", "https://www.okx.com")

        self.client = OKXAPIClient(
            self.api_key, self.secret_key, self.passphrase, self.base_url
        )

        self.test_results = []

    def log_test_result(self, test_id: str, title: str, status: str, details: str = ""):
        """记录测试结果"""
        result = {
            "test_id": test_id,
            "title": title,
            "status": status,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.test_results.append(result)
        print(f"[{status}] {test_id}: {title}")
        if details:
            print(f"    Details: {details}")

    def test_api_credentials(self) -> bool:
        """测试API凭证配置"""
        if not self.api_key or not self.secret_key:
            self.log_test_result(
                "OKX-CRED-01", "API凭证配置检查", "FAIL", "API Key或Secret Key未配置"
            )
            return False

        self.log_test_result(
            "OKX-CRED-01",
            "API凭证配置检查",
            "PASS",
            f"API Key: {self.api_key[:8]}..., Secret Key: {self.secret_key[:8]}...",
        )
        return True

    def test_public_api(self) -> bool:
        """测试公共API（不需要签名）"""
        try:
            result = self.client.get_instruments("SPOT")

            if result["status_code"] == 200:
                data = result["data"]
                if "data" in data and len(data["data"]) > 0:
                    self.log_test_result(
                        "OKX-PUB-01",
                        "公共API测试（获取交易产品）",
                        "PASS",
                        f"成功获取 {len(data['data'])} 个交易产品信息",
                    )
                    return True
                else:
                    self.log_test_result(
                        "OKX-PUB-01", "公共API测试（获取交易产品）", "FAIL", "返回数据格式不正确"
                    )
                    return False
            else:
                self.log_test_result(
                    "OKX-PUB-01",
                    "公共API测试（获取交易产品）",
                    "FAIL",
                    f"HTTP {result['status_code']}: {result['data']}",
                )
                return False

        except Exception as e:
            self.log_test_result(
                "OKX-PUB-01", "公共API测试（获取交易产品）", "FAIL", f"异常: {str(e)}"
            )
            return False

    def test_private_api(self) -> bool:
        """测试私有API（需要签名）"""
        try:
            result = self.client.get_account_balance()

            if result["status_code"] == 200:
                data = result["data"]
                if "data" in data:
                    self.log_test_result(
                        "OKX-PRIV-01", "私有API测试（获取账户余额）", "PASS", "成功获取账户余额信息"
                    )
                    return True
                else:
                    self.log_test_result(
                        "OKX-PRIV-01", "私有API测试（获取账户余额）", "FAIL", f"返回数据格式不正确: {data}"
                    )
                    return False
            elif result["status_code"] == 401:
                self.log_test_result(
                    "OKX-PRIV-01", "私有API测试（获取账户余额）", "FAIL", "认证失败，请检查API凭证"
                )
                return False
            else:
                self.log_test_result(
                    "OKX-PRIV-01",
                    "私有API测试（获取账户余额）",
                    "FAIL",
                    f"HTTP {result['status_code']}: {result['data']}",
                )
                return False

        except Exception as e:
            self.log_test_result(
                "OKX-PRIV-01", "私有API测试（获取账户余额）", "FAIL", f"异常: {str(e)}"
            )
            return False

    def test_order_placement(self) -> bool:
        """测试订单下单（INT-EX-02）"""
        try:
            # 注意：这是一个真实的订单测试，使用极小金额
            result = self.client.place_test_order("BTC-USDT", "buy", "0.00001")

            if result["status_code"] == 200:
                data = result["data"]
                if "data" in data and len(data["data"]) > 0:
                    order_info = data["data"][0]
                    if "ordId" in order_info:
                        self.log_test_result(
                            "INT-EX-02",
                            "执行OKX测试订单",
                            "PASS",
                            f"订单创建成功，订单ID: {order_info['ordId']}",
                        )
                        return True
                    else:
                        self.log_test_result(
                            "INT-EX-02", "执行OKX测试订单", "FAIL", f"返回数据缺少ordId: {data}"
                        )
                        return False
                else:
                    self.log_test_result(
                        "INT-EX-02", "执行OKX测试订单", "FAIL", f"返回数据格式不正确: {data}"
                    )
                    return False
            else:
                self.log_test_result(
                    "INT-EX-02",
                    "执行OKX测试订单",
                    "FAIL",
                    f"HTTP {result['status_code']}: {result['data']}",
                )
                return False

        except Exception as e:
            self.log_test_result("INT-EX-02", "执行OKX测试订单", "FAIL", f"异常: {str(e)}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有OKX集成测试"""
        print("\n=== OKX交易所API集成测试 ===")
        print("目标: 验证与OKX交易所的实际连接")
        print("=" * 40)

        tests = [
            ("API凭证配置检查", self.test_api_credentials),
            ("公共API测试", self.test_public_api),
            ("私有API测试", self.test_private_api),
            ("订单下单测试", self.test_order_placement),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n运行测试: {test_name}")
            if test_func():
                passed += 1
            else:
                # 如果前面的测试失败，可能影响后续测试
                if test_name in ["API凭证配置检查", "私有API测试"]:
                    print(f"关键测试失败，跳过后续测试")
                    break

        success_rate = (passed / total) * 100
        status = "PASSED" if passed == total else "PARTIAL" if passed > 0 else "FAILED"

        print(f"\n=== OKX集成测试结果 ===")
        print(f"通过: {passed}/{total} ({success_rate:.1f}%)")
        print(f"状态: {status}")

        return {
            "test_type": "OKX Integration Test",
            "status": status,
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "results": self.test_results,
        }

    def save_report(self, results: Dict[str, Any]):
        """保存测试报告"""
        report_file = "okx_integration_test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n测试报告已保存: {report_file}")


def main():
    """主函数"""
    # 加载环境变量
    from dotenv import load_dotenv

    load_dotenv()

    tester = OKXIntegrationTester()
    results = tester.run_all_tests()
    tester.save_report(results)

    # 返回适当的退出码
    if results["status"] == "FAILED":
        sys.exit(1)
    elif results["status"] == "PARTIAL":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
