#!/usr/bin/env python3
"""
TACoreService测试脚本

这个脚本用于测试TACoreService的各种功能
"""

import os
import sys
import json
import time
import zmq
import asyncio
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tacoreservice.config import get_settings
from tacoreservice.core.message_handler import ServiceRequest, ServiceResponse
from tacoreservice.monitoring.logger import ServiceLogger


class TACoreServiceTester:
    """TACoreService测试器"""

    def __init__(self):
        self.settings = get_settings()
        self.logger = ServiceLogger.get_logger("tester")
        self.zmq_context = None
        self.zmq_socket = None

    def setup_zmq(self):
        """设置ZeroMQ连接"""
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REQ)

        # 设置超时
        self.zmq_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10秒接收超时
        self.zmq_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5秒发送超时

        # 连接到服务
        endpoint = (
            f"tcp://{self.settings.zmq_bind_address}:{self.settings.zmq_frontend_port}"
        )
        self.zmq_socket.connect(endpoint)
        self.logger.info(f"连接到ZeroMQ服务: {endpoint}")

    def cleanup_zmq(self):
        """清理ZeroMQ连接"""
        if self.zmq_socket:
            self.zmq_socket.close()
        if self.zmq_context:
            self.zmq_context.term()

    def send_zmq_request(
        self, method: str, parameters: Dict[str, Any] = None
    ) -> Optional[ServiceResponse]:
        """发送ZeroMQ请求"""
        if not self.zmq_socket:
            self.setup_zmq()

        # 创建请求
        request = ServiceRequest(
            method=method,
            parameters=parameters or {},
            request_id=f"test_{int(time.time() * 1000)}",
        )

        try:
            # 发送请求
            self.logger.info(f"发送请求: {method}")
            self.zmq_socket.send_json(request.to_dict())

            # 接收响应
            response_data = self.zmq_socket.recv_json()
            response = ServiceResponse.from_dict(response_data)

            self.logger.info(f"收到响应: {response.status}")
            return response

        except zmq.Again:
            self.logger.error("请求超时")
            return None
        except Exception as e:
            self.logger.error(f"发送请求失败: {e}")
            return None

    def test_health_check(self) -> bool:
        """测试健康检查"""
        print("\n=== 测试健康检查 ===")

        response = self.send_zmq_request("health.check")

        if response and response.status == "success":
            print("✓ 健康检查通过")
            print(f"  响应时间: {response.response_time:.3f}秒")
            return True
        else:
            print("✗ 健康检查失败")
            if response:
                print(f"  错误: {response.error}")
            return False

    def test_market_scan(self) -> bool:
        """测试市场扫描"""
        print("\n=== 测试市场扫描 ===")

        parameters = {
            "market": "US",
            "criteria": {"min_volume": 1000000, "max_price": 100},
        }

        response = self.send_zmq_request("scan.market", parameters)

        if response and response.status == "success":
            print("✓ 市场扫描成功")
            print(f"  响应时间: {response.response_time:.3f}秒")
            if response.data:
                print(f"  扫描结果: {len(response.data.get('stocks', []))} 只股票")
            return True
        else:
            print("✗ 市场扫描失败")
            if response:
                print(f"  错误: {response.error}")
            return False

    def test_order_execution(self) -> bool:
        """测试订单执行"""
        print("\n=== 测试订单执行 ===")

        parameters = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "order_type": "MARKET",
        }

        response = self.send_zmq_request("execute.order", parameters)

        if response and response.status == "success":
            print("✓ 订单执行成功")
            print(f"  响应时间: {response.response_time:.3f}秒")
            if response.data:
                print(f"  订单ID: {response.data.get('order_id')}")
            return True
        else:
            print("✗ 订单执行失败")
            if response:
                print(f"  错误: {response.error}")
            return False

    def test_risk_evaluation(self) -> bool:
        """测试风险评估"""
        print("\n=== 测试风险评估 ===")

        parameters = {
            "portfolio": {"AAPL": 1000, "GOOGL": 500, "MSFT": 800},
            "risk_metrics": ["var", "sharpe_ratio", "max_drawdown"],
        }

        response = self.send_zmq_request("evaluate.risk", parameters)

        if response and response.status == "success":
            print("✓ 风险评估成功")
            print(f"  响应时间: {response.response_time:.3f}秒")
            if response.data:
                print(f"  风险指标: {list(response.data.keys())}")
            return True
        else:
            print("✗ 风险评估失败")
            if response:
                print(f"  错误: {response.error}")
            return False

    def test_stock_analysis(self) -> bool:
        """测试股票分析"""
        print("\n=== 测试股票分析 ===")

        parameters = {
            "symbol": "AAPL",
            "analysis_type": "technical",
            "timeframe": "1d",
            "indicators": ["sma", "rsi", "macd"],
        }

        response = self.send_zmq_request("analyze.stock", parameters)

        if response and response.status == "success":
            print("✓ 股票分析成功")
            print(f"  响应时间: {response.response_time:.3f}秒")
            if response.data:
                print(f"  分析结果: {list(response.data.keys())}")
            return True
        else:
            print("✗ 股票分析失败")
            if response:
                print(f"  错误: {response.error}")
            return False

    def test_market_data(self) -> bool:
        """测试市场数据获取"""
        print("\n=== 测试市场数据获取 ===")

        parameters = {
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "data_type": "quote",
            "fields": ["price", "volume", "change"],
        }

        response = self.send_zmq_request("get.market_data", parameters)

        if response and response.status == "success":
            print("✓ 市场数据获取成功")
            print(f"  响应时间: {response.response_time:.3f}秒")
            if response.data:
                print(f"  数据条数: {len(response.data)}")
            return True
        else:
            print("✗ 市场数据获取失败")
            if response:
                print(f"  错误: {response.error}")
            return False

    def test_http_api(self) -> bool:
        """测试HTTP API"""
        print("\n=== 测试HTTP API ===")

        base_url = f"http://{self.settings.http_host}:{self.settings.http_port}"

        # 测试健康检查
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✓ HTTP健康检查通过")
            else:
                print(f"✗ HTTP健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ HTTP健康检查失败: {e}")
            return False

        # 测试服务状态
        try:
            response = requests.get(f"{base_url}/api/status", timeout=5)
            if response.status_code == 200:
                print("✓ 服务状态API正常")
                data = response.json()
                print(f"  服务状态: {data.get('status')}")
            else:
                print(f"✗ 服务状态API失败: {response.status_code}")
        except Exception as e:
            print(f"✗ 服务状态API失败: {e}")

        # 测试工作进程状态
        try:
            response = requests.get(f"{base_url}/api/workers", timeout=5)
            if response.status_code == 200:
                print("✓ 工作进程状态API正常")
                data = response.json()
                print(f"  工作进程数: {len(data)}")
            else:
                print(f"✗ 工作进程状态API失败: {response.status_code}")
        except Exception as e:
            print(f"✗ 工作进程状态API失败: {e}")

        return True

    def test_performance(self, iterations: int = 100) -> bool:
        """测试性能"""
        print(f"\n=== 性能测试 ({iterations} 次请求) ===")

        start_time = time.time()
        success_count = 0
        total_response_time = 0

        for i in range(iterations):
            request_start = time.time()
            response = self.send_zmq_request("health.check")
            request_end = time.time()

            if response and response.status == "success":
                success_count += 1
                total_response_time += request_end - request_start

            if (i + 1) % 10 == 0:
                print(f"  完成 {i + 1}/{iterations} 次请求")

        end_time = time.time()
        total_time = end_time - start_time

        print(f"\n性能测试结果:")
        print(f"  总时间: {total_time:.3f}秒")
        print(f"  成功请求: {success_count}/{iterations}")
        print(f"  成功率: {success_count/iterations*100:.1f}%")
        print(f"  平均响应时间: {total_response_time/success_count*1000:.1f}ms")
        print(f"  吞吐量: {success_count/total_time:.1f} 请求/秒")

        return success_count > iterations * 0.9  # 90%成功率

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("开始TACoreService功能测试...")

        tests = [
            ("健康检查", self.test_health_check),
            ("市场扫描", self.test_market_scan),
            ("订单执行", self.test_order_execution),
            ("风险评估", self.test_risk_evaluation),
            ("股票分析", self.test_stock_analysis),
            ("市场数据", self.test_market_data),
            ("HTTP API", self.test_http_api),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"✗ {test_name}测试异常: {e}")

        print(f"\n=== 测试总结 ===")
        print(f"通过: {passed}/{total} ({passed/total*100:.1f}%)")

        return passed == total


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TACoreService 测试脚本")
    parser.add_argument(
        "test_type",
        choices=[
            "all",
            "health",
            "market",
            "order",
            "risk",
            "analysis",
            "data",
            "http",
            "performance",
        ],
        help="测试类型",
    )
    parser.add_argument("--iterations", type=int, default=100, help="性能测试迭代次数")
    parser.add_argument("--host", default="127.0.0.1", help="服务主机地址")
    parser.add_argument("--zmq-port", type=int, default=5555, help="ZeroMQ端口")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP端口")

    args = parser.parse_args()

    # 覆盖配置
    os.environ["ZMQ_BIND_ADDRESS"] = args.host
    os.environ["ZMQ_FRONTEND_PORT"] = str(args.zmq_port)
    os.environ["HTTP_HOST"] = args.host
    os.environ["HTTP_PORT"] = str(args.http_port)

    tester = TACoreServiceTester()

    try:
        if args.test_type == "all":
            success = tester.run_all_tests()
        elif args.test_type == "health":
            success = tester.test_health_check()
        elif args.test_type == "market":
            success = tester.test_market_scan()
        elif args.test_type == "order":
            success = tester.test_order_execution()
        elif args.test_type == "risk":
            success = tester.test_risk_evaluation()
        elif args.test_type == "analysis":
            success = tester.test_stock_analysis()
        elif args.test_type == "data":
            success = tester.test_market_data()
        elif args.test_type == "http":
            success = tester.test_http_api()
        elif args.test_type == "performance":
            success = tester.test_performance(args.iterations)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"测试失败: {e}")
        sys.exit(1)
    finally:
        tester.cleanup_zmq()


if __name__ == "__main__":
    main()
