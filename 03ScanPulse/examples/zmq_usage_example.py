#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZeroMQ客户端使用示例
演示如何使用扫描器模组的ZMQ通信功能
"""

import asyncio
import time
import json
from typing import Dict, Any
from scanner.communication.zmq_client import (
    ScannerZMQClient,
    MessageType,
    create_scanner_zmq_client,
    create_zmq_publisher,
    create_zmq_subscriber,
    get_connection_pool,
)
from scanner.utils.logger import get_logger

logger = get_logger(__name__)


def example_message_handler(topic: str, payload: Dict[str, Any]) -> None:
    """
    示例消息处理器
    处理接收到的ZMQ消息
    """
    logger.info("Received message", topic=topic, payload=payload)

    # 根据消息类型处理
    if "news" in topic:
        handle_news_message(payload)
    elif "status" in topic:
        handle_status_message(payload)
    else:
        logger.debug("Unknown message type", topic=topic)


def handle_news_message(payload: Dict[str, Any]) -> None:
    """
    处理新闻消息
    """
    news_type = payload.get("type")
    symbol = payload.get("symbol")
    content = payload.get("content")

    logger.info("Processing news", type=news_type, symbol=symbol, content=content)

    # 这里可以添加具体的新闻处理逻辑
    # 例如：触发黑马检测、更新市场数据等


def handle_status_message(payload: Dict[str, Any]) -> None:
    """
    处理状态消息
    """
    status = payload.get("status")
    timestamp = payload.get("timestamp")

    logger.info("Processing status update", status=status, timestamp=timestamp)


def example_request_handler(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    示例请求处理器
    处理REQ/REP模式的请求
    """
    logger.info("Processing request", request=request_data)

    request_type = request_data.get("type")

    if request_type == "scan_status":
        return {
            "success": True,
            "status": "running",
            "last_scan": "2024-01-15T10:30:00Z",
            "processed_count": 1250,
        }
    elif request_type == "get_opportunities":
        return {
            "success": True,
            "opportunities": [
                {
                    "symbol": "RNDR/USDT",
                    "score": 92,
                    "type": "black_horse",
                    "reason": "Coinbase listing announcement",
                },
                {
                    "symbol": "SOL/USDT",
                    "score": 85,
                    "type": "three_high",
                    "reason": "High volatility and volume",
                },
            ],
        }
    else:
        return {"success": False, "error": f"Unknown request type: {request_type}"}


def example_publisher():
    """
    发布者示例
    演示如何发布消息
    """
    logger.info("Starting publisher example")

    # 创建发布者
    publisher = create_zmq_publisher(host="localhost", port=5555, bind=True)

    if not publisher.connect():
        logger.error("Failed to connect publisher")
        return

    # 启动心跳
    publisher.start_heartbeat()

    try:
        # 发布交易机会
        opportunity_data = {
            "symbol": "RNDR/USDT",
            "source": "scanner",
            "type": "black_horse",
            "score": 92,
            "timestamp": "2024-01-15T10:30:00Z",
            "details": {
                "reason": "Coinbase listing announcement",
                "volume_24h": 15000000,
                "price_change_24h": 0.15,
                "market_cap": 500000000,
            },
        }

        success = publisher.publish_opportunity(opportunity_data)
        logger.info("Published opportunity", success=success)

        # 发布状态更新
        status_data = {
            "status": "running",
            "last_scan": "2024-01-15T10:30:00Z",
            "processed_count": 1250,
            "active_rules": ["three_high", "black_horse", "potential_gems"],
        }

        success = publisher.publish_status(status_data)
        logger.info("Published status", success=success)

        # 等待一段时间让消息发送
        time.sleep(2)

    finally:
        publisher.disconnect()
        logger.info("Publisher disconnected")


def example_subscriber():
    """
    订阅者示例
    演示如何订阅和处理消息
    """
    logger.info("Starting subscriber example")

    # 创建订阅者
    subscriber = create_zmq_subscriber(
        host="localhost", port=5556, topics=["crawler.news", "scanner.status"]
    )

    if not subscriber.connect():
        logger.error("Failed to connect subscriber")
        return

    # 添加消息处理器
    subscriber.add_message_handler("crawler.news", example_message_handler)
    subscriber.add_message_handler("scanner.status", example_message_handler)

    # 开始监听
    if not subscriber.start_listening():
        logger.error("Failed to start listening")
        return

    try:
        # 运行一段时间
        logger.info("Subscriber listening for 10 seconds...")
        time.sleep(10)

    finally:
        subscriber.disconnect()
        logger.info("Subscriber disconnected")


