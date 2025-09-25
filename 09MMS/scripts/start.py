#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 启动脚本
用于启动整个MMS系统，包括负载均衡器和工作进程

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.utils.logger import get_logger, setup_logging

# 设置日志
setup_logging()
logger = get_logger(__name__)


class MMSLauncher:
    """MMS系统启动器"""

    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.main_process: Optional[subprocess.Popen] = None
        self.worker_processes: List[subprocess.Popen] = []
        self.redis_process: Optional[subprocess.Popen] = None

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，开始关闭系统...")
        self.shutdown()
        sys.exit(0)

    def check_dependencies(self) -> bool:
        """检查系统依赖"""
        logger.info("检查系统依赖...")

        # 检查Python版本
        if sys.version_info < (3, 8):
            logger.error("需要Python 3.8或更高版本")
            return False

        # 检查必需的包
        required_packages = [
            "fastapi",
            "uvicorn",
            "redis",
            "zmq",
            "pandas",
            "numpy",
            "pydantic",
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            logger.error(f"缺少必需的包: {', '.join(missing_packages)}")
            logger.info("请运行: pip install -r requirements.txt")
            return False

        # 检查配置文件
        if not self._validate_config():
            return False

        logger.info("依赖检查通过")
        return True

    def _validate_config(self) -> bool:
        """验证配置"""
        try:
            # 检查必需的配置项
            required_configs = [
                "HOST",
                "PORT",
                "ZMQ_FRONTEND_PORT",
                "ZMQ_BACKEND_PORT",
                "REDIS_HOST",
                "REDIS_PORT",
                "DATABASE_PATH",
            ]

            for config_name in required_configs:
                if not hasattr(Config, config_name):
                    logger.error(f"缺少配置项: {config_name}")
                    return False

            # 检查端口是否可用
            if not self._check_port_available(Config.PORT):
                logger.error(f"端口 {Config.PORT} 已被占用")
                return False

            if not self._check_port_available(Config.ZMQ_FRONTEND_PORT):
                logger.error(f"ZMQ前端端口 {Config.ZMQ_FRONTEND_PORT} 已被占用")
                return False

            if not self._check_port_available(Config.ZMQ_BACKEND_PORT):
                logger.error(f"ZMQ后端端口 {Config.ZMQ_BACKEND_PORT} 已被占用")
                return False

            return True
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False

    def _check_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return True
        except OSError:
            return False

    def start_redis(self) -> bool:
        """启动Redis服务"""
        if Config.REDIS_HOST != "localhost" and Config.REDIS_HOST != "127.0.0.1":
            logger.info("使用外部Redis服务")
            return True

        logger.info("启动Redis服务...")

        try:
            # 检查Redis是否已经运行
            import redis

            r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)
            r.ping()
            logger.info("Redis服务已在运行")
            return True
        except:
            pass

        # 尝试启动Redis
        try:
            redis_cmd = ["redis-server", "--port", str(Config.REDIS_PORT)]
            self.redis_process = subprocess.Popen(
                redis_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # 等待Redis启动
            time.sleep(2)

            # 验证Redis是否启动成功
            import redis

            r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)
            r.ping()

            logger.info("Redis服务启动成功")
            return True
        except Exception as e:
            logger.warning(f"无法启动Redis服务: {e}")
            logger.info("请手动启动Redis服务或使用Docker")
            return False

    def start_main_process(self) -> bool:
        """启动主进程（负载均衡器）"""
        logger.info("启动主进程（负载均衡器）...")

        try:
            main_script = project_root / "main.py"

            cmd = [sys.executable, str(main_script)]

            self.main_process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                env=dict(os.environ, PYTHONPATH=str(project_root)),
            )

            # 等待主进程启动
            time.sleep(3)

            if self.main_process.poll() is None:
                logger.info(f"主进程启动成功，PID: {self.main_process.pid}")
                return True
            else:
                logger.error("主进程启动失败")
                return False

        except Exception as e:
            logger.error(f"启动主进程失败: {e}")
            return False

    def start_worker_processes(self, worker_count: int) -> bool:
        """启动工作进程"""
        logger.info(f"启动 {worker_count} 个工作进程...")

        worker_script = project_root / "worker.py"

        for i in range(worker_count):
            try:
                cmd = [sys.executable, str(worker_script), f"--worker-id={i+1}"]

                process = subprocess.Popen(
                    cmd,
                    cwd=str(project_root),
                    env=dict(os.environ, PYTHONPATH=str(project_root)),
                )

                self.worker_processes.append(process)
                logger.info(f"工作进程 {i+1} 启动成功，PID: {process.pid}")

                # 短暂延迟，避免同时启动过多进程
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"启动工作进程 {i+1} 失败: {e}")
                return False

        logger.info(f"所有 {worker_count} 个工作进程启动完成")
        return True

    def monitor_processes(self):
        """监控进程状态"""
        logger.info("开始监控进程状态...")

        while True:
            try:
                # 检查主进程
                if self.main_process and self.main_process.poll() is not None:
                    logger.error("主进程异常退出")
                    break

                # 检查工作进程
                dead_workers = []
                for i, worker in enumerate(self.worker_processes):
                    if worker.poll() is not None:
                        dead_workers.append(i)
                        logger.warning(f"工作进程 {i+1} 异常退出")

                # 重启异常退出的工作进程
                for i in dead_workers:
                    logger.info(f"重启工作进程 {i+1}...")
                    self._restart_worker(i)

                # 每30秒检查一次
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("接收到中断信号，停止监控")
                break
            except Exception as e:
                logger.error(f"监控进程异常: {e}")
                time.sleep(10)

    def _restart_worker(self, worker_index: int):
        """重启工作进程"""
        try:
            worker_script = project_root / "worker.py"

            cmd = [sys.executable, str(worker_script), f"--worker-id={worker_index+1}"]

            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                env=dict(os.environ, PYTHONPATH=str(project_root)),
            )

            self.worker_processes[worker_index] = process
            logger.info(f"工作进程 {worker_index+1} 重启成功，PID: {process.pid}")

        except Exception as e:
            logger.error(f"重启工作进程 {worker_index+1} 失败: {e}")

    def shutdown(self):
        """关闭所有进程"""
        logger.info("开始关闭MMS系统...")

        # 关闭工作进程
        for i, worker in enumerate(self.worker_processes):
            if worker.poll() is None:
                logger.info(f"关闭工作进程 {i+1}...")
                worker.terminate()
                try:
                    worker.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"强制关闭工作进程 {i+1}")
                    worker.kill()

        # 关闭主进程
        if self.main_process and self.main_process.poll() is None:
            logger.info("关闭主进程...")
            self.main_process.terminate()
            try:
                self.main_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("强制关闭主进程")
                self.main_process.kill()

        # 关闭Redis进程（如果是本地启动的）
        if self.redis_process and self.redis_process.poll() is None:
            logger.info("关闭Redis服务...")
            self.redis_process.terminate()
            try:
                self.redis_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.redis_process.kill()

        logger.info("MMS系统已关闭")

    def start(self, worker_count: int = 4, skip_redis: bool = False):
        """启动MMS系统"""
        logger.info("启动市场微结构仿真引擎 (MMS)...")

        try:
            # 检查依赖
            if not self.check_dependencies():
                logger.error("依赖检查失败，无法启动系统")
                return False

            # 启动Redis（如果需要）
            if not skip_redis:
                if not self.start_redis():
                    logger.error("Redis启动失败，无法继续")
                    return False

            # 启动主进程
            if not self.start_main_process():
                logger.error("主进程启动失败")
                return False

            # 启动工作进程
            if not self.start_worker_processes(worker_count):
                logger.error("工作进程启动失败")
                return False

            logger.info("MMS系统启动完成")
            logger.info(f"API服务地址: http://{Config.HOST}:{Config.PORT}")
            logger.info(f"健康检查: http://{Config.HOST}:{Config.PORT}/health")
            logger.info(f"系统状态: http://{Config.HOST}:{Config.PORT}/status")

            # 开始监控
            self.monitor_processes()

            return True

        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            self.shutdown()
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="市场微结构仿真引擎 (MMS) 启动器")
    parser.add_argument("--workers", type=int, default=4, help="工作进程数量 (默认: 4)")
    parser.add_argument(
        "--skip-redis", action="store_true", help="跳过Redis启动（使用外部Redis服务）"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)",
    )

    args = parser.parse_args()

    # 设置日志级别
    setup_logging(args.log_level)

    # 创建启动器
    launcher = MMSLauncher()

    try:
        # 启动系统
        success = launcher.start(worker_count=args.workers, skip_redis=args.skip_redis)

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("接收到中断信号")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)
    finally:
        launcher.shutdown()


if __name__ == "__main__":
    main()
