# -*- coding: utf-8 -*-
"""
认证模块

提供API密钥认证、权限管理和用户会话功能
"""

import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.exceptions import Unauthorized, BadRequest, Forbidden

from .middleware import validate_json, handle_errors

# 创建蓝图
auth_bp = Blueprint("auth", __name__)


class UserRole(Enum):
    """用户角色"""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class Permission(Enum):
    """权限类型"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class APIKey:
    """API密钥信息"""

    key: str
    name: str
    role: UserRole
    permissions: List[Permission]
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    usage_count: int
    rate_limit: Optional[int]  # 每分钟请求限制
    allowed_ips: List[str]  # 允许的IP地址
    metadata: Dict[str, Any]


@dataclass
class Session:
    """用户会话"""

    session_id: str
    api_key: str
    user_role: UserRole
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_active: bool


class AuthManager:
    """认证管理器"""

    def __init__(self, config, logger):
        """初始化认证管理器

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

        # API密钥存储
        self.api_keys: Dict[str, APIKey] = {}

        # 会话存储
        self.sessions: Dict[str, Session] = {}

        # 权限映射
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.READ,
                Permission.WRITE,
                Permission.DELETE,
                Permission.ADMIN,
            ],
            UserRole.USER: [Permission.READ, Permission.WRITE],
            UserRole.READONLY: [Permission.READ],
        }

        # 加载配置
        auth_config = config.get_config("api.auth", {})
        self.enabled = auth_config.get("enabled", True)
        self.session_timeout = auth_config.get("session_timeout", 3600)  # 1小时
        self.max_sessions_per_key = auth_config.get("max_sessions_per_key", 5)

        # 初始化默认API密钥
        self._init_default_keys()

        self.logger.info(f"认证管理器初始化完成: 启用={self.enabled}")

    def _init_default_keys(self):
        """初始化默认API密钥"""
        auth_config = self.config.get_config("api.auth", {})
        default_keys = auth_config.get("default_keys", [])

        for key_config in default_keys:
            api_key = APIKey(
                key=key_config["key"],
                name=key_config.get("name", "Default Key"),
                role=UserRole(key_config.get("role", "user")),
                permissions=[
                    Permission(p) for p in key_config.get("permissions", ["read"])
                ],
                created_at=datetime.utcnow(),
                last_used=None,
                expires_at=None,
                is_active=True,
                usage_count=0,
                rate_limit=key_config.get("rate_limit"),
                allowed_ips=key_config.get("allowed_ips", []),
                metadata={},
            )

            self.api_keys[api_key.key] = api_key
            self.logger.debug(f"加载默认API密钥: {api_key.name} ({api_key.role.value})")

    def generate_api_key(
        self,
        name: str,
        role: UserRole,
        permissions: List[Permission] = None,
        expires_days: int = None,
        rate_limit: int = None,
        allowed_ips: List[str] = None,
    ) -> str:
        """生成新的API密钥

        Args:
            name: 密钥名称
            role: 用户角色
            permissions: 权限列表
            expires_days: 过期天数
            rate_limit: 速率限制
            allowed_ips: 允许的IP地址

        Returns:
            生成的API密钥
        """
        # 生成密钥
        key = f"ntn_{secrets.token_urlsafe(32)}"

        # 设置权限
        if permissions is None:
            permissions = self.role_permissions.get(role, [Permission.READ])

        # 设置过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # 创建API密钥对象
        api_key = APIKey(
            key=key,
            name=name,
            role=role,
            permissions=permissions,
            created_at=datetime.utcnow(),
            last_used=None,
            expires_at=expires_at,
            is_active=True,
            usage_count=0,
            rate_limit=rate_limit,
            allowed_ips=allowed_ips or [],
            metadata={},
        )

        # 存储密钥
        self.api_keys[key] = api_key

        self.logger.info(f"生成新API密钥: {name} ({role.value}) | 密钥: {key[:16]}...")

        return key

    def validate_api_key(
        self, key: str, ip_address: str = None
    ) -> Tuple[bool, Optional[APIKey], str]:
        """验证API密钥

        Args:
            key: API密钥
            ip_address: 客户端IP地址

        Returns:
            (是否有效, API密钥对象, 错误信息)
        """
        if not self.enabled:
            return True, None, ""

        if not key:
            return False, None, "API key required"

        # 查找密钥
        api_key = self.api_keys.get(key)
        if not api_key:
            return False, None, "Invalid API key"

        # 检查是否激活
        if not api_key.is_active:
            return False, None, "API key is disabled"

        # 检查过期时间
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            return False, None, "API key has expired"

        # 检查IP限制
        if api_key.allowed_ips and ip_address:
            if ip_address not in api_key.allowed_ips:
                return False, None, f"IP address {ip_address} not allowed"

        # 更新使用信息
        api_key.last_used = datetime.utcnow()
        api_key.usage_count += 1

        return True, api_key, ""

    def check_permission(self, api_key: APIKey, permission: Permission) -> bool:
        """检查权限

        Args:
            api_key: API密钥对象
            permission: 所需权限

        Returns:
            是否有权限
        """
        if not api_key:
            return False

        return permission in api_key.permissions

    def create_session(
        self, api_key: str, ip_address: str, user_agent: str
    ) -> Optional[str]:
        """创建用户会话

        Args:
            api_key: API密钥
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            会话ID
        """
        # 验证API密钥
        is_valid, key_obj, error = self.validate_api_key(api_key, ip_address)
        if not is_valid:
            return None

        # 检查会话数量限制
        active_sessions = [
            s for s in self.sessions.values() if s.api_key == api_key and s.is_active
        ]

        if len(active_sessions) >= self.max_sessions_per_key:
            # 删除最旧的会话
            oldest_session = min(active_sessions, key=lambda s: s.last_activity)
            self.revoke_session(oldest_session.session_id)

        # 生成会话ID
        session_id = secrets.token_urlsafe(32)

        # 创建会话
        session = Session(
            session_id=session_id,
            api_key=api_key,
            user_role=key_obj.role,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.session_timeout),
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
        )

        self.sessions[session_id] = session

        self.logger.info(f"创建会话: {session_id[:16]}... | API密钥: {api_key[:16]}...")

        return session_id

    def validate_session(self, session_id: str) -> Tuple[bool, Optional[Session], str]:
        """验证会话

        Args:
            session_id: 会话ID

        Returns:
            (是否有效, 会话对象, 错误信息)
        """
        if not session_id:
            return False, None, "Session ID required"

        session = self.sessions.get(session_id)
        if not session:
            return False, None, "Invalid session ID"

        if not session.is_active:
            return False, None, "Session is inactive"

        if datetime.utcnow() > session.expires_at:
            session.is_active = False
            return False, None, "Session has expired"

        # 更新活动时间
        session.last_activity = datetime.utcnow()

        return True, session, ""

    def revoke_session(self, session_id: str) -> bool:
        """撤销会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功撤销
        """
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
            self.logger.info(f"撤销会话: {session_id[:16]}...")
            return True

        return False

    def revoke_api_key(self, key: str) -> bool:
        """撤销API密钥

        Args:
            key: API密钥

        Returns:
            是否成功撤销
        """
        api_key = self.api_keys.get(key)
        if api_key:
            api_key.is_active = False

            # 撤销相关会话
            for session in self.sessions.values():
                if session.api_key == key:
                    session.is_active = False

            self.logger.info(f"撤销API密钥: {api_key.name} | 密钥: {key[:16]}...")
            return True

        return False

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.utcnow()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if session.expires_at < now:
                session.is_active = False
                expired_sessions.append(session_id)

        if expired_sessions:
            self.logger.info(f"清理过期会话: {len(expired_sessions)}个")

    def get_stats(self) -> Dict[str, Any]:
        """获取认证统计信息"""
        active_keys = sum(1 for key in self.api_keys.values() if key.is_active)
        active_sessions = sum(
            1 for session in self.sessions.values() if session.is_active
        )

        return {
            "enabled": self.enabled,
            "total_api_keys": len(self.api_keys),
            "active_api_keys": active_keys,
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "session_timeout": self.session_timeout,
            "max_sessions_per_key": self.max_sessions_per_key,
        }


