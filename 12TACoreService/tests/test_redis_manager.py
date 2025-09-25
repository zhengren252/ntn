"""Tests for Redis cache manager."""

import pytest
import json
import pickle
from unittest.mock import Mock, patch, AsyncMock
from tacoreservice.core.redis_manager import RedisManager
from tacoreservice.config import Settings


@pytest.mark.unit
class TestRedisManager:
    """Test RedisManager functionality."""

    @pytest.fixture
    def redis_manager(self, test_settings, mock_redis):
        """Create RedisManager instance with mocked Redis."""
        with patch("tacoreservice.core.redis_manager.redis.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis
            with patch(
                "tacoreservice.core.redis_manager.get_settings",
                return_value=test_settings,
            ):
                manager = RedisManager()
                return manager, mock_redis

    def test_initialization(self, test_settings, mock_redis):
        """测试Redis管理器初始化"""
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            manager = RedisManager()
            manager.client = mock_redis
            manager.connected = True

            assert manager.settings is not None
            assert manager.key_prefix == "tacoreservice:"
            assert isinstance(manager.default_ttl, dict)
            assert manager.default_ttl["request"] == 3600
            assert manager.default_ttl["market_data"] == 300
            assert manager.default_ttl["analysis"] == 1800

    def test_test_connection_success(self, test_settings, mock_redis):
        """测试成功的Redis连接测试"""
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.test_connection()

            assert result is True
            mock_redis.ping.assert_called()

    def test_test_connection_failure(self, test_settings, mock_redis):
        """测试失败的Redis连接测试"""
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = False

            result = redis_manager.test_connection()

            assert result is False

    def test_set_get_string(self, test_settings, mock_redis):
        """测试设置和获取字符串值"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = b'"test_value"'
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            # 设置值
            result = redis_manager.set("request", "test_key", "test_value")
            assert result is True

            # 获取值
            value = redis_manager.get("request", "test_key")
            assert value == "test_value"

            # 验证Redis调用
            mock_redis.setex.assert_called_with(
                "tacoreservice:request:test_key",
                3600,  # TTL
                json.dumps("test_value", ensure_ascii=False).encode("utf-8"),
            )
            mock_redis.get.assert_called_with("tacoreservice:request:test_key")

    def test_set_get_dict(self, test_settings, mock_redis):
        """测试设置和获取字典值"""
        test_dict = {"key1": "value1", "key2": 123}
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = json.dumps(test_dict).encode("utf-8")
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            # 设置值
            result = redis_manager.set("market_data", "test_dict", test_dict)
            assert result == True

            # 获取值
            value = redis_manager.get("market_data", "test_dict")
            assert value == test_dict

    def test_set_get_pickled(self, test_settings, mock_redis):
        """测试设置和获取需要pickle的复杂对象"""
        import datetime

        test_obj = datetime.datetime.now()
        pickled_data = pickle.dumps(test_obj)

        mock_redis.setex.return_value = True
        mock_redis.get.return_value = pickled_data
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            # 设置值
            result = redis_manager.set("analysis", "test_obj", test_obj)
            assert result == True

            # 获取值
            value = redis_manager.get("analysis", "test_obj")
            assert isinstance(value, datetime.datetime)

    def test_get_nonexistent_key(self, test_settings, mock_redis):
        """测试获取不存在的键"""
        mock_redis.get.return_value = None
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            value = redis_manager.get("request", "nonexistent_key")
            assert value is None

    def test_delete_key(self, test_settings, mock_redis):
        """测试删除键"""
        mock_redis.delete.return_value = 1
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.delete("request", "test_key")
            assert result == True

            mock_redis.delete.assert_called_with("tacoreservice:request:test_key")

    def test_exists(self, test_settings, mock_redis):
        """测试检查键是否存在"""
        mock_redis.exists.return_value = 1
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.exists("market_data", "test_key")
            assert result == True

            # market_data键类型映射到tacoreservice:market:前缀
            mock_redis.exists.assert_called_with("tacoreservice:market:test_key")

    def test_expire(self, test_settings, mock_redis):
        """测试设置键过期时间"""
        mock_redis.expire.return_value = True
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.expire("session", "test_key", 1800)
            assert result == True

            mock_redis.expire.assert_called_with("tacoreservice:session:test_key", 1800)

    def test_clear_pattern(self, test_settings, mock_redis):
        """测试按模式清除键"""
        mock_redis.scan_iter.return_value = [
            "tacoreservice:market:AAPL",
            "tacoreservice:market:GOOGL",
        ]
        mock_redis.delete.return_value = 2
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.clear_pattern("market_data", "*")
            assert result == 2

            mock_redis.scan_iter.assert_called_with(match="tacoreservice:market:*")
            mock_redis.delete.assert_called()

    def test_get_stats(self, test_settings, mock_redis):
        """测试获取缓存统计信息"""
        mock_redis.info.return_value = {
            "used_memory": 1024000,
            "keyspace_hits": 100,
            "keyspace_misses": 10,
        }
        mock_redis.dbsize.return_value = 50
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            stats = redis_manager.get_stats()

            assert stats["memory_usage"] == 1024000
            assert stats["hit_rate"] == 0.909  # 100/(100+10)
            assert stats["total_keys"] == 50

    def test_cache_market_data(self, test_settings, mock_redis):
        """测试缓存市场数据"""
        market_data = {
            "AAPL": {"price": 150.0, "volume": 1000000},
            "GOOGL": {"price": 2500.0, "volume": 500000},
        }

        mock_redis.setex.return_value = True
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.cache_market_data("stocks", market_data)
            assert result == True

            # 验证使用了正确的TTL
            mock_redis.setex.assert_called_once()
            args = mock_redis.setex.call_args[0]
            assert args[0] == "tacoreservice:market:stocks"
            assert args[1] == 300  # market_data的默认TTL

    def test_get_cached_market_data(self, test_settings, mock_redis):
        """测试获取缓存的市场数据"""
        market_data = {"AAPL": {"price": 150.0, "volume": 1000000}}

        mock_redis.get.return_value = json.dumps(market_data).encode("utf-8")
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.get_cached_market_data("stocks")
            assert result == market_data

            mock_redis.get.assert_called_with("tacoreservice:market:stocks")

    def test_cache_analysis_result(self, test_settings, mock_redis):
        """测试缓存分析结果"""
        analysis_result = {
            "symbol": "AAPL",
            "sma": 150.0,
            "rsi": 65.0,
            "recommendation": "BUY",
        }

        mock_redis.setex.return_value = True
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.cache_analysis_result("AAPL", analysis_result)
            assert result == True

            # 验证使用了正确的TTL
            mock_redis.setex.assert_called_once()
            args = mock_redis.setex.call_args[0]
            assert args[0] == "tacoreservice:analysis:AAPL"
            assert args[1] == 1800  # analysis的默认TTL

    def test_get_cached_analysis(self, test_settings, mock_redis):
        """测试获取缓存的分析结果"""
        analysis_result = {"symbol": "AAPL", "sma": 150.0, "rsi": 65.0}

        mock_redis.get.return_value = json.dumps(analysis_result).encode("utf-8")
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            result = redis_manager.get_cached_analysis("AAPL")
            assert result == analysis_result

            mock_redis.get.assert_called_with("tacoreservice:analysis:AAPL")

    def test_close(self, test_settings, mock_redis):
        """测试关闭Redis连接"""
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            redis_manager.close()

            mock_redis.close.assert_called_once()
            assert redis_manager.connected == False

    def test_error_handling(self, test_settings, mock_redis):
        """测试错误处理"""
        mock_redis.get.side_effect = Exception("Redis error")
        mock_redis.ping.return_value = True

        with patch(
            "tacoreservice.core.redis_manager.get_settings", return_value=test_settings
        ):
            redis_manager = RedisManager()
            redis_manager.client = mock_redis
            redis_manager.connected = True

            # 获取操作应该返回None而不是抛出异常
            result = redis_manager.get("request", "test_key")
            assert result is None

            # 设置操作应该返回False而不是抛出异常
            mock_redis.setex.side_effect = Exception("Redis error")
            result = redis_manager.set("request", "test_key", "test_value")
            assert result == False
