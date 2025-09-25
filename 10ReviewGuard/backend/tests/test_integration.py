#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试模块
测试ReviewGuard模组与消息队列、数据库和缓存的协同工作能力
"""

import pytest
import asyncio
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 导入项目模块
from src.models.database import DatabaseManager, StrategyReview, User
from src.services.zmq_service import ZMQService
from src.services.rule_engine import RuleEngine
from src.utils.auth import AuthManager
from src.main import app
from fastapi.testclient import TestClient


class TestIntegration:
    """集成测试类"""
    
    @pytest.fixture
    def setup_integration_env(self):
        """设置集成测试环境"""
        # 创建测试数据库管理器
        db_manager = DatabaseManager(":memory:")
        
        # 创建测试用户
        test_user = User(
            id="test_user_001",
            username="test_reviewer",
            email="test@example.com",
            password_hash="hashed_password",
            role="reviewer",
            is_active=True,
            created_at=datetime.now()
        )
        
        # 创建测试策略审核记录
        test_review = StrategyReview(
            id="test_review_001",
            strategy_id="strategy_001",
            symbol="BTCUSDT",
            strategy_type="grid_trading",
            expected_return=0.15,
            max_drawdown=0.05,
            risk_level="low",
            status="pending",
            raw_data={
                "position_size": 0.1,
                "stop_loss": 0.02,
                "take_profit": 0.05
            }
        )
        
        return {
            "db_manager": db_manager,
            "test_user": test_user,
            "test_review": test_review
        }
    
    def test_int_rg_zmq_01_complete_flow_auto_approve(self, setup_integration_env):
        """INT-RG-ZMQ-01: ZMQ消息输入到输出的完整流程 (自动批准)"""
        env = setup_integration_env
        
        # 模拟接收到的消息
        received_messages = []
        
        def mock_zmq_subscriber_callback(message):
            """模拟ZMQ订阅者回调函数"""
            received_messages.append(message)
        
        # 创建模拟的ZMQ服务
        with patch('src.services.zmq_service.ZMQService') as mock_zmq_service:
            # 配置模拟的ZMQ服务
            mock_zmq_instance = Mock()
            mock_zmq_service.return_value = mock_zmq_instance
            
            # 模拟发布器
            mock_publisher = Mock()
            mock_zmq_instance.get_publisher.return_value = mock_publisher
            
            # 创建规则引擎实例
            rule_engine = RuleEngine(env["db_manager"])
            
            # 准备符合"低风险自动通过"规则的策略包
            strategy_package = {
                "strategy_id": "strategy_001",
                "symbol": "BTCUSDT",
                "strategy_type": "grid_trading",
                "expected_return": 0.15,
                "max_drawdown": 0.05,
                "risk_level": "low",
                "position_size": 0.1,
                "stop_loss": 0.02,
                "take_profit": 0.05,
                "timestamp": datetime.now().isoformat()
            }
            
            # 模拟数据库中的自动批准规则
            with patch.object(env["db_manager"], 'get_audit_rules') as mock_get_rules:
                mock_get_rules.return_value = [
                    {
                        "id": "rule_001",
                        "name": "低风险自动通过",
                        "conditions": {"risk_level": "low"},
                        "action": "approve",
                        "is_active": True
                    }
                ]
                
                # 模拟创建策略审核记录
                with patch.object(env["db_manager"], 'create_strategy_review') as mock_create_review:
                    mock_create_review.return_value = env["test_review"]
                    
                    # 执行规则引擎处理
                    result = rule_engine.process_strategy(strategy_package)
                    
                    # 验证结果
                    assert result["action"] == "approve"
                    assert result["reviewer"] == "auto"
                    
                    # 验证ZMQ发布器被调用
                    mock_publisher.send_message.assert_called_once()
                    
                    # 获取发布的消息
                    published_message = mock_publisher.send_message.call_args[0][1]
                    
                    # 验证发布的消息包含review_info字段
                    assert "review_info" in published_message
                    assert published_message["review_info"]["reviewer"] == "auto"
                    assert published_message["review_info"]["action"] == "approve"
                    
                    # 验证原始策略包数据被保留
                    assert published_message["strategy_id"] == strategy_package["strategy_id"]
                    assert published_message["symbol"] == strategy_package["symbol"]
                    assert published_message["risk_level"] == strategy_package["risk_level"]
    
    def test_int_rg_api_db_01_manual_approval_flow(self, setup_integration_env):
        """INT-RG-API-DB-01: API-数据库集成 - 人工批准流程"""
        env = setup_integration_env
        
        # 创建测试客户端
        client = TestClient(app)
        
        # 模拟认证和数据库操作
        with patch('src.main.auth_manager') as mock_auth_manager, \
             patch('src.main.db_manager') as mock_db_manager:
            
            # 配置认证模拟
            mock_auth_manager.verify_token.return_value = "test_user_001"
            mock_db_manager.get_user_by_id.return_value = env["test_user"]
            
            # 配置数据库模拟 - 获取待审核记录
            test_review = env["test_review"]
            test_review.status = "pending"
            mock_db_manager.get_strategy_review_by_id.return_value = test_review
            
            # 模拟创建决策记录
            mock_db_manager.create_review_decision.return_value = True
            
            # 模拟更新策略审核状态
            mock_db_manager.update_strategy_review_status.return_value = True
            
            # 执行API调用
            response = client.post(
                "/api/reviews/test_review_001/decision",
                json={
                    "decision": "approve",
                    "reason": "策略风险可控"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证API响应
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True
            assert "decision_id" in response_data
            
            # 验证数据库操作被正确调用
            mock_db_manager.create_review_decision.assert_called_once()
            mock_db_manager.update_strategy_review_status.assert_called_once_with(
                "test_review_001", "approved"
            )
            
            # 验证决策记录的创建参数
            create_call_args = mock_db_manager.create_review_decision.call_args[0]
            decision_obj = create_call_args[0]
            assert decision_obj.strategy_review_id == "test_review_001"
            assert decision_obj.decision == "approve"
            assert decision_obj.reviewer_id == "test_user_001"
            assert decision_obj.reason == "策略风险可控"
    
    def test_int_rg_zmq_01_manual_review_flow(self, setup_integration_env):
        """INT-RG-ZMQ-01: ZMQ消息流程 - 强制人工审核路径"""
        env = setup_integration_env
        
        # 创建模拟的ZMQ服务
        with patch('src.services.zmq_service.ZMQService') as mock_zmq_service:
            # 配置模拟的ZMQ服务
            mock_zmq_instance = Mock()
            mock_zmq_service.return_value = mock_zmq_instance
            
            # 模拟发布器
            mock_publisher = Mock()
            mock_zmq_instance.get_publisher.return_value = mock_publisher
            
            # 创建规则引擎实例
            rule_engine = RuleEngine(env["db_manager"])
            
            # 准备符合"高风险强制审核"规则的策略包
            strategy_package = {
                "strategy_id": "strategy_002",
                "symbol": "ETHUSDT",
                "strategy_type": "momentum_trading",
                "expected_return": 0.30,
                "max_drawdown": 0.15,
                "risk_level": "high",
                "position_size": 0.5,
                "stop_loss": 0.10,
                "take_profit": 0.20,
                "timestamp": datetime.now().isoformat()
            }
            
            # 模拟数据库中的强制人工审核规则
            with patch.object(env["db_manager"], 'get_audit_rules') as mock_get_rules:
                mock_get_rules.return_value = [
                    {
                        "id": "rule_002",
                        "name": "高风险强制审核",
                        "conditions": {"risk_level": "high"},
                        "action": "manual_review",
                        "is_active": True
                    }
                ]
                
                # 模拟创建策略审核记录
                with patch.object(env["db_manager"], 'create_strategy_review') as mock_create_review:
                    test_review = env["test_review"]
                    test_review.status = "pending_manual_review"
                    mock_create_review.return_value = test_review
                    
                    # 执行规则引擎处理
                    result = rule_engine.process_strategy(strategy_package)
                    
                    # 验证结果
                    assert result["action"] == "manual_review"
                    assert result["status"] == "pending_manual_review"
                    
                    # 验证ZMQ发布器未被调用（因为需要人工审核）
                    mock_publisher.send_message.assert_not_called()
                    
                    # 验证数据库记录被创建
                    mock_create_review.assert_called_once()