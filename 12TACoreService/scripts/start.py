#!/usr/bin/env python3
"""
TACoreService启动脚本

这个脚本提供了多种启动模式：
- 开发模式：单进程启动，便于调试
- 生产模式：多进程启动，高性能
- 工作进程模式：仅启动工作进程
- 监控模式：仅启动监控API
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import multiprocessing
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tacoreservice.config import get_settings
import logging
from tacoreservice.monitoring.logger import ServiceLogger


class TACoreServiceLauncher:
    """TACoreService启动器"""

    def __init__(self):
        self.settings = get_settings()
        # Setup logging
        service_logger = ServiceLogger()
        service_logger.setup_logging()
        self.logger = logging.getLogger("launcher")
        self.processes: List[subprocess.Popen] = []
        self.running = False

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"接收到信号 {signum}，开始关闭服务...")
        self.stop()

    def start_development(self):
        """开发模式启动"""
        self.logger.info("启动开发模式...")

        # 设置开发环境变量
        os.environ["DEBUG"] = "true"
        os.environ["WORKER_COUNT"] = "2"

        # 启动主服务
        main_script = project_root / "main.py"
        cmd = [sys.executable, str(main_script)]

        self.logger.info(f"执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, cwd=project_root)
        self.processes.append(process)

        self.running = True
        self._wait_for_processes()

    def start_production(self):
        """生产模式启动"""
        self.logger.info("启动生产模式...")

        # 设置生产环境变量
        os.environ["DEBUG"] = "false"

        # 启动负载均衡器
        self._start_load_balancer()

        # 启动工作进程
        worker_count = self.settings.worker_count
        for i in range(worker_count):
            self._start_worker(i)

        # 启动监控API
        self._start_monitoring_api()

        self.running = True
        self._wait_for_processes()

    def start_workers_only(self, count: Optional[int] = None):
        """仅启动工作进程"""
        worker_count = count or self.settings.worker_count
        self.logger.info(f"启动 {worker_count} 个工作进程...")

        for i in range(worker_count):
            self._start_worker(i)

        self.running = True
        self._wait_for_processes()

    def start_monitoring_only(self):
        """仅启动监控API"""
        self.logger.info("启动监控API...")
        self._start_monitoring_api()

        self.running = True
        self._wait_for_processes()

    def _start_load_balancer(self):
        """启动负载均衡器"""
        self.logger.info("启动负载均衡器...")

        cmd = [
            sys.executable,
            "-c",
            "from tacoreservice.core.load_balancer import LoadBalancer; "
            "from tacoreservice.config import get_settings; "
            "lb = LoadBalancer(get_settings()); "
            "lb.start()",
        ]

        process = subprocess.Popen(cmd, cwd=project_root)
        self.processes.append(process)

        # 等待负载均衡器启动
        time.sleep(2)

    def _start_worker(self, worker_id: int):
        """启动工作进程"""
        self.logger.info(f"启动工作进程 {worker_id}...")

        env = os.environ.copy()
        env["WORKER_ID"] = str(worker_id)

        cmd = [
            sys.executable,
            "-c",
            "from tacoreservice.workers.worker import Worker; "
            "import os; "
            "worker_id = f'worker-{os.environ.get(\"WORKER_ID\", 0)}'; "
            "worker = Worker(worker_id); "
            "worker.start()",
        ]

        process = subprocess.Popen(cmd, cwd=project_root, env=env)
        self.processes.append(process)

    def _start_monitoring_api(self):
        """启动监控API"""
        self.logger.info("启动监控API...")

        cmd = [
            sys.executable,
            "-c",
            "import uvicorn; "
            "from tacoreservice.api.monitoring import MonitoringAPI; "
            "from tacoreservice.api.health import HealthAPI; "
            "from tacoreservice.config import get_settings; "
            "from fastapi import FastAPI; "
            "settings = get_settings(); "
            "app = FastAPI(title='TACoreService Monitoring'); "
            "monitoring_api = MonitoringAPI(settings); "
            "health_api = HealthAPI(settings); "
            "app.mount('/api', monitoring_api.app); "
            "app.mount('/health', health_api.app); "
            "uvicorn.run(app, host=settings.http_host, port=settings.http_port)",
        ]

        process = subprocess.Popen(cmd, cwd=project_root)
        self.processes.append(process)

    def _wait_for_processes(self):
        """等待进程结束"""
        try:
            while self.running and self.processes:
                # 检查进程状态
                for process in self.processes[:]:
                    if process.poll() is not None:
                        self.logger.warning(
                            f"进程 {process.pid} 已退出，退出码: {process.returncode}"
                        )
                        self.processes.remove(process)

                if not self.processes:
                    self.logger.info("所有进程已退出")
                    break

                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("接收到中断信号")

        finally:
            self.stop()

    def stop(self):
        """停止所有进程"""
        if not self.running:
            return

        self.running = False
        self.logger.info("正在停止所有进程...")

        # 发送SIGTERM信号
        for process in self.processes:
            try:
                if process.poll() is None:
                    self.logger.info(f"终止进程 {process.pid}")
                    process.terminate()
            except Exception as e:
                self.logger.error(f"终止进程失败: {e}")

        # 等待进程优雅退出
        time.sleep(5)

        # 强制杀死仍在运行的进程
        for process in self.processes:
            try:
                if process.poll() is None:
                    self.logger.warning(f"强制杀死进程 {process.pid}")
                    process.kill()
            except Exception as e:
                self.logger.error(f"杀死进程失败: {e}")

        self.processes.clear()
        self.logger.info("所有进程已停止")

    def status(self):
        """显示服务状态"""
        print("TACoreService 状态:")
        print(f"运行状态: {'运行中' if self.running else '已停止'}")
        print(f"进程数量: {len(self.processes)}")

        for i, process in enumerate(self.processes):
            status = "运行中" if process.poll() is None else f"已退出({process.returncode})"
            print(f"  进程 {i+1} (PID: {process.pid}): {status}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TACoreService 启动脚本")
    parser.add_argument(
        "mode", choices=["dev", "prod", "workers", "monitoring", "status"], help="启动模式"
    )
    parser.add_argument("--workers", type=int, help="工作进程数量（仅在workers模式下有效）")
    parser.add_argument("--config", help="配置文件路径")

    args = parser.parse_args()

    # 设置配置文件
    if args.config:
        os.environ["CONFIG_FILE"] = args.config

    launcher = TACoreServiceLauncher()

    try:
        if args.mode == "dev":
            launcher.start_development()
        elif args.mode == "prod":
            launcher.start_production()
        elif args.mode == "workers":
            launcher.start_workers_only(args.workers)
        elif args.mode == "monitoring":
            launcher.start_monitoring_only()
        elif args.mode == "status":
            launcher.status()

    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
