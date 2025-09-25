#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由模块

实现总控模块的核心API端点：
- 系统状态管理
- 模组状态监控
- 风险告警处理
- 资金状态查询
- 控制指令发送
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.redis_manager import get_redis_manager
from app.core.zmq_manager import get_zmq_manager

settings = get_settings()
logger = logging.getLogger(__name__)

# 创建API路由器
api_router = APIRouter()

# 请求/响应模型
class SystemStatusResponse(BaseModel):
    status: str
    modules: Dict[str, Any]
    timestamp: float

class ModuleStatusUpdate(BaseModel):
    module_name: str
    status: str
    health: str
    cpu_usage: float
    memory_usage: float

class RiskAlert(BaseModel):
    alert_type: str
    level: str
    message: str
    data: Optional[Dict[str, Any]] = None

class ControlCommand(BaseModel):
    command_type: str
    target_module: str
    payload: Dict[str, Any]
    priority: str = "medium"

class CommandRequest(BaseModel):
    command: str
    payload: Optional[Dict[str, Any]] = None

# 系统状态相关API
@api_router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """获取系统整体状态"""
    try:
        redis_manager = get_redis_manager()
        
        # 获取系统状态
        system_status = await redis_manager.get_system_status()
        
        # 获取所有模组状态
        module_status = await redis_manager.get_all_module_status()
        
        return SystemStatusResponse(
            status="healthy" if system_status else "unknown",
            modules=module_status,
            timestamp=datetime.now().timestamp()
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/system/status")
async def update_system_status(status_data: Dict[str, Any]):
    """更新系统状态"""
    try:
        redis_manager = get_redis_manager()
        await redis_manager.set_system_status(status_data)
        return {"message": "系统状态更新成功"}
    except Exception as e:
        logger.error(f"更新系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 模组状态相关API
@api_router.get("/modules/status")
async def get_all_modules_status():
    """获取所有模组状态"""
    try:
        redis_manager = get_redis_manager()
        modules = await redis_manager.get_all_module_status()
        return {"modules": modules}
    except Exception as e:
        logger.error(f"获取模组状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/modules/{module_name}/status")
async def get_module_status(module_name: str):
    """获取指定模组状态"""
    try:
        redis_manager = get_redis_manager()
        status = await redis_manager.get_module_status(module_name)
        if not status:
            raise HTTPException(status_code=404, detail=f"模组 {module_name} 未找到")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模组 {module_name} 状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/modules/status")
async def update_module_status(status_update: ModuleStatusUpdate):
    """更新模组状态"""
    try:
        redis_manager = get_redis_manager()
        status_data = {
            "status": status_update.status,
            "health": status_update.health,
            "cpu_usage": str(status_update.cpu_usage),
            "memory_usage": str(status_update.memory_usage),
            "last_update": datetime.now().isoformat()
        }
        await redis_manager.set_module_status(status_update.module_name, status_data)
        return {"message": f"模组 {status_update.module_name} 状态更新成功"}
    except Exception as e:
        logger.error(f"更新模组状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 风险告警相关API
@api_router.get("/risk/alerts")
async def get_risk_alerts(limit: int = 10):
    """获取风险告警列表"""
    try:
        redis_manager = get_redis_manager()
        alerts = await redis_manager.get_risk_alerts(limit)
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"获取风险告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/risk/alerts")
async def create_risk_alert(alert: RiskAlert):
    """创建风险告警"""
    try:
        redis_manager = get_redis_manager()
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        alert_data = {
            "type": alert.alert_type,
            "level": alert.level,
            "message": alert.message,
            "data": json.dumps(alert.data) if alert.data else "{}"
        }
        await redis_manager.set_risk_alert(alert_id, alert_data)
        return {"alert_id": alert_id, "message": "风险告警创建成功"}
    except Exception as e:
        logger.error(f"创建风险告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 资金状态相关API
@api_router.get("/fund/status")
async def get_fund_status():
    """获取资金状态"""
    try:
        redis_manager = get_redis_manager()
        fund_status = await redis_manager.get_fund_status()
        return fund_status if fund_status else {"message": "暂无资金状态数据"}
    except Exception as e:
        logger.error(f"获取资金状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/fund/status")
async def update_fund_status(fund_data: Dict[str, Any]):
    """更新资金状态"""
    try:
        redis_manager = get_redis_manager()
        await redis_manager.set_fund_status(fund_data)
        return {"message": "资金状态更新成功"}
    except Exception as e:
        logger.error(f"更新资金状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 市场数据相关API
@api_router.get("/market/bull-bear-index")
async def get_bull_bear_index():
    """获取牛熊指数"""
    try:
        redis_manager = get_redis_manager()
        index_data = await redis_manager.get_bull_bear_index()
        return index_data if index_data else {"message": "暂无牛熊指数数据"}
    except Exception as e:
        logger.error(f"获取牛熊指数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/market/bull-bear-index")
async def update_bull_bear_index(index_value: float, indicators: Dict[str, Any]):
    """更新牛熊指数"""
    try:
        redis_manager = get_redis_manager()
        await redis_manager.set_bull_bear_index(index_value, indicators)
        return {"message": "牛熊指数更新成功"}
    except Exception as e:
        logger.error(f"更新牛熊指数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 控制指令相关API
@api_router.post("/commands/execute")
async def execute_control_command(cmd: CommandRequest):
    """执行控制指令（用于单元测试验证）"""
    try:
        zmq_manager = get_zmq_manager()

        # 指令白名单（仅允许大写）
        allowed_commands = {
            "SWITCH_MODE",
            "EMERGENCY_SHUTDOWN",
            "START",
            "STOP",
        }

        # 基本校验
        if not cmd.command or not cmd.command.isupper() or cmd.command not in allowed_commands:
            raise HTTPException(status_code=422, detail=f"Invalid command type: {cmd.command}")

        payload = cmd.payload or {}

        # 构造消息，符合测试断言字段
        message = {
            "type": "command",
            "command": cmd.command,
            "payload": payload,
            "source": "master_control",
            "timestamp": datetime.now().isoformat(),
        }

        # 发布到统一控制主题
        await zmq_manager.publish_message("control.commands", message)

        return {"message": f"指令 {cmd.command} 执行成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行控制指令失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 健康检查API
@api_router.get("/health")
async def health_check():
    """API健康检查"""
    try:
        redis_manager = get_redis_manager()
        zmq_manager = get_zmq_manager()
        
        # 检查Redis连接
        redis_health = "healthy"
        try:
            await redis_manager.redis.ping()
        except:
            redis_health = "unhealthy"
        
        # 检查ZeroMQ状态
        zmq_health = "healthy" if zmq_manager.running else "stopped"
        
        return {
            "status": "healthy",
            "components": {
                "redis": redis_health,
                "zeromq": zmq_health
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))