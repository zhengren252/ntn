#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境验证测试模块
测试03ScanPulse在生产环境下的各项功能和性能表现
包括：真实数据源集成测试、多环境配置验证、安全性和权限测试、监控和告警功能测试
"""

import pytest
import asyncio
import time
import json
import os
import ssl
import hashlib
import hmac
import base64
import requests
import websocket
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import configparser
import tempfile
import shutil
from cryptography.fernet import Fernet
import jwt
from urllib.parse import urljoin, urlparse
import socket
import threading
from contextlib import contextmanager

import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.detectors.black_horse_detector import BlackHorseDetector
from scanner.detectors.potential_finder import PotentialFinder
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.main import ScannerApplication
from scanner.core.data_processor import DataProcessor
from scanner.web.app import ScannerWebApp


@dataclass
class ProductionTestResult:
    """生产环境测试结果"""

    test_name: str
    environment: str
    start_time: float
    end_time: float
    success: bool
    error_message: Optional[str]
    metrics: Dict[str, Any]
    security_score: float
    performance_score: float
    reliability_score: float


class ProductionEnvironmentManager:
    """生产环境管理器"""

    def __init__(self, base_config: Dict[str, Any]):
        self.base_config = base_config
        self.environments = {}
        self.current_env = None
        self.temp_dirs = []

    def create_environment(
        self, env_name: str, overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """创建测试环境"""
        env_config = self.base_config.copy()

        if overrides:
            self._deep_update(env_config, overrides)

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix=f"scanpulse_{env_name}_")
        self.temp_dirs.append(temp_dir)

        env_config["temp_dir"] = temp_dir
        env_config["environment"] = env_name

        self.environments[env_name] = env_config
        return env_config

    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if (
                isinstance(value, dict)
                and key in base_dict
                and isinstance(base_dict[key], dict)
            ):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    @contextmanager
    def use_environment(self, env_name: str):
        """使用指定环境"""
        if env_name not in self.environments:
            raise ValueError(f"Environment {env_name} not found")

        old_env = self.current_env
        self.current_env = env_name

        try:
            yield self.environments[env_name]
        finally:
            self.current_env = old_env

    def cleanup(self):
        """清理临时资源"""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()


class RealDataSourceSimulator:
    """真实数据源模拟器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_connected = False
        self.websocket_client = None
        self.api_session = None
        self.data_buffer = []
        self.connection_errors = []

    async def connect_to_binance_api(self) -> bool:
        """连接到币安API（模拟）"""
        try:
            # 模拟API连接
            self.api_session = requests.Session()

            # 测试连接
            response = self.api_session.get(
                "https://api.binance.com/api/v3/ping", timeout=10
            )

            if response.status_code == 200:
                self.is_connected = True
                return True
            else:
                self.connection_errors.append(
                    f"API ping failed: {response.status_code}"
                )
                return False

        except Exception as e:
            self.connection_errors.append(f"API connection error: {str(e)}")
            return False

    async def connect_to_websocket_stream(self) -> bool:
        """连接到WebSocket数据流（模拟）"""
        try:
            # 模拟WebSocket连接
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self.data_buffer.append(data)
                except Exception as e:
                    self.connection_errors.append(f"WebSocket message error: {str(e)}")

            def on_error(ws, error):
                self.connection_errors.append(f"WebSocket error: {str(error)}")

            def on_close(ws, close_status_code, close_msg):
                self.is_connected = False

            # 模拟连接成功
            self.is_connected = True
            return True

        except Exception as e:
            self.connection_errors.append(f"WebSocket connection error: {str(e)}")
            return False

    async def fetch_market_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取市场数据"""
        if not self.is_connected:
            raise ConnectionError("Not connected to data source")

        market_data = []

        for symbol in symbols:
            # 模拟真实市场数据
            data = {
                "symbol": symbol,
                "price": 50.0 + (hash(symbol) % 1000) / 10.0,
                "volume": 1000000 + (hash(symbol) % 5000000),
                "change_24h": ((hash(symbol) % 200) - 100) / 1000.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bid": 49.95 + (hash(symbol) % 1000) / 10.0,
                "ask": 50.05 + (hash(symbol) % 1000) / 10.0,
                "high_24h": 52.0 + (hash(symbol) % 1000) / 10.0,
                "low_24h": 48.0 + (hash(symbol) % 1000) / 10.0,
                "market_cap": 100000000 + (hash(symbol) % 500000000),
                "technical_indicators": {
                    "rsi": (hash(symbol + "rsi") % 100),
                    "macd": ((hash(symbol + "macd") % 200) - 100) / 100.0,
                    "volatility": (hash(symbol + "vol") % 50) / 100.0,
                },
            }
            market_data.append(data)

        return market_data

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        if self.api_session:
            self.api_session.close()
        if self.websocket_client:
            self.websocket_client.close()


class SecurityValidator:
    """安全性验证器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.security_issues = []
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)

    def validate_api_authentication(
        self, api_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """验证API认证"""
        issues = []

        # 检查API密钥是否存在
        if "api_key" not in api_config or not api_config["api_key"]:
            issues.append("API密钥缺失")

        # 检查API密钥强度
        if "api_key" in api_config:
            api_key = api_config["api_key"]
            if len(api_key) < 32:
                issues.append("API密钥长度不足")
            if api_key.isalnum() and api_key.islower():
                issues.append("API密钥复杂度不足")

        # 检查密钥存储安全性
        if "secret_key" in api_config:
            secret_key = api_config["secret_key"]
            if secret_key == api_config.get("api_key"):
                issues.append("API密钥和密钥相同")

        return len(issues) == 0, issues

    def validate_data_encryption(self, sensitive_data: str) -> Tuple[bool, str]:
        """验证数据加密"""
        try:
            # 加密数据
            encrypted_data = self.cipher_suite.encrypt(sensitive_data.encode())

            # 解密验证
            decrypted_data = self.cipher_suite.decrypt(encrypted_data).decode()

            return decrypted_data == sensitive_data, encrypted_data.decode("latin-1")

        except Exception as e:
            self.security_issues.append(f"数据加密失败: {str(e)}")
            return False, ""

    def validate_network_security(self, endpoints: List[str]) -> Dict[str, bool]:
        """验证网络安全"""
        results = {}

        for endpoint in endpoints:
            try:
                parsed_url = urlparse(endpoint)

                # 检查HTTPS
                is_https = parsed_url.scheme == "https"

                # 检查SSL证书（模拟）
                ssl_valid = True
                if is_https:
                    try:
                        context = ssl.create_default_context()
                        with socket.create_connection(
                            (parsed_url.hostname, parsed_url.port or 443), timeout=10
                        ) as sock:
                            with context.wrap_socket(
                                sock, server_hostname=parsed_url.hostname
                            ) as ssock:
                                ssl_valid = True
                    except Exception:
                        ssl_valid = False

                results[endpoint] = is_https and ssl_valid

            except Exception as e:
                self.security_issues.append(f"网络安全验证失败 {endpoint}: {str(e)}")
                results[endpoint] = False

        return results

    def validate_access_control(
        self, user_roles: List[str], required_permissions: List[str]
    ) -> bool:
        """验证访问控制"""
        # 模拟角色权限映射
        role_permissions = {
            "admin": ["read", "write", "delete", "configure", "monitor"],
            "operator": ["read", "write", "monitor"],
            "viewer": ["read", "monitor"],
            "guest": ["read"],
        }

        user_permissions = set()
        for role in user_roles:
            if role in role_permissions:
                user_permissions.update(role_permissions[role])

        return all(perm in user_permissions for perm in required_permissions)

    def generate_security_report(self) -> Dict[str, Any]:
        """生成安全报告"""
        return {
            "security_issues": self.security_issues,
            "total_issues": len(self.security_issues),
            "security_score": max(0, 100 - len(self.security_issues) * 10),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class MonitoringSystem:
    """监控系统"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = {}
        self.alerts = []
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "error_rate": 0.05,
            "response_time": 5.0,
            "disk_usage": 90.0,
        }
        self.is_monitoring = False

    def start_monitoring(self):
        """开始监控"""
        self.is_monitoring = True
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "error_count": 0,
            "request_count": 0,
            "response_times": [],
            "disk_usage": [],
        }

    def record_metric(self, metric_name: str, value: float):
        """记录指标"""
        if not self.is_monitoring:
            return

        if metric_name in self.metrics:
            if isinstance(self.metrics[metric_name], list):
                self.metrics[metric_name].append(value)
            else:
                self.metrics[metric_name] = value

        # 检查阈值
        self._check_thresholds(metric_name, value)

    def _check_thresholds(self, metric_name: str, value: float):
        """检查阈值"""
        if metric_name in self.thresholds:
            threshold = self.thresholds[metric_name]

            if value > threshold:
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "severity": "high" if value > threshold * 1.2 else "medium",
                }
                self.alerts.append(alert)

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        summary = {
            "monitoring_duration": time.time()
            - (self.metrics.get("start_time", time.time())),
            "total_alerts": len(self.alerts),
            "high_severity_alerts": len(
                [a for a in self.alerts if a["severity"] == "high"]
            ),
            "metrics_summary": {},
        }

        for metric_name, values in self.metrics.items():
            if isinstance(values, list) and values:
                summary["metrics_summary"][metric_name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "max": max(values),
                    "min": min(values),
                }
            elif not isinstance(values, list):
                summary["metrics_summary"][metric_name] = values

        return summary

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False


class TestProductionValidation:
    """生产环境验证测试类"""

    @pytest.fixture
    def production_config(self):
        """生产环境配置"""
        return {
            "environments": {
                "development": {
                    "redis": {"host": "localhost", "port": 6379, "db": 0},
                    "zmq": {"pub_port": 5561, "rep_port": 5562},
                    "api": {"base_url": "http://localhost:8000", "timeout": 30},
                },
                "staging": {
                    "redis": {"host": "staging-redis", "port": 6379, "db": 1},
                    "zmq": {"pub_port": 5563, "rep_port": 5564},
                    "api": {
                        "base_url": "https://staging-api.example.com",
                        "timeout": 30,
                    },
                },
                "production": {
                    "redis": {"host": "prod-redis", "port": 6379, "db": 2},
                    "zmq": {"pub_port": 5565, "rep_port": 5566},
                    "api": {"base_url": "https://api.example.com", "timeout": 30},
                },
            },
            "security": {
                "api_key": "test_api_key_12345678901234567890",
                "secret_key": "test_secret_key_09876543210987654321",
                "encryption_enabled": True,
                "ssl_verify": True,
            },
            "monitoring": {"enabled": True, "interval": 10, "retention_days": 30},
            "data_sources": {
                "binance": {
                    "api_url": "https://api.binance.com",
                    "websocket_url": "wss://stream.binance.com:9443",
                    "rate_limit": 1200,
                },
                "coinbase": {
                    "api_url": "https://api.pro.coinbase.com",
                    "websocket_url": "wss://ws-feed.pro.coinbase.com",
                    "rate_limit": 10,
                },
            },
        }

    @pytest.mark.production
    @pytest.mark.asyncio
    async def test_real_data_source_integration(self, production_config):
        """测试真实数据源集成"""
        test_result = ProductionTestResult(
            test_name="real_data_source_integration",
            environment="production",
            start_time=time.time(),
            end_time=0,
            success=False,
            error_message=None,
            metrics={},
            security_score=0,
            performance_score=0,
            reliability_score=0,
        )

        try:
            # 测试币安API集成
            binance_simulator = RealDataSourceSimulator(
                production_config["data_sources"]["binance"]
            )

            # 连接测试
            api_connected = await binance_simulator.connect_to_binance_api()
            ws_connected = await binance_simulator.connect_to_websocket_stream()

            assert api_connected, f"币安API连接失败: {binance_simulator.connection_errors}"
            assert (
                ws_connected
            ), f"币安WebSocket连接失败: {binance_simulator.connection_errors}"

            # 数据获取测试
            test_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
            market_data = await binance_simulator.fetch_market_data(test_symbols)

            assert len(market_data) == len(test_symbols), "市场数据数量不匹配"

            # 验证数据质量
            for data in market_data:
                assert "symbol" in data, "缺少交易对信息"
                assert "price" in data and data["price"] > 0, "价格数据无效"
                assert "volume" in data and data["volume"] > 0, "成交量数据无效"
                assert "timestamp" in data, "缺少时间戳"
                assert "technical_indicators" in data, "缺少技术指标"

            # 数据处理测试
            data_processor = DataProcessor(Mock())

            processed_count = 0
            for data in market_data:
                try:
                    processed_data = await data_processor.process_market_data(data)
                    assert processed_data is not None, "数据处理失败"
                    processed_count += 1
                except Exception as e:
                    test_result.error_message = f"数据处理错误: {str(e)}"

            # 性能指标
            processing_rate = processed_count / len(market_data)

            test_result.metrics = {
                "api_connected": api_connected,
                "websocket_connected": ws_connected,
                "symbols_tested": len(test_symbols),
                "data_received": len(market_data),
                "processing_rate": processing_rate,
                "connection_errors": len(binance_simulator.connection_errors),
            }

            test_result.performance_score = processing_rate * 100
            test_result.reliability_score = (
                100 - len(binance_simulator.connection_errors) * 10
            )
            test_result.success = (
                processing_rate > 0.8 and len(binance_simulator.connection_errors) == 0
            )

            binance_simulator.disconnect()

        except Exception as e:
            test_result.error_message = str(e)
            test_result.success = False

        finally:
            test_result.end_time = time.time()

        # 断言
        assert test_result.success, f"真实数据源集成测试失败: {test_result.error_message}"
        assert (
            test_result.performance_score > 80
        ), f"性能评分过低: {test_result.performance_score}"
        assert (
            test_result.reliability_score > 90
        ), f"可靠性评分过低: {test_result.reliability_score}"

        print(f"真实数据源集成测试结果: {asdict(test_result)}")

    @pytest.mark.production
    @pytest.mark.asyncio
    async def test_multi_environment_configuration(self, production_config):
        """测试多环境配置验证"""
        env_manager = ProductionEnvironmentManager(production_config)

        try:
            # 测试各个环境配置
            environments = ["development", "staging", "production"]
            test_results = {}

            for env_name in environments:
                print(f"测试环境: {env_name}")

                # 创建环境配置
                env_config = env_manager.create_environment(
                    env_name, production_config["environments"][env_name]
                )

                with env_manager.use_environment(env_name):
                    # 验证Redis配置
                    redis_config = env_config["redis"]
                    assert "host" in redis_config, f"{env_name}: Redis主机配置缺失"
                    assert "port" in redis_config, f"{env_name}: Redis端口配置缺失"
                    assert "db" in redis_config, f"{env_name}: Redis数据库配置缺失"

                    # 验证ZMQ配置
                    zmq_config = env_config["zmq"]
                    assert "pub_port" in zmq_config, f"{env_name}: ZMQ发布端口配置缺失"
                    assert "rep_port" in zmq_config, f"{env_name}: ZMQ响应端口配置缺失"

                    # 验证API配置
                    api_config = env_config["api"]
                    assert "base_url" in api_config, f"{env_name}: API基础URL配置缺失"
                    assert "timeout" in api_config, f"{env_name}: API超时配置缺失"

                    # 环境特定验证
                    if env_name == "production":
                        assert api_config["base_url"].startswith(
                            "https://"
                        ), "生产环境必须使用HTTPS"
                        assert api_config["timeout"] >= 30, "生产环境超时时间应该更长"

                    # 模拟组件初始化
                    try:
                        # 创建模拟组件
                        mock_redis = Mock(spec=RedisClient)
                        mock_zmq = Mock(spec=ScannerZMQClient)

                        # 验证组件配置
                        three_high_engine = ThreeHighEngine(
                            mock_redis, {"price_threshold": 100}
                        )
                        assert (
                            three_high_engine is not None
                        ), f"{env_name}: ThreeHighEngine初始化失败"

                        test_results[env_name] = {
                            "config_valid": True,
                            "components_initialized": True,
                            "environment_score": 100,
                        }

                    except Exception as e:
                        test_results[env_name] = {
                            "config_valid": False,
                            "components_initialized": False,
                            "environment_score": 0,
                            "error": str(e),
                        }

            # 验证环境隔离
            dev_config = env_manager.environments["development"]
            prod_config = env_manager.environments["production"]

            assert (
                dev_config["redis"]["db"] != prod_config["redis"]["db"]
            ), "开发和生产环境Redis数据库应该隔离"
            assert (
                dev_config["zmq"]["pub_port"] != prod_config["zmq"]["pub_port"]
            ), "开发和生产环境ZMQ端口应该隔离"

            # 断言所有环境配置有效
            for env_name, result in test_results.items():
                assert result[
                    "config_valid"
                ], f"{env_name}环境配置无效: {result.get('error', '')}"
                assert result["components_initialized"], f"{env_name}环境组件初始化失败"
                assert (
                    result["environment_score"] == 100
                ), f"{env_name}环境评分: {result['environment_score']}"

            print(f"多环境配置验证结果: {test_results}")

        finally:
            env_manager.cleanup()

    @pytest.mark.production
    @pytest.mark.asyncio
    async def test_security_and_permissions(self, production_config):
        """测试安全性和权限"""
        security_validator = SecurityValidator(production_config["security"])

        # API认证验证
        auth_valid, auth_issues = security_validator.validate_api_authentication(
            production_config["security"]
        )

        assert auth_valid, f"API认证验证失败: {auth_issues}"

        # 数据加密验证
        sensitive_data = "sensitive_trading_data_12345"
        encryption_valid, encrypted_data = security_validator.validate_data_encryption(
            sensitive_data
        )

        assert encryption_valid, "数据加密验证失败"
        assert encrypted_data != sensitive_data, "数据未被正确加密"

        # 网络安全验证
        test_endpoints = [
            "https://api.binance.com/api/v3/ping",
            "https://api.example.com/health",
            "http://localhost:8000/status",  # 本地开发环境可以使用HTTP
        ]

        network_security = security_validator.validate_network_security(test_endpoints)

        # 生产环境端点必须使用HTTPS
        for endpoint, is_secure in network_security.items():
            if "localhost" not in endpoint and "example.com" not in endpoint:
                assert is_secure, f"生产环境端点必须安全: {endpoint}"

        # 访问控制验证
        test_cases = [
            (["admin"], ["read", "write", "delete"], True),
            (["operator"], ["read", "write"], True),
            (["viewer"], ["read"], True),
            (["guest"], ["write"], False),
            (["viewer"], ["delete"], False),
        ]

        for user_roles, required_perms, expected in test_cases:
            result = security_validator.validate_access_control(
                user_roles, required_perms
            )
            assert result == expected, f"访问控制验证失败: {user_roles} -> {required_perms}"

        # 生成安全报告
        security_report = security_validator.generate_security_report()

        assert (
            security_report["security_score"] > 80
        ), f"安全评分过低: {security_report['security_score']}"
        assert (
            security_report["total_issues"] < 3
        ), f"安全问题过多: {security_report['total_issues']}"

        print(f"安全性和权限测试结果: {security_report}")

    @pytest.mark.production
    @pytest.mark.asyncio
    async def test_monitoring_and_alerting(self, production_config):
        """测试监控和告警功能"""
        monitoring_system = MonitoringSystem(production_config["monitoring"])

        # 开始监控
        monitoring_system.start_monitoring()

        try:
            # 模拟正常运行指标
            for i in range(10):
                monitoring_system.record_metric("cpu_usage", 50.0 + i * 2)
                monitoring_system.record_metric("memory_usage", 60.0 + i * 1.5)
                monitoring_system.record_metric("response_time", 1.0 + i * 0.1)
                monitoring_system.record_metric("disk_usage", 70.0 + i * 0.5)
                await asyncio.sleep(0.1)

            # 模拟异常指标触发告警
            monitoring_system.record_metric("cpu_usage", 95.0)  # 超过阈值
            monitoring_system.record_metric("memory_usage", 90.0)  # 超过阈值
            monitoring_system.record_metric("response_time", 8.0)  # 超过阈值

            # 模拟错误计数
            for i in range(5):
                monitoring_system.record_metric("error_count", i + 1)
                monitoring_system.record_metric("request_count", (i + 1) * 100)

            # 获取监控摘要
            summary = monitoring_system.get_monitoring_summary()

            # 验证监控功能
            assert (
                len(monitoring_system.alerts) >= 3
            ), f"告警数量不足: {len(monitoring_system.alerts)}"
            assert summary["total_alerts"] >= 3, "告警统计不正确"
            assert summary["high_severity_alerts"] >= 1, "高严重性告警不足"

            # 验证指标收集
            assert "cpu_usage" in summary["metrics_summary"], "CPU使用率指标缺失"
            assert "memory_usage" in summary["metrics_summary"], "内存使用率指标缺失"
            assert "response_time" in summary["metrics_summary"], "响应时间指标缺失"

            # 验证告警内容
            cpu_alerts = [
                a for a in monitoring_system.alerts if a["metric"] == "cpu_usage"
            ]
            assert len(cpu_alerts) > 0, "CPU告警缺失"
            assert cpu_alerts[0]["value"] == 95.0, "CPU告警值不正确"
            assert cpu_alerts[0]["severity"] in ["medium", "high"], "CPU告警严重性不正确"

            # 验证指标统计
            cpu_stats = summary["metrics_summary"]["cpu_usage"]
            assert cpu_stats["max"] == 95.0, "CPU最大值统计不正确"
            assert cpu_stats["count"] >= 10, "CPU指标数量不足"

            print(f"监控和告警测试结果: {summary}")
            print(f"告警详情: {monitoring_system.alerts}")

        finally:
            monitoring_system.stop_monitoring()

        # 断言监控系统正常工作
        assert not monitoring_system.is_monitoring, "监控系统未正确停止"
        assert len(monitoring_system.alerts) > 0, "未产生任何告警"
        assert summary["metrics_summary"], "未收集到任何指标"

    @pytest.mark.production
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_end_to_end_production_workflow(self, production_config):
        """测试端到端生产工作流"""
        # 综合测试：数据源 -> 处理 -> 存储 -> 监控 -> 告警

        # 1. 环境设置
        env_manager = ProductionEnvironmentManager(production_config)
        prod_env = env_manager.create_environment(
            "production", production_config["environments"]["production"]
        )

        # 2. 安全验证
        security_validator = SecurityValidator(production_config["security"])
        auth_valid, _ = security_validator.validate_api_authentication(
            production_config["security"]
        )
        assert auth_valid, "生产环境安全验证失败"

        # 3. 监控启动
        monitoring_system = MonitoringSystem(production_config["monitoring"])
        monitoring_system.start_monitoring()

        # 4. 数据源连接
        data_source = RealDataSourceSimulator(
            production_config["data_sources"]["binance"]
        )
        api_connected = await data_source.connect_to_binance_api()
        ws_connected = await data_source.connect_to_websocket_stream()

        assert api_connected and ws_connected, "生产数据源连接失败"

        try:
            with env_manager.use_environment("production"):
                # 5. 组件初始化
                mock_redis = Mock(spec=RedisClient)
                mock_redis.get_historical_data = AsyncMock(return_value=[])
                mock_redis.set_scan_result = AsyncMock(return_value=True)

                mock_zmq = Mock(spec=ScannerZMQClient)
                mock_zmq.publish_scan_result = AsyncMock()

                three_high_engine = ThreeHighEngine(
                    mock_redis, prod_env["scanner"]["rules"]["three_high"]
                )
                black_horse_detector = BlackHorseDetector(
                    mock_redis, prod_env["scanner"]["rules"]["black_horse"]
                )
                potential_finder = PotentialFinder(
                    mock_redis, prod_env["scanner"]["rules"]["potential_finder"]
                )

                # 6. 数据处理工作流
                test_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
                market_data = await data_source.fetch_market_data(test_symbols)

                processed_results = []
                for data in market_data:
                    start_time = time.time()

                    try:
                        # 三高引擎分析
                        three_high_result = await three_high_engine.analyze(
                            data["symbol"], data
                        )

                        # 黑马检测
                        black_horse_result = await black_horse_detector.detect(
                            data["symbol"], data
                        )

                        # 潜力挖掘
                        potential_result = await potential_finder.find_potential(
                            data["symbol"], data
                        )

                        # 记录处理时间
                        processing_time = time.time() - start_time
                        monitoring_system.record_metric(
                            "response_time", processing_time
                        )

                        # 模拟存储结果
                        result = {
                            "symbol": data["symbol"],
                            "three_high": three_high_result,
                            "black_horse": black_horse_result,
                            "potential": potential_result,
                            "processing_time": processing_time,
                        }
                        processed_results.append(result)

                        # 发布结果
                        await mock_zmq.publish_scan_result(result)

                        # 记录成功指标
                        monitoring_system.record_metric(
                            "request_count", len(processed_results)
                        )

                    except Exception as e:
                        monitoring_system.record_metric("error_count", 1)
                        print(f"处理错误: {data['symbol']} - {str(e)}")

                # 7. 性能验证
                avg_processing_time = sum(
                    r["processing_time"] for r in processed_results
                ) / len(processed_results)
                success_rate = len(processed_results) / len(market_data)

                monitoring_system.record_metric("cpu_usage", 75.0)
                monitoring_system.record_metric("memory_usage", 80.0)

                # 8. 获取最终监控摘要
                final_summary = monitoring_system.get_monitoring_summary()

                # 9. 生产环境断言
                assert success_rate >= 0.95, f"生产环境成功率过低: {success_rate:.2%}"
                assert (
                    avg_processing_time < 2.0
                ), f"生产环境处理时间过长: {avg_processing_time:.2f}s"
                assert len(processed_results) == len(test_symbols), "生产环境数据处理不完整"

                # 验证所有组件调用
                assert mock_redis.set_scan_result.call_count >= len(
                    processed_results
                ), "Redis存储调用不足"
                assert mock_zmq.publish_scan_result.call_count >= len(
                    processed_results
                ), "ZMQ发布调用不足"

                print(f"端到端生产工作流测试结果:")
                print(f"  - 处理成功率: {success_rate:.2%}")
                print(f"  - 平均处理时间: {avg_processing_time:.2f}s")
                print(f"  - 监控摘要: {final_summary}")

        finally:
            data_source.disconnect()
            monitoring_system.stop_monitoring()
            env_manager.cleanup()


if __name__ == "__main__":
    # 运行生产环境验证测试
    pytest.main([__file__, "-v", "-m", "production", "--tb=short"])
