#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策引擎单元测试

测试用例：
- UNIT-DECISION-01: 决策引擎 - 切换进攻模式
- UNIT-DECISION-02: 决策引擎 - 紧急熔断
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.decision_engine import DecisionEngine, get_decision_engine


class TestDecisionEngine:
    """决策引擎测试类"""

    @pytest.fixture
    def decision_engine(self):
        """创建决策引擎实例"""
        engine = DecisionEngine()
        return engine

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unit_decision_01_switch_aggressive_mode(self, decision_engine, mock_redis_manager, mock_zmq_manager):
        """
        UNIT-DECISION-01: 决策引擎 - 切换进攻模式
        
        测试步骤：
        1. Mock Redis客户端
        2. 配置Mock的Redis，使其在被查询market:bull_bear_index键时，返回一个代表强牛市的值（例如 80）
        3. 调用总控模组的主决策函数
        
        验收标准：
        - 验证被Mock的ZMQ发布器（Publisher）被调用了一次
        - 验证发布的ZMQ主题是 control.commands
        - 验证发布的消息内容是 {"command": "SWITCH_MODE", "payload": "AGGRESSIVE", ...}
        """
        # 1. Mock Redis客户端
        decision_engine.redis_manager = mock_redis_manager
        decision_engine.zmq_manager = mock_zmq_manager
        
        # 2. 配置Mock的Redis，返回强牛市值（80）
        mock_redis_manager.get_bull_bear_index.return_value = {
            "index": 80,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        # 3. 调用总控模组的主决策函数
        result = await decision_engine.run_decision_cycle()
        
        # 验证结果
        assert result["status"] == "success"
        assert result["executed"] is True
        
        # 验证决策内容
        decision = result["decision"]
        assert decision["action"] == "SWITCH_MODE"
        assert decision["payload"] == "AGGRESSIVE"
        assert "强牛市信号" in decision["reason"]
        
        # 验证被Mock的ZMQ发布器被调用了一次
        mock_zmq_manager.publish_message.assert_called_once()
        
        # 获取调用参数
        call_args = mock_zmq_manager.publish_message.call_args
        topic = call_args[0][0]
        message_type = call_args[0][1]
        message_data = call_args[0][2]
        
        # 验证发布的ZMQ主题是 control.commands
        assert topic == "control.commands"
        assert message_type == "command"
        
        # 验证发布的消息内容
        assert message_data["command"] == "SWITCH_MODE"
        assert message_data["payload"] == "AGGRESSIVE"
        assert "强牛市信号" in message_data["reason"]
        assert "timestamp" in message_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unit_decision_02_emergency_shutdown(self, decision_engine, mock_redis_manager, mock_zmq_manager):
        """
        UNIT-DECISION-02: 决策引擎 - 紧急熔断
        
        测试步骤：
        1. Mock ZMQ订阅器（Subscriber）
        2. 模拟从 risk.alerts 主题收到一条"黑天鹅事件"警报消息
        3. 调用总控模组的消息处理函数
        
        验收标准：
        - 验证被Mock的ZMQ发布器（Publisher）被调用，并向control.commands主题发布了 EMERGENCY_SHUTDOWN 指令
        """
        # 1. Mock依赖
        decision_engine.redis_manager = mock_redis_manager
        decision_engine.zmq_manager = mock_zmq_manager
        
        # 2. 模拟从 risk.alerts 主题收到"黑天鹅事件"警报消息
        alert_data = {
            "alert_type": "market_crash",
            "level": "critical",
            "message": "检测到黑天鹅事件：市场异常波动",
            "module": "risk_control",
            "timestamp": datetime.now().isoformat()
        }
        
        # 3. 调用总控模组的消息处理函数
        result = await decision_engine.handle_risk_alert(alert_data)
        
        # 验证处理成功
        assert result is True
        
        # 验证被Mock的ZMQ发布器被调用
        mock_zmq_manager.publish_message.assert_called_once()
        
        # 获取调用参数
        call_args = mock_zmq_manager.publish_message.call_args
        topic = call_args[0][0]
        message_type = call_args[0][1]
        message_data = call_args[0][2]
        
        # 验证向control.commands主题发布了 EMERGENCY_SHUTDOWN 指令
        assert topic == "control.commands"
        assert message_type == "command"
        assert message_data["command"] == "EMERGENCY_SHUTDOWN"
        assert "黑天鹅事件" in message_data["reason"]
        assert message_data["alert_type"] == "market_crash"
        assert "timestamp" in message_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_market_analysis_strong_bull(self, decision_engine, mock_redis_manager):
        """测试强牛市分析"""
        decision_engine.redis_manager = mock_redis_manager
        
        # 设置强牛市数据
        mock_redis_manager.get_bull_bear_index.return_value = {
            "index": 85,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        result = await decision_engine.analyze_market_condition()
        
        assert result["status"] == "strong_bull"
        assert result["index"] == 85
        assert result["recommendation"] == "AGGRESSIVE"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_market_analysis_strong_bear(self, decision_engine, mock_redis_manager):
        """测试强熊市分析"""
        decision_engine.redis_manager = mock_redis_manager
        
        # 设置强熊市数据
        mock_redis_manager.get_bull_bear_index.return_value = {
            "index": 15,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        result = await decision_engine.analyze_market_condition()
        
        assert result["status"] == "strong_bear"
        assert result["index"] == 15
        assert result["recommendation"] == "DEFENSIVE"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_market_analysis_no_data(self, decision_engine, mock_redis_manager):
        """测试无数据情况"""
        decision_engine.redis_manager = mock_redis_manager
        
        # 设置无数据
        mock_redis_manager.get_bull_bear_index.return_value = None
        
        result = await decision_engine.analyze_market_condition()
        
        assert result["status"] == "unknown"
        assert "无牛熊指数数据" in result["reason"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_risk_alert_high_level(self, decision_engine, mock_redis_manager, mock_zmq_manager):
        """测试高级别风险告警处理"""
        decision_engine.redis_manager = mock_redis_manager
        decision_engine.zmq_manager = mock_zmq_manager
        
        alert_data = {
            "alert_type": "high_volatility",
            "level": "high",
            "message": "市场波动率异常升高",
            "module": "risk_control"
        }
        
        result = await decision_engine.handle_risk_alert(alert_data)
        
        assert result is True
        mock_zmq_manager.publish_message.assert_called_once()
        
        # 验证切换到防御模式
        call_args = mock_zmq_manager.publish_message.call_args
        message_data = call_args[0][2]
        assert message_data["command"] == "SWITCH_MODE"
        assert message_data["payload"] == "DEFENSIVE"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_risk_alert_low_level(self, decision_engine, mock_redis_manager, mock_zmq_manager):
        """测试低级别风险告警处理"""
        decision_engine.redis_manager = mock_redis_manager
        decision_engine.zmq_manager = mock_zmq_manager
        
        alert_data = {
            "alert_type": "minor_issue",
            "level": "warning",
            "message": "轻微异常",
            "module": "risk_control"
        }
        
        result = await decision_engine.handle_risk_alert(alert_data)
        
        assert result is True
        # 低级别告警不应触发ZMQ消息
        mock_zmq_manager.publish_message.assert_not_called()