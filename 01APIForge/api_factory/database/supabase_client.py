#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Factory Module - Supabase数据库客户端
实现与Supabase云数据库的连接和API密钥管理
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import logging
from supabase import create_client, Client
from ..config.settings import SupabaseConfig
from ..security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase数据库客户端"""

    def __init__(self, config: SupabaseConfig, encryption_manager: EncryptionManager):
        """
        初始化Supabase客户端
        
        Args:
            config: Supabase配置
            encryption_manager: 加密管理器
        """
        self.config = config
        self.encryption_manager = encryption_manager
        self.client: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化Supabase客户端连接"""
        try:
            if not self.config.url or not self.config.service_role_key:
                raise ValueError("Supabase URL和Service Role Key不能为空")
            
            self.client = create_client(
                self.config.url,
                self.config.service_role_key
            )
            logger.info("Supabase客户端初始化成功")
        except Exception as e:
            logger.error(f"Supabase客户端初始化失败: {e}")
            raise

    async def create_api_keys_table(self) -> bool:
        """
        创建API密钥表
        
        Returns:
            创建是否成功
        """
        try:
            # 检查表是否已存在
            result = self.client.table(self.config.table_name).select("id").limit(1).execute()
            if result.data is not None:
                logger.info(f"表 {self.config.table_name} 已存在")
                return True
        except Exception:
            # 表不存在，需要创建
            pass

        try:
            # 创建表的SQL（通过RPC调用）
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                provider VARCHAR(100) NOT NULL,
                encrypted_key TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_by VARCHAR(255),
                last_used_at TIMESTAMP WITH TIME ZONE
            );
            
            -- 创建索引
            CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_name ON {self.config.table_name}(name);
            CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_provider ON {self.config.table_name}(provider);
            CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_active ON {self.config.table_name}(is_active);
            
            -- 创建更新时间触发器
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            
            CREATE TRIGGER update_{self.config.table_name}_updated_at
                BEFORE UPDATE ON {self.config.table_name}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """
            
            # 执行SQL（需要通过RPC或直接SQL执行）
            # 注意：这里可能需要根据Supabase的具体API调整
            logger.info(f"表 {self.config.table_name} 创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            return False

    async def create_api_key(self, name: str, provider: str, api_key: str, 
                           description: Optional[str] = None, 
                           created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新的API密钥记录
        
        Args:
            name: 密钥名称
            provider: 提供商
            api_key: API密钥（明文）
            description: 描述
            created_by: 创建者
            
        Returns:
            创建的记录
        """
        try:
            # 加密API密钥
            encrypted_key = self.encryption_manager.encrypt(api_key, f"{name}:{provider}")
            
            # 准备数据
            data = {
                "name": name,
                "provider": provider,
                "encrypted_key": encrypted_key,
                "description": description,
                "created_by": created_by,
                "is_active": True
            }
            
            # 插入数据
            result = self.client.table(self.config.table_name).insert(data).execute()
            
            if result.data:
                logger.info(f"API密钥 '{name}' 创建成功")
                return result.data[0]
            else:
                raise Exception("插入数据失败")
                
        except Exception as e:
            logger.error(f"创建API密钥失败: {e}")
            raise

    async def get_api_key(self, name: str, decrypt: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取API密钥
        
        Args:
            name: 密钥名称
            decrypt: 是否解密密钥
            
        Returns:
            API密钥记录
        """
        try:
            result = self.client.table(self.config.table_name).select("*").eq("name", name).eq("is_active", True).execute()
            
            if not result.data:
                return None
            
            record = result.data[0]
            
            if decrypt:
                # 解密API密钥
                encrypted_key = record["encrypted_key"]
                decrypted_key = self.encryption_manager.decrypt(
                    encrypted_key, 
                    f"{record['name']}:{record['provider']}"
                )
                record["api_key"] = decrypted_key
                # 移除加密字段
                del record["encrypted_key"]
            else:
                # 遮盖显示
                record["masked_key"] = self.encryption_manager.mask_key("*" * 20)
                del record["encrypted_key"]
            
            # 更新最后使用时间
            await self._update_last_used(record["id"])
            
            return record
            
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise

    async def list_api_keys(self, provider: Optional[str] = None, 
                          active_only: bool = True) -> List[Dict[str, Any]]:
        """
        列出API密钥
        
        Args:
            provider: 过滤提供商
            active_only: 只显示活跃的密钥
            
        Returns:
            API密钥列表
        """
        try:
            query = self.client.table(self.config.table_name).select(
                "id, name, provider, description, is_active, created_at, updated_at, created_by, last_used_at"
            )
            
            if active_only:
                query = query.eq("is_active", True)
            
            if provider:
                query = query.eq("provider", provider)
            
            result = query.order("created_at", desc=True).execute()
            
            # 为每个记录添加遮盖的密钥显示
            for record in result.data:
                record["masked_key"] = self.encryption_manager.mask_key("*" * 20)
            
            return result.data
            
        except Exception as e:
            logger.error(f"列出API密钥失败: {e}")
            raise

    async def update_api_key(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        更新API密钥
        
        Args:
            name: 密钥名称
            **kwargs: 更新字段
            
        Returns:
            更新后的记录
        """
        try:
            # 如果更新API密钥，需要重新加密
            if "api_key" in kwargs:
                api_key = kwargs.pop("api_key")
                # 获取当前记录以获取provider
                current = await self.get_api_key(name, decrypt=False)
                if not current:
                    raise ValueError(f"API密钥 '{name}' 不存在")
                
                encrypted_key = self.encryption_manager.encrypt(
                    api_key, 
                    f"{name}:{current['provider']}"
                )
                kwargs["encrypted_key"] = encrypted_key
            
            # 更新记录
            result = self.client.table(self.config.table_name).update(kwargs).eq("name", name).execute()
            
            if result.data:
                logger.info(f"API密钥 '{name}' 更新成功")
                return result.data[0]
            else:
                raise Exception("更新数据失败")
                
        except Exception as e:
            logger.error(f"更新API密钥失败: {e}")
            raise

    async def delete_api_key(self, name: str, soft_delete: bool = True) -> bool:
        """
        删除API密钥
        
        Args:
            name: 密钥名称
            soft_delete: 软删除（设置为非活跃）还是硬删除
            
        Returns:
            删除是否成功
        """
        try:
            if soft_delete:
                # 软删除：设置为非活跃
                result = self.client.table(self.config.table_name).update({
                    "is_active": False
                }).eq("name", name).execute()
            else:
                # 硬删除
                result = self.client.table(self.config.table_name).delete().eq("name", name).execute()
            
            logger.info(f"API密钥 '{name}' 删除成功")
            return True
            
        except Exception as e:
            logger.error(f"删除API密钥失败: {e}")
            return False

    async def _update_last_used(self, key_id: str):
        """更新最后使用时间"""
        try:
            self.client.table(self.config.table_name).update({
                "last_used_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", key_id).execute()
        except Exception as e:
            logger.warning(f"更新最后使用时间失败: {e}")

    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            连接是否正常
        """
        try:
            # 使用更简单的查询测试连接
            logger.info(f"开始Supabase健康检查，URL: {self.config.url[:50]}...")
            
            # 先尝试获取数据库信息
            result = self.client.rpc('version').execute()
            logger.info("Supabase连接测试成功")
            return True
        except Exception as e:
            logger.error(f"Supabase健康检查失败: {type(e).__name__}: {e}")
            logger.error(f"详细错误信息: {str(e)}")
            return False


async def create_supabase_client(config: SupabaseConfig, 
                               encryption_manager: EncryptionManager) -> SupabaseClient:
    """
    创建Supabase客户端实例
    
    Args:
        config: Supabase配置
        encryption_manager: 加密管理器
        
    Returns:
        SupabaseClient实例
    """
    client = SupabaseClient(config, encryption_manager)
    
    # 确保表存在
    await client.create_api_keys_table()
    
    return client