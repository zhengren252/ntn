#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - ZeroMQ负载均衡器
实现基于ZeroMQ的负载均衡和任务分发

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import zmq
import zmq.asyncio

from .config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ZMQLoadBalancer:
    """ZeroMQ负载均衡器"""

    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.frontend = None  # 面向客户端的套接字
        self.backend = None  # 面向工作进程的套接字
        self.running = False
        self.worker_stats: Dict[str, dict] = {}  # 工作进程统计信息
        self.task_queue: List[dict] = []  # 任务队列
        self.active_tasks: Dict[str, dict] = {}  # 活跃任务

    async def start(self):
        """启动负载均衡器"""
        try:
            logger.info("正在启动ZeroMQ负载均衡器...")

            # 创建前端套接字（面向客户端）
            self.frontend = self.context.socket(zmq.ROUTER)
            self.frontend.bind(f"tcp://*:{settings.FRONTEND_PORT}")
            logger.info(f"前端套接字绑定到端口: {settings.FRONTEND_PORT}")

            # 创建后端套接字（面向工作进程）
            self.backend = self.context.socket(zmq.ROUTER)
            self.backend.bind(f"tcp://*:{settings.BACKEND_PORT}")
            logger.info(f"后端套接字绑定到端口: {settings.BACKEND_PORT}")

            self.running = True

            # 设置信号处理
            self._setup_signal_handlers()

            # 启动主循环
            await self._run_main_loop()

        except Exception as e:
            logger.error(f"启动负载均衡器失败: {e}")
            raise

    async def stop(self):
        """停止负载均衡器"""
        logger.info("正在停止ZeroMQ负载均衡器...")

        self.running = False

        # 通知所有工作进程停止
        await self._notify_workers_shutdown()

        # 关闭套接字
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()

        # 终止上下文
        self.context.term()

        logger.info("ZeroMQ负载均衡器已停止")

    async def _run_main_loop(self):
        """运行主循环"""
        logger.info("负载均衡器主循环已启动")

        # 创建轮询器
        poller = zmq.asyncio.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend, zmq.POLLIN)

        # 可用的工作进程队列
        available_workers = []

        while self.running:
            try:
                # 轮询套接字事件
                events = await poller.poll(timeout=1000)  # 1秒超时

                for socket, event in events:
                    if socket == self.backend and event == zmq.POLLIN:
                        # 处理来自工作进程的消息
                        await self._handle_worker_message(available_workers)

                    elif socket == self.frontend and event == zmq.POLLIN:
                        # 处理来自客户端的消息
                        await self._handle_client_message(available_workers)

                # 定期清理和统计
                await self._periodic_maintenance()

            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    logger.info("ZMQ上下文已终止，退出主循环")
                    break
                else:
                    logger.error(f"ZMQ错误: {e}")
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                await asyncio.sleep(1)

    async def _handle_worker_message(self, available_workers: List[bytes]):
        """处理来自工作进程的消息"""
        try:
            # 接收工作进程消息
            parts = await self.backend.recv_multipart()
            if len(parts) < 2:
                logger.error(f"工作进程消息格式错误，期望至少2个部分，实际收到{len(parts)}个")
                return

            worker_id = parts[0]
            message = parts[-1]  # 最后一个部分是消息内容

            # 解析消息
            try:
                msg_data = json.loads(message.decode("utf-8"))
            except json.JSONDecodeError:
                logger.error(f"无法解析工作进程消息: {message}")
                return

            msg_type = msg_data.get("type")

            if msg_type == "ready":
                # 工作进程就绪
                if worker_id not in available_workers:
                    available_workers.append(worker_id)
                    logger.info(f"工作进程就绪: {worker_id.decode()}")

                # 更新工作进程统计
                self.worker_stats[worker_id.decode()] = {
                    "status": "ready",
                    "last_seen": time.time(),
                    "tasks_completed": msg_data.get("tasks_completed", 0),
                    "uptime": msg_data.get("uptime", 0),
                }

            elif msg_type == "result":
                # 任务结果
                task_id = msg_data.get("task_id")
                client_id = msg_data.get("client_id")

                if task_id and client_id:
                    # 转发结果给客户端
                    await self.frontend.send_multipart(
                        [client_id.encode(), b"", json.dumps(msg_data).encode("utf-8")]
                    )

                    # 清理活跃任务
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]

                    logger.info(f"任务完成: {task_id}")

                # 工作进程重新可用
                if worker_id not in available_workers:
                    available_workers.append(worker_id)

                # 更新统计
                worker_key = worker_id.decode()
                if worker_key in self.worker_stats:
                    self.worker_stats[worker_key]["tasks_completed"] += 1
                    self.worker_stats[worker_key]["last_seen"] = time.time()

            elif msg_type == "heartbeat":
                # 心跳消息
                worker_key = worker_id.decode()
                if worker_key in self.worker_stats:
                    self.worker_stats[worker_key]["last_seen"] = time.time()
                    self.worker_stats[worker_key]["status"] = "alive"

            elif msg_type == "error":
                # 错误消息
                task_id = msg_data.get("task_id")
                client_id = msg_data.get("client_id")

                if task_id and client_id:
                    # 转发错误给客户端
                    error_response = {
                        "type": "error",
                        "task_id": task_id,
                        "error": msg_data.get("error", "未知错误"),
                        "message": msg_data.get("message", "任务执行失败"),
                    }

                    await self.frontend.send_multipart(
                        [
                            client_id.encode(),
                            b"",
                            json.dumps(error_response).encode("utf-8"),
                        ]
                    )

                    # 清理活跃任务
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]

                    logger.error(f"任务失败: {task_id}, 错误: {msg_data.get('error')}")

                # 工作进程重新可用
                if worker_id not in available_workers:
                    available_workers.append(worker_id)

        except Exception as e:
            logger.error(f"处理工作进程消息失败: {e}")

    async def _handle_client_message(self, available_workers: List[bytes]):
        """处理来自客户端的消息"""
        try:
            # 接收客户端消息
            client_id, empty, message = await self.frontend.recv_multipart()

            # 解析消息
            try:
                msg_data = json.loads(message.decode("utf-8"))
            except json.JSONDecodeError:
                logger.error(f"无法解析客户端消息: {message}")
                return

            msg_type = msg_data.get("type")

            if msg_type == "simulation":
                # 仿真任务请求
                if available_workers:
                    # 选择工作进程
                    worker_id = self._select_worker(available_workers)
                    available_workers.remove(worker_id)

                    # 添加客户端ID到任务数据
                    task_data = msg_data.copy()
                    task_data["client_id"] = client_id.decode()
                    task_id = task_data.get("data", {}).get("task_id")

                    # 转发任务给工作进程
                    await self.backend.send_multipart(
                        [worker_id, b"", json.dumps(task_data).encode("utf-8")]
                    )

                    # 记录活跃任务
                    if task_id:
                        self.active_tasks[task_id] = {
                            "client_id": client_id.decode(),
                            "worker_id": worker_id.decode(),
                            "start_time": time.time(),
                            "task_data": task_data,
                        }

                    logger.info(f"任务分发: {task_id} -> 工作进程 {worker_id.decode()}")

                else:
                    # 没有可用工作进程，加入队列
                    task_data = msg_data.copy()
                    task_data["client_id"] = client_id.decode()
                    task_data["queued_at"] = time.time()

                    self.task_queue.append(task_data)

                    # 通知客户端任务已排队
                    queue_response = {
                        "type": "queued",
                        "message": "任务已加入队列，等待工作进程处理",
                        "queue_position": len(self.task_queue),
                    }

                    await self.frontend.send_multipart(
                        [client_id, b"", json.dumps(queue_response).encode("utf-8")]
                    )

                    logger.info(f"任务排队: 队列长度 {len(self.task_queue)}")

            elif msg_type == "status":
                # 状态查询
                status_response = {
                    "type": "status",
                    "available_workers": len(available_workers),
                    "queue_length": len(self.task_queue),
                    "active_tasks": len(self.active_tasks),
                    "worker_stats": self.worker_stats,
                }

                await self.frontend.send_multipart(
                    [client_id, b"", json.dumps(status_response).encode("utf-8")]
                )

        except Exception as e:
            logger.error(f"处理客户端消息失败: {e}")

    def _select_worker(self, available_workers: List[bytes]) -> bytes:
        """选择工作进程（简单的轮询策略）"""
        if not available_workers:
            raise ValueError("没有可用的工作进程")

        # 简单的轮询选择
        return available_workers[0]

    async def _periodic_maintenance(self):
        """定期维护任务"""
        current_time = time.time()

        # 清理超时的工作进程
        timeout_workers = []
        for worker_id, stats in self.worker_stats.items():
            if current_time - stats["last_seen"] > 60:  # 60秒超时
                timeout_workers.append(worker_id)

        for worker_id in timeout_workers:
            del self.worker_stats[worker_id]
            logger.warning(f"工作进程超时: {worker_id}")

        # 清理超时的活跃任务
        timeout_tasks = []
        for task_id, task_info in self.active_tasks.items():
            if current_time - task_info["start_time"] > settings.MAX_SIMULATION_TIME:
                timeout_tasks.append(task_id)

        for task_id in timeout_tasks:
            task_info = self.active_tasks[task_id]
            del self.active_tasks[task_id]

            # 通知客户端任务超时
            timeout_response = {
                "type": "timeout",
                "task_id": task_id,
                "message": "任务执行超时",
            }

            try:
                await self.frontend.send_multipart(
                    [
                        task_info["client_id"].encode(),
                        b"",
                        json.dumps(timeout_response).encode("utf-8"),
                    ]
                )
            except Exception as e:
                logger.error(f"发送超时通知失败: {e}")

            logger.warning(f"任务超时: {task_id}")

    async def _notify_workers_shutdown(self):
        """通知所有工作进程关闭"""
        shutdown_message = {"type": "shutdown", "message": "负载均衡器正在关闭"}

        for worker_id in self.worker_stats.keys():
            try:
                await self.backend.send_multipart(
                    [
                        worker_id.encode(),
                        b"",
                        json.dumps(shutdown_message).encode("utf-8"),
                    ]
                )
            except Exception as e:
                logger.error(f"通知工作进程关闭失败: {e}")

    def _setup_signal_handlers(self):
        """设置信号处理器"""

        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭负载均衡器...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def get_stats(self) -> dict:
        """获取负载均衡器统计信息"""
        return {
            "running": self.running,
            "worker_count": len(self.worker_stats),
            "queue_length": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
            "worker_stats": self.worker_stats,
            "uptime": time.time() - getattr(self, "start_time", time.time()),
        }


async def main():
    """主函数"""
    load_balancer = ZMQLoadBalancer()

    try:
        await load_balancer.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"负载均衡器异常: {e}")
    finally:
        await load_balancer.stop()


if __name__ == "__main__":
    asyncio.run(main())
