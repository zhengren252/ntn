#!/usr/bin/env python3
"""
调试测试客户端 - 模拟LazyPirateClient的行为
"""

import zmq
import json
import time
import uuid


def test_zmq_connection():
    """测试ZMQ连接"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

    try:
        # 准备请求数据 - 模拟测试用例
        request_id = f"test_{int(time.time())}"
        request = {
            "request_id": request_id,
            "method": "scan.market",
            "params": {
                "market_type": "crypto",
                "symbols": ["BTC/USDT", "ETH/USDT"],
                "scan_type": "opportunities",
            },
        }

        print(f"发送请求: {request}")

        # 发送请求
        socket.send_string(json.dumps(request))

        # 设置超时
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        if poller.poll(5000):  # 5秒超时
            try:
                # 尝试接收单帧响应
                response_json = socket.recv_string(zmq.NOBLOCK)
                response = json.loads(response_json)
                print(f"收到单帧响应: {response}")
                print(f"响应状态: {response.get('status')}")
                return response
            except zmq.Again:
                print("没有更多数据")
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                # 尝试接收多帧消息
                try:
                    parts = socket.recv_multipart(zmq.NOBLOCK)
                    print(f"收到多帧消息，共{len(parts)}帧:")
                    for i, part in enumerate(parts):
                        try:
                            decoded = part.decode("utf-8")
                            print(f"  帧{i}: {decoded[:200]}")
                        except:
                            print(f"  帧{i}: {part[:50]} (二进制)")

                    # 尝试解析最后一帧
                    if parts:
                        try:
                            response_json = parts[-1].decode("utf-8")
                            response = json.loads(response_json)
                            print(f"解析最后一帧成功: {response.get('status')}")
                            return response
                        except Exception as e2:
                            print(f"解析最后一帧失败: {e2}")
                except zmq.Again:
                    print("没有多帧数据")
        else:
            print("请求超时")
            return None

    except Exception as e:
        print(f"发生错误: {e}")
        return None
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    print("=== 调试测试客户端 ===")
    result = test_zmq_connection()
    if result:
        print(f"\n最终结果: {result.get('status')}")
    else:
        print("\n测试失败")