# 全局认证管理器实例
auth_manager = None


def get_auth_manager():
    """获取认证管理器实例"""
    global auth_manager

    if auth_manager is None:
        config = current_app.config_manager
        logger = current_app.logger_instance
        auth_manager = AuthManager(config, logger)

    return auth_manager


def get_client_ip() -> str:
    """获取客户端IP地址"""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    else:
        return request.remote_addr or "unknown"


@auth_bp.route("/login", methods=["POST"])
@validate_json(required_fields=["api_key"])
@handle_errors
def login():
    """用户登录"""
    data = g.json_data
    api_key = data.get("api_key")

    auth_mgr = get_auth_manager()

    # 验证API密钥
    ip_address = get_client_ip()
    user_agent = request.headers.get("User-Agent", "Unknown")

    is_valid, key_obj, error = auth_mgr.validate_api_key(api_key, ip_address)

    if not is_valid:
        return jsonify({"error": {"message": error}}), 401

    # 创建会话
    session_id = auth_mgr.create_session(api_key, ip_address, user_agent)

    if not session_id:
        return jsonify({"error": {"message": "Failed to create session"}}), 500

    return jsonify(
        {
            "success": True,
            "session_id": session_id,
            "expires_at": (
                datetime.utcnow() + timedelta(seconds=auth_mgr.session_timeout)
            ).isoformat(),
            "user": {
                "role": key_obj.role.value,
                "permissions": [p.value for p in key_obj.permissions],
            },
        }
    )


