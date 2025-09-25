#!/usr/bin/env python3
"""
测试总控模块订阅功能
"""

import zmq
import zmq.asyncio
import json
import asyncio
import logging
from datetime import datetime
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_master_control_subscription():
    """测试总控模块订阅功能"""
    settings = get_settings()
    context = zmq.asyncio.Context()
    
    # 发布者 - 模拟风控模块
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://*:5795")  # risk_management模组发布端口
    
    # 订阅者 - 模拟总控模块的订阅逻辑
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, b"")  # 订阅所有消息
    
    # 连接到所有模组端口（模拟总控模块的连接逻辑）
    logger.info(f"总控模块订阅端口列表: {settings.zmq_sub_ports}")
    for port in settings.zmq_sub_ports:
        subscriber.connect(f"tcp://localhost:{port}")
        logger.info(f"连接到端口: {port}")
    
    # 等待连接建立
    await asyncio.sleep(3)
    
    # 发送测试警报
    test_alert = {
        "alert_id": "TEST_002",
        "alert_type": "BLACK_SWAN",
        "severity": "CRITICAL",
        "timestamp": datetime.now().isoformat(),
        "source": "risk_control_simulator",
        "description": "检测到LUNA代币崩盘，市场出现系统性风险",
        "recommended_action": "EMERGENCY_SHUTDOWN",
        "type": "alert"  # 添加消息类型
    }
    
    logger.info("发送黑天鹅警报到risk.alerts主题...")
    await publisher.send_multipart([
        b"risk.alerts",
        json.dumps(test_alert, ensure_ascii=False).encode('utf-8')
    ])
    
    # 尝试接收消息
    logger.info("等待总控模块接收消息...")
    try:
        message = await asyncio.wait_for(
            subscriber.recv_multipart(), 
            timeout=10.0
        )
        topic = message[0].decode('utf-8')
        data = json.loads(message[1].decode('utf-8'))
        logger.info(f"✓ 总控模块收到消息: {topic} - {data.get('alert_type')} - {data.get('severity')}")
        
        # 检查是否应该触发紧急停机
        if data.get('severity') == 'CRITICAL' and data.get('alert_type') == 'BLACK_SWAN':
            logger.info("✓ 满足紧急停机条件")
        
        return True
    except asyncio.TimeoutError:
        logger.error("✗ 超时：总控模块未收到消息")
        return False
    finally:
        publisher.close()
        subscriber.close()
        context.term()

if __name__ == "__main__":
    result = asyncio.run(test_master_control_subscription())
    if result:
        print("✓ 总控模块订阅测试成功")
    else:
        print("✗ 总控模块订阅测试失败")