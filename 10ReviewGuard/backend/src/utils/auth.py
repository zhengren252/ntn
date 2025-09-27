#!/usr/bin/env python3
"""
ReviewGuard人工审核模组 - 认证管理
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from .config import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_expire_minutes
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        try:
            # 生成盐值并哈希密码
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def create_token(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """创建JWT令牌"""
        try:
            # 计算过期时间
            expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
            
            # 构建载荷
            payload = {
                'user_id': user_id,
                'exp': expire,
                'iat': datetime.utcnow(),
                'type': 'access_token'
            }
            
            # 添加额外声明
            if additional_claims:
                payload.update(additional_claims)
            
            # 生成令牌
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"Token created for user: {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Error creating token: {e}")
            raise
    
    def verify_token(self, token: str) -> str:
        """验证JWT令牌并返回用户ID"""
        try:
            # 解码令牌
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # 检查令牌类型
            if payload.get('type') != 'access_token':
                raise jwt.InvalidTokenError("Invalid token type")
            
            user_id = payload.get('user_id')
            if not user_id:
                raise jwt.InvalidTokenError("Missing user_id in token")
            
            return user_id
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            raise jwt.InvalidTokenError("Token verification failed")
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """解码令牌（不验证过期时间）"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            raise
    
    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        try:
            # 刷新令牌有效期更长（7天）
            expire = datetime.utcnow() + timedelta(days=7)
            
            payload = {
                'user_id': user_id,
                'exp': expire,
                'iat': datetime.utcnow(),
                'type': 'refresh_token'
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"Refresh token created for user: {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise
    
    def verify_refresh_token(self, token: str) -> str:
        """验证刷新令牌"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            if payload.get('type') != 'refresh_token':
                raise jwt.InvalidTokenError("Invalid token type")
            
            user_id = payload.get('user_id')
            if not user_id:
                raise jwt.InvalidTokenError("Missing user_id in token")
            
            return user_id
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            raise jwt.InvalidTokenError("Refresh token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise
        except Exception as e:
            logger.error(f"Error verifying refresh token: {e}")
            raise jwt.InvalidTokenError("Refresh token verification failed")
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """获取令牌信息"""
        try:
            payload = self.decode_token(token)
            
            return {
                'user_id': payload.get('user_id'),
                'type': payload.get('type'),
                'issued_at': datetime.fromtimestamp(payload.get('iat', 0)),
                'expires_at': datetime.fromtimestamp(payload.get('exp', 0)),
                'is_expired': datetime.utcnow() > datetime.fromtimestamp(payload.get('exp', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {}


class PermissionManager:
    """权限管理器"""
    
    # 角色权限映射
    ROLE_PERMISSIONS = {
        'admin': {
            'review_strategies',
            'manage_rules',
            'view_statistics',
            'manage_users',
            'system_config'
        },
        'reviewer': {
            'review_strategies',
            'view_statistics'
        },
        'viewer': {
            'view_statistics'
        }
    }
    
    @classmethod
    def has_permission(cls, user_role: str, permission: str) -> bool:
        """检查用户是否有指定权限"""
        role_permissions = cls.ROLE_PERMISSIONS.get(user_role, set())
        return permission in role_permissions
    
    @classmethod
    def get_user_permissions(cls, user_role: str) -> set:
        """获取用户所有权限"""
        return cls.ROLE_PERMISSIONS.get(user_role, set())
    
    @classmethod
    def can_review_strategies(cls, user_role: str) -> bool:
        """检查是否可以审核策略"""
        return cls.has_permission(user_role, 'review_strategies')
    
    @classmethod
    def can_manage_rules(cls, user_role: str) -> bool:
        """检查是否可以管理规则"""
        return cls.has_permission(user_role, 'manage_rules')
    
    @classmethod
    def can_view_statistics(cls, user_role: str) -> bool:
        """检查是否可以查看统计"""
        return cls.has_permission(user_role, 'view_statistics')
    
    @classmethod
    def can_manage_users(cls, user_role: str) -> bool:
        """检查是否可以管理用户"""
        return cls.has_permission(user_role, 'manage_users')


def require_permission(permission: str):
    """权限装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 这里应该从请求上下文中获取用户信息
            # 简化实现，实际使用时需要集成到FastAPI的依赖注入系统
            user_role = kwargs.get('user_role', 'viewer')
            
            if not PermissionManager.has_permission(user_role, permission):
                raise PermissionError(f"Insufficient permissions: {permission}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试认证管理器
    auth_manager = AuthManager()
    
    # 测试密码哈希
    password = os.getenv("TEST_USER_PASSWORD", "test123")
    hashed = auth_manager.hash_password(password)
    print(f"Hashed password: {hashed}")
    
    # 测试密码验证
    is_valid = auth_manager.verify_password(password, hashed)
    print(f"Password verification: {is_valid}")
    
    # 测试令牌创建和验证
    user_id = "test_user_123"
    token = auth_manager.create_token(user_id)
    print(f"Token: {token}")
    
    verified_user_id = auth_manager.verify_token(token)
    print(f"Verified user ID: {verified_user_id}")
    
    # 测试令牌信息
    token_info = auth_manager.get_token_info(token)
    print(f"Token info: {token_info}")
    
    # 测试权限管理
    print(f"Admin can review: {PermissionManager.can_review_strategies('admin')}")
    print(f"Viewer can review: {PermissionManager.can_review_strategies('viewer')}")
    print(f"Admin permissions: {PermissionManager.get_user_permissions('admin')}")