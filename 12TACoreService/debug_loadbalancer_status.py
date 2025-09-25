#!/usr/bin/env python3
"""
调试LoadBalancer状态
"""

import requests
import json


def check_loadbalancer_status():
    """检查LoadBalancer状态"""
    try:
        # 检查HTTP API状态
        response = requests.get("http://localhost:8080/api/status")
        if response.status_code == 200:
            status_data = response.json()
            print("=== LoadBalancer HTTP API 状态 ===")
            print(f"状态: {status_data.get('status')}")
            print(f"版本: {status_data.get('version')}")
            print(f"启动时间: {status_data.get('uptime')}")
            print()

        # 检查worker状态
        response = requests.get("http://localhost:8080/api/workers")
        if response.status_code == 200:
            workers_data = response.json()
            print("=== Worker 状态 ===")

            # workers_data 是一个数组
            if isinstance(workers_data, list):
                total_workers = len(workers_data)
                active_workers = [
                    w for w in workers_data if w.get("status") == "active"
                ]
                idle_workers = [w for w in workers_data if w.get("status") == "idle"]
                stopped_workers = [
                    w for w in workers_data if w.get("status") == "stopped"
                ]

                print(f"总worker数: {total_workers}")
                print(f"活跃worker数: {len(active_workers)}")
                print(f"空闲worker数: {len(idle_workers)}")
                print(f"停止worker数: {len(stopped_workers)}")
                print()

                # 显示最近的worker状态
                recent_workers = [
                    w for w in workers_data if w.get("status") in ["active", "idle"]
                ][:5]
                print("=== 最近活跃的Worker ===")
                for worker in recent_workers:
                    print(f"Worker {worker.get('worker_id')}:")
                    print(f"  状态: {worker.get('status')}")
                    print(f"  处理请求数: {worker.get('processed_requests')}")
                    print(f"  最后见到: {worker.get('last_seen')}")
                    print()
            else:
                print(f"意外的数据格式: {type(workers_data)}")
                print(workers_data)

        return True

    except Exception as e:
        print(f"检查状态时发生错误: {e}")
        return False


if __name__ == "__main__":
    print("=== LoadBalancer 状态检查 ===")
    check_loadbalancer_status()
