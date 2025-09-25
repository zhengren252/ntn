#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证中心路由 - 用户认证和权限管理
核心功能：用户注册、登录、JWT令牌管理、API密钥管理
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Header, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr

from ..core.zmq_manager import ZMQManager, MessageTopics
from ..core.sqlite_manager import SQLiteManager, Tables
from ..security.auth import AuthManager, Permissions
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
router = APIRouter()
import uuid

# 请求模型


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    role: str = Field(default="user", description="角色")


class UserLoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class APIKeyCreateRequest(BaseModel):
    key_name: str = Field(..., description="密钥名称")
    permissions: List[str] = Field(..., description="权限列表")
    expires_days: Optional[int] = Field(default=None, description="过期天数")


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


# 响应模型


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: Dict[str, Any]


class APIKeyResponse(BaseModel):
    key_id: int
    api_key: str
    key_name: str
    permissions: List[str]
    expires_at: Optional[str]
    created_at: str


# 依赖注入


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """获取当前用户信息"""
    try:
        # 这里应该验证JWT令牌
        token = credentials.credentials

        # 模拟令牌验证
        if not token or token == "invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 模拟用户信息
        return {
            "user_id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin",
            "tenant_id": "default",
        }

    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_tenant_id(x_tenant_id: Optional[str] = Header(None)):
    """获取租户ID"""
    return x_tenant_id or "default"


