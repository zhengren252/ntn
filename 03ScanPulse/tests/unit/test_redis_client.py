# Redis客户端单元测试
# 测试Redis缓存管理和数据存储功能

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.communication.redis_client import RedisClient


class TestRedisClient:
    """Redis客户端测试类"""

    @pytest.fixture
    def redis_config(self):
        """Redis配置"""
        return {
            "host": "localhost",
            "port": 6379,
            "db": 15,
            "password": None,
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "max_connections": 10,
            "key_prefix": "scanner",
            "default_ttl": 3600,
        }

    @pytest.fixture
    def mock_redis(self):
        """模拟Redis连接"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.ttl.return_value = 3600
        mock_redis.keys.return_value = []
        mock_redis.info.return_value = {"used_memory_human": "1M"}
        mock_redis.dbsize.return_value = 0
        return mock_redis

    @pytest.fixture
    def redis_client(self, redis_config):
        """Redis客户端实例"""
        return RedisClient(redis_config)

    @pytest.fixture
    def sample_scan_result(self):
        """示例扫描结果"""
        return {
            "symbol": "BTCUSDT",
            "timestamp": "2024-01-01T12:00:00Z",
            "triggered": True,
            "score": 0.85,
            "details": {
                "volatility_score": 0.9,
                "volume_score": 0.8,
                "correlation_score": 0.85,
            },
        }

    @pytest.fixture
    def sample_market_data(self):
        """示例市场数据"""
        return {
            "symbol": "BTCUSDT",
            "price": 45000.0,
            "volume": 1500000.0,
            "change_24h": 0.05,
            "high_24h": 46000.0,
            "low_24h": 44000.0,
            "market_cap": 850000000000,
            "timestamp": "2024-01-01T12:00:00Z",
        }

    @pytest.fixture
    def sample_news_event(self):
        """示例新闻事件"""
        return {
            "id": "news_001",
            "title": "Bitcoin reaches new milestone",
            "content": "Bitcoin has reached a significant milestone...",
            "sentiment": 0.8,
            "relevance": 0.9,
            "source": "CryptoNews",
            "timestamp": "2024-01-01T10:00:00Z",
            "symbols": ["BTCUSDT", "ETHUSDT"],
        }

    @pytest.mark.unit
    def test_client_initialization(self, redis_config):
        """测试客户端初始化"""
        client = RedisClient(redis_config)

        assert client.host == "localhost"
        assert client.port == 6379
        assert client.db == 15
        assert client.key_prefix == "scanner"
        assert client.default_ttl == 3600
        assert client.redis is None
        assert client.is_connected() is False

    @pytest.mark.unit
    @patch("redis.Redis")
    def test_connect_success(self, mock_redis_class, redis_client, mock_redis):
        """测试成功连接"""
        mock_redis_class.return_value = mock_redis

        result = redis_client.connect()

        assert result is True
        assert redis_client.is_connected() is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.unit
    @patch("redis.Redis")
    def test_connect_failure(self, mock_redis_class, redis_client):
        """测试连接失败"""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_redis

        result = redis_client.connect()

        assert result is False
        assert redis_client.is_connected() is False

    @pytest.mark.unit
    def test_disconnect(self, redis_client, mock_redis):
        """测试断开连接"""
        redis_client.redis = mock_redis

        redis_client.disconnect()

        assert redis_client.redis is None
        assert redis_client.is_connected() is False

    @pytest.mark.unit
    def test_generate_key(self, redis_client):
        """测试键名生成"""
        key = redis_client._generate_key("test", "BTCUSDT")
        assert key == "scanner:test:BTCUSDT"

        key_with_suffix = redis_client._generate_key("data", "ETHUSDT", "2024-01-01")
        assert key_with_suffix == "scanner:data:ETHUSDT:2024-01-01"

    @pytest.mark.unit
    def test_set_scan_result(self, redis_client, mock_redis, sample_scan_result):
        """测试设置扫描结果"""
        redis_client.redis = mock_redis

        result = redis_client.set_scan_result("BTCUSDT", sample_scan_result)

        assert result is True
        mock_redis.set.assert_called_once()

        # 验证调用参数
        call_args = mock_redis.set.call_args
        key = call_args[0][0]
        value = call_args[0][1]

        assert "scanner:scan_results:BTCUSDT" in key
        assert json.loads(value) == sample_scan_result

    @pytest.mark.unit
    def test_get_scan_result(self, redis_client, mock_redis, sample_scan_result):
        """测试获取扫描结果"""
        redis_client.redis = mock_redis
        mock_redis.get.return_value = json.dumps(sample_scan_result)

        result = redis_client.get_scan_result("BTCUSDT")

        assert result == sample_scan_result
        mock_redis.get.assert_called_once()

    @pytest.mark.unit
    def test_get_scan_result_not_found(self, redis_client, mock_redis):
        """测试获取不存在的扫描结果"""
        redis_client.redis = mock_redis
        mock_redis.get.return_value = None

        result = redis_client.get_scan_result("NONEXISTENT")

        assert result is None

    @pytest.mark.unit
    def test_set_market_data(self, redis_client, mock_redis, sample_market_data):
        """测试设置市场数据"""
        redis_client.redis = mock_redis

        result = redis_client.set_market_data("BTCUSDT", sample_market_data)

        assert result is True
        mock_redis.set.assert_called_once()

    @pytest.mark.unit
    def test_get_market_data(self, redis_client, mock_redis, sample_market_data):
        """测试获取市场数据"""
        redis_client.redis = mock_redis
        mock_redis.get.return_value = json.dumps(sample_market_data)

        result = redis_client.get_market_data("BTCUSDT")

        assert result == sample_market_data

    @pytest.mark.unit
    def test_cache_news_event(self, redis_client, mock_redis, sample_news_event):
        """测试缓存新闻事件"""
        redis_client.redis = mock_redis

        result = redis_client.cache_news_event(sample_news_event)

        assert result is True
        mock_redis.set.assert_called_once()

        # 验证TTL设置
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 86400  # 24小时

    @pytest.mark.unit
    def test_get_cached_news(self, redis_client, mock_redis, sample_news_event):
        """测试获取缓存的新闻"""
        redis_client.redis = mock_redis
        mock_redis.keys.return_value = ["scanner:news:news_001"]
        mock_redis.get.return_value = json.dumps(sample_news_event)

        result = redis_client.get_cached_news(["BTCUSDT"])

        assert len(result) == 1
        assert result[0] == sample_news_event

    @pytest.mark.unit
    def test_store_rule_config(self, redis_client, mock_redis):
        """测试存储规则配置"""
        redis_client.redis = mock_redis

        config = {"enabled": True, "threshold": 0.8, "parameters": {"window": 300}}

        result = redis_client.store_rule_config("three_high", config)

        assert result is True
        mock_redis.set.assert_called_once()

    @pytest.mark.unit
    def test_get_rule_config(self, redis_client, mock_redis):
        """测试获取规则配置"""
        redis_client.redis = mock_redis

        config = {"enabled": True, "threshold": 0.8}
        mock_redis.get.return_value = json.dumps(config)

        result = redis_client.get_rule_config("three_high")

        assert result == config

    @pytest.mark.unit
    def test_cleanup_expired_data(self, redis_client, mock_redis):
        """测试清理过期数据"""
        redis_client.redis = mock_redis

        # 模拟过期的键
        expired_keys = [
            "scanner:scan_results:BTCUSDT:2024-01-01",
            "scanner:market_data:ETHUSDT:2024-01-01",
        ]
        mock_redis.keys.return_value = expired_keys
        mock_redis.ttl.return_value = -1  # 已过期
        mock_redis.delete.return_value = len(expired_keys)

        deleted_count = redis_client.cleanup_expired_data()

        assert deleted_count == 2
        assert mock_redis.delete.call_count == 1

    @pytest.mark.unit
    def test_get_stats(self, redis_client, mock_redis):
        """测试获取统计信息"""
        redis_client.redis = mock_redis
        mock_redis.dbsize.return_value = 100
        mock_redis.info.return_value = {"used_memory_human": "5M"}

        stats = redis_client.get_stats()

        assert stats["total_keys"] == 100
        assert stats["memory_usage"] == "5M"
        assert "uptime" in stats

    @pytest.mark.unit
    def test_health_check_healthy(self, redis_client, mock_redis):
        """测试健康检查 - 健康状态"""
        redis_client.redis = mock_redis
        mock_redis.ping.return_value = True

        with patch("time.time", side_effect=[1000.0, 1000.001]):
            health = redis_client.health_check()

        assert health["status"] == "healthy"
        assert health["latency"] == 1.0  # 1ms
        assert health["connected"] is True

    @pytest.mark.unit
    def test_health_check_unhealthy(self, redis_client, mock_redis):
        """测试健康检查 - 不健康状态"""
        redis_client.redis = mock_redis
        mock_redis.ping.side_effect = Exception("Connection lost")

        health = redis_client.health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health
        assert health["connected"] is False

    @pytest.mark.unit
    def test_get_historical_data(self, redis_client, mock_redis):
        """测试获取历史数据"""
        redis_client.redis = mock_redis

        # 模拟历史数据键
        historical_keys = [
            "scanner:market_data:BTCUSDT:2024-01-01T11:55:00",
            "scanner:market_data:BTCUSDT:2024-01-01T12:00:00",
        ]
        mock_redis.keys.return_value = historical_keys

        # 模拟历史数据值
        historical_values = [
            json.dumps(
                {"price": 44000, "volume": 1400000, "timestamp": "2024-01-01T11:55:00Z"}
            ),
            json.dumps(
                {"price": 45000, "volume": 1500000, "timestamp": "2024-01-01T12:00:00Z"}
            ),
        ]
        mock_redis.mget.return_value = historical_values

        result = redis_client.get_historical_data("BTCUSDT", 300)  # 5分钟窗口

        assert len(result) == 2
        assert result[0]["price"] == 44000
        assert result[1]["price"] == 45000

    @pytest.mark.unit
    def test_batch_operations(self, redis_client, mock_redis):
        """测试批量操作"""
        redis_client.redis = mock_redis

        # 批量设置数据
        data_batch = {
            "BTCUSDT": {"price": 45000, "volume": 1500000},
            "ETHUSDT": {"price": 3000, "volume": 1200000},
        }

        result = redis_client.batch_set_market_data(data_batch)

        assert result is True
        # 验证pipeline使用
        mock_redis.pipeline.assert_called_once()

    @pytest.mark.unit
    def test_error_handling(self, redis_client, mock_redis):
        """测试错误处理"""
        redis_client.redis = mock_redis
        mock_redis.set.side_effect = Exception("Redis error")

        result = redis_client.set_scan_result("BTCUSDT", {"test": "data"})

        assert result is False

    @pytest.mark.unit
    def test_ttl_management(self, redis_client, mock_redis):
        """测试TTL管理"""
        redis_client.redis = mock_redis

        # 测试自定义TTL
        redis_client.set_scan_result("BTCUSDT", {"test": "data"}, ttl=1800)

        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 1800

    @pytest.mark.unit
    def test_key_pattern_matching(self, redis_client, mock_redis):
        """测试键模式匹配"""
        redis_client.redis = mock_redis

        # 模拟匹配的键
        matching_keys = [
            "scanner:scan_results:BTCUSDT:2024-01-01",
            "scanner:scan_results:ETHUSDT:2024-01-01",
        ]
        mock_redis.keys.return_value = matching_keys

        keys = redis_client.get_keys_by_pattern("scan_results:*:2024-01-01")

        assert len(keys) == 2
        assert all("scan_results" in key for key in keys)

    @pytest.mark.unit
    def test_connection_retry(self, redis_client, mock_redis):
        """测试连接重试机制"""
        redis_client.redis = mock_redis

        # 第一次失败，第二次成功
        mock_redis.ping.side_effect = [Exception("Timeout"), True]

        with patch.object(redis_client, "connect", return_value=True):
            result = redis_client._ensure_connection()

        assert result is True

    @pytest.mark.integration
    def test_full_workflow(
        self, redis_client, mock_redis, sample_scan_result, sample_market_data
    ):
        """测试完整工作流"""
        redis_client.redis = mock_redis

        # 1. 存储市场数据
        assert redis_client.set_market_data("BTCUSDT", sample_market_data) is True

        # 2. 存储扫描结果
        assert redis_client.set_scan_result("BTCUSDT", sample_scan_result) is True

        # 3. 获取数据
        mock_redis.get.return_value = json.dumps(sample_scan_result)
        result = redis_client.get_scan_result("BTCUSDT")
        assert result == sample_scan_result

        # 4. 健康检查
        mock_redis.ping.return_value = True
        health = redis_client.health_check()
        assert health["status"] == "healthy"

        # 5. 清理数据
        mock_redis.keys.return_value = ["scanner:test:key"]
        mock_redis.delete.return_value = 1
        deleted = redis_client.cleanup_expired_data()
        assert deleted >= 0

    @pytest.mark.unit
    def test_json_serialization_edge_cases(self, redis_client, mock_redis):
        """测试JSON序列化边界情况"""
        redis_client.redis = mock_redis

        # 测试包含特殊字符的数据
        special_data = {
            "symbol": "BTC/USDT",
            "description": 'Bitcoin with "quotes" and \n newlines',
            "unicode": "测试数据",
            "numbers": [1, 2.5, -3],
        }

        result = redis_client.set_scan_result("SPECIAL", special_data)
        assert result is True

        # 验证序列化正确
        call_args = mock_redis.set.call_args
        serialized_data = call_args[0][1]
        deserialized_data = json.loads(serialized_data)
        assert deserialized_data == special_data