@auth_bp.route("/logout", methods=["POST"])
@handle_errors
def logout():
    """用户登出"""
    session_id = (
        request.headers.get("X-Session-ID") or request.json.get("session_id")
        if request.is_json
        else None
    )

    if not session_id:
        return jsonify({"error": {"message": "Session ID required"}}), 400

    auth_mgr = get_auth_manager()

    # 撤销会话
    success = auth_mgr.revoke_session(session_id)

    if success:
        return jsonify({"success": True, "message": "Logged out successfully"})
    else:
        return jsonify({"error": {"message": "Invalid session ID"}}), 400


@auth_bp.route("/validate", methods=["POST"])
@handle_errors
def validate_token():
    """验证令牌"""
    # 获取认证信息
    api_key = request.headers.get("X-API-Key") or (
        request.json.get("api_key") if request.is_json else None
    )
    session_id = request.headers.get("X-Session-ID") or (
        request.json.get("session_id") if request.is_json else None
    )

    auth_mgr = get_auth_manager()

    if session_id:
        # 验证会话
        is_valid, session, error = auth_mgr.validate_session(session_id)

        if is_valid:
            return jsonify(
                {
                    "valid": True,
                    "type": "session",
                    "user": {
                        "role": session.user_role.value,
                        "session_id": session.session_id,
                        "expires_at": session.expires_at.isoformat(),
                    },
                }
            )
        else:
            return jsonify({"valid": False, "error": error}), 401

    elif api_key:
        # 验证API密钥
        ip_address = get_client_ip()
        is_valid, key_obj, error = auth_mgr.validate_api_key(api_key, ip_address)

        if is_valid:
            return jsonify(
                {
                    "valid": True,
                    "type": "api_key",
                    "user": {
                        "role": key_obj.role.value,
                        "permissions": [p.value for p in key_obj.permissions],
                        "name": key_obj.name,
                    },
                }
            )
        else:
            return jsonify({"valid": False, "error": error}), 401

    else:
        return jsonify({"valid": False, "error": "No authentication provided"}), 400


