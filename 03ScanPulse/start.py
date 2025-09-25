#!/usr/bin/env python3
# 扫描器模组启动脚本
# 提供便捷的应用程序启动方式

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_environment(env: str) -> None:
    """设置环境变量"""
    os.environ["SCANNER_ENV"] = env

    # 设置环境特定的配置文件
    config_file = f"config.{env}.yaml"
    config_path = project_root / "scanner" / "config" / config_file

    if config_path.exists():
        os.environ["SCANNER_CONFIG_FILE"] = str(config_path)
    else:
        print(f"Warning: Configuration file {config_file} not found")
        print(f"Using default configuration")


def check_dependencies() -> bool:
    """检查依赖是否安装"""
    try:
        import zmq
        import redis
        import yaml
        import structlog
        import pandas
        import numpy
        import requests
        import aiohttp
        import dateutil
        import pytz
        import dotenv
        import pydantic
        import aioredis

        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="NeuroTrade Nexus Scanner Module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py                    # 使用默认环境(development)
  python start.py --env production   # 使用生产环境
  python start.py --env staging      # 使用预发布环境
  python start.py --check-deps       # 检查依赖
        """,
    )

    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="development",
        help="运行环境 (默认: development)",
    )

    parser.add_argument("--check-deps", action="store_true", help="检查依赖是否安装")

    parser.add_argument("--config-file", type=str, help="指定配置文件路径")

    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别"
    )

    parser.add_argument("--redis-host", type=str, help="Redis主机地址")

    parser.add_argument("--redis-port", type=int, help="Redis端口")

    parser.add_argument("--zmq-port", type=int, help="ZeroMQ端口")

    args = parser.parse_args()

    # 检查依赖
    if args.check_deps:
        if check_dependencies():
            print("All dependencies are installed")
            return 0
        else:
            return 1

    # 检查依赖
    if not check_dependencies():
        return 1

    # 设置环境
    setup_environment(args.env)

    # 设置可选的环境变量
    if args.config_file:
        os.environ["SCANNER_CONFIG_FILE"] = args.config_file

    if args.log_level:
        os.environ["SCANNER_LOG_LEVEL"] = args.log_level

    if args.redis_host:
        os.environ["REDIS_HOST"] = args.redis_host

    if args.redis_port:
        os.environ["REDIS_PORT"] = str(args.redis_port)

    if args.zmq_port:
        os.environ["ZMQ_PORT"] = str(args.zmq_port)

    print(f"Starting NeuroTrade Nexus Scanner Module...")
    print(f"Environment: {args.env}")
    print(f"Project Root: {project_root}")

    # 导入并运行主程序
    try:
        from scanner.main import main as scanner_main
        import asyncio

        # 运行扫描器
        asyncio.run(scanner_main())

    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Error starting scanner: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
