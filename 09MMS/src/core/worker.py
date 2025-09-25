#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 工作进程
实现仿真任务的工作进程和任务分发逻辑

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import zmq
import zmq.asyncio

from .config import get_settings
from .database import DatabaseManager
from .simulation_engine import SimulationEngine
from ..models.simulation import SimulationRequest, TaskStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SimulationWorker:
    """仿真工作进程"""

    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.context = zmq.asyncio.Context()
        self.socket = None
        self.running = False
        self.db_manager = None
        self.simulation_engine = None
        self.start_time = time.time()
        self.tasks_completed = 0
        self.current_task = None

    async def start(self):
        """启动工作进程"""
        try:
            logger.info(f"正在启动工作进程: {self.worker_id}")

            # 初始化数据库管理器
            self.db_manager = DatabaseManager()
            await self.db_manager.init_database()

            # 初始化仿真引擎
            self.simulation_engine = SimulationEngine(self.db_manager)

            # 创建ZeroMQ套接字
            self.socket = self.context.socket(zmq.DEALER)
            self.socket.connect(f"tcp://localhost:{settings.BACKEND_PORT}")

            # 设置套接字选项
            self.socket.setsockopt(zmq.IDENTITY, self.worker_id.encode())
            self.socket.setsockopt(zmq.LINGER, 0)

            self.running = True

            # 设置信号处理
            self._setup_signal_handlers()

            # 发送就绪消息
            await self._send_ready_message()

            # 启动主循环
            await self._run_main_loop()

        except Exception as e:
            logger.error(f"启动工作进程失败: {e}")
            raise

    async def stop(self):
        """停止工作进程"""
        logger.info(f"正在停止工作进程: {self.worker_id}")

        self.running = False

        # 如果有正在执行的任务，尝试取消
        if self.current_task:
            logger.info(f"取消当前任务: {self.current_task}")
            # 这里可以添加任务取消逻辑

        # 关闭数据库连接
        if self.db_manager:
            await self.db_manager.close()

        # 关闭套接字
        if self.socket:
            self.socket.close()

        # 终止上下文
        self.context.term()

        logger.info(f"工作进程已停止: {self.worker_id}")

    async def _run_main_loop(self):
        """运行主循环"""
        logger.info(f"工作进程主循环已启动: {self.worker_id}")

        heartbeat_interval = 30  # 30秒心跳间隔
        last_heartbeat = time.time()

        while self.running:
            try:
                # 检查是否需要发送心跳
                current_time = time.time()
                if current_time - last_heartbeat > heartbeat_interval:
                    await self._send_heartbeat()
                    last_heartbeat = current_time

                # 等待任务消息
                try:
                    message = await asyncio.wait_for(
                        self.socket.recv_multipart(), timeout=5.0  # 5秒超时
                    )

                    # 处理消息
                    await self._handle_message(message)

                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue

            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    logger.info(f"ZMQ上下文已终止，退出主循环: {self.worker_id}")
                    break
                else:
                    logger.error(f"ZMQ错误: {e}")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message):
        """处理接收到的消息"""
        try:
            # 解析消息
            if len(message) < 2:
                logger.error("消息格式错误")
                return

            # 获取消息内容
            msg_content = message[-1].decode("utf-8")

            try:
                msg_data = json.loads(msg_content)
            except json.JSONDecodeError:
                logger.error(f"无法解析消息: {msg_content}")
                return

            msg_type = msg_data.get("type")

            if msg_type == "simulation":
                # 处理仿真任务
                await self._process_simulation_task(msg_data)

            elif msg_type == "shutdown":
                # 关闭命令
                logger.info(f"收到关闭命令: {self.worker_id}")
                self.running = False

            elif msg_type == "ping":
                # 响应ping
                await self._send_pong()

            else:
                logger.warning(f"未知消息类型: {msg_type}")

        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    async def _process_simulation_task(self, task_data: dict):
        """处理仿真任务"""
        task_info = task_data.get("data", {})
        task_id = task_info.get("task_id")
        client_id = task_data.get("client_id")

        if not task_id or not client_id:
            logger.error("任务数据缺少必要字段")
            return

        self.current_task = task_id
        start_time = time.time()

        try:
            logger.info(f"开始处理仿真任务: {task_id}")

            # 构建仿真请求
            simulation_request = self._build_simulation_request(task_info)

            # 执行仿真
            result = await self.simulation_engine.execute_simulation(simulation_request)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 发送结果
            await self._send_task_result(task_id, client_id, result, execution_time)

            # 更新统计
            self.tasks_completed += 1

            logger.info(f"仿真任务完成: {task_id}, 耗时: {execution_time:.2f}秒")

        except Exception as e:
            logger.error(f"仿真任务失败: {task_id}, 错误: {e}")

            # 发送错误结果
            await self._send_task_error(task_id, client_id, str(e))

        finally:
            self.current_task = None

    def _build_simulation_request(self, task_info: dict) -> SimulationRequest:
        """构建仿真请求对象"""
        try:
            # 从任务信息构建SimulationRequest
            return SimulationRequest(
                task_id=task_info.get("task_id"),
                scenario_type=task_info.get("scenario", "MARKET_MAKING"),
                parameters=task_info.get("strategy_params", {}),
                symbol=task_info.get("symbol", "BTCUSDT"),
                start_time=task_info.get("start_time"),
                end_time=task_info.get("end_time"),
            )
        except Exception as e:
            logger.error(f"构建仿真请求失败: {e}")
            raise ValueError(f"无效的任务参数: {e}")

    async def _send_ready_message(self):
        """发送就绪消息"""
        ready_msg = {
            "type": "ready",
            "worker_id": self.worker_id,
            "tasks_completed": self.tasks_completed,
            "uptime": time.time() - self.start_time,
        }

        await self.socket.send_multipart([json.dumps(ready_msg).encode("utf-8")])

        logger.info(f"发送就绪消息: {self.worker_id}")

    async def _send_heartbeat(self):
        """发送心跳消息"""
        heartbeat_msg = {
            "type": "heartbeat",
            "worker_id": self.worker_id,
            "timestamp": time.time(),
            "tasks_completed": self.tasks_completed,
            "uptime": time.time() - self.start_time,
            "current_task": self.current_task,
        }

        try:
            await self.socket.send_multipart(
                [json.dumps(heartbeat_msg).encode("utf-8")]
            )
        except Exception as e:
            logger.error(f"发送心跳失败: {e}")

    async def _send_task_result(
        self, task_id: str, client_id: str, result, execution_time: float
    ):
        """发送任务结果"""
        result_msg = {
            "type": "result",
            "task_id": task_id,
            "client_id": client_id,
            "worker_id": self.worker_id,
            "status": "completed",
            "data": result.dict() if hasattr(result, "dict") else result,
            "execution_time": execution_time,
            "completed_at": datetime.now().isoformat(),
        }

        await self.socket.send_multipart([json.dumps(result_msg).encode("utf-8")])

    async def _send_task_error(self, task_id: str, client_id: str, error: str):
        """发送任务错误"""
        error_msg = {
            "type": "error",
            "task_id": task_id,
            "client_id": client_id,
            "worker_id": self.worker_id,
            "status": "failed",
            "error": error,
            "message": "任务执行失败",
            "failed_at": datetime.now().isoformat(),
        }

        await self.socket.send_multipart([json.dumps(error_msg).encode("utf-8")])

    async def _send_pong(self):
        """发送pong响应"""
        pong_msg = {
            "type": "pong",
            "worker_id": self.worker_id,
            "timestamp": time.time(),
        }

        await self.socket.send_multipart([json.dumps(pong_msg).encode("utf-8")])

    def _setup_signal_handlers(self):
        """设置信号处理器"""

        def signal_handler(signum, frame):
            logger.info(f"工作进程 {self.worker_id} 收到信号 {signum}，准备关闭...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def get_stats(self) -> dict:
        """获取工作进程统计信息"""
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "uptime": time.time() - self.start_time,
            "tasks_completed": self.tasks_completed,
            "current_task": self.current_task,
            "pid": os.getpid(),
        }


