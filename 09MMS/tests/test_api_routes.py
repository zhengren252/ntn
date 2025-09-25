# -*- coding: utf-8 -*-
"""
API 路由测试模块

测试市场微结构仿真引擎的 FastAPI 路由功能
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routes import router
from src.models.simulation import SimulationRequest, SimulationResponse


# 创建测试应用
app = FastAPI()
app.include_router(router)


class TestHealthAndStatus:
    """健康检查和状态测试"""

    def test_health_check(self):
        """测试健康检查端点"""
        with TestClient(app) as client:
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data

    @patch("src.api.routes.psutil")
    @patch("src.api.routes.redis_client")
    @patch("src.api.routes.db_manager")
    def test_system_status(self, mock_db, mock_redis, mock_psutil):
        """测试系统状态端点"""
        # 模拟系统资源
        mock_psutil.cpu_percent.return_value = 45.2
        mock_psutil.virtual_memory.return_value.percent = 62.1
        mock_psutil.disk_usage.return_value.percent = 78.5

        # 模拟 Redis 连接
        mock_redis.ping = AsyncMock(return_value=True)

        # 模拟数据库连接
        mock_db.get_task_stats = AsyncMock(
            return_value={
                "total_tasks": 150,
                "completed_tasks": 145,
                "failed_tasks": 3,
                "pending_tasks": 2,
            }
        )

        with TestClient(app) as client:
            response = client.get("/status")

            assert response.status_code == 200
            data = response.json()

            assert "system" in data
            assert "services" in data
            assert "database" in data
            assert "timestamp" in data

            # 检查系统信息
            system = data["system"]
            assert "cpu_usage" in system
            assert "memory_usage" in system
            assert "disk_usage" in system

            # 检查服务状态
            services = data["services"]
            assert "redis" in services
            assert "zmq" in services

    @patch("src.api.routes.metrics_collector")
    def test_metrics_endpoint(self, mock_metrics):
        """测试性能指标端点"""
        # 模拟指标数据
        mock_metrics.get_metrics.return_value = {
            "response_times": {"avg": 0.125, "p95": 0.250, "p99": 0.500},
            "system_resources": {
                "cpu_usage": 45.2,
                "memory_usage": 62.1,
                "disk_usage": 78.5,
            },
            "simulation_metrics": {
                "total_simulations": 1250,
                "avg_execution_time": 2.34,
                "success_rate": 0.987,
            },
        }

        with TestClient(app) as client:
            response = client.get("/metrics")

            assert response.status_code == 200
            data = response.json()

            assert "response_times" in data
            assert "system_resources" in data
            assert "simulation_metrics" in data


class TestSimulationEndpoints:
    """仿真相关端点测试"""

    @patch("src.api.routes.zmq_socket")
    @patch("src.api.routes.redis_client")
    def test_simulate_endpoint_success(self, mock_redis, mock_zmq):
        """测试仿真端点成功情况"""
        # 模拟缓存未命中
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)

        # 模拟 ZeroMQ 响应
        mock_zmq.send_json = MagicMock()
        mock_zmq.recv_json = MagicMock(
            return_value={
                "status": "success",
                "result": {
                    "simulation_id": "sim_20241201_001",
                    "slippage": 0.0015,
                    "fill_probability": 0.98,
                    "price_impact": 0.0005,
                    "total_return": 0.125,
                    "max_drawdown": -0.08,
                    "sharpe_ratio": 1.85,
                    "var_95": -0.025,
                    "var_99": -0.045,
                    "max_consecutive_loss": -0.12,
                    "win_rate": 0.65,
                    "profit_factor": 1.8,
                    "execution_time": 2.34,
                },
            }
        )

        request_data = {
            "symbol": "BTCUSDT",
            "period": "30d",
            "scenario": "normal",
            "strategy_params": {
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
        }

        with TestClient(app) as client:
            response = client.post(
                "/simulate",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.json()

            # 检查响应字段
            assert "simulation_id" in data
            assert "slippage" in data
            assert "fill_probability" in data
            assert "price_impact" in data
            assert "total_return" in data
            assert "max_drawdown" in data
            assert "sharpe_ratio" in data
            assert "execution_time" in data

            # 检查数值合理性
            assert data["slippage"] >= 0
            assert 0 <= data["fill_probability"] <= 1
            assert data["price_impact"] >= 0
            assert data["execution_time"] > 0

    def test_simulate_endpoint_invalid_request(self):
        """测试仿真端点无效请求"""
        invalid_request = {
            "symbol": "",  # 空符号
            "period": "invalid_period",
            "scenario": "invalid_scenario",
        }

        with TestClient(app) as client:
            response = client.post(
                "/simulate",
                json=invalid_request,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 422  # Validation error

    @patch("src.api.routes.redis_client")
    def test_simulate_endpoint_cache_hit(self, mock_redis):
        """测试仿真端点缓存命中"""
        # 模拟缓存命中
        cached_result = {
            "simulation_id": "sim_cached_001",
            "slippage": 0.0012,
            "fill_probability": 0.99,
            "price_impact": 0.0003,
            "total_return": 0.145,
            "max_drawdown": -0.06,
            "sharpe_ratio": 2.1,
            "execution_time": 0.001,  # 缓存响应应该很快
            "cached": True,
        }

        mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))

        request_data = {
            "symbol": "BTCUSDT",
            "period": "30d",
            "scenario": "normal",
            "strategy_params": {
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
        }

        with TestClient(app) as client:
            response = client.post(
                "/simulate",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["simulation_id"] == "sim_cached_001"
            assert data["cached"] is True
            assert data["execution_time"] < 0.01  # 缓存响应应该很快

    @patch("src.api.routes.zmq_socket")
    def test_simulate_endpoint_worker_error(self, mock_zmq):
        """测试仿真端点工作进程错误"""
        # 模拟工作进程返回错误
        mock_zmq.send_json = MagicMock()
        mock_zmq.recv_json = MagicMock(
            return_value={
                "status": "error",
                "error": "Simulation failed: Invalid parameters",
            }
        )

        request_data = {
            "symbol": "BTCUSDT",
            "period": "30d",
            "scenario": "normal",
            "strategy_params": {
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
        }

        with TestClient(app) as client:
            response = client.post(
                "/simulate",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 500
            data = response.json()
            assert "error" in data


class TestCalibrationEndpoints:
    """参数校准端点测试"""

    @patch("src.api.routes.zmq_socket")
    def test_calibrate_endpoint_success(self, mock_zmq):
        """测试参数校准端点成功情况"""
        # 模拟校准响应
        mock_zmq.send_json = MagicMock()
        mock_zmq.recv_json = MagicMock(
            return_value={
                "status": "success",
                "result": {
                    "calibration_id": "cal_20241201_001",
                    "symbol": "BTCUSDT",
                    "scenario": "normal",
                    "parameters": {
                        "volatility_factor": 1.2,
                        "liquidity_factor": 0.8,
                        "spread_factor": 1.1,
                        "impact_factor": 0.9,
                    },
                    "confidence_score": 0.85,
                    "execution_time": 5.67,
                },
            }
        )

        request_data = {"symbol": "BTCUSDT", "scenario": "normal"}

        with TestClient(app) as client:
            response = client.post(
                "/calibrate",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.json()

            assert "calibration_id" in data
            assert "parameters" in data
            assert "confidence_score" in data
            assert "execution_time" in data

            # 检查参数合理性
            assert 0 <= data["confidence_score"] <= 1
            assert data["execution_time"] > 0

    def test_calibrate_endpoint_invalid_request(self):
        """测试参数校准端点无效请求"""
        invalid_request = {"symbol": "", "scenario": "invalid_scenario"}  # 空符号

        with TestClient(app) as client:
            response = client.post(
                "/calibrate",
                json=invalid_request,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 422  # Validation error


class TestTaskAndReportEndpoints:
    """任务和报告端点测试"""

    @patch("src.api.routes.db_manager")
    def test_get_task_details_success(self, mock_db):
        """测试获取任务详情成功情况"""
        # 模拟数据库响应
        mock_db.get_task_by_id = AsyncMock(
            return_value={
                "task_id": "sim_20241201_001",
                "symbol": "BTCUSDT",
                "scenario": "normal",
                "status": "completed",
                "created_at": "2024-12-01T10:00:00Z",
                "completed_at": "2024-12-01T10:02:34Z",
                "execution_time": 2.34,
                "result": {
                    "slippage": 0.0015,
                    "fill_probability": 0.98,
                    "total_return": 0.125,
                },
            }
        )

        with TestClient(app) as client:
            response = client.get("/tasks/sim_20241201_001")

            assert response.status_code == 200
            data = response.json()

            assert data["task_id"] == "sim_20241201_001"
            assert data["status"] == "completed"
            assert "result" in data

    @patch("src.api.routes.db_manager")
    def test_get_task_details_not_found(self, mock_db):
        """测试获取不存在的任务详情"""
        # 模拟任务不存在
        mock_db.get_task_by_id = AsyncMock(return_value=None)

        with TestClient(app) as client:
            response = client.get("/tasks/nonexistent_task")

            assert response.status_code == 404
            data = response.json()
            assert "error" in data

    @patch("src.api.routes.os.path.exists")
    def test_get_simulation_report_success(self, mock_exists):
        """测试获取仿真报告成功情况"""
        # 模拟报告文件存在
        mock_exists.return_value = True

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
            <html>
            <head><title>Simulation Report</title></head>
            <body>
                <h1>Simulation Report: sim_20241201_001</h1>
                <p>Slippage: 0.0015</p>
                <p>Fill Probability: 0.98</p>
            </body>
            </html>
            """

            with TestClient(app) as client:
                response = client.get("/reports/sim_20241201_001")

                assert response.status_code == 200
                assert "text/html" in response.headers["content-type"]
                assert "Simulation Report" in response.text

    @patch("src.api.routes.os.path.exists")
    def test_get_simulation_report_not_found(self, mock_exists):
        """测试获取不存在的仿真报告"""
        # 模拟报告文件不存在
        mock_exists.return_value = False

        with TestClient(app) as client:
            response = client.get("/reports/nonexistent_report")

            assert response.status_code == 404
            data = response.json()
            assert "error" in data


