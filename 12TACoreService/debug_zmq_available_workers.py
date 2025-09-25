#!/usr/bin/env python3
"""
调试ZMQ available_workers状态
"""

import zmq
import json
import time


def debug_zmq_available_workers():
    """通过ZMQ直接查询LoadBalancer的available_workers状态"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    try:
        # 连接到LoadBalancer
        socket.connect("tcp://localhost:5555")
        socket.setsockopt(zmq.LINGER, 0)

        # 发送调试请求
        debug_request = {
            "method": "debug.available_workers",
            "params": {},
            "id": "debug_001",
        }

        print("发送调试请求...")
        socket.send_json(debug_request)

        # 等待响应
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        if poller.poll(5000):  # 5秒超时
            # 尝试接收单帧响应
            try:
                response = socket.recv_json(zmq.NOBLOCK)
                print(f"收到响应: {response}")
            except zmq.Again:
                # 尝试接收多帧响应
                try:
                    frames = socket.recv_multipart(zmq.NOBLOCK)
                    print(f"收到多帧响应: {len(frames)} 帧")
                    for i, frame in enumerate(frames):
                        try:
                            if isinstance(frame, bytes):
                                decoded = frame.decode("utf-8")
                                print(f"帧 {i}: {decoded}")
                                # 尝试解析为JSON
                                try:
                                    json_data = json.loads(decoded)
                                    print(f"帧 {i} JSON: {json_data}")
                                except json.JSONDecodeError:
                                    pass
                            else:
                                print(f"帧 {i}: {frame}")
                        except UnicodeDecodeError:
                            print(f"帧 {i}: 二进制数据 (长度: {len(frame)})")
                except Exception as e:
                    print(f"接收多帧响应时出错: {e}")
        else:
            print("请求超时")

    except Exception as e:
        print(f"调试时发生错误: {e}")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    print("=== ZMQ Available Workers 调试 ===")
    debug_zmq_available_workers()
