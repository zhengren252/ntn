"""Redis cache manager for TACoreService."""

import json
import logging
import pickle
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..config import get_settings


class RedisManager:
    """Redis cache manager for TACoreService.

    Provides caching functionality for request results, market data,
    and other frequently accessed information.
    """

    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.connected = False

        # Cache key prefixes
        self.key_prefixes = {
            "request": "tacoreservice:request:",
            "market_data": "tacoreservice:market:",
            "analysis": "tacoreservice:analysis:",
            "session": "tacoreservice:session:",
            "metrics": "tacoreservice:metrics:",
            "config": "tacoreservice:config:",
        }

        # Backward compatibility
        self.key_prefix = "tacoreservice:"

        # Default TTL values (in seconds)
        self.default_ttl = {
            "request": 3600,  # 1 hour
            "market_data": 300,  # 5 minutes
            "analysis": 1800,  # 30 minutes
            "session": 3600,  # 1 hour
            "metrics": 300,  # 5 minutes
            "config": 86400,  # 24 hours
        }

        # Initialize Redis connection
        self._init_connection()

    def _init_connection(self):
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis not available - caching disabled")
            return

        try:
            # Build Redis URL
            redis_url = self._build_redis_url()

            # Create Redis client
            self.client = redis.from_url(
                redis_url,
                socket_timeout=5,
                socket_connect_timeout=5,
                decode_responses=False,  # We'll handle encoding ourselves
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            self.client.ping()
            self.connected = True

            self.logger.info(
                f"Redis connected: {self.settings.redis_host}:{self.settings.redis_port}"
            )

        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            self.connected = False
            self.client = None

    def _build_redis_url(self) -> str:
        """Build Redis connection URL."""
        if self.settings.redis_password:
            return (
                f"redis://:{self.settings.redis_password}@"
                f"{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"
            )
        else:
            return f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.connected or not self.client:
            return False

        try:
            self.client.ping()
            return True
        except Exception:
            self.connected = False
            return False

    def _get_key(self, key_type: str, key: str) -> str:
        """Get full cache key with prefix."""
        prefix = self.key_prefixes.get(key_type, "tacoreservice:")
        return f"{prefix}{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Use pickle for complex objects, JSON for simple ones
            if isinstance(
                value, (dict, list, str, int, float, bool)
            ) and not isinstance(value, bytes):
                return json.dumps(value, ensure_ascii=False).encode("utf-8")
            else:
                return pickle.dumps(value)
        except Exception as e:
            self.logger.error(f"Serialization error: {e}")
            return pickle.dumps(value)

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            try:
                return json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                return pickle.loads(data)
        except Exception as e:
            self.logger.error(f"Deserialization error: {e}")
            return None

    def set(
        self, key_type: str, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set a value in cache.

        Args:
            key_type: Type of key (request, market_data, etc.)
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            cache_key = self._get_key(key_type, key)
            serialized_value = self._serialize_value(value)

            if ttl is None:
                ttl = self.default_ttl.get(key_type, 3600)

            result = self.client.setex(cache_key, ttl, serialized_value)

            if result:
                self.logger.debug(f"Cached {key_type}:{key} (TTL: {ttl}s)")

            return bool(result)

        except Exception as e:
            self.logger.error(f"Cache set error for {key_type}:{key}: {e}")
            return False

    def get(self, key_type: str, key: str) -> Any:
        """Get a value from cache.

        Args:
            key_type: Type of key (request, market_data, etc.)
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.is_connected():
            return None

        try:
            cache_key = self._get_key(key_type, key)
            data = self.client.get(cache_key)

            if data is None:
                return None

            value = self._deserialize_value(data)
            self.logger.debug(f"Cache hit for {key_type}:{key}")

            return value

        except Exception as e:
            self.logger.error(f"Cache get error for {key_type}:{key}: {e}")
            return None

    def delete(self, key_type: str, key: str) -> bool:
        """Delete a value from cache.

        Args:
            key_type: Type of key
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            cache_key = self._get_key(key_type, key)
            result = self.client.delete(cache_key)

            if result:
                self.logger.debug(f"Deleted cache {key_type}:{key}")

            return bool(result)

        except Exception as e:
            self.logger.error(f"Cache delete error for {key_type}:{key}: {e}")
            return False

    def exists(self, key_type: str, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key_type: Type of key
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            cache_key = self._get_key(key_type, key)
            return bool(self.client.exists(cache_key))

        except Exception as e:
            self.logger.error(f"Cache exists error for {key_type}:{key}: {e}")
            return False

    def expire(self, key_type: str, key: str, ttl: int) -> bool:
        """Set expiration time for a key.

        Args:
            key_type: Type of key
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            cache_key = self._get_key(key_type, key)
            result = self.client.expire(cache_key, ttl)

            return bool(result)

        except Exception as e:
            self.logger.error(f"Cache expire error for {key_type}:{key}: {e}")
            return False

    def get_ttl(self, key_type: str, key: str) -> int:
        """Get remaining TTL for a key.

        Args:
            key_type: Type of key
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self.is_connected():
            return -2

        try:
            cache_key = self._get_key(key_type, key)
            return self.client.ttl(cache_key)

        except Exception as e:
            self.logger.error(f"Cache TTL error for {key_type}:{key}: {e}")
            return -2

    def clear_pattern(self, key_type: str, pattern: str = "*") -> int:
        """Clear keys matching a pattern.

        Args:
            key_type: Type of key
            pattern: Pattern to match (default: all keys of type)

        Returns:
            Number of keys deleted
        """
        if not self.is_connected():
            return 0

        try:
            search_pattern = self._get_key(key_type, pattern)
            keys = list(self.client.scan_iter(match=search_pattern))

            if keys:
                deleted = self.client.delete(*keys)
                self.logger.info(
                    f"Cleared {deleted} cache keys matching {search_pattern}"
                )
                return deleted

            return 0

        except Exception as e:
            self.logger.error(
                f"Cache clear error for pattern {key_type}:{pattern}: {e}"
            )
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics.

        Returns:
            Dictionary containing Redis stats
        """
        if not self.is_connected():
            return {"connected": False}

        try:
            info = self.client.info()
            dbsize = self.client.dbsize()

            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total_requests = hits + misses
            hit_rate = hits / total_requests if total_requests > 0 else 0

            return {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "memory_usage": info.get("used_memory", 0),
                "memory_usage_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_rate": round(hit_rate, 3),
                "total_keys": dbsize,
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }

        except Exception as e:
            self.logger.error(f"Error getting Redis stats: {e}")
            return {"connected": False, "error": str(e)}

    def flush_db(self) -> bool:
        """Flush current database (use with caution).

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            self.client.flushdb()
            self.logger.warning("Redis database flushed")
            return True

        except Exception as e:
            self.logger.error(f"Error flushing Redis database: {e}")
            return False

    def test_connection(self) -> bool:
        """Test Redis connection.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if not self.client:
                self._init_connection()

            if self.client:
                self.client.ping()
                self.connected = True
                return True
            else:
                self.connected = False
                return False

        except Exception as e:
            self.logger.error(f"Redis connection test failed: {e}")
            self.connected = False
            return False

    def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                self.client.close()
                self.logger.info("Redis connection closed")
            except Exception as e:
                self.logger.error(f"Error closing Redis connection: {e}")
            finally:
                self.client = None
                self.connected = False

    # Convenience methods for specific data types
    def cache_market_data(
        self, symbol: str, data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Cache market data for a symbol."""
        return self.set("market_data", symbol, data, ttl)

    def get_cached_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached market data for a symbol."""
        return self.get("market_data", symbol)

    def cache_analysis_result(
        self, symbol: str, result: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Cache analysis result for a symbol."""
        return self.set("analysis", symbol, result, ttl)

    def get_cached_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result for a symbol."""
        return self.get("analysis", symbol)


# Global Redis manager instance
_redis_manager = None


def get_redis_manager() -> RedisManager:
    """Get global Redis manager instance."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager
