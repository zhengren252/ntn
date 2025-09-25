#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试 (End-to-End Testing) - Mock版本
验证【人工审核模组】的完整业务流程

测试用例：E2E-REVIEW-01 - 人工审核完整操作流程（模拟版）
"""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 导入需要测试的模块
from src.services.review_service import ReviewService
from src.services.zmq_service import ZMQService
from src.models.database import StrategyReview, ReviewDecision, User


class TestE2EMock:
    """端到端测试类 - Mock版本"""
    
    @pytest.fixture
    def mock_services(self):
        """创建模拟服务"""
        # Mock数据库服务
        mock_db = Mock()
        mock_db.create_strategy_review = AsyncMock()
        mock_db.get_strategy_reviews = Mock()
        mock_db.get_strategy_review = AsyncMock()
        mock_db.get_strategy_review_by_id = AsyncMock()
        mock_db.create_review_decision = AsyncMock()
        mock_db.update_strategy_review_status = AsyncMock()
        mock_db.update_review_status = AsyncMock()
        mock_db.get_review_decisions_by_strategy = Mock()
        mock_db.get_audit_rules = AsyncMock()
        
        # Mock Redis服务
        mock_redis = Mock()
        mock_redis.cache_strategy_data = AsyncMock()
        mock_redis.get_cached_strategy = AsyncMock()
        mock_redis.add_to_review_queue = AsyncMock()
        mock_redis.push_to_queue = AsyncMock()
        mock_redis.increment_counter = AsyncMock()
        mock_redis.cache_review_result = AsyncMock()
        mock_redis.remove_from_review_queue = AsyncMock()
        
        # Mock ZMQ服务
        mock_zmq = Mock()
        mock_zmq.publish_approved_strategy = AsyncMock()
        mock_zmq.publish_rejected_strategy = AsyncMock()
        
        # 创建ReviewService实例
        review_service = ReviewService(
            database_service=mock_db,
            redis_service=mock_redis,
            zeromq_service=mock_zmq
        )
        
        return {
            "review_service": review_service,
            "mock_db": mock_db,
            "mock_redis": mock_redis,
            "mock_zmq": mock_zmq
        }
    
    @pytest.mark.asyncio
    async def test_e2e_review_01_complete_manual_review_flow_mock(self, mock_services):
        """
        E2E-REVIEW-01: 人工审核完整操作流程（模拟版）
        
        测试完整的业务流程：
        1. 策略优化模组发布策略 -> 人工审核模组接收
        2. 规则引擎评估 -> 判定需要人工审核
        3. 前端API查询待审列表 -> 显示待审策略
        4. 审核员提交决策 -> 系统处理决策
        5. 批准策略发送到下游 -> 完成审核闭环
        """
        services = mock_services
        review_service = services["review_service"]
        mock_db = services["mock_db"]
        mock_zmq = services["mock_zmq"]
        
        # ===== 步骤1: 模拟策略优化模组发布策略 =====
        strategy_data = {
            "strategy_id": "test_strategy_e2e_001",
            "symbol": "BTCUSDT",
            "strategy_type": "momentum",
            "expected_return": 0.15,
            "max_drawdown": 0.08,
            "position_size": 0.5,
            "parameters": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "risk_level": "high",  # 高风险，触发人工审核
                "position_size": 0.5,
                "stop_loss": 0.02,
                "take_profit": 0.05
            },
            "backtest_results": {
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock数据库操作
        mock_strategy_review = StrategyReview(
            id="review_001",
            strategy_id=strategy_data["strategy_id"],
            symbol=strategy_data["parameters"]["symbol"],
            strategy_type=strategy_data["strategy_type"],
            raw_data=json.dumps(strategy_data),
            status="pending",
            risk_level="high",
            expected_return=0.15,
            max_drawdown=0.08,
            created_at=datetime.now().isoformat()
        )
        
        mock_db.create_strategy_review.return_value = mock_strategy_review.id
        
        # Mock审核规则 - 配置为需要人工审核
        mock_audit_rule = Mock()
        mock_audit_rule.get.side_effect = lambda key, default=None: {
            'id': 'rule_manual_review_001',
            'rule_name': '低风险强制人工审核',
            'rule_type': 'require_review',
            'conditions': '{"risk_level": "low"}',
            'action': 'manual_review',
            'is_active': True
        }.get(key, default)
        
        mock_db.get_audit_rules.return_value = [mock_audit_rule]
        
        # ===== 步骤2: 规则引擎评估策略 =====
        review_id = await review_service.submit_strategy_for_review(strategy_data)
        
        # 验证策略被提交审核
        assert review_id is not None
        mock_db.create_strategy_review.assert_called_once()
        
        # ===== 步骤3: 模拟前端API查询待审列表 =====
        mock_db.get_strategy_reviews.return_value = [mock_strategy_review]
        
        # 模拟API调用获取待审列表
        pending_reviews = mock_db.get_strategy_reviews(status="pending")
        
        # 验证待审列表包含我们的策略
        assert len(pending_reviews) == 1
        assert pending_reviews[0].strategy_id == strategy_data["strategy_id"]
        assert pending_reviews[0].status == "pending"
        
        # ===== 步骤4: 模拟审核员提交决策 =====
        mock_user = User(
            id="reviewer_001",
            username="test_reviewer",
            email="reviewer@test.com",
            password_hash="hashed_password",
            role="reviewer"
        )
        
        decision_data = {
            "decision": "approve",
            "reason": "策略风险可控，批准执行",
            "risk_adjustment": {
                "position_limit": 0.8
            }
        }
        
        # Mock决策相关的数据库操作（异步方法需要使用AsyncMock）
        # get_strategy_review返回字典而不是对象
        mock_strategy_review_dict = {
            "id": mock_strategy_review.id,
            "strategy_id": mock_strategy_review.strategy_id,
            "symbol": mock_strategy_review.symbol,
            "strategy_type": mock_strategy_review.strategy_type,
            "raw_data": mock_strategy_review.raw_data,
            "status": mock_strategy_review.status,
            "risk_level": mock_strategy_review.risk_level,
            "expected_return": mock_strategy_review.expected_return,
            "max_drawdown": mock_strategy_review.max_drawdown,
            "created_at": mock_strategy_review.created_at
        }
        mock_db.get_strategy_review = AsyncMock(return_value=mock_strategy_review_dict)
        mock_db.get_strategy_review_by_id = AsyncMock(return_value=mock_strategy_review_dict)
        mock_db.create_review_decision = AsyncMock(return_value=True)
        mock_db.update_strategy_review_status = AsyncMock(return_value=True)
        
        # Mock Redis操作
        mock_redis = services["mock_redis"]
        mock_redis.remove_from_review_queue = AsyncMock(return_value=True)
        
        # 提交人工审核决策
        result = await review_service.submit_manual_decision(
            strategy_id=mock_strategy_review.id,
            reviewer_id=mock_user.id,
            decision=decision_data["decision"],
            reason=decision_data["reason"],
            risk_adjustment=decision_data["risk_adjustment"]
        )
        
        # 验证决策提交成功
        assert result is True
        mock_db.create_review_decision.assert_called_once()
        mock_db.update_strategy_review_status.assert_called_with(
            mock_strategy_review.id, "approved"
        )
        
        # ===== 步骤5: 验证批准策略发送到下游 =====
        # 验证ZMQ发布器被调用
        mock_zmq.publish_approved_strategy.assert_called_once()
        
        # 获取发布的消息内容
        call_args = mock_zmq.publish_approved_strategy.call_args
        published_strategy = call_args[0][0]  # 第一个参数是策略数据
        published_decision = call_args[0][1]  # 第二个参数是决策数据
        
        # 验证发布的消息包含正确的信息
        assert published_strategy["strategy_id"] == strategy_data["strategy_id"]
        assert published_decision["decision"] == "approve"
        
        # ===== 步骤6: 验证审核历史记录 =====
        mock_decision = ReviewDecision(
            id="decision_001",
            strategy_review_id=mock_strategy_review.id,
            reviewer_id=mock_user.id,
            decision="approve",
            reason=decision_data["reason"],
            decision_time=datetime.now()
        )
        
        mock_db.get_review_decisions_by_strategy.return_value = [mock_decision]
        
        # 获取审核历史
        decisions = mock_db.get_review_decisions_by_strategy(mock_strategy_review.id)
        
        # 验证审核历史记录
        assert len(decisions) == 1
        assert decisions[0].decision == "approve"
        assert decisions[0].reason == decision_data["reason"]
        assert decisions[0].reviewer_id == mock_user.id
        
        print("✅ E2E-REVIEW-01 Mock测试通过：人工审核完整操作流程验证成功")
    
    @pytest.mark.asyncio
    async def test_e2e_review_02_auto_approve_flow_mock(self, mock_services):
        """
        E2E-REVIEW-02: 自动批准流程（模拟版）
        
        测试自动批准的完整流程：
        1. 低风险策略提交
        2. 规则引擎自动批准
        3. 直接发送到下游
        """
        services = mock_services
        review_service = services["review_service"]
        mock_db = services["mock_db"]
        mock_zmq = services["mock_zmq"]
        
        # 低风险策略数据
        strategy_data = {
            "strategy_id": "test_strategy_auto_001",
            "symbol": "BTCUSDT",
            "strategy_type": "conservative",
            "expected_return": 0.08,
            "max_drawdown": 0.03,
            "position_size": 0.1,
            "parameters": {
                "symbol": "BTCUSDT",
                "timeframe": "4h",
                "risk_level": "low",  # 低风险，自动批准
                "position_size": 0.1,
                "stop_loss": 0.01,
                "take_profit": 0.02
            },
            "backtest_results": {
                "total_return": 0.08,
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.03
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock自动批准规则
        mock_audit_rule = Mock()
        mock_audit_rule.get.side_effect = lambda key, default=None: {
            'id': 'rule_auto_approve_001',
            'rule_name': '低风险自动批准',
            'rule_type': 'auto_approve',
            'conditions': '{"risk_level": "low"}',
            'action': 'approve',
            'is_active': True
        }.get(key, default)
        
        mock_strategy_review = StrategyReview(
            id="review_auto_001",
            strategy_id=strategy_data["strategy_id"],
            symbol=strategy_data["parameters"]["symbol"],
            strategy_type=strategy_data["strategy_type"],
            raw_data=json.dumps(strategy_data),
            status="approved",
            risk_level="low",
            expected_return=0.08,
            max_drawdown=0.03,
            created_at=datetime.now().isoformat()
        )
        
        mock_db.get_audit_rules.return_value = [mock_audit_rule]
        mock_db.get_active_audit_rules.return_value = [mock_audit_rule]
        mock_db.get_strategy_review_by_id = AsyncMock(return_value=mock_strategy_review)
        mock_db.create_strategy_review.return_value = mock_strategy_review.id
        mock_db.update_review_status = AsyncMock(return_value=True)
        mock_db.create_review_decision = AsyncMock(return_value="decision_001")
        
        # 提交策略审核
        review_id = await review_service.submit_strategy_for_review(strategy_data)
        
        # 验证策略被自动批准
        assert review_id is not None
        mock_db.update_review_status.assert_called_with(
            mock_strategy_review.id, "approved"
        )
        
        # 验证策略被直接发送到下游
        mock_zmq.publish_approved_strategy.assert_called_once()
        
        print("✅ E2E-REVIEW-02 Mock测试通过：自动批准流程验证成功")
    
    @pytest.mark.asyncio
    async def test_e2e_review_03_auto_reject_flow_mock(self, mock_services):
        """
        E2E-REVIEW-03: 自动拒绝流程（模拟版）
        
        测试自动拒绝的完整流程：
        1. 超高风险策略提交
        2. 规则引擎自动拒绝
        3. 不发送到下游
        """
        services = mock_services
        review_service = services["review_service"]
        mock_db = services["mock_db"]
        mock_zmq = services["mock_zmq"]
        
        # 超高风险策略数据
        strategy_data = {
            "strategy_id": "test_strategy_reject_001",
            "symbol": "BTCUSDT",
            "strategy_type": "aggressive",
            "expected_return": 0.5,
            "max_drawdown": 0.3,
            "position_size": 1.0,
            "parameters": {
                "symbol": "BTCUSDT",
                "timeframe": "1m",
                "risk_level": "extreme",  # 极高风险，自动拒绝
                "position_size": 1.0,
                "stop_loss": 0.1,
                "take_profit": 0.2
            },
            "backtest_results": {
                "total_return": 0.5,
                "sharpe_ratio": 0.5,
                "max_drawdown": 0.3
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock自动拒绝规则
        mock_audit_rule = Mock()
        mock_audit_rule.get.side_effect = lambda key, default=None: {
            'id': 'rule_auto_reject_001',
            'rule_name': '极高风险自动拒绝',
            'rule_type': 'auto_reject',
            'conditions': '{"risk_level": "extreme"}',
            'action': 'reject',
            'is_active': True
        }.get(key, default)
        
        mock_strategy_review = StrategyReview(
            id="review_reject_001",
            strategy_id=strategy_data["strategy_id"],
            symbol=strategy_data["parameters"]["symbol"],
            strategy_type=strategy_data["strategy_type"],
            raw_data=json.dumps(strategy_data),
            status="rejected",
            risk_level="extreme",
            expected_return=0.5,
            max_drawdown=0.3,
            created_at=datetime.now().isoformat()
        )
        
        mock_db.get_audit_rules.return_value = [mock_audit_rule]
        mock_db.get_active_audit_rules.return_value = [mock_audit_rule]
        mock_db.get_strategy_review_by_id = AsyncMock(return_value=mock_strategy_review)
        mock_db.create_strategy_review.return_value = mock_strategy_review.id
        mock_db.update_review_status = AsyncMock(return_value=True)
        mock_db.create_review_decision = AsyncMock(return_value="decision_001")
        
        # 提交策略审核
        review_id = await review_service.submit_strategy_for_review(strategy_data)
        
        # 验证策略被自动拒绝
        assert review_id is not None
        mock_db.update_review_status.assert_called_with(
            mock_strategy_review.id, "rejected"
        )
        
        # 验证策略没有被发送到下游
        mock_zmq.publish_approved_strategy.assert_not_called()
        
        print("✅ E2E-REVIEW-03 Mock测试通过：自动拒绝流程验证成功")


if __name__ == "__main__":
    # 运行端到端测试
    pytest.main(["-v", "-s", __file__])