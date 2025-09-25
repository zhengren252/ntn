#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroMQ消息队列管理器

负责总控模块的消息通信：
- 与其他模组的双向通信
- 命令分发和响应处理
- 心跳监控和状态同步
- 告警消息处理
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Callable

import zmq
import zmq.asyncio

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    COMMAND = "command"
    RESPONSE = "response"
    ALERT = "alert"


class ZMQManager:
    """ZeroMQ管理器"""

    def __init__(self):
        self.context = None
        self.publisher = None  # PUB socket for broadcasting
        self.subscriber = None  # SUB socket for receiving
        self.dealer = None  # DEALER socket for request-response
        self.router = None  # ROUTER socket for handling requests
        self.running = False
        self.message_handlers = {}
        self.tasks = []

    async def init_zmq(self):
        """初始化ZeroMQ连接"""
        try:
            self.context = zmq.asyncio.Context()

            # 发布者 - 用于广播消息
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(
                f"tcp://*:{settings.zmq_pub_port}"
            )

            # 订阅者 - 用于接收其他模组的消息
            self.subscriber = self.context.socket(zmq.SUB)
            # 订阅所有主题
            self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
            # 连接到其他模组的发布端口
            for port in settings.zmq_sub_ports:
                self.subscriber.connect(f"tcp://localhost:{port}")

            # DEALER - 用于发送请求
            self.dealer = self.context.socket(zmq.DEALER)
            self.dealer.connect(f"tcp://localhost:{settings.zmq_dealer_port}")

            # ROUTER - 用于处理请求
            self.router = self.context.socket(zmq.ROUTER)
            self.router.bind(f"tcp://*:{settings.zmq_router_port}")

            # 注册默认消息处理器
            self.register_handler(
                MessageType.HEARTBEAT.value, self._handle_heartbeat
            )
            self.register_handler(
                MessageType.STATUS.value, self._handle_status_update
            )
            self.register_handler(
                MessageType.ALERT.value, self._handle_alert
            )
            self.register_handler(
                MessageType.RESPONSE.value, self._handle_response
            )
            self.register_handler(
                MessageType.COMMAND.value, self._handle_command
            )

            logger.info("ZeroMQ初始化完成")

        except Exception as e:
            logger.error(f"ZeroMQ初始化失败: {e}")
            raise

    async def start(self):
        """启动ZMQ管理器"""
        if self.running:
            return

        self.running = True
        logger.info("启动ZMQ管理器")

        # 启动消息处理任务
        self.tasks = [
            asyncio.create_task(self._subscriber_loop()),
            asyncio.create_task(self._router_loop()),
            asyncio.create_task(self._heartbeat_loop())
        ]

    async def stop(self):
        """停止ZMQ管理器"""
        self.running = False
        logger.info("停止ZMQ管理器")

        # 取消所有任务
        for task in self.tasks:
            task.cancel()

        # 等待任务完成
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # 关闭socket
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.dealer:
            self.dealer.close()
        if self.router:
            self.router.close()
        if self.context:
            self.context.term()

    async def _subscriber_loop(self):
        """订阅者消息循环"""
        logger.info("启动订阅者消息循环")

        while self.running:
            try:
                # 接收消息 (非阻塞)
                message = await self.subscriber.recv_multipart(zmq.NOBLOCK)
                topic = message[0].decode('utf-8')
                data = json.loads(message[1].decode('utf-8'))

                # 将topic放入消息，便于下游感知来源主题
                try:
                    data["_topic"] = topic
                except Exception:
                    pass

                logger.debug(
                    f"收到订阅消息: {topic} - "
                    f"{data.get('type')}"
                )

                # 处理消息
                await self._process_message(data)

            except zmq.Again:
                # 没有消息，继续循环
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"订阅者消息处理错误: {e}")
                await asyncio.sleep(1)

    async def _router_loop(self):
        """路由器消息循环"""
        logger.info("启动路由器消息循环")

        while self.running:
            try:
                # 接收请求 (非阻塞)
                message = await self.router.recv_multipart(zmq.NOBLOCK)
                identity = message[0]
                empty = message[1]
                data = json.loads(message[2].decode('utf-8'))

                logger.debug(
                    f"收到路由请求: {data.get('type')}"
                )

                # 处理请求
                response = await self._process_request(data)

                # 发送响应
                await self.router.send_multipart([
                    identity,
                    empty,
                    json.dumps(response, ensure_ascii=False).encode('utf-8')
                ])

            except zmq.Again:
                # 没有消息，继续循环
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"路由器消息处理错误: {e}")
                await asyncio.sleep(1)

    async def _heartbeat_loop(self):
        """心跳循环"""
        logger.info("启动心跳循环")

        while self.running:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(30)  # 每30秒发送一次心跳
            except Exception as e:
                logger.error(f"心跳发送错误: {e}")
                await asyncio.sleep(5)

    async def _process_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            message_type = data.get('type')
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](data)
            else:
                logger.warning(f"未知消息类型: {message_type}")
        except Exception as e:
            logger.error(f"消息处理错误: {e}")

    async def _process_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理接收到的请求"""
        try:
            request_type = data.get('type')
            request_id = data.get('request_id')

            if request_type == 'command':
                return await self._handle_command_request(data)
            elif request_type == 'status':
                return await self._handle_status_request(data)
            else:
                return {
                    "request_id": request_id,
                    "status": "error",
                    "message": f"未知请求类型: {request_type}"
                }

        except Exception as e:
            logger.error(f"请求处理错误: {e}")
            return {
                "request_id": data.get('request_id'),
                "status": "error",
                "message": str(e)
            }

    async def _handle_command_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理命令请求"""
        try:
            request_id = data.get('request_id')
            command = data.get('command')
            params = data.get('params', {})

            logger.info(f"处理命令请求: {command}")

            if command == "get_status":
                # 获取系统状态
                from app.core.redis_manager import get_redis_manager
                redis_manager = get_redis_manager()
                status = await redis_manager.get_system_status()

                return {
                    "request_id": request_id,
                    "status": "success",
                    "data": status
                }

            elif command == "emergency_stop":
                # 紧急停止
                await self.broadcast_command("emergency_stop", params)

                return {
                    "request_id": request_id,
                    "status": "success",
                    "message": "紧急停止命令已发送"
                }

            elif command == "set_fund_mode":
                # 设置资金模式
                mode = params.get('mode')
                await self.broadcast_command("set_fund_mode", {"mode": mode})

                return {
                    "request_id": request_id,
                    "status": "success",
                    "message": f"资金模式已设置为: {mode}"
                }

            else:
                return {
                    "request_id": request_id,
                    "status": "error",
                    "message": f"未知命令: {command}"
                }

        except Exception as e:
            logger.error(f"命令处理错误: {e}")
            return {
                "request_id": data.get('request_id'),
                "status": "error",
                "message": str(e)
            }

    # 消息处理器
    async def _handle_heartbeat(self, data: Dict[str, Any]):
        """处理心跳消息"""
        module_name = data.get('module')
        timestamp = data.get('timestamp')

        logger.debug(f"收到心跳: {module_name} - {timestamp}")

        # 更新模组状态到Redis
        from app.core.redis_manager import get_redis_manager
        redis_manager = get_redis_manager()
        await redis_manager.set_module_status(module_name, {
            "status": "online",
            "last_heartbeat": timestamp
        })

    async def _handle_status_update(self, data: Dict[str, Any]):
        """处理状态更新消息"""
        module_name = data.get('module')
        status = data.get('status')

        logger.info(f"模组状态更新: {module_name} - {status}")

        # 更新模组状态到Redis
        from app.core.redis_manager import get_redis_manager
        redis_manager = get_redis_manager()
        await redis_manager.set_module_status(module_name, status)

    async def _handle_alert(self, data: Dict[str, Any]):
        """处理告警消息"""
        # 兼容不同来源字段与大小写
        topic = data.get("_topic", "")
        alert_type_raw = data.get('alert_type') or data.get('type') or 'UNKNOWN'
        severity_raw = data.get('severity') or data.get('level') or 'MEDIUM'
        message = data.get('description', data.get('message', ''))
        module = data.get('source', data.get('module', 'unknown'))
        recommended_action = data.get('recommended_action')

        alert_type = str(alert_type_raw).upper()
        severity = str(severity_raw).upper()

        logger.warning(
            f"收到告警[{topic}]: {module} - {alert_type} - {severity} - {message}"
        )

        # 保存告警到Redis（同时保留原始级别字段，规范化为severity）
        from app.core.redis_manager import get_redis_manager
        redis_manager = get_redis_manager()
        alert_id = str(uuid.uuid4())
        await redis_manager.set_risk_alert(alert_id, {
            "type": alert_type,
            "severity": severity,
            "level": severity,  # 兼容下游读取level
            "message": message,
            "module": module,
            "recommended_action": recommended_action,
            "timestamp": datetime.now().isoformat()
        })

        # 紧急停机触发条件：
        # 1) 严重级别 CRITICAL 且 告警类型为 BLACK_SWAN/ MARKET_CRASH 等
        # 2) 或者建议操作为 EMERGENCY_SHUTDOWN
        # 3) 或者消息文本包含关键字（黑天鹅/black swan）
        try:
            contains_black_swan = (
                '黑天鹅' in message or 'BLACK SWAN' in message.upper()
            )
            is_catastrophic_type = alert_type in {"BLACK_SWAN", "MARKET_CRASH", "SYSTEM_FAILURE"}
            if severity == 'CRITICAL' and (is_catastrophic_type or contains_black_swan) or (recommended_action == 'EMERGENCY_SHUTDOWN'):
                logger.critical(f"触发紧急停机: {alert_type} - {message}")
                # 统一使用 control.commands 主题
                await self.publish_message(
                    "control.commands",
                    MessageType.COMMAND.value,
                    {
                        "command": "EMERGENCY_SHUTDOWN",
                        "reason": f"{alert_type}: {message}",
                        "alert_id": alert_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"紧急停机触发处理错误: {e}")

    async def _handle_response(self, data: Dict[str, Any]):
        """处理响应消息"""
        request_id = data.get('request_id')
        status = data.get('status')

        logger.info(f"收到响应: {request_id} - {status}")

    async def _handle_command(self, data: Dict[str, Any]):
        """处理命令消息"""
        command = data.get('command')
        params = data.get('params', {})
        module = data.get('module', 'unknown')

        logger.info(f"收到命令: {command} from {module}")

        # 处理特定命令
        if command == "emergency_shutdown":
            logger.warning("收到紧急停机命令")
            # 这里可以添加紧急停机逻辑
        elif command == "set_fund_mode":
            mode = params.get('mode')
            logger.info(f"设置资金模式: {mode}")
        else:
            logger.warning(f"未知命令: {command}")

    # 公共接口
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"注册消息处理器: {message_type}")

    async def publish_message(self, topic: str, message_type: str,
                              data: Dict[str, Any]):
        """发布消息"""
        try:
            message_data = {
                "type": message_type,
                "timestamp": datetime.now().isoformat(),
                "module": "master_control",
                **data
            }

            await self.publisher.send_multipart([
                topic.encode('utf-8'),
                json.dumps(
                    message_data, ensure_ascii=False
                ).encode('utf-8')
            ])

            logger.debug(f"发布消息: {topic} - {message_type}")

        except Exception as e:
            logger.error(f"消息发布错误: {e}")

    async def send_command(self, target_module: str, command: str,
                           params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送命令到指定模组"""
        try:
            request_id = str(uuid.uuid4())

            command_data = {
                "request_id": request_id,
                "command": command,
                "params": params or {},
                "timestamp": datetime.now().isoformat(),
                "from_module": "master_control"
            }

            # 发送命令
            await self.dealer.send_multipart([
                target_module.encode('utf-8'),
                b'',
                json.dumps(
                    command_data, ensure_ascii=False
                ).encode('utf-8')
            ])

            logger.info(f"发送命令到 {target_module}: {command}")

            # 等待响应 (简化版本，实际应该有超时机制)
            response = await self.dealer.recv_multipart()
            response_data = json.loads(response[0].decode('utf-8'))

            return response_data

        except Exception as e:
            logger.error(f"命令发送错误: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def broadcast_command(self, command: str,
                                params: Dict[str, Any] = None):
        """广播命令到所有模组"""
        await self.publish_message("control.commands", MessageType.COMMAND.value, {
            "command": command,
            "params": params or {}
        })

    async def send_heartbeat(self):
        """发送心跳"""
        await self.publish_message("heartbeat", MessageType.HEARTBEAT.value, {
            "module": "master_control",
            "timestamp": datetime.now().isoformat(),
            "status": "online"
        })

    async def send_status_update(self, status_data: Dict[str, Any]):
        """发送状态更新"""
        await self.publish_message("status", MessageType.STATUS.value, {
            "module": "master_control",
            **status_data
        })

    async def send_alert(self, alert_type: str, message: str,
                         level: str = "warning"):
        """发送告警"""
        await self.publish_message("alert", MessageType.ALERT.value, {
            "alert_type": alert_type,
            "message": message,
            "level": level,
            "module": "master_control"
        })


# 全局ZMQ管理器实例
zmq_manager = ZMQManager()


async def init_zmq():
    """初始化ZeroMQ"""
    await zmq_manager.init_zmq()
    await zmq_manager.start()


def get_zmq_manager() -> ZMQManager:
    """获取ZMQ管理器实例"""
    return zmq_manager