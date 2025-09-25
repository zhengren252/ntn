#!/usr/bin/env python3
"""
调试LoadBalancer内部状态
"""

import zmq
import json
import time


def send_simple_request():
    """发送一个简单请求来触发worker响应处理"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    try:
        # 连接到LoadBalancer
        socket.connect("tcp://localhost:5555")
        socket.setsockopt(zmq.LINGER, 0)

        # 发送简单的扫描请求
        request = {
            "method": "scan.market",
            "params": {"symbol": "BTCUSDT", "timeframe": "1h"},
            "id": f"debug_{int(time.time())}",
        }

        print(f"发送请求: {request['method']}")
        socket.send_json(request)

        # 等待响应
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        if poller.poll(10000):  # 10秒超时
            try:
                # 尝试接收单帧响应
                response = socket.recv_json(zmq.NOBLOCK)
                print(f"收到单帧响应: {response.get('status', 'unknown')}")
                return True
            except zmq.Again:
                # 尝试接收多帧响应
                try:
                    frames = socket.recv_multipart(zmq.NOBLOCK)
                    print(f"收到多帧响应: {len(frames)} 帧")
                    if frames:
                        last_frame = frames[-1]
                        try:
                            response = json.loads(last_frame.decode("utf-8"))
                            print(f"最后一帧响应: {response.get('status', 'unknown')}")
                            return True
                        except:
                            print(f"无法解析最后一帧: {last_frame[:100]}")
                except Exception as e:
                    print(f"接收多帧响应时出错: {e}")
        else:
            print("请求超时")
            return False

    except Exception as e:
        print(f"发送请求时发生错误: {e}")
        return False
    finally:
        socket.close()
        context.term()


def check_worker_status_after_request():
    """检查请求后的worker状态"""
    import requests

    try:
        response = requests.get("http://localhost:8080/api/workers")
        if response.status_code == 200:
            workers_data = response.json()

            if isinstance(workers_data, list):
                active_workers = [
                    w for w in workers_data if w.get("status") == "active"
                ]
                idle_workers = [w for w in workers_data if w.get("status") == "idle"]

                print(f"\n=== 请求后Worker状态 ===")
                print(f"活跃worker数: {len(active_workers)}")
                print(f"空闲worker数: {len(idle_workers)}")

                # 显示最近处理过请求的worker
                processed_workers = [
                    w for w in workers_data if w.get("processed_requests", 0) > 0
                ][:3]
                print("\n=== 处理过请求的Worker ===")
                for worker in processed_workers:
                    print(f"Worker {worker.get('worker_id')}:")
                    print(f"  状态: {worker.get('status')}")
                    print(f"  处理请求数: {worker.get('processed_requests')}")
                    print(f"  最后见到: {worker.get('last_seen')}")
                    print()

        return True
    except Exception as e:
        print(f"检查worker状态时出错: {e}")
        return False


if __name__ == "__main__":
    print("=== LoadBalancer 内部状态调试 ===")

    # 1. 发送请求触发worker处理
    print("\n1. 发送测试请求...")
    success = send_simple_request()

    if success:
        # 2. 等待一下让状态更新
        print("\n2. 等待状态更新...")
        time.sleep(2)

        # 3. 检查worker状态
        print("\n3. 检查worker状态...")
        check_worker_status_after_request()

        # 4. 再次尝试发送请求看是否还有"No workers available"错误
        print("\n4. 再次发送请求验证...")
        success2 = send_simple_request()

        if not success2:
            print("\n❌ 仍然出现'No workers available'错误！")
            print("这确认了available_workers列表管理存在问题。")
        else:
            print("\n✅ 第二次请求成功！")
    else:
        print("\n❌ 第一次请求就失败了")
