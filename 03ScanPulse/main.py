#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鎵弿鍣ㄦā缁勪富鍏ュ彛鏂囦欢
璐熻矗鍚姩鍜岀鐞嗘壂鎻忓櫒鏈嶅姟
"""

import sys
import os
import asyncio
import signal
from pathlib import Path
from typing import Optional
import structlog
import click

# 娣诲姞椤圭洰鏍圭洰褰曞埌Python璺緞
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scanner.core.scanner_controller import ScannerController
from scanner.utils.logger import setup_logging
from scanner.config.manager import ConfigManager
# 新增：引入统一应用入口（scanner/main.py）
from scanner.main import main as scanner_app_main

# 閰嶇疆鏃ュ織
logger = structlog.get_logger(__name__)


class ScannerService:
    """鎵弿鍣ㄦ湇鍔＄鐞嗙被"""

    def __init__(
        self, config_path: Optional[str] = None, environment: str = "development"
    ):
        self.config_path = config_path
        self.environment = environment
        self.controller: Optional[ScannerController] = None
        self.running = False

        # 璁剧疆淇″彿澶勭悊
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up signal handlers."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Windows鐗瑰畾淇″彿
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, signal_handler)

    async def start(self) -> bool:
        """Start the scanner service.

        Returns:
            bool: True if started successfully, otherwise False.
        """
        try:
            logger.info("Starting Scanner Service", environment=self.environment)

            # 设置运行环境变量，供 ConfigManager 使用
            os.environ["APP_ENV"] = self.environment

            # 加载配置（当提供 config_path 时，将其作为配置目录传入）
            config_manager = (
                ConfigManager(config_dir=self.config_path)
                if self.config_path
                else ConfigManager()
            )
            config = config_manager.load_config()

            # 设置日志
            setup_logging(config.get("logging", {}))

            # 创建控制器
            self.controller = ScannerController(config)

            # 启动控制器
            success = await self.controller.start()
            if not success:
                logger.error("Failed to start scanner controller")
                return False

            self.running = True
            logger.info("Scanner Service started successfully")

            # 保持运行
            await self._run_forever()

            return True

        except Exception as e:
            logger.error("Error starting scanner service", error=str(e))
            return False

    async def _run_forever(self):
        """淇濇寔鏈嶅姟杩愯"""
        try:
            while self.running and self.controller:
                # 妫€鏌ユ帶鍒跺櫒鐘舵€?
                if not await self.controller.is_healthy():
                    logger.warning("Controller health check failed")
                    
                # 绛夊緟涓€娈垫椂闂?
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("Service loop cancelled")
        except Exception as e:
            logger.error("Error in service loop", error=str(e))
            self.running = False

    def stop(self):
        """Stop the scanner service."""
        logger.info("Stopping Scanner Service")
        self.running = False
        
        if self.controller:
            asyncio.create_task(self.controller.stop())

    async def restart(self) -> bool:
        """Restart the scanner service."""
        logger.info("Restarting Scanner Service")
        
        # 鍋滄褰撳墠鏈嶅姟
        self.stop()
        await asyncio.sleep(2)
        
        # 閲嶆柊鍚姩
        return await self.start()


# CLI鍛戒护瀹氫箟
@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.pass_context
def cli(ctx, debug):
    """Scanner module CLI utility."""
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
    
    if debug:
        os.environ['LOG_LEVEL'] = 'DEBUG'


@cli.command()
@click.option('--environment', '-e', default='development', 
              type=click.Choice(['development', 'staging', 'production']),
              help='杩愯鐜')
@click.option('--config', '-c', help='閰嶇疆鏂囦欢璺緞')
@click.pass_context
def start(ctx, environment, config):
    """Start scanner service (unified entry)."""
    # 统一入口：委托给 scanner.main.main()，确保启动 Web 健康检查与扫描器
    os.environ['SCANNER_ENV'] = environment
    try:
        asyncio.run(scanner_app_main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error("Service failed", error=str(e))
        sys.exit(1)


@cli.command()
@click.option('--environment', '-e', default='development',
              type=click.Choice(['development', 'staging', 'production']),
              help='杩愯鐜')
def status(environment):
    """Show scanner service status."""
    # 杩欓噷鍙互瀹炵幇鐘舵€佹鏌ラ€昏緫
    click.echo(f"Checking scanner status for environment: {environment}")
    # TODO: 瀹炵幇瀹為檯鐨勭姸鎬佹鏌?


@cli.command()
@click.option('--environment', '-e', default='development',
              type=click.Choice(['development', 'staging', 'production']),
              help='杩愯鐜')
def stop(environment):
    """Stop scanner service."""
    # 杩欓噷鍙互瀹炵幇鍋滄閫昏緫
    click.echo(f"Stopping scanner for environment: {environment}")
    # TODO: 瀹炵幇瀹為檯鐨勫仠姝㈤€昏緫


@cli.command()
@click.option('--environment', '-e', default='development',
              type=click.Choice(['development', 'staging', 'production']),
              help='杩愯鐜')
def restart(environment):
    """Restart scanner service."""
    click.echo(f"Restarting scanner for environment: {environment}")
    # TODO: 瀹炵幇瀹為檯鐨勯噸鍚€昏緫


@cli.command()
@click.option('--environment', '-e', default='development',
              type=click.Choice(['development', 'staging', 'production']),
              help='杩愯鐜')
def health(environment):
    """Health check."""
    click.echo(f"Health check for environment: {environment}")
    # TODO: 瀹炵幇鍋ュ悍妫€鏌ラ€昏緫


if __name__ == '__main__':
    # 璁剧疆鐜鍙橀噺
    os.environ.setdefault('SCANNER_ENV', 'development')
    
    # 鍚姩CLI
    cli()
