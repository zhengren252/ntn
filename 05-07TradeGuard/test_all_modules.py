import os
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
所有模组连接测试
验证TACoreService与各个模组的连接状态
"""

import zmq
import json
import time
from typing import Dict, Any, List


class ModuleConnectionTester:
    def __init__(self, service_endpoint: str = "tcp://localhost:5555"):
        self.service_endpoint = service_endpoint
        self.context = zmq.Context()
        self.socket = None
        self.request_id = 0
        self.test_results = []

    def connect(self) -> bool:
        """连接到TACoreService"""
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            self.socket.setsockopt(zmq.SNDTIMEO, 5000)
            self.socket.connect(self.service_endpoint)
            print(f"✅ 已连接到TACoreService: {self.service_endpoint}")
            return True
        except Exception as e:
            print(f"❌ 连接TACoreService失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
        self.context.term()

    def send_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送请求"""
        if not self.socket:
            if not self.connect():
                return {"error": "连接失败"}

        self.request_id += 1
        request = {"id": self.request_id, "method": method, "params": params or {}}

        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            return response
        except Exception as e:
            return {"error": str(e)}

    def test_system_health(self) -> bool:
        """测试系统健康状况"""
        print("\n🏥 测试系统健康状况...")
        response = self.send_request("system.health")

        if "result" in response and response["result"].get("status") == "healthy":
            print("✅ 系统健康检查通过")
            self.test_results.append(
                {"test": "system.health", "status": "pass", "response": response}
            )
            return True
        else:
            print(f"❌ 系统健康检查失败: {response}")
            self.test_results.append(
                {"test": "system.health", "status": "fail", "response": response}
            )
            return False

    def test_market_scan(self) -> bool:
        """测试市场扫描功能"""
        print("\n📊 测试市场扫描功能...")
        params = {"symbol": "BTCUSDT", "timeframe": "1h", "indicators": ["RSI", "MACD"]}
        response = self.send_request("scan.market", params)

        if "result" in response:
            print("✅ 市场扫描功能正常")
            print(f"   扫描结果: {json.dumps(response['result'], indent=2)}")
            self.test_results.append(
                {"test": "scan.market", "status": "pass", "response": response}
            )
            return True
        else:
            print(f"❌ 市场扫描功能失败: {response}")
            self.test_results.append(
                {"test": "scan.market", "status": "fail", "response": response}
            )
            return False

    def test_trade_execution(self) -> bool:
        """测试交易执行功能"""
        print("\n💰 测试交易执行功能...")
        params = {
            "symbol": "BTCUSDT",
            "side": "buy",
            "amount": 0.001,
            "price": 45000,
            "type": "limit",
        }
        response = self.send_request("trade.execute", params)

        if "result" in response:
            print("✅ 交易执行功能正常")
            print(f"   执行结果: {json.dumps(response['result'], indent=2)}")
            self.test_results.append(
                {"test": "trade.execute", "status": "pass", "response": response}
            )
            return True
        else:
            print(f"❌ 交易执行功能失败: {response}")
            self.test_results.append(
                {"test": "trade.execute", "status": "fail", "response": response}
            )
            return False

    def test_risk_assessment(self) -> bool:
        """测试风险评估功能"""
        print("\n⚠️ 测试风险评估功能...")
        params = {
            "portfolio": {
                "BTCUSDT": {"amount": 0.5, "value": 22500},
                "ETHUSDT": {"amount": 10, "value": 25000},
            },
            "market_conditions": "volatile",
        }
        response = self.send_request("risk.assess", params)

        if "result" in response:
            print("✅ 风险评估功能正常")
            print(f"   评估结果: {json.dumps(response['result'], indent=2)}")
            self.test_results.append(
                {"test": "risk.assess", "status": "pass", "response": response}
            )
            return True
        else:
            print(f"❌ 风险评估功能失败: {response}")
            self.test_results.append(
                {"test": "risk.assess", "status": "fail", "response": response}
            )
            return False

    def test_fund_allocation(self) -> bool:
        """测试资金分配功能"""
        print("\n💼 测试资金分配功能...")
        params = {
            "total_capital": 100000,
            "risk_tolerance": "medium",
            "strategies": ["momentum", "mean_reversion"],
        }
        response = self.send_request("fund.allocate", params)

        if "result" in response:
            print("✅ 资金分配功能正常")
            print(f"   分配结果: {json.dumps(response['result'], indent=2)}")
            self.test_results.append(
                {"test": "fund.allocate", "status": "pass", "response": response}
            )
            return True
        else:
            print(f"❌ 资金分配功能失败: {response}")
            self.test_results.append(
                {"test": "fund.allocate", "status": "fail", "response": response}
            )
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始全模组连接测试...")
        print("=" * 50)

        # 连接测试
        if not self.connect():
            return {"status": "failed", "error": "无法连接到TACoreService"}

        # 执行各项测试
        tests = [
            self.test_system_health,
            self.test_market_scan,
            self.test_trade_execution,
            self.test_risk_assessment,
            self.test_fund_allocation,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            try:
                if test():
                    passed += 1
                time.sleep(0.5)  # 避免请求过于频繁
            except Exception as e:
                print(f"❌ 测试执行异常: {e}")

        # 生成测试报告
        print("\n" + "=" * 50)
        print("📋 测试结果汇总:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")
        print(f"   成功率: {(passed/total)*100:.1f}%")

        status = "passed" if passed == total else "partial" if passed > 0 else "failed"

        return {
            "status": status,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": (passed / total) * 100,
            "test_results": self.test_results,
        }


def main():
    """主函数"""
    tester = ModuleConnectionTester()

    try:
        result = tester.run_all_tests()

        if result["status"] == "passed":
            print("\n🎉 所有模组连接测试通过！")
        elif result["status"] == "partial":
            print("\n⚠️ 部分模组连接测试通过，请检查失败项目")
        else:
            print("\n❌ 模组连接测试失败，请检查系统状态")

        return result["status"] == "passed"

    except KeyboardInterrupt:
        print("\n用户中断测试")
        return False
    except Exception as e:
        print(f"\n测试过程中出现异常: {e}")
        return False
    finally:
        tester.disconnect()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
