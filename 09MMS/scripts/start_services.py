#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 服务启动脚本
用于启动和管理各个服务组件

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
from typing import List, Dict, Optional
import psutil
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceManager:
    """服务管理器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(project_root / "config" / "config.yaml")
        self.processes: Dict[str, subprocess.Popen] = {}
        self.config = self._load_config()

        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "server": {"host": "0.0.0.0", "port": 8000, "workers": 4},
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "zmq": {"frontend_port": 5555, "backend_port": 5556, "worker_count": 4},
        }

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在关闭服务...")
        self.stop_all_services()
        sys.exit(0)

    def check_dependencies(self) -> bool:
        """检查依赖服务"""
        logger.info("检查依赖服务...")

        # 检查Redis
        redis_running = self._check_redis()
        if not redis_running:
            logger.warning("Redis服务未运行，某些功能可能不可用")

        # 检查端口占用
        ports_to_check = [
            self.config["server"]["port"],
            self.config["zmq"]["frontend_port"],
            self.config["zmq"]["backend_port"],
        ]

        for port in ports_to_check:
            if self._is_port_in_use(port):
                logger.error(f"端口 {port} 已被占用")
                return False

        logger.info("依赖检查完成")
        return True

    def _check_redis(self) -> bool:
        """检查Redis服务"""
        try:
            import redis

            r = redis.Redis(
                host=self.config["redis"]["host"],
                port=self.config["redis"]["port"],
                db=self.config["redis"]["db"],
                socket_timeout=5,
            )
            r.ping()
            logger.info("Redis服务正常")
            return True
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}")
            return False

    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False

    def start_api_server(self) -> bool:
        """启动API服务器"""
        logger.info("启动API服务器...")

        try:
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "src.api.main:app",
                "--host",
                self.config["server"]["host"],
                "--port",
                str(self.config["server"]["port"]),
                "--workers",
                str(self.config["server"]["workers"]),
            ]

            process = subprocess.Popen(
                cmd, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            self.processes["api_server"] = process
            logger.info(f"API服务器已启动 (PID: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"启动API服务器失败: {e}")
            return False

    def start_load_balancer(self) -> bool:
        """启动负载均衡器"""
        logger.info("启动负载均衡器...")

        try:
            cmd = [sys.executable, "-m", "src.core.load_balancer"]

            process = subprocess.Popen(
                cmd, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            self.processes["load_balancer"] = process
            logger.info(f"负载均衡器已启动 (PID: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"启动负载均衡器失败: {e}")
            return False

    def start_workers(self, count: Optional[int] = None) -> bool:
        """启动工作进程"""
        worker_count = count or self.config["zmq"]["worker_count"]
        logger.info(f"启动 {worker_count} 个工作进程...")

        success_count = 0

        for i in range(worker_count):
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "src.core.worker",
                    "--worker-id",
                    f"worker_{i+1}",
                ]

                process = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.processes[f"worker_{i+1}"] = process
                logger.info(f"工作进程 worker_{i+1} 已启动 (PID: {process.pid})")
                success_count += 1

            except Exception as e:
                logger.error(f"启动工作进程 worker_{i+1} 失败: {e}")

        logger.info(f"成功启动 {success_count}/{worker_count} 个工作进程")
        return success_count > 0

    def start_all_services(self) -> bool:
        """启动所有服务"""
        logger.info("启动所有服务...")

        if not self.check_dependencies():
            logger.error("依赖检查失败，无法启动服务")
            return False

        # 启动负载均衡器
        if not self.start_load_balancer():
            logger.error("负载均衡器启动失败")
            return False

        # 等待负载均衡器启动
        time.sleep(2)

        # 启动工作进程
        if not self.start_workers():
            logger.error("工作进程启动失败")
            return False

        # 等待工作进程启动
        time.sleep(2)

        # 启动API服务器
        if not self.start_api_server():
            logger.error("API服务器启动失败")
            return False

        logger.info("所有服务启动完成")
        return True

    def stop_service(self, service_name: str) -> bool:
        """停止指定服务"""
        if service_name not in self.processes:
            logger.warning(f"服务 {service_name} 未运行")
            return False

        process = self.processes[service_name]

        try:
            # 优雅关闭
            process.terminate()

            # 等待进程结束
            try:
                process.wait(timeout=10)
                logger.info(f"服务 {service_name} 已停止")
            except subprocess.TimeoutExpired:
                # 强制关闭
                process.kill()
                process.wait()
                logger.warning(f"服务 {service_name} 被强制关闭")

            del self.processes[service_name]
            return True

        except Exception as e:
            logger.error(f"停止服务 {service_name} 失败: {e}")
            return False

    def stop_all_services(self) -> bool:
        """停止所有服务"""
        logger.info("停止所有服务...")

        success_count = 0
        total_count = len(self.processes)

        # 复制进程列表，避免在迭代时修改
        services = list(self.processes.keys())

        for service_name in services:
            if self.stop_service(service_name):
                success_count += 1

        logger.info(f"成功停止 {success_count}/{total_count} 个服务")
        return success_count == total_count

    def restart_service(self, service_name: str) -> bool:
        """重启指定服务"""
        logger.info(f"重启服务 {service_name}...")

        # 停止服务
        self.stop_service(service_name)

        # 等待一段时间
        time.sleep(1)

        # 重新启动服务
        if service_name == "api_server":
            return self.start_api_server()
        elif service_name == "load_balancer":
            return self.start_load_balancer()
        elif service_name.startswith("worker_"):
            # 重启单个工作进程
            return self.start_workers(count=1)
        else:
            logger.error(f"未知服务: {service_name}")
            return False

    def get_service_status(self) -> Dict[str, dict]:
        """获取服务状态"""
        status = {}

        for service_name, process in self.processes.items():
            try:
                # 检查进程是否还在运行
                if process.poll() is None:
                    # 进程仍在运行
                    ps_process = psutil.Process(process.pid)
                    status[service_name] = {
                        "status": "running",
                        "pid": process.pid,
                        "cpu_percent": ps_process.cpu_percent(),
                        "memory_percent": ps_process.memory_percent(),
                        "create_time": ps_process.create_time(),
                    }
                else:
                    # 进程已结束
                    status[service_name] = {
                        "status": "stopped",
                        "exit_code": process.returncode,
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                status[service_name] = {"status": "unknown", "pid": process.pid}

        return status

    def monitor_services(self, interval: int = 30):
        """监控服务状态"""
        logger.info(f"开始监控服务，检查间隔: {interval}秒")

        try:
            while True:
                status = self.get_service_status()

                # 检查是否有服务异常退出
                for service_name, info in status.items():
                    if info["status"] == "stopped":
                        logger.warning(
                            f"服务 {service_name} 异常退出，退出码: {info.get('exit_code')}"
                        )
                        # 可以在这里添加自动重启逻辑

                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("监控被中断")
        except Exception as e:
            logger.error(f"监控过程中发生错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="市场微结构仿真引擎服务管理器")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status", "monitor"],
        help="要执行的操作",
    )
    parser.add_argument("--service", help="指定服务名称（可选）")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--workers", type=int, help="工作进程数量")
    parser.add_argument("--monitor-interval", type=int, default=30, help="监控检查间隔（秒）")

    args = parser.parse_args()

    # 创建服务管理器
    manager = ServiceManager(config_path=args.config)

    try:
        if args.action == "start":
            if args.service:
                if args.service == "api_server":
                    success = manager.start_api_server()
                elif args.service == "load_balancer":
                    success = manager.start_load_balancer()
                elif args.service == "workers":
                    success = manager.start_workers(count=args.workers)
                else:
                    logger.error(f"未知服务: {args.service}")
                    return 1
            else:
                success = manager.start_all_services()

            if success:
                logger.info("服务启动成功")
                return 0
            else:
                logger.error("服务启动失败")
                return 1

        elif args.action == "stop":
            if args.service:
                success = manager.stop_service(args.service)
            else:
                success = manager.stop_all_services()

            if success:
                logger.info("服务停止成功")
                return 0
            else:
                logger.error("服务停止失败")
                return 1

        elif args.action == "restart":
            if args.service:
                success = manager.restart_service(args.service)
            else:
                success = manager.stop_all_services()
                if success:
                    time.sleep(2)
                    success = manager.start_all_services()

            if success:
                logger.info("服务重启成功")
                return 0
            else:
                logger.error("服务重启失败")
                return 1

        elif args.action == "status":
            status = manager.get_service_status()

            print("\n服务状态:")
            print("-" * 60)

            for service_name, info in status.items():
                print(f"服务: {service_name}")
                print(f"  状态: {info['status']}")

                if info["status"] == "running":
                    print(f"  PID: {info['pid']}")
                    print(f"  CPU: {info['cpu_percent']:.1f}%")
                    print(f"  内存: {info['memory_percent']:.1f}%")
                elif info["status"] == "stopped":
                    print(f"  退出码: {info.get('exit_code', 'N/A')}")

                print()

            return 0

        elif args.action == "monitor":
            manager.monitor_services(interval=args.monitor_interval)
            return 0

    except KeyboardInterrupt:
        logger.info("操作被中断")
        manager.stop_all_services()
        return 0
    except Exception as e:
        logger.error(f"操作失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
