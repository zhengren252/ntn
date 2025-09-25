#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - 策略优化模组启动脚本
遵循核心设计理念：微服务架构、三环境隔离、Docker容器化部署

功能：
1. 环境检查和初始化
2. 依赖验证
3. 服务启动
4. 健康检查
5. 日志管理

使用方法：
    python scripts/start.py --env development
    python scripts/start.py --env staging --docker
    python scripts/start.py --env production --docker --monitoring
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("OptiCore.Startup")


class OptiCoreStarter:
    """策略优化模组启动器"""

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.project_root = project_root
        self.config = get_config(environment)
        self.required_dirs = [
            "data",
            "logs",
            "config",
            "tests",
            "optimizer",
            "optimizer/strategies",
            "optimizer/backtester",
            "optimizer/optimization",
            "optimizer/decision",
        ]
        self.required_files = [
            "requirements.txt",
            "config/config.py",
            "optimizer/main.py",
            "Dockerfile",
            "docker-compose.yml",
        ]

    def check_environment(self) -> bool:
        """检查运行环境"""
        logger.info(f"检查 {self.environment} 环境...")

        # 检查Python版本
        if sys.version_info < (3, 11):
            logger.error("需要Python 3.11或更高版本")
            return False

        # 检查必需目录
        for dir_path in self.required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                logger.warning(f"创建缺失目录: {dir_path}")
                full_path.mkdir(parents=True, exist_ok=True)

        # 检查必需文件
        for file_path in self.required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                logger.error(f"缺失必需文件: {file_path}")
                return False

        # 设置环境变量
        os.environ["NTN_ENVIRONMENT"] = self.environment
        os.environ["PYTHONPATH"] = str(self.project_root)

        logger.info("环境检查完成")
        return True

    def check_dependencies(self) -> bool:
        """检查依赖包"""
        logger.info("检查Python依赖...")

        try:
            # 检查核心依赖
            import fastapi
            import numpy
            import pandas
            import redis
            import uvicorn
            import zmq

            logger.info("核心依赖检查通过")

            # 检查可选依赖
            try:
                import vectorbt

                logger.info("VectorBT可用")
            except ImportError:
                logger.warning("VectorBT未安装，回测功能可能受限")

            try:
                import groq

                logger.info("Groq SDK可用")
            except ImportError:
                logger.warning("Groq SDK未安装，LPU加速不可用")

            return True

        except ImportError as e:
            logger.error(f"依赖检查失败: {e}")
            logger.info("请运行: pip install -r requirements.txt")
            return False

    def check_external_services(self) -> Dict[str, bool]:
        """检查外部服务"""
        logger.info("检查外部服务...")

        services_status = {"redis": False, "zmq_ports": False}

        # 检查Redis
        try:
            import redis

            r = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                db=self.config.redis.db,
                socket_timeout=5,
            )
            r.ping()
            services_status["redis"] = True
            logger.info("Redis连接正常")
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}")

        # 检查ZeroMQ端口
        try:
            import socket

            ports_to_check = [
                self.config.zeromq.publisher_port,
                self.config.zeromq.subscriber_port,
                self.config.zeromq.reply_port,
            ]

            for port in ports_to_check:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                sock.close()

                if result != 0:  # 端口未被占用
                    services_status["zmq_ports"] = True
                    break

            if services_status["zmq_ports"]:
                logger.info("ZeroMQ端口可用")
            else:
                logger.warning("ZeroMQ端口可能被占用")

        except Exception as e:
            logger.warning(f"ZeroMQ端口检查失败: {e}")

        return services_status

    def install_dependencies(self) -> bool:
        """安装依赖包"""
        logger.info("安装Python依赖...")

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=True,
                cwd=self.project_root,
            )
            logger.info("依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"依赖安装失败: {e}")
            return False

    def start_native(self) -> bool:
        """原生启动服务"""
        logger.info("启动策略优化模组 (原生模式)...")

        try:
            # 启动主服务
            cmd = [
                sys.executable,
                "-m",
                "optimizer.main",
                "--environment",
                self.environment,
            ]

            logger.info(f"执行命令: {' '.join(cmd)}")

            # 在后台启动服务
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # 等待服务启动
            time.sleep(5)

            # 检查进程状态
            if process.poll() is None:
                logger.info(f"服务启动成功 (PID: {process.pid})")

                # 保存进程ID
                pid_file = self.project_root / "logs" / "opticore.pid"
                with open(pid_file, "w") as f:
                    f.write(str(process.pid))

                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"服务启动失败: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False

    def start_docker(self, with_monitoring: bool = False) -> bool:
        """Docker启动服务"""
        logger.info("启动策略优化模组 (Docker模式)...")

        try:
            # 构建Docker镜像
            logger.info("构建Docker镜像...")
            subprocess.run(
                ["docker", "build", "-t", f"opticore:{self.environment}", "."],
                check=True,
                cwd=self.project_root,
            )

            # 准备Docker Compose命令
            compose_cmd = ["docker-compose"]

            # 选择环境配置
            if self.environment == "development":
                compose_cmd.extend(["--profile", "dev"])
            elif self.environment == "staging":
                compose_cmd.extend(["--profile", "staging"])
            elif self.environment == "production":
                compose_cmd.extend(["--profile", "prod"])

            # 添加监控服务
            if with_monitoring:
                compose_cmd.extend(["--profile", "monitoring"])

            compose_cmd.extend(["up", "-d"])

            logger.info(f"执行命令: {' '.join(compose_cmd)}")

            # 启动服务
            subprocess.run(compose_cmd, check=True, cwd=self.project_root)

            logger.info("Docker服务启动成功")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker启动失败: {e}")
            return False

    def health_check(self, max_retries: int = 10) -> bool:
        """健康检查"""
        logger.info("执行健康检查...")

        import requests

        health_url = f"http://localhost:{self.config.api.port}/health"

        for i in range(max_retries):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    logger.info("健康检查通过")
                    return True
            except requests.RequestException:
                pass

            logger.info(f"健康检查重试 {i+1}/{max_retries}...")
            time.sleep(2)

        logger.error("健康检查失败")
        return False

    def show_status(self):
        """显示服务状态"""
        logger.info("=" * 60)
        logger.info("NeuroTrade Nexus - 策略优化模组")
        logger.info("=" * 60)
        logger.info(f"环境: {self.environment}")
        logger.info(f"项目根目录: {self.project_root}")
        logger.info(f"API端口: {self.config.api.port}")
        logger.info(f"ZeroMQ发布端口: {self.config.zeromq.publisher_port}")
        logger.info(f"ZeroMQ订阅端口: {self.config.zeromq.subscriber_port}")
        logger.info(f"Redis: {self.config.redis.host}:{self.config.redis.port}")
        logger.info("=" * 60)

        # 显示访问地址
        logger.info("服务地址:")
        logger.info(f"  API文档: http://localhost:{self.config.api.port}/docs")
        logger.info(f"  健康检查: http://localhost:{self.config.api.port}/health")
        logger.info(f"  指标监控: http://localhost:{self.config.api.port}/metrics")
        logger.info("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NeuroTrade Nexus 策略优化模组启动脚本")

    parser.add_argument(
        "--env",
        "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="运行环境 (默认: development)",
    )

    parser.add_argument("--docker", action="store_true", help="使用Docker启动")

    parser.add_argument("--monitoring", action="store_true", help="启用监控服务 (仅Docker模式)")

    parser.add_argument("--install-deps", action="store_true", help="安装依赖包")

    parser.add_argument("--check-only", action="store_true", help="仅执行环境检查")

    parser.add_argument("--no-health-check", action="store_true", help="跳过健康检查")

    args = parser.parse_args()

    # 创建启动器
    starter = OptiCoreStarter(args.env)

    try:
        # 环境检查
        if not starter.check_environment():
            logger.error("环境检查失败")
            sys.exit(1)

        # 安装依赖
        if args.install_deps:
            if not starter.install_dependencies():
                logger.error("依赖安装失败")
                sys.exit(1)

        # 依赖检查
        if not starter.check_dependencies():
            logger.error("依赖检查失败")
            if not args.install_deps:
                logger.info("请使用 --install-deps 参数安装依赖")
            sys.exit(1)

        # 外部服务检查
        services_status = starter.check_external_services()

        # 仅检查模式
        if args.check_only:
            logger.info("环境检查完成")
            return

        # 启动服务
        if args.docker:
            success = starter.start_docker(args.monitoring)
        else:
            success = starter.start_native()

        if not success:
            logger.error("服务启动失败")
            sys.exit(1)

        # 健康检查
        if not args.no_health_check:
            if not starter.health_check():
                logger.warning("健康检查失败，但服务可能仍在启动中")

        # 显示状态
        starter.show_status()

        logger.info("策略优化模组启动完成")

    except KeyboardInterrupt:
        logger.info("用户中断启动")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
