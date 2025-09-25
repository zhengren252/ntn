#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - API路由
定义FastAPI的路由和请求处理逻辑

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import uuid
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
import zmq
import zmq.asyncio
import redis.asyncio as redis

from src.models.simulation import (
    SimulationRequest,
    SimulationResponse,
    SystemStatus,
    ErrorResponse,
    TaskStatus,
    ScenarioType,
)
from src.core.config import get_settings
from src.core.database import DatabaseManager
from src.core.cache import get_simulation_cache
from src.utils.logger import get_logger
from src.utils.metrics import MetricsCollector

# 初始化日志器和配置
logger = get_logger(__name__)
config = get_settings()

# 创建路由器
router = APIRouter()

# 全局变量
zmq_context = None
zmq_socket = None
redis_client = None
db_manager = None
metrics_collector = None


async def get_zmq_socket():
    """获取ZeroMQ套接字"""
    global zmq_context, zmq_socket
    if zmq_socket is None:
        zmq_context = zmq.asyncio.Context()
        zmq_socket = zmq_context.socket(zmq.REQ)
        zmq_socket.connect(f"tcp://localhost:{config.FRONTEND_PORT}")
    return zmq_socket


async def get_redis_client():
    """获取Redis客户端"""
    global redis_client
    if redis_client is None:
        redis_config = config.get_redis_config()
        redis_client = redis.Redis(
            host=redis_config["url"].split("//")[1].split(":")[0],
            port=int(redis_config["url"].split(":")[-1]),
            db=redis_config["db"],
            password=redis_config["password"],
            decode_responses=True,
        )
    return redis_client