@router.post("/register", response_model=Dict[str, Any])
async def register_user(
    register_request: UserRegisterRequest, tenant_id: str = Depends(get_tenant_id)
):
    """用户注册"""
    try:
        settings = get_settings()

        # 验证角色
        valid_roles = ["admin", "user", "readonly"]
        if register_request.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"无效的角色，支持的角色: {valid_roles}")

        # 模拟用户创建
        user_data = {
            "user_id": 1,  # 模拟生成的用户ID
            "username": register_request.username,
            "email": register_request.email,
            "role": register_request.role,
            "tenant_id": tenant_id,
            "created_at": datetime.now().isoformat(),
        }

        logger.info(
            f"用户注册成功 - Username: {register_request.username}, Em"
            "il: {register_request.email}, Tenant: {tenant_id}"
        )

        # 发布ZeroMQ消息
        # await zmq_manager.publish_message(
        #     MessageTopics.AUTH_EVENT,
        #     {"action": "user_registered", "user_id": user_data["user_id"], "username": register_request.username},
        #     tenant_id
        # )

        return {"success": True, "message": "用户注册成功", "user_info": user_data}

    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_request: UserLoginRequest, tenant_id: str = Depends(get_tenant_id)
):
    """用户登录"""
    try:
        settings = get_settings()

        # 模拟用户认证
        if login_request.username == "admin" and login_request.password == "admin123":
            user_data = {
                "user_id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "tenant_id": tenant_id,
            }
        elif login_request.username == "user" and login_request.password == "user123":
            user_data = {
                "user_id": 2,
                "username": "user",
                "email": "user@example.com",
                "role": "user",
                "tenant_id": tenant_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
            )

        # 模拟生成令牌
        access_token = (
            f"access_token_for_{user_data['username']}_{datetime.now().timestamp()}"
        )
        refresh_token = (
            f"refresh_token_for_{user_data['username']}_{datetime.now().timestamp()}"
        )

        logger.info(f"用户登录成功 - Username: {login_request.username}, Tenant: {tenant_id}")

        # 发布ZeroMQ消息
        # await zmq_manager.publish_message(
        #     MessageTopics.AUTH_EVENT,
        #     {"action": "user_login", "user_id": user_data["user_id"], "username": login_request.username},
        #     tenant_id
        # )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,  # 30分钟
            user_info=user_data,
        )

    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_request: TokenRefreshRequest, tenant_id: str = Depends(get_tenant_id)
):
    """刷新访问令牌"""
    try:
        # 模拟令牌刷新
        if not refresh_request.refresh_token.startswith("refresh_token_for_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
            )

        # 提取用户信息
        username = refresh_request.refresh_token.split("_")[3]

        # 生成新的访问令牌
        new_access_token = f"access_token_for_{username}_{datetime.now().timestamp()}"

        logger.info(f"令牌刷新成功 - Username: {username}, Tenant: {tenant_id}")

        return {
            "success": True,
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout", response_model=Dict[str, Any])
async def logout_user(
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """用户登出"""
    try:
        # 模拟令牌撤销
        logger.info(
            f"用户登出成功 - Username: {current_user['username']}, Tenant: {tenant_id}"
        )

        # 发布ZeroMQ消息
        # await zmq_manager.publish_message(
        #     MessageTopics.AUTH_EVENT,
        #     {"action": "user_logout", "user_id": current_user["user_id"], "username": current_user["username"]},
        #     tenant_id
        # )

        return {"success": True, "message": "登出成功"}

    except Exception as e:
        logger.error(f"用户登出失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取用户资料"""
    try:
        # 模拟获取用户详细信息
        profile = {
            **current_user,
            "last_login": "2024-01-01T12:00:00",
            "created_at": "2024-01-01T00:00:00",
            "api_keys_count": 2,
            "permissions": ["api.read", "api.write"]
            if current_user["role"] == "user"
            else ["*"],
        }

        logger.info(
            f"获取用户资料 - Username: {current_user['username']}, Tenant: {tenant_id}"
        )

        return profile

    except Exception as e:
        logger.error(f"获取用户资料失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile(
    profile_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """更新用户资料"""
    try:
        # 模拟更新用户资料
        allowed_fields = ["email"]
        update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}

        logger.info(
            f"用户资料更新成功 - Username: {current_user['username']}, Tenant: {tenant_id}"
        )

        return {
            "success": True,
            "message": "用户资料更新成功",
            "updated_fields": list(update_data.keys()),
        }

    except Exception as e:
        logger.error(f"更新用户资料失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-password", response_model=Dict[str, Any])
async def change_password(
    password_request: PasswordChangeRequest,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """修改密码"""
    try:
        # 模拟密码验证和更新
        if password_request.old_password != "current_password":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

        logger.info(
            f"密码修改成功 - Username: {current_user['username']}, Tenant: {tenant_id}"
        )

        return {"success": True, "message": "密码修改成功"}

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_request: APIKeyCreateRequest,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """创建API密钥"""
    try:
        # 验证权限
        valid_permissions = [
            Permissions.API_READ,
            Permissions.API_WRITE,
            Permissions.API_DELETE,
        ]
        invalid_perms = [
            p for p in key_request.permissions if p not in valid_permissions
        ]
        if invalid_perms:
            raise HTTPException(status_code=400, detail=f"无效的权限: {invalid_perms}")

        # 模拟创建API密钥
        api_key_data = {
            "key_id": 1,
            "api_key": f"ak_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user['user_id']}",
            "key_name": key_request.key_name,
            "permissions": key_request.permissions,
            "expires_at": (
                datetime.now()
                .replace(day=datetime.now().day + key_request.expires_days)
                .isoformat()
                if key_request.expires_days
                else None
            ),
            "created_at": datetime.now().isoformat(),
        }

        logger.info(
            f"API密钥创建成功 - Name: {key_request.key_name}, User: {current_user['username']}, Tenant: {tenant_id}"
        )

        return APIKeyResponse(**api_key_data)

    except Exception as e:
        logger.error(f"创建API密钥失败: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-keys", response_model=List[Dict[str, Any]])
async def list_api_keys(
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取API密钥列表"""
    try:
        # 模拟获取API密钥列表
        api_keys = [
            {
                "key_id": 1,
                "key_name": "Production Key",
                "permissions": ["api.read", "api.write"],
                "expires_at": "2024-12-31T23:59:59",
                "last_used": "2024-01-01T12:00:00",
                "status": "active",
                "created_at": "2024-01-01T00:00:00",
            },
            {
                "key_id": 2,
                "key_name": "Development Key",
                "permissions": ["api.read"],
                "expires_at": None,
                "last_used": "2024-01-01T10:00:00",
                "status": "active",
                "created_at": "2024-01-01T00:00:00",
            },
        ]

        logger.info(
            f"获取API密钥列表 - Count: {len(api_keys)}, User: {current_user['username']}, Tenant: {tenant_id}"
        )

        return api_keys

    except Exception as e:
        logger.error(f"获取API密钥列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{key_id}", response_model=Dict[str, Any])
async def delete_api_key(
    key_id: int,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """删除API密钥"""
    try:
        # 模拟删除API密钥
        logger.info(
            f"API密钥删除成功 - KeyID: {key_id}, User: {current_user['username']}, Tenant: {tenant_id}"
        )

        return {"success": True, "message": "API密钥删除成功", "key_id": key_id}

    except Exception as e:
        logger.error(f"删除API密钥失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions", response_model=List[str])
async def list_permissions(
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取可用权限列表"""
    try:
        permissions = [
            Permissions.API_READ,
            Permissions.API_WRITE,
            Permissions.API_DELETE,
            Permissions.USER_MANAGE,
            Permissions.QUOTA_MANAGE,
            Permissions.CLUSTER_MANAGE,
        ]

        # 根据用户角色过滤权限
        if current_user["role"] != "admin":
            permissions = [
                p
                for p in permissions
                if not p.startswith("system.") and not p.endswith(".manage")
            ]

        return permissions

    except Exception as e:
        logger.error(f"获取权限列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def health_check(request: Request):
    """认证中心健康检查"""
    try:
        req_id = (
            request.headers.get("x-request-id")
            or request.headers.get("X-Request-ID")
            or uuid.uuid4().hex
        )
        ts = datetime.now(timezone.utc).isoformat()
        health_status = {
            "success": True,
            "auth_service": "healthy",
            "token_service": "healthy",
            "user_database": "healthy",
            "session_cache": "healthy",
            "timestamp": ts,
            "request_id": req_id,
        }

        return health_status

    except Exception as e:
        logger.error(f"认证中心健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
