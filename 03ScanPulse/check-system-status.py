#!/usr/bin/env python3
"""
AI智能体驱动交易系统 V3.5 - 系统状态检查脚本
检查所有12个模组的运行状态和健康状况
"""

import requests
import zmq
import redis
import json
import time
from typing import Dict, List, Tuple
from datetime import datetime


class SystemStatusChecker:
    def __init__(self):
        self.services = {
            "tacore_service": {"type": "zmq", "address": "tcp://localhost:5555"},
            "redis": {"type": "redis", "host": "localhost", "port": 6379},
            "api_factory": {"type": "http", "url": "http://localhost:8001/health"},
            "crawler": {"type": "http", "url": "http://localhost:8002/health"},
            "scanner": {"type": "http", "url": "http://localhost:8003/health"},
            "trader": {"type": "http", "url": "http://localhost:8004/health"},
            "risk_manager": {"type": "http", "url": "http://localhost:8005/health"},
            "portfolio": {"type": "http", "url": "http://localhost:8006/health"},
            "notifier": {"type": "http", "url": "http://localhost:8007/health"},
            "analytics": {"type": "http", "url": "http://localhost:8008/health"},
            "backtester": {"type": "http", "url": "http://localhost:8009/health"},
            "web_ui": {"type": "http", "url": "http://localhost:3000"},
            "monitor": {"type": "http", "url": "http://localhost:9090"},
        }

    def check_zmq_service(self, address: str) -> Tuple[bool, str]:
        """检查ZMQ服务状态"""
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            socket.connect(address)

            # 发送健康检查请求
            health_request = {
                "method": "health.check",
                "params": {},
                "id": "health_check_" + str(int(time.time())),
            }

            socket.send_json(health_request)
            response = socket.recv_json()

            socket.close()
            context.term()

            if response.get("result", {}).get("status") == "success":
                return True, "健康"
            else:
                return False, f"响应异常: {response}"

        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def check_redis_service(self, host: str, port: int) -> Tuple[bool, str]:
        """检查Redis服务状态"""
        try:
            r = redis.Redis(host=host, port=port, socket_timeout=5)
            r.ping()
            info = r.info()
            return True, f"健康 (连接数: {info.get('connected_clients', 'N/A')})"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def check_http_service(self, url: str) -> Tuple[bool, str]:
        """检查HTTP服务状态"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True, f"健康 (状态码: {response.status_code})"
            else:
                return False, f"状态码异常: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "连接被拒绝"
        except requests.exceptions.Timeout:
            return False, "请求超时"
        except Exception as e:
            return False, f"请求失败: {str(e)}"

    def check_service(self, name: str, config: Dict) -> Tuple[bool, str]:
        """检查单个服务状态"""
        service_type = config["type"]

        if service_type == "zmq":
            return self.check_zmq_service(config["address"])
        elif service_type == "redis":
            return self.check_redis_service(config["host"], config["port"])
        elif service_type == "http":
            return self.check_http_service(config["url"])
        else:
            return False, f"未知服务类型: {service_type}"

    def check_all_services(self) -> Dict[str, Tuple[bool, str]]:
        """检查所有服务状态"""
        results = {}

        print("正在检查系统状态...\n")

        for service_name, config in self.services.items():
            print(f"检查 {service_name}...", end=" ")
            is_healthy, message = self.check_service(service_name, config)
            results[service_name] = (is_healthy, message)

            status_icon = "✅" if is_healthy else "❌"
            print(f"{status_icon} {message}")

        return results

    def generate_report(self, results: Dict[str, Tuple[bool, str]]) -> None:
        """生成状态报告"""
        print("\n" + "=" * 60)
        print("AI智能体驱动交易系统 V3.5 - 系统状态报告")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 核心服务状态
        print("🔧 核心服务层:")
        core_services = ["tacore_service", "redis"]
        for service in core_services:
            if service in results:
                is_healthy, message = results[service]
                status_icon = "✅" if is_healthy else "❌"
                print(f"  {status_icon} {service}: {message}")

        print()

        # 业务模组状态
        print("📊 业务模组层:")
        business_services = [
            "api_factory",
            "crawler",
            "scanner",
            "trader",
            "risk_manager",
            "portfolio",
            "notifier",
            "analytics",
            "backtester",
            "web_ui",
            "monitor",
        ]

        for service in business_services:
            if service in results:
                is_healthy, message = results[service]
                status_icon = "✅" if is_healthy else "❌"
                print(f"  {status_icon} {service}: {message}")

        print()

        # 统计信息
        total_services = len(results)
        healthy_services = sum(1 for is_healthy, _ in results.values() if is_healthy)
        unhealthy_services = total_services - healthy_services

        print("📈 统计信息:")
        print(f"  总服务数: {total_services}")
        print(f"  健康服务: {healthy_services}")
        print(f"  异常服务: {unhealthy_services}")
        print(f"  系统健康度: {(healthy_services/total_services)*100:.1f}%")

        if unhealthy_services > 0:
            print("\n⚠️  异常服务列表:")
            for service_name, (is_healthy, message) in results.items():
                if not is_healthy:
                    print(f"  - {service_name}: {message}")

        print("\n" + "=" * 60)

        # 系统整体状态
        if unhealthy_services == 0:
            print("🎉 系统状态: 全部服务正常运行")
        elif unhealthy_services <= 2:
            print("⚠️  系统状态: 部分服务异常，建议检查")
        else:
            print("🚨 系统状态: 多个服务异常，需要立即处理")


def main():
    checker = SystemStatusChecker()
    results = checker.check_all_services()
    checker.generate_report(results)


if __name__ == "__main__":
    main()
