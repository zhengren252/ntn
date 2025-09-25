#!/usr/bin/env python3
"""
NeuroTrade Nexus - 风控模拟器
模拟风控模块向risk.alerts主题发布风险警报

用于端到端测试中模拟风险事件触发
"""

import zmq
import zmq.asyncio
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskControlSimulator:
    """风控模拟器"""
    
    def __init__(self, zmq_port=5795):  # risk_management模组发布端口
        self.zmq_context = None
        self.zmq_publisher = None
        self.zmq_port = zmq_port
        self.alert_history = []
        
    async def setup(self) -> bool:
        """初始化ZMQ连接"""
        try:
            self.zmq_context = zmq.asyncio.Context()
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind(f"tcp://*:{self.zmq_port}")
            
            # 等待连接建立
            await asyncio.sleep(1)
            
            logger.info(f"✓ 风控模拟器已启动，监听端口: {self.zmq_port}")
            return True
            
        except Exception as e:
            logger.error(f"✗ ZMQ初始化失败: {e}")
            return False
            
    async def cleanup(self):
        """清理资源"""
        if self.zmq_publisher:
            self.zmq_publisher.close()
        if self.zmq_context:
            self.zmq_context.term()
        logger.info("✓ 风控模拟器已关闭")
        
    def create_alert(self, alert_type: str, severity: str, **kwargs) -> Dict[str, Any]:
        """创建风险警报"""
        base_alert = {
            "type": "alert",  # 添加消息类型字段
            "alert_id": f"ALERT_{int(datetime.now().timestamp() * 1000)}",
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "source": "risk_control_simulator",
            "version": "1.0"
        }
        
        # 合并额外参数
        base_alert.update(kwargs)
        
        return base_alert
        
    async def publish_alert(self, topic: str, alert_data: Dict[str, Any]) -> bool:
        """发布警报到指定主题"""
        try:
            message = json.dumps(alert_data, ensure_ascii=False)
            
            await self.zmq_publisher.send_multipart([
                topic.encode('utf-8'),
                message.encode('utf-8')
            ])
            
            # 记录到历史
            self.alert_history.append({
                "topic": topic,
                "alert": alert_data,
                "sent_at": datetime.now().isoformat()
            })
            
            logger.info(f"✓ 发布警报: {topic} - {alert_data['alert_type']} ({alert_data['severity']})")
            return True
            
        except Exception as e:
            logger.error(f"✗ 发布警报失败: {e}")
            return False
            
    async def send_black_swan_alert(self) -> bool:
        """发送黑天鹅事件警报"""
        alert = self.create_alert(
            alert_type="BLACK_SWAN",
            severity="CRITICAL",
            event="LUNA_CRASH",
            description="检测到LUNA代币崩盘，市场出现系统性风险",
            risk_level=10,
            affected_symbols=["LUNA-USDT", "UST-USDT", "BTC-USDT", "ETH-USDT"],
            market_impact="SEVERE",
            recommended_action="EMERGENCY_SHUTDOWN",
            details={
                "luna_price_drop": 99.9,
                "ust_depeg": 70.0,
                "market_cap_loss": 60000000000,
                "contagion_risk": "HIGH"
            }
        )
        
        return await self.publish_alert("risk.alerts", alert)
        
    async def send_liquidation_alert(self, symbol: str, liquidation_amount: float) -> bool:
        """发送清算警报"""
        alert = self.create_alert(
            alert_type="LIQUIDATION",
            severity="HIGH",
            event="POSITION_LIQUIDATION",
            description=f"检测到{symbol}大额清算，可能引发连锁反应",
            risk_level=8,
            affected_symbols=[symbol],
            liquidation_amount=liquidation_amount,
            recommended_action="REDUCE_EXPOSURE"
        )
        
        return await self.publish_alert("risk.alerts", alert)
        
    async def send_volatility_alert(self, symbol: str, volatility_level: float) -> bool:
        """发送波动率警报"""
        severity = "CRITICAL" if volatility_level > 50 else "HIGH" if volatility_level > 30 else "MEDIUM"
        
        alert = self.create_alert(
            alert_type="VOLATILITY",
            severity=severity,
            event="HIGH_VOLATILITY",
            description=f"{symbol}波动率异常，当前波动率: {volatility_level}%",
            risk_level=min(10, int(volatility_level / 5)),
            affected_symbols=[symbol],
            volatility_level=volatility_level,
            recommended_action="MONITOR" if volatility_level < 40 else "REDUCE_POSITION"
        )
        
        return await self.publish_alert("risk.alerts", alert)
        
    async def send_correlation_alert(self, symbols: List[str], correlation: float) -> bool:
        """发送相关性警报"""
        alert = self.create_alert(
            alert_type="CORRELATION",
            severity="MEDIUM",
            event="HIGH_CORRELATION",
            description=f"检测到资产间异常高相关性: {correlation:.2f}",
            risk_level=6,
            affected_symbols=symbols,
            correlation_level=correlation,
            recommended_action="DIVERSIFY"
        )
        
        return await self.publish_alert("risk.alerts", alert)
        
    async def send_margin_alert(self, margin_ratio: float) -> bool:
        """发送保证金警报"""
        severity = "CRITICAL" if margin_ratio < 0.1 else "HIGH" if margin_ratio < 0.2 else "MEDIUM"
        
        alert = self.create_alert(
            alert_type="MARGIN",
            severity=severity,
            event="LOW_MARGIN",
            description=f"保证金比率过低: {margin_ratio:.2%}",
            risk_level=10 if margin_ratio < 0.1 else 7,
            margin_ratio=margin_ratio,
            recommended_action="ADD_MARGIN" if margin_ratio > 0.05 else "EMERGENCY_SHUTDOWN"
        )
        
        return await self.publish_alert("risk.alerts", alert)
        
    async def simulate_risk_scenario(self, scenario: str = "black_swan") -> bool:
        """模拟风险场景"""
        logger.info(f"--- 模拟风险场景: {scenario} ---")
        
        if scenario == "black_swan":
            return await self._simulate_black_swan_scenario()
        elif scenario == "flash_crash":
            return await self._simulate_flash_crash_scenario()
        elif scenario == "margin_call":
            return await self._simulate_margin_call_scenario()
        elif scenario == "correlation_spike":
            return await self._simulate_correlation_scenario()
        else:
            logger.error(f"未知风险场景: {scenario}")
            return False
            
    async def _simulate_black_swan_scenario(self) -> bool:
        """模拟黑天鹅场景"""
        try:
            logger.info("开始模拟黑天鹅事件...")
            
            # 1. 首先发送波动率警报
            await self.send_volatility_alert("LUNA-USDT", 85.0)
            await asyncio.sleep(1)
            
            # 2. 发送清算警报
            await self.send_liquidation_alert("LUNA-USDT", 500000000)
            await asyncio.sleep(1)
            
            # 3. 发送关键的黑天鹅警报
            await self.send_black_swan_alert()
            await asyncio.sleep(1)
            
            # 4. 发送保证金警报
            await self.send_margin_alert(0.05)
            
            logger.info("✓ 黑天鹅场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 黑天鹅场景模拟失败: {e}")
            return False
            
    async def _simulate_flash_crash_scenario(self) -> bool:
        """模拟闪崩场景"""
        try:
            logger.info("开始模拟闪崩事件...")
            
            symbols = ["BTC-USDT", "ETH-USDT", "ADA-USDT", "SOL-USDT"]
            
            # 快速连续发送多个警报
            for symbol in symbols:
                await self.send_volatility_alert(symbol, random.uniform(40, 70))
                await asyncio.sleep(0.5)
                
            # 发送相关性警报
            await self.send_correlation_alert(symbols, 0.95)
            
            logger.info("✓ 闪崩场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 闪崩场景模拟失败: {e}")
            return False
            
    async def _simulate_margin_call_scenario(self) -> bool:
        """模拟保证金追缴场景"""
        try:
            logger.info("开始模拟保证金追缴...")
            
            # 逐步降低保证金比率
            margin_levels = [0.3, 0.2, 0.15, 0.08]
            
            for margin in margin_levels:
                await self.send_margin_alert(margin)
                await asyncio.sleep(2)
                
            logger.info("✓ 保证金追缴场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 保证金追缴场景模拟失败: {e}")
            return False
            
    async def _simulate_correlation_scenario(self) -> bool:
        """模拟相关性异常场景"""
        try:
            logger.info("开始模拟相关性异常...")
            
            # 不同资产组合的相关性警报
            asset_groups = [
                (["BTC-USDT", "ETH-USDT"], 0.98),
                (["LUNA-USDT", "UST-USDT"], 0.99),
                (["ADA-USDT", "SOL-USDT", "AVAX-USDT"], 0.95)
            ]
            
            for symbols, correlation in asset_groups:
                await self.send_correlation_alert(symbols, correlation)
                await asyncio.sleep(1)
                
            logger.info("✓ 相关性异常场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 相关性异常场景模拟失败: {e}")
            return False
            
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """获取警报历史"""
        return self.alert_history
        
    def clear_alert_history(self):
        """清空警报历史"""
        self.alert_history.clear()
        logger.info("✓ 警报历史已清空")
        
