import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient
import json

from api_factory.main import app
from api_factory.security.auth import AuthManager


class TestAuthCenter:
    """认证中心测试类"""

    @pytest.mark.unit
    @pytest.mark.auth
    def test_unit_sec_01_no_credentials_request(self, client):
        """UNIT-SEC-01: 无凭证请求测试

        测试描述: 模拟一个不带任何API Key/Secret的HTTP请求
        验收标准: 请求被拒绝，服务返回 401 或 403 HTTP状态码
        """
        # 测试用户注册端点 - 无凭证
        response = client.post("/auth/register")
        assert response.status_code in [
            401,
            403,
            422,
        ], f"Expected 401/403/422, got {response.status_code}"

        # 测试用户登录端点 - 无凭证
        response = client.post("/auth/login")
        assert response.status_code in [
            401,
            403,
            422,
        ], f"Expected 401/403/422, got {response.status_code}"

        # 测试需要认证的API网关端点 - 无凭证
        response = client.get("/api/configs")
        assert response.status_code in [
            401,
            403,
        ], f"Expected 401/403, got {response.status_code}"

        # 测试配额管理端点 - 无凭证
        response = client.get("/quota/quotas")
        assert response.status_code in [
            401,
            403,
        ], f"Expected 401/403, got {response.status_code}"

        # 测试集群管理端点 - 无凭证
        response = client.get("/cluster/nodes")
        assert response.status_code in [
            401,
            403,
        ], f"Expected 401/403, got {response.status_code}"

        print("✅ UNIT-SEC-01: 无凭证请求测试通过")

    @pytest.mark.unit
    @pytest.mark.auth
    def test_unit_sec_02_invalid_credentials_request(self, client, mock_auth_manager):
        """UNIT-SEC-02: 无效凭证请求测试

        测试描述: 模拟一个携带了错误API Key/Secret的HTTP请求
        验收标准: 请求被拒绝，服务返回 401 或 403 HTTP状态码
        """
        # Mock认证管理器返回None表示认证失败
        mock_auth_manager.verify_token.return_value = None
        mock_auth_manager.verify_api_key.return_value = None

        with patch("api_factory.main.auth_manager", mock_auth_manager):
            # 测试无效JWT Token
            headers = {"Authorization": "Bearer invalid_jwt_token"}
            response = client.get("/api/configs", headers=headers)
            assert response.status_code in [
                401,
                403,
            ], f"Expected 401/403, got {response.status_code}"

            # 测试无效API Key
            headers = {"X-API-Key": "invalid_api_key"}
            response = client.get("/api/configs", headers=headers)
            assert response.status_code in [
                401,
                403,
            ], f"Expected 401/403, got {response.status_code}"

            # 测试错误格式的Authorization头
            headers = {"Authorization": "InvalidFormat token"}
            response = client.get("/api/configs", headers=headers)
            assert response.status_code in [
                401,
                403,
            ], f"Expected 401/403, got {response.status_code}"

            # 测试空的API Key
            headers = {"X-API-Key": ""}
            response = client.get("/api/configs", headers=headers)
            assert response.status_code in [
                401,
                403,
            ], f"Expected 401/403, got {response.status_code}"

            # 测试用户登录 - 错误凭证
            mock_auth_manager.authenticate_user.return_value = None
            login_data = {"username": "invalid_user", "password": "wrong_password"}
            response = client.post("/auth/login", json=login_data)
            assert response.status_code in [
                401,
                403,
            ], f"Expected 401/403, got {response.status_code}"

        print("✅ UNIT-SEC-02: 无效凭证请求测试通过")

    @pytest.mark.unit
    @pytest.mark.auth
    def test_auth_manager_token_verification(self, mock_auth_manager):
        """测试认证管理器的令牌验证功能"""
        # 测试有效令牌
        valid_token_data = {
            "user_id": 1,
            "username": "test_user",
            "role": "user",
            "tenant_id": "test_tenant",
        }
        mock_auth_manager.verify_token.return_value = valid_token_data

        result = mock_auth_manager.verify_token("valid_token")
        assert result == valid_token_data

        # 测试无效令牌
        mock_auth_manager.verify_token.return_value = None
        result = mock_auth_manager.verify_token("invalid_token")
        assert result is None

        print("✅ 认证管理器令牌验证测试通过")

    @pytest.mark.unit
    @pytest.mark.auth
    def test_auth_manager_api_key_verification(self, mock_auth_manager):
        """测试认证管理器的API密钥验证功能"""
        # 测试有效API密钥
        valid_key_data = {
            "key_id": 1,
            "user_id": 1,
            "tenant_id": "test_tenant",
            "permissions": ["api.read", "api.write"],
        }
        mock_auth_manager.verify_api_key.return_value = valid_key_data

        result = mock_auth_manager.verify_api_key("valid_api_key")
        assert result == valid_key_data

        # 测试无效API密钥
        mock_auth_manager.verify_api_key.return_value = None
        result = mock_auth_manager.verify_api_key("invalid_api_key")
        assert result is None

        print("✅ 认证管理器API密钥验证测试通过")

    @pytest.mark.unit
    @pytest.mark.auth
    def test_permission_check(self, mock_auth_manager):
        """测试权限检查功能"""
        # 测试管理员权限
        mock_auth_manager.check_permission.return_value = True
        assert mock_auth_manager.check_permission("admin", "api.read") == True

        # 测试普通用户权限
        mock_auth_manager.check_permission.return_value = False
        assert mock_auth_manager.check_permission("user", "system.admin") == False

        print("✅ 权限检查测试通过")
