#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - ZeroMQ消息服务
"""

import asyncio
import json
import zmq
import zmq.asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import logging

try:
    from ..models.database import StrategyReview
except ImportError:
    from models.database import StrategyReview
try:
    from ..utils.config import get_settings
except ImportError:
    from utils.config import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class ZMQService:
    """ZeroMQ消息服务"""
    
    def __init__(self, review_service=None):
        self.review_service = review_service
        self.context = None
        self.subscriber = None
        self.publisher = None
        self.is_running = False
        
        # ZeroMQ配置
        self.sub_endpoint = settings.zmq_sub_endpoint  # 订阅optimizer.pool.trading
        self.pub_endpoint = settings.zmq_pub_endpoint  # 发布reviewguard.pool.approved
        
    async def start(self):
        """启动ZeroMQ服务"""
        try:
            # 创建异步上下文
            self.context = zmq.asyncio.Context()
            
            # 创建订阅者socket
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(self.sub_endpoint)
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "optimizer.pool.trading")
            
            # 创建发布者socket
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(self.pub_endpoint)
            
            self.is_running = True
            logger.info(f"ZeroMQ service started - SUB: {self.sub_endpoint}, PUB: {self.pub_endpoint}")
            
            # 启动消息监听任务
            asyncio.create_task(self._listen_for_strategies())
            
        except Exception as e:
            logger.error(f"Failed to start ZeroMQ service: {e}")
            raise
    
    async def stop(self):
        """停止ZeroMQ服务"""
        self.is_running = False
        
        if self.subscriber:
            self.subscriber.close()
        if self.publisher:
            self.publisher.close()
        if self.context:
            self.context.term()
            
        logger.info("ZeroMQ service stopped")
    
    async def _listen_for_strategies(self):
        """监听策略优化模组的消息"""
        logger.info("Started listening for strategy messages...")
        
        while self.is_running:
            try:
                # 接收消息（非阻塞）
                message = await self.subscriber.recv_multipart(flags=zmq.NOBLOCK)
                
                if len(message) >= 2:
                    topic = message[0].decode('utf-8')
                    data = json.loads(message[1].decode('utf-8'))
                    
                    logger.info(f"Received message on topic: {topic}")
                    
                    # 处理策略消息
                    if topic == "optimizer.pool.trading":
                        await self._process_strategy_message(data)
                        
            except zmq.Again:
                # 没有消息，继续等待
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)
    
    async def _process_strategy_message(self, data: Dict[str, Any]):
        """处理策略消息"""
        try:
            # 验证消息格式
            required_fields = ['strategy_id', 'strategy_name', 'parameters', 'expected_return', 'risk_level']
            if not all(field in data for field in required_fields):
                logger.warning(f"Invalid strategy message format: {data}")
                return
            
            # 创建策略审核记录
            strategy_review = StrategyReview(
                id=str(uuid.uuid4()),
                strategy_id=data['strategy_id'],
                strategy_name=data['strategy_name'],
                strategy_type=data.get('strategy_type', 'unknown'),
                parameters=json.dumps(data['parameters']),
                expected_return=float(data['expected_return']),
                risk_level=data['risk_level'],
                max_drawdown=float(data.get('max_drawdown', 0.0)),
                status='pending',
                raw_data=json.dumps(data),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 保存到数据库
            if self.review_service:
                success = await self.review_service.create_strategy_review(strategy_review)
                if success:
                    logger.info(f"Strategy review created: {strategy_review.id}")
                    
                    # 执行自动审核规则
                    await self.review_service.apply_auto_review_rules(strategy_review)
                else:
                    logger.error(f"Failed to create strategy review for: {data['strategy_id']}")
            
        except Exception as e:
            logger.error(f"Error processing strategy message: {e}")
    
    async def publish_approved_strategy(self, strategy_review: StrategyReview, decision_data: Dict[str, Any], report_data: Optional[Dict[str, Any]] = None):
        """发布已批准的策略到下游模组"""
        try:
            if not self.publisher or not self.is_running:
                logger.warning("Publisher not available")
                return False
            
            # 构造发布消息
            message_data = {
                'strategy_id': strategy_review.strategy_id,
                'strategy_name': strategy_review.strategy_name,
                'strategy_type': strategy_review.strategy_type,
                'parameters': json.loads(strategy_review.parameters) if strategy_review.parameters else {},
                'expected_return': strategy_review.expected_return,
                'risk_level': strategy_review.risk_level,
                'max_drawdown': strategy_review.max_drawdown,
                'review_decision': decision_data,
                'approved_at': datetime.now().isoformat(),
                'reviewer_id': decision_data.get('reviewer_id'),
                'approval_reason': decision_data.get('reason')
            }

            # 可选附加三页式报告
            if report_data:
                message_data['review_report'] = report_data.get('report')
                message_data['review_report_html'] = report_data.get('report_html')
            
            # 发布消息
            topic = "reviewguard.pool.approved"
            message = [
                topic.encode('utf-8'),
                json.dumps(message_data).encode('utf-8')
            ]
            
            await self.publisher.send_multipart(message)
            logger.info(f"Published approved strategy: {strategy_review.strategy_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing approved strategy: {e}")
            return False
    
    async def publish_rejected_strategy(self, strategy_review: StrategyReview, decision_data: Dict[str, Any]):
        """发布被拒绝的策略通知"""
        try:
            if not self.publisher or not self.is_running:
                logger.warning("Publisher not available")
                return False
            
            # 构造拒绝通知消息
            message_data = {
                'strategy_id': strategy_review.strategy_id,
                'strategy_name': strategy_review.strategy_name,
                'rejection_reason': decision_data.get('reason', 'No reason provided'),
                'risk_level': strategy_review.risk_level,
                'rejected_at': datetime.now().isoformat(),
                'reviewer_id': decision_data.get('reviewer_id')
            }
            
            # 发布到拒绝通知主题
            topic = "review.pool.rejected"
            message = [
                topic.encode('utf-8'),
                json.dumps(message_data).encode('utf-8')
            ]
            
            await self.publisher.send_multipart(message)
            logger.info(f"Published rejected strategy notification: {strategy_review.strategy_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing rejected strategy: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            'is_running': self.is_running,
            'subscriber_connected': self.subscriber is not None,
            'publisher_connected': self.publisher is not None,
            'sub_endpoint': self.sub_endpoint,
            'pub_endpoint': self.pub_endpoint
        }

    class _PublisherAdapter:
        """对外暴露的发布器适配器，提供同步的 send_message 接口"""
        def __init__(self, service: 'ZMQService'):
            self._service = service

        def send_message(self, topic: str, payload: Dict[str, Any]) -> bool:
            """同步方法：封装异步发送，多数测试使用同步断言此调用是否发生"""
            try:
                if not self._service.publisher or not self._service.is_running:
                    logger.warning("Publisher not available")
                    return False
                message = [topic.encode('utf-8'), json.dumps(payload).encode('utf-8')]
                coro = self._service.publisher.send_multipart(message)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    # 无运行中的事件循环，直接运行一次
                    asyncio.run(coro)
                return True
            except Exception as e:
                logger.error(f"Adapter send_message error: {e}")
                return False

    def get_publisher(self):
        """提供一个带有 send_message(topic, payload) 方法的发布器，兼容测试桩"""
        return ZMQService._PublisherAdapter(self)