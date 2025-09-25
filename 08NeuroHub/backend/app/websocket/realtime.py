#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket实时数据推送模块

实现总控模块的实时数据推送功能：
- 系统状态实时推送
- 模组状态监控推送
- 风险告警实时通知
- 市场数据实时更新
- 资金状态变化推送
"""

import json
import asyncio
import logging
from typing import Dict, Set, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.core.config import get_settings
from app.core.redis_manager import get_redis_manager
from app.core.zmq_manager import get_zmq_manager

settings = get_settings()
logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_subscriptions: Dict[WebSocket, Set[str]] = {}
        self.running = False
        self.data_push_task = None
    
    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_subscriptions[websocket] = set()
        logger.info(f"WebSocket客户端已连接，当前连接数: {len(self.active_connections)}")
        
        # 启动数据推送任务（如果尚未启动）
        if not self.running:
            await self.start_data_push()
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        self.active_connections.discard(websocket)
        self.client_subscriptions.pop(websocket, None)
        logger.info(f"WebSocket客户端已断开，当前连接数: {len(self.active_connections)}")
        
        # 如果没有活跃连接，停止数据推送
        if not self.active_connections and self.running:
            self.stop_data_push()
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str, data_type: str = None):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections.copy():
            try:
                # 检查客户端是否订阅了此类型的数据
                if data_type and data_type not in self.client_subscriptions.get(connection, set()):
                    continue
                
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    disconnected.add(connection)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.add(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    def subscribe(self, websocket: WebSocket, data_types: list):
        """订阅数据类型"""
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket].update(data_types)
            logger.info(f"客户端订阅数据类型: {data_types}")
    
    def unsubscribe(self, websocket: WebSocket, data_types: list):
        """取消订阅数据类型"""
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket] -= set(data_types)
            logger.info(f"客户端取消订阅数据类型: {data_types}")
    
    async def start_data_push(self):
        """启动数据推送任务"""
        if self.running:
            return
        
        self.running = True
        self.data_push_task = asyncio.create_task(self._data_push_loop())
        logger.info("WebSocket数据推送任务已启动")
    
    def stop_data_push(self):
        """停止数据推送任务"""
        self.running = False
        if self.data_push_task:
            self.data_push_task.cancel()
        logger.info("WebSocket数据推送任务已停止")
    
    async def _data_push_loop(self):
        """数据推送循环"""
        redis_manager = get_redis_manager()
        
        while self.running:
            try:
                # 推送系统状态
                await self._push_system_status(redis_manager)
                
                # 推送模组状态
                await self._push_module_status(redis_manager)
                
                # 推送风险告警
                await self._push_risk_alerts(redis_manager)
                
                # 推送市场数据
                await self._push_market_data(redis_manager)
                
                # 推送资金状态
                await self._push_fund_status(redis_manager)
                
                # 等待下次推送
                await asyncio.sleep(1)  # 每秒推送一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"数据推送循环出错: {e}")
                await asyncio.sleep(5)  # 出错后等待5秒再重试
    
    async def _push_system_status(self, redis_manager):
        """推送系统状态"""
        try:
            system_status = await redis_manager.get_system_status()
            if system_status:
                message = {
                    "type": "system_status",
                    "data": system_status,
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(json.dumps(message), "system_status")
        except Exception as e:
            logger.error(f"推送系统状态失败: {e}")
    
    async def _push_module_status(self, redis_manager):
        """推送模组状态"""
        try:
            module_status = await redis_manager.get_all_module_status()
            if module_status:
                message = {
                    "type": "module_status",
                    "data": module_status,
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(json.dumps(message), "module_status")
        except Exception as e:
            logger.error(f"推送模组状态失败: {e}")
    
    async def _push_risk_alerts(self, redis_manager):
        """推送风险告警"""
        try:
            alerts = await redis_manager.get_risk_alerts(5)  # 获取最新5条告警
            if alerts:
                message = {
                    "type": "risk_alerts",
                    "data": alerts,
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(json.dumps(message), "risk_alerts")
        except Exception as e:
            logger.error(f"推送风险告警失败: {e}")
    
    async def _push_market_data(self, redis_manager):
        """推送市场数据"""
        try:
            bull_bear_index = await redis_manager.get_bull_bear_index()
            if bull_bear_index:
                message = {
                    "type": "market_data",
                    "data": {
                        "bull_bear_index": bull_bear_index
                    },
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(json.dumps(message), "market_data")
        except Exception as e:
            logger.error(f"推送市场数据失败: {e}")
    
    async def _push_fund_status(self, redis_manager):
        """推送资金状态"""
        try:
            fund_status = await redis_manager.get_fund_status()
            if fund_status:
                message = {
                    "type": "fund_status",
                    "data": fund_status,
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(json.dumps(message), "fund_status")
        except Exception as e:
            logger.error(f"推送资金状态失败: {e}")

# 全局连接管理器实例
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点处理函数"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "无效的JSON格式"
                    }),
                    websocket
                )
            except Exception as e:
                logger.error(f"处理客户端消息失败: {e}")
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": f"处理消息失败: {str(e)}"
                    }),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        manager.disconnect(websocket)

async def handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """处理客户端消息"""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # 订阅数据类型
        data_types = message.get("data_types", [])
        manager.subscribe(websocket, data_types)
        
        response = {
            "type": "subscribe_response",
            "message": f"已订阅数据类型: {data_types}",
            "subscribed_types": list(manager.client_subscriptions.get(websocket, set()))
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    elif message_type == "unsubscribe":
        # 取消订阅数据类型
        data_types = message.get("data_types", [])
        manager.unsubscribe(websocket, data_types)
        
        response = {
            "type": "unsubscribe_response",
            "message": f"已取消订阅数据类型: {data_types}",
            "subscribed_types": list(manager.client_subscriptions.get(websocket, set()))
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    elif message_type == "ping":
        # 心跳检测
        response = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    elif message_type == "get_status":
        # 获取当前状态
        redis_manager = get_redis_manager()
        
        system_status = await redis_manager.get_system_status()
        module_status = await redis_manager.get_all_module_status()
        
        response = {
            "type": "current_status",
            "data": {
                "system": system_status,
                "modules": module_status
            },
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(response), websocket)
    
    else:
        # 未知消息类型
        response = {
            "type": "error",
            "message": f"未知的消息类型: {message_type}"
        }
        await manager.send_personal_message(json.dumps(response), websocket)