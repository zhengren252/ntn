#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - Redis缓存管理
实现基于Redis的缓存功能和数据管理

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import json
import logging
import pickle
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from .config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RedisCache:
    """Redis缓存管理器"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self.connected = False

    async def connect(self):
        """连接到Redis服务器"""
        try:
            # 创建连接池
            redis_config = settings.get_redis_config()
            
            # 从REDIS_URL解析连接信息
            redis_url = redis_config.get("url", "redis://localhost:6379")
            
            self.connection_pool = ConnectionPool.from_url(
                redis_url,
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                max_connections=redis_config.get("max_connections", 20),
                decode_responses=redis_config.get("decode_responses", True),
                socket_timeout=30,
                socket_connect_timeout=10,
                retry_on_timeout=True,
            )

            # 创建Redis客户端
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # 测试连接
            await self.redis_client.ping()

            self.connected = True
            logger.info("Redis连接成功")

        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()

        if self.connection_pool:
            await self.connection_pool.disconnect()

        self.connected = False
        logger.info("Redis连接已断开")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.connected:
            await self.connect()

        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (int, float, str, bool)):
                serialized_value = str(value)
            else:
                # 使用pickle序列化复杂对象
                serialized_value = pickle.dumps(value)

            # 设置缓存
            if ttl:
                result = await self.redis_client.setex(key, ttl, serialized_value)
            else:
                result = await self.redis_client.set(key, serialized_value)

            return result

        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        if not self.connected:
            await self.connect()

        try:
            value = await self.redis_client.get(key)

            if value is None:
                return default

            # 尝试反序列化
            try:
                # 首先尝试JSON反序列化
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    # 尝试pickle反序列化
                    return pickle.loads(value)
                except (pickle.PickleError, TypeError):
                    # 返回原始字符串
                    return value

        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return default

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.connected:
            await self.connect()

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.connected:
            await self.connect()

        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间"""
        if not self.connected:
            await self.connect()

        try:
            result = await self.redis_client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"设置缓存过期时间失败 {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取缓存剩余生存时间"""
        if not self.connected:
            await self.connect()

        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"获取缓存TTL失败 {key}: {e}")
            return -1

    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的所有键"""
        if not self.connected:
            await self.connect()

        try:
            return await self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"获取缓存键失败 {pattern}: {e}")
            return []

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有缓存"""
        if not self.connected:
            await self.connect()

        try:
            keys = await self.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"清除缓存模式失败 {pattern}: {e}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        if not self.connected:
            await self.connect()

        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增计数器失败 {key}: {e}")
            return 0

    async def decrement(self, key: str, amount: int = 1) -> int:
        """递减计数器"""
        if not self.connected:
            await self.connect()

        try:
            return await self.redis_client.decrby(key, amount)
        except Exception as e:
            logger.error(f"递减计数器失败 {key}: {e}")
            return 0


