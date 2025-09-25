#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的TACoreService测试脚本
用于验证基本功能
"""

import zmq
import json
import time
from datetime import datetime


class SimpleTACoreClient:
    """简化的TACoreService客户端"""

    def __init__(self, host="localhost", port=5555):
        self.host = host
        self.port = port
        self.context = None
        self.socket = None

    def connect(self):
        """连接到服务"""
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(f"tcp://{self.host}:{self.port}")
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            print(f"✓ Connected to TACoreService at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        print("✓ Disconnected from TACoreService")

    def send_request(self, method, params=None):
        """发送请求"""
        if not self.socket:
            return None

        try:
            request = {
                "method": method,
                "params": params or {},
                "request_id": str(int(time.time() * 1000)),
            }

            print(f"Sending: {method}")
            self.socket.send_json(request)
            response = self.socket.recv_json()

            if response.get("status") == "success":
                print(f"✓ {method} - Success")
                return response
            else:
                print(f"✗ {method} - Error: {response.get('message', 'Unknown error')}")
                return response

        except zmq.Again:
            print(f"✗ {method} - Timeout")
            return None
        except Exception as e:
            print(f"✗ {method} - Exception: {e}")
            return None


def run_simple_tests():
    """运行简化测试"""
    print("=" * 50)
    print("TACoreService Simple Integration Test")
    print("=" * 50)

    client = SimpleTACoreClient()

    # 连接测试
    if not client.connect():
        print("❌ Connection failed - TACoreService may not be running")
        return False

    try:
        # 测试1: 健康检查
        print("\n1. Testing Health Check...")
        response = client.send_request("health.check")
        if not response or response.get("status") != "success":
            print("❌ Health check failed")
            return False

        # 测试2: 市场扫描
        print("\n2. Testing Market Scan...")
        response = client.send_request("scan.market")
        if not response or response.get("status") != "success":
            print("❌ Market scan failed")
            return False

        # 测试3: 交易对分析
        print("\n3. Testing Symbol Analysis...")
        response = client.send_request("analyze.symbol", {"symbol": "BTCUSDT"})
        if not response or response.get("status") != "success":
            print("❌ Symbol analysis failed")
            return False

        # 测试4: 市场数据获取
        print("\n4. Testing Market Data...")
        response = client.send_request("get.market_data", {"symbol": "BTCUSDT"})
        if not response or response.get("status") != "success":
            print("❌ Market data failed")
            return False

        # 测试5: 无效方法测试
        print("\n5. Testing Invalid Method...")
        response = client.send_request("invalid.method")
        if not response or response.get("status") != "error":
            print("❌ Invalid method test failed")
            return False

        print("\n🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    finally:
        client.disconnect()


if __name__ == "__main__":
    success = run_simple_tests()
    exit(0 if success else 1)
