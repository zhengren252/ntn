#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块八：总控模块 (Master Control Module)
主应用入口文件

严格按照核心设计理念和全局规范实现：
- 微服务架构
- ZeroMQ通信
- Redis状态管理
- SQLite持久化存储
- 三环境隔离
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

# 获取配置
settings = get_settings()

# 配置日志
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
    """应用生命周期管理"""
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    logger.info(f"运行环境: {settings.app_env}")

    try:
        # 初始化数据库
        logger.info("初始化数据库...")
        await init_database()

        # 初始化Redis
        logger.info("初始化Redis...")
        await init_redis()

        # 初始化ZeroMQ
        logger.info("初始化ZeroMQ...")
        await init_zmq()

        logger.info("所有组件初始化完成")

        yield

    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    finally:
        # 清理资源
        logger.info("关闭应用组件...")

        try:
            # 关闭ZeroMQ
            zmq_manager = get_zmq_manager()
            await zmq_manager.stop()

            # 关闭Redis
            redis_manager = get_redis_manager()
            await redis_manager.close()

            # 关闭数据库
            await close_database()

            logger.info("应用已安全关闭")
        except Exception as e:
            logger.error(f"应用关闭时出错: {e}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="NeuroTrade Nexus交易系统的决策大脑和指挥中心",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix=settings.api_v1_prefix)
# 为兼容历史与测试期望，额外挂载 /api 前缀，确保 /api/commands/execute 可用
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查Redis连接
        redis_manager = get_redis_manager()
        redis_status = await redis_manager.ping()
        
        # 检查ZeroMQ连接
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
    """获取系统状态"""
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
    """WebSocket实时数据端点"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        await websocket_manager.disconnect(websocket)


if __name__ == "__main__":
    # 根据环境启动应用
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