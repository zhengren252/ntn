# 扫描器集成测试
# 测试各组件之间的协作和完整工作流

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.main import ScannerApplication
from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.detectors.black_horse_detector import BlackHorseDetector
from scanner.detectors.potential_finder import PotentialFinder
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.adapters.trading_agents_cn_adapter import TACoreServiceAdapter
from scanner.config.env_manager import EnvironmentManager
from scanner.health_check import HealthChecker


class TestScannerIntegration:
    """扫描器集成测试类"""

    @pytest.fixture
    def integration_config(self):
        """集成测试配置"""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "password": None,
                "socket_timeout": 5,
                "key_prefix": "test_scanner",
                "default_ttl": 300,
            },
            "zmq": {
                "pub_port": 15555,
                "rep_port": 15556,
                "context_io_threads": 1,
                "socket_linger": 0,
                "heartbeat_interval": 5,
            },
            "scanner": {
                "scan_interval": 10,
                "batch_size": 5,
                "max_workers": 2,
                "timeout": 30,
                "rules": {
                    "three_high": {
                        "enabled": True,
                        "volatility_threshold": 0.05,
                        "volume_threshold": 1000000,
                        "correlation_threshold": 0.7,
                    },
                    "black_horse": {
                        "enabled": True,
                        "price_change_threshold": 0.1,
                        "volume_spike_threshold": 2.0,
                        "confidence_threshold": 0.8,
                    },
                    "potential_finder": {
                        "enabled": True,
                        "max_market_cap": 100000000,
                        "max_price": 1.0,
                        "min_volume": 50000,
                    },
                },
            },
        }

    @pytest.fixture
    def mock_env_manager(self, integration_config):
        """模拟环境管理器"""
        env_manager = Mock(spec=EnvironmentManager)
        env_manager.get_redis_config.return_value = integration_config["redis"]
        env_manager.get_zmq_config.return_value = integration_config["zmq"]
        env_manager.get_scanner_config.return_value = integration_config["scanner"]
        env_manager.get_logging_config.return_value = {
            "level": "DEBUG",
            "format": "json",
            "file_enabled": False,
            "console_enabled": False,
        }
        env_manager.is_development.return_value = True
        env_manager.validate_config.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        return env_manager

    @pytest.fixture
    def sample_market_data_batch(self):
        """示例市场数据批次"""
        return [
            {
                "symbol": "BTCUSDT",
                "price": 45000.0,
                "volume": 1500000.0,
                "change_24h": 0.08,
                "high_24h": 46000.0,
                "low_24h": 44000.0,
                "market_cap": 850000000000,
                "timestamp": "2024-01-01T12:00:00Z",
                "technical_indicators": {
                    "rsi": 75.0,
                    "volatility": 0.09,
                    "volume_sma": 1200000.0,
                },
            },
            {
                "symbol": "ETHUSDT",
                "price": 3000.0,
                "volume": 2500000.0,
                "change_24h": 0.06,
                "high_24h": 3100.0,
                "low_24h": 2900.0,
                "market_cap": 360000000000,
                "timestamp": "2024-01-01T12:00:00Z",
                "technical_indicators": {
                    "rsi": 68.0,
                    "volatility": 0.07,
                    "volume_sma": 1800000.0,
                },
            },
            {
                "symbol": "NEWCOIN",
                "price": 0.5,
                "volume": 800000.0,
                "change_24h": 0.15,
                "high_24h": 0.55,
                "low_24h": 0.45,
                "market_cap": 50000000,
                "timestamp": "2024-01-01T12:00:00Z",
                "technical_indicators": {
                    "rsi": 85.0,
                    "volatility": 0.18,
                    "volume_sma": 400000.0,
                },
            },
        ]

    @pytest.mark.integration
    async def test_full_scanner_workflow(
        self, mock_env_manager, sample_market_data_batch
    ):
        """测试完整扫描器工作流"""
        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.is_connected.return_value = True
        mock_redis.ping.return_value = True
        mock_redis.set_scan_result.return_value = True
        mock_redis.get_historical_data.return_value = []

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.is_running.return_value = True
        mock_zmq.publish_scan_result = AsyncMock()
        mock_zmq.publish_status_update = AsyncMock()

        mock_adapter = Mock(spec=TACoreServiceAdapter)
        mock_adapter.connect = AsyncMock()
        mock_adapter.scan_symbols = AsyncMock(return_value=sample_market_data_batch)
        mock_adapter.analyze_symbol_detailed = AsyncMock(
            return_value={
                "symbol": "BTCUSDT",
                "analysis": {"score": 0.85, "signals": ["bullish"]},
                "market_data": {"price": 45000.0, "volume": 1500000.0},
            }
        )
        mock_adapter.get_market_overview = AsyncMock(
            return_value={
                "summary": {"total_symbols": 3, "active_symbols": 3},
                "popular_symbols": sample_market_data_batch,
            }
        )
        mock_adapter.health_check = Mock(return_value=True)
        mock_adapter.is_connected = Mock(return_value=True)
        mock_adapter.get_adapter_status = Mock(
            return_value={"connected": True, "healthy": True}
        )

        # 创建扫描器应用
        with patch(
            "scanner.main.get_env_manager", return_value=mock_env_manager
        ), patch("scanner.main.RedisClient", return_value=mock_redis), patch(
            "scanner.main.ScannerZMQClient", return_value=mock_zmq
        ), patch(
            "scanner.main.TACoreServiceAdapter", return_value=mock_adapter
        ), patch(
            "scanner.main.get_health_checker"
        ) as mock_health_checker:
            app = ScannerApplication()

            # 初始化组件
            success = await app.initialize_components()
            assert success is True

            # 验证组件初始化
            mock_redis.connect.assert_called_once()
            mock_zmq.start.assert_called_once()
            mock_adapter.connect.assert_called_once()

    @pytest.mark.integration
    async def test_scan_result_processing_pipeline(
        self, mock_env_manager, sample_market_data_batch
    ):
        """测试扫描结果处理管道"""
        # 模拟各个引擎的分析结果
        three_high_result = {
            "triggered": True,
            "score": 0.85,
            "details": {
                "volatility_score": 0.9,
                "volume_score": 0.8,
                "correlation_score": 0.85,
            },
        }

        black_horse_result = {
            "detected": True,
            "confidence": 0.9,
            "reasons": ["High volume spike", "Positive news sentiment"],
        }

        potential_result = {
            "has_potential": True,
            "potential_score": 0.75,
            "reasons": ["Low market cap", "Growing volume"],
        }

        # 创建模拟引擎
        mock_three_high = Mock(spec=ThreeHighEngine)
        mock_three_high.analyze = AsyncMock(return_value=three_high_result)

        mock_black_horse = Mock(spec=BlackHorseDetector)
        mock_black_horse.detect = AsyncMock(return_value=black_horse_result)

        mock_potential = Mock(spec=PotentialFinder)
        mock_potential.find_potential = AsyncMock(return_value=potential_result)

        # 创建模拟通信组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.set_scan_result.return_value = True

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.publish_scan_result = AsyncMock()

        # 创建扫描器应用并设置引擎
        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq
            app.three_high_engine = mock_three_high
            app.black_horse_detector = mock_black_horse
            app.potential_finder = mock_potential

            # 处理扫描结果
            for market_data in sample_market_data_batch:
                await app._apply_scan_engines(market_data["symbol"], market_data)

            # 验证引擎调用
            assert mock_three_high.analyze.call_count == 3
            assert mock_black_horse.detect.call_count == 3
            assert mock_potential.find_potential.call_count == 3

            # 验证结果发布
            assert mock_zmq.publish_scan_result.call_count >= 3  # 至少发布了触发的信号

    @pytest.mark.integration
    async def test_error_handling_and_recovery(self, mock_env_manager):
        """测试错误处理和恢复机制"""
        # 模拟Redis连接失败
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = False

        with patch(
            "scanner.main.get_env_manager", return_value=mock_env_manager
        ), patch("scanner.main.RedisClient", return_value=mock_redis):
            app = ScannerApplication()

            # 初始化应该失败
            success = await app.initialize_components()
            assert success is False

    @pytest.mark.integration
    async def test_health_monitoring_integration(self, mock_env_manager):
        """测试健康监控集成"""
        mock_health_checker = Mock(spec=HealthChecker)
        mock_health_checker.start_monitoring = AsyncMock()
        mock_health_checker.stop_monitoring.return_value = None

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.health_check.return_value = {"status": "healthy"}

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.is_running.return_value = True

        with patch(
            "scanner.main.get_env_manager", return_value=mock_env_manager
        ), patch(
            "scanner.main.get_health_checker", return_value=mock_health_checker
        ), patch(
            "scanner.main.RedisClient", return_value=mock_redis
        ), patch(
            "scanner.main.ScannerZMQClient", return_value=mock_zmq
        ):
            app = ScannerApplication()
            await app.initialize_components()

            # 验证健康检查器被正确设置
            assert app.health_checker == mock_health_checker

    @pytest.mark.integration
    async def test_configuration_validation_integration(self, mock_env_manager):
        """测试配置验证集成"""
        # 测试无效配置
        mock_env_manager.validate_config.return_value = {
            "valid": False,
            "errors": ["Invalid Redis host", "Missing ZMQ port"],
            "warnings": [],
        }

        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()

            # 模拟运行，应该因配置无效而退出
            with patch.object(app, "initialize_components", return_value=True):
                await app.run()

                # 验证配置验证被调用
                mock_env_manager.validate_config.assert_called_once()

    @pytest.mark.integration
    async def test_trading_adapter_integration(
        self, mock_env_manager, sample_market_data_batch
    ):
        """测试交易适配器集成"""
        mock_adapter = Mock(spec=TACoreServiceAdapter)
        mock_adapter.connect = AsyncMock()
        mock_adapter.scan_symbols = AsyncMock()
        mock_adapter.set_callbacks.return_value = None

        # 模拟适配器回调
        scan_callback = None
        error_callback = None

        def set_callbacks(scan_result_callback, error_callback_func):
            nonlocal scan_callback, error_callback
            scan_callback = scan_result_callback
            error_callback = error_callback_func

        mock_adapter.set_callbacks.side_effect = set_callbacks

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.set_scan_result.return_value = True

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        with patch(
            "scanner.main.get_env_manager", return_value=mock_env_manager
        ), patch(
            "scanner.main.TACoreServiceAdapter", return_value=mock_adapter
        ), patch(
            "scanner.main.RedisClient", return_value=mock_redis
        ), patch(
            "scanner.main.ScannerZMQClient", return_value=mock_zmq
        ):
            app = ScannerApplication()
            await app.initialize_components()

            # 验证回调设置
            assert scan_callback is not None
            assert error_callback is not None

            # 测试扫描结果回调
            await scan_callback(sample_market_data_batch)

            # 验证结果处理
            assert mock_redis.set_scan_result.call_count == len(
                sample_market_data_batch
            )
            assert mock_zmq.publish_scan_result.call_count == len(
                sample_market_data_batch
            )

    @pytest.mark.integration
    async def test_concurrent_scan_processing(
        self, mock_env_manager, sample_market_data_batch
    ):
        """测试并发扫描处理"""
        # 创建多个并发扫描任务
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.set_scan_result.return_value = True
        mock_redis.get_historical_data.return_value = []

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        # 模拟引擎处理延迟
        mock_three_high = Mock(spec=ThreeHighEngine)

        async def slow_analyze(symbol, data):
            await asyncio.sleep(0.1)  # 模拟处理时间
            return {"triggered": True, "score": 0.8}

        mock_three_high.analyze = slow_analyze

        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq
            app.three_high_engine = mock_three_high

            # 并发处理多个交易对
            start_time = time.time()

            tasks = []
            for market_data in sample_market_data_batch:
                task = app._apply_scan_engines(market_data["symbol"], market_data)
                tasks.append(task)

            await asyncio.gather(*tasks)

            end_time = time.time()

            # 验证并发处理效率（应该比串行处理快）
            assert end_time - start_time < 0.5  # 应该在0.5秒内完成

    @pytest.mark.integration
    async def test_data_flow_consistency(
        self, mock_env_manager, sample_market_data_batch
    ):
        """测试数据流一致性"""
        # 跟踪数据流
        data_flow = []

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True

        def track_redis_set(symbol, data):
            data_flow.append(f"redis_set_{symbol}")
            return True

        mock_redis.set_scan_result.side_effect = track_redis_set

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None

        async def track_zmq_publish(data):
            symbol = data.get("symbol", "unknown")
            data_flow.append(f"zmq_publish_{symbol}")

        mock_zmq.publish_scan_result.side_effect = track_zmq_publish

        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq

            # 处理扫描结果
            for market_data in sample_market_data_batch:
                await app._handle_scan_result([market_data])

            # 验证数据流顺序
            for market_data in sample_market_data_batch:
                symbol = market_data["symbol"]
                assert f"redis_set_{symbol}" in data_flow
                assert f"zmq_publish_{symbol}" in data_flow

                # 验证Redis存储在ZMQ发布之前
                redis_index = data_flow.index(f"redis_set_{symbol}")
                zmq_index = data_flow.index(f"zmq_publish_{symbol}")
                assert redis_index < zmq_index

    @pytest.mark.integration
    async def test_resource_cleanup(self, mock_env_manager):
        """测试资源清理"""
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.disconnect.return_value = None

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.stop.return_value = None

        mock_adapter = Mock(spec=TACoreServiceAdapter)
        mock_adapter.connect = AsyncMock()
        mock_adapter.disconnect = AsyncMock()

        mock_health_checker = Mock(spec=HealthChecker)
        mock_health_checker.stop_monitoring.return_value = None

        with patch(
            "scanner.main.get_env_manager", return_value=mock_env_manager
        ), patch("scanner.main.RedisClient", return_value=mock_redis), patch(
            "scanner.main.ScannerZMQClient", return_value=mock_zmq
        ), patch(
            "scanner.main.TACoreServiceAdapter", return_value=mock_adapter
        ), patch(
            "scanner.main.get_health_checker", return_value=mock_health_checker
        ):
            app = ScannerApplication()
            await app.initialize_components()

            # 执行关闭
            await app.shutdown()

            # 验证资源清理
            mock_health_checker.stop_monitoring.assert_called_once()
            mock_adapter.disconnect.assert_called_once()
            mock_zmq.stop.assert_called_once()
            mock_redis.disconnect.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_performance_under_load(self, mock_env_manager):
        """测试负载下的性能"""
        # 生成大量测试数据
        large_data_batch = []
        for i in range(100):
            data = {
                "symbol": f"TEST{i}USDT",
                "price": 100.0 + i,
                "volume": 1000000 + i * 10000,
                "change_24h": 0.01 * (i % 10),
                "timestamp": "2024-01-01T12:00:00Z",
            }
            large_data_batch.append(data)

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.set_scan_result.return_value = True

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq

            # 测试处理大批量数据的性能
            start_time = time.time()

            await app._handle_scan_result(large_data_batch)

            end_time = time.time()
            processing_time = end_time - start_time

            # 验证性能指标
            assert processing_time < 5.0  # 应该在5秒内完成100个项目
            assert mock_redis.set_scan_result.call_count == 100
            assert mock_zmq.publish_scan_result.call_count == 100

            # 计算吞吐量
            throughput = len(large_data_batch) / processing_time
            assert throughput > 20  # 每秒至少处理20个项目
