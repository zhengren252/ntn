#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - API输入验证测试

测试用例：
- UNIT-RG-API-01: API 输入验证 - 无效决策值
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from src.services.review_service import ReviewService
from src.services.database_service import DatabaseService
from src.services.redis_service import RedisService
from src.services.zmq_service import ZMQService

class TestAPIValidation:
    """API输入验证测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_services(self):
        """Mock所有服务依赖"""
        with patch('main.review_service') as mock_review, \
             patch('main.db_manager') as mock_db, \
             patch('main.zmq_service') as mock_zmq, \
             patch('main.auth_manager') as mock_auth_manager, \
             patch('main.security') as mock_security:
            
            # 配置mock服务
            mock_review.submit_manual_decision = AsyncMock()
            mock_review.publish_approved_strategy = AsyncMock()
            mock_db.get_strategy_review_by_id = MagicMock()
            mock_db.create_review_decision = MagicMock(return_value=True)
            mock_db.update_strategy_review_status = MagicMock()
            mock_zmq.publish_approved_strategy = AsyncMock()
            
            # Mock认证管理器
            from models.database import User
            mock_user = User(
                id='test_user_001',
                username='test_user',
                email='test@example.com',
                password_hash='hashed_password',
                role='reviewer',
                is_active=True
            )
            
            # 配置auth_manager.verify_token返回用户ID
            mock_auth_manager.verify_token.return_value = 'test_user_001'
            
            # 配置db_manager.get_user_by_id返回用户对象
            mock_db.get_user_by_id.return_value = mock_user
            
            yield {
                'review': mock_review,
                'db': mock_db,
                'zmq': mock_zmq,
                'auth_manager': mock_auth_manager,
                'security': mock_security
            }
    
    @pytest.fixture
    def valid_review_data(self):
        """有效的审核记录数据"""
        return {
            'strategy_id': 'test_strategy_001',
            'strategy_data': json.dumps({
                'strategy_type': 'momentum',
                'position_size': 0.05,
                'risk_level': 'medium'
            }),
            'status': 'pending_manual_review',
            'created_at': '2024-01-01T10:00:00Z'
        }
    
    def test_unit_rg_api_01_invalid_decision_value(self, client, mock_services, valid_review_data):
        """
        UNIT-RG-API-01: API 输入验证 - 无效决策值
        
        测试步骤：
        向 POST /api/reviews/{id}/decision 端点发送一个decision字段为无效值（如'maybe'）的请求
        
        验收标准：
        API返回 HTTP 状态码 400 Bad Request
        """
        # 准备测试数据
        review_id = "test_review_001"
        
        # Mock数据库返回有效的审核记录
        from models.database import StrategyReview
        mock_review = StrategyReview(
            id=review_id,
            strategy_id=valid_review_data['strategy_id'],
            symbol='BTCUSDT',
            strategy_type='momentum',
            expected_return=0.15,
            risk_level='medium',
            max_drawdown=0.10,
            status='pending',
            raw_data=valid_review_data['strategy_data']
        )
        mock_services['db'].get_strategy_review_by_id.return_value = mock_review
        
        # 测试无效的decision值
        invalid_decisions = ['maybe', 'unknown', 'pending', 'invalid', '', None, 123, []]
        
        for invalid_decision in invalid_decisions:
            # 发送包含无效decision值的请求
            response = client.post(
                f"/api/reviews/{review_id}/decision",
                json={
                    "decision": invalid_decision,
                    "reason": "Test reason"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证返回400状态码
            assert response.status_code == 400, f"Expected 400 for decision '{invalid_decision}', got {response.status_code}"
            
            # 验证错误响应格式
            error_data = response.json()
            assert "detail" in error_data
            assert isinstance(error_data["detail"], list)
            
            print(f"✅ 无效决策值 '{invalid_decision}' 正确返回400错误")
    
    def test_valid_decision_values(self, client, mock_services, valid_review_data):
        """
        补充测试：验证有效的decision值能正常处理
        """
        review_id = "test_review_001"
        
        # Mock数据库返回有效的审核记录
        from models.database import StrategyReview
        mock_review = StrategyReview(
            id=review_id,
            strategy_id=valid_review_data['strategy_id'],
            symbol='BTCUSDT',
            strategy_type='momentum',
            expected_return=0.15,
            risk_level='medium',
            max_drawdown=0.10,
            status='pending',
            raw_data=valid_review_data['strategy_data']
        )
        mock_services['db'].get_strategy_review_by_id.return_value = mock_review
        mock_services['db'].create_review_decision.return_value = True
        mock_services['db'].update_strategy_review_status.return_value = True
        
        # 测试有效的decision值
        valid_decisions = ['approve', 'reject', 'defer']
        
        for valid_decision in valid_decisions:
            # 发送包含有效decision值的请求
            response = client.post(
                f"/api/reviews/{review_id}/decision",
                json={
                    "decision": valid_decision,
                    "reason": "Test reason"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            # 验证不返回400状态码（应该是200或其他成功状态码）
            assert response.status_code != 400, f"Valid decision '{valid_decision}' should not return 400"
            
            print(f"✅ 有效决策值 '{valid_decision}' 正确处理")
    
    def test_missing_required_fields(self, client, mock_services, valid_review_data):
        """
        补充测试：验证缺少必需字段的请求
        """
        review_id = "test_review_001"
        
        # Mock数据库返回有效的审核记录
        from models.database import StrategyReview
        mock_review = StrategyReview(
            id=review_id,
            strategy_id=valid_review_data['strategy_id'],
            symbol='BTCUSDT',
            strategy_type='momentum',
            expected_return=0.15,
            risk_level='medium',
            max_drawdown=0.10,
            status='pending',
            raw_data=valid_review_data['strategy_data']
        )
        mock_services['db'].get_strategy_review_by_id.return_value = mock_review
        
        # 测试缺少decision字段
        response = client.post(
            f"/api/reviews/{review_id}/decision",
            json={
                "reason": "Test reason"
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 400
        print("✅ 缺少decision字段正确返回400错误")
        
        # 测试缺少reason字段
        response = client.post(
            f"/api/reviews/{review_id}/decision",
            json={
                "decision": "approve"
            },
            headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 400
        print("✅ 缺少reason字段正确返回400错误")
    
    def test_invalid_json_format(self, client):
        """
        补充测试：验证无效JSON格式的请求
        """
        review_id = "test_review_001"
        
        # 发送无效JSON格式的请求
        response = client.post(
            f"/api/reviews/{review_id}/decision",
            data="{invalid json}",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json"
            }
        )
        
        # 验证返回400状态码 (JSON解析错误)
        assert response.status_code == 400
        print("✅ 无效JSON格式正确返回400错误")
    
    def test_nonexistent_review_id(self, client, mock_services):
        """
        补充测试：验证不存在的审核ID
        """
        review_id = "nonexistent_review_001"
        
        # Mock数据库返回None（审核记录不存在）
        mock_services['db'].get_strategy_review_by_id.return_value = None
        
        # 发送请求
        response = client.post(
            f"/api/reviews/{review_id}/decision",
            json={
                "decision": "approve",
                "reason": "Test reason"
            },
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证返回404状态码（审核记录不存在）
        assert response.status_code == 404
        print("✅ 不存在的审核ID正确返回404错误")

if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])