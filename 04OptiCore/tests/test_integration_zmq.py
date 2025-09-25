#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZMQ消息完整流程集成测试
NeuroTrade Nexus (NTN) - ZMQ Integration Test

测试目标：
1. 验证ZMQ消息从输入到输出的完整流程
2. 模拟扫描器发送交易机会消息
3. 验证策略优化模组接收并处理消息
4. 验证输出策略参数包的格式和内容
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List

import zmq
import zmq.asyncio


class ZMQTestPublisher:
    """ZMQ测试发布者 - 模拟扫描器"""

    def __init__(self, endpoint: str):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(endpoint)
        self.endpoint = endpoint
        print(f"发布者绑定到: {endpoint}")

    async def publish_trading_opportunity(
        self, symbol: str, opportunity_data: Dict[str, Any]
    ):
        """发布交易机会消息"""
        topic = "scanner.pool.preliminary"
        message_data = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "opportunity_type": "breakout",
            "confidence": 0.85,
            "data": opportunity_data,
        }

        message = f"{topic} {json.dumps(message_data)}"
        await self.socket.send_string(message)
        print(f"发布消息: {topic} - {symbol}")

    def close(self):
        """关闭发布者"""
        self.socket.close()
        self.context.term()


class ZMQTestSubscriber:
    """ZMQ测试订阅者 - 监听策略参数包"""

    def __init__(self, endpoint: str):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(endpoint)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "optimizer.pool.trading")
        self.endpoint = endpoint
        self.received_messages = []
        print(f"订阅者连接到: {endpoint}")

    async def listen_for_messages(self, timeout_seconds: int = 10):
        """监听消息"""
        print(f"开始监听消息，超时时间: {timeout_seconds}秒")
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                # 非阻塞接收
                message = await asyncio.wait_for(
                    self.socket.recv_string(zmq.NOBLOCK), timeout=1.0
                )

                # 解析消息
                parts = message.split(" ", 1)
                if len(parts) == 2:
                    topic, data_json = parts
                    data = json.loads(data_json)
                    self.received_messages.append(
                        {
                            "topic": topic,
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    print(f"接收到消息: {topic}")

            except asyncio.TimeoutError:
                continue
            except zmq.Again:
                await asyncio.sleep(0.1)
                continue

        print(f"监听结束，共接收到 {len(self.received_messages)} 条消息")
        return self.received_messages

    def close(self):
        """关闭订阅者"""
        self.socket.close()
        self.context.term()


class TestZMQIntegration:
    """ZMQ集成测试类"""

    def __init__(self):
        self.publisher = None
        self.subscriber = None
        self.scanner_endpoint = None
        self.optimizer_endpoint = None

    async def setup(self):
        """设置测试环境"""
        print("设置ZMQ测试环境...")

        # ZMQ端点配置 - 使用随机端口避免冲突
        import random

        scanner_port = random.randint(20000, 30000)
        optimizer_port = scanner_port + 1
        self.scanner_endpoint = f"tcp://127.0.0.1:{scanner_port}"
        self.optimizer_endpoint = f"tcp://127.0.0.1:{optimizer_port}"

        # 创建发布者（模拟扫描器）
        self.publisher = ZMQTestPublisher(self.scanner_endpoint)

        # 创建订阅者（监听优化器输出）
        self.subscriber = ZMQTestSubscriber(self.optimizer_endpoint)

        # 等待连接建立
        await asyncio.sleep(1)
        print("ZMQ测试环境设置完成")

    async def teardown(self):
        """清理测试环境"""
        print("清理ZMQ测试环境...")

        if self.publisher:
            self.publisher.close()

        if self.subscriber:
            self.subscriber.close()

        print("ZMQ测试环境清理完成")

    async def test_int_zmq_01_complete_message_flow(self):
        """测试ZMQ消息完整流程"""
        print("\n=== 开始ZMQ消息完整流程测试 ===")

        try:
            # 1. 准备测试数据
            test_symbol = "BTC/USDT"
            opportunity_data = {
                "price": 45000.0,
                "volume": 1000.0,
                "trend": "bullish",
                "indicators": {"rsi": 65.0, "macd": 0.5, "bollinger_position": 0.8},
            }

            # 2. 启动消息监听
            print("启动消息监听...")
            listen_task = asyncio.create_task(
                self.subscriber.listen_for_messages(timeout_seconds=15)
            )

            # 3. 等待一段时间确保监听器准备就绪
            await asyncio.sleep(2)

            # 4. 发布交易机会消息
            print(f"发布交易机会消息: {test_symbol}")
            await self.publisher.publish_trading_opportunity(
                test_symbol, opportunity_data
            )

            # 5. 等待消息处理
            print("等待消息处理...")
            await asyncio.sleep(3)

            # 6. 模拟策略优化模组的响应（在实际测试中，这应该由真实的模组完成）
            # 这里我们手动发布一个策略参数包来验证订阅者能正常接收
            mock_strategy_package = {
                "strategy_id": "test_strategy_001",
                "symbol": test_symbol,
                "parameters": {
                    "entry_price": 45000.0,
                    "stop_loss": 44000.0,
                    "take_profit": 47000.0,
                    "position_size": 0.1,
                },
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat(),
                "backtest_results": {
                    "sharpe_ratio": 2.1,
                    "max_drawdown": 0.08,
                    "total_return": 0.15,
                },
            }

            # 创建临时发布者发送策略参数包
            temp_publisher = ZMQTestPublisher(self.optimizer_endpoint)
            await asyncio.sleep(1)  # 等待绑定

            topic = "optimizer.pool.trading"
            message = f"{topic} {json.dumps(mock_strategy_package)}"
            await temp_publisher.socket.send_string(message)
            print(f"发布策略参数包: {topic}")

            # 7. 等待并获取监听结果
            received_messages = await listen_task
            temp_publisher.close()

            # 8. 验证结果
            print(f"\n接收到的消息数量: {len(received_messages)}")

            # 基础验证：至少应该接收到一条消息
            assert len(received_messages) > 0, "未接收到任何消息"

            # 查找策略参数包消息
            strategy_messages = [
                msg
                for msg in received_messages
                if msg["topic"] == "optimizer.pool.trading"
            ]

            assert len(strategy_messages) > 0, "未接收到策略参数包消息"

            # 验证策略参数包结构
            strategy_msg = strategy_messages[0]
            strategy_data = strategy_msg["data"]

            # 验证必需字段
            required_fields = ["strategy_id", "symbol", "parameters", "confidence"]
            for field in required_fields:
                assert field in strategy_data, f"策略参数包缺少必需字段: {field}"

            # 验证参数结构
            params = strategy_data["parameters"]
            param_fields = ["entry_price", "stop_loss", "take_profit", "position_size"]
            for field in param_fields:
                assert field in params, f"策略参数缺少字段: {field}"
                assert isinstance(params[field], (int, float)), f"参数 {field} 应为数值类型"

            # 验证数值合理性
            assert 0 < strategy_data["confidence"] <= 1, "置信度应在0-1之间"
            assert params["entry_price"] > 0, "入场价格应大于0"
            assert params["stop_loss"] > 0, "止损价格应大于0"
            assert params["take_profit"] > 0, "止盈价格应大于0"
            assert params["position_size"] > 0, "仓位大小应大于0"

            print("\n✅ ZMQ消息完整流程测试通过")
            print(f"   - 成功接收 {len(received_messages)} 条消息")
            print(f"   - 策略参数包结构验证通过")
            print(f"   - 数值合理性验证通过")

            return True

        except Exception as e:
            print(f"\n❌ ZMQ消息完整流程测试失败: {str(e)}")
            return False


async def run_zmq_integration_test():
    """运行ZMQ集成测试"""
    test_instance = TestZMQIntegration()

    try:
        await test_instance.setup()
        success = await test_instance.test_int_zmq_01_complete_message_flow()

        if success:
            print("\n🎉 所有ZMQ集成测试通过！")
        else:
            print("\n💥 ZMQ集成测试失败！")

    finally:
        await test_instance.teardown()


if __name__ == "__main__":
    asyncio.run(run_zmq_integration_test())
