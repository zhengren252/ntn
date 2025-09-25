#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配额和熔断器路由 - API限流和熔断保护
核心功能：API配额管理、熔断器控制、流量监控
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks, Request
from pydantic import BaseModel, Field
from enum import Enum

from ..core.zmq_manager import ZMQManager, MessageTopics
from ..core.sqlite_manager import SQLiteManager, Tables
from ..config.settings import get_settings
from .. import main as main_app
import inspect
from fastapi import status
import uuid
from ..dependencies import get_current_active_user as _get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

# 枚举定义


class QuotaType(str, Enum):
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_MONTH = "per_month"


class CircuitState(str, Enum):
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


# 请求模型


class QuotaCreateRequest(BaseModel):
    api_name: str = Field(..., description="API名称")
    quota_type: QuotaType = Field(..., description="配额类型")
    limit_value: int = Field(..., gt=0, description="限制值")
    user_id: Optional[int] = Field(default=None, description="用户ID（为空则为全局配额）")


class QuotaUpdateRequest(BaseModel):
    limit_value: Optional[int] = Field(default=None, gt=0, description="限制值")
    status: Optional[str] = Field(default=None, description="状态")


class CircuitBreakerConfigRequest(BaseModel):
    service_name: str = Field(..., description="服务名称")
    failure_threshold: int = Field(default=5, gt=0, description="失败阈值")
    timeout_seconds: int = Field(default=60, gt=0, description="超时时间（秒）")
    half_open_max_calls: int = Field(default=3, gt=0, description="半开状态最大调用次数")


class RateLimitCheckRequest(BaseModel):
    api_name: str = Field(..., description="API名称")
    user_id: Optional[int] = Field(default=None, description="用户ID")


# 响应模型


class QuotaStatus(BaseModel):
    quota_id: int
    api_name: str
    quota_type: QuotaType
    limit_value: int
    current_usage: int
    remaining: int
    reset_at: str
    status: str


class CircuitBreakerStatus(BaseModel):
    service_name: str
    state: CircuitState
    failure_count: int
    last_failure_time: Optional[str]
    next_attempt_time: Optional[str]
    success_count: int


