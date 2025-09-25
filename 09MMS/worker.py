#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 工作进程
负责执行具体的仿真任务

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import json
import signal
import sys
import time
import uuid
from typing import Dict, Any, Optional

import zmq
import zmq.asyncio
from loguru import logger

from src.core.config import settings
from src.core.database import get_database
from src.services.simulation_engine import SimulationEngine
from src.services.data_calibrator import DataCalibrator
from src.services.result_analyzer import ResultAnalyzer
from src.models.simulation import SimulationTask, SimulationResult
from src.utils.logger import setup_logger
from src.utils.exceptions import SimulationError, ValidationError


class SimulationWorker:
    """仿真工作进程类"""

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.context = zmq.asyncio.Context()
        self.socket: Optional[zmq.asyncio.Socket] = None
        self.running = False
        self.shutdown_event = asyncio.Event()

        # 初始化服务组件
        self.simulation_engine = SimulationEngine()
        self.data_calibrator = DataCalibrator()
        self.result_analyzer = ResultAnalyzer()

        logger.info(f"工作进程 {self.worker_id} 初始化完成")

    async def connect(self):
        """连接到负载均衡器"""
        try:
            self.socket = self.context.socket(zmq.DEALER)
            self.socket.identity = self.worker_id.encode("utf-8")

            backend_address = f"tcp://localhost:{settings.BACKEND_PORT}"
            self.socket.connect(backend_address)

            logger.info(f"工作进程 {self.worker_id} 已连接到 {backend_address}")

            # 发送就绪信号
            await self.socket.send_multipart([b"READY"])

        except Exception as e:
            logger.error(f"连接失败: {e}")
            raise

    async def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
        self.context.term()
        logger.info(f"工作进程 {self.worker_id} 已断开连接")

    async def process_simulation_request(
        self, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理仿真请求"""
        start_time = time.time()
        task_id = f"sim_{int(start_time)}_{uuid.uuid4().hex[:8]}"

        try:
            # 1. 验证请求参数
            logger.info(f"开始处理仿真任务 {task_id}")

            # 创建仿真任务对象
            task = SimulationTask(
                task_id=task_id,
                symbol=request_data["symbol"],
                period=request_data["period"],
                scenario=request_data["scenario"],
                strategy_params=request_data["strategy_params"],
                start_time=request_data.get("start_time"),
                end_time=request_data.get("end_time"),
            )

            # 2. 保存任务到数据库
            db = await get_database()
            await db.save_simulation_task(task)

            # 3. 数据校准
            logger.info(f"任务 {task_id}: 开始数据校准")
            calibration_params = await self.data_calibrator.calibrate(
                symbol=task.symbol, scenario=task.scenario, period=task.period
            )

            # 4. 执行仿真
            logger.info(f"任务 {task_id}: 开始执行仿真")
            simulation_data = await self.simulation_engine.run_simulation(
                task=task, calibration_params=calibration_params
            )

            # 5. 结果分析
            logger.info(f"任务 {task_id}: 开始结果分析")
            analysis_result = await self.result_analyzer.analyze(
                simulation_data=simulation_data, task=task
            )

            # 6. 生成报告
            report_url = await self.result_analyzer.generate_report(
                task_id=task_id, analysis_result=analysis_result
            )

            # 7. 保存结果
            execution_time = time.time() - start_time
            result = SimulationResult(
                result_id=f"result_{task_id}",
                task_id=task_id,
                slippage=analysis_result["slippage"],
                fill_probability=analysis_result["fill_probability"],
                price_impact=analysis_result["price_impact"],
                total_return=analysis_result["total_return"],
                max_drawdown=analysis_result["max_drawdown"],
                sharpe_ratio=analysis_result["sharpe_ratio"],
                report_path=report_url,
                execution_time=execution_time,
            )

            await db.save_simulation_result(result)

            # 8. 更新任务状态
            await db.update_task_status(task_id, "completed")

            logger.info(f"任务 {task_id} 完成，耗时 {execution_time:.2f}秒")

            # 返回结果
            return {
                "simulation_id": task_id,
                "slippage": result.slippage,
                "fill_probability": result.fill_probability,
                "price_impact": result.price_impact,
                "total_return": result.total_return,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "report_url": f"http://mms:50051/reports/{task_id}",
                "execution_time": execution_time,
            }

        except ValidationError as e:
            logger.error(f"任务 {task_id} 参数验证失败: {e}")
            await self._update_task_failed(task_id, str(e))
            raise

        except SimulationError as e:
            logger.error(f"任务 {task_id} 仿真执行失败: {e}")
            await self._update_task_failed(task_id, str(e))
            raise

        except Exception as e:
            logger.error(f"任务 {task_id} 处理异常: {e}")
            await self._update_task_failed(task_id, str(e))
            raise

    async def _update_task_failed(self, task_id: str, error_message: str):
        """更新任务为失败状态"""
        try:
            db = await get_database()
            await db.update_task_status(task_id, "failed", error_message)
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")

    async def run(self):
        """运行工作进程"""
        self.running = True

        try:
            await self.connect()

            while self.running and not self.shutdown_event.is_set():
                try:
                    # 等待消息，设置超时以便检查关闭信号
                    if await self.socket.poll(timeout=1000):  # 1秒超时
                        # 接收消息
                        message = await self.socket.recv_multipart()

                        if len(message) >= 2:
                            client_id = message[0]
                            request_data = json.loads(message[1].decode("utf-8"))

                            logger.info(f"工作进程 {self.worker_id} 接收到请求")

                            try:
                                # 处理请求
                                response = await self.process_simulation_request(
                                    request_data
                                )

                                # 发送响应
                                await self.socket.send_multipart(
                                    [
                                        client_id,
                                        json.dumps(
                                            {"status": "success", "data": response}
                                        ).encode("utf-8"),
                                    ]
                                )

                            except Exception as e:
                                # 发送错误响应
                                await self.socket.send_multipart(
                                    [
                                        client_id,
                                        json.dumps(
                                            {"status": "error", "message": str(e)}
                                        ).encode("utf-8"),
                                    ]
                                )

                        # 发送就绪信号
                        await self.socket.send_multipart([b"READY"])

                except zmq.Again:
                    # 超时，继续循环
                    continue
                except Exception as e:
                    logger.error(f"工作进程处理消息时出错: {e}")
                    break

        except Exception as e:
            logger.error(f"工作进程运行错误: {e}")
        finally:
            await self.disconnect()

    def stop(self):
        """停止工作进程"""
        logger.info(f"工作进程 {self.worker_id} 正在停止...")
        self.running = False
        self.shutdown_event.set()


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {signum}，工作进程准备退出")
    sys.exit(0)


async def main():
    """主函数"""
    # 设置日志
    setup_logger()

    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建工作进程
    worker = SimulationWorker()

    logger.info(f"启动仿真工作进程 {worker.worker_id}")

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("接收到键盘中断")
    except Exception as e:
        logger.error(f"工作进程异常: {e}")
    finally:
        worker.stop()
        logger.info("工作进程已退出")


if __name__ == "__main__":
    asyncio.run(main())