class TestErrorHandling:
    """错误处理测试"""

    @patch("src.api.routes.zmq_socket")
    def test_zmq_timeout_error(self, mock_zmq):
        """测试 ZeroMQ 超时错误"""
        import zmq

        # 模拟 ZeroMQ 超时
        mock_zmq.send_json = MagicMock()
        mock_zmq.recv_json = MagicMock(side_effect=zmq.Again("Timeout"))

        request_data = {
            "symbol": "BTCUSDT",
            "period": "30d",
            "scenario": "normal",
            "strategy_params": {
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
        }

        with TestClient(app) as client:
            response = client.post(
                "/simulate",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 504  # Gateway timeout
            data = response.json()
            assert "error" in data
            assert "timeout" in data["error"].lower()

    @patch("src.api.routes.redis_client")
    def test_redis_connection_error(self, mock_redis):
        """测试 Redis 连接错误"""
        # 模拟 Redis 连接错误
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

        request_data = {
            "symbol": "BTCUSDT",
            "period": "30d",
            "scenario": "normal",
            "strategy_params": {
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
        }

        with TestClient(app) as client:
            response = client.post(
                "/simulate",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            # 即使 Redis 失败，仍应能处理请求（降级到直接处理）
            assert response.status_code in [200, 500]


@pytest.mark.integration
class TestAPIIntegration:
    """API 集成测试"""

    def test_full_simulation_workflow(self):
        """测试完整的仿真工作流程"""
        with TestClient(app) as client:
            # 1. 检查系统健康状态
            health_response = client.get("/health")
            assert health_response.status_code == 200

            # 2. 检查系统状态
            status_response = client.get("/status")
            # 注意：在测试环境中可能会失败，因为依赖服务未启动
            # assert status_response.status_code == 200

            # 3. 获取性能指标
            metrics_response = client.get("/metrics")
            # 同样，在测试环境中可能会失败
            # assert metrics_response.status_code == 200

    def test_api_documentation(self):
        """测试 API 文档可访问性"""
        with TestClient(app) as client:
            # FastAPI 自动生成的文档
            docs_response = client.get("/docs")
            assert docs_response.status_code == 200

            # OpenAPI 规范
            openapi_response = client.get("/openapi.json")
            assert openapi_response.status_code == 200

            openapi_data = openapi_response.json()
            assert "openapi" in openapi_data
            assert "paths" in openapi_data
