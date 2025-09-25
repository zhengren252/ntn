#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroMQ 通信客户端
NeuroTrade Nexus (NTN) - ZeroMQ Communication Client

核心功能：
1. 订阅交易机会消息 (scanner.pool.preliminary)
2. 发布策略参数包 (optimizer.pool.trading)
3. 消息序列化/反序列化
4. 连接管理和重连机制
5. 消息队列缓冲
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    import zmq
    import zmq.asyncio
except ImportError:
    logging.warning("ZeroMQ未安装，将使用模拟通信客户端")
    zmq = None


@dataclass
class ZMQConnectionConfig:
    """ZeroMQ连接配置"""

    subscriber_address: str = "tcp://localhost:5555"
    publisher_address: str = "tcp://localhost:5556"
    subscribe_topics: List[str] = field(
        default_factory=lambda: ["scanner.pool.preliminary"]
    )
    publish_topic: str = "optimizer.pool.trading"
    max_buffer_size: int = 1000
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10


@dataclass
class ZMQConnectionState:
    """ZeroMQ连接状态"""

    context: Optional[zmq.asyncio.Context] = None
    subscriber: Optional[zmq.asyncio.Socket] = None
    publisher: Optional[zmq.asyncio.Socket] = None
    is_connected: bool = False
    is_running: bool = False
    message_handlers: Dict[str, Callable] = field(default_factory=dict)
    message_buffer: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ZMQStats:
    """ZeroMQ统计信息"""

    messages_received: int = 0
    messages_sent: int = 0
    connection_errors: int = 0
    last_message_time: Optional[str] = None


@dataclass
class TradingOpportunity:
    """交易机会数据结构"""

    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'NEUTRAL'
    confidence: float
    price: float
    volume: float
    timestamp: str
    source: str  # 来源模组
    metadata: Dict[str, Any]
    analysis_period: Dict[str, str]  # {"start": "2024-01-01", "end": "2024-12-31"}
    market_context: Dict[str, Any]  # 市场环境上下文信息
    strategy_type: str = "momentum"  # 策略类型


@dataclass
class StrategyPackage:
    """策略参数包数据结构"""

    strategy_id: str
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    position_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    parameters: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    timestamp: str
    source: str = "optimizer"


