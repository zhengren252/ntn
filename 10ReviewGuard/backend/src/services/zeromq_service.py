#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroMQ消息服务

负责ReviewGuard模组与其他模组的消息通信：
1. 订阅策略优化模组的交易策略 (optimizer.pool.trading)
2. 发布审核结果到交易员模组 (review.pool.approved)
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

try:
    import zmq
    import zmq.asyncio
except ImportError:
    raise ImportError("请安装pyzmq: pip install pyzmq")

try:
    from ..utils.logger import setup_logger
except ImportError:
    from utils.logger import setup_logger

logger = setup_logger(__name__)

class ZeroMQService:
    """ZeroMQ消息服务类"""
    
    def __init__(self):
        self.context = None
        self.subscriber = None
        self.publisher = None
        self.is_running = False
        self.message_handlers = {}
        
        # 从环境变量获取配置
        import os
        self.sub_endpoint = os.getenv("ZEROMQ_SUB_ENDPOINT", "tcp://localhost:5555")
        self.pub_endpoint = os.getenv("ZEROMQ_PUB_ENDPOINT", "tcp://*:5556")
        self.sub_topic = os.getenv("ZEROMQ_SUB_TOPIC", "optimizer.pool.trading")
        self.pub_topic = os.getenv("ZEROMQ_PUB_TOPIC", "review.pool.approved")
    
    async def start(self):
        """启动ZeroMQ服务"""
        try:
            logger.info("正在启动ZeroMQ服务...")
            
            # 创建异步上下文
            self.context = zmq.asyncio.Context()
            
            # 创建订阅者套接字
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(self.sub_endpoint)
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, self.sub_topic)
            
            # 创建发布者套接字
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(self.pub_endpoint)
            
            # 等待连接建立
            await asyncio.sleep(0.1)
            
            self.is_running = True
            logger.info(f"ZeroMQ服务启动成功 - SUB: {self.sub_endpoint}, PUB: {self.pub_endpoint}")
            
        except Exception as e:
            logger.error(f"ZeroMQ服务启动失败: {e}")
            raise
    
    async def stop(self):
        """停止ZeroMQ服务"""
        try:
            logger.info("正在停止ZeroMQ服务...")
            
            self.is_running = False
            
            if self.subscriber:
                self.subscriber.close()
            if self.publisher:
                self.publisher.close()
            if self.context:
                self.context.term()
            
            logger.info("ZeroMQ服务已停止")
            
        except Exception as e:
            logger.error(f"停止ZeroMQ服务时出错: {e}")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.is_running and self.subscriber is not None and self.publisher is not None
    
    def register_handler(self, topic: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[topic] = handler
        logger.info(f"已注册消息处理器: {topic}")
    
    async def listen_for_strategies(self):
        """监听策略优化模组的消息"""
        if not self.is_running or not self.subscriber:
            logger.error("ZeroMQ服务未启动，无法监听消息")
            return
        
        logger.info(f"开始监听策略消息: {self.sub_topic}")
        
        try:
            while self.is_running:
                try:
                    # 接收消息（非阻塞）
                    message = await self.subscriber.recv_multipart(zmq.NOBLOCK)
                    
                    if len(message) >= 2:
                        topic = message[0].decode('utf-8')
                        data = message[1].decode('utf-8')
                        
                        logger.info(f"收到消息 - 主题: {topic}")
                        
                        # 解析JSON数据
                        try:
                            strategy_data = json.loads(data)
                            await self._handle_strategy_message(topic, strategy_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"消息JSON解析失败: {e}")
                    
                except zmq.Again:
                    # 没有消息，短暂等待
                    await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"监听消息时出错: {e}")
    
    async def _handle_strategy_message(self, topic: str, strategy_data: Dict[str, Any]):
        """处理策略消息"""
        try:
            # 验证消息格式
            if not self._validate_strategy_message(strategy_data):
                logger.warning("收到无效的策略消息格式")
                return
            
            # 调用注册的处理器
            if topic in self.message_handlers:
                await self.message_handlers[topic](strategy_data)
            else:
                # 默认处理逻辑
                await self._default_strategy_handler(strategy_data)
        
        except Exception as e:
            logger.error(f"处理策略消息失败: {e}")
    
    def _validate_strategy_message(self, data: Dict[str, Any]) -> bool:
        """验证策略消息格式"""
        required_fields = ['strategy_id', 'symbol', 'strategy_type', 'schema_version']
        return all(field in data for field in required_fields)
    
    async def _default_strategy_handler(self, strategy_data: Dict[str, Any]):
        """默认策略处理器"""
        logger.info(f"使用默认处理器处理策略: {strategy_data.get('strategy_id')}")
        
        # 这里应该调用审核服务
        # 暂时记录日志
        logger.info(f"策略详情: {json.dumps(strategy_data, ensure_ascii=False, indent=2)}")
    
    async def publish_review_result(self, review_data: Dict[str, Any]):
        """发布审核结果"""
        if not self.is_running or not self.publisher:
            logger.error("ZeroMQ服务未启动，无法发布消息")
            return False
        
        try:
            # 按照架构文档要求构建消息格式
            message_data = {
                **review_data,
                'reviewed_at': datetime.utcnow().isoformat(),
                'reviewer_service': 'ReviewGuard',
                'schema_version': '1.0',
                'review_info': {
                    'reviewer': review_data.get('reviewer_id', 'auto'),
                    'decision_time': datetime.utcnow().isoformat(),
                    'decision': review_data.get('decision'),
                    'reason': review_data.get('reason')
                }
            }
            
            # 序列化消息
            message_json = json.dumps(message_data, ensure_ascii=False)
            
            # 发布消息
            await self.publisher.send_multipart([
                self.pub_topic.encode('utf-8'),
                message_json.encode('utf-8')
            ])
            
            logger.info(f"已发布审核结果: {review_data.get('strategy_id')}")
            return True
            
        except Exception as e:
            logger.error(f"发布审核结果失败: {e}")
            return False
    
    async def publish_rejection(self, strategy_id: str, reason: str, original_data: Dict[str, Any], reviewer_id: str = 'auto'):
        """发布拒绝消息"""
        rejection_data = {
            'strategy_id': strategy_id,
            'status': 'rejected',
            'decision': 'reject',
            'reason': reason,
            'reviewer_id': reviewer_id,
            'original_strategy': original_data,
            'rejected_at': datetime.utcnow().isoformat(),
            'schema_version': '1.0'
        }
        
        return await self.publish_review_result(rejection_data)
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'is_running': self.is_running,
            'subscriber_endpoint': self.sub_endpoint,
            'publisher_endpoint': self.pub_endpoint,
            'subscribe_topic': self.sub_topic,
            'publish_topic': self.pub_topic,
            'registered_handlers': list(self.message_handlers.keys())
        }