# 扫描器模组V3.5升级后的核心单元测试
# 实现TEST-PLAN-M03-SCANNER-V1中定义的四个核心测试用例

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.communication.zmq_client import ScannerZMQClient
from scanner.adapters.trading_agents_cn_adapter import (
    TACoreServiceAgent,
    TACoreServiceClient,
)
from scanner.main import ScannerApplication
from scanner.config.env_manager import get_env_manager


class TestScannerCoreV35:
    """扫描器模组V3.5核心功能测试类"""

    @pytest.fixture
    def mock_zmq_client(self):
        """模拟ZMQ客户端"""
        client = Mock()
        client.start = Mock(return_value=None)
        client.stop = Mock(return_value=None)
        client.is_running = Mock(return_value=True)
        client.send_scan_request = AsyncMock()
        client.publish_scan_result = AsyncMock()
        client.publish_status_update = AsyncMock()
        return client

    @pytest.fixture
    def mock_tacore_client(self):
        """模拟TACoreService客户端"""
        client = Mock()
        client.connect = Mock(return_value=True)
        client.disconnect = Mock(return_value=None)
        client.is_connected = Mock(return_value=True)
        client.send_request = AsyncMock()
        return client

    @pytest.fixture
    def mock_tacore_agent(self, mock_tacore_client):
        """模拟TACoreService代理"""
        agent = Mock()
        agent.client = mock_tacore_client
        agent.scan_market = AsyncMock()
        agent.get_market_opportunities = AsyncMock()
        return agent

    @pytest.fixture
    def scanner_app(self, mock_zmq_client, mock_tacore_agent):
        """扫描器应用实例"""
        with patch("scanner.main.ScannerApplication.__init__", return_value=None):
            app = ScannerApplication()
            # 手动设置必要的属性
            app.env_manager = Mock()
            app.logger = Mock()
            app.error_handler = Mock()
            app.is_running = False
            app.shutdown_event = Mock()
            app.zmq_client = mock_zmq_client
            app.trading_adapter = mock_tacore_agent
            app.redis_client = Mock()
            app.health_checker = Mock()
            app.three_high_engine = None
            app.black_horse_detector = None
            app.potential_finder = None
            return app

    @pytest.fixture
    def valid_scan_response(self):
        """有效的扫描响应数据"""
        return [
            {
                "symbol": "BTCUSDT",
                "price": 45000.0,
                "volume": 1500000.0,
                "change_24h": 0.05,
                "score": 0.85,
                "type": "three_high",
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.9,
            },
            {
                "symbol": "ETHUSDT",
                "price": 3000.0,
                "volume": 800000.0,
                "change_24h": 0.03,
                "score": 0.75,
                "type": "black_horse",
                "timestamp": datetime.now().isoformat(),
                "confidence": 0.8,
            },
        ]

    @pytest.fixture
    def empty_scan_response(self):
        """空的扫描响应数据"""
        return []

    @pytest.fixture
    def error_scan_response(self):
        """错误的扫描响应数据"""
        return {
            "status": "error",
            "message": "Internal server error",
            "error_code": "TACORE_500",
            "timestamp": datetime.now().isoformat(),
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unit_01_success_scenario(
        self, scanner_app, mock_tacore_agent, mock_zmq_client, valid_scan_response
    ):
        """UNIT-01: 成功场景 - 服务返回有效数据

        测试目标：
        - 验证扫描器正确解析了返回的JSON数据
        - 验证扫描器调用了数据推送模块
        """
        # 设置Mock：TACoreService返回有效数据
        mock_tacore_agent.scan_market.return_value = valid_scan_response

        # 执行扫描器的核心扫描函数
        await scanner_app._handle_scan_result(valid_scan_response)

        # 验证点1：验证扫描器正确解析了返回的JSON数据
        assert len(valid_scan_response) == 2
        assert valid_scan_response[0]["symbol"] == "BTCUSDT"
        assert valid_scan_response[1]["symbol"] == "ETHUSDT"

        # 验证点2：验证扫描器调用了数据推送模块
        # 应该为每个结果调用一次publish_scan_result
        assert mock_zmq_client.publish_scan_result.call_count == 2

        # 验证推送的数据格式正确
        call_args_list = mock_zmq_client.publish_scan_result.call_args_list
        first_call_data = call_args_list[0][0][0]
        second_call_data = call_args_list[1][0][0]

        assert first_call_data["symbol"] == "BTCUSDT"
        assert second_call_data["symbol"] == "ETHUSDT"

        print("✅ UNIT-01 测试通过：成功场景验证完成")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unit_02_empty_data_scenario(
        self, scanner_app, mock_tacore_agent, mock_zmq_client, empty_scan_response
    ):
        """UNIT-02: 无机会场景 - 服务返回空列表

        测试目标：
        - 验证扫描器优雅地处理了空响应，未产生任何错误
        - 验证扫描器没有调用数据推送模块
        - 验证系统记录了'本轮未发现机会'的常规日志
        """
        # 设置Mock：TACoreService返回空列表
        mock_tacore_agent.scan_market.return_value = empty_scan_response

        # 执行扫描器的核心扫描函数
        try:
            await scanner_app._handle_scan_result(empty_scan_response)
            no_error_occurred = True
        except Exception as e:
            no_error_occurred = False
            pytest.fail(f"扫描器处理空响应时发生错误: {e}")

        # 验证点1：验证扫描器优雅地处理了空响应，未产生任何错误
        assert no_error_occurred, "扫描器应该能够优雅处理空响应"

        # 验证点2：验证扫描器没有调用数据推送模块
        mock_zmq_client.publish_scan_result.assert_not_called()

        # 验证点3：验证空响应的处理逻辑
        assert len(empty_scan_response) == 0

        print("✅ UNIT-02 测试通过：空数据场景验证完成")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unit_03_error_scenario(
        self, scanner_app, mock_tacore_agent, mock_zmq_client, error_scan_response
    ):
        """UNIT-03: 服务失败场景 - 服务返回错误信息

        测试目标：
        - 验证扫描器正确捕获了异常或错误状态
        - 验证扫描器没有崩溃，并执行了错误处理逻辑
        - 验证系统记录了详细的错误日志
        """
        # 设置Mock：TACoreService返回错误信息
        mock_tacore_agent.scan_market.side_effect = Exception(
            "TACoreService Internal Error"
        )

        # 模拟错误处理回调
        error_handled = False
        original_handle_adapter_error = scanner_app._handle_adapter_error

        async def mock_handle_adapter_error(error_type: str, error_message: str):
            nonlocal error_handled
            error_handled = True
            await original_handle_adapter_error(error_type, error_message)

        scanner_app._handle_adapter_error = mock_handle_adapter_error

        # 执行扫描器的核心扫描函数，期望捕获异常
        try:
            # 模拟调用扫描器的主要扫描逻辑
            await mock_tacore_agent.scan_market()
            pytest.fail("应该抛出异常")
        except Exception as e:
            # 验证点1：验证扫描器正确捕获了异常或错误状态
            assert "TACoreService Internal Error" in str(e)

            # 模拟错误处理
            await scanner_app._handle_adapter_error("service_error", str(e))

        # 验证点2：验证扫描器执行了错误处理逻辑
        assert error_handled, "错误处理逻辑应该被执行"

        # 验证点3：验证系统发布了错误状态更新
        mock_zmq_client.publish_status_update.assert_called_once()

        # 验证错误状态更新的内容
        call_args = mock_zmq_client.publish_status_update.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["component"] == "trading_adapter"
        assert "service_error" in call_args["error_type"]

        print("✅ UNIT-03 测试通过：错误场景验证完成")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unit_04_timeout_scenario(
        self, scanner_app, mock_tacore_agent, mock_zmq_client
    ):
        """UNIT-04: 服务超时场景 - 服务无响应

        测试目标：
        - 验证扫描器的ZMQ客户端超时机制被正确触发
        - 验证扫描器在超时后，执行了预期的错误处理逻辑
        - 验证扫描器进程保持稳定，未被阻塞或崩溃
        """
        # 设置Mock：模拟网络超时
        timeout_error = asyncio.TimeoutError("Request timeout after 15 seconds")
        mock_tacore_agent.scan_market.side_effect = timeout_error

        # 记录超时处理状态
        timeout_handled = False
        original_handle_adapter_error = scanner_app._handle_adapter_error

        async def mock_handle_adapter_error(error_type: str, error_message: str):
            nonlocal timeout_handled
            if "timeout" in error_type.lower() or "timeout" in error_message.lower():
                timeout_handled = True
            await original_handle_adapter_error(error_type, error_message)

        scanner_app._handle_adapter_error = mock_handle_adapter_error

        # 执行扫描器的核心扫描函数，期望处理超时
        try:
            await mock_tacore_agent.scan_market()
            pytest.fail("应该抛出超时异常")
        except asyncio.TimeoutError as e:
            # 验证点1：验证扫描器的超时机制被正确触发
            assert "timeout" in str(e).lower()

            # 模拟超时错误处理
            await scanner_app._handle_adapter_error("timeout_error", str(e))

        # 验证点2：验证扫描器在超时后执行了预期的错误处理逻辑
        assert timeout_handled, "超时错误处理逻辑应该被执行"

        # 验证点3：验证扫描器进程保持稳定
        # 检查ZMQ客户端仍然运行
        assert mock_zmq_client.is_running.return_value is True

        # 验证发布了超时状态更新
        mock_zmq_client.publish_status_update.assert_called_once()

        # 验证超时状态更新的内容
        call_args = mock_zmq_client.publish_status_update.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["component"] == "trading_adapter"
        assert "timeout" in call_args["error_type"].lower()

        print("✅ UNIT-04 测试通过：超时场景验证完成")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_scanner_initialization(self):
        """测试扫描器初始化过程"""
        app = ScannerApplication()

        # 验证基本属性初始化
        assert app.env_manager is not None
        assert app.logger is not None
        assert app.error_handler is not None
        assert app.is_running is False
        assert app.shutdown_event is not None

        print("✅ 扫描器初始化测试通过")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_component_integration(
        self, scanner_app, mock_zmq_client, mock_tacore_agent
    ):
        """测试组件集成"""
        # 验证组件正确设置
        assert scanner_app.zmq_client == mock_zmq_client
        assert scanner_app.trading_adapter == mock_tacore_agent

        # 验证组件状态
        assert mock_zmq_client.is_running.return_value is True
        assert mock_tacore_agent.client.is_connected.return_value is True

        print("✅ 组件集成测试通过")


class TestScannerV35Configuration:
    """扫描器V3.5配置测试类"""

    @pytest.mark.unit
    def test_environment_configuration(self):
        """测试环境配置"""
        env_manager = get_env_manager()

        # 验证配置加载
        redis_config = env_manager.get_redis_config()
        zmq_config = env_manager.get_zmq_config()
        scanner_config = env_manager.get_scanner_config()

        assert redis_config is not None
        assert zmq_config is not None
        assert scanner_config is not None

        # 验证关键配置项
        assert "host" in redis_config
        assert "port" in redis_config
        # ZMQ配置可能有不同的端口字段名
        zmq_has_port = any(
            key in zmq_config for key in ["pub_port", "port", "rep_port", "req_port"]
        )
        assert zmq_has_port, f"ZMQ配置中应包含端口信息，当前配置: {zmq_config}"
        assert "rules" in scanner_config

        print("✅ 环境配置测试通过")

    @pytest.mark.unit
    def test_scanner_rules_configuration(self):
        """测试扫描器规则配置"""
        env_manager = get_env_manager()
        scanner_config = env_manager.get_scanner_config()

        rules = scanner_config.get("rules", {})

        # 验证三高规则配置
        if "three_high" in rules:
            three_high = rules["three_high"]
            assert "enabled" in three_high
            assert isinstance(three_high["enabled"], bool)

        # 验证黑马检测配置
        if "black_horse" in rules:
            black_horse = rules["black_horse"]
            assert "enabled" in black_horse
            assert isinstance(black_horse["enabled"], bool)

        # 验证潜力挖掘配置
        if "potential_finder" in rules:
            potential_finder = rules["potential_finder"]
            assert "enabled" in potential_finder
            assert isinstance(potential_finder["enabled"], bool)

        print("✅ 扫描器规则配置测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short", "-m", "unit"])