class ZMQClient:
    """
    ZeroMQ 通信客户端

    实现NeuroTrade Nexus规范：
    - 微服务间消息通信
    - 异步消息处理
    - 自动重连机制
    - 消息缓冲队列
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)

        # 初始化配置
        self.config = ZMQConnectionConfig(
            subscriber_address=config.get("subscriber_address", "tcp://localhost:5555"),
            publisher_address=config.get("publisher_address", "tcp://localhost:5556"),
            subscribe_topics=config.get(
                "subscribe_topics", ["scanner.pool.preliminary"]
            ),
            publish_topic=config.get("publish_topic", "optimizer.pool.trading"),
            max_buffer_size=config.get("max_buffer_size", 1000),
            reconnect_interval=config.get("reconnect_interval", 5),
            max_reconnect_attempts=config.get("max_reconnect_attempts", 10),
        )

        # 初始化连接状态
        self.state = ZMQConnectionState()

        # 初始化统计信息
        self.stats = ZMQStats()

    async def initialize(self):
        """
        初始化ZeroMQ客户端
        """
        self.logger.info("正在初始化ZeroMQ客户端...")

        if zmq is None:
            self.logger.warning("ZeroMQ不可用，使用模拟模式")
            return

        try:
            # 创建ZeroMQ上下文
            self.state.context = zmq.asyncio.Context()

            # 创建订阅者套接字
            self.state.subscriber = self.state.context.socket(zmq.SUB)
            self.state.subscriber.connect(self.config.subscriber_address)

            # 订阅主题
            for topic in self.config.subscribe_topics:
                self.state.subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
                self.logger.info("订阅主题: %s", topic)

            # 创建发布者套接字
            self.state.publisher = self.state.context.socket(zmq.PUB)
            self.state.publisher.connect(self.config.publisher_address)

            # 等待连接建立
            await asyncio.sleep(1)

            self.state.is_connected = True
            self.logger.info("ZeroMQ客户端初始化完成")

        except (ConnectionError, ImportError, AttributeError, OSError) as e:
            self.logger.error("ZeroMQ客户端初始化失败: %s", e)
            self.stats.connection_errors += 1
            raise

    async def start(self):
        """
        启动消息处理循环
        """
        if not self.state.is_connected:
            await self.initialize()

        self.state.is_running = True
        self.logger.info("启动ZeroMQ消息处理循环")

        # 启动消息接收任务
        asyncio.create_task(self._message_receiver_loop())

        # 启动连接监控任务
        asyncio.create_task(self._connection_monitor_loop())

    async def stop(self):
        """
        停止消息处理
        """
        self.logger.info("停止ZeroMQ消息处理")
        self.state.is_running = False

        if self.state.subscriber:
            self.state.subscriber.close()

        if self.state.publisher:
            self.state.publisher.close()

        if self.state.context:
            self.state.context.term()

        self.state.is_connected = False

    def register_handler(self, topic: str, handler: Callable):
        """
        注册消息处理器

        Args:
            topic: 消息主题
            handler: 处理函数
        """
        self.state.message_handlers[topic] = handler
        self.logger.info("注册消息处理器: %s", topic)

    async def publish_strategy_package(self, strategy_package: StrategyPackage):
        """
        发布策略参数包

        Args:
            strategy_package: 策略参数包
        """
        try:
            # 序列化消息
            message_data = asdict(strategy_package)
            message_json = json.dumps(message_data, ensure_ascii=False)

            # 构造完整消息
            topic = self.config.publish_topic
            full_message = f"{topic} {message_json}"

            if self.state.publisher and self.state.is_connected:
                # 发送消息
                await self.state.publisher.send_string(full_message)
                self.stats.messages_sent += 1

                self.logger.debug(
                    "发布策略包: %s - %s", strategy_package.symbol, strategy_package.action
                )

            else:
                # 缓存消息
                self._buffer_message(topic, message_data)
                self.logger.warning("ZeroMQ未连接，消息已缓存")

        except (ConnectionError, RuntimeError, AttributeError) as e:
            self.logger.error("发布策略包失败: %s", e)
            self._buffer_message(self.config.publish_topic, asdict(strategy_package))

    async def _message_receiver_loop(self):
        """
        消息接收循环
        """
        while self.state.is_running:
            try:
                if not self.state.subscriber or not self.state.is_connected:
                    await asyncio.sleep(1)
                    continue

                # 非阻塞接收消息
                try:
                    message = await asyncio.wait_for(
                        self.state.subscriber.recv_string(zmq.NOBLOCK), timeout=1.0
                    )

                    await self._process_received_message(message)

                except asyncio.TimeoutError:
                    continue
                except zmq.Again:
                    continue

            except (ConnectionError, RuntimeError, OSError) as e:
                self.logger.error("消息接收错误: %s", e)
                self.stats.connection_errors += 1
                await asyncio.sleep(self.config.reconnect_interval)

    async def _process_received_message(self, message: str):
        """
        处理接收到的消息

        Args:
            message: 原始消息字符串
        """
        try:
            # 解析消息
            parts = message.split(" ", 1)
            if len(parts) != 2:
                self.logger.warning("消息格式错误: %s", message)
                return

            topic, data_json = parts
            data = json.loads(data_json)

            # 更新统计
            self.stats.messages_received += 1
            self.stats.last_message_time = datetime.now().isoformat()

            # 处理交易机会消息
            if topic in self.config.subscribe_topics:
                trading_opportunity = TradingOpportunity(**data)

                # 调用注册的处理器
                if topic in self.state.message_handlers:
                    await self.state.message_handlers[topic](trading_opportunity)
                else:
                    self.logger.debug("收到消息但无处理器: %s", topic)

                self.logger.debug(
                    "处理交易机会: %s - %s",
                    trading_opportunity.symbol,
                    trading_opportunity.signal_type,
                )

        except (ValueError, AttributeError, RuntimeError) as e:
            self.logger.error("消息处理失败: %s", e)

    async def _connection_monitor_loop(self):
        """
        连接监控循环
        """
        reconnect_attempts = 0

        while self.state.is_running:
            try:
                if (
                    not self.state.is_connected
                    and reconnect_attempts < self.config.max_reconnect_attempts
                ):
                    self.logger.info(
                        "尝试重连 ZeroMQ (%s/%s)",
                        reconnect_attempts + 1,
                        self.config.max_reconnect_attempts,
                    )

                    try:
                        await self.initialize()
                        reconnect_attempts = 0

                        # 发送缓存的消息
                        await self._flush_message_buffer()

                    except (ConnectionError, OSError, RuntimeError) as e:
                        self.logger.warning("重连失败: %s", e)
                        reconnect_attempts += 1

                await asyncio.sleep(self.config.reconnect_interval)

            except (RuntimeError, OSError) as e:
                self.logger.error("连接监控错误: %s", e)
                await asyncio.sleep(self.config.reconnect_interval)

    def _buffer_message(self, topic: str, data: Dict[str, Any]):
        """
        缓存消息

        Args:
            topic: 消息主题
            data: 消息数据
        """
        if len(self.state.message_buffer) >= self.config.max_buffer_size:
            # 移除最旧的消息
            self.state.message_buffer.pop(0)

        self.state.message_buffer.append(
            {"topic": topic, "data": data, "timestamp": datetime.now().isoformat()}
        )

    async def _flush_message_buffer(self):
        """
        发送缓存的消息
        """
        if not self.state.message_buffer:
            return

        self.logger.info("发送 %s 条缓存消息", len(self.state.message_buffer))

        for buffered_message in self.state.message_buffer.copy():
            try:
                topic = buffered_message["topic"]
                data = buffered_message["data"]

                message_json = json.dumps(data, ensure_ascii=False)
                full_message = f"{topic} {message_json}"

                if self.state.publisher and self.state.is_connected:
                    await self.state.publisher.send_string(full_message)
                    self.state.message_buffer.remove(buffered_message)
                    self.stats.messages_sent += 1

            except (ConnectionError, RuntimeError, OSError) as e:
                self.logger.error("发送缓存消息失败: %s", e)
                break

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "messages_received": self.stats.messages_received,
            "messages_sent": self.stats.messages_sent,
            "connection_errors": self.stats.connection_errors,
            "last_message_time": self.stats.last_message_time,
            "is_connected": self.state.is_connected,
            "is_running": self.state.is_running,
            "buffer_size": len(self.state.message_buffer),
            "subscribed_topics": self.config.subscribe_topics,
            "publish_topic": self.config.publish_topic,
        }


class MockZMQClient(ZMQClient):
    """
    模拟ZeroMQ客户端（用于测试和开发）
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_messages = []

    async def initialize(self):
        """模拟初始化"""
        self.logger.info("初始化模拟ZeroMQ客户端")
        self.state.is_connected = True

    async def start(self):
        """模拟启动"""
        self.state.is_running = True
        self.logger.info("启动模拟ZeroMQ客户端")

        # 启动模拟消息生成
        asyncio.create_task(self._generate_mock_messages())

    async def stop(self):
        """模拟停止"""
        self.state.is_running = False
        self.state.is_connected = False
        self.logger.info("停止模拟ZeroMQ客户端")

    async def publish_strategy_package(self, strategy_package: StrategyPackage):
        """模拟发布策略包"""
        self.mock_messages.append(
            {
                "type": "strategy_package",
                "data": asdict(strategy_package),
                "timestamp": datetime.now().isoformat(),
            }
        )

        self.stats.messages_sent += 1
        self.logger.debug(f"模拟发布策略包: {strategy_package.symbol}")

    async def _generate_mock_messages(self):
        """生成模拟交易机会消息"""
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        signal_types = ["BUY", "SELL", "NEUTRAL"]

        while self.state.is_running:
            try:
                # 生成模拟交易机会
                import random

                opportunity = TradingOpportunity(
                    symbol=random.choice(symbols),
                    signal_type=random.choice(signal_types),
                    confidence=random.uniform(0.6, 0.95),
                    price=random.uniform(100, 50000),
                    volume=random.uniform(1000, 100000),
                    timestamp=datetime.now().isoformat(),
                    source="scanner",
                    metadata={"test": True},
                )

                # 调用处理器
                for topic, handler in self.state.message_handlers.items():
                    if "scanner" in topic:
                        await handler(opportunity)

                self.stats.messages_received += 1
                self.stats.last_message_time = datetime.now().isoformat()

                # 等待30秒再生成下一条消息
                await asyncio.sleep(30)

            except (RuntimeError, ValueError) as e:
                self.logger.error("生成模拟消息失败: %s", e)
                await asyncio.sleep(5)


def create_zmq_client(config: Dict[str, Any]) -> ZMQClient:
    """
    创建ZeroMQ客户端

    Args:
        config: 配置字典

    Returns:
        ZeroMQ客户端实例
    """
    # 检查是否强制使用Mock模式（用于测试）
    use_mock = config.get("use_mock", False)

    if zmq is None or use_mock:
        return MockZMQClient(config)
    else:
        return ZMQClient(config)
