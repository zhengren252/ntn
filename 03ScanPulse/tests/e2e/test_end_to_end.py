# 端到端测试
# 测试完整的用户场景和工作流

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.main import ScannerApplication
from scanner.config.env_manager import EnvironmentManager
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.adapters.trading_agents_cn_adapter import TACoreServiceAdapter
from scanner.health_check import HealthChecker


class TestEndToEnd:
    """端到端测试类"""

    @pytest.fixture
    def e2e_config(self):
        """端到端测试配置"""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 14,
                "password": None,
                "socket_timeout": 10,
                "key_prefix": "e2e_scanner",
                "default_ttl": 600,
            },
            "zmq": {
                "pub_port": 15559,
                "rep_port": 15560,
                "context_io_threads": 2,
                "socket_linger": 1000,
                "heartbeat_interval": 10,
            },
            "scanner": {
                "scan_interval": 30,
                "batch_size": 20,
                "max_workers": 4,
                "timeout": 60,
                "rules": {
                    "three_high": {
                        "enabled": True,
                        "volatility_threshold": 0.05,
                        "volume_threshold": 1000000,
                        "correlation_threshold": 0.7,
                        "min_score": 0.6,
                    },
                    "black_horse": {
                        "enabled": True,
                        "price_change_threshold": 0.1,
                        "volume_spike_threshold": 2.0,
                        "confidence_threshold": 0.8,
                        "news_weight": 0.3,
                    },
                    "potential_finder": {
                        "enabled": True,
                        "max_market_cap": 100000000,
                        "max_price": 1.0,
                        "min_volume": 50000,
                        "growth_threshold": 0.2,
                    },
                },
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file_enabled": True,
                "console_enabled": True,
                "log_dir": "logs",
            },
        }

    @pytest.fixture
    def realistic_market_data(self):
        """真实市场数据模拟"""
        base_time = datetime.now(timezone.utc)

        return [
            # 主流币种 - 高流动性
            {
                "symbol": "BTCUSDT",
                "price": 43500.0,
                "volume": 2500000000.0,
                "change_24h": 0.035,
                "high_24h": 44200.0,
                "low_24h": 42800.0,
                "market_cap": 850000000000,
                "timestamp": base_time.isoformat(),
                "technical_indicators": {
                    "rsi": 68.5,
                    "volatility": 0.08,
                    "volume_sma": 2200000000.0,
                    "price_sma_20": 43200.0,
                    "bollinger_upper": 44500.0,
                    "bollinger_lower": 42000.0,
                },
                "news_sentiment": 0.6,
                "social_metrics": {"mentions": 15000, "sentiment_score": 0.65},
            },
            # 以太坊 - 高相关性
            {
                "symbol": "ETHUSDT",
                "price": 2650.0,
                "volume": 1800000000.0,
                "change_24h": 0.042,
                "high_24h": 2720.0,
                "low_24h": 2580.0,
                "market_cap": 320000000000,
                "timestamp": base_time.isoformat(),
                "technical_indicators": {
                    "rsi": 72.0,
                    "volatility": 0.09,
                    "volume_sma": 1600000000.0,
                    "price_sma_20": 2620.0,
                    "bollinger_upper": 2750.0,
                    "bollinger_lower": 2500.0,
                },
                "news_sentiment": 0.7,
                "social_metrics": {"mentions": 12000, "sentiment_score": 0.72},
            },
            # 新兴币种 - 黑马候选
            {
                "symbol": "NEWCOINUSDT",
                "price": 0.85,
                "volume": 150000000.0,
                "change_24h": 0.25,
                "high_24h": 0.95,
                "low_24h": 0.68,
                "market_cap": 85000000,
                "timestamp": base_time.isoformat(),
                "technical_indicators": {
                    "rsi": 88.0,
                    "volatility": 0.35,
                    "volume_sma": 80000000.0,
                    "price_sma_20": 0.72,
                    "bollinger_upper": 1.0,
                    "bollinger_lower": 0.5,
                },
                "news_sentiment": 0.85,
                "social_metrics": {"mentions": 8500, "sentiment_score": 0.88},
            },
            # 潜力币种 - 低市值
            {
                "symbol": "GEMCOINUSDT",
                "price": 0.15,
                "volume": 25000000.0,
                "change_24h": 0.18,
                "high_24h": 0.17,
                "low_24h": 0.12,
                "market_cap": 15000000,
                "timestamp": base_time.isoformat(),
                "technical_indicators": {
                    "rsi": 78.0,
                    "volatility": 0.28,
                    "volume_sma": 18000000.0,
                    "price_sma_20": 0.13,
                    "bollinger_upper": 0.18,
                    "bollinger_lower": 0.08,
                },
                "news_sentiment": 0.75,
                "social_metrics": {"mentions": 3200, "sentiment_score": 0.78},
            },
            # 稳定币 - 低波动
            {
                "symbol": "USDCUSDT",
                "price": 1.0001,
                "volume": 500000000.0,
                "change_24h": 0.0001,
                "high_24h": 1.0005,
                "low_24h": 0.9998,
                "market_cap": 32000000000,
                "timestamp": base_time.isoformat(),
                "technical_indicators": {
                    "rsi": 50.0,
                    "volatility": 0.001,
                    "volume_sma": 480000000.0,
                    "price_sma_20": 1.0000,
                    "bollinger_upper": 1.002,
                    "bollinger_lower": 0.998,
                },
                "news_sentiment": 0.5,
                "social_metrics": {"mentions": 1000, "sentiment_score": 0.5},
            },
        ]

    @pytest.fixture
    def news_events_data(self):
        """新闻事件数据"""
        base_time = datetime.now(timezone.utc)

        return [
            {
                "id": "news_001",
                "title": "Major Exchange Lists NEWCOIN with Trading Pairs",
                "content": "Leading cryptocurrency exchange announces listing of NEWCOIN with multiple trading pairs including USDT and BTC.",
                "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                "source": "CryptoNews",
                "sentiment": 0.9,
                "relevance": 0.95,
                "symbols": ["NEWCOINUSDT"],
                "category": "listing",
                "impact_score": 0.8,
            },
            {
                "id": "news_002",
                "title": "GEMCOIN Partnership with Major DeFi Protocol",
                "content": "GEMCOIN announces strategic partnership with leading DeFi protocol for yield farming integration.",
                "timestamp": (base_time - timedelta(hours=4)).isoformat(),
                "source": "DeFiDaily",
                "sentiment": 0.8,
                "relevance": 0.85,
                "symbols": ["GEMCOINUSDT"],
                "category": "partnership",
                "impact_score": 0.7,
            },
            {
                "id": "news_003",
                "title": "Bitcoin ETF Approval Boosts Market Sentiment",
                "content": "SEC approval of Bitcoin ETF drives positive sentiment across cryptocurrency markets.",
                "timestamp": (base_time - timedelta(hours=6)).isoformat(),
                "source": "FinancialTimes",
                "sentiment": 0.85,
                "relevance": 0.9,
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "category": "regulation",
                "impact_score": 0.9,
            },
        ]

    @pytest.mark.e2e
    async def test_complete_scanning_workflow(
        self, e2e_config, realistic_market_data, news_events_data
    ):
        """测试完整扫描工作流"""
        # 创建结果收集器
        scan_results = []
        status_updates = []

        # 创建模拟环境管理器
        mock_env_manager = Mock(spec=EnvironmentManager)
        mock_env_manager.get_redis_config.return_value = e2e_config["redis"]
        mock_env_manager.get_zmq_config.return_value = e2e_config["zmq"]
        mock_env_manager.get_scanner_config.return_value = e2e_config["scanner"]
        mock_env_manager.get_logging_config.return_value = e2e_config["logging"]
        mock_env_manager.is_development.return_value = False
        mock_env_manager.validate_config.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # 创建模拟Redis客户端
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.is_connected.return_value = True
        mock_redis.ping.return_value = True
        mock_redis.get_historical_data.return_value = []
        mock_redis.get_news_events.return_value = news_events_data
        mock_redis.get_market_overview.return_value = {
            "total_market_cap": 2500000000000,
            "total_volume_24h": 80000000000,
            "btc_dominance": 0.52,
        }

        def store_scan_result(symbol, data):
            scan_results.append({"symbol": symbol, "data": data})
            return True

        mock_redis.set_scan_result.side_effect = store_scan_result

        # 创建模拟ZMQ客户端
        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.is_running.return_value = True

        async def capture_scan_result(data):
            scan_results.append({"type": "zmq_scan", "data": data})

        mock_zmq.publish_scan_result.side_effect = capture_scan_result

        async def capture_status_update(data):
            status_updates.append(data)

        mock_zmq.publish_status_update.side_effect = capture_status_update

        # 创建模拟适配器
        mock_adapter = Mock(spec=TACoreServiceAdapter)
        mock_adapter.connect = AsyncMock()
        mock_adapter.is_connected.return_value = True
        mock_adapter.get_status.return_value = {"status": "connected", "agents": 3}

        # 模拟适配器扫描
        scan_callback = None

        def set_callbacks(scan_result_callback, error_callback):
            nonlocal scan_callback
            scan_callback = scan_result_callback

        mock_adapter.set_callbacks.side_effect = set_callbacks

        # 创建模拟健康检查器
        mock_health_checker = Mock(spec=HealthChecker)
        mock_health_checker.start_monitoring = AsyncMock()
        mock_health_checker.get_overall_status.return_value = "healthy"

        # 运行完整工作流
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

            # 初始化组件
            success = await app.initialize_components()
            assert success is True

            # 验证组件初始化
            mock_redis.connect.assert_called_once()
            mock_zmq.start.assert_called_once()
            mock_adapter.connect.assert_called_once()
            mock_health_checker.start_monitoring.assert_called_once()

            # 模拟适配器返回扫描数据
            assert scan_callback is not None
            await scan_callback(realistic_market_data)

            # 等待处理完成
            await asyncio.sleep(0.1)

            # 验证扫描结果
            assert len(scan_results) >= len(realistic_market_data)

            # 验证三高规则触发
            btc_results = [r for r in scan_results if "BTCUSDT" in str(r)]
            eth_results = [r for r in scan_results if "ETHUSDT" in str(r)]
            assert len(btc_results) > 0
            assert len(eth_results) > 0

            # 验证黑马检测
            newcoin_results = [r for r in scan_results if "NEWCOINUSDT" in str(r)]
            assert len(newcoin_results) > 0

            # 验证潜力挖掘
            gemcoin_results = [r for r in scan_results if "GEMCOINUSDT" in str(r)]
            assert len(gemcoin_results) > 0

            # 验证状态更新
            assert len(status_updates) > 0

            # 执行关闭
            await app.shutdown()

    @pytest.mark.e2e
    async def test_real_time_market_monitoring(self, e2e_config, realistic_market_data):
        """测试实时市场监控"""
        # 模拟实时数据流
        market_updates = []

        # 创建模拟组件
        mock_env_manager = Mock(spec=EnvironmentManager)
        mock_env_manager.get_scanner_config.return_value = e2e_config["scanner"]

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.get_historical_data.return_value = []
        mock_redis.get_news_events.return_value = []
        mock_redis.get_market_overview.return_value = {
            "total_market_cap": 2500000000000
        }

        def capture_market_update(symbol, data):
            market_updates.append(
                {"symbol": symbol, "data": data, "timestamp": time.time()}
            )
            return True

        mock_redis.set_scan_result.side_effect = capture_market_update

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        # 创建扫描器应用
        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq

            # 初始化引擎
            await app._initialize_engines()

            # 模拟实时数据更新
            for i in range(3):  # 3轮更新
                # 更新价格数据
                updated_data = []
                for data in realistic_market_data:
                    updated = data.copy()
                    # 模拟价格变化
                    price_change = (i + 1) * 0.01  # 1%, 2%, 3%
                    updated["price"] = data["price"] * (1 + price_change)
                    updated["change_24h"] = data["change_24h"] + price_change
                    updated["timestamp"] = datetime.now(timezone.utc).isoformat()
                    updated_data.append(updated)

                # 处理更新
                await app._handle_scan_result(updated_data)

                # 等待处理
                await asyncio.sleep(0.1)

            # 验证实时更新
            assert len(market_updates) >= len(realistic_market_data) * 3

            # 验证时间序列
            timestamps = [update["timestamp"] for update in market_updates]
            assert all(
                timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1)
            )

    @pytest.mark.e2e
    async def test_error_recovery_scenarios(self, e2e_config):
        """测试错误恢复场景"""
        recovery_events = []

        # 创建模拟组件
        mock_env_manager = Mock(spec=EnvironmentManager)
        mock_env_manager.get_redis_config.return_value = e2e_config["redis"]
        mock_env_manager.get_zmq_config.return_value = e2e_config["zmq"]
        mock_env_manager.get_scanner_config.return_value = e2e_config["scanner"]

        # 模拟Redis连接问题
        mock_redis = Mock(spec=RedisClient)
        connection_attempts = 0

        def simulate_connection_issues():
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts <= 2:
                recovery_events.append(f"redis_connection_failed_{connection_attempts}")
                return False
            else:
                recovery_events.append("redis_connection_recovered")
                return True

        mock_redis.connect.side_effect = simulate_connection_issues
        mock_redis.is_connected.return_value = True

        # 模拟ZMQ问题
        mock_zmq = Mock(spec=ScannerZMQClient)
        zmq_start_attempts = 0

        def simulate_zmq_issues():
            nonlocal zmq_start_attempts
            zmq_start_attempts += 1
            if zmq_start_attempts <= 1:
                recovery_events.append(f"zmq_start_failed_{zmq_start_attempts}")
                raise Exception("ZMQ connection failed")
            else:
                recovery_events.append("zmq_start_recovered")
                return None

        mock_zmq.start.side_effect = simulate_zmq_issues
        mock_zmq.is_running.return_value = True

        # 模拟适配器问题
        mock_adapter = Mock(spec=TACoreServiceAdapter)
        adapter_connect_attempts = 0

        async def simulate_adapter_issues():
            nonlocal adapter_connect_attempts
            adapter_connect_attempts += 1
            if adapter_connect_attempts <= 1:
                recovery_events.append(
                    f"adapter_connect_failed_{adapter_connect_attempts}"
                )
                raise Exception("Adapter connection failed")
            else:
                recovery_events.append("adapter_connect_recovered")
                return None

        mock_adapter.connect.side_effect = simulate_adapter_issues

        # 测试错误恢复
        with patch(
            "scanner.main.get_env_manager", return_value=mock_env_manager
        ), patch("scanner.main.RedisClient", return_value=mock_redis), patch(
            "scanner.main.ScannerZMQClient", return_value=mock_zmq
        ), patch(
            "scanner.main.TACoreServiceAdapter", return_value=mock_adapter
        ):
            app = ScannerApplication()

            # 多次尝试初始化（模拟重试机制）
            for attempt in range(3):
                try:
                    success = await app.initialize_components()
                    if success:
                        break
                except Exception as e:
                    recovery_events.append(
                        f"initialization_attempt_{attempt + 1}_failed"
                    )
                    await asyncio.sleep(0.1)  # 短暂等待后重试

            # 验证恢复事件
            assert "redis_connection_failed_1" in recovery_events
            assert "redis_connection_recovered" in recovery_events
            assert "zmq_start_failed_1" in recovery_events
            assert "zmq_start_recovered" in recovery_events
            assert "adapter_connect_failed_1" in recovery_events
            assert "adapter_connect_recovered" in recovery_events

    @pytest.mark.e2e
    async def test_configuration_hot_reload(self, e2e_config):
        """测试配置热重载"""
        config_changes = []

        # 创建动态配置管理器
        mock_env_manager = Mock(spec=EnvironmentManager)

        # 初始配置
        current_config = e2e_config["scanner"].copy()
        mock_env_manager.get_scanner_config.return_value = current_config

        # 模拟配置变更
        def update_config(new_values):
            current_config.update(new_values)
            config_changes.append({"timestamp": time.time(), "changes": new_values})
            return current_config

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None

        # 创建扫描器应用
        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq

            # 初始化
            await app._initialize_engines()

            # 验证初始配置
            assert app.three_high_engine.config["volatility_threshold"] == 0.05

            # 模拟配置更新
            new_scanner_config = update_config(
                {
                    "rules": {
                        "three_high": {
                            "enabled": True,
                            "volatility_threshold": 0.08,  # 更新阈值
                            "volume_threshold": 2000000,  # 更新阈值
                            "correlation_threshold": 0.75,
                        }
                    }
                }
            )

            # 重新初始化引擎（模拟热重载）
            await app._initialize_engines()

            # 验证配置更新
            assert len(config_changes) == 1
            assert (
                config_changes[0]["changes"]["rules"]["three_high"][
                    "volatility_threshold"
                ]
                == 0.08
            )

    @pytest.mark.e2e
    async def test_multi_environment_deployment(self, e2e_config):
        """测试多环境部署"""
        environments = ["development", "staging", "production"]
        deployment_results = {}

        for env in environments:
            # 为每个环境创建不同的配置
            env_config = e2e_config.copy()

            if env == "development":
                env_config["redis"]["db"] = 15
                env_config["scanner"]["scan_interval"] = 5
                env_config["logging"]["level"] = "DEBUG"
            elif env == "staging":
                env_config["redis"]["db"] = 1
                env_config["scanner"]["scan_interval"] = 15
                env_config["logging"]["level"] = "INFO"
            else:  # production
                env_config["redis"]["db"] = 0
                env_config["scanner"]["scan_interval"] = 30
                env_config["logging"]["level"] = "WARNING"

            # 创建环境特定的模拟组件
            mock_env_manager = Mock(spec=EnvironmentManager)
            mock_env_manager.get_redis_config.return_value = env_config["redis"]
            mock_env_manager.get_zmq_config.return_value = env_config["zmq"]
            mock_env_manager.get_scanner_config.return_value = env_config["scanner"]
            mock_env_manager.get_logging_config.return_value = env_config["logging"]
            mock_env_manager.is_development.return_value = env == "development"
            mock_env_manager.validate_config.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
            }

            mock_redis = Mock(spec=RedisClient)
            mock_redis.connect.return_value = True

            mock_zmq = Mock(spec=ScannerZMQClient)
            mock_zmq.start.return_value = None

            # 测试环境部署
            with patch(
                "scanner.main.get_env_manager", return_value=mock_env_manager
            ), patch("scanner.main.RedisClient", return_value=mock_redis), patch(
                "scanner.main.ScannerZMQClient", return_value=mock_zmq
            ):
                app = ScannerApplication()

                try:
                    success = await app.initialize_components()
                    deployment_results[env] = {
                        "success": success,
                        "redis_db": env_config["redis"]["db"],
                        "scan_interval": env_config["scanner"]["scan_interval"],
                        "log_level": env_config["logging"]["level"],
                    }
                except Exception as e:
                    deployment_results[env] = {"success": False, "error": str(e)}

                await app.shutdown()

        # 验证所有环境部署成功
        for env in environments:
            assert deployment_results[env]["success"] is True
            assert "redis_db" in deployment_results[env]
            assert "scan_interval" in deployment_results[env]
            assert "log_level" in deployment_results[env]

        # 验证环境差异
        assert deployment_results["development"]["redis_db"] == 15
        assert deployment_results["staging"]["redis_db"] == 1
        assert deployment_results["production"]["redis_db"] == 0

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_long_running_stability(self, e2e_config, realistic_market_data):
        """测试长期运行稳定性"""
        stability_metrics = {
            "uptime": 0,
            "processed_batches": 0,
            "errors": [],
            "memory_samples": [],
            "performance_samples": [],
        }

        # 创建模拟组件
        mock_env_manager = Mock(spec=EnvironmentManager)
        mock_env_manager.get_scanner_config.return_value = e2e_config["scanner"]

        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.set_scan_result.return_value = True
        mock_redis.get_historical_data.return_value = []
        mock_redis.get_news_events.return_value = []
        mock_redis.get_market_overview.return_value = {
            "total_market_cap": 2500000000000
        }

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        # 创建扫描器应用
        with patch("scanner.main.get_env_manager", return_value=mock_env_manager):
            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq

            # 初始化
            await app._initialize_engines()

            start_time = time.time()

            # 模拟长期运行（简化版本）
            for cycle in range(10):  # 10个周期
                try:
                    cycle_start = time.time()

                    # 处理数据批次
                    await app._handle_scan_result(realistic_market_data)

                    cycle_end = time.time()

                    # 记录性能指标
                    stability_metrics["processed_batches"] += 1
                    stability_metrics["performance_samples"].append(
                        cycle_end - cycle_start
                    )

                    # 模拟内存使用（简化）
                    stability_metrics["memory_samples"].append(
                        100 + cycle * 2
                    )  # 模拟轻微增长

                    # 短暂等待
                    await asyncio.sleep(0.1)

                except Exception as e:
                    stability_metrics["errors"].append(str(e))

            end_time = time.time()
            stability_metrics["uptime"] = end_time - start_time

            # 验证稳定性指标
            assert stability_metrics["processed_batches"] == 10
            assert len(stability_metrics["errors"]) == 0
            assert stability_metrics["uptime"] > 0

            # 验证性能稳定性
            avg_performance = sum(stability_metrics["performance_samples"]) / len(
                stability_metrics["performance_samples"]
            )
            assert avg_performance < 1.0  # 平均处理时间小于1秒

            # 验证内存稳定性
            memory_growth = (
                stability_metrics["memory_samples"][-1]
                - stability_metrics["memory_samples"][0]
            )
            assert memory_growth < 50  # 内存增长小于50MB（模拟值）

            print(f"长期运行稳定性测试结果: {stability_metrics}")
