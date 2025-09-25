#!/usr/bin/env python3
"""
TACoreService停止脚本

这个脚本用于安全地停止TACoreService的所有组件
"""

import os
import sys
import time
import signal
import psutil
import argparse
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tacoreservice.monitoring.logger import ServiceLogger


class TACoreServiceStopper:
    """TACoreService停止器"""

    def __init__(self):
        self.logger = ServiceLogger.get_logger("stopper")

    def stop_all(self, force: bool = False):
        """停止所有TACoreService进程"""
        self.logger.info("开始停止TACoreService...")

        processes = self._find_tacoreservice_processes()

        if not processes:
            self.logger.info("未找到运行中的TACoreService进程")
            return

        self.logger.info(f"找到 {len(processes)} 个TACoreService进程")

        if force:
            self._force_stop_processes(processes)
        else:
            self._graceful_stop_processes(processes)

    def stop_by_pid(self, pid: int, force: bool = False):
        """根据PID停止特定进程"""
        try:
            process = psutil.Process(pid)

            if not self._is_tacoreservice_process(process):
                self.logger.warning(f"PID {pid} 不是TACoreService进程")
                return False

            self.logger.info(f"停止进程 {pid}: {process.name()}")

            if force:
                process.kill()
                self.logger.info(f"强制杀死进程 {pid}")
            else:
                process.terminate()
                self.logger.info(f"发送终止信号到进程 {pid}")

                # 等待进程退出
                try:
                    process.wait(timeout=10)
                    self.logger.info(f"进程 {pid} 已优雅退出")
                except psutil.TimeoutExpired:
                    self.logger.warning(f"进程 {pid} 未在10秒内退出，强制杀死")
                    process.kill()

            return True

        except psutil.NoSuchProcess:
            self.logger.warning(f"进程 {pid} 不存在")
            return False
        except psutil.AccessDenied:
            self.logger.error(f"没有权限停止进程 {pid}")
            return False
        except Exception as e:
            self.logger.error(f"停止进程 {pid} 时发生错误: {e}")
            return False

    def stop_by_port(self, port: int, force: bool = False):
        """根据端口停止进程"""
        processes = self._find_processes_by_port(port)

        if not processes:
            self.logger.info(f"未找到使用端口 {port} 的进程")
            return

        self.logger.info(f"找到 {len(processes)} 个使用端口 {port} 的进程")

        for process in processes:
            self.stop_by_pid(process.pid, force)

    def _find_tacoreservice_processes(self) -> List[psutil.Process]:
        """查找所有TACoreService进程"""
        processes = []

        for process in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if self._is_tacoreservice_process(process):
                    processes.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes

    def _is_tacoreservice_process(self, process: psutil.Process) -> bool:
        """判断是否为TACoreService进程"""
        try:
            cmdline = process.cmdline()

            # 检查命令行参数
            for arg in cmdline:
                if any(
                    keyword in arg.lower()
                    for keyword in [
                        "tacoreservice",
                        "main.py",
                        "load_balancer",
                        "worker.py",
                    ]
                ):
                    return True

            # 检查进程名
            name = process.name().lower()
            if "python" in name:
                # 进一步检查是否为TACoreService相关的Python进程
                cwd = process.cwd()
                if "tacoreservice" in cwd.lower():
                    return True

            return False

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _find_processes_by_port(self, port: int) -> List[psutil.Process]:
        """根据端口查找进程"""
        processes = []

        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.pid:
                try:
                    process = psutil.Process(conn.pid)
                    processes.append(process)
                except psutil.NoSuchProcess:
                    continue

        return processes

    def _graceful_stop_processes(self, processes: List[psutil.Process]):
        """优雅停止进程"""
        # 发送SIGTERM信号
        for process in processes:
            try:
                self.logger.info(f"发送终止信号到进程 {process.pid}: {process.name()}")
                process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.warning(f"无法终止进程 {process.pid}: {e}")

        # 等待进程退出
        self.logger.info("等待进程优雅退出...")

        timeout = 15  # 15秒超时
        start_time = time.time()

        while time.time() - start_time < timeout:
            alive_processes = []

            for process in processes:
                try:
                    if process.is_running():
                        alive_processes.append(process)
                except psutil.NoSuchProcess:
                    continue

            if not alive_processes:
                self.logger.info("所有进程已优雅退出")
                return

            processes = alive_processes
            time.sleep(1)

        # 强制杀死仍在运行的进程
        if processes:
            self.logger.warning(f"仍有 {len(processes)} 个进程在运行，强制杀死")
            self._force_stop_processes(processes)

    def _force_stop_processes(self, processes: List[psutil.Process]):
        """强制停止进程"""
        for process in processes:
            try:
                self.logger.info(f"强制杀死进程 {process.pid}: {process.name()}")
                process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.warning(f"无法杀死进程 {process.pid}: {e}")

        # 等待进程被杀死
        time.sleep(2)

        # 验证进程是否已被杀死
        for process in processes:
            try:
                if process.is_running():
                    self.logger.error(f"进程 {process.pid} 仍在运行")
                else:
                    self.logger.info(f"进程 {process.pid} 已被杀死")
            except psutil.NoSuchProcess:
                self.logger.info(f"进程 {process.pid} 已不存在")

    def list_processes(self):
        """列出所有TACoreService进程"""
        processes = self._find_tacoreservice_processes()

        if not processes:
            print("未找到运行中的TACoreService进程")
            return

        print(f"找到 {len(processes)} 个TACoreService进程:")
        print(f"{'PID':<8} {'名称':<20} {'状态':<10} {'CPU%':<8} {'内存%':<8} {'命令行'}")
        print("-" * 80)

        for process in processes:
            try:
                cpu_percent = process.cpu_percent()
                memory_percent = process.memory_percent()
                status = process.status()
                cmdline = " ".join(process.cmdline()[:3])  # 只显示前3个参数

                print(
                    f"{process.pid:<8} {process.name():<20} {status:<10} {cpu_percent:<8.1f} {memory_percent:<8.1f} {cmdline}"
                )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print(
                    f"{process.pid:<8} {'N/A':<20} {'N/A':<10} {'N/A':<8} {'N/A':<8} {'N/A'}"
                )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TACoreService 停止脚本")
    parser.add_argument("action", choices=["stop", "kill", "list", "port"], help="操作类型")
    parser.add_argument("--pid", type=int, help="指定要停止的进程PID")
    parser.add_argument("--port", type=int, help="指定要停止的端口")
    parser.add_argument("--force", action="store_true", help="强制停止（使用SIGKILL）")

    args = parser.parse_args()

    stopper = TACoreServiceStopper()

    try:
        if args.action == "stop":
            if args.pid:
                stopper.stop_by_pid(args.pid, args.force)
            else:
                stopper.stop_all(args.force)

        elif args.action == "kill":
            if args.pid:
                stopper.stop_by_pid(args.pid, force=True)
            else:
                stopper.stop_all(force=True)

        elif args.action == "list":
            stopper.list_processes()

        elif args.action == "port":
            if not args.port:
                print("错误: --port 参数是必需的")
                sys.exit(1)
            stopper.stop_by_port(args.port, args.force)

    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