class WorkerManager:
    """工作进程管理器"""

    def __init__(self, worker_count: Optional[int] = None):
        self.worker_count = worker_count or settings.WORKER_COUNT
        self.workers: Dict[str, SimulationWorker] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        self.running = False

    async def start_all_workers(self):
        """启动所有工作进程"""
        logger.info(f"正在启动 {self.worker_count} 个工作进程...")

        self.running = True

        for i in range(self.worker_count):
            worker_id = f"worker_{i+1}_{uuid4().hex[:8]}"
            worker = SimulationWorker(worker_id)

            # 启动工作进程
            task = asyncio.create_task(worker.start())

            self.workers[worker_id] = worker
            self.worker_tasks[worker_id] = task

            logger.info(f"工作进程已启动: {worker_id}")

            # 稍微延迟以避免同时连接
            await asyncio.sleep(0.1)

        logger.info(f"所有 {self.worker_count} 个工作进程已启动")

    async def stop_all_workers(self):
        """停止所有工作进程"""
        logger.info("正在停止所有工作进程...")

        self.running = False

        # 停止所有工作进程
        stop_tasks = []
        for worker in self.workers.values():
            stop_tasks.append(asyncio.create_task(worker.stop()))

        # 等待所有工作进程停止
        await asyncio.gather(*stop_tasks, return_exceptions=True)

        # 取消所有任务
        for task in self.worker_tasks.values():
            if not task.done():
                task.cancel()

        # 等待任务完成
        await asyncio.gather(*self.worker_tasks.values(), return_exceptions=True)

        self.workers.clear()
        self.worker_tasks.clear()

        logger.info("所有工作进程已停止")

    async def restart_worker(self, worker_id: str):
        """重启指定的工作进程"""
        if worker_id not in self.workers:
            logger.error(f"工作进程不存在: {worker_id}")
            return

        logger.info(f"正在重启工作进程: {worker_id}")

        # 停止旧的工作进程
        old_worker = self.workers[worker_id]
        old_task = self.worker_tasks[worker_id]

        await old_worker.stop()
        if not old_task.done():
            old_task.cancel()

        # 启动新的工作进程
        new_worker = SimulationWorker(worker_id)
        new_task = asyncio.create_task(new_worker.start())

        self.workers[worker_id] = new_worker
        self.worker_tasks[worker_id] = new_task

        logger.info(f"工作进程重启完成: {worker_id}")

    def get_all_stats(self) -> dict:
        """获取所有工作进程的统计信息"""
        stats = {
            "manager_running": self.running,
            "worker_count": len(self.workers),
            "workers": {},
        }

        for worker_id, worker in self.workers.items():
            stats["workers"][worker_id] = worker.get_stats()

        return stats


async def main():
    """主函数 - 单个工作进程模式"""
    worker = SimulationWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"工作进程异常: {e}")
        traceback.print_exc()
    finally:
        await worker.stop()


if __name__ == "__main__":
    # 检查是否指定了工作进程ID
    worker_id = None
    if len(sys.argv) > 1:
        worker_id = sys.argv[1]

    if worker_id:
        # 单个工作进程模式
        worker = SimulationWorker(worker_id)
        asyncio.run(worker.start())
    else:
        # 默认单个工作进程模式
        asyncio.run(main())
