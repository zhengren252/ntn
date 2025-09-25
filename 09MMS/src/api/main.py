#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - FastAPI主应用
主要的FastAPI应用入口点

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn
import time
import uuid
from datetime import datetime, timezone

from ..core.config import get_settings
from ..core.database import DatabaseManager
from ..core.simulation_engine import SimulationEngine
from ..utils.logger import setup_logging, get_logger
from ..utils.metrics import MetricsCollector
from .routes import router

# 获取配置
settings = get_settings()

# 设置日志
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

# 全局变量
db_manager: DatabaseManager = None
simulation_engine: SimulationEngine = None
metrics_collector: MetricsCollector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动市场微结构仿真引擎 (MMS)...")

    try:
        # 初始化数据库管理器
        global db_manager
        db_manager = DatabaseManager()
        await db_manager.init_database()
        logger.info("数据库初始化完成")

        # 初始化仿真引擎
        global simulation_engine
        simulation_engine = SimulationEngine(db_manager)
        logger.info("仿真引擎初始化完成")

        # 初始化指标收集器
        global metrics_collector
        metrics_collector = MetricsCollector()
        logger.info("指标收集器初始化完成")

        # 设置信号处理
        setup_signal_handlers()

        logger.info(f"MMS服务启动完成，监听端口: {settings.HTTP_PORT}")

        yield

    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise

    finally:
        # 关闭时清理资源
        logger.info("正在关闭MMS服务...")

        if simulation_engine:
            # 取消所有运行中的仿真任务
            running_tasks = simulation_engine.get_running_simulations()
            for task_id in running_tasks:
                await simulation_engine.cancel_simulation(task_id)
            logger.info(f"已取消 {len(running_tasks)} 个运行中的仿真任务")

        if db_manager:
            logger.info("数据库管理器清理完成")

        logger.info("MMS服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="市场微结构仿真引擎 (MMS)",
    description="""市场微结构仿真引擎提供高精度的交易执行仿真服务，
    支持多种市场场景和交易策略的仿真分析。
    
    ## 主要功能
    
    * **仿真执行**: 支持多种交易策略的市场微结构仿真
    * **参数校准**: 基于历史数据的仿真参数自动校准
    * **性能分析**: 详细的仿真结果分析和报告生成
    * **实时监控**: 系统状态和性能指标的实时监控
    
    ## 支持的场景类型
    
    * 正常市场条件
    * 黑天鹅事件
    * 高波动率环境
    * 低流动性市场
    * 闪崩场景
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# 请求中间件
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """请求处理中间件"""
    start_time = asyncio.get_event_loop().time()

    # 生成/透传 Request ID
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    setattr(request.state, "request_id", request_id)

    # 记录请求
    logger.info(f"收到请求: {request.method} {request.url}")

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = asyncio.get_event_loop().time() - start_time

    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Service-Name"] = "MMS"
    response.headers["X-Service-Version"] = settings.APP_VERSION
    response.headers["X-Request-ID"] = request_id

    # 记录响应
    logger.info(f"响应完成: {response.status_code}, 耗时: {process_time:.4f}秒")

    # 记录指标
    if metrics_collector:
        await metrics_collector.record_request(
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration=process_time,
        )

    return response


# 异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)

    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "内部服务器错误",
            "timestamp": timestamp,
            "success": False,
            "request_id": request_id,
            "path": str(request.url.path),
        },
    )


# 健康检查端点
@app.get("/", tags=["基础"])
async def root():
    """根端点"""
    return {
        "service": "市场微结构仿真引擎 (MMS)",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs_url": "/docs" if settings.is_development else None,
    }


@app.get("/health", tags=["基础"], summary="健康检查")
async def health_check_root(request: Request):
    """根级健康检查端点，与 /api/v1/health 保持一致，供编排探针使用"""
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or uuid.uuid4().hex
    return {
        "status": "healthy",
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "service": "MMS",
        "version": settings.APP_VERSION,
    }

# 包含路由
app.include_router(router, prefix="/api/v1", tags=["仿真引擎"])


# 自定义OpenAPI
def custom_openapi():
    """自定义OpenAPI文档"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="市场微结构仿真引擎 API",
        version=settings.APP_VERSION,
        description="市场微结构仿真引擎的RESTful API接口文档",
        routes=app.routes,
    )

    # 添加自定义信息
    openapi_schema["info"]["x-logo"] = {"url": "https://example.com/logo.png"}

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def setup_signal_handlers():
    """设置信号处理器"""
    import threading
    
    try:
        # 只在主线程中设置信号处理器
        if threading.current_thread() is threading.main_thread():
            def signal_handler(signum, frame):
                logger.info(f"收到信号 {signum}，准备关闭服务...")
                # 这里可以添加优雅关闭逻辑
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            logger.debug("信号处理器注册成功")
        else:
            logger.debug("跳过信号处理器注册（非主线程）")
    except Exception as e:
        logger.warning(f"信号处理器设置失败: {e}")
        # 在测试环境中继续运行，不因信号处理失败而中断


# 依赖注入函数
async def get_db_manager() -> DatabaseManager:
    """获取数据库管理器依赖"""
    return db_manager


async def get_simulation_engine() -> SimulationEngine:
    """获取仿真引擎依赖"""
    return simulation_engine


async def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器依赖"""
    return metrics_collector


# 开发模式下的调试端点
if settings.is_development:

    @app.get("/debug/config", tags=["调试"])
    async def debug_config():
        """调试配置信息"""
        return {
            "app_env": settings.APP_ENV,
            "debug": settings.DEBUG,
            "host": settings.HOST,
            "port": settings.HTTP_PORT,
            "database_url": settings.DATABASE_URL,
            "redis_url": settings.REDIS_URL,
            "log_level": settings.LOG_LEVEL,
        }

    @app.get("/debug/metrics", tags=["调试"])
    async def debug_metrics():
        """调试指标信息"""
        if metrics_collector:
            return await metrics_collector.get_all_metrics()
        return {"message": "指标收集器未初始化"}


if __name__ == "__main__":
    # 直接运行时的配置
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.HTTP_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
