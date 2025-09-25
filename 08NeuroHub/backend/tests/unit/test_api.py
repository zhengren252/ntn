#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API单元测试

测试总控模块API端点的核心逻辑，包括：
- 控制指令验证
- 错误处理
- 响应格式
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes import api_router
from app.core.zmq_manager import ZMQManager

# 创建测试应用
app = FastAPI()
app.include_router(api_router, prefix="/api")

# 创建测试客户端
client = TestClient(app)

class TestAPIEndpoints:
    """API端点测试类"""
    
    @pytest.mark.unit
    @patch('app.api.routes.get_zmq_manager')
    def test_unit_api_01_invalid_command_type(self, mock_get_zmq_manager):
        """
        UNIT-API-01: API无效控制指令测试
        
        测试场景：
        1. 向 POST /api/commands/execute 端点发送无效command类型
        2. 验证返回422状态码和错误信息
        """
        # 准备测试数据
        invalid_command = {
            "command": "DO_NOTHING",  # 无效的指令类型
            "payload": {"test": "data"}
        }
        
        # Mock ZMQ管理器
        mock_zmq_manager = AsyncMock(spec=ZMQManager)
        mock_get_zmq_manager.return_value = mock_zmq_manager
        
        # 发送请求
        response = client.post(
            "/api/commands/execute",
            json=invalid_command
        )
        
        # 验证响应
        assert response.status_code == 422
        response_data = response.json()
        assert "Invalid command type" in response_data["detail"]
        assert "DO_NOTHING" in response_data["detail"]
        
        # 验证ZMQ管理器没有被调用（因为验证失败）
        mock_zmq_manager.publish_message.assert_not_called()
        
        print("✅ UNIT-API-01: API无效控制指令测试通过")
    
    @pytest.mark.unit
    @patch('app.api.routes.get_zmq_manager')
    def test_valid_command_execution(self, mock_get_zmq_manager):
        """
        测试有效控制指令的执行
        """
        # 准备测试数据
        valid_command = {
            "command": "SWITCH_MODE",
            "payload": {"mode": "AGGRESSIVE"}
        }
        
        # Mock ZMQ管理器
        mock_zmq_manager = AsyncMock(spec=ZMQManager)
        mock_get_zmq_manager.return_value = mock_zmq_manager
        
        # 发送请求
        response = client.post(
            "/api/commands/execute",
            json=valid_command
        )
        
        # 验证响应
        assert response.status_code == 200
        response_data = response.json()
        assert "指令 SWITCH_MODE 执行成功" in response_data["message"]
        
        # 验证ZMQ管理器被正确调用
        mock_zmq_manager.publish_message.assert_called_once()
        call_args = mock_zmq_manager.publish_message.call_args
        assert call_args[0][0] == "control.commands"  # 主题
        
        # 验证消息内容
        message = call_args[0][1]
        assert message["type"] == "command"
        assert message["command"] == "SWITCH_MODE"
        assert message["payload"] == {"mode": "AGGRESSIVE"}
        assert message["source"] == "master_control"
        
        print("✅ 有效控制指令执行测试通过")
    
    @pytest.mark.unit
    @patch('app.api.routes.get_zmq_manager')
    def test_command_validation_edge_cases(self, mock_get_zmq_manager):
        """
        测试指令验证的边界情况
        """
        # Mock ZMQ管理器
        mock_zmq_manager = AsyncMock(spec=ZMQManager)
        mock_get_zmq_manager.return_value = mock_zmq_manager
        
        # 测试空指令
        response = client.post(
            "/api/commands/execute",
            json={"command": "", "payload": {}}
        )
        assert response.status_code == 422
        
        # 测试大小写敏感
        response = client.post(
            "/api/commands/execute",
            json={"command": "switch_mode", "payload": {}}
        )
        assert response.status_code == 422
        
        # 测试无payload的有效指令
        response = client.post(
            "/api/commands/execute",
            json={"command": "EMERGENCY_SHUTDOWN"}
        )
        assert response.status_code == 200
        
        print("✅ 指令验证边界情况测试通过")

if __name__ == "__main__":
    # 运行测试
    test_api = TestAPIEndpoints()
    
    # 模拟pytest环境
    import sys
    from unittest.mock import MagicMock
    
    # Mock get_zmq_manager
    with patch('app.api.routes.get_zmq_manager') as mock_get_zmq_manager:
        mock_zmq_manager = AsyncMock(spec=ZMQManager)
        mock_get_zmq_manager.return_value = mock_zmq_manager
        
        try:
            test_api.test_unit_api_01_invalid_command_type()
            test_api.test_valid_command_execution()
            test_api.test_command_validation_edge_cases()
            print("\n🎉 所有API单元测试通过！")
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            sys.exit(1)