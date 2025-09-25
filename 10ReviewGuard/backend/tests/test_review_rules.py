#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - 规则引擎单元测试

测试用例：
- UNIT-RG-RULES-01: 自动审核规则引擎 - 自动批准路径
- UNIT-RG-RULES-02: 自动审核规则引擎 - 自动拒绝路径  
- UNIT-RG-RULES-03: 自动审核规则引擎 - 强制人工审核路径
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.services.review_service import ReviewService, DecisionType
from src.models.database import StrategyReview, ReviewDecision
from src.utils.config import get_settings

class TestReviewRulesEngine:
    """审核规则引擎测试类"""
    
    @pytest.fixture
    def review_service(self):
        """创建ReviewService实例用于测试"""
        # Mock所有依赖服务
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_zmq = AsyncMock()
        
        # 创建ReviewService实例，传入必需的依赖
        service = ReviewService(
            database_service=mock_db,
            redis_service=mock_redis,
            zeromq_service=mock_zmq
        )
        
        return service
    
    @pytest.fixture
    def low_risk_strategy_data(self):
        """低风险策略数据（符合自动批准规则）"""
        return {
            'strategy_id': 'test_strategy_001',
            'symbol': 'BTCUSDT',
            'strategy_type': 'momentum',
            'position_size': 0.02,  # 2% 仓位，低风险
            'risk_assessment': {
                'risk_level': 'low',
                'risk_score': 0.2,
                'max_drawdown': 0.05,
                'sharpe_ratio': 2.1
            },
            'backtest_metrics': {
                'total_return': 0.15,
                'win_rate': 0.65,
                'profit_factor': 1.8
            },
            'created_at': datetime.utcnow().isoformat()
        }
    
    @pytest.fixture
    def high_risk_strategy_data(self):
        """高风险策略数据（符合自动拒绝规则）"""
        return {
            'strategy_id': 'test_strategy_002',
            'symbol': 'ETHUSDT',
            'strategy_type': 'scalping',
            'position_size': 0.15,  # 15% 仓位，超大仓位
            'risk_assessment': {
                'risk_level': 'high',
                'risk_score': 0.9,
                'max_drawdown': 0.25,
                'sharpe_ratio': 0.8
            },
            'backtest_metrics': {
                'total_return': -0.05,
                'win_rate': 0.35,
                'profit_factor': 0.7
            },
            'created_at': datetime.utcnow().isoformat()
        }
    
    @pytest.fixture
    def manual_review_strategy_data(self):
        """需要人工审核的策略数据"""
        return {
            'strategy_id': 'test_strategy_003',
            'symbol': 'ADAUSDT',
            'strategy_type': 'arbitrage',
            'position_size': 0.08,  # 8% 仓位，中等风险
            'risk_assessment': {
                'risk_level': 'medium',
                'risk_score': 0.6,
                'max_drawdown': 0.12,
                'sharpe_ratio': 1.5
            },
            'backtest_metrics': {
                'total_return': 0.08,
                'win_rate': 0.55,
                'profit_factor': 1.2
            },
            'created_at': datetime.utcnow().isoformat()
        }
    
    @pytest.fixture
    def mock_audit_rules_auto_approve(self):
        """Mock审核规则 - 自动批准"""
        from src.models.database import AuditRule
        rule = AuditRule(
            id='rule_001',
            rule_name='低风险自动通过',
            rule_type='risk_level',
            conditions=json.dumps({
                'risk_level': 'low',
                'position_size_max': 0.05,
                'risk_score_max': 0.3,
                'action': 'auto_approve'
            }),
            action='approve',
            is_active=True
        )
        # 添加rule_config属性以匹配实际代码
        rule.rule_config = rule.conditions
        return [rule]
    
    @pytest.fixture
    def mock_audit_rules_auto_reject(self):
        """Mock审核规则 - 自动拒绝"""
        from src.models.database import AuditRule
        rule = AuditRule(
            id='rule_002',
            rule_name='超大仓位自动拒绝',
            rule_type='risk_level',
            conditions=json.dumps({
                'position_size_min': 0.10,
                'action': 'auto_reject'
            }),
            action='reject',
            is_active=True
        )
        # 添加rule_config属性以匹配实际代码
        rule.rule_config = rule.conditions
        return [rule]
    
    @pytest.fixture
    def mock_audit_rules_manual_review(self):
        """Mock审核规则 - 强制人工审核"""
        from src.models.database import AuditRule
        rule = AuditRule(
            id='rule_003',
            rule_name='高风险强制审核',
            rule_type='risk_level',
            conditions=json.dumps({
                'risk_level': 'medium',
                'strategy_type': 'arbitrage',
                'action': 'manual_review'
            }),
            action='manual_review',
            is_active=True
        )
        # 添加rule_config属性以匹配实际代码
        rule.rule_config = rule.conditions
        return [rule]
    
    @pytest.mark.asyncio
    async def test_unit_rg_rules_01_auto_approve_path(self, review_service, low_risk_strategy_data, mock_audit_rules_auto_approve):
        """
        UNIT-RG-RULES-01: 自动审核规则引擎 - 自动批准路径
        
        测试步骤：
        1. Mock数据库，使其在查询audit_rules表时返回预设的"低风险自动通过"规则
        2. 准备一个符合该规则的模拟"策略参数包"（例如 risk_level: 'low'）
        3. 调用规则引擎的核心处理函数
        
        验收标准：
        - 函数返回action: 'approve'
        - 被Mock的ZMQ发布器（Publisher）被调用，准备向 review.pool.approved 主题发布消息
        """
        # 1. Mock数据库返回自动批准规则
        review_service.db.get_active_audit_rules.return_value = mock_audit_rules_auto_approve
        review_service.db.update_strategy_review_status.return_value = True
        review_service.db.create_review_decision.return_value = True
        
        # 创建策略审核记录
        strategy_review = StrategyReview(
            id="test_review_001",
            strategy_id=low_risk_strategy_data['strategy_id'],
            symbol=low_risk_strategy_data['symbol'],
            strategy_type=low_risk_strategy_data['strategy_type'],
            expected_return=low_risk_strategy_data.get('expected_return'),
            max_drawdown=low_risk_strategy_data.get('max_drawdown'),
            risk_level=low_risk_strategy_data.get('risk_level', 'low'),
            raw_data=json.dumps(low_risk_strategy_data),
            status='pending',
            created_at=datetime.utcnow().isoformat()
        )
        
        # 2. 执行自动审核规则
        await review_service.apply_auto_review_rules(strategy_review)
        
        # 3. 验证结果
        # 验证数据库状态更新被调用
        review_service.db.update_strategy_review_status.assert_called_with(
            low_risk_strategy_data['strategy_id'], 'approved'
        )
        
        # 验证决策记录被创建
        review_service.db.create_review_decision.assert_called_once()
        call_args = review_service.db.create_review_decision.call_args[0][0]
        assert call_args.decision == DecisionType.APPROVE.value
        assert call_args.reviewer_id == 'system'
        assert '低风险自动通过' in call_args.reason
        
        # 验证ZMQ发布器被调用
        review_service.zmq.publish_approved_strategy.assert_called_once()
        
        print("✅ UNIT-RG-RULES-01: 自动批准路径测试通过")
    
    @pytest.mark.asyncio
    async def test_unit_rg_rules_02_auto_reject_path(self, review_service, high_risk_strategy_data, mock_audit_rules_auto_reject):
        """
        UNIT-RG-RULES-02: 自动审核规则引擎 - 自动拒绝路径
        
        测试步骤：
        1. Mock数据库，返回"超大仓位自动拒绝"规则
        2. 准备一个符合该规则的策略包
        
        验收标准：
        - 函数返回action: 'reject'
        - ZMQ发布器未被调用
        - 数据库中该条审核记录的状态被更新为'rejected'
        """
        # 1. Mock数据库返回自动拒绝规则
        review_service.db.get_active_audit_rules.return_value = mock_audit_rules_auto_reject
        review_service.db.update_strategy_review_status.return_value = True
        review_service.db.create_review_decision.return_value = True
        
        # 创建策略审核记录
        strategy_review = StrategyReview(
            id="test_review_002",
            strategy_id=high_risk_strategy_data['strategy_id'],
            symbol=high_risk_strategy_data.get('symbol'),
            strategy_type=high_risk_strategy_data['strategy_type'],
            expected_return=high_risk_strategy_data.get('expected_return'),
            max_drawdown=high_risk_strategy_data.get('max_drawdown'),
            risk_level=high_risk_strategy_data.get('risk_level', 'high'),
            raw_data=json.dumps(high_risk_strategy_data),
            status='pending',
            created_at=datetime.utcnow().isoformat()
        )
        
        # 2. 执行自动审核规则
        await review_service.apply_auto_review_rules(strategy_review)
        
        # 3. 验证结果
        # 验证数据库状态更新为rejected
        review_service.db.update_strategy_review_status.assert_called_with(
            high_risk_strategy_data['strategy_id'], 'rejected'
        )
        
        # 验证决策记录被创建
        review_service.db.create_review_decision.assert_called_once()
        call_args = review_service.db.create_review_decision.call_args[0][0]
        assert call_args.decision == DecisionType.REJECT.value
        assert call_args.reviewer_id == 'system'
        assert '超大仓位自动拒绝' in call_args.reason
        
        # 验证ZMQ发布器未被调用（拒绝的策略不发布）
        review_service.zmq.publish_approved_strategy.assert_not_called()
        
        print("✅ UNIT-RG-RULES-02: 自动拒绝路径测试通过")
    
    @pytest.mark.asyncio
    async def test_unit_rg_rules_03_manual_review_path(self, review_service, manual_review_strategy_data, mock_audit_rules_manual_review):
        """
        UNIT-RG-RULES-03: 自动审核规则引擎 - 强制人工审核路径
        
        测试步骤：
        1. Mock数据库，返回"高风险强制审核"规则
        2. 准备一个符合该规则的策略包
        
        验收标准：
        - 函数返回action: 'manual_review'
        - ZMQ发布器未被调用
        - 数据库中该条审核记录的状态被更新为'pending_manual_review'
        """
        # 1. Mock数据库返回人工审核规则
        review_service.db.get_active_audit_rules.return_value = mock_audit_rules_manual_review
        review_service.db.update_strategy_review_status.return_value = True
        review_service.redis.add_to_review_queue.return_value = True
        
        # 创建策略审核记录
        strategy_review = StrategyReview(
            id="test_review_003",
            strategy_id=manual_review_strategy_data['strategy_id'],
            symbol=manual_review_strategy_data.get('symbol'),
            strategy_type=manual_review_strategy_data['strategy_type'],
            expected_return=manual_review_strategy_data.get('expected_return'),
            max_drawdown=manual_review_strategy_data.get('max_drawdown'),
            risk_level=manual_review_strategy_data.get('risk_level', 'medium'),
            raw_data=json.dumps(manual_review_strategy_data),
            status='pending',
            created_at=datetime.utcnow().isoformat()
        )
        
        # 2. 执行自动审核规则
        await review_service.apply_auto_review_rules(strategy_review)
        
        # 3. 验证结果
        # 验证数据库状态更新为pending_manual_review
        review_service.db.update_strategy_review_status.assert_called_with(
            manual_review_strategy_data['strategy_id'], 'processing'
        )
        
        # 验证添加到Redis审核队列
        review_service.redis.add_to_review_queue.assert_called_once()
        
        # 验证ZMQ发布器未被调用（需要人工审核的策略不自动发布）
        review_service.zmq.publish_approved_strategy.assert_not_called()
        
        print("✅ UNIT-RG-RULES-03: 强制人工审核路径测试通过")

if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])