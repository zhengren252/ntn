#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus (NTN) - 策略优化模组 API

核心功能：
1. 健康检查接口
2. 回测启动接口
3. 参数优化接口
4. 策略决策接口
5. 系统状态监控
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.logging_config import setup_logging

# 导入核心模块
from config.settings import get_settings
from optimizer.backtester.engine import BacktestEngine
from optimizer.decision.engine import DecisionEngine

# 导入优化器模块
from optimizer.main import StrategyOptimizationModule
from optimizer.optimization.genetic_optimizer import GeneticOptimizer

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title="NeuroTrade Nexus - 策略优化模组",
    description="高性能交易策略优化与决策系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
optimization_module: Optional[StrategyOptimizationModule] = None
backtest_engine: Optional[BacktestEngine] = None
genetic_optimizer: Optional[GeneticOptimizer] = None
decision_engine: Optional[DecisionEngine] = None


# 请求/响应模型
class HealthResponse(BaseModel):
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="时间戳")
    version: str = Field(..., description="版本号")
    environment: str = Field(..., description="运行环境")
    components: Dict[str, str] = Field(..., description="组件状态")


class BacktestRequest(BaseModel):
    symbol: str = Field(..., description="交易对符号")
    strategy_configs: List[Dict[str, Any]] = Field(..., description="策略配置列表")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    initial_capital: Optional[float] = Field(10000, description="初始资金")


class BacktestResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="状态消息")
    timestamp: str = Field(..., description="时间戳")


class OptimizationRequest(BaseModel):
    symbol: str = Field(..., description="交易对符号")
    strategy_id: str = Field(..., description="策略ID")
    optimization_method: str = Field("genetic_algorithm", description="优化方法")
    target_metrics: List[str] = Field(
        ["return", "sharpe", "drawdown"], description="目标指标"
    )
    constraints: Optional[Dict[str, Any]] = Field(None, description="约束条件")


class OptimizationResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="状态消息")
    timestamp: str = Field(..., description="时间戳")


class DecisionRequest(BaseModel):
    optimization_results: Dict[str, Any] = Field(..., description="优化结果")
    market_data: Dict[str, Any] = Field(..., description="市场数据")
    risk_tolerance: Optional[str] = Field("medium", description="风险承受度")


class DecisionResponse(BaseModel):
    decisions: List[Dict[str, Any]] = Field(..., description="决策列表")
    timestamp: str = Field(..., description="时间戳")
    total_decisions: int = Field(..., description="决策总数")


# 任务状态管理
task_status = {}


