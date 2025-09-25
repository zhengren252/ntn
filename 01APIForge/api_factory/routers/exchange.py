#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易路由（Exchange）
职责：对外提供交易相关统一API端点；内部复用通用API网关调用逻辑，避免重复实现。
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Body, Depends, Request

from .api_gateway import (
    APICallRequest,
    APIResponse,
    get_current_user,
    get_tenant_id,
    call_api,
)

router = APIRouter(prefix="/exchange", tags=["Exchange"])


@router.post("/{exchange_name}/order", response_model=APIResponse)
async def execute_order(
    exchange_name: str,
    order: Dict[str, Any] = Body(..., description="订单参数"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> APIResponse:
    """
    下单接口：统一转发到配置的交易所API。
    - exchange_name: 交易所名称（如 binance/okx 等）
    - order: 订单参数（侧由上游完成校验与风控）
    """
    call = APICallRequest(
        api_name=exchange_name,
        method="POST",
        path="/order",
        params=None,
        headers=None,
        body=order,
    )
    return await call_api(
        call_request=call, request=request, current_user=current_user, tenant_id=tenant_id
    )


@router.get("/{exchange_name}/klines", response_model=APIResponse)
async def get_klines(
    exchange_name: str,
    symbol: str,
    interval: str = "1h",
    limit: Optional[int] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> APIResponse:
    """
    K线获取接口：统一转发到配置的交易所API。
    - exchange_name: 交易所名称
    - symbol: 交易对（如 BTCUSDT）
    - interval: K线周期（如 1m,5m,1h）
    - limit: 返回条数限制
    """
    params: Dict[str, Any] = {"symbol": symbol, "interval": interval}
    if limit is not None:
        params["limit"] = limit

    call = APICallRequest(
        api_name=exchange_name,
        method="GET",
        path="/klines",
        params=params,
        headers=None,
        body=None,
    )
    return await call_api(
        call_request=call, request=request, current_user=current_user, tenant_id=tenant_id
    )