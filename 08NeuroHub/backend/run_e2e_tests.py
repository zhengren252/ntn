#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试脚本 - E2E-MASTER-01 全链路熔断协议验证

测试流程：
1. 模拟交易员持仓状态
2. 触发风控警报（黑天鹅事件）
3. 监控总控模块紧急停机指令
4. 验证持仓清空
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List

import aiohttp
import redis
import zmq
import zmq.asyncio

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class E2ETestRunner:
    """端到端测试运行器"""
    
    def __init__(self):
        self.redis_client = None
        self.zmq_context = None
        self.zmq_publisher = None
        self.zmq_subscriber = None
        self.api_base_url = "http://localhost:8000"
        self.test_results = []
        
    async def setup(self):
        """初始化测试环境"""
        logger.info("=== 初始化端到端测试环境 ===")
        
        # 连接Redis
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("✓ Redis连接成功")
        except Exception as e:
            logger.error(f"✗ Redis连接失败: {e}")
            raise
            
        # 初始化ZMQ
        try:
            self.zmq_context = zmq.asyncio.Context()
            
            # 发布者 - 模拟风控模块发送警报
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind("tcp://*:5795")  # 风控模块的发布端口
            
            # 订阅者 - 监听总控模块发出的指令
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect("tcp://localhost:5755")  # 总控模块的发布端口
            -        self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "command")
            +        self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "control.commands")
            logger.info("✓ ZMQ连接成功")
            await asyncio.sleep(1)  # 等待连接建立
        except Exception as e:
            logger.error(f"✗ ZMQ连接失败: {e}")
            raise
            
    async def cleanup(self):
        """清理测试环境"""
        logger.info("=== 清理测试环境 ===")
        
        if self.redis_client:
            # 清理测试数据
            test_keys = self.redis_client.keys("test:*")
            if test_keys:
                self.redis_client.delete(*test_keys)
            logger.info("✓ Redis测试数据已清理")
            
        if self.zmq_publisher:
            self.zmq_publisher.close()
        if self.zmq_subscriber:
            self.zmq_subscriber.close()
        if self.zmq_context:
            self.zmq_context.term()
        logger.info("✓ ZMQ连接已关闭")
        
    async def simulate_trader_positions(self) -> bool:
        """模拟交易员模块写入持仓状态"""
        logger.info("--- 步骤1: 模拟交易员持仓状态 ---")
        
        try:
            # 模拟持仓数据
            positions = {
                "BTC-USDT": {
                    "symbol": "BTC-USDT",
                    "side": "long",
                    "size": 1.5,
                    "entry_price": 45000.0,
                    "current_price": 44500.0,
                    "unrealized_pnl": -750.0,
                    "timestamp": datetime.now().isoformat()
                },
                "ETH-USDT": {
                    "symbol": "ETH-USDT",
                    "side": "short",
                    "size": 10.0,
                    "entry_price": 3200.0,
                    "current_price": 3150.0,
                    "unrealized_pnl": 500.0,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # 写入Redis
            for symbol, position in positions.items():
                key = f"positions:{symbol}"
                self.redis_client.hset(key, mapping=position)
                logger.info(f"✓ 写入持仓: {symbol} - {position['side']} {position['size']}")
                
            # 设置总持仓统计
            portfolio_stats = {
                "total_positions": len(positions),
                "total_unrealized_pnl": sum(p["unrealized_pnl"] for p in positions.values()),
                "last_update": datetime.now().isoformat()
            }
            self.redis_client.hset("portfolio:stats", mapping=portfolio_stats)
            logger.info(f"✓ 写入组合统计: {portfolio_stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 模拟持仓失败: {e}")
            return False
            
    async def trigger_risk_alert(self) -> bool:
        """触发风控警报 - 模拟黑天鹅事件"""
        logger.info("--- 步骤2: 触发风控警报 ---")
        
        try:
            # 构造黑天鹅事件警报
            alert_data = {
                "type": "alert",  # 添加消息类型字段
                "alert_type": "BLACK_SWAN",
                "severity": "CRITICAL",
                "event": "LUNA_CRASH",
                "description": "检测到LUNA代币崩盘，市场出现系统性风险",
                "risk_level": 10,
                "affected_symbols": ["LUNA-USDT", "UST-USDT", "BTC-USDT", "ETH-USDT"],
                "recommended_action": "EMERGENCY_SHUTDOWN",
                "timestamp": datetime.now().isoformat(),
                "source": "risk_control_module"
            }
            
            # 发布到risk.alerts主题
            topic = "risk.alerts"
            message = json.dumps(alert_data)
            
            await self.zmq_publisher.send_multipart([
                topic.encode('utf-8'),
                message.encode('utf-8')
            ])
            
            logger.info(f"✓ 发布风控警报: {alert_data['event']} - {alert_data['severity']}")
            logger.info(f"  警报内容: {alert_data['description']}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 发布风控警报失败: {e}")
            return False
            
    async def monitor_emergency_shutdown(self, timeout: int = 30) -> bool:
        """监控紧急停机指令"""
        logger.info("--- 步骤3: 监控紧急停机指令 ---")
        
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # 非阻塞接收
                    message = await asyncio.wait_for(
                        self.zmq_subscriber.recv_multipart(),
                        timeout=1.0
                    )
                    
                    if len(message) >= 2:
                        topic = message[0].decode('utf-8')
                        content = message[1].decode('utf-8')
                        
                        logger.info(f"✓ 收到指令: {topic}")
                        logger.info(f"  指令内容: {content}")
                        
                        if topic == "command":
                            try:
                                command_data = json.loads(content)
                                if command_data.get('command') == 'EMERGENCY_SHUTDOWN':
                                    logger.info(f"✓ 紧急停机指令确认: {command_data.get('reason', 'Unknown')}")
                                    return True
                                else:
                                    logger.info(f"收到其他命令: {command_data.get('command')}")
                            except json.JSONDecodeError:
                                logger.info(f"✓ 紧急停机指令确认: {content}")
                                return True
                                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f"接收消息时出错: {e}")
                    continue
                    
            logger.error(f"✗ 超时未收到紧急停机指令 ({timeout}秒)")
            return False
            
        except Exception as e:
            logger.error(f"✗ 监控紧急停机指令失败: {e}")
            return False
            
    async def verify_position_clearing(self) -> bool:
        """验证持仓清空"""
        logger.info("--- 步骤4: 验证持仓清空 ---")
        
        try:
            # 等待清仓操作完成
            await asyncio.sleep(2)
            
            # 检查持仓键是否被清空
            position_keys = self.redis_client.keys("positions:*")
            
            if not position_keys:
                logger.info("✓ 所有持仓已清空")
                return True
            else:
                logger.info(f"检查剩余持仓: {len(position_keys)}个")
                
                # 检查每个持仓的状态
                cleared_positions = 0
                for key in position_keys:
                    position_data = self.redis_client.hgetall(key)
                    if position_data.get('status') == 'CLEARED' or position_data.get('size') == '0':
                        cleared_positions += 1
                        logger.info(f"✓ 持仓已清空: {key}")
                    else:
                        logger.warning(f"✗ 持仓未清空: {key} - {position_data}")
                        
                if cleared_positions == len(position_keys):
                    logger.info("✓ 所有持仓状态已更新为已清空")
                    return True
                else:
                    logger.error(f"✗ 仍有 {len(position_keys) - cleared_positions} 个持仓未清空")
                    return False
                    
        except Exception as e:
            logger.error(f"✗ 验证持仓清空失败: {e}")
            return False
            
    async def check_api_status(self) -> bool:
        """检查API服务状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base_url}/health") as response:
                    if response.status == 200:
                        logger.info("✓ API服务运行正常")
                        return True
                    else:
                        logger.error(f"✗ API服务状态异常: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"✗ API服务连接失败: {e}")
            return False
            
    async def run_e2e_test(self) -> Dict[str, Any]:
        """运行完整的端到端测试"""
        logger.info("\n" + "="*60)
        logger.info("开始执行 E2E-MASTER-01 全链路熔断协议验证测试")
        logger.info("="*60)
        
        test_result = {
            "test_case": "E2E-MASTER-01",
            "description": "全链路熔断协议验证",
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "overall_result": "FAILED"
        }
        
        try:
            # 检查前置条件
            logger.info("\n--- 前置条件检查 ---")
            api_ok = await self.check_api_status()
            if not api_ok:
                test_result["error"] = "API服务不可用"
                return test_result
                
            # 步骤1: 模拟交易员持仓
            step1_result = await self.simulate_trader_positions()
            test_result["steps"].append({
                "step": 1,
                "description": "模拟交易员持仓状态",
                "result": "PASSED" if step1_result else "FAILED"
            })
            
            if not step1_result:
                test_result["error"] = "步骤1失败：无法模拟持仓状态"
                return test_result
                
            # 步骤2: 触发风控警报
            step2_result = await self.trigger_risk_alert()
            test_result["steps"].append({
                "step": 2,
                "description": "触发风控警报",
                "result": "PASSED" if step2_result else "FAILED"
            })
            
            if not step2_result:
                test_result["error"] = "步骤2失败：无法触发风控警报"
                return test_result
                
            # 步骤3: 监控紧急停机指令
            step3_result = await self.monitor_emergency_shutdown()
            test_result["steps"].append({
                "step": 3,
                "description": "监控紧急停机指令",
                "result": "PASSED" if step3_result else "FAILED"
            })
            
            if not step3_result:
                test_result["error"] = "步骤3失败：未收到紧急停机指令"
                return test_result
                
            # 步骤4: 验证持仓清空
            step4_result = await self.verify_position_clearing()
            test_result["steps"].append({
                "step": 4,
                "description": "验证持仓清空",
                "result": "PASSED" if step4_result else "FAILED"
            })
            
            if not step4_result:
                test_result["error"] = "步骤4失败：持仓未正确清空"
                return test_result
                
            # 所有步骤成功
            test_result["overall_result"] = "PASSED"
            logger.info("\n" + "="*60)
            logger.info("🎉 E2E-MASTER-01 测试完全通过！")
            logger.info("全链路熔断协议验证成功")
            logger.info("="*60)
            
        except Exception as e:
            test_result["error"] = f"测试执行异常: {str(e)}"
            logger.error(f"✗ 测试执行异常: {e}")
            
        finally:
            test_result["end_time"] = datetime.now().isoformat()
            
        return test_result
        
    def generate_test_report(self, results: List[Dict[str, Any]]):
        """生成测试报告"""
        logger.info("\n" + "="*60)
        logger.info("端到端测试报告")
        logger.info("="*60)
        
        for result in results:
            logger.info(f"\n测试用例: {result['test_case']}")
            logger.info(f"描述: {result['description']}")
            logger.info(f"开始时间: {result['start_time']}")
            logger.info(f"结束时间: {result.get('end_time', 'N/A')}")
            logger.info(f"总体结果: {result['overall_result']}")
            
            if 'steps' in result:
                logger.info("\n步骤详情:")
                for step in result['steps']:
                    status_icon = "✓" if step['result'] == 'PASSED' else "✗"
                    logger.info(f"  {status_icon} 步骤{step['step']}: {step['description']} - {step['result']}")
                    
            if 'error' in result:
                logger.info(f"\n错误信息: {result['error']}")
                
        # 统计
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['overall_result'] == 'PASSED')
        
        logger.info(f"\n测试统计:")
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过数: {passed_tests}")
        logger.info(f"失败数: {total_tests - passed_tests}")
        logger.info(f"通过率: {(passed_tests/total_tests)*100:.1f}%")
        
async def main():
    """主函数"""
    runner = E2ETestRunner()
    
    try:
        # 初始化
        await runner.setup()
        
        # 运行测试
        result = await runner.run_e2e_test()
        
        # 生成报告
        runner.generate_test_report([result])
        
        # 返回结果
        return result['overall_result'] == 'PASSED'
        
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        return False
        
    finally:
        await runner.cleanup()
        
if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)