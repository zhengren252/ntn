#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
甯傚満寰粨鏋勪豢鐪熷紩鎿?(MMS) - 涓诲叆鍙ｆ枃浠?
璐熻浇鍧囪　鍣ㄥ疄鐜帮紝鍩轰簬ZeroMQ DEALER/ROUTER妯″紡

浣滆€? NeuroTrade Nexus 寮€鍙戝洟闃?
鐗堟湰: 1.0.0
鍒涘缓鏃堕棿: 2024-12-01
"""

import asyncio
import logging
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import zmq
import zmq.asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from uvicorn import Config, Server

from src.core.config import settings
from src.core.database import init_database
from src.api.routes import router as api_router
from src.services.load_balancer import LoadBalancer
from src.utils.logger import setup_logger
from src.utils.exceptions import ErrorHandler


class HealthResponse(BaseModel):
    """鍋ュ悍妫€鏌ュ搷搴旀ā鍨?""

    status: str
    timestamp: float
    version: str
    workers: int


class StatusResponse(BaseModel):
    """绯荤粺鐘舵€佸搷搴旀ā鍨?""

    service_status: str
    worker_count: int
    queue_length: int
    avg_response_time: float
    memory_usage: float
    cpu_usage: float


class MMSApplication:
    """MMS搴旂敤绋嬪簭涓荤被"""

    def __init__(self):
        self.app = FastAPI(
            title="甯傚満寰粨鏋勪豢鐪熷紩鎿?(MMS)",
            description="NeuroTrade Nexus 浜ゆ槗绯荤粺鐨勮櫄鎷熺幇瀹炲紩鎿?,
            version="1.0.0",
            docs_url="/docs" if settings.DEBUG else None,
            redoc_url="/redoc" if settings.DEBUG else None,
        )
        self.load_balancer: Optional[LoadBalancer] = None
        self.server: Optional[Server] = None
        self.shutdown_event = threading.Event()

        # 璁剧疆CORS
        allowed_origins = (
            ["*"]
            if settings.DEBUG
            else [f"http://{host}" for host in settings.ALLOWED_HOSTS]
            + [f"https://{host}" for host in settings.ALLOWED_HOSTS]
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

        # 娉ㄥ唽璺敱
        self.setup_routes()

        # 璁剧疆閿欒澶勭悊
        self.setup_error_handlers()

        # 璁剧疆淇″彿澶勭悊
        self.setup_signal_handlers()

    def setup_routes(self):
        """璁剧疆API璺敱"""

        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """鍋ュ悍妫€鏌ョ鐐?""
            worker_count = (
                self.load_balancer.get_worker_count()
                if self.load_balancer
                else 0
            )
            return HealthResponse(
                status="healthy",
                timestamp=time.time(),
                version="1.0.0",
                workers=worker_count,
            )

        @self.app.get("/status", response_model=StatusResponse)
        async def get_status():
            """鑾峰彇绯荤粺鐘舵€?""
            if not self.load_balancer:
                raise HTTPException(status_code=503, detail="Load balancer not ready")

            stats = self.load_balancer.get_stats()
            return StatusResponse(
                service_status="running",
                worker_count=stats.get("worker_count", 0),
                queue_length=stats.get("queue_length", 0),
                avg_response_time=stats.get("avg_response_time", 0.0),
                memory_usage=stats.get("memory_usage", 0.0),
                cpu_usage=stats.get("cpu_usage", 0.0),
            )

        # 娉ㄥ唽API璺敱
        self.app.include_router(api_router, prefix="/api/v1")

    def setup_error_handlers(self):
        """璁剧疆閿欒澶勭悊鍣?""
        error_handler = ErrorHandler()

        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            return await error_handler.handle_exception(request, exc)

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return await error_handler.handle_http_exception(request, exc)

        @self.app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            return await error_handler.handle_value_error(request, exc)

    def setup_signal_handlers(self):
        """璁剧疆淇″彿澶勭悊鍣?""
        try:
            # 只在主线程中设置信号处理器
            if threading.current_thread() is threading.main_thread():
                def signal_handler(signum, frame):
                    logger.info(f"Received signal {signum}, shutting down gracefully...")
                    self.shutdown_event.set()

                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                logger.debug("Signal handlers registered successfully")
            else:
                logger.debug("Skipping signal handler registration (not in main thread)")
        except Exception as e:
            logger.warning(f"Failed to setup signal handlers: {e}")
            # 在测试环境中继续运行，不因信号处理失败而中断

    async def start_load_balancer(self):
        """鍚姩璐熻浇鍧囪　鍣?""
        try:
            self.load_balancer = LoadBalancer(
                frontend_port=settings.FRONTEND_PORT,
                backend_port=settings.BACKEND_PORT,
                worker_count=settings.WORKER_COUNT,
            )
            await self.load_balancer.start()
            logger.info("Load balancer started successfully")
        except Exception as e:
            logger.error(f"Failed to start load balancer: {e}")
            raise

    async def start_web_server(self):
        """鍚姩Web鏈嶅姟鍣?""
        try:
            config = Config(
                app=self.app,
                host=settings.HOST,
                port=settings.PORT,
                log_level=settings.LOG_LEVEL.lower(),
                access_log=settings.DEBUG,
            )
            self.server = Server(config)
            await self.server.serve()
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise

    async def run(self):
        """杩愯搴旂敤绋嬪簭"""
        try:
            # 璁剧疆鏃ュ織
            setup_logger()
            logger.info("Starting MMS Application...")

            # 鍒濆鍖栨暟鎹簱
            await init_database()
            logger.info("Database initialized")

            # 鍚姩璐熻浇鍧囪　鍣?
            await self.start_load_balancer()

            # 鍚姩Web鏈嶅姟鍣?
            server_task = asyncio.create_task(self.start_web_server())

            # 绛夊緟鍏抽棴淇″彿
            while not self.shutdown_event.is_set():
                await asyncio.sleep(1)

            # 浼橀泤鍏抽棴
            logger.info("Shutting down...")
            await self.cleanup()

        except Exception as e:
            logger.error(f"Application error: {e}")
            sys.exit(1)

    async def cleanup(self):
        """娓呯悊璧勬簮"""
        try:
            if self.load_balancer:
                await self.load_balancer.stop()
                logger.info("Load balancer stopped")

            if self.server:
                self.server.should_exit = True
                logger.info("Web server stopped")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """涓诲嚱鏁?""
    try:
        app = MMSApplication()
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
