#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Factory Module - 涓诲簲鐢ㄥ叆鍙?
鏍稿績璁捐鐞嗗康锛氬井鏈嶅姟鏋舵瀯銆佹暟鎹殧绂汇€乑eroMQ閫氫俊銆佷笁鐜闅旂
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import zmq
import zmq.asyncio
from typing import Dict, Any
from datetime import datetime, timezone
import uuid
import os

from .config.settings import get_settings
from .routers import api_gateway, auth_center, quota_circuit, cluster_management, exchange, llm
from .core.zmq_manager import ZMQManager, MessageTopics
from .core.redis_manager import RedisManager
from .core.sqlite_manager import SQLiteManager
from .security.auth import AuthManager

# 閰嶇疆鏃ュ織
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 鍏ㄥ眬绠＄悊鍣ㄥ疄渚?
zmq_manager: ZMQManager = None
redis_manager: RedisManager = None
sqlite_manager: SQLiteManager = None
auth_manager: AuthManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """搴旂敤鐢熷懡鍛ㄦ湡绠＄悊 - 涓ユ牸鎸夌収鍏ㄥ眬瑙勮寖"""
    global zmq_manager, redis_manager, sqlite_manager, auth_manager

    settings = get_settings()
    logger.info(f"鍚姩API Factory Module - 鐜: {settings.environment}")

    try:
        # 鍒濆鍖栨牳蹇冪粍浠?- 鎸夌収绯荤粺绾ч泦鎴愭祦绋?
        zmq_manager = ZMQManager(settings.zmq_config)
        await zmq_manager.initialize()

        redis_manager = RedisManager(settings.redis_config)
        await redis_manager.initialize()

        sqlite_manager = SQLiteManager(settings.sqlite_config)
        await sqlite_manager.initialize()

        auth_manager = AuthManager(settings.auth_config)
        await auth_manager.initialize()

        logger.info("鎵€鏈夋牳蹇冪粍浠跺垵濮嬪寲瀹屾垚")

        # 在服务启动成功后，通过ZMQ发布UP状态
        try:
            if zmq_manager:
                up_message = {
                    "service": "api_factory",
                    "type": "status_change",
                    "status": "up",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "environment": settings.environment,
                    "version": "1.0.0",
                }
                await zmq_manager.publish_message(
                    topic=MessageTopics.STATUS_CHANGE, message=up_message
                )
                logger.info("ZMQ status published: UP")
        except Exception as pub_err:
            logger.error(f"Failed to publish ZMQ UP status: {pub_err}")

        yield

    except Exception as e:
        logger.error(f"搴旂敤鍚姩澶辫触: {e}")
        raise
    finally:
        # 在服务关闭前，通过ZMQ发布DOWN状态
        try:
            if zmq_manager:
                down_message = {
                    "service": "api_factory",
                    "type": "status_change",
                    "status": "down",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "environment": os.getenv("ENV", "unknown"),
                    "version": "1.0.0",
                }
                # 尝试发送关闭通知，但不因失败而阻断清理流程
                try:
                    await zmq_manager.publish_message(
                        topic=MessageTopics.STATUS_CHANGE, message=down_message
                    )
                    logger.info("ZMQ status published: DOWN")
                except Exception as pub_err2:
                    logger.error(f"Failed to publish ZMQ DOWN status: {pub_err2}")
        except Exception:
            pass

        # 娓呯悊璧勬簮
        if zmq_manager:
            await zmq_manager.cleanup()
        if redis_manager:
            await redis_manager.cleanup()
        if sqlite_manager:
            await sqlite_manager.cleanup()
        if auth_manager:
            await auth_manager.cleanup()

        logger.info("API Factory Module shutdown complete")


# 鍒涘缓FastAPI搴旂敤瀹炰緥
app = FastAPI(
    title="API Factory Module",
    description="缁熶竴API绠＄悊宸ュ巶 - 寰湇鍔℃灦鏋勩€佹暟鎹殧绂汇€乑eroMQ閫氫俊",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS涓棿浠堕厤缃?
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 鐢熶骇鐜闇€瑕侀檺鍒?
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 瀹夊叏璁よ瘉
security = HTTPBearer()

# 娉ㄥ唽璺敱妯″潡 - 鍥涘ぇ鏍稿績鍔熻兘
app.include_router(api_gateway.router, prefix="/api/v1/gateway", tags=["API Gateway"])

app.include_router(
    auth_center.router, prefix="/api/v1/auth", tags=["Authentication Center"]
)

app.include_router(
    quota_circuit.router, prefix="/api/v1/quota", tags=["Quota & Circuit Breaker"]
)

app.include_router(
    cluster_management.router, prefix="/api/v1/cluster", tags=["Cluster Management"]
)

# 新增：注册 Exchange 与 LLM 的版本化路由
app.include_router(
    exchange.router, prefix="/api/v1", tags=["Exchange"]
)
app.include_router(
    llm.router, prefix="/api/v1", tags=["LLM"]
)

# 兼容性路由（无版本前缀），以适配历史测试与调用路径
# /auth -> /api/v1/auth, /quota -> /api/v1/quota, /cluster -> /api/v1/cluster, /api -> /api/v1/gateway
app.include_router(
    auth_center.router, prefix="/auth", tags=["Authentication Center (compat)"]
)
app.include_router(
    quota_circuit.router, prefix="/quota", tags=["Quota & Circuit Breaker (compat)"]
)
app.include_router(
    cluster_management.router, prefix="/cluster", tags=["Cluster Management (compat)"]
)
# 新增：注册 Exchange 与 LLM 的兼容性路由
app.include_router(
    exchange.router, prefix="", tags=["Exchange (compat)"]
)
app.include_router(
    llm.router, prefix="", tags=["LLM (compat)"]
)
# 注意：将 /api 映射到 gateway 的根（历史上 tests 使用 /api/configs 等路径）
app.include_router(
    api_gateway.router, prefix="/api", tags=["API Gateway (compat)"]
)


@app.get("/")
async def root():
    """Root - system status probe."""
    settings = get_settings()
    return {
        "service": "API Factory Module",
        "version": "1.0.0",
        "environment": settings.environment,
        "status": "running",
        "core_modules": [
            "API Gateway",
            "Authentication Center",
            "Quota & Circuit Breaker",
            "Cluster Management",
        ],
    }


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint - basic liveness and readiness."""
    try:
        # Prepare standardized fields
        req_id = (
            request.headers.get("x-request-id")
            or request.headers.get("X-Request-ID")
            or uuid.uuid4().hex
        )
        ts = datetime.now(timezone.utc).isoformat()
        # Check component status
        zmq_status = await zmq_manager.health_check() if zmq_manager else False
        redis_status = await redis_manager.health_check() if redis_manager else False
        sqlite_status = await sqlite_manager.health_check() if sqlite_manager else False

        return {
            "status": "healthy",
            "success": True,
            "timestamp": ts,
            "module": "API Factory Module",
            "version": "1.0.0",
            "request_id": req_id,
            "components": {
                "zmq": zmq_status,
                "redis": redis_status,
                "sqlite": sqlite_status,
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "api_factory.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
