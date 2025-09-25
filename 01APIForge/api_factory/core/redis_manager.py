#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis管理器 - 缓存和会话管理
核心设计理念：数据隔离、高性能缓存、会话管理
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
import redis.asyncio as redis
from ..config.settings import RedisConfig

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis管理器 - 缓存和会话管理"""

    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None

        # 统计信息
        self.stats = {
            "operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "start_time": None,
        }

        # 键前缀 - 数据隔离
        self.key_prefixes = {
            "session": "session:",
            "cache": "cache:",
            "quota": "quota:",
            "circuit": "circuit:",
            "auth": "auth:",
            "tenant": "tenant:",
        }

    async def initialize(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self.connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                max_connections=self.config.max_connections,
                decode_responses=True,
            )

            # 创建Redis客户端
            self.client = redis.Redis(connection_pool=self.connection_pool)

            # 测试连接
            await self.client.ping()

            self.stats["start_time"] = datetime.now()
            logger.info(
                f"Redis管理器初始化完成 - {self.config.host}:{self.config.port}/{self.config.db}"
            )

        except Exception as e:
            logger.warning(f"Redis初始化失败，将在模拟模式下运行: {e}")
            # 不抛出异常，允许应用在没有Redis的情况下启动
            self.client = None
            self.connection_pool = None
            self.stats["start_time"] = datetime.now()

    def _build_key(
        self, key_type: str, key: str, tenant_id: Optional[str] = None
    ) -> str:
        """构建键名 - 支持数据隔离"""
        prefix = self.key_prefixes.get(key_type, "")
        if tenant_id:
            return f"{prefix}{tenant_id}:{key}"
        return f"{prefix}{key}"

    async def set_cache(
        self, key: str, value: Any, ttl: int = 3600, tenant_id: Optional[str] = None
    ) -> bool:
        """设置缓存"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，跳过缓存设置 - Key: {key}")
                return False

            cache_key = self._build_key("cache", key, tenant_id)

            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)

            # 设置缓存
            result = await self.client.setex(cache_key, ttl, serialized_value)

            self.stats["operations"] += 1
            logger.debug(f"缓存已设置 - Key: {cache_key}, TTL: {ttl}")

            return result

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"设置缓存失败: {e}")
            return False

    async def get_cache(
        self, key: str, tenant_id: Optional[str] = None
    ) -> Optional[Any]:
        """获取缓存"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，返回空缓存 - Key: {key}")
                return None

            cache_key = self._build_key("cache", key, tenant_id)
            value = await self.client.get(cache_key)

            self.stats["operations"] += 1

            if value is None:
                self.stats["cache_misses"] += 1
                return None

            self.stats["cache_hits"] += 1

            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取缓存失败: {e}")
            return None

    async def delete_cache(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """删除缓存"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，跳过缓存删除 - Key: {key}")
                return False

            cache_key = self._build_key("cache", key, tenant_id)
            result = await self.client.delete(cache_key)

            self.stats["operations"] += 1
            logger.debug(f"缓存已删除 - Key: {cache_key}")

            return result > 0

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"删除缓存失败: {e}")
            return False

    async def set_session(
        self, session_id: str, session_data: Dict[str, Any], ttl: int = 1800
    ) -> bool:
        """设置会话数据"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，跳过会话设置 - Session: {session_id}")
                return False

            session_key = self._build_key("session", session_id)
            session_json = json.dumps(session_data, ensure_ascii=False)

            result = await self.client.setex(session_key, ttl, session_json)

            self.stats["operations"] += 1
            logger.debug(f"会话已设置 - Session: {session_id}, TTL: {ttl}")

            return result

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"设置会话失败: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，返回空会话 - Session: {session_id}")
                return None

            session_key = self._build_key("session", session_id)
            session_data = await self.client.get(session_key)

            self.stats["operations"] += 1

            if session_data:
                return json.loads(session_data)
            return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取会话失败: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，跳过会话删除 - Session: {session_id}")
                return False

            session_key = self._build_key("session", session_id)
            result = await self.client.delete(session_key)

            self.stats["operations"] += 1
            logger.debug(f"会话已删除 - Session: {session_id}")

            return result > 0

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"删除会话失败: {e}")
            return False

    async def increment_quota(
        self, key: str, window: int = 60, tenant_id: Optional[str] = None
    ) -> int:
        """增加配额计数 - 用于限流"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，返回模拟配额计数 - Key: {key}")
                return 1

            quota_key = self._build_key("quota", key, tenant_id)

            # 使用管道执行原子操作
            pipe = self.client.pipeline()
            pipe.incr(quota_key)
            pipe.expire(quota_key, window)
            results = await pipe.execute()

            count = results[0]

            self.stats["operations"] += 1
            logger.debug(f"配额计数 - Key: {quota_key}, Count: {count}")

            return count

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"增加配额计数失败: {e}")
            return 0

    async def get_quota_count(self, key: str, tenant_id: Optional[str] = None) -> int:
        """获取配额计数"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，返回模拟配额计数 - Key: {key}")
                return 0

            quota_key = self._build_key("quota", key, tenant_id)
            count = await self.client.get(quota_key)

            self.stats["operations"] += 1

            return int(count) if count else 0

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取配额计数失败: {e}")
            return 0

    async def set_circuit_breaker(
        self, service: str, state: str, ttl: int = 60, tenant_id: Optional[str] = None
    ) -> bool:
        """设置熔断器状态"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，跳过熔断器设置 - Service: {service}")
                return False

            circuit_key = self._build_key("circuit", service, tenant_id)
            circuit_data = {
                "state": state,
                "timestamp": datetime.now().isoformat(),
                "service": service,
            }

            result = await self.client.setex(circuit_key, ttl, json.dumps(circuit_data))

            self.stats["operations"] += 1
            logger.debug(f"熔断器状态已设置 - Service: {service}, State: {state}")

            return result

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"设置熔断器状态失败: {e}")
            return False

    async def get_circuit_breaker(
        self, service: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取熔断器状态"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，返回默认熔断器状态 - Service: {service}")
                return {
                    "state": "closed",
                    "timestamp": datetime.now().isoformat(),
                    "service": service,
                }

            circuit_key = self._build_key("circuit", service, tenant_id)
            circuit_data = await self.client.get(circuit_key)

            self.stats["operations"] += 1

            if circuit_data:
                return json.loads(circuit_data)
            return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取熔断器状态失败: {e}")
            return None

    async def publish_message(self, channel: str, message: Dict[str, Any]) -> int:
        """发布消息到频道"""
        try:
            if not self.client:
                raise RuntimeError("Redis客户端未初始化")

            message_json = json.dumps(message, ensure_ascii=False)
            result = await self.client.publish(channel, message_json)

            self.stats["operations"] += 1
            logger.debug(f"消息已发布 - Channel: {channel}")

            return result

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"发布消息失败: {e}")
            return 0

    async def get_keys_by_pattern(
        self, pattern: str, tenant_id: Optional[str] = None
    ) -> List[str]:
        """根据模式获取键列表"""
        try:
            if not self.client:
                logger.debug(f"Redis不可用，返回空键列表 - Pattern: {pattern}")
                return []

            if tenant_id:
                search_pattern = f"*{tenant_id}:{pattern}"
            else:
                search_pattern = pattern

            keys = await self.client.keys(search_pattern)

            self.stats["operations"] += 1

            return keys

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"获取键列表失败: {e}")
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.client:
                return False

            # 执行ping命令
            result = await self.client.ping()
            return result is True

        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            info = await self.client.info() if self.client else {}

            uptime = None
            if self.stats["start_time"]:
                uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

            return {
                **self.stats,
                "uptime_seconds": uptime,
                "redis_info": {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                },
            }

        except Exception as e:
            logger.error(f"获取Redis统计信息失败: {e}")
            return self.stats

    async def cleanup(self):
        """清理资源"""
        try:
            if self.client:
                await self.client.close()
            if self.connection_pool:
                await self.connection_pool.disconnect()

            logger.info("Redis管理器已清理")

        except Exception as e:
            logger.error(f"Redis清理失败: {e}")

    # Redis键命名常量

    """Redis键命名规范"""

    # 会话相关
    USER_SESSION = "user_session"
    API_SESSION = "api_session"

    # 缓存相关
    API_RESPONSE = "api_response"
    USER_INFO = "user_info"
    CONFIG_CACHE = "config_cache"

    # 限流相关
    RATE_LIMIT = "rate_limit"
    API_QUOTA = "api_quota"

    # 熔断器相关
    CIRCUIT_BREAKER = "circuit_breaker"
    SERVICE_HEALTH = "service_health"
