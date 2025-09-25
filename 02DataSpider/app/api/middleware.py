# -*- coding: utf-8 -*-
"""
API中间件模块

提供请求限流、认证、日志记录等中间件功能
"""

import time
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, Callable
from collections import defaultdict, deque

from flask import request, jsonify, g, current_app
from werkzeug.exceptions import TooManyRequests, Unauthorized


class RateLimiter:
    """请求限流器"""

    def __init__(self):
        """初始化限流器"""
        self.requests = defaultdict(deque)  # IP -> 请求时间队列
        self.cleanup_interval = 300  # 清理间隔（秒）
        self.last_cleanup = time.time()

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """检查是否允许请求

        Args:
            key: 限流键（通常是IP地址）
            limit: 限制次数
            window: 时间窗口（秒）

        Returns:
            是否允许请求
        """
        now = time.time()

        # 定期清理过期记录
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired_records(now)
            self.last_cleanup = now

        # 获取请求队列
        request_times = self.requests[key]

        # 移除过期请求
        cutoff_time = now - window
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()

        # 检查是否超过限制
        if len(request_times) >= limit:
            return False

        # 记录当前请求
        request_times.append(now)
        return True

    def _cleanup_expired_records(self, now: float):
        """清理过期记录"""
        expired_keys = []

        for key, request_times in self.requests.items():
            # 移除1小时前的记录
            cutoff_time = now - 3600
            while request_times and request_times[0] < cutoff_time:
                request_times.popleft()

            # 如果队列为空，标记为过期
            if not request_times:
                expired_keys.append(key)

        # 删除过期键
        for key in expired_keys:
            del self.requests[key]

    def get_stats(self) -> Dict[str, Any]:
        """获取限流统计"""
        return {
            "active_keys": len(self.requests),
            "total_requests": sum(len(queue) for queue in self.requests.values()),
            "last_cleanup": self.last_cleanup,
        }


class RequestLogger:
    """请求日志记录器"""

    def __init__(self):
        """初始化日志记录器"""
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.start_time = time.time()

    def log_request(
        self, method: str, path: str, status_code: int, response_time: float
    ):
        """记录请求日志

        Args:
            method: HTTP方法
            path: 请求路径
            status_code: 响应状态码
            response_time: 响应时间
        """
        self.request_count += 1
        self.total_response_time += response_time

        if status_code >= 400:
            self.error_count += 1

        # 记录详细日志
        if hasattr(current_app, "logger_instance"):
            current_app.logger_instance.info(
                f"API请求: {method} {path} | "
                f"状态: {status_code} | "
                f"耗时: {response_time:.3f}s | "
                f"IP: {request.remote_addr}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self.start_time

        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "avg_response_time": self.total_response_time / max(self.request_count, 1),
            "requests_per_second": self.request_count / max(uptime, 1),
            "uptime": uptime,
        }


# 全局实例
rate_limiter = RateLimiter()
request_logger = RequestLogger()


def setup_middleware(app):
    """设置中间件

    Args:
        app: Flask应用实例
    """
    # 存储中间件实例
    app.rate_limiter = rate_limiter
    app.request_logger = request_logger

    # 请求前处理
    @app.before_request
    def before_request_middleware():
        """请求前中间件"""
        # 跳过健康检查和静态文件
        if request.path in ["/health", "/favicon.ico"] or request.path.startswith(
            "/static"
        ):
            return

        # 获取配置
        config = getattr(app, "config_manager", None)
        if not config:
            return

        # 请求限流
        rate_limit_config = config.get_config("api.rate_limit", {})
        if rate_limit_config.get("enabled", True):
            client_ip = get_client_ip()
            limit = rate_limit_config.get("requests_per_minute", 60)
            window = 60  # 1分钟窗口

            if not rate_limiter.is_allowed(client_ip, limit, window):
                raise TooManyRequests(
                    description=f"Rate limit exceeded: {limit} requests per minute"
                )

        # 设置请求开始时间
        g.request_start_time = time.time()

    # 请求后处理
    @app.after_request
    def after_request_middleware(response):
        """请求后中间件"""
        # 跳过健康检查和静态文件
        if request.path in ["/health", "/favicon.ico"] or request.path.startswith(
            "/static"
        ):
            return response

        # 记录请求日志
        if hasattr(g, "request_start_time"):
            response_time = time.time() - g.request_start_time
            request_logger.log_request(
                request.method, request.path, response.status_code, response_time
            )

        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response


def get_client_ip() -> str:
    """获取客户端IP地址

    Returns:
        客户端IP地址
    """
    # 检查代理头
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    else:
        return request.remote_addr or "unknown"


def require_auth(f):
    """认证装饰器

    Args:
        f: 被装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取配置
        config = getattr(current_app, "config_manager", None)
        if not config:
            raise Unauthorized(description="Configuration not available")

        auth_config = config.get_config("api.auth", {})

        # 如果禁用认证，直接通过
        if not auth_config.get("enabled", True):
            return f(*args, **kwargs)

        # 检查API密钥
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not api_key:
            raise Unauthorized(description="API key required")

        # 验证API密钥
        valid_keys = auth_config.get("api_keys", [])
        if api_key not in valid_keys:
            raise Unauthorized(description="Invalid API key")

        # 设置认证信息
        g.authenticated = True
        g.api_key = api_key

        return f(*args, **kwargs)

    return decorated_function


def require_admin(f):
    """管理员权限装饰器

    Args:
        f: 被装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 先检查基础认证
        if not getattr(g, "authenticated", False):
            raise Unauthorized(description="Authentication required")

        # 获取配置
        config = getattr(current_app, "config_manager", None)
        if not config:
            raise Unauthorized(description="Configuration not available")

        auth_config = config.get_config("api.auth", {})

        # 检查管理员权限
        admin_keys = auth_config.get("admin_keys", [])
        if getattr(g, "api_key", "") not in admin_keys:
            raise Unauthorized(description="Admin privileges required")

        return f(*args, **kwargs)

    return decorated_function


def validate_json(f=None, *, required_fields: list = None):
    """JSON验证装饰器

    Args:
        f: 被装饰的函数
        required_fields: 必需字段列表

    Returns:
        装饰器函数
    """

    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            # 检查Content-Type
            if not request.is_json:
                return (
                    jsonify(
                        {
                            "error": {
                                "code": 400,
                                "message": "Content-Type must be application/json",
                            }
                        }
                    ),
                    400,
                )

            # 解析JSON
            try:
                data = request.get_json()
                if data is None:
                    raise ValueError("No JSON data provided")
            except Exception as e:
                return (
                    jsonify(
                        {"error": {"code": 400, "message": f"Invalid JSON: {str(e)}"}}
                    ),
                    400,
                )

            # 验证必需字段
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data:
                        missing_fields.append(field)

                if missing_fields:
                    return (
                        jsonify(
                            {
                                "error": {
                                    "code": 400,
                                    "message": f'Missing required fields: {", ".join(missing_fields)}',
                                }
                            }
                        ),
                        400,
                    )

            # 将数据添加到g对象
            g.json_data = data

            return func(*args, **kwargs)

        return decorated_function

    if f is None:
        return decorator
    else:
        return decorator(f)


def handle_errors(f):
    """错误处理装饰器

    Args:
        f: 被装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # 记录错误
            if hasattr(current_app, "logger_instance"):
                current_app.logger_instance.error(
                    f"API错误: {type(e).__name__}: {str(e)} | "
                    f"路径: {request.path} | "
                    f"方法: {request.method}",
                    exc_info=True,
                )

            # 返回错误响应
            return (
                jsonify(
                    {
                        "error": {
                            "code": 500,
                            "message": "Internal server error",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    }
                ),
                500,
            )

    return decorated_function


def cache_response(timeout: int = 300):
    """响应缓存装饰器

    Args:
        timeout: 缓存超时时间（秒）

    Returns:
        装饰器函数
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)

            # 添加缓存头
            if hasattr(response, "headers"):
                response.headers["Cache-Control"] = f"public, max-age={timeout}"
                response.headers["Expires"] = (
                    datetime.utcnow() + timedelta(seconds=timeout)
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")

            return response

        return decorated_function

    return decorator


if __name__ == "__main__":
    # 测试中间件功能
    print("测试请求限流器...")

    limiter = RateLimiter()

    # 测试限流
    test_ip = "192.168.1.1"
    limit = 5
    window = 60

    print(f"测试IP: {test_ip}, 限制: {limit}次/{window}秒")

    for i in range(7):
        allowed = limiter.is_allowed(test_ip, limit, window)
        print(f"请求 {i+1}: {'允许' if allowed else '拒绝'}")

    # 显示统计
    stats = limiter.get_stats()
    print(f"限流器统计: {stats}")

    print("\n测试请求日志记录器...")

    logger = RequestLogger()

    # 模拟请求
    logger.log_request("GET", "/api/v1/status", 200, 0.123)
    logger.log_request("POST", "/api/v1/crawlers", 201, 0.456)
    logger.log_request("GET", "/api/v1/invalid", 404, 0.089)

    # 显示统计
    stats = logger.get_stats()
    print(f"请求日志统计: {stats}")
