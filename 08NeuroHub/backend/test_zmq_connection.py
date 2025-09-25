#!/usr/bin/env python3
"""
测试ZMQ连接 - 验证风控模拟器和总控模块之间的通信
"""

import zmq
import zmq.asyncio
import json
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_zmq_communication():
    """测试ZMQ通信"""
    context = zmq.asyncio.Context()
    
    # 发布者 - 模拟风控模块
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://*:5795")  # risk_management模组发布端口
    
    # 订阅者 - 模拟总控模块
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://localhost:5795")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"")  # 订阅所有消息
    
    # 等待连接建立
    await asyncio.sleep(2)
    
    # 发送测试消息
    test_alert = {
        "alert_id": "TEST_001",
        "alert_type": "BLACK_SWAN",
        "severity": "CRITICAL",
        "timestamp": datetime.now().isoformat(),
        "source": "test_simulator",
        "description": "测试黑天鹅事件",
        "recommended_action": "EMERGENCY_SHUTDOWN"
    }
    
    logger.info("发送测试警报...")
    await publisher.send_multipart([
        b"risk.alerts",
        json.dumps(test_alert, ensure_ascii=False).encode('utf-8')
    ])
    
    # 尝试接收消息
    logger.info("等待接收消息...")
    try:
        message = await asyncio.wait_for(
            subscriber.recv_multipart(zmq.NOBLOCK), 
            timeout=5.0
        )
        topic = message[0].decode('utf-8')
        data = json.loads(message[1].decode('utf-8'))
        logger.info(f"✓ 收到消息: {topic} - {data['alert_type']}")
        return True
    except asyncio.TimeoutError:
        logger.error("✗ 超时：未收到消息")
        return False
    except zmq.Again:
        logger.error("✗ 没有消息可接收")
        return False
    finally:
        publisher.close()
        subscriber.close()
        context.term()

if __name__ == "__main__":
    result = asyncio.run(test_zmq_communication())
    if result:
        print("✓ ZMQ通信测试成功")
    else:
        print("✗ ZMQ通信测试失败")