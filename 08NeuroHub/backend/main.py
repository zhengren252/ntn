#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
妯＄粍鍏細鎬绘帶妯″潡 (Master Control Module)
涓诲簲鐢ㄥ叆鍙ｆ枃浠?

涓ユ牸鎸夌収鏍稿績璁捐鐞嗗康鍜屽叏灞€瑙勮寖瀹炵幇锛?
- 寰湇鍔℃灦鏋?
- ZeroMQ閫氫俊
- Redis鐘舵€佺鐞?
- SQLite鎸佷箙鍖栧瓨鍌?
- 涓夌幆澧冮殧绂?
"""

import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_database, close_database
from app.core.redis_manager import init_redis, get_redis_manager
from app.core.zmq_manager import init_zmq, get_zmq_manager
from app.api.routes import api_router
from app.websocket.realtime import websocket_manager

# 鑾峰彇閰嶇疆
settings = get_settings()

# 閰嶇疆鏃ュ織
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """搴旂敤鐢熷懡鍛ㄦ湡绠＄悊"""
    logger.info(f"鍚姩 {settings.app_name} v{settings.app_version}")
    logger.info(f"杩愯鐜: {settings.app_env}")

    try:
        # 鍒濆鍖栨暟鎹簱
        logger.info("鍒濆鍖栨暟鎹簱...")
        await init_database()

        # 鍒濆鍖朢edis
        logger.info("鍒濆鍖朢edis...")
        await init_redis()

        # 鍒濆鍖朲eroMQ
        logger.info("鍒濆鍖朲eroMQ...")
        await init_zmq()

        logger.info("鎵€鏈夌粍浠跺垵濮嬪寲瀹屾垚")

        yield

    except Exception as e:
        logger.error(f"搴旂敤鍚姩澶辫触: {e}")
        raise
    finally:
        # 娓呯悊璧勬簮
        logger.info("鍏抽棴搴旂敤缁勪欢...")

        try:
            # 鍏抽棴ZeroMQ
            zmq_manager = get_zmq_manager()
            await zmq_manager.stop()

            # 鍏抽棴Redis
            redis_manager = get_redis_manager()
            await redis_manager.close()

            # 鍏抽棴鏁版嵁搴?
            await close_database()

            logger.info("搴旂敤宸插畨鍏ㄥ叧闂?")
        except Exception as e:
            logger.error(f"搴旂敤鍏抽棴鏃跺嚭閿? {e}")


# 鍒涘缓FastAPI搴旂敤
app = FastAPI(
    title=settings.app_name,
    description="NeuroTrade Nexus浜ゆ槗绯荤粺鐨勫喅绛栧ぇ鑴戝拰鎸囨尌涓績",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# 娣诲姞CORS涓棿浠?
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 娉ㄥ唽璺敱
app.include_router(api_router, prefix=settings.api_v1_prefix)
# 为兼容历史与测试期望，额外挂载 /api 前缀，确保 /api/commands/execute 可用
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """鍋ュ悍妫€鏌ョ鐐?""
    try:
        # 妫€鏌edis杩炴帴
        redis_manager = get_redis_manager()
        redis_status = await redis_manager.ping()
        
        # 妫€鏌eroMQ杩炴帴
        zmq_manager = get_zmq_manager()
        zmq_status = zmq_manager.is_connected()
        
        if redis_status and zmq_status:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": asyncio.get_event_loop().time(),
                    "services": {
                        "redis": "connected",
                        "zmq": "connected"
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": asyncio.get_event_loop().time(),
                    "services": {
                        "redis": "connected" if redis_status else "disconnected",
                        "zmq": "connected" if zmq_status else "disconnected"
                    }
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": str(e)}
        )


@app.get(f"{settings.api_v1_prefix}/system/status")
async def get_system_status():
    """鑾峰彇绯荤粺鐘舵€?""
    try:
        redis_manager = get_redis_manager()
        zmq_manager = get_zmq_manager()
        
        system_status = {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "timestamp": asyncio.get_event_loop().time(),
            "components": {
                "redis": {
                    "status": "connected" if await redis_manager.ping() else "disconnected",
                    "info": await redis_manager.get_info()
                },
                "zmq": {
                    "status": "connected" if zmq_manager.is_connected() else "disconnected",
                    "endpoints": zmq_manager.get_endpoints()
                }
            }
        }
        
        return JSONResponse(
            status_code=200,
            content=system_status
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket瀹炴椂鏁版嵁绔偣"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # 淇濇寔杩炴帴娲昏穬
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket杩炴帴閿欒: {e}")
    finally:
        await websocket_manager.disconnect(websocket)


if __name__ == "__main__":
    # 鏍规嵁鐜鍚姩搴旂敤
    if settings.app_env == "development":
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level=settings.log_level.lower()
        )
    else:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            workers=4,
            log_level=settings.log_level.lower()
        )