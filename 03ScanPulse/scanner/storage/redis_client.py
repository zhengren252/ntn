#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis缓存客户端
提供数据存储、缓存管理和环境隔离功能
严格遵循数据隔离规范和系统级集成流程
"""

import json
import pickle
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheStats:
    """缓存统计信息"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    start_time: str = ""

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# Redis客户端 - 存储层
# 负责通用KV缓存与数据读写

import json
from datetime import datetime
from typing import Any, Dict, Optional

import redis
import structlog
import threading
import time

logger = structlog.get_logger(__name__)


class RedisClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[redis.Redis] = None
        self.is_connected = False

        # 连接配置
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6379)
        self.db = config.get("database", 0)
        self.password = config.get("password")
        self.socket_timeout = config.get("socket_timeout", 5)
        self.socket_connect_timeout = config.get("socket_connect_timeout", 5)
        self.retry_on_timeout = config.get("retry_on_timeout", True)
        self.health_check_interval = config.get("health_check_interval", 30)

        # 键前缀（环境隔离）
        self.key_prefix = config.get("key_prefix", "scanner")

        # 自动重连控制
        self._lock = threading.RLock()
        self._last_reconnect_at = 0.0
        self._reconnect_cooldown = float(config.get("reconnect_cooldown", 2.0))

        logger.info(
            "Storage RedisClient initialized",
            host=self.host,
            port=self.port,
            db=self.db,
            key_prefix=self.key_prefix,
        )

    def connect(self) -> bool:
        try:
            if self.is_connected:
                return True

            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                health_check_interval=self.health_check_interval,
                decode_responses=True,
            )
            self.client.ping()
            self.is_connected = True
            logger.info("Storage Redis connected")
            return True
        except Exception as e:
            logger.error("Storage Redis connect failed", error=str(e))
            self.client = None
            self.is_connected = False
            return False

    def _try_reconnect(self) -> bool:
        with self._lock:
            now = time.time()
            if now - self._last_reconnect_at < self._reconnect_cooldown:
                return False
            self._last_reconnect_at = now
            try:
                self.disconnect()
            except Exception:
                pass
            return self.connect()

    def disconnect(self) -> None:
        try:
            if self.client:
                self.client.close()
                self.client = None
            self.is_connected = False
            logger.info("Storage Redis disconnected")
        except Exception as e:
            logger.error("Storage Redis disconnect error", error=str(e))

    def ping(self) -> bool:
        try:
            if not self.client:
                if not self._try_reconnect():
                    return False
            return bool(self.client.ping())
        except Exception as e:
            logger.error("Storage Redis ping failed", error=str(e))
            if self._try_reconnect():
                try:
                    return bool(self.client.ping())
                except Exception:
                    return False
            return False

    def _k(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        if not self.is_connected and not self._try_reconnect():
            return False
        try:
            payload = json.dumps(value, ensure_ascii=False)
            if ttl:
                return bool(self.client.setex(self._k(key), ttl, payload))
            return bool(self.client.set(self._k(key), payload))
        except Exception as e:
            logger.error("Storage Redis set_json failed", key=key, error=str(e))
            if self._try_reconnect():
                try:
                    if ttl:
                        return bool(self.client.setex(self._k(key), ttl, json.dumps(value, ensure_ascii=False)))
                    return bool(self.client.set(self._k(key), json.dumps(value, ensure_ascii=False)))
                except Exception:
                    return False
            return False

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected and not self._try_reconnect():
            return None
        try:
            raw = self.client.get(self._k(key))
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.error("Storage Redis get_json failed", key=key, error=str(e))
            if self._try_reconnect():
                try:
                    raw = self.client.get(self._k(key))
                    return json.loads(raw) if raw else None
                except Exception:
                    return None
            return None

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        if not self.is_connected and not self._try_reconnect():
            return None
        try:
            return int(self.client.incr(self._k(key), amount))
        except Exception as e:
            logger.error("Storage Redis incr failed", key=key, error=str(e))
            if self._try_reconnect():
                try:
                    return int(self.client.incr(self._k(key), amount))
                except Exception:
                    return None
            return None

    def set_str(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        if not self.is_connected and not self._try_reconnect():
            return False
        try:
            if ttl:
                return bool(self.client.setex(self._k(key), ttl, value))
            return bool(self.client.set(self._k(key), value))
        except Exception as e:
            logger.error("Storage Redis set_str failed", key=key, error=str(e))
            if self._try_reconnect():
                try:
                    if ttl:
                        return bool(self.client.setex(self._k(key), ttl, value))
                    return bool(self.client.set(self._k(key), value))
                except Exception:
                    return False
            return False

    def get_str(self, key: str) -> Optional[str]:
        if not self.is_connected and not self._try_reconnect():
            return None
        try:
            return self.client.get(self._k(key))
        except Exception as e:
            logger.error("Storage Redis get_str failed", key=key, error=str(e))
            if self._try_reconnect():
                try:
                    return self.client.get(self._k(key))
                except Exception:
                    return None
            return None

    def exists(self, key: str) -> bool:
        try:
            if not self.is_connected:
                return False

            redis_key = self._get_key(key)
            return bool(self.client.exists(redis_key))

        except Exception as e:
            logger.error("Error checking key existence", key=key, error=str(e))
            return False

    def expire(self, key: str, ttl: int) -> bool:
        try:
            if not self.is_connected:
                return False

            redis_key = self._get_key(key)
            return bool(self.client.expire(redis_key, ttl))

        except Exception as e:
            logger.error("Error setting expiration", key=key, error=str(e))
            return False

    def ttl(self, key: str) -> int:
        try:
            if not self.is_connected:
                return -1

            redis_key = self._get_key(key)
            return self.client.ttl(redis_key)

        except Exception as e:
            logger.error("Error getting TTL", key=key, error=str(e))
            return -1

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            if not self.is_connected:
                return []

            redis_pattern = self._get_key(pattern)
            keys = self.client.keys(redis_pattern)

            # 移除前缀
            prefix_len = len(self.key_prefix) + 1
            return [key.decode("utf-8")[prefix_len:] for key in keys]

        except Exception as e:
            logger.error("Error getting keys", pattern=pattern, error=str(e))
            return []

    def clear_pattern(self, pattern: str) -> int:
        try:
            if not self.is_connected:
                return 0

            redis_pattern = self._get_key(pattern)
            keys = self.client.keys(redis_pattern)

            if keys:
                deleted = self.client.delete(*keys)
                self.stats.deletes += deleted
                logger.info("Cleared keys by pattern", pattern=pattern, count=deleted)
                return deleted
            else:
                return 0

        except Exception as e:
            logger.error(
                "Error clearing keys by pattern", pattern=pattern, error=str(e)
            )
            return 0

    def flush_db(self) -> bool:
        try:
            if not self.is_connected:
                return False

            self.client.flushdb()
            logger.warning("Database flushed", db=self.db)
            return True

        except Exception as e:
            logger.error("Error flushing database", error=str(e))
            return False

    # 扫描器专用方法
    def store_scan_result(
        self, scan_id: str, result: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """存储扫描结果"""
        key = f"scan_results:{scan_id}"
        return self.set(key, result, ttl or 7200)  # 2小时默认TTL

    def get_scan_result(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描结果"""
        key = f"scan_results:{scan_id}"
        return self.get(key)

    def store_market_data(
        self, symbol: str, data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """存储市场数据"""
        key = f"market_data:{symbol}"
        return self.set(key, data, ttl or 300)  # 5分钟默认TTL

    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据"""
        key = f"market_data:{symbol}"
        return self.get(key)

    def store_opportunity(
        self,
        opportunity_id: str,
        opportunity: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """存储交易机会"""
        key = f"opportunities:{opportunity_id}"
        return self.set(key, opportunity, ttl or 1800)  # 30分钟默认TTL

    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """获取交易机会"""
        key = f"opportunities:{opportunity_id}"
        return self.get(key)

    def store_rule_config(self, rule_name: str, config: Dict[str, Any]) -> bool:
        """存储规则配置"""
        key = f"rule_configs:{rule_name}"
        return self.set(key, config, ttl=None)  # 永不过期

    def get_rule_config(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """获取规则配置"""
        key = f"rule_configs:{rule_name}"
        return self.get(key)

    def store_news_event(
        self, event_id: str, event: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """存储新闻事件"""
        key = f"news_events:{event_id}"
        return self.set(key, event, ttl or 86400)  # 24小时默认TTL

    def get_news_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """获取新闻事件"""
        key = f"news_events:{event_id}"
        return self.get(key)

    def store_scanner_status(self, status: Dict[str, Any]) -> bool:
        """存储扫描器状态"""
        key = "scanner_status"
        return self.set(key, status, ttl=60)  # 1分钟TTL

    def get_scanner_status(self) -> Optional[Dict[str, Any]]:
        """获取扫描器状态"""
        key = "scanner_status"
        return self.get(key)

    # 批量操作
    def batch_set(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """批量设置缓存"""
        success_count = 0

        try:
            if not self.is_connected:
                return 0

            pipe = self.client.pipeline()
            expire_time = ttl or self.default_ttl

            for key, value in items.items():
                try:
                    redis_key = self._get_key(key)
                    serialized_value = self._serialize_value(value)
                    pipe.setex(redis_key, expire_time, serialized_value)
                except Exception as e:
                    logger.error("Error preparing batch set", key=key, error=str(e))

            results = pipe.execute()
            success_count = sum(1 for result in results if result)

            self.stats.sets += success_count
            logger.debug("Batch set completed", total=len(items), success=success_count)

        except Exception as e:
            logger.error("Error in batch set", error=str(e))
            self.stats.errors += 1

        return success_count

    def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        results = {}

        try:
            if not self.is_connected:
                return results

            pipe = self.client.pipeline()
            redis_keys = [self._get_key(key) for key in keys]

            for redis_key in redis_keys:
                pipe.get(redis_key)

            data_list = pipe.execute()

            for i, data in enumerate(data_list):
                key = keys[i]
                if data is not None:
                    try:
                        results[key] = self._deserialize_value(data)
                        self.stats.hits += 1
                    except Exception as e:
                        logger.error(
                            "Error deserializing batch get result",
                            key=key,
                            error=str(e),
                        )
                        self.stats.errors += 1
                else:
                    self.stats.misses += 1

            logger.debug("Batch get completed", requested=len(keys), found=len(results))

        except Exception as e:
            logger.error("Error in batch get", error=str(e))
            self.stats.errors += 1

        return results

    def batch_delete(self, keys: List[str]) -> int:
        """批量删除缓存"""
        try:
            if not self.is_connected:
                return 0

            redis_keys = [self._get_key(key) for key in keys]
            deleted = self.client.delete(*redis_keys)

            self.stats.deletes += deleted
            logger.debug("Batch delete completed", requested=len(keys), deleted=deleted)

            return deleted

        except Exception as e:
            logger.error("Error in batch delete", error=str(e))
            self.stats.errors += 1
            return 0

    # 清理过期数据
    def cleanup_expired_data(self) -> Dict[str, int]:
        """清理过期数据"""
        cleanup_stats = {
            "scan_results": 0,
            "market_data": 0,
            "opportunities": 0,
            "news_events": 0,
        }

        try:
            # 清理过期的扫描结果（超过24小时）
            scan_keys = self.keys("scan_results:*")
            for key in scan_keys:
                ttl_value = self.ttl(key)
                if ttl_value == -1:  # 没有设置过期时间的旧数据
                    self.delete(key)
                    cleanup_stats["scan_results"] += 1

            # 清理过期的市场数据（超过1小时）
            market_keys = self.keys("market_data:*")
            for key in market_keys:
                ttl_value = self.ttl(key)
                if ttl_value == -1:  # 没有设置过期时间的旧数据
                    self.delete(key)
                    cleanup_stats["market_data"] += 1

            # 清理过期的交易机会（超过2小时）
            opportunity_keys = self.keys("opportunities:*")
            for key in opportunity_keys:
                ttl_value = self.ttl(key)
                if ttl_value == -1:  # 没有设置过期时间的旧数据
                    self.delete(key)
                    cleanup_stats["opportunities"] += 1

            # 清理过期的新闻事件（超过7天）
            news_keys = self.keys("news_events:*")
            for key in news_keys:
                ttl_value = self.ttl(key)
                if ttl_value == -1:  # 没有设置过期时间的旧数据
                    self.delete(key)
                    cleanup_stats["news_events"] += 1

            total_cleaned = sum(cleanup_stats.values())
            if total_cleaned > 0:
                logger.info(
                    "Cleanup completed", stats=cleanup_stats, total=total_cleaned
                )

        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

        return cleanup_stats

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = asdict(self.stats)

        # 添加运行时间
        if stats.get("start_time"):
            try:
                start_time = datetime.fromisoformat(stats["start_time"])
                uptime_seconds = (datetime.now() - start_time).total_seconds()
                stats["uptime_seconds"] = uptime_seconds
            except Exception:
                pass

        # 添加连接状态
        stats["is_connected"] = self.is_connected
        stats["key_prefix"] = self.key_prefix
        stats["database"] = self.db

        # 添加Redis服务器信息
        if self.is_connected:
            try:
                info = self.client.info()
                stats["redis_version"] = info.get("redis_version")
                stats["used_memory_human"] = info.get("used_memory_human")
                stats["connected_clients"] = info.get("connected_clients")
                stats["total_commands_processed"] = info.get("total_commands_processed")
            except Exception as e:
                logger.debug("Could not get Redis server info", error=str(e))

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "unknown",
            "connected": self.is_connected,
            "timestamp": datetime.now().isoformat(),
            "errors": [],
        }

        try:
            if not self.is_connected:
                health_status["status"] = "disconnected"
                health_status["errors"].append("Redis client not connected")
                return health_status

            # 测试基本连接
            ping_result = self.client.ping()
            if not ping_result:
                health_status["status"] = "unhealthy"
                health_status["errors"].append("Ping failed")
                return health_status

            # 测试读写操作
            test_key = "health_check_test"
            test_value = {"timestamp": time.time(), "test": True}

            if not self.set(test_key, test_value, ttl=60):
                health_status["status"] = "unhealthy"
                health_status["errors"].append("Write test failed")
                return health_status

            retrieved_value = self.get(test_key)
            if retrieved_value != test_value:
                health_status["status"] = "unhealthy"
                health_status["errors"].append("Read test failed")
                return health_status

            # 清理测试数据
            self.delete(test_key)

            # 获取服务器信息
            try:
                info = self.client.info()
                health_status["redis_info"] = {
                    "version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                }
            except Exception as e:
                health_status["errors"].append(f"Could not get server info: {str(e)}")

            health_status["status"] = "healthy"

        except Exception as e:
            health_status["status"] = "error"
            health_status["errors"].append(f"Health check failed: {str(e)}")
            logger.error("Health check failed", error=str(e))

        return health_status

    def __enter__(self):
        """上下文管理器入口"""
        if not self.is_connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except Exception:
            pass  # 忽略析构时的错误
