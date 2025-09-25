# Redis客户端
# 实现缓存和数据存储，严格遵循数据隔离与环境管理规范

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis
import structlog
import threading
import time

logger = structlog.get_logger(__name__)


class RedisClient:
    """Redis客户端 - 实现缓存和数据存储"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.is_connected = False

        # 配置参数
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

        # TTL配置
        self.default_ttl = config.get("default_ttl", 3600)  # 1小时
        self.ttl_config = config.get("ttl", {})

        # 自动重连控制
        self._lock = threading.RLock()
        self._last_reconnect_at = 0.0
        self._reconnect_cooldown = float(config.get("reconnect_cooldown", 2.0))
        self._max_retries = int(config.get("max_retries", 1))

        logger.info(
            "RedisClient initialized",
            host=self.host,
            port=self.port,
            db=self.db,
            key_prefix=self.key_prefix,
        )

    def connect(self) -> bool:
        """建立Redis连接"""
        try:
            if self.is_connected:
                logger.warning("Redis client already connected")
                return True

            # 创建Redis连接
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

            # 测试连接
            self.client.ping()

            self.is_connected = True
            logger.info("Redis client connected successfully")

            return True

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.client = None
            self.is_connected = False
            return False

    def _try_reconnect(self) -> bool:
        """线程安全的重连尝试，带冷却时间以避免抖动"""
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
        """断开Redis连接"""
        try:
            if self.client:
                self.client.close()
                self.client = None

            self.is_connected = False
            logger.info("Redis client disconnected")

        except Exception as e:
            logger.error("Error disconnecting Redis client", error=str(e))

    def ping(self) -> bool:
        """检查与Redis的连接健康状态

        Returns:
            bool: True 表示连接正常，False 表示不可用
        """
        try:
            if not self.client:
                # 尝试自动重连
                if not self._try_reconnect():
                    return False
            return bool(self.client.ping())
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            # ping失败时尝试一次重连
            if self._try_reconnect():
                try:
                    return bool(self.client.ping())
                except Exception:
                    return False
            return False

    def _get_key(self, key: str) -> str:
        """获取带前缀的键名（环境隔离）"""
        return f"{self.key_prefix}:{key}"

    def _get_ttl(self, data_type: str) -> int:
        """获取数据类型对应的TTL"""
        return self.ttl_config.get(data_type, self.default_ttl)

    def set_scan_result(
        self, symbol: str, result: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """存储扫描结果

        Args:
            symbol: 交易对符号
            result: 扫描结果
            ttl: 过期时间（秒），默认使用配置值

        Returns:
            是否存储成功
        """
        if not self.is_connected and not self._try_reconnect():
            logger.error("Redis client not connected")
            return False

        try:
            key = self._get_key(f"scan_result:{symbol}")

            # 添加时间戳
            result_with_meta = {
                **result,
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
            }

            # 序列化并存储
            value = json.dumps(result_with_meta, ensure_ascii=False)
            ttl_seconds = ttl or self._get_ttl("scan_result")

            success = self.client.setex(key, ttl_seconds, value)

            if success:
                logger.debug(
                    "Scan result stored",
                    symbol=symbol,
                    ttl=ttl_seconds,
                    score=result.get("score"),
                )

            return bool(success)

        except Exception as e:
            logger.error("Failed to store scan result", symbol=symbol, error=str(e))
            # 一次重试机会
            if self._try_reconnect():
                try:
                    key = self._get_key(f"scan_result:{symbol}")
                    value = json.dumps(result_with_meta, ensure_ascii=False)
                    ttl_seconds = ttl or self._get_ttl("scan_result")
                    return bool(self.client.setex(key, ttl_seconds, value))
                except Exception:
                    return False
            return False

    def get_scan_result(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取扫描结果

        Args:
            symbol: 交易对符号

        Returns:
            扫描结果或None
        """
        if not self.is_connected and not self._try_reconnect():
            logger.error("Redis client not connected")
            return None

        try:
            key = self._get_key(f"scan_result:{symbol}")
            value = self.client.get(key)

            if value:
                result = json.loads(value)
                logger.debug("Scan result retrieved", symbol=symbol)
                return result

            return None

        except Exception as e:
            logger.error("Failed to get scan result", symbol=symbol, error=str(e))
            if self._try_reconnect():
                try:
                    value = self.client.get(self._get_key(f"scan_result:{symbol}"))
                    return json.loads(value) if value else None
                except Exception:
                    return None
            return None

    def set_market_data(
        self, symbol: str, data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """存储市场数据

        Args:
            symbol: 交易对符号
            data: 市场数据
            ttl: 过期时间（秒）

        Returns:
            是否存储成功
        """
        if not self.is_connected and not self._try_reconnect():
            return False

        try:
            key = self._get_key(f"market_data:{symbol}")

            # 添加时间戳
            data_with_meta = {
                **data,
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
            }

            value = json.dumps(data_with_meta, ensure_ascii=False)
            ttl_seconds = ttl or self._get_ttl("market_data")

            success = self.client.setex(key, ttl_seconds, value)

            if success:
                logger.debug("Market data stored", symbol=symbol, ttl=ttl_seconds)

            return bool(success)

        except Exception as e:
            logger.error("Failed to store market data", symbol=symbol, error=str(e))
            if self._try_reconnect():
                try:
                    key = self._get_key(f"market_data:{symbol}")
                    value = json.dumps(data_with_meta, ensure_ascii=False)
                    ttl_seconds = ttl or self._get_ttl("market_data")
                    return bool(self.client.setex(key, ttl_seconds, value))
                except Exception:
                    return False
            return False

    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据

        Args:
            symbol: 交易对符号

        Returns:
            市场数据或None
        """
        if not self.is_connected and not self._try_reconnect():
            return None

        try:
            key = self._get_key(f"market_data:{symbol}")
            value = self.client.get(key)

            if value:
                data = json.loads(value)
                logger.debug("Market data retrieved", symbol=symbol)
                return data

            return None

        except Exception as e:
            logger.error("Failed to get market data", symbol=symbol, error=str(e))
            return None

    def cache_news_events(
        self, events: List[Dict[str, Any]], ttl: Optional[int] = None
    ) -> bool:
        """缓存新闻事件

        Args:
            events: 新闻事件列表
            ttl: 过期时间（秒）

        Returns:
            是否缓存成功
        """
        if not self.is_connected or not events:
            return False

        try:
            # 使用管道批量操作
            pipe = self.client.pipeline()
            ttl_seconds = ttl or self._get_ttl("news_events")

            for event in events:
                event_id = event.get("id") or event.get("title", "")[:50]
                if not event_id:
                    continue

                key = self._get_key(f"news_event:{event_id}")

                # 添加时间戳
                event_with_meta = {**event, "cached_at": datetime.now().isoformat()}

                value = json.dumps(event_with_meta, ensure_ascii=False)
                pipe.setex(key, ttl_seconds, value)

            # 执行批量操作
            results = pipe.execute()
            success_count = sum(1 for result in results if result)

            logger.info(
                "News events cached",
                total_count=len(events),
                success_count=success_count,
                ttl=ttl_seconds,
            )

            return success_count > 0

        except Exception as e:
            logger.error("Failed to cache news events", error=str(e))
            return False

    def get_cached_news_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取缓存的新闻事件

        Args:
            limit: 最大返回数量

        Returns:
            新闻事件列表
        """
        if not self.is_connected:
            return []

        try:
            pattern = self._get_key("news_event:*")
            keys = self.client.keys(pattern)

            if not keys:
                return []

            # 限制数量
            keys = keys[:limit]

            # 批量获取
            values = self.client.mget(keys)
            events = []

            for value in values:
                if value:
                    try:
                        event = json.loads(value)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

            logger.debug("Cached news events retrieved", count=len(events))
            return events

        except Exception as e:
            logger.error("Failed to get cached news events", error=str(e))
            return []

    def set_rule_config(self, rule_name: str, config: Dict[str, Any]) -> bool:
        """存储规则配置

        Args:
            rule_name: 规则名称
            config: 规则配置

        Returns:
            是否存储成功
        """
        if not self.is_connected:
            return False

        try:
            key = self._get_key(f"rule_config:{rule_name}")

            config_with_meta = {
                **config,
                "updated_at": datetime.now().isoformat(),
                "rule_name": rule_name,
            }

            value = json.dumps(config_with_meta, ensure_ascii=False)
            success = self.client.set(key, value)  # 规则配置不设置过期时间

            if success:
                logger.debug("Rule config stored", rule_name=rule_name)

            return bool(success)

        except Exception as e:
            logger.error(
                "Failed to store rule config", rule_name=rule_name, error=str(e)
            )
            return False

    def get_rule_config(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """获取规则配置

        Args:
            rule_name: 规则名称

        Returns:
            规则配置或None
        """
        if not self.is_connected:
            return None

        try:
            key = self._get_key(f"rule_config:{rule_name}")
            value = self.client.get(key)

            if value:
                config = json.loads(value)
                logger.debug("Rule config retrieved", rule_name=rule_name)
                return config

            return None

        except Exception as e:
            logger.error("Failed to get rule config", rule_name=rule_name, error=str(e))
            return None

    def clear_expired_data(self) -> int:
        """清理过期数据

        Returns:
            清理的键数量
        """
        if not self.is_connected:
            return 0

        try:
            # 获取所有扫描器相关的键
            pattern = self._get_key("*")
            keys = self.client.keys(pattern)

            if not keys:
                return 0

            # 检查TTL并删除过期键
            expired_keys = []
            for key in keys:
                ttl = self.client.ttl(key)
                if ttl == -2:  # 键已过期但未被删除
                    expired_keys.append(key)

            if expired_keys:
                deleted_count = self.client.delete(*expired_keys)
                logger.info("Expired data cleared", count=deleted_count)
                return deleted_count

            return 0

        except Exception as e:
            logger.error("Failed to clear expired data", error=str(e))
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取Redis统计信息

        Returns:
            统计信息字典
        """
        if not self.is_connected:
            return {}

        try:
            info = self.client.info()
            pattern = self._get_key("*")
            key_count = len(self.client.keys(pattern))

            stats = {
                "connected": True,
                "key_count": key_count,
                "memory_usage": info.get("used_memory_human", "N/A"),
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }

            # 计算命中率
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            if hits + misses > 0:
                stats["hit_rate"] = hits / (hits + misses)
            else:
                stats["hit_rate"] = 0.0

            return stats

        except Exception as e:
            logger.error("Failed to get Redis stats", error=str(e))
            return {"connected": False, "error": str(e)}

    def health_check(self) -> bool:
        """健康检查

        Returns:
            是否健康
        """
        try:
            if not self.is_connected:
                return False

            # 执行ping命令
            response = self.client.ping()
            return response is True

        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False

    def get_historical_data(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取历史数据

        Args:
            symbol: 交易对符号
            hours: 获取多少小时的历史数据

        Returns:
            历史数据列表
        """
        if not self.is_connected:
            return []

        try:
            # 从历史数据集合中获取
            key = self._get_key(f"historical:{symbol}")

            # 获取指定时间范围内的数据
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            # 使用有序集合存储历史数据（按时间戳排序）
            start_score = start_time.timestamp()
            end_score = end_time.timestamp()

            data_list = self.client.zrangebyscore(
                key, start_score, end_score, withscores=False
            )

            historical_data = []
            for data_str in data_list:
                try:
                    data = json.loads(data_str)
                    historical_data.append(data)
                except json.JSONDecodeError:
                    continue

            logger.debug(
                "Historical data retrieved", symbol=symbol, count=len(historical_data)
            )
            return historical_data

        except Exception as e:
            logger.error("Failed to get historical data", symbol=symbol, error=str(e))
            return []

    def add_historical_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """添加历史数据

        Args:
            symbol: 交易对符号
            data: 数据

        Returns:
            是否添加成功
        """
        if not self.is_connected:
            return False

        try:
            key = self._get_key(f"historical:{symbol}")

            # 添加时间戳
            data_with_timestamp = {
                **data,
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
            }

            # 使用当前时间戳作为分数
            score = datetime.now().timestamp()
            value = json.dumps(data_with_timestamp, ensure_ascii=False)

            # 添加到有序集合
            success = self.client.zadd(key, {value: score})

            # 保持最近7天的数据
            cutoff_time = datetime.now() - timedelta(days=7)
            self.client.zremrangebyscore(key, 0, cutoff_time.timestamp())

            return bool(success)

        except Exception as e:
            logger.error("Failed to add historical data", symbol=symbol, error=str(e))
            return False

    def get_news_events(
        self, symbol: Optional[str] = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取新闻事件

        Args:
            symbol: 交易对符号（可选，为None时获取所有）
            hours: 获取多少小时内的新闻

        Returns:
            新闻事件列表
        """
        if not self.is_connected:
            return []

        try:
            if symbol:
                # 获取特定交易对的新闻
                pattern = self._get_key(f"news_event:*{symbol}*")
            else:
                # 获取所有新闻
                pattern = self._get_key("news_event:*")

            keys = self.client.keys(pattern)

            if not keys:
                return []

            # 批量获取
            values = self.client.mget(keys)
            events = []

            cutoff_time = datetime.now() - timedelta(hours=hours)

            for value in values:
                if value:
                    try:
                        event = json.loads(value)

                        # 检查时间范围
                        event_time_str = event.get("timestamp") or event.get(
                            "cached_at"
                        )
                        if event_time_str:
                            event_time = datetime.fromisoformat(
                                event_time_str.replace("Z", "+00:00")
                            )
                            if event_time >= cutoff_time:
                                events.append(event)
                        else:
                            events.append(event)  # 没有时间戳的也包含

                    except (json.JSONDecodeError, ValueError):
                        continue

            # 按时间排序（最新的在前）
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            logger.debug("News events retrieved", symbol=symbol, count=len(events))
            return events

        except Exception as e:
            logger.error("Failed to get news events", symbol=symbol, error=str(e))
            return []

    def add_to_triggered_list(
        self, list_name: str, symbol: str, data: Dict[str, Any]
    ) -> bool:
        """添加到触发列表

        Args:
            list_name: 列表名称（如 'three_high', 'black_horse', 'potential'）
            symbol: 交易对符号
            data: 数据

        Returns:
            是否添加成功
        """
        if not self.is_connected:
            return False

        try:
            key = self._get_key(f"triggered:{list_name}")

            # 添加时间戳和符号
            data_with_meta = {
                **data,
                "symbol": symbol,
                "triggered_at": datetime.now().isoformat(),
            }

            # 使用当前时间戳作为分数，保持时间顺序
            score = datetime.now().timestamp()
            value = json.dumps(data_with_meta, ensure_ascii=False)

            # 添加到有序集合
            success = self.client.zadd(key, {value: score})

            # 保持最近1000条记录
            self.client.zremrangebyrank(key, 0, -1001)

            if success:
                logger.debug(
                    "Added to triggered list", list_name=list_name, symbol=symbol
                )

            return bool(success)

        except Exception as e:
            logger.error(
                "Failed to add to triggered list",
                list_name=list_name,
                symbol=symbol,
                error=str(e),
            )
            return False

    def get_triggered_list(
        self, list_name: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取触发列表

        Args:
            list_name: 列表名称
            limit: 最大返回数量

        Returns:
            触发记录列表
        """
        if not self.is_connected:
            return []

        try:
            key = self._get_key(f"triggered:{list_name}")

            # 获取最新的记录（按分数倒序）
            data_list = self.client.zrevrange(key, 0, limit - 1, withscores=False)

            triggered_data = []
            for data_str in data_list:
                try:
                    data = json.loads(data_str)
                    triggered_data.append(data)
                except json.JSONDecodeError:
                    continue

            logger.debug(
                "Triggered list retrieved",
                list_name=list_name,
                count=len(triggered_data),
            )
            return triggered_data

        except Exception as e:
            logger.error(
                "Failed to get triggered list", list_name=list_name, error=str(e)
            )
            return []

    def batch_set(self, data_dict: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """批量设置数据

        Args:
            data_dict: 键值对字典
            ttl: 过期时间（秒）

        Returns:
            成功设置的数量
        """
        if not self.is_connected or not data_dict:
            return 0

        try:
            pipe = self.client.pipeline()
            ttl_seconds = ttl or self.default_ttl

            for key, value in data_dict.items():
                full_key = self._get_key(key)

                if isinstance(value, (dict, list)):
                    json_value = json.dumps(value, ensure_ascii=False)
                else:
                    json_value = str(value)

                if ttl_seconds > 0:
                    pipe.setex(full_key, ttl_seconds, json_value)
                else:
                    pipe.set(full_key, json_value)

            results = pipe.execute()
            success_count = sum(1 for result in results if result)

            logger.debug(
                "Batch set completed", total=len(data_dict), success=success_count
            )
            return success_count

        except Exception as e:
            logger.error("Failed to batch set data", error=str(e))
            return 0

    def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取数据

        Args:
            keys: 键列表

        Returns:
            键值对字典
        """
        if not self.is_connected or not keys:
            return {}

        try:
            full_keys = [self._get_key(key) for key in keys]
            values = self.client.mget(full_keys)

            result = {}
            for i, value in enumerate(values):
                if value:
                    try:
                        # 尝试解析JSON
                        result[keys[i]] = json.loads(value)
                    except json.JSONDecodeError:
                        # 如果不是JSON，直接返回字符串
                        result[keys[i]] = value

            logger.debug("Batch get completed", requested=len(keys), found=len(result))
            return result

        except Exception as e:
            logger.error("Failed to batch get data", error=str(e))
            return {}

    def ping(self) -> bool:
        """检查Redis连接状态

        Returns:
            连接是否正常
        """
        if not self.is_connected or not self.client:
            return False

        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            return False

    def get(self, key: str) -> Optional[str]:
        """获取Redis中的值

        Args:
            key: 键名

        Returns:
            值或None
        """
        if not self.is_connected or not self.client:
            return None

        try:
            full_key = self._get_key(key)
            value = self.client.get(full_key)
            return value
        except Exception as e:
            logger.error("Redis get failed", key=key, error=str(e))
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """设置Redis中的值

        Args:
            key: 键名
            value: 值
            ex: 过期时间（秒）

        Returns:
            是否设置成功
        """
        if not self.is_connected or not self.client:
            return False

        try:
            full_key = self._get_key(key)
            return bool(self.client.set(full_key, value, ex=ex))
        except Exception as e:
            logger.error("Redis set failed", key=key, error=str(e))
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