# 依赖注入


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    统一代理到公共认证依赖函数，保持对外依赖名不变，避免下游引用变更。
    """
    return await _get_current_active_user(authorization=authorization, x_api_key=x_api_key)


async def get_tenant_id(x_tenant_id: Optional[str] = Header(None)):
    """获取租户ID"""
    return x_tenant_id or "default"


# 配额管理端点
@router.post("/quotas", response_model=Dict[str, Any])
async def create_quota(
    quota_request: QuotaCreateRequest,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """创建API配额"""
    try:
        # 计算重置时间
        now = datetime.now()
        if quota_request.quota_type == QuotaType.PER_MINUTE:
            reset_at = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            window_seconds = 60
        elif quota_request.quota_type == QuotaType.PER_HOUR:
            reset_at = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )
            window_seconds = 3600
        elif quota_request.quota_type == QuotaType.PER_DAY:
            reset_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            window_seconds = 86400
        else:  # PER_MONTH
            next_month = now.replace(day=1) + timedelta(days=32)
            reset_at = next_month.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            window_seconds = 2592000  # 30天

        # 模拟保存配额配置
        quota_data = {
            "quota_id": 1,  # 模拟生成的ID
            "tenant_id": tenant_id,
            "user_id": quota_request.user_id,
            "api_name": quota_request.api_name,
            "quota_type": quota_request.quota_type,
            "limit_value": quota_request.limit_value,
            "window_seconds": window_seconds,
            "current_usage": 0,
            "reset_at": reset_at.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        logger.info(
            f"配额创建成功 - API: {quota_request.api_name}, Type: {quota_request.quota_type}, Limit: {quota_request.limit_value}, Tenant: {tenant_id}"
        )

        # 发布ZeroMQ消息
        # await zmq_manager.publish_message(
        #     MessageTopics.QUOTA_ALERT,
        #     {"action": "quota_created", "api_name": quota_request.api_name, "limit": quota_request.limit_value},
        #     tenant_id
        # )

        return {"success": True, "message": "配额创建成功", "quota_data": quota_data}

    except Exception as e:
        logger.error(f"创建配额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotas", response_model=List[QuotaStatus])
async def list_quotas(
    api_name: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取配额列表"""
    try:
        # 基础频率限制（默认：每分钟5次）
        try:
            from importlib import import_module
            main_module = import_module("api_factory.main")
            _redis = getattr(main_module, "redis_manager", None)
        except Exception:
            _redis = getattr(main_app, "redis_manager", None)

        if _redis is None:
            logger.warning("Redis manager not initialized; skipping rate limit check")
        else:
            # 组合限流Key：租户/用户/接口
            uid = None
            try:
                if isinstance(current_user, dict):
                    uid = current_user.get("user_id") or current_user.get("id")
            except Exception:
                uid = None
            uid = uid or "anonymous"
            api_key = api_name or "quotas_list"
            quota_key = f"quota:{tenant_id}:{uid}:{api_key}"
            window_seconds = 60
            limit_value = 5

            # 兼容异步/同步的Mock或真实实现
            count_result = _redis.increment_quota(quota_key, window_seconds)
            if inspect.isawaitable(count_result):
                count = await count_result
            else:
                count = count_result

            # 诊断日志：记录每次限流计数
            logger.info(
                f"Rate limit check: key={quota_key}, count={count}, limit={limit_value}, window={window_seconds}s"
            )

            if count > limit_value:
                logger.info(
                    f"Rate limit exceeded: key={quota_key}, count={count}, limit={limit_value}, window={window_seconds}s"
                )
                raise HTTPException(status_code=429, detail={
                    "success": False,
                    "message": "Rate limit exceeded",
                    "quota_key": quota_key,
                    "count": count,
                    "limit": limit_value,
                    "window_seconds": window_seconds,
                })

        # 模拟配额数据
        quotas = [
            QuotaStatus(
                quota_id=1,
                api_name="binance_spot",
                quota_type=QuotaType.PER_MINUTE,
                limit_value=60,
                current_usage=25,
                remaining=35,
                reset_at=(datetime.now() + timedelta(minutes=1)).isoformat(),
                status="active",
            ),
            QuotaStatus(
                quota_id=2,
                api_name="openai_gpt4",
                quota_type=QuotaType.PER_HOUR,
                limit_value=100,
                current_usage=45,
                remaining=55,
                reset_at=(datetime.now() + timedelta(hours=1)).isoformat(),
                status="active",
            ),
            QuotaStatus(
                quota_id=3,
                api_name="yahoo_finance",
                quota_type=QuotaType.PER_DAY,
                limit_value=1000,
                current_usage=150,
                remaining=850,
                reset_at=(datetime.now() + timedelta(days=1)).isoformat(),
                status="active",
            ),
        ]

        # 过滤条件
        if api_name:
            quotas = [q for q in quotas if q.api_name == api_name]
        if user_id:
            # 这里应该根据user_id过滤，暂时返回所有
            pass

        logger.info(f"获取配额列表 - Count: {len(quotas)}, Tenant: {tenant_id}")

        return quotas

    except HTTPException as e:
        # 直接透传HTTP异常（例如429限流），避免被通用异常处理吞掉
        logger.info(f"Passthrough HTTPException in list_quotas: {getattr(e, 'detail', str(e))}")
        raise e
    except Exception as e:
        logger.error(f"获取配额列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotas/{quota_id}", response_model=QuotaStatus)
async def get_quota(
    quota_id: int,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取指定配额信息"""
    try:
        # 模拟获取配额信息
        quota = QuotaStatus(
            quota_id=quota_id,
            api_name="binance_spot",
            quota_type=QuotaType.PER_MINUTE,
            limit_value=60,
            current_usage=25,
            remaining=35,
            reset_at=(datetime.now() + timedelta(minutes=1)).isoformat(),
            status="active",
        )

        logger.info(f"获取配额信息 - QuotaID: {quota_id}, Tenant: {tenant_id}")

        return quota

    except Exception as e:
        logger.error(f"获取配额信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/quotas/{quota_id}", response_model=Dict[str, Any])
async def update_quota(
    quota_id: int,
    quota_update: QuotaUpdateRequest,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """更新配额配置"""
    try:
        # 模拟更新配额
        update_fields = {}
        if quota_update.limit_value is not None:
            update_fields["limit_value"] = quota_update.limit_value
        if quota_update.status is not None:
            update_fields["status"] = quota_update.status

        logger.info(
            f"配额更新成功 - QuotaID: {quota_id}, Fields: {list(update_fields.keys())}, Tenant: {tenant_id}"
        )

        return {
            "success": True,
            "message": "配额更新成功",
            "quota_id": quota_id,
            "updated_fields": list(update_fields.keys()),
        }

    except Exception as e:
        logger.error(f"更新配额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/quotas/{quota_id}", response_model=Dict[str, Any])
async def delete_quota(
    quota_id: int,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """删除配额"""
    try:
        # 模拟删除配额
        logger.info(f"配额删除成功 - QuotaID: {quota_id}, Tenant: {tenant_id}")

        return {"success": True, "message": "配额删除成功", "quota_id": quota_id}

    except Exception as e:
        logger.error(f"删除配额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-limit/check", response_model=Dict[str, Any])
async def check_rate_limit(
    check_request: RateLimitCheckRequest,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """检查API调用是否超过限流"""
    try:
        # 模拟限流检查
        api_name = check_request.api_name
        user_id = check_request.user_id or current_user["user_id"]

        # 模拟当前使用量
        current_usage = 25
        limit_value = 60
        remaining = limit_value - current_usage

        is_allowed = remaining > 0

        result = {
            "allowed": is_allowed,
            "api_name": api_name,
            "current_usage": current_usage,
            "limit_value": limit_value,
            "remaining": remaining,
            "reset_at": (datetime.now() + timedelta(minutes=1)).isoformat(),
            "retry_after": None if is_allowed else 60,
        }

        if not is_allowed:
            logger.warning(
                f"API限流触发 - API: {api_name}, User: {user_id}, Usage: {current_usage}/{limit_value}, Tenant: {tenant_id}"
            )

            # 发布限流告警
            # await zmq_manager.publish_message(
            #     MessageTopics.QUOTA_ALERT,
            #     {"action": "rate_limit_exceeded", "api_name": api_name, "user_id": user_id},
            #     tenant_id
            # )

        return result

    except Exception as e:
        logger.error(f"检查限流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 熔断器管理端点
@router.post("/circuit-breaker", response_model=Dict[str, Any])
async def create_circuit_breaker(
    config_request: CircuitBreakerConfigRequest,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """创建熔断器配置"""
    try:
        # 模拟创建熔断器配置
        circuit_config = {
            "service_name": config_request.service_name,
            "failure_threshold": config_request.failure_threshold,
            "timeout_seconds": config_request.timeout_seconds,
            "half_open_max_calls": config_request.half_open_max_calls,
            "state": CircuitState.CLOSED,
            "failure_count": 0,
            "success_count": 0,
            "created_at": datetime.now().isoformat(),
        }

        logger.info(
            f"熔断器配置创建成功 - Service: {config_request.service_name}, Threshold: {config_request.failure_threshold}, Tenant: {tenant_id}"
        )

        return {"success": True, "message": "熔断器配置创建成功", "config": circuit_config}

    except Exception as e:
        logger.error(f"创建熔断器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breaker", response_model=List[CircuitBreakerStatus])
async def list_circuit_breakers(
    service_name: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取熔断器状态列表"""
    try:
        # 模拟熔断器状态
        circuit_breakers = [
            CircuitBreakerStatus(
                service_name="binance_api",
                state=CircuitState.CLOSED,
                failure_count=1,
                last_failure_time="2024-01-01T10:00:00",
                next_attempt_time=None,
                success_count=150,
            ),
            CircuitBreakerStatus(
                service_name="openai_api",
                state=CircuitState.HALF_OPEN,
                failure_count=3,
                last_failure_time="2024-01-01T11:30:00",
                next_attempt_time="2024-01-01T12:30:00",
                success_count=2,
            ),
            CircuitBreakerStatus(
                service_name="yahoo_api",
                state=CircuitState.OPEN,
                failure_count=5,
                last_failure_time="2024-01-01T11:45:00",
                next_attempt_time="2024-01-01T12:45:00",
                success_count=0,
            ),
        ]

        # 过滤条件
        if service_name:
            circuit_breakers = [
                cb for cb in circuit_breakers if cb.service_name == service_name
            ]

        logger.info(f"获取熔断器状态列表 - Count: {len(circuit_breakers)}, Tenant: {tenant_id}")

        return circuit_breakers

    except Exception as e:
        logger.error(f"获取熔断器状态列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breaker/{service_name}", response_model=CircuitBreakerStatus)
async def get_circuit_breaker(
    service_name: str,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取指定服务的熔断器状态"""
    try:
        # 模拟获取熔断器状态
        circuit_breaker = CircuitBreakerStatus(
            service_name=service_name,
            state=CircuitState.CLOSED,
            failure_count=1,
            last_failure_time="2024-01-01T10:00:00",
            next_attempt_time=None,
            success_count=150,
        )

        logger.info(
            f"获取熔断器状态 - Service: {service_name}, State: {circuit_breaker.state}, Tenant: {tenant_id}"
        )

        return circuit_breaker

    except Exception as e:
        logger.error(f"获取熔断器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breaker/{service_name}/reset", response_model=Dict[str, Any])
async def reset_circuit_breaker(
    service_name: str,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """重置熔断器状态"""
    try:
        # 模拟重置熔断器
        logger.info(f"熔断器重置成功 - Service: {service_name}, Tenant: {tenant_id}")

        # 发布熔断器事件
        # await zmq_manager.publish_message(
        #     MessageTopics.CIRCUIT_BREAKER,
        #     {"action": "circuit_reset", "service_name": service_name},
        #     tenant_id
        # )

        return {
            "success": True,
            "message": "熔断器重置成功",
            "service_name": service_name,
            "new_state": CircuitState.CLOSED,
        }

    except Exception as e:
        logger.error(f"重置熔断器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breaker/{service_name}/test", response_model=Dict[str, Any])
async def test_circuit_breaker(
    service_name: str,
    success: bool = True,
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """测试熔断器（模拟成功/失败调用）"""
    try:
        # 模拟测试熔断器
        if success:
            result = {
                "success": True,
                "message": "模拟成功调用",
                "service_name": service_name,
                "action": "success_recorded",
            }
        else:
            result = {
                "success": False,
                "message": "模拟失败调用",
                "service_name": service_name,
                "action": "failure_recorded",
            }

        logger.info(
            f"熔断器测试 - Service: {service_name}, Success: {success}, Tenant: {tenant_id}"
        )

        return result

    except Exception as e:
        logger.error(f"测试熔断器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, Any])
async def get_quota_circuit_stats(
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """获取配额和熔断器统计信息"""
    try:
        # 模拟统计数据
        stats = {
            "quota_stats": {
                "total_quotas": 15,
                "active_quotas": 12,
                "quota_violations_today": 3,
                "top_limited_apis": [
                    {"api_name": "binance_spot", "violations": 5},
                    {"api_name": "openai_gpt4", "violations": 2},
                ],
            },
            "circuit_breaker_stats": {
                "total_services": 8,
                "healthy_services": 6,
                "open_circuits": 1,
                "half_open_circuits": 1,
                "total_failures_today": 12,
                "recovery_attempts": 3,
            },
            "performance_metrics": {
                "avg_response_time": 245.5,
                "success_rate": 0.96,
                "total_requests_today": 2500,
                "blocked_requests": 45,
            },
            "last_updated": datetime.now().isoformat(),
        }

        logger.info(f"获取配额和熔断器统计信息 - Tenant: {tenant_id}")

        return stats

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def health_check(request: Request):
    """配额和熔断器健康检查"""
    try:
        req_id = (
            request.headers.get("x-request-id")
            or request.headers.get("X-Request-ID")
            or uuid.uuid4().hex
        )
        ts = datetime.now(timezone.utc).isoformat()
        health_status = {
            "success": True,
            "quota_service": "healthy",
            "circuit_breaker_service": "healthy",
            "rate_limiter": "healthy",
            "monitoring": "healthy",
            "timestamp": ts,
            "request_id": req_id,
        }

        return health_status

    except Exception as e:
        logger.error(f"配额和熔断器健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
