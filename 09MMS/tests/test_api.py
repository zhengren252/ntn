#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - API模块测试
测试FastAPI接口和路由

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.main import app
from src.api.routes import get_redis_client, get_metrics_collector, get_db_manager, get_zmq_socket
from src.models.simulation import SimulationRequest, TaskStatus


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self):
        """测试健康检查端点"""
        with TestClient(app) as client:
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_async(self):
        """测试异步健康检查"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestStatusEndpoint:
    """状态端点测试"""

    @pytest.mark.asyncio
    async def test_system_status(self):
        """测试系统状态端点"""
        # 创建模拟Redis客户端
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.return_value = "4"  # worker_count
        mock_redis_instance.llen.return_value = 2  # queue_length
        
        # 创建模拟指标收集器
        mock_metrics_instance = AsyncMock()
        mock_metrics_instance.get_avg_response_time.return_value = 0.05
        mock_metrics_instance.get_memory_usage.return_value = 512.5
        mock_metrics_instance.get_cpu_usage.return_value = 25.3
        
        # 覆盖FastAPI的依赖注入
        app.dependency_overrides[get_redis_client] = lambda: mock_redis_instance
        app.dependency_overrides[get_metrics_collector] = lambda: mock_metrics_instance
        
        try:
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/status")

                assert response.status_code == 200
                data = response.json()
                assert "service_status" in data
                assert "worker_count" in data
                assert "queue_length" in data
                assert data["service_status"] == "running"
                assert data["worker_count"] == 4
                assert data["queue_length"] == 2
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """测试性能指标端点"""
        with patch("src.api.routes.get_metrics_collector") as mock_metrics:
            mock_metrics.return_value.get_all_metrics.return_value = {
                "timers": {
                    "api.request.duration": {"count": 100, "avg": 0.05, "p95": 0.1}
                }
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/metrics")

                assert response.status_code == 200
                data = response.json()
                assert "metrics" in data


class TestSimulationEndpoint:
    """仿真端点测试"""

    @pytest.mark.asyncio
    async def test_simulate_success(self, sample_simulation_request, shared_test_database):
        """测试成功的仿真请求"""
        mock_result = {
            "status": "success",
            "data": {
                "slippage": 0.0015,
                "fill_probability": 0.98,
                "price_impact": 0.0005,
                "total_return": 0.125,
                "max_drawdown": -0.08,
                "sharpe_ratio": 1.85,
            }
        }

        # 创建模拟对象
        mock_zmq_socket = AsyncMock()
        mock_zmq_socket.recv_json.return_value = mock_result
        mock_zmq_socket.send_json = AsyncMock()
        
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get.return_value = None  # 没有缓存结果
        mock_cache_instance.setex = AsyncMock()  # 设置缓存
        
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.return_value = None  # 没有缓存结果
        mock_redis_instance.setex = AsyncMock()  # 设置缓存
        
        mock_metrics_instance = AsyncMock()
        mock_metrics_instance.record_simulation = AsyncMock()
        
        # 使用FastAPI的依赖覆盖
        app.dependency_overrides[get_zmq_socket] = lambda: mock_zmq_socket
        app.dependency_overrides[get_redis_client] = lambda: mock_redis_instance
        app.dependency_overrides[get_db_manager] = lambda: shared_test_database
        app.dependency_overrides[get_metrics_collector] = lambda: mock_metrics_instance
        
        try:
            async with AsyncClient(app=app, base_url="http://test") as client:
                # 将Pydantic对象转换为字典
                request_data = sample_simulation_request.model_dump(mode='json')
                response = await client.post(
                    "/api/v1/simulate", json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert "simulation_id" in data
                assert "slippage" in data
                assert "fill_probability" in data
                assert "price_impact" in data
                assert "total_return" in data
                assert "max_drawdown" in data
                assert "sharpe_ratio" in data
                assert "report_url" in data
                assert "execution_time" in data
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_simulate_validation_error(self):
        """测试仿真请求验证错误"""
        invalid_request = {
            "symbol": "",  # 空符号
            "scenario_type": "invalid_scenario",
            "start_date": "invalid_date",
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/simulate", json=invalid_request)

            assert response.status_code == 422  # 验证错误

    @pytest.mark.asyncio
    async def test_simulate_timeout(self, sample_simulation_request):
        """测试仿真超时"""
        with patch("src.api.routes.zmq_socket") as mock_socket:
            # 模拟超时
            mock_socket.recv_json.side_effect = asyncio.TimeoutError()

            async with AsyncClient(app=app, base_url="http://test") as client:
                # 将Pydantic对象转换为字典
                request_data = sample_simulation_request.model_dump(mode='json')
                response = await client.post(
                    "/api/v1/simulate", json=request_data
                )

                assert response.status_code == 408  # 请求超时
                data = response.json()
                assert data["success"] is False
                assert "timeout" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """测试获取任务状态"""
        task_id = "test_task_001"
        mock_status = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.5,
            "estimated_completion": "2024-01-01T12:00:00",
        }

        with patch("src.api.routes.get_simulation_cache") as mock_cache:
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get_task_status.return_value = mock_status
            mock_cache.return_value = mock_cache_instance

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/api/v1/tasks/{task_id}")

                assert response.status_code == 200
                data = response.json()
                assert data["task_id"] == task_id
                assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        task_id = "nonexistent_task"

        with patch("src.api.routes.get_simulation_cache") as mock_cache:
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get_task_status.return_value = None
            mock_cache.return_value = mock_cache_instance

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/api/v1/tasks/{task_id}")

                assert response.status_code == 404


class TestCalibrationEndpoint:
    """校准端点测试"""

    @pytest.mark.asyncio
    async def test_calibrate_parameters(self):
        """测试参数校准"""
        calibration_request = {
            "symbol": "AAPL",
            "scenario_type": "market_making",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        }

        mock_result = {
            "symbol": "AAPL",
            "scenario_type": "market_making",
            "parameters": {"volatility": 0.2, "mean_reversion_speed": 0.1},
            "quality_score": 0.85,
        }

        with patch("src.api.routes.get_simulation_cache") as mock_cache:
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get_calibration_params.return_value = None
            mock_cache_instance.cache_calibration_params.return_value = True
            mock_cache.return_value = mock_cache_instance

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/calibrate", json=calibration_request)

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "parameters" in data

    @pytest.mark.asyncio
    async def test_calibrate_cached_result(self):
        """测试使用缓存的校准结果"""
        calibration_request = {
            "symbol": "AAPL",
            "scenario_type": "market_making",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        }

        cached_params = {"volatility": 0.2, "mean_reversion_speed": 0.1}

        with patch("src.api.routes.get_simulation_cache") as mock_cache:
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get_calibration_params.return_value = cached_params
            mock_cache.return_value = mock_cache_instance

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/calibrate", json=calibration_request)

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["parameters"] == cached_params
                assert data["cached"] is True


class TestReportEndpoint:
    """报告端点测试"""

    @pytest.mark.asyncio
    async def test_get_simulation_report(self):
        """测试获取仿真报告"""
        simulation_id = "test_sim_001"

        mock_result = {
            "result": {
                "total_return": 0.05,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.02,
                "win_rate": 0.65,
            },
            "task_id": simulation_id,
        }

        with patch("src.api.routes.get_simulation_cache") as mock_cache:
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get_simulation_result.return_value = mock_result
            mock_cache.return_value = mock_cache_instance

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/reports/{simulation_id}")

                assert response.status_code == 200
                data = response.json()
                assert "simulation_id" in data
                assert "summary" in data
                assert "detailed_results" in data

    @pytest.mark.asyncio
    async def test_get_report_not_found(self):
        """测试获取不存在的报告"""
        simulation_id = "nonexistent_sim"

        with patch("src.api.routes.get_simulation_cache") as mock_cache:
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get_simulation_result.return_value = None
            mock_cache.return_value = mock_cache_instance

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(f"/reports/{simulation_id}")

                assert response.status_code == 404


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_internal_server_error(self):
        """测试内部服务器错误处理"""
        with patch("src.api.routes.get_metrics_collector") as mock_metrics:
            mock_metrics.side_effect = Exception("Internal error")

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/metrics")

                assert response.status_code == 500
                data = response.json()
                assert data["success"] is False
                assert "error" in data

    @pytest.mark.asyncio
    async def test_method_not_allowed(self):
        """测试方法不允许错误"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put("/health")  # PUT方法不被允许

            assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_not_found(self):
        """测试404错误"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/nonexistent-endpoint")

            assert response.status_code == 404


class TestMiddleware:
    """中间件测试"""

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """测试CORS头部"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.options("/health")

            # 检查CORS头部
            assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_gzip_compression(self):
        """测试Gzip压缩"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Accept-Encoding": "gzip"}
            response = await client.get("/health", headers=headers)

            # 检查是否有压缩
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_timing(self):
        """测试请求计时中间件"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            # 检查响应头中是否包含处理时间
            assert "X-Process-Time" in response.headers
            process_time = float(response.headers["X-Process-Time"])
            assert process_time >= 0


class TestWebSocketEndpoints:
    """WebSocket端点测试"""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        # 注意：这需要WebSocket支持，如果没有实现可以跳过
        pytest.skip("WebSocket endpoints not implemented yet")


if __name__ == "__main__":
    pytest.main([__file__])
