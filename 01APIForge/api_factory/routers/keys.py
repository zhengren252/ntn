#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Factory Module - API密钥管理路由
实现API密钥的CRUD操作端点
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging
import uuid

from ..database.supabase_client import SupabaseClient
from ..security.encryption import EncryptionManager
from ..config.settings import get_settings
from ..dependencies import get_supabase_client, get_encryption_manager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/keys",
    tags=["API密钥管理"],
    responses={404: {"description": "Not found"}}
)


# Pydantic模型定义
class APIKeyCreate(BaseModel):
    """创建API密钥请求模型"""
    name: str = Field(..., min_length=1, max_length=255, description="密钥名称")
    provider: str = Field(..., min_length=1, max_length=100, description="提供商")
    api_key: str = Field(..., min_length=1, description="API密钥")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    created_by: Optional[str] = Field(None, max_length=255, description="创建者")


class APIKeyUpdate(BaseModel):
    """更新API密钥请求模型"""
    api_key: Optional[str] = Field(None, min_length=1, description="API密钥")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    is_active: Optional[bool] = Field(None, description="是否活跃")


class APIKeyResponse(BaseModel):
    """API密钥响应模型"""
    id: str = Field(..., description="密钥ID")
    name: str = Field(..., description="密钥名称")
    provider: str = Field(..., description="提供商")
    description: Optional[str] = Field(None, description="描述")
    is_active: bool = Field(..., description="是否活跃")
    masked_key: Optional[str] = Field(None, description="遮盖的密钥")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")


class APIKeyDetailResponse(APIKeyResponse):
    """API密钥详细响应模型（包含完整密钥）"""
    api_key: str = Field(..., description="完整API密钥")


class APIResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="响应时间")
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="请求ID")


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    创建新的API密钥
    
    Args:
        key_data: API密钥创建数据
        supabase_client: Supabase客户端
        
    Returns:
        创建结果
    """
    try:
        logger.info(f"创建API密钥: {key_data.name} ({key_data.provider})")
        
        # 检查名称是否已存在
        existing = await supabase_client.get_api_key(key_data.name, decrypt=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"API密钥名称 '{key_data.name}' 已存在"
            )
        
        # 创建API密钥
        result = await supabase_client.create_api_key(
            name=key_data.name,
            provider=key_data.provider,
            api_key=key_data.api_key,
            description=key_data.description,
            created_by=key_data.created_by
        )
        
        return APIResponse(
            success=True,
            message=f"API密钥 '{key_data.name}' 创建成功",
            data={
                "id": result["id"],
                "name": result["name"],
                "provider": result["provider"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建API密钥失败: {str(e)}"
        )


@router.get("/", response_model=APIResponse)
async def list_api_keys(
    provider: Optional[str] = Query(None, description="过滤提供商"),
    active_only: bool = Query(True, description="只显示活跃的密钥"),
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    列出API密钥
    
    Args:
        provider: 过滤提供商
        active_only: 只显示活跃的密钥
        supabase_client: Supabase客户端
        
    Returns:
        API密钥列表
    """
    try:
        logger.info(f"列出API密钥: provider={provider}, active_only={active_only}")
        
        keys = await supabase_client.list_api_keys(
            provider=provider,
            active_only=active_only
        )
        
        return APIResponse(
            success=True,
            message=f"获取到 {len(keys)} 个API密钥",
            data=keys
        )
        
    except Exception as e:
        logger.error(f"列出API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出API密钥失败: {str(e)}"
        )