class SimulationCache:
    """仿真专用缓存管理器"""

    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.prefix = "mms:simulation:"

    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键"""
        return f"{self.prefix}{key}"

    async def cache_simulation_result(
        self, task_id: str, result: dict, ttl: int = None
    ) -> bool:
        """缓存仿真结果"""
        key = self._make_key(f"result:{task_id}")
        cache_ttl = ttl or settings.CACHE_TTL

        cache_data = {
            "result": result,
            "cached_at": datetime.now().isoformat(),
            "task_id": task_id,
        }

        return await self.cache.set(key, cache_data, cache_ttl)

    async def get_simulation_result(self, task_id: str) -> Optional[dict]:
        """获取缓存的仿真结果"""
        key = self._make_key(f"result:{task_id}")
        return await self.cache.get(key)

    async def cache_market_data(
        self, symbol: str, timeframe: str, data: List[dict], ttl: int = None
    ) -> bool:
        """缓存市场数据"""
        key = self._make_key(f"market_data:{symbol}:{timeframe}")
        cache_ttl = ttl or settings.MARKET_DATA_CACHE_TTL

        cache_data = {
            "data": data,
            "symbol": symbol,
            "timeframe": timeframe,
            "cached_at": datetime.now().isoformat(),
            "count": len(data),
        }

        return await self.cache.set(key, cache_data, cache_ttl)

    async def get_market_data(
        self, symbol: str, timeframe: str
    ) -> Optional[List[dict]]:
        """获取缓存的市场数据"""
        key = self._make_key(f"market_data:{symbol}:{timeframe}")
        cached_data = await self.cache.get(key)

        if cached_data and isinstance(cached_data, dict):
            return cached_data.get("data")

        return None

    async def cache_calibration_params(
        self, symbol: str, scenario: str, params: dict, ttl: int = None
    ) -> bool:
        """缓存校准参数"""
        key = self._make_key(f"calibration:{symbol}:{scenario}")
        cache_ttl = ttl or settings.CACHE_TTL

        cache_data = {
            "params": params,
            "symbol": symbol,
            "scenario": scenario,
            "cached_at": datetime.now().isoformat(),
        }

        return await self.cache.set(key, cache_data, cache_ttl)

    async def get_calibration_params(
        self, symbol: str, scenario: str
    ) -> Optional[dict]:
        """获取缓存的校准参数"""
        key = self._make_key(f"calibration:{symbol}:{scenario}")
        cached_data = await self.cache.get(key)

        if cached_data and isinstance(cached_data, dict):
            return cached_data.get("params")

        return None

    async def cache_task_status(
        self, task_id: str, status: dict, ttl: int = 3600
    ) -> bool:
        """缓存任务状态"""
        key = self._make_key(f"status:{task_id}")

        status_data = {
            "status": status,
            "task_id": task_id,
            "updated_at": datetime.now().isoformat(),
        }

        return await self.cache.set(key, status_data, ttl)

    async def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取缓存的任务状态"""
        key = self._make_key(f"status:{task_id}")
        cached_data = await self.cache.get(key)

        if cached_data and isinstance(cached_data, dict):
            return cached_data.get("status")

        return None

    async def increment_task_counter(self, counter_type: str) -> int:
        """递增任务计数器"""
        key = self._make_key(f"counter:{counter_type}")
        return await self.cache.increment(key)

    async def get_task_counter(self, counter_type: str) -> int:
        """获取任务计数器"""
        key = self._make_key(f"counter:{counter_type}")
        value = await self.cache.get(key, 0)
        return int(value) if value is not None else 0

    async def cache_worker_stats(
        self, worker_id: str, stats: dict, ttl: int = 300
    ) -> bool:
        """缓存工作进程统计信息"""
        key = self._make_key(f"worker:{worker_id}")

        stats_data = {
            "stats": stats,
            "worker_id": worker_id,
            "updated_at": datetime.now().isoformat(),
        }

        return await self.cache.set(key, stats_data, ttl)

    async def get_worker_stats(self, worker_id: str) -> Optional[dict]:
        """获取缓存的工作进程统计信息"""
        key = self._make_key(f"worker:{worker_id}")
        cached_data = await self.cache.get(key)

        if cached_data and isinstance(cached_data, dict):
            return cached_data.get("stats")

        return None

    async def get_all_worker_stats(self) -> Dict[str, dict]:
        """获取所有工作进程的统计信息"""
        pattern = self._make_key("worker:*")
        keys = await self.cache.keys(pattern)

        worker_stats = {}
        for key in keys:
            worker_id = key.split(":")[-1]
            stats = await self.get_worker_stats(worker_id)
            if stats:
                worker_stats[worker_id] = stats

        return worker_stats

    async def clear_simulation_cache(self, task_id: str = None) -> int:
        """清除仿真缓存"""
        if task_id:
            # 清除特定任务的缓存
            patterns = [
                self._make_key(f"result:{task_id}"),
                self._make_key(f"status:{task_id}"),
            ]

            count = 0
            for pattern in patterns:
                if await self.cache.delete(pattern):
                    count += 1

            return count
        else:
            # 清除所有仿真缓存
            pattern = self._make_key("*")
            return await self.cache.clear_pattern(pattern)

    async def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        try:
            # 获取各类缓存的数量
            result_keys = await self.cache.keys(self._make_key("result:*"))
            status_keys = await self.cache.keys(self._make_key("status:*"))
            market_data_keys = await self.cache.keys(self._make_key("market_data:*"))
            calibration_keys = await self.cache.keys(self._make_key("calibration:*"))
            worker_keys = await self.cache.keys(self._make_key("worker:*"))

            return {
                "total_keys": len(result_keys)
                + len(status_keys)
                + len(market_data_keys)
                + len(calibration_keys)
                + len(worker_keys),
                "result_cache_count": len(result_keys),
                "status_cache_count": len(status_keys),
                "market_data_cache_count": len(market_data_keys),
                "calibration_cache_count": len(calibration_keys),
                "worker_cache_count": len(worker_keys),
                "updated_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局缓存实例
_redis_cache: Optional[RedisCache] = None
_simulation_cache: Optional[SimulationCache] = None


async def get_redis_cache() -> RedisCache:
    """获取Redis缓存实例"""
    global _redis_cache

    if _redis_cache is None:
        _redis_cache = RedisCache()
        await _redis_cache.connect()

    return _redis_cache


async def get_simulation_cache() -> SimulationCache:
    """获取仿真缓存实例"""
    global _simulation_cache

    if _simulation_cache is None:
        redis_cache = await get_redis_cache()
        _simulation_cache = SimulationCache(redis_cache)

    return _simulation_cache


async def cleanup_cache():
    """清理缓存资源"""
    global _redis_cache, _simulation_cache

    if _redis_cache:
        await _redis_cache.disconnect()
        _redis_cache = None

    _simulation_cache = None
