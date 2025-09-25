#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型路由（LLM）
职责：对外提供大模型调用端点；内部复用通用API网关调用逻辑，保持一致的认证与限流。
"""

from typing import Dict, Any
from fastapi import APIRouter, Body, Depends, Request

from .api_gateway import (
    APICallRequest,
    APIResponse,
    get_current_user,
    get_tenant_id,
    call_api,
)

router = APIRouter(prefix="/llm", tags=["LLM"])


@router.post("/{model_name}/chat", response_model=APIResponse)
async def chat(
    model_name: str,
    payload: Dict[str, Any] = Body(..., description="聊天请求载荷"),
    request: Request = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> APIResponse:
    """
    聊天接口：转发到配置的大模型API。
    - model_name: 模型名称（如 deepseek 等）
    - payload: 聊天消息与参数
    """
    call = APICallRequest(
        api_name=model_name,
        method="POST",
        path="/chat",
        params=None,
        headers=None,
        body=payload,
    )
    return await call_api(
        call_request=call, request=request, current_user=current_user, tenant_id=tenant_id
    )