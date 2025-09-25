#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证管理器 - 用户认证和权限管理
核心设计理念：安全认证、权限控制、数据隔离
"""

import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from ..config.settings import AuthConfig
from ..core.sqlite_manager import SQLiteManager, Tables
from ..core.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class AuthManager:
    """认证管理器 - 安全认证中心"""

    def __init__(self, config: AuthConfig):
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.sqlite_manager: Optional[SQLiteManager] = None
        self.redis_manager: Optional[RedisManager] = None

        # 统计信息
        self.stats = {
            "authentications": 0,
            "failed_attempts": 0,
            "tokens_issued": 0,
            "tokens_revoked": 0,
            "start_time": None,
        }

    async def initialize(self):
        """初始化认证管理器"""
        try:
            self.stats["start_time"] = datetime.now()
            logger.info("认证管理器初始化完成")

        except Exception as e:
            logger.error(f"认证管理器初始化失败: {e}")
            raise

    def set_managers(self, sqlite_manager: SQLiteManager, redis_manager: RedisManager):
        """设置依赖的管理器"""
        self.sqlite_manager = sqlite_manager
        self.redis_manager = redis_manager

    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_api_key(self) -> str:
        """生成API密钥"""
        return secrets.token_urlsafe(32)

    def hash_api_key(self, api_key: str) -> str:
        """API密钥哈希"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def create_user(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: str,
        role: str = "user",
    ) -> Dict[str, Any]:
        """创建用户"""
        try:
            if not self.sqlite_manager:
                raise RuntimeError("SQLite管理器未设置")

            # 检查用户是否已存在
            existing_users = await self.sqlite_manager.get_records(
                Tables.USERS,
                "tenant_id = ? AND (username = ? OR email = ?)",
                (tenant_id, username, email),
            )

            if existing_users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="用户名或邮箱已存在"
                )

            # 创建用户
            password_hash = self.hash_password(password)
            user_data = {
                "tenant_id": tenant_id,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            user_id = await self.sqlite_manager.insert_record(Tables.USERS, user_data)

            logger.info(
                f"用户创建成功 - ID: {user_id}, Username: {username}, Tenant: {tenant_id}"
            )

            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "tenant_id": tenant_id,
            }

        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            raise

    async def authenticate_user(
        self, tenant_id: str, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """用户认证"""
        try:
            if not self.sqlite_manager:
                raise RuntimeError("SQLite管理器未设置")

            # 查找用户
            users = await self.sqlite_manager.get_records(
                Tables.USERS,
                "tenant_id = ? AND username = ? AND status = 'active'",
                (tenant_id, username),
            )

            if not users:
                self.stats["failed_attempts"] += 1
                return None

            user = users[0]

            # 验证密码
            if not self.verify_password(password, user["password_hash"]):
                self.stats["failed_attempts"] += 1
                return None

            # 更新最后登录时间
            await self.sqlite_manager.update_record(
                Tables.USERS,
                {"last_login": datetime.now().isoformat()},
                "id = ?",
                (user["id"],),
            )

            self.stats["authentications"] += 1

            return {
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "tenant_id": user["tenant_id"],
            }

        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            self.stats["failed_attempts"] += 1
            return None

    async def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        try:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.access_token_expire_minutes
            )

            to_encode = {
                "sub": str(user_data["user_id"]),
                "username": user_data["username"],
                "role": user_data["role"],
                "tenant_id": user_data["tenant_id"],
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "type": "access",
            }

            token = jwt.encode(
                to_encode, self.config.secret_key, algorithm=self.config.algorithm
            )

            # 缓存令牌信息
            if self.redis_manager:
                token_key = f"access_token:{user_data['user_id']}"
                await self.redis_manager.set_cache(
                    token_key,
                    {
                        "token": token,
                        "user_data": user_data,
                        "expires_at": expire.isoformat(),
                    },
                    ttl=self.config.access_token_expire_minutes * 60,
                    tenant_id=user_data["tenant_id"],
                )

            self.stats["tokens_issued"] += 1

            return token

        except Exception as e:
            logger.error(f"创建访问令牌失败: {e}")
            raise

    async def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        try:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.config.refresh_token_expire_days
            )

            to_encode = {
                "sub": str(user_data["user_id"]),
                "tenant_id": user_data["tenant_id"],
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "type": "refresh",
            }

            token = jwt.encode(
                to_encode, self.config.secret_key, algorithm=self.config.algorithm
            )

            # 缓存刷新令牌
            if self.redis_manager:
                refresh_key = f"refresh_token:{user_data['user_id']}"
                await self.redis_manager.set_cache(
                    refresh_key,
                    {
                        "token": token,
                        "user_id": user_data["user_id"],
                        "expires_at": expire.isoformat(),
                    },
                    ttl=self.config.refresh_token_expire_days * 24 * 60 * 60,
                    tenant_id=user_data["tenant_id"],
                )

            return token

        except Exception as e:
            logger.error(f"创建刷新令牌失败: {e}")
            raise

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(
                token, self.config.secret_key, algorithms=[self.config.algorithm]
            )

            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            token_type = payload.get("type")

            if not all([user_id, tenant_id, token_type]):
                return None

            # 检查令牌是否被撤销
            if self.redis_manager:
                revoked_key = f"revoked_token:{token}"
                is_revoked = await self.redis_manager.get_cache(revoked_key)
                if is_revoked:
                    return None

            return {
                "user_id": int(user_id),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "tenant_id": tenant_id,
                "token_type": token_type,
            }

        except JWTError as e:
            logger.warning(f"令牌验证失败: {e}")
            return None
        except Exception as e:
            logger.error(f"验证令牌时发生错误: {e}")
            return None

    async def revoke_token(self, token: str, tenant_id: str) -> bool:
        """撤销令牌"""
        try:
            if not self.redis_manager:
                return False

            # 将令牌加入撤销列表
            revoked_key = f"revoked_token:{token}"
            await self.redis_manager.set_cache(
                revoked_key,
                {"revoked_at": datetime.now().isoformat()},
                ttl=self.config.access_token_expire_minutes * 60,
                tenant_id=tenant_id,
            )

            self.stats["tokens_revoked"] += 1

            return True

        except Exception as e:
            logger.error(f"撤销令牌失败: {e}")
            return False

    async def create_api_key(
        self,
        tenant_id: str,
        user_id: int,
        key_name: str,
        permissions: List[str],
        expires_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """创建API密钥"""
        try:
            if not self.sqlite_manager:
                raise RuntimeError("SQLite管理器未设置")

            # 生成API密钥
            api_key = self.generate_api_key()
            key_hash = self.hash_api_key(api_key)

            # 设置过期时间
            expires_at = None
            if expires_days:
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

            # 保存API密钥
            key_data = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "key_name": key_name,
                "key_hash": key_hash,
                "permissions": ",".join(permissions),
                "expires_at": expires_at,
                "status": "active",
                "created_at": datetime.now().isoformat(),
            }

            key_id = await self.sqlite_manager.insert_record(Tables.API_KEYS, key_data)

            logger.info(f"API密钥创建成功 - ID: {key_id}, Name: {key_name}, User: {user_id}")

            return {
                "key_id": key_id,
                "api_key": api_key,  # 只在创建时返回
                "key_name": key_name,
                "permissions": permissions,
                "expires_at": expires_at,
            }

        except Exception as e:
            logger.error(f"创建API密钥失败: {e}")
            raise

    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证API密钥"""
        try:
            if not self.sqlite_manager:
                raise RuntimeError("SQLite管理器未设置")

            key_hash = self.hash_api_key(api_key)

            # 查找API密钥
            keys = await self.sqlite_manager.get_records(
                Tables.API_KEYS, "key_hash = ? AND status = 'active'", (key_hash,)
            )

            if not keys:
                return None

            key_info = keys[0]

            # 检查过期时间
            if key_info["expires_at"]:
                expires_at = datetime.fromisoformat(key_info["expires_at"])
                if datetime.now() > expires_at:
                    return None

            # 更新最后使用时间
            await self.sqlite_manager.update_record(
                Tables.API_KEYS,
                {"last_used": datetime.now().isoformat()},
                "id = ?",
                (key_info["id"],),
            )

            return {
                "key_id": key_info["id"],
                "user_id": key_info["user_id"],
                "tenant_id": key_info["tenant_id"],
                "key_name": key_info["key_name"],
                "permissions": key_info["permissions"].split(",")
                if key_info["permissions"]
                else [],
            }

        except Exception as e:
            logger.error(f"验证API密钥失败: {e}")
            return None

    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """检查权限"""
        role_permissions = {
            "admin": ["*"],  # 管理员拥有所有权限
            "user": ["api.read", "api.write"],
            "readonly": ["api.read"],
        }

        permissions = role_permissions.get(user_role, [])

        # 检查是否有通配符权限
        if "*" in permissions:
            return True

        # 检查具体权限
        return required_permission in permissions

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 测试JWT编码解码
            test_payload = {
                "test": "data",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
            }
            test_token = jwt.encode(
                test_payload, self.config.secret_key, algorithm=self.config.algorithm
            )
            jwt.decode(
                test_token, self.config.secret_key, algorithms=[self.config.algorithm]
            )

            return True

        except Exception as e:
            logger.error(f"认证管理器健康检查失败: {e}")
            return False

    def is_healthy(self) -> bool:
        """同步健康检查方法"""
        try:
            # 检查基本配置
            if not self.config or not self.config.secret_key:
                return False
            
            # 检查密码上下文
            if not self.pwd_context:
                return False
            
            # 检查统计信息初始化
            if not hasattr(self, 'stats') or not isinstance(self.stats, dict):
                return False
            
            return True
        except Exception as e:
            logger.error(f"认证管理器同步健康检查失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {**self.stats, "uptime_seconds": uptime}

    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("认证管理器已清理")
        except Exception as e:
            logger.error(f"认证管理器清理失败: {e}")


# 权限常量


class Permissions:
    """权限定义"""

    API_READ = "api.read"
    API_WRITE = "api.write"
    API_DELETE = "api.delete"
    USER_MANAGE = "user.manage"
    SYSTEM_ADMIN = "system.admin"
    QUOTA_MANAGE = "quota.manage"
    CLUSTER_MANAGE = "cluster.manage"