async def main():
    """主函数 - 用于独立运行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='风控模拟器')
    parser.add_argument('--scenario', 
                       choices=['black_swan', 'flash_crash', 'margin_call', 'correlation_spike'],
                       default='black_swan', help='风险场景')
    parser.add_argument('--port', type=int, default=5556, help='ZMQ发布端口')
    parser.add_argument('--single-alert', choices=['black_swan', 'liquidation', 'volatility', 'margin'],
                       help='发送单个警报类型')
    
    args = parser.parse_args()
    
    # 创建模拟器
    simulator = RiskControlSimulator(args.port)
    
    try:
        if not await simulator.setup():
            logger.error("风控模拟器初始化失败")
            return False
            
        if args.single_alert:
            # 发送单个警报
            if args.single_alert == 'black_swan':
                success = await simulator.send_black_swan_alert()
            elif args.single_alert == 'liquidation':
                success = await simulator.send_liquidation_alert("BTC-USDT", 1000000)
            elif args.single_alert == 'volatility':
                success = await simulator.send_volatility_alert("ETH-USDT", 60.0)
            elif args.single_alert == 'margin':
                success = await simulator.send_margin_alert(0.05)
            else:
                success = False
                
            if success:
                logger.info(f"✓ {args.single_alert} 警报发送成功")
            else:
                logger.error(f"✗ {args.single_alert} 警报发送失败")
                
        else:
            # 运行完整场景
            success = await simulator.simulate_risk_scenario(args.scenario)
            
        # 显示历史
        history = simulator.get_alert_history()
        if history:
            logger.info(f"\n发送了 {len(history)} 个警报:")
            for i, record in enumerate(history, 1):
                alert = record['alert']
                logger.info(f"  {i}. {alert['alert_type']} - {alert['severity']} ({record['sent_at']})")
                
        return success
        
    except KeyboardInterrupt:
        logger.info("用户中断")
        return True
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return False
    finally:
        await simulator.cleanup()
        
if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)