def example_request_reply():
    """
    请求-响应示例
    演示REQ/REP通信模式
    """
    logger.info("Starting request-reply example")

    # 配置
    config = {"host": "localhost", "request_port": 5557, "reply_port": 5558}

    # 创建扫描器ZMQ客户端
    client = create_scanner_zmq_client(config)

    # 初始化请求客户端和响应服务器
    if not client.initialize_request_client():
        logger.error("Failed to initialize request client")
        return

    if not client.initialize_reply_server(example_request_handler):
        logger.error("Failed to initialize reply server")
        return

    try:
        # 发送请求
        request_data = {"type": "scan_status"}
        response = client.send_request(request_data, timeout=5000)
        logger.info("Request response", response=response)

        # 发送另一个请求
        request_data = {"type": "get_opportunities"}
        response = client.send_request(request_data, timeout=5000)
        logger.info("Opportunities response", response=response)

    finally:
        client.shutdown()
        logger.info("Request-reply example completed")


def example_scanner_client():
    """
    完整的扫描器客户端示例
    演示如何使用ScannerZMQClient
    """
    logger.info("Starting scanner client example")

    # 配置
    config = {
        "host": "localhost",
        "publisher_port": 5555,
        "subscriber_port": 5556,
        "topics": {
            "publish": "scanner.pool.preliminary",
            "subscribe": ["crawler.news", "api.market_data"],
        },
    }

    # 创建扫描器客户端
    scanner_client = create_scanner_zmq_client(config)

    try:
        # 初始化发布者和订阅者
        if not scanner_client.initialize_publisher():
            logger.error("Failed to initialize publisher")
            return

        if not scanner_client.initialize_subscriber():
            logger.error("Failed to initialize subscriber")
            return

        # 添加消息处理器
        scanner_client.add_message_handler("crawler.news", example_message_handler)
        scanner_client.add_message_handler("api.market_data", example_message_handler)

        # 开始监听
        if not scanner_client.start_subscriber():
            logger.error("Failed to start subscriber")
            return

        # 发布一些测试消息
        for i in range(3):
            opportunity = {
                "symbol": f"TEST{i}/USDT",
                "score": 80 + i * 5,
                "type": "test",
                "timestamp": time.time(),
            }

            success = scanner_client.publish_opportunity(opportunity)
            logger.info(f"Published test opportunity {i}", success=success)
            time.sleep(1)

        # 获取统计信息
        stats = scanner_client.get_stats()
        logger.info("Client statistics", stats=stats)

        # 检查健康状态
        healthy = scanner_client.is_healthy()
        logger.info("Client health status", healthy=healthy)

        # 运行一段时间
        logger.info("Running for 5 seconds...")
        time.sleep(5)

    finally:
        scanner_client.shutdown()
        logger.info("Scanner client example completed")


def example_connection_pool():
    """
    连接池示例
    演示如何使用连接池管理连接
    """
    logger.info("Starting connection pool example")

    # 获取连接池
    pool = get_connection_pool(max_connections=5)

    try:
        # 创建多个连接
        configs = [
            {"host": "localhost", "port": 5555, "bind": True},
            {"host": "localhost", "port": 5556, "bind": False, "topics": ["test"]},
            {"host": "localhost", "port": 5557, "bind": False},
        ]

        from scanner.communication.zmq_client import CommunicationMode

        modes = [
            CommunicationMode.PUBLISHER,
            CommunicationMode.SUBSCRIBER,
            CommunicationMode.REQUEST,
        ]

        connections = []
        for i, (config, mode) in enumerate(zip(configs, modes)):
            conn_id = f"conn_{i}"
            connection = pool.get_connection(conn_id, config, mode)
            if connection:
                connections.append((conn_id, connection))
                logger.info(f"Created connection {conn_id}", mode=mode.value)

        # 获取连接池统计
        stats = pool.get_stats()
        logger.info("Connection pool stats", stats=stats)

        # 释放连接
        for conn_id, _ in connections:
            pool.release_connection(conn_id)
            logger.info(f"Released connection {conn_id}")

    finally:
        pool.close_all()
        logger.info("Connection pool example completed")


if __name__ == "__main__":
    # 设置日志
    import logging

    logging.basicConfig(level=logging.INFO)

    logger.info("Starting ZMQ usage examples")

    try:
        # 运行各种示例
        logger.info("=== Publisher Example ===")
        example_publisher()

        logger.info("=== Subscriber Example ===")
        example_subscriber()

        logger.info("=== Request-Reply Example ===")
        example_request_reply()

        logger.info("=== Scanner Client Example ===")
        example_scanner_client()

        logger.info("=== Connection Pool Example ===")
        example_connection_pool()

    except KeyboardInterrupt:
        logger.info("Examples interrupted by user")
    except Exception as e:
        logger.error("Error in examples", error=str(e))
    finally:
        # 清理连接池
        from scanner.communication.zmq_client import cleanup_connection_pool

        cleanup_connection_pool()
        logger.info("ZMQ usage examples completed")