@router.get("/{name}", response_model=APIResponse)
async def get_api_key(
    name: str,
    decrypt: bool = Query(False, description="是否返回完整密钥"),
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    获取指定的API密钥
    
    Args:
        name: 密钥名称
        decrypt: 是否返回完整密钥
        supabase_client: Supabase客户端
        
    Returns:
        API密钥详情
    """
    try:
        logger.info(f"获取API密钥: {name}, decrypt={decrypt}")
        
        key = await supabase_client.get_api_key(name, decrypt=decrypt)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API密钥 '{name}' 不存在"
            )
        
        return APIResponse(
            success=True,
            message=f"获取API密钥 '{name}' 成功",
            data=key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取API密钥失败: {str(e)}"
        )


@router.put("/{name}", response_model=APIResponse)
async def update_api_key(
    name: str,
    key_data: APIKeyUpdate,
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    更新API密钥
    
    Args:
        name: 密钥名称
        key_data: 更新数据
        supabase_client: Supabase客户端
        
    Returns:
        更新结果
    """
    try:
        logger.info(f"更新API密钥: {name}")
        
        # 检查密钥是否存在
        existing = await supabase_client.get_api_key(name, decrypt=False)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API密钥 '{name}' 不存在"
            )
        
        # 准备更新数据
        update_data = {}
        if key_data.api_key is not None:
            update_data["api_key"] = key_data.api_key
        if key_data.description is not None:
            update_data["description"] = key_data.description
        if key_data.is_active is not None:
            update_data["is_active"] = key_data.is_active
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供更新数据"
            )
        
        # 更新API密钥
        result = await supabase_client.update_api_key(name, **update_data)
        
        return APIResponse(
            success=True,
            message=f"API密钥 '{name}' 更新成功",
            data={
                "id": result["id"],
                "name": result["name"],
                "updated_at": result["updated_at"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新API密钥失败: {str(e)}"
        )


@router.delete("/{name}", response_model=APIResponse)
async def delete_api_key(
    name: str,
    hard_delete: bool = Query(False, description="是否硬删除"),
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    删除API密钥
    
    Args:
        name: 密钥名称
        hard_delete: 是否硬删除
        supabase_client: Supabase客户端
        
    Returns:
        删除结果
    """
    try:
        logger.info(f"删除API密钥: {name}, hard_delete={hard_delete}")
        
        # 检查密钥是否存在
        existing = await supabase_client.get_api_key(name, decrypt=False)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API密钥 '{name}' 不存在"
            )
        
        # 删除API密钥
        success = await supabase_client.delete_api_key(name, soft_delete=not hard_delete)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除API密钥 '{name}' 失败"
            )
        
        delete_type = "硬删除" if hard_delete else "软删除"
        return APIResponse(
            success=True,
            message=f"API密钥 '{name}' {delete_type}成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除API密钥失败: {str(e)}"
        )


@router.get("/health/check", response_model=APIResponse)
async def health_check(
    request: Request,
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    健康检查端点
    
    Args:
        request: FastAPI 请求对象，用于链路追踪
        supabase_client: Supabase客户端
        
    Returns:
        健康状态
    """
    try:
        is_healthy = await supabase_client.health_check()
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        ts = datetime.now(timezone.utc)
        
        if is_healthy:
            return APIResponse(
                success=True,
                message="API密钥管理服务运行正常",
                timestamp=ts,
                request_id=req_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库连接异常"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"健康检查失败: {str(e)}"
        )


@router.post("/providers/{provider}/test", response_model=APIResponse)
async def test_api_key(
    provider: str,
    name: str = Query(..., description="密钥名称"),
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    测试API密钥有效性
    
    Args:
        provider: 提供商
        name: 密钥名称
        supabase_client: Supabase客户端
        
    Returns:
        测试结果
    """
    try:
        logger.info(f"测试API密钥: {name} ({provider})")
        
        # 获取API密钥
        key = await supabase_client.get_api_key(name, decrypt=True)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API密钥 '{name}' 不存在"
            )
        
        if key["provider"] != provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"密钥提供商不匹配: 期望 {provider}, 实际 {key['provider']}"
            )
        
        # TODO: 实现具体的API密钥测试逻辑
        # 这里应该根据不同的provider调用相应的API进行测试
        
        return APIResponse(
            success=True,
            message=f"API密钥 '{name}' 测试功能待实现",
            data={
                "provider": provider,
                "name": name,
                "test_status": "pending"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试API密钥失败: {str(e)}"
        )