async def get_db_manager():
    """获取数据库管理器"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(config.database_path)
        await db_manager.init_database()
    return db_manager


async def get_metrics_collector():
    """获取指标收集器"""
    global metrics_collector
    if metrics_collector is None:
        metrics_collector = MetricsCollector()
    return metrics_collector


@router.get("/health", summary="健康检查", description="检查服务健康状态")
async def health_check(request: Request):
    """健康检查端点"""
    try:
        # 检查Redis连接
        redis_client = await get_redis_client()
        await redis_client.ping()

        # 检查数据库连接
        db_manager = await get_db_manager()

        # 生成/透传 request_id
        request_id = getattr(getattr(request, "state", object()), "request_id", None) or request.headers.get("X-Request-ID") or uuid.uuid4().hex

        return {
            "status": "healthy",
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "version": getattr(config, "APP_VERSION", "1.0.0"),
            "services": {
                "redis": "connected",
                "database": "connected",
                "zmq": "connected",
            },
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不可用")


@router.get(
    "/status", response_model=SystemStatus, summary="系统状态", description="获取系统运行状态"
)
async def get_system_status(
    metrics: MetricsCollector = Depends(get_metrics_collector),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """获取系统状态"""
    try:
        # 获取工作进程数量
        worker_count = await redis_client.get("mms:worker_count") or 0
        worker_count = int(worker_count)

        # 获取队列长度
        queue_length = await redis_client.llen("mms:task_queue") or 0

        # 获取性能指标
        avg_response_time = await metrics.get_avg_response_time()
        memory_usage = await metrics.get_memory_usage()
        cpu_usage = await metrics.get_cpu_usage()

        return SystemStatus(
            service_status="running",
            worker_count=worker_count,
            queue_length=queue_length,
            avg_response_time=avg_response_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统状态失败")


@router.get("/metrics", summary="性能指标", description="获取详细的性能指标")
async def get_metrics(metrics: MetricsCollector = Depends(get_metrics_collector)):
    """获取性能指标"""
    try:
        return await metrics.get_all_metrics()
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能指标失败")


@router.get("/cache", summary="获取仿真缓存", description="获取仿真缓存实例信息")
async def get_simulation_cache_info():
    """获取仿真缓存信息"""
    try:
        cache = await get_simulation_cache()
        if cache is None:
            raise HTTPException(status_code=503, detail="缓存服务不可用")

        # 获取缓存统计信息
        cache_info = {
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_type": "redis",
            "connection_info": {
                "host": cache.connection_pool.connection_kwargs.get("host", "unknown"),
                "port": cache.connection_pool.connection_kwargs.get("port", "unknown"),
                "db": cache.connection_pool.connection_kwargs.get("db", 0),
            },
        }

        # 尝试获取缓存键数量
        try:
            keys_count = await cache.dbsize()
            cache_info["keys_count"] = keys_count
        except Exception:
            cache_info["keys_count"] = "unknown"

        return cache_info
    except Exception as e:
        logger.error(f"获取仿真缓存失败: {e}")
        raise HTTPException(status_code=500, detail="获取仿真缓存失败")


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="执行仿真",
    description="提交市场微结构仿真任务",
)
async def simulate_market(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    zmq_socket=Depends(get_zmq_socket),
    redis_client: redis.Redis = Depends(get_redis_client),
    db_manager: DatabaseManager = Depends(get_db_manager),
    metrics: MetricsCollector = Depends(get_metrics_collector),
):
    """执行市场微结构仿真"""
    from src.models.simulation import SimulationTask, ScenarioType  # 导入SimulationTask和ScenarioType
    
    start_time = time.time()
    simulation_id = (
        f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    )

    try:
        logger.info(f"开始处理仿真请求: {simulation_id}")

        # 验证请求参数
        await _validate_simulation_request(request)

        # 检查缓存
        cache_key = f"mms:simulation:{_generate_cache_key(request)}"
        cached_result = await redis_client.get(cache_key)
        if cached_result:  # 简化缓存逻辑
            logger.info(f"返回缓存结果: {simulation_id}")
            cached_data = json.loads(cached_result)
            return SimulationResponse(**cached_data)

        # 创建仿真任务对象
        task = SimulationTask(
            task_id=simulation_id,
            symbol=request.symbol,
            period=request.period,
            scenario=ScenarioType(request.scenario),  # 将字符串转换为枚举
            strategy_params=request.strategy_params,
            start_time=datetime.fromisoformat(request.start_time.replace("Z", "+00:00")) if isinstance(request.start_time, str) else request.start_time,
            end_time=datetime.fromisoformat(request.end_time.replace("Z", "+00:00")) if isinstance(request.end_time, str) else request.end_time,
            status=TaskStatus.PENDING
        )

        # 保存任务到数据库
        await db_manager.save_simulation_task(task)

        # 发送任务到工作进程
        task_data = {
            "task_id": simulation_id,
            "symbol": request.symbol,
            "period": request.period,
            "scenario": request.scenario,
            "strategy_params": request.strategy_params,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "created_at": datetime.now().isoformat(),
        }
        message = {"type": "simulation", "data": task_data}

        await zmq_socket.send_json(message)

        # 等待结果（设置超时）
        try:
            result = await asyncio.wait_for(
                zmq_socket.recv_json(), timeout=300  # 默认超时时间
            )
        except asyncio.TimeoutError:
            logger.error(f"仿真任务超时: {simulation_id}")
            await db_manager.update_task_status(
                simulation_id, TaskStatus.FAILED, "任务执行超时"
            )
            raise HTTPException(status_code=408, detail="仿真任务执行超时")

        if result.get("status") == "error":
            error_msg = result.get("message", "未知错误")
            logger.error(f"仿真任务失败: {simulation_id}, 错误: {error_msg}")
            await db_manager.update_task_status(
                simulation_id, TaskStatus.FAILED, error_msg
            )
            raise HTTPException(status_code=500, detail=f"仿真执行失败: {error_msg}")

        # 处理成功结果
        simulation_result = result["data"]
        execution_time = time.time() - start_time

        # 构建响应
        response = SimulationResponse(
            simulation_id=simulation_id,
            slippage=simulation_result["slippage"],
            fill_probability=simulation_result["fill_probability"],
            price_impact=simulation_result["price_impact"],
            total_return=simulation_result["total_return"],
            max_drawdown=simulation_result["max_drawdown"],
            sharpe_ratio=simulation_result["sharpe_ratio"],
            report_url=f"http://{config.HOST}:{config.HTTP_PORT}/reports/{simulation_id}",
            execution_time=execution_time,
        )

        # 缓存结果
        await redis_client.setex(cache_key, config.CACHE_TTL, response.json())

        # 记录指标
        await metrics.record_simulation(execution_time, True)

        # 更新任务状态
        await db_manager.update_task_status(simulation_id, TaskStatus.COMPLETED)

        logger.info(f"仿真任务完成: {simulation_id}, 耗时: {execution_time:.2f}秒")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"仿真任务异常: {simulation_id}, 错误: {e}")
        await metrics.record_simulation(time.time() - start_time, False)
        if db_manager:
            await db_manager.update_task_status(
                simulation_id, TaskStatus.FAILED, str(e)
            )
        raise HTTPException(status_code=500, detail=f"仿真执行异常: {str(e)}")


@router.post("/calibrate", summary="参数校准", description="校准仿真引擎参数")
async def calibrate_parameters(
    symbol: str,
    scenario: ScenarioType,
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """校准仿真引擎参数"""
    try:
        logger.info(f"开始校准参数: {symbol}, 场景: {scenario}")

        # 获取历史市场数据
        market_data = await db_manager.get_market_data(symbol, limit=1000)

        if not market_data:
            raise HTTPException(status_code=404, detail="未找到市场数据")

        # 执行参数校准逻辑
        calibration_result = await _perform_calibration(market_data, scenario)

        # 保存校准参数
        param_id = (
            f"cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        calibration_data = {
            "param_id": param_id,
            "symbol": symbol,
            "scenario": scenario.value,
            "base_slippage": calibration_result["base_slippage"],
            "volatility_factor": calibration_result["volatility_factor"],
            "liquidity_factor": calibration_result["liquidity_factor"],
            "calibrated_at": datetime.now().isoformat(),
            "is_active": True,
        }

        await db_manager.save_calibration_params(calibration_data)

        logger.info(f"参数校准完成: {param_id}")
        return {
            "calibration_id": param_id,
            "symbol": symbol,
            "scenario": scenario,
            "parameters": calibration_result,
            "calibrated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"参数校准失败: {e}")
        raise HTTPException(status_code=500, detail=f"参数校准失败: {str(e)}")


@router.get("/tasks/{task_id}", summary="获取任务详情", description="根据任务ID获取仿真任务详情")
async def get_task_details(
    task_id: str, db_manager: DatabaseManager = Depends(get_db_manager)
):
    """获取任务详情"""
    try:
        task_info = await db_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")

        return task_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务详情失败")


@router.get("/reports/{simulation_id}", summary="获取仿真报告", description="获取详细的仿真分析报告")
async def get_simulation_report(
    simulation_id: str, db_manager: DatabaseManager = Depends(get_db_manager)
):
    """获取仿真报告"""
    try:
        # 获取仿真结果
        result = await db_manager.get_simulation_result(simulation_id)
        if not result:
            raise HTTPException(status_code=404, detail="仿真结果不存在")

        # 生成详细报告
        report = await _generate_detailed_report(simulation_id, result)

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取仿真报告失败: {e}")
        raise HTTPException(status_code=500, detail="获取仿真报告失败")


async def _validate_simulation_request(request: SimulationRequest):
    """验证仿真请求参数"""
    # 验证交易对
    if not request.symbol or len(request.symbol) < 3:
        raise HTTPException(status_code=400, detail="无效的交易对符号")

    # 验证策略参数
    required_params = ["entry_threshold", "exit_threshold", "position_size"]
    for param in required_params:
        if param not in request.strategy_params:
            raise HTTPException(status_code=400, detail=f"缺少必需的策略参数: {param}")

    # 验证参数范围
    if not 0 < request.strategy_params.get("position_size", 0) <= 1:
        raise HTTPException(status_code=400, detail="仓位大小必须在0到1之间")


def _generate_cache_key(request: SimulationRequest) -> str:
    """生成缓存键"""
    key_data = {
        "symbol": request.symbol,
        "period": request.period,
        "scenario": request.scenario,
        "strategy_params": sorted(request.strategy_params.items()),
    }
    return str(hash(str(key_data)))


async def _perform_calibration(
    market_data: list, scenario: ScenarioType
) -> Dict[str, float]:
    """执行参数校准"""
    # 简化的校准逻辑，实际应用中需要更复杂的算法
    import numpy as np

    prices = [float(data["close_price"]) for data in market_data]
    returns = np.diff(np.log(prices))
    volatility = np.std(returns)

    # 根据场景调整参数
    scenario_factors = {
        ScenarioType.NORMAL: {
            "base_slippage": 0.001,
            "vol_factor": 1.0,
            "liq_factor": 1.0,
        },
        ScenarioType.BLACK_SWAN: {
            "base_slippage": 0.005,
            "vol_factor": 3.0,
            "liq_factor": 0.3,
        },
        ScenarioType.HIGH_VOLATILITY: {
            "base_slippage": 0.003,
            "vol_factor": 2.0,
            "liq_factor": 0.7,
        },
        ScenarioType.LOW_LIQUIDITY: {
            "base_slippage": 0.004,
            "vol_factor": 1.5,
            "liq_factor": 0.5,
        },
        ScenarioType.FLASH_CRASH: {
            "base_slippage": 0.008,
            "vol_factor": 5.0,
            "liq_factor": 0.2,
        },
    }

    factors = scenario_factors.get(scenario, scenario_factors[ScenarioType.NORMAL])

    return {
        "base_slippage": factors["base_slippage"] * (1 + volatility),
        "volatility_factor": factors["vol_factor"] * volatility,
        "liquidity_factor": factors["liq_factor"],
    }


async def _generate_detailed_report(simulation_id: str, result: dict) -> dict:
    """生成详细报告"""
    return {
        "simulation_id": simulation_id,
        "summary": {
            "total_return": result["total_return"],
            "max_drawdown": result["max_drawdown"],
            "sharpe_ratio": result["sharpe_ratio"],
            "execution_time": result["execution_time"],
        },
        "market_impact": {
            "slippage": result["slippage"],
            "fill_probability": result["fill_probability"],
            "price_impact": result["price_impact"],
        },
        "risk_metrics": {
            "volatility": result.get("volatility", 0),
            "var_95": result.get("var_95", 0),
            "max_consecutive_losses": result.get("max_consecutive_losses", 0),
        },
        "generated_at": datetime.now().isoformat(),
        "report_version": "1.0.0",
    }


# 注意：异常处理器应该在FastAPI应用级别设置，而不是在APIRouter级别


# 清理资源
async def cleanup_resources():
    """清理资源"""
    global zmq_socket, zmq_context, redis_client

    if zmq_socket:
        zmq_socket.close()
    if zmq_context:
        zmq_context.term()
    if redis_client:
        await redis_client.close()


@router.get("/live")
async def live():
    """Liveness probe - quick check that the service is up"""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": "市场微结构仿真引擎 (MMS)",
        "version": getattr(config, "APP_VERSION", "1.0.0")
    }
