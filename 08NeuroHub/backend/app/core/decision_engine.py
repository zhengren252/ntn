#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策引擎模块

负责总控模块的核心决策逻辑：
- 市场状态分析
- 交易模式切换
- 风险控制决策
- 紧急响应处理
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.redis_manager import get_redis_manager
from app.core.zmq_manager import get_zmq_manager

logger = logging.getLogger(__name__)


class DecisionEngine:
    """决策引擎"""

    def __init__(self):
        self.redis_manager = None
        self.zmq_manager = None

    async def init_dependencies(self):
        """初始化依赖"""
        self.redis_manager = get_redis_manager()
        self.zmq_manager = get_zmq_manager()

    async def analyze_market_condition(self) -> Dict[str, Any]:
        """分析市场状况"""
        try:
            # 获取牛熊指数
            bull_bear_data = await self.redis_manager.get_bull_bear_index()
            if not bull_bear_data:
                return {"status": "unknown", "reason": "无牛熊指数数据"}

            index_value = bull_bear_data.get("index", 50)
            
            # 分析市场状态
            if index_value >= 80:
                return {
                    "status": "strong_bull",
                    "index": index_value,
                    "recommendation": "AGGRESSIVE"
                }
            elif index_value >= 60:
                return {
                    "status": "bull",
                    "index": index_value,
                    "recommendation": "MODERATE"
                }
            elif index_value <= 20:
                return {
                    "status": "strong_bear",
                    "index": index_value,
                    "recommendation": "DEFENSIVE"
                }
            elif index_value <= 40:
                return {
                    "status": "bear",
                    "index": index_value,
                    "recommendation": "CONSERVATIVE"
                }
            else:
                return {
                    "status": "neutral",
                    "index": index_value,
                    "recommendation": "BALANCED"
                }

        except Exception as e:
            logger.error(f"市场状况分析失败: {e}")
            return {"status": "error", "reason": str(e)}

    async def make_trading_decision(self) -> Dict[str, Any]:
        """制定交易决策"""
        try:
            # 分析市场状况
            market_analysis = await self.analyze_market_condition()
            
            if market_analysis["status"] == "error":
                return market_analysis

            recommendation = market_analysis.get("recommendation")
            
            # 根据分析结果制定决策
            if recommendation == "AGGRESSIVE":
                decision = {
                    "action": "SWITCH_MODE",
                    "payload": "AGGRESSIVE",
                    "reason": f"强牛市信号，牛熊指数: {market_analysis['index']}",
                    "timestamp": datetime.now().isoformat()
                }
            elif recommendation == "DEFENSIVE":
                decision = {
                    "action": "SWITCH_MODE",
                    "payload": "DEFENSIVE",
                    "reason": f"强熊市信号，牛熊指数: {market_analysis['index']}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                decision = {
                    "action": "SWITCH_MODE",
                    "payload": recommendation,
                    "reason": f"市场状态: {market_analysis['status']}, 牛熊指数: {market_analysis['index']}",
                    "timestamp": datetime.now().isoformat()
                }

            return decision

        except Exception as e:
            logger.error(f"交易决策制定失败: {e}")
            return {"status": "error", "reason": str(e)}

    async def execute_trading_decision(self, decision: Dict[str, Any]) -> bool:
        """执行交易决策"""
        try:
            action = decision.get("action")
            payload = decision.get("payload")
            
            if action == "SWITCH_MODE":
                # 通过ZMQ广播模式切换指令
                await self.zmq_manager.publish_message(
                    "control.commands",
                    "command",
                    {
                        "command": "SWITCH_MODE",
                        "payload": payload,
                        "reason": decision.get("reason"),
                        "timestamp": decision.get("timestamp")
                    }
                )
                
                logger.info(f"已发布模式切换指令: {payload}")
                return True
            else:
                logger.warning(f"未知决策动作: {action}")
                return False

        except Exception as e:
            logger.error(f"决策执行失败: {e}")
            return False

    async def handle_risk_alert(self, alert_data: Dict[str, Any]) -> bool:
        """处理风险告警"""
        try:
            alert_type = alert_data.get("alert_type")
            level = alert_data.get("level", "warning")
            message = alert_data.get("message", "")
            
            logger.warning(f"收到风险告警: {alert_type} - {level} - {message}")
            
            # 根据告警类型和级别决定响应
            if level == "critical" or "黑天鹅" in message:
                # 紧急熔断
                await self.zmq_manager.publish_message(
                    "control.commands",
                    "command",
                    {
                        "command": "EMERGENCY_SHUTDOWN",
                        "reason": f"风险告警触发紧急熔断: {message}",
                        "timestamp": datetime.now().isoformat(),
                        "alert_type": alert_type
                    }
                )
                
                logger.critical(f"已发布紧急熔断指令，原因: {message}")
                return True
            elif level == "high":
                # 切换到防御模式
                await self.zmq_manager.publish_message(
                    "control.commands",
                    "command",
                    {
                        "command": "SWITCH_MODE",
                        "payload": "DEFENSIVE",
                        "reason": f"高风险告警触发防御模式: {message}",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                logger.warning(f"已切换到防御模式，原因: {message}")
                return True
            else:
                # 记录告警但不采取行动
                logger.info(f"记录风险告警: {alert_type} - {message}")
                return True

        except Exception as e:
            logger.error(f"风险告警处理失败: {e}")
            return False

    async def run_decision_cycle(self) -> Dict[str, Any]:
        """运行决策周期"""
        try:
            # 制定交易决策
            decision = await self.make_trading_decision()
            
            if decision.get("status") == "error":
                return decision
            
            # 执行决策
            success = await self.execute_trading_decision(decision)
            
            return {
                "status": "success" if success else "failed",
                "decision": decision,
                "executed": success
            }

        except Exception as e:
            logger.error(f"决策周期运行失败: {e}")
            return {"status": "error", "reason": str(e)}


# 全局决策引擎实例
decision_engine = DecisionEngine()


def get_decision_engine() -> DecisionEngine:
    """获取决策引擎实例"""
    return decision_engine