@auth_bp.route("/keys", methods=["GET"])
@handle_errors
def list_api_keys():
    """列出API密钥（需要管理员权限）"""
    # 简单的权限检查
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": {"message": "API key required"}}), 401

    auth_mgr = get_auth_manager()

    # 验证权限
    is_valid, key_obj, error = auth_mgr.validate_api_key(api_key, get_client_ip())
    if not is_valid or not auth_mgr.check_permission(key_obj, Permission.ADMIN):
        return jsonify({"error": {"message": "Admin privileges required"}}), 403

    # 返回API密钥列表（隐藏实际密钥值）
    keys = []
    for key, api_key_obj in auth_mgr.api_keys.items():
        keys.append(
            {
                "key": key[:16] + "...",  # 只显示前16个字符
                "name": api_key_obj.name,
                "role": api_key_obj.role.value,
                "permissions": [p.value for p in api_key_obj.permissions],
                "created_at": api_key_obj.created_at.isoformat(),
                "last_used": api_key_obj.last_used.isoformat()
                if api_key_obj.last_used
                else None,
                "expires_at": api_key_obj.expires_at.isoformat()
                if api_key_obj.expires_at
                else None,
                "is_active": api_key_obj.is_active,
                "usage_count": api_key_obj.usage_count,
            }
        )

    return jsonify({"keys": keys, "total": len(keys)})


@auth_bp.route("/keys", methods=["POST"])
@validate_json(required_fields=["name", "role"])
@handle_errors
def create_api_key():
    """创建新的API密钥（需要管理员权限）"""
    # 简单的权限检查
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": {"message": "API key required"}}), 401

    auth_mgr = get_auth_manager()

    # 验证权限
    is_valid, key_obj, error = auth_mgr.validate_api_key(api_key, get_client_ip())
    if not is_valid or not auth_mgr.check_permission(key_obj, Permission.ADMIN):
        return jsonify({"error": {"message": "Admin privileges required"}}), 403

    data = g.json_data

    try:
        # 生成新密钥
        new_key = auth_mgr.generate_api_key(
            name=data["name"],
            role=UserRole(data["role"]),
            permissions=[Permission(p) for p in data.get("permissions", [])],
            expires_days=data.get("expires_days"),
            rate_limit=data.get("rate_limit"),
            allowed_ips=data.get("allowed_ips", []),
        )

        return (
            jsonify(
                {
                    "success": True,
                    "api_key": new_key,
                    "message": f'API key "{data["name"]}" created successfully',
                }
            ),
            201,
        )

    except ValueError as e:
        return (
            jsonify({"error": {"message": f"Invalid role or permission: {str(e)}"}}),
            400,
        )


@auth_bp.route("/stats", methods=["GET"])
@handle_errors
def get_auth_stats():
    """获取认证统计信息"""
    auth_mgr = get_auth_manager()

    # 清理过期会话
    auth_mgr.cleanup_expired_sessions()

    return jsonify(auth_mgr.get_stats())


if __name__ == "__main__":
    # 测试认证功能
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化
    config = ConfigManager("development")
    logger = Logger(config)

    auth_mgr = AuthManager(config, logger)

    print("测试认证管理器...")

    # 生成测试密钥
    admin_key = auth_mgr.generate_api_key("Test Admin", UserRole.ADMIN, expires_days=30)

    user_key = auth_mgr.generate_api_key("Test User", UserRole.USER, rate_limit=100)

    print(f"管理员密钥: {admin_key}")
    print(f"用户密钥: {user_key}")

    # 测试验证
    is_valid, key_obj, error = auth_mgr.validate_api_key(admin_key, "127.0.0.1")
    print(f"管理员密钥验证: {is_valid} | 错误: {error}")

    # 测试权限
    has_admin = auth_mgr.check_permission(key_obj, Permission.ADMIN)
    print(f"管理员权限: {has_admin}")

    # 创建会话
    session_id = auth_mgr.create_session(user_key, "127.0.0.1", "Test Agent")
    print(f"会话ID: {session_id}")

    # 验证会话
    is_valid, session, error = auth_mgr.validate_session(session_id)
    print(f"会话验证: {is_valid} | 错误: {error}")

    # 显示统计
    stats = auth_mgr.get_stats()
    print(f"认证统计: {stats}")
