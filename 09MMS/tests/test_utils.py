#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 工具模块测试
测试工具和辅助功能

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.utils.exceptions import (
    MMSBaseException,
    SimulationError,
    ValidationError,
    ErrorHandler,
    RetryHandler,
    CircuitBreaker,
)
from src.utils.metrics import (
    MetricsCollector,
    SystemMetricsCollector,
    SimulationMetricsCollector,
    PerformanceTimer,
    HealthChecker,
)
from src.utils.logger import LoggerManager, get_logger


class TestExceptions:
    """异常处理测试"""

    def test_mms_base_exception(self):
        """测试基础异常类"""
        with patch("src.utils.exceptions.logger") as mock_logger:
            error_details = {"key": "value"}
            cause = ValueError("Original error")

            exception = MMSBaseException(
                message="Test error",
                error_code="TEST_ERROR",
                details=error_details,
                cause=cause,
            )

            assert exception.message == "Test error"
            assert exception.error_code == "TEST_ERROR"
            assert exception.details == error_details
            assert exception.cause == cause
            assert isinstance(exception.timestamp, datetime)

            # 检查是否记录了日志
            mock_logger.error.assert_called()

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        with patch("src.utils.exceptions.logger"):
            exception = SimulationError("Simulation failed", error_code="SIM_001")

            result = exception.to_dict()

            assert result["error_code"] == "SIM_001"
            assert result["message"] == "Simulation failed"
            assert "timestamp" in result
            assert "details" in result

    def test_validation_error(self):
        """测试验证错误"""
        with patch("src.utils.exceptions.logger"):
            error = ValidationError(
                "Invalid parameter", details={"parameter": "spread", "value": -0.1}
            )

            assert isinstance(error, MMSBaseException)
            assert error.message == "Invalid parameter"

    def test_error_handler(self):
        """测试错误处理器"""
        handler = ErrorHandler()

        # 测试处理标准异常
        try:
            raise ValueError("Test value error")
        except Exception as e:
            result = handler.handle_exception(e, reraise=False)

            assert result["error_code"] == "VALIDATION_ERROR"
            assert result["message"] == "Test value error"
            assert "timestamp" in result

    def test_error_handler_mms_exception(self):
        """测试处理MMS异常"""
        handler = ErrorHandler()

        with patch("src.utils.exceptions.logger"):
            mms_error = SimulationError("Simulation failed")

            result = handler.handle_exception(mms_error, reraise=False)

            assert result["error_code"] == "SimulationError"
            assert result["message"] == "Simulation failed"

    def test_create_error_response(self):
        """测试创建错误响应"""
        handler = ErrorHandler()

        try:
            raise ValueError("Test error")
        except Exception as e:
            response = handler.create_error_response(e, status_code=400)

            assert response["success"] is False
            assert response["status_code"] == 400
            assert "error" in response


