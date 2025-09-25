#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - 策略优化模组停止脚本
遵循核心设计理念：优雅关闭、资源清理、状态保存

功能：
1. 优雅停止服务
2. 清理临时文件
3. 保存运行状态
4. 释放系统资源
5. 生成停止报告

使用方法：
    python scripts/stop.py
    python scripts/stop.py --docker
    python scripts/stop.py --force
    python scripts/stop.py --cleanup
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("OptiCore.Shutdown")


class OptiCoreStopper:
    """策略优化模组停止器"""

    def __init__(self):
        self.project_root = project_root
        self.pid_file = self.project_root / "logs" / "opticore.pid"
        self.state_file = self.project_root / "logs" / "opticore.state"
        self.temp_dirs = [
            "logs/temp",
            "data/cache",
            "data/temp",
            ".pytest_cache",
            "__pycache__",
        ]

    def get_running_pid(self) -> Optional[int]:
        """获取运行中的进程ID"""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())

                # 检查进程是否存在
                try:
                    os.kill(pid, 0)  # 发送信号0检查进程存在性
                    return pid
                except OSError:
                    # 进程不存在，删除PID文件
                    self.pid_file.unlink()
                    return None
            return None
        except (ValueError, FileNotFoundError):
            return None

    def save_state(self) -> bool:
        """保存当前状态"""
        logger.info("保存运行状态...")

        try:
            state_data = {
                "shutdown_time": time.time(),
                "shutdown_reason": "manual_stop",
                "environment": os.environ.get("NTN_ENVIRONMENT", "unknown"),
                "project_root": str(self.project_root),
                "python_version": sys.version,
                "platform": sys.platform,
            }

            # 确保logs目录存在
            self.state_file.parent.mkdir(exist_ok=True)

            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)

            logger.info("状态保存完成")
            return True

        except Exception as e:
            logger.error(f"状态保存失败: {e}")
            return False

    def stop_native_service(self, force: bool = False) -> bool:
        """停止原生服务"""
        logger.info("停止策略优化模组 (原生模式)...")

        pid = self.get_running_pid()
        if not pid:
            logger.info("未找到运行中的服务")
            return True

        try:
            logger.info(f"停止进程 {pid}...")

            if force:
                # 强制终止
                os.kill(pid, signal.SIGKILL)
                logger.info("强制终止进程")
            else:
                # 优雅停止
                os.kill(pid, signal.SIGTERM)
                logger.info("发送停止信号")

                # 等待进程结束
                for i in range(30):  # 最多等待30秒
                    try:
                        os.kill(pid, 0)
                        time.sleep(1)
                    except OSError:
                        # 进程已结束
                        break
                else:
                    # 超时，强制终止
                    logger.warning("优雅停止超时，强制终止进程")
                    os.kill(pid, signal.SIGKILL)

            # 删除PID文件
            if self.pid_file.exists():
                self.pid_file.unlink()

            logger.info("服务停止完成")
            return True

        except OSError as e:
            if e.errno == 3:  # No such process
                logger.info("进程已不存在")
                if self.pid_file.exists():
                    self.pid_file.unlink()
                return True
            else:
                logger.error(f"停止进程失败: {e}")
                return False
        except Exception as e:
            logger.error(f"停止服务失败: {e}")
            return False

    def stop_docker_service(self, force: bool = False) -> bool:
        """停止Docker服务"""
        logger.info("停止策略优化模组 (Docker模式)...")

        try:
            if force:
                # 强制停止并删除容器
                subprocess.run(
                    ["docker-compose", "down", "--remove-orphans", "--volumes"],
                    check=True,
                    cwd=self.project_root,
                )
                logger.info("强制停止Docker服务")
            else:
                # 优雅停止
                subprocess.run(
                    ["docker-compose", "stop"], check=True, cwd=self.project_root
                )
                logger.info("优雅停止Docker服务")

                # 等待容器停止
                time.sleep(5)

                # 删除容器
                subprocess.run(
                    ["docker-compose", "down"], check=True, cwd=self.project_root
                )

            logger.info("Docker服务停止完成")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker停止失败: {e}")
            return False

    def cleanup_temp_files(self) -> bool:
        """清理临时文件"""
        logger.info("清理临时文件...")

        try:
            import shutil

            cleaned_count = 0

            for temp_dir in self.temp_dirs:
                temp_path = self.project_root / temp_dir
                if temp_path.exists():
                    if temp_path.is_dir():
                        shutil.rmtree(temp_path)
                        logger.info(f"删除目录: {temp_dir}")
                        cleaned_count += 1
                    else:
                        temp_path.unlink()
                        logger.info(f"删除文件: {temp_dir}")
                        cleaned_count += 1

            # 清理Python缓存文件
            for cache_file in self.project_root.rglob("*.pyc"):
                cache_file.unlink()
                cleaned_count += 1

            for cache_dir in self.project_root.rglob("__pycache__"):
                if cache_dir.is_dir():
                    shutil.rmtree(cache_dir)
                    cleaned_count += 1

            logger.info(f"清理完成，删除了 {cleaned_count} 个文件/目录")
            return True

        except Exception as e:
            logger.error(f"清理失败: {e}")
            return False

    def cleanup_docker_resources(self) -> bool:
        """清理Docker资源"""
        logger.info("清理Docker资源...")

        try:
            # 删除未使用的镜像
            subprocess.run(
                ["docker", "image", "prune", "-f"], check=True, capture_output=True
            )

            # 删除未使用的卷
            subprocess.run(
                ["docker", "volume", "prune", "-f"], check=True, capture_output=True
            )

            # 删除未使用的网络
            subprocess.run(
                ["docker", "network", "prune", "-f"], check=True, capture_output=True
            )

            logger.info("Docker资源清理完成")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker资源清理失败: {e}")
            return False

    def check_running_services(self) -> Dict[str, bool]:
        """检查运行中的服务"""
        logger.info("检查运行中的服务...")

        services = {
            "native_process": False,
            "docker_containers": False,
            "redis": False,
            "zmq_ports": False,
        }

        # 检查原生进程
        if self.get_running_pid():
            services["native_process"] = True

        # 检查Docker容器
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0 and result.stdout.strip():
                services["docker_containers"] = True
        except subprocess.CalledProcessError:
            pass

        # 检查Redis
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, socket_timeout=1)
            r.ping()
            services["redis"] = True
        except (ImportError, redis.ConnectionError, redis.TimeoutError):
            pass

        # 检查ZeroMQ端口
        try:
            import socket

            for port in [5555, 5556, 5557]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                sock.close()
                if result == 0:
                    services["zmq_ports"] = True
                    break
        except (ImportError, socket.error, OSError):
            pass

        return services

    def generate_stop_report(
        self, services_before: Dict[str, bool], services_after: Dict[str, bool]
    ) -> bool:
        """生成停止报告"""
        logger.info("生成停止报告...")

        try:
            report = {
                "timestamp": time.time(),
                "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "services_before": services_before,
                "services_after": services_after,
                "stopped_services": [],
                "remaining_services": [],
            }

            # 分析停止的服务
            for service, was_running in services_before.items():
                is_running = services_after.get(service, False)
                if was_running and not is_running:
                    report["stopped_services"].append(service)
                elif is_running:
                    report["remaining_services"].append(service)

            # 保存报告
            report_file = self.project_root / "logs" / "stop_report.json"
            report_file.parent.mkdir(exist_ok=True)

            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)

            # 显示报告摘要
            logger.info("停止报告摘要:")
            logger.info(f"  停止的服务: {', '.join(report['stopped_services']) or '无'}")
            logger.info(f"  剩余的服务: {', '.join(report['remaining_services']) or '无'}")
            logger.info(f"  报告文件: {report_file}")

            return True

        except Exception as e:
            logger.error(f"生成停止报告失败: {e}")
            return False

    def show_status(self):
        """显示停止状态"""
        logger.info("=" * 60)
        logger.info("NeuroTrade Nexus - 策略优化模组停止完成")
        logger.info("=" * 60)
        logger.info(f"项目根目录: {self.project_root}")
        logger.info(f"停止时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NeuroTrade Nexus 策略优化模组停止脚本")

    parser.add_argument("--docker", action="store_true", help="停止Docker服务")

    parser.add_argument("--force", action="store_true", help="强制停止服务")

    parser.add_argument("--cleanup", action="store_true", help="清理临时文件和缓存")

    parser.add_argument("--cleanup-docker", action="store_true", help="清理Docker资源")

    parser.add_argument("--no-report", action="store_true", help="不生成停止报告")

    parser.add_argument("--check-only", action="store_true", help="仅检查运行状态")

    args = parser.parse_args()

    # 创建停止器
    stopper = OptiCoreStopper()

    try:
        # 检查运行中的服务
        services_before = stopper.check_running_services()

        logger.info("当前运行的服务:")
        for service, is_running in services_before.items():
            status = "运行中" if is_running else "未运行"
            logger.info(f"  {service}: {status}")

        # 仅检查模式
        if args.check_only:
            return

        # 保存状态
        stopper.save_state()

        # 停止服务
        if args.docker:
            success = stopper.stop_docker_service(args.force)
        else:
            success = stopper.stop_native_service(args.force)

        if not success:
            logger.error("服务停止失败")
            sys.exit(1)

        # 清理临时文件
        if args.cleanup:
            stopper.cleanup_temp_files()

        # 清理Docker资源
        if args.cleanup_docker:
            stopper.cleanup_docker_resources()

        # 再次检查服务状态
        services_after = stopper.check_running_services()

        # 生成停止报告
        if not args.no_report:
            stopper.generate_stop_report(services_before, services_after)

        # 显示状态
        stopper.show_status()

        logger.info("策略优化模组停止完成")

    except KeyboardInterrupt:
        logger.info("用户中断停止")
        sys.exit(1)
    except Exception as e:
        logger.error(f"停止过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
