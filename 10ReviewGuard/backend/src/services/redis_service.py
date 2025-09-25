#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis缓存服务

负责ReviewGuard模组的Redis缓存操作：
1. 缓存连接管理
2. 会话存储和管理
3. 审核队列管理
4. 实时数据缓存
"""

import os
import json
import asyncio
# 优先使用redis.asyncio以避免旧版aioredis的兼容性问题
try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - 兼容少数环境
    import aioredis  # type: ignore
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

try:
    from ..utils.logger import setup_logger
except ImportError:
    from utils.logger import setup_logger

logger = setup_logger(__name__)

class RedisService:
    """Redis缓存服务类"""
    
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        
        self.redis_client = None
        
        # 缓存键前缀
        self.KEY_PREFIX = "reviewguard:"
        self.SESSION_PREFIX = f"{self.KEY_PREFIX}session:"
        self.QUEUE_PREFIX = f"{self.KEY_PREFIX}queue:"
        self.CACHE_PREFIX = f"{self.KEY_PREFIX}cache:"
        self.LOCK_PREFIX = f"{self.KEY_PREFIX}lock:"
    
    async def initialize(self):
        """初始化Redis连接"""
        try:
            logger.info(f"正在连接Redis: {self.redis_host}:{self.redis_port}")
            
            # 创建Redis连接（from_url在redis.asyncio与aioredis均可用）
            self.redis_client = aioredis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}",
                password=self.redis_password,
                db=self.redis_db,
                encoding="utf-8",
                decode_responses=True
            )
            
            # 测试连接
            await self.redis_client.ping()
            
            logger.info("Redis连接成功")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis连接已关闭")
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        return self.redis_client is not None
    
    async def ping(self) -> bool:
        """检查Redis服务状态"""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis ping失败: {e}")
        return False
    
    # 基础缓存操作
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """设置缓存值"""
        try:
            full_key = f"{self.CACHE_PREFIX}{key}"
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            if expire:
                await self.redis_client.setex(full_key, expire, value)
            else:
                await self.redis_client.set(full_key, value)
            
            return True
        except Exception as e:
            logger.error(f"Redis设置失败 {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            full_key = f"{self.CACHE_PREFIX}{key}"
            value = await self.redis_client.get(full_key)
            
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis获取失败 {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            full_key = f"{self.CACHE_PREFIX}{key}"
            result = await self.redis_client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis删除失败 {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            full_key = f"{self.CACHE_PREFIX}{key}"
            return await self.redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Redis检查存在失败 {key}: {e}")
            return False
    
    # 会话管理
    async def create_session(self, user_id: str, session_data: Dict[str, Any], expire: int = 3600) -> str:
        """创建用户会话"""
        import uuid
        
        session_id = f"sess_{uuid.uuid4().hex}"
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        
        session_info = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_access": datetime.now().isoformat(),
            **session_data
        }
        
        try:
            await self.redis_client.setex(
                session_key, 
                expire, 
                json.dumps(session_info, ensure_ascii=False)
            )
            
            logger.info(f"已创建会话: {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        try:
            session_key = f"{self.SESSION_PREFIX}{session_id}"
            session_data = await self.redis_client.get(session_key)
            
            if session_data:
                session_info = json.loads(session_data)
                
                # 更新最后访问时间
                session_info["last_access"] = datetime.now().isoformat()
                await self.redis_client.set(
                    session_key, 
                    json.dumps(session_info, ensure_ascii=False)
                )
                
                return session_info
            
            return None
            
        except Exception as e:
            logger.error(f"获取会话失败 {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            session_key = f"{self.SESSION_PREFIX}{session_id}"
            result = await self.redis_client.delete(session_key)
            
            if result > 0:
                logger.info(f"已删除会话: {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除会话失败 {session_id}: {e}")
            return False
    
    # 队列管理
    async def push_to_queue(self, queue_name: str, item: Any) -> bool:
        """推送项目到队列"""
        try:
            queue_key = f"{self.QUEUE_PREFIX}{queue_name}"
            
            if isinstance(item, (dict, list)):
                item = json.dumps(item, ensure_ascii=False)
            
            await self.redis_client.lpush(queue_key, item)
            return True
        except Exception as e:
            logger.error(f"推送到队列失败 {queue_name}: {e}")
            return False
    
    async def pop_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """从队列弹出项目"""
        try:
            queue_key = f"{self.QUEUE_PREFIX}{queue_name}"
            
            if timeout > 0:
                result = await self.redis_client.brpop(queue_key, timeout=timeout)
                if result:
                    _, item = result
                else:
                    return None
            else:
                item = await self.redis_client.rpop(queue_key)
            
            if item:
                try:
                    return json.loads(item)
                except (json.JSONDecodeError, TypeError):
                    return item
            
            return None
            
        except Exception as e:
            logger.error(f"从队列弹出失败 {queue_name}: {e}")
            return None
    
    async def get_queue_length(self, queue_name: str) -> int:
        """获取队列长度"""
        try:
            queue_key = f"{self.QUEUE_PREFIX}{queue_name}"
            return await self.redis_client.llen(queue_key)
        except Exception as e:
            logger.error(f"获取队列长度失败 {queue_name}: {e}")
            return 0
    
    # 分布式锁
    async def acquire_lock(self, lock_name: str, expire: int = 30) -> bool:
        """获取分布式锁"""
        try:
            lock_key = f"{self.LOCK_PREFIX}{lock_name}"
            
            # 使用SET NX EX命令原子性获取锁
            result = await self.redis_client.set(
                lock_key, 
                "locked", 
                nx=True, 
                ex=expire
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"获取锁失败 {lock_name}: {e}")
            return False
    
    async def release_lock(self, lock_name: str) -> bool:
        """释放分布式锁"""
        try:
            lock_key = f"{self.LOCK_PREFIX}{lock_name}"
            result = await self.redis_client.delete(lock_key)
            return result > 0
        except Exception as e:
            logger.error(f"释放锁失败 {lock_name}: {e}")
            return False
    
    # 统计和监控
    async def increment_counter(self, counter_name: str, amount: int = 1) -> int:
        """递增计数器"""
        try:
            counter_key = f"{self.CACHE_PREFIX}counter:{counter_name}"
            return await self.redis_client.incrby(counter_key, amount)
        except Exception as e:
            logger.error(f"递增计数器失败 {counter_name}: {e}")
            return 0
    
    async def get_counter(self, counter_name: str) -> int:
        """获取计数器值"""
        try:
            counter_key = f"{self.CACHE_PREFIX}counter:{counter_name}"
            value = await self.redis_client.get(counter_key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"获取计数器失败 {counter_name}: {e}")
            return 0
    
    async def reset_counter(self, counter_name: str) -> bool:
        """重置计数器"""
        try:
            counter_key = f"{self.CACHE_PREFIX}counter:{counter_name}"
            await self.redis_client.delete(counter_key)
            return True
        except Exception as e:
            logger.error(f"重置计数器失败 {counter_name}: {e}")
            return False
    
    # 缓存策略相关数据
    async def cache_strategy_data(self, strategy_id: str, data: Dict[str, Any], expire: int = 1800):
        """缓存策略数据"""
        key = f"strategy:{strategy_id}"
        await self.set(key, data, expire)
    
    async def get_cached_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的策略数据"""
        key = f"strategy:{strategy_id}"
        return await self.get(key)
    
    async def cache_review_result(self, review_id: str, result: Dict[str, Any], expire: int = 3600):
        """缓存审核结果"""
        key = f"review_result:{review_id}"
        await self.set(key, result, expire)
    
    async def get_cached_review_result(self, review_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的审核结果"""
        key = f"review_result:{review_id}"
        return await self.get(key)
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            stats = {
                "redis_info": await self.redis_client.info(),
                "pending_reviews": await self.get_queue_length("pending_reviews"),
                "active_sessions": len(await self.redis_client.keys(f"{self.SESSION_PREFIX}*")),
                "cache_keys": len(await self.redis_client.keys(f"{self.CACHE_PREFIX}*")),
                "total_reviews": await self.get_counter("total_reviews"),
                "approved_reviews": await self.get_counter("approved_reviews"),
                "rejected_reviews": await self.get_counter("rejected_reviews")
            }
            return stats
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}