@app.on_event("startup")
async def startup_event():
    """
    应用启动事件
    """
    global optimization_module, backtest_engine, genetic_optimizer, decision_engine

    logger.info("正在启动策略优化模组...")

    try:
        # 初始化核心组件
        optimization_module = StrategyOptimizationModule(settings)
        await optimization_module.initialize()

        backtest_engine = BacktestEngine(settings)
        await backtest_engine.initialize()

        genetic_optimizer = GeneticOptimizer(settings)
        await genetic_optimizer.initialize()

        # 创建决策引擎配置
        decision_config = {
            "max_position_size": 0.1,
            "max_daily_loss": 0.02,
            "max_drawdown_threshold": getattr(settings, "max_drawdown_threshold", 0.05),
            "min_confidence_threshold": getattr(
                settings, "min_confidence_threshold", 0.6
            ),
        }
        decision_engine = DecisionEngine(decision_config)

        logger.info("策略优化模组启动完成")

    except Exception as e:
        logger.error("策略优化模组启动失败: %s", e)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭事件
    """
    logger.info("正在关闭策略优化模组...")

    if optimization_module:
        await optimization_module.cleanup()

    logger.info("策略优化模组已关闭")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口
    """
    try:
        # 检查各组件状态
        components = {
            "optimization_module": "healthy" if optimization_module else "unavailable",
            "backtest_engine": "healthy" if backtest_engine else "unavailable",
            "genetic_optimizer": "healthy" if genetic_optimizer else "unavailable",
            "decision_engine": "healthy" if decision_engine else "unavailable",
            "zmq_connection": "healthy"
            if optimization_module and hasattr(optimization_module, 'communication') and optimization_module.communication.zmq_context
            else "unavailable",
        }

        # 判断整体状态
        overall_status = (
            "healthy"
            if all(status == "healthy" for status in components.values())
            else "degraded"
        )

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            environment=settings.environment,
            components=components,
        )

    except Exception as e:
        logger.error("健康检查失败: %s", e)
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@app.get("/live")
async def liveness_probe():
    """存活性探针（轻量级，避免依赖外部组件）"""
    return {
        "status": "alive",
        "module": "OptiCore",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/backtest/start", response_model=BacktestResponse)
async def start_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """
    启动回测任务
    """
    if not backtest_engine:
        raise HTTPException(status_code=503, detail="回测引擎未初始化")

    try:
        # 生成任务ID
        task_id = (
            f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.symbol}"
        )

        # 初始化任务状态
        task_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "回测任务已启动",
            "start_time": datetime.now().isoformat(),
            "result": None,
        }

        # 在后台运行回测
        background_tasks.add_task(
            run_backtest_task, task_id, request.symbol, request.strategy_configs
        )

        return BacktestResponse(
            task_id=task_id,
            status="running",
            message="回测任务已启动",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error("启动回测任务失败: %s", e)
        raise HTTPException(status_code=500, detail=f"启动回测任务失败: {str(e)}")


@app.post("/api/optimization/start", response_model=OptimizationResponse)
async def start_optimization(
    request: OptimizationRequest, background_tasks: BackgroundTasks
):
    """
    启动参数优化任务
    """
    if not genetic_optimizer:
        raise HTTPException(status_code=503, detail="遗传优化器未初始化")

    try:
        # 生成任务ID
        task_id = (
            f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.symbol}"
        )

        # 初始化任务状态
        task_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "参数优化任务已启动",
            "start_time": datetime.now().isoformat(),
            "result": None,
        }

        # 在后台运行优化
        background_tasks.add_task(
            run_optimization_task,
            task_id,
            request.symbol,
            request.strategy_id,
            request.optimization_method,
        )

        return OptimizationResponse(
            task_id=task_id,
            status="running",
            message="参数优化任务已启动",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error("启动优化任务失败: %s", e)
        raise HTTPException(status_code=500, detail=f"启动优化任务失败: {str(e)}")


@app.post("/api/decision/make", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    生成策略决策
    """
    if not decision_engine:
        raise HTTPException(status_code=503, detail="决策引擎未初始化")

    try:
        # 生成决策
        decisions = await decision_engine.make_decision(
            request.optimization_results, request.market_data
        )

        # 转换决策为字典格式
        decision_dicts = []
        for decision in decisions:
            decision_dict = {
                "strategy_id": decision.strategy_id,
                "symbol": decision.symbol,
                "action": decision.action,
                "confidence": decision.confidence,
                "risk_score": decision.risk_score,
                "expected_return": decision.expected_return,
                "max_drawdown": decision.max_drawdown,
                "position_size": decision.position_size,
                "stop_loss": decision.stop_loss,
                "take_profit": decision.take_profit,
                "reasoning": decision.reasoning,
                "timestamp": decision.timestamp.isoformat(),
            }
            decision_dicts.append(decision_dict)

        return DecisionResponse(
            decisions=decision_dicts,
            timestamp=datetime.now().isoformat(),
            total_decisions=len(decision_dicts),
        )

    except Exception as e:
        logger.error("生成决策失败: %s", e)
        raise HTTPException(status_code=500, detail=f"生成决策失败: {str(e)}")


@app.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    获取任务状态
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task_status[task_id]


@app.get("/api/task/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_status[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    return task["result"]


# 后台任务函数
async def run_backtest_task(task_id: str, symbol: str, strategy_configs: List[Dict]):
    """
    运行回测任务
    """
    try:
        logger.info("开始执行回测任务: %s", task_id)

        # 更新任务状态
        task_status[task_id]["progress"] = 10
        task_status[task_id]["message"] = "正在准备回测数据"

        # 执行回测
        result = await backtest_engine.run_backtest(symbol, strategy_configs)

        # 更新任务状态
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["progress"] = 100
        task_status[task_id]["message"] = "回测任务完成"
        task_status[task_id]["result"] = result
        task_status[task_id]["end_time"] = datetime.now().isoformat()

        logger.info("回测任务完成: %s", task_id)

    except Exception as e:
        logger.error("回测任务失败 %s: %s", task_id, e)
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["message"] = f"回测任务失败: {str(e)}"
        task_status[task_id]["end_time"] = datetime.now().isoformat()


async def run_optimization_task(
    task_id: str, symbol: str, strategy_id: str, method: str
):
    """
    运行优化任务
    """
    try:
        logger.info("开始执行优化任务: %s", task_id)

        # 更新任务状态
        task_status[task_id]["progress"] = 10
        task_status[task_id]["message"] = "正在准备优化数据"

        # 首先运行回测获取基础结果
        strategy_configs = [{"strategy_id": strategy_id, "params": {}}]  # 使用默认参数

        backtest_results = await backtest_engine.run_backtest(symbol, strategy_configs)

        # 更新进度
        task_status[task_id]["progress"] = 50
        task_status[task_id]["message"] = "正在执行参数优化"

        # 执行优化
        result = await genetic_optimizer.optimize(symbol, backtest_results)

        # 更新任务状态
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["progress"] = 100
        task_status[task_id]["message"] = "优化任务完成"
        task_status[task_id]["result"] = result
        task_status[task_id]["end_time"] = datetime.now().isoformat()

        logger.info("优化任务完成: %s", task_id)

    except Exception as e:
        logger.error("优化任务失败 %s: %s", task_id, e)
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["message"] = f"优化任务失败: {str(e)}"
        task_status[task_id]["end_time"] = datetime.now().isoformat()


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
