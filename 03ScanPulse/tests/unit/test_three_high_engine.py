# 三高规则引擎单元测试
# 测试高波动、高流动性、高相关性筛选逻辑

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.communication.redis_client import RedisClient


class TestThreeHighEngine:
    """三高规则引擎测试类"""

    @pytest.fixture
    def engine_config(self):
        """引擎配置"""
        return {
            "enabled": True,
            "volatility_threshold": 0.05,  # 5%波动率阈值
            "volume_threshold": 1000000,  # 100万成交量阈值
            "correlation_threshold": 0.7,  # 70%相关性阈值
            "time_window": 300,  # 5分钟时间窗口
            "min_data_points": 10,  # 最少数据点
            "weight_volatility": 0.4,  # 波动性权重
            "weight_volume": 0.3,  # 流动性权重
            "weight_correlation": 0.3,  # 相关性权重
        }

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        redis_client = Mock(spec=RedisClient)
        redis_client.get_market_data.return_value = None
        redis_client.set_market_data.return_value = True
        redis_client.get_historical_data.return_value = []
        return redis_client

    @pytest.fixture
    def three_high_engine(self, engine_config, mock_redis_client):
        """三高规则引擎实例"""
        return ThreeHighEngine(engine_config, mock_redis_client)

    @pytest.fixture
    def high_volatility_data(self):
        """高波动性数据"""
        return {
            "symbol": "BTCUSDT",
            "price": 45000.0,
            "volume": 1500000.0,
            "change_24h": 0.08,  # 8%变化，超过5%阈值
            "high_24h": 46000.0,
            "low_24h": 44000.0,
            "market_cap": 850000000000,
            "timestamp": "2024-01-01T12:00:00Z",
            "technical_indicators": {
                "rsi": 75.0,
                "volatility": 0.09,  # 9%波动率
                "volume_sma": 1200000.0,
            },
        }

    @pytest.fixture
    def high_volume_data(self):
        """高流动性数据"""
        return {
            "symbol": "ETHUSDT",
            "price": 3000.0,
            "volume": 2500000.0,  # 超过100万阈值
            "change_24h": 0.03,
            "high_24h": 3100.0,
            "low_24h": 2900.0,
            "market_cap": 360000000000,
            "timestamp": "2024-01-01T12:00:00Z",
            "technical_indicators": {
                "rsi": 65.0,
                "volatility": 0.04,
                "volume_sma": 1800000.0,
                "volume_ratio": 1.39,  # 当前成交量/平均成交量
            },
        }

    @pytest.fixture
    def low_quality_data(self):
        """低质量数据（不满足三高条件）"""
        return {
            "symbol": "ADAUSDT",
            "price": 0.5,
            "volume": 500000.0,  # 低于100万阈值
            "change_24h": 0.02,  # 低于5%阈值
            "high_24h": 0.51,
            "low_24h": 0.49,
            "market_cap": 15000000000,
            "timestamp": "2024-01-01T12:00:00Z",
            "technical_indicators": {
                "rsi": 50.0,
                "volatility": 0.03,  # 低于5%阈值
                "volume_sma": 600000.0,
            },
        }

    @pytest.mark.unit
    async def test_engine_initialization(self, engine_config, mock_redis_client):
        """测试引擎初始化"""
        engine = ThreeHighEngine(engine_config, mock_redis_client)

        assert engine.config == engine_config
        assert engine.redis_client == mock_redis_client
        assert engine.volatility_threshold == 0.05
        assert engine.volume_threshold == 1000000
        assert engine.correlation_threshold == 0.7

    @pytest.mark.unit
    async def test_calculate_volatility_score(
        self, three_high_engine, high_volatility_data
    ):
        """测试波动性评分计算"""
        score = three_high_engine._calculate_volatility_score(high_volatility_data)

        # 8%变化率应该得到高分
        assert score > 0.8
        assert 0 <= score <= 1

    @pytest.mark.unit
    async def test_calculate_volume_score(self, three_high_engine, high_volume_data):
        """测试流动性评分计算"""
        score = three_high_engine._calculate_volume_score(high_volume_data)

        # 250万成交量应该得到高分
        assert score > 0.8
        assert 0 <= score <= 1

    @pytest.mark.unit
    async def test_calculate_correlation_score(self, three_high_engine):
        """测试相关性评分计算"""
        # 模拟历史数据
        historical_data = [
            {"price": 44000, "timestamp": "2024-01-01T11:55:00Z"},
            {"price": 44500, "timestamp": "2024-01-01T11:56:00Z"},
            {"price": 45000, "timestamp": "2024-01-01T11:57:00Z"},
            {"price": 45500, "timestamp": "2024-01-01T11:58:00Z"},
            {"price": 46000, "timestamp": "2024-01-01T11:59:00Z"},
        ]

        with patch.object(
            three_high_engine, "_get_market_correlation", return_value=0.85
        ):
            score = await three_high_engine._calculate_correlation_score(
                "BTCUSDT", historical_data
            )

        # 85%相关性应该得到高分
        assert score > 0.8
        assert 0 <= score <= 1

    @pytest.mark.unit
    async def test_analyze_high_quality_symbol(
        self, three_high_engine, high_volatility_data
    ):
        """测试分析高质量交易对"""
        # 模拟获取历史数据
        three_high_engine.redis_client.get_historical_data.return_value = [
            {"price": 44000, "volume": 1400000, "timestamp": "2024-01-01T11:55:00Z"},
            {"price": 45000, "volume": 1500000, "timestamp": "2024-01-01T12:00:00Z"},
        ]

        with patch.object(
            three_high_engine, "_get_market_correlation", return_value=0.8
        ):
            result = await three_high_engine.analyze("BTCUSDT", high_volatility_data)

        assert result["triggered"] is True
        assert result["score"] > 0.7
        assert "volatility_score" in result["details"]
        assert "volume_score" in result["details"]
        assert "correlation_score" in result["details"]
        assert result["timestamp"] is not None

    @pytest.mark.unit
    async def test_analyze_low_quality_symbol(
        self, three_high_engine, low_quality_data
    ):
        """测试分析低质量交易对"""
        # 模拟获取历史数据
        three_high_engine.redis_client.get_historical_data.return_value = [
            {"price": 0.49, "volume": 450000, "timestamp": "2024-01-01T11:55:00Z"},
            {"price": 0.5, "volume": 500000, "timestamp": "2024-01-01T12:00:00Z"},
        ]

        with patch.object(
            three_high_engine, "_get_market_correlation", return_value=0.3
        ):
            result = await three_high_engine.analyze("ADAUSDT", low_quality_data)

        assert result["triggered"] is False
        assert result["score"] < 0.5
        assert len(result["reasons"]) > 0

    @pytest.mark.unit
    async def test_analyze_missing_data(self, three_high_engine):
        """测试分析缺失数据"""
        incomplete_data = {
            "symbol": "TESTUSDT",
            "price": 100.0
            # 缺少volume等关键数据
        }

        result = await three_high_engine.analyze("TESTUSDT", incomplete_data)

        assert result["triggered"] is False
        assert "Missing required data" in result["reasons"]

    @pytest.mark.unit
    def test_calculate_volatility_score_edge_cases(self, three_high_engine):
        """测试波动性评分边界情况"""
        # 零变化
        zero_change_data = {
            "change_24h": 0.0,
            "technical_indicators": {"volatility": 0.0},
        }
        score = three_high_engine._calculate_volatility_score(zero_change_data)
        assert score == 0.0

        # 极高变化
        high_change_data = {
            "change_24h": 0.5,
            "technical_indicators": {"volatility": 0.6},
        }
        score = three_high_engine._calculate_volatility_score(high_change_data)
        assert score == 1.0

        # 负变化
        negative_change_data = {
            "change_24h": -0.1,
            "technical_indicators": {"volatility": 0.1},
        }
        score = three_high_engine._calculate_volatility_score(negative_change_data)
        assert score > 0.8  # 绝对值计算

    @pytest.mark.unit
    def test_calculate_volume_score_edge_cases(self, three_high_engine):
        """测试流动性评分边界情况"""
        # 零成交量
        zero_volume_data = {
            "volume": 0.0,
            "technical_indicators": {"volume_sma": 1000000},
        }
        score = three_high_engine._calculate_volume_score(zero_volume_data)
        assert score == 0.0

        # 极高成交量
        high_volume_data = {
            "volume": 10000000.0,
            "technical_indicators": {"volume_sma": 1000000},
        }
        score = three_high_engine._calculate_volume_score(high_volume_data)
        assert score == 1.0

    @pytest.mark.unit
    async def test_get_market_correlation(self, three_high_engine):
        """测试市场相关性计算"""
        symbol = "BTCUSDT"

        # 模拟市场数据
        market_data = {
            "BTCUSDT": [45000, 45500, 46000, 45800, 46200],
            "ETHUSDT": [3000, 3050, 3100, 3080, 3120],
            "BNBUSDT": [400, 405, 410, 408, 412],
        }

        with patch.object(
            three_high_engine, "_get_market_prices", return_value=market_data
        ):
            correlation = await three_high_engine._get_market_correlation(symbol)

        assert 0 <= correlation <= 1

    @pytest.mark.unit
    async def test_store_analysis_result(self, three_high_engine):
        """测试存储分析结果"""
        result = {
            "triggered": True,
            "score": 0.85,
            "details": {
                "volatility_score": 0.9,
                "volume_score": 0.8,
                "correlation_score": 0.85,
            },
        }

        await three_high_engine._store_analysis_result("BTCUSDT", result)

        # 验证Redis存储调用
        three_high_engine.redis_client.set_scan_result.assert_called_once()

    @pytest.mark.unit
    async def test_get_cached_result(self, three_high_engine):
        """测试获取缓存结果"""
        cached_result = {
            "triggered": True,
            "score": 0.8,
            "timestamp": "2024-01-01T12:00:00Z",
        }

        three_high_engine.redis_client.get_scan_result.return_value = cached_result

        result = await three_high_engine._get_cached_result("BTCUSDT")

        assert result == cached_result
        three_high_engine.redis_client.get_scan_result.assert_called_once_with(
            "BTCUSDT"
        )

    @pytest.mark.unit
    async def test_is_cache_valid(self, three_high_engine):
        """测试缓存有效性检查"""
        # 有效缓存（5分钟内）
        recent_time = datetime.now(timezone.utc).isoformat()
        assert three_high_engine._is_cache_valid(recent_time) is True

        # 无效缓存（超过5分钟）
        old_time = "2024-01-01T10:00:00Z"
        assert three_high_engine._is_cache_valid(old_time) is False

    @pytest.mark.unit
    async def test_calculate_composite_score(self, three_high_engine):
        """测试综合评分计算"""
        volatility_score = 0.9
        volume_score = 0.8
        correlation_score = 0.7

        composite_score = three_high_engine._calculate_composite_score(
            volatility_score, volume_score, correlation_score
        )

        # 验证加权平均计算
        expected_score = (0.9 * 0.4) + (0.8 * 0.3) + (0.7 * 0.3)
        assert abs(composite_score - expected_score) < 0.001
        assert 0 <= composite_score <= 1

    @pytest.mark.unit
    async def test_error_handling(self, three_high_engine, high_volatility_data):
        """测试错误处理"""
        # 模拟Redis错误
        three_high_engine.redis_client.get_historical_data.side_effect = Exception(
            "Redis error"
        )

        result = await three_high_engine.analyze("BTCUSDT", high_volatility_data)

        assert result["triggered"] is False
        assert "error" in result
        assert "Redis error" in result["error"]

    @pytest.mark.unit
    async def test_performance_metrics(self, three_high_engine, high_volatility_data):
        """测试性能指标"""
        import time

        start_time = time.time()

        # 模拟快速响应
        three_high_engine.redis_client.get_historical_data.return_value = []

        with patch.object(
            three_high_engine, "_get_market_correlation", return_value=0.8
        ):
            result = await three_high_engine.analyze("BTCUSDT", high_volatility_data)

        end_time = time.time()
        execution_time = end_time - start_time

        # 验证执行时间合理（应该在1秒内完成）
        assert execution_time < 1.0
        assert "execution_time" in result

    @pytest.mark.integration
    async def test_full_analysis_workflow(
        self, three_high_engine, high_volatility_data
    ):
        """测试完整分析工作流"""
        # 模拟完整的分析流程
        three_high_engine.redis_client.get_historical_data.return_value = [
            {"price": 44000, "volume": 1400000, "timestamp": "2024-01-01T11:55:00Z"},
            {"price": 44500, "volume": 1450000, "timestamp": "2024-01-01T11:56:00Z"},
            {"price": 45000, "volume": 1500000, "timestamp": "2024-01-01T11:57:00Z"},
        ]

        with patch.object(
            three_high_engine, "_get_market_correlation", return_value=0.85
        ):
            result = await three_high_engine.analyze("BTCUSDT", high_volatility_data)

        # 验证完整结果结构
        assert "triggered" in result
        assert "score" in result
        assert "details" in result
        assert "timestamp" in result
        assert "execution_time" in result

        if result["triggered"]:
            assert result["score"] > 0.7
            assert "volatility_score" in result["details"]
            assert "volume_score" in result["details"]
            assert "correlation_score" in result["details"]
        else:
            assert "reasons" in result
            assert len(result["reasons"]) > 0