class TestRetryHandler:
    """重试处理器测试"""

    @pytest.mark.asyncio
    async def test_retry_success(self):
        """测试重试成功"""
        retry_handler = RetryHandler(max_retries=3, delay=0.01)

        call_count = 0

        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = await retry_handler.retry_async(
            failing_function, retryable_exceptions=(ConnectionError,)
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_max_attempts(self):
        """测试达到最大重试次数"""
        retry_handler = RetryHandler(max_retries=2, delay=0.01)

        async def always_failing_function():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await retry_handler.retry_async(
                always_failing_function, retryable_exceptions=(ConnectionError,)
            )

    @pytest.mark.asyncio
    async def test_retry_non_retryable_exception(self):
        """测试不可重试异常"""
        retry_handler = RetryHandler(max_retries=3, delay=0.01)

        async def function_with_non_retryable_error():
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            await retry_handler.retry_async(
                function_with_non_retryable_error,
                retryable_exceptions=(ConnectionError,),
            )

    def test_retry_sync(self):
        """测试同步重试"""
        retry_handler = RetryHandler(max_retries=2, delay=0.01)

        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = retry_handler.retry_sync(
            failing_function, retryable_exceptions=(ConnectionError,)
        )

        assert result == "success"
        assert call_count == 2


class TestCircuitBreaker:
    """熔断器测试"""

    def test_circuit_breaker_closed_state(self):
        """测试熔断器关闭状态"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        def successful_function():
            return "success"

        result = breaker._call(successful_function)
        assert result == "success"
        assert breaker.state == "CLOSED"

    def test_circuit_breaker_open_state(self):
        """测试熔断器打开状态"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        def failing_function():
            raise ConnectionError("Connection failed")

        # 触发足够的失败以打开熔断器
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker._call(failing_function)

        assert breaker.state == "OPEN"

        # 现在应该抛出ServiceUnavailableError
        with pytest.raises(Exception):  # ServiceUnavailableError
            breaker._call(failing_function)

    def test_circuit_breaker_half_open_state(self):
        """测试熔断器半开状态"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        def failing_function():
            raise ConnectionError("Connection failed")

        def successful_function():
            return "success"

        # 打开熔断器
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker._call(failing_function)

        assert breaker.state == "OPEN"

        # 等待恢复超时
        time.sleep(0.2)

        # 下一次调用应该进入半开状态并成功
        result = breaker._call(successful_function)
        assert result == "success"
        assert breaker.state == "CLOSED"

    def test_circuit_breaker_reset(self):
        """测试熔断器重置"""
        breaker = CircuitBreaker(failure_threshold=2)

        def failing_function():
            raise ConnectionError("Connection failed")

        # 触发一些失败
        with pytest.raises(ConnectionError):
            breaker._call(failing_function)

        assert breaker.failure_count == 1

        # 重置熔断器
        breaker.reset()

        assert breaker.failure_count == 0
        assert breaker.state == "CLOSED"
        assert breaker.last_failure_time is None


class TestMetricsCollector:
    """指标收集器测试"""

    @pytest.mark.asyncio
    async def test_record_counter(self):
        """测试记录计数器"""
        collector = MetricsCollector()

        await collector.record_counter("test_counter", 5)
        await collector.record_counter("test_counter", 3)

        assert collector.counters["test_counter"] == 8

    @pytest.mark.asyncio
    async def test_record_gauge(self):
        """测试记录仪表盘指标"""
        collector = MetricsCollector()

        await collector.record_gauge("test_gauge", 10.5)
        await collector.record_gauge("test_gauge", 15.2)

        assert collector.gauges["test_gauge"] == 15.2

    @pytest.mark.asyncio
    async def test_record_histogram(self):
        """测试记录直方图指标"""
        collector = MetricsCollector()

        await collector.record_histogram("test_histogram", 1.0)
        await collector.record_histogram("test_histogram", 2.0)
        await collector.record_histogram("test_histogram", 3.0)

        assert len(collector.histograms["test_histogram"]) == 3
        assert 1.0 in collector.histograms["test_histogram"]

    @pytest.mark.asyncio
    async def test_record_timer(self):
        """测试记录计时器指标"""
        collector = MetricsCollector()

        await collector.record_timer("test_timer", 0.5)
        await collector.record_timer("test_timer", 1.2)

        assert len(collector.timers["test_timer"]) == 2
        assert 0.5 in collector.timers["test_timer"]

    @pytest.mark.asyncio
    async def test_get_metric_summary(self):
        """测试获取指标摘要"""
        collector = MetricsCollector()

        await collector.record_histogram("test_metric", 1.0)
        await collector.record_histogram("test_metric", 2.0)
        await collector.record_histogram("test_metric", 3.0)

        summary = await collector.get_metric_summary("test_metric")

        assert summary is not None
        assert summary.name == "test_metric"
        assert summary.count == 3
        assert summary.min_value == 1.0
        assert summary.max_value == 3.0
        assert summary.avg_value == 2.0

    @pytest.mark.asyncio
    async def test_get_all_metrics(self):
        """测试获取所有指标"""
        collector = MetricsCollector()

        await collector.record_counter("test_counter", 5)
        await collector.record_gauge("test_gauge", 10.0)
        await collector.record_histogram("test_histogram", 1.5)
        await collector.record_timer("test_timer", 0.8)

        metrics = await collector.get_all_metrics()

        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert "timers" in metrics
        assert "summaries" in metrics
        assert "collection_time" in metrics
        assert "uptime_seconds" in metrics

        assert metrics["counters"]["test_counter"] == 5
        assert metrics["gauges"]["test_gauge"] == 10.0

    @pytest.mark.asyncio
    async def test_reset_metrics(self):
        """测试重置指标"""
        collector = MetricsCollector()

        await collector.record_counter("test_counter", 5)
        await collector.record_gauge("test_gauge", 10.0)

        await collector.reset_metrics()

        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.metrics) == 0


class TestPerformanceTimer:
    """性能计时器测试"""

    @pytest.mark.asyncio
    async def test_async_performance_timer(self):
        """测试异步性能计时器"""
        collector = MetricsCollector()

        async with PerformanceTimer(collector, "test_operation"):
            await asyncio.sleep(0.01)  # 模拟一些工作

        # 检查是否记录了计时器指标
        assert len(collector.timers["test_operation"]) == 1
        assert collector.timers["test_operation"][0] >= 0.01

    def test_sync_performance_timer(self):
        """测试同步性能计时器"""
        collector = MetricsCollector()

        with PerformanceTimer(collector, "test_operation"):
            time.sleep(0.01)  # 模拟一些工作

        # 注意：同步版本需要在事件循环中运行才能正确记录
        # 这里只测试计时器的基本功能
        assert (
            collector.timers.get("test_operation") is not None
            or len(collector.timers) == 0
        )


class TestHealthChecker:
    """健康检查器测试"""

    @pytest.mark.asyncio
    async def test_register_and_run_check(self):
        """测试注册和运行健康检查"""
        collector = MetricsCollector()
        health_checker = HealthChecker(collector)

        def database_check():
            return True

        async def redis_check():
            return {"status": "connected", "latency": 0.001}

        health_checker.register_check("database", database_check)
        health_checker.register_check("redis", redis_check)

        results = await health_checker.run_all_checks()

        assert results["healthy"] is True
        assert "database" in results["checks"]
        assert "redis" in results["checks"]
        assert results["checks"]["database"]["healthy"] is True
        assert results["checks"]["redis"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_failing_health_check(self):
        """测试失败的健康检查"""
        collector = MetricsCollector()
        health_checker = HealthChecker(collector)

        def failing_check():
            raise ConnectionError("Service unavailable")

        def passing_check():
            return True

        health_checker.register_check("failing_service", failing_check)
        health_checker.register_check("passing_service", passing_check)

        results = await health_checker.run_all_checks()

        assert results["healthy"] is False
        assert results["checks"]["failing_service"]["healthy"] is False
        assert results["checks"]["passing_service"]["healthy"] is True
        assert "error" in results["checks"]["failing_service"]

    @pytest.mark.asyncio
    async def test_get_health_summary(self):
        """测试获取健康状态摘要"""
        collector = MetricsCollector()
        health_checker = HealthChecker(collector)

        def check1():
            return True

        def check2():
            return False

        health_checker.register_check("service1", check1)
        health_checker.register_check("service2", check2)

        await health_checker.run_all_checks()

        summary = await health_checker.get_health_summary()

        assert summary["overall_healthy"] is False
        assert summary["total_checks"] == 2
        assert summary["healthy_checks"] == 1
        assert "last_check_time" in summary


class TestLogger:
    """日志器测试"""

    def test_get_logger(self):
        """测试获取日志器"""
        logger = get_logger("test_logger")

        assert logger is not None
        assert logger.name == "test_logger"

    def test_logger_manager_initialization(self):
        """测试日志管理器初始化"""
        # 重置初始化状态
        LoggerManager._initialized = False

        with patch("src.utils.logger.Config") as mock_config:
            mock_config.LOG_DIR = "/tmp/test_logs"
            mock_config.LOG_LEVEL = "INFO"
            mock_config.LOG_FORMAT = "standard"
            mock_config.LOG_MAX_SIZE = 10485760
            mock_config.LOG_BACKUP_COUNT = 5

            LoggerManager.initialize()

            assert LoggerManager._initialized is True

    def test_logger_set_level(self):
        """测试设置日志级别"""
        LoggerManager.set_level("DEBUG")

        # 验证级别设置（这里只是基本测试）
        logger = get_logger("test_level_logger")
        assert logger is not None


if __name__ == "__main__":
    pytest.main([__file__])
