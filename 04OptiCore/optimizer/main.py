#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略优化模组主入口文件
NeuroTrade Nexus (NTN) - Strategy Optimization Module

核心职责：
1. 订阅扫描器发布的潜在交易机会
2. 执行策略回测和参数优化
3. 进行压力测试和风险评估
4. 发布经过验证的策略参数包
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import setup_logging
from config.settings import get_settings
from optimizer.backtester.engine import BacktestEngine
from optimizer.communication.zmq_client import (
    StrategyPackage,
    TradingOpportunity,
    create_zmq_client,
)
from optimizer.decision.engine import DecisionEngine
from optimizer.optimization.genetic_optimizer import GeneticOptimizer
from optimizer.strategies.manager import StrategyManager
from optimizer.utils.api_client import create_api_forge_client
from optimizer.utils.mms_client import create_mms_client


@dataclass
class OptimizerComponents:
    """优化器核心组件"""

    backtest_engine: Optional[Any] = None
    genetic_optimizer: Optional[Any] = None
    decision_engine: Optional[Any] = None
    strategy_manager: Optional[Any] = None
    risk_manager: Optional[Any] = None
    data_validator: Optional[Any] = None
    api_forge_client: Optional[Any] = None
    mms_client: Optional[Any] = None


@dataclass
class OptimizerCommunication:
    """优化器通信组件"""

    zmq_client: Optional[Any] = None
    zmq_context: Optional[Any] = None


@dataclass
class OptimizerState:
    """优化器运行状态"""

    is_running: bool = False


@dataclass
class OptimizerStats:
    """优化器统计信息"""

    opportunities_processed: int = 0
    strategies_published: int = 0
    last_activity: Optional[datetime] = None


class StrategyOptimizationModule:
    """
    策略优化模组主类

    实现NeuroTrade Nexus核心设计理念：
    - 微服务架构设计
    - ZeroMQ消息总线通信
    - 三环境隔离(development/staging/production)
    - 数据隔离与环境管理规范
    """

    def __init__(self, config=None):
        if config is not None:
            self.config = config
        else:
            self.config = get_settings()

        self.logger = logging.getLogger(__name__)

        # 使用数据类管理组件和状态
        self.components = OptimizerComponents()
        self.communication = OptimizerCommunication()
        self.state = OptimizerState()
        self.stats = OptimizerStats()

        # 初始化标志
        self._initialized = False

    async def initialize(self):
        """初始化优化器组件"""
        if self._initialized:
            self.logger.warning("优化器已经初始化，跳过重复初始化")
            return

        try:
            self.logger.info("开始初始化策略优化模组...")

            # 初始化核心组件
            await self._initialize_components()

            # 初始化通信组件
            await self._initialize_communication()

            self._initialized = True
            self.logger.info("策略优化模组初始化完成")

        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            await self.cleanup()
            raise

    async def _initialize_components(self):
        """初始化核心组件"""
        try:
            # 初始化回测引擎
            self.components.backtest_engine = BacktestEngine(self.config)

            # 初始化遗传算法优化器
            self.components.genetic_optimizer = GeneticOptimizer(self.config)

            # 初始化决策引擎
            self.components.decision_engine = DecisionEngine(
                config={
                    "risk_threshold": getattr(self.config, "max_drawdown_threshold", 0.05),
                    "min_sharpe_ratio": getattr(self.config, "min_sharpe_ratio", 1.0),
                    "min_confidence_threshold": getattr(self.config, "min_confidence_threshold", 0.6),
                }
            )

            # 初始化策略管理器
            self.components.strategy_manager = StrategyManager(
                config={
                    "strategy_path": "./strategies",
                    "max_strategies": 100,
                }
            )

            # 初始化APIForge客户端
            self.components.api_forge_client = create_api_forge_client({
                "base_url": self.config.api_forge_base_url,
                "api_key": self.config.api_forge_api_key,
                "timeout": 30,
                "max_retries": 3
            })
            await self.components.api_forge_client.initialize()

            # 初始化MMS客户端
            self.components.mms_client = create_mms_client({
                "base_url": self.config.mms_base_url,
                "api_key": self.config.mms_api_key,
                "timeout": 60,
                "max_retries": 3
            })
            await self.components.mms_client.initialize()

            self.logger.info("核心组件初始化完成")

        except Exception as e:
            self.logger.error(f"核心组件初始化失败: {e}")
            raise

    async def _initialize_communication(self):
        """初始化通信组件"""
        try:
            await self._initialize_zmq_client()
            self.logger.info("通信组件初始化完成")

        except Exception as e:
            self.logger.error(f"通信组件初始化失败: {e}")
            raise

    async def _initialize_zmq_client(self):
        """初始化ZMQ客户端"""
        try:
            zmq_config = {
                "subscriber_address": self.config.zmq_scanner_endpoint,
                "publisher_address": self.config.zmq_optimizer_endpoint,
                "subscribe_topics": ["scanner.pool.preliminary"],
                "publish_topic": "optimizer.pool.trading",
                "max_buffer_size": 1000,
                "reconnect_interval": 5,
                "max_reconnect_attempts": 10
            }
            
            self.communication.zmq_client = create_zmq_client(zmq_config)
            await self.communication.zmq_client.initialize()

            # 设置消息处理回调
            self.communication.zmq_client.register_handler(
                "scanner.pool.preliminary", self._handle_trading_opportunity
            )

            self.logger.info(
                f"ZMQ客户端初始化完成 - "
                f"订阅端点: {self.config.zmq_scanner_endpoint}, "
                f"发布端点: {self.config.zmq_optimizer_endpoint}"
            )

        except Exception as e:
            self.logger.error(f"ZMQ客户端初始化失败: {e}")
            raise

    async def start(self):
        """启动优化器"""
        if not self._initialized:
            await self.initialize()

        if self.state.is_running:
            self.logger.warning("优化器已在运行中")
            return

        try:
            self.state.is_running = True
            self.logger.info("策略优化模组启动")

            # 启动ZMQ客户端
            if self.communication.zmq_client:
                await self.communication.zmq_client.start()

            # 启动主运行循环
            await self.run()

        except Exception as e:
            self.logger.error(f"启动失败: {e}")
            self.state.is_running = False
            raise

    async def stop(self):
        """停止优化器"""
        if not self.state.is_running:
            self.logger.warning("优化器未在运行")
            return

        try:
            self.state.is_running = False
            self.logger.info("正在停止策略优化模组...")

            # 停止ZMQ客户端
            if self.communication.zmq_client:
                await self.communication.zmq_client.stop()

            self.logger.info("策略优化模组已停止")

        except Exception as e:
            self.logger.error(f"停止过程中发生错误: {e}")
            raise

    async def run(self):
        """主运行循环"""
        self.logger.info("进入主运行循环")

        try:
            while self.state.is_running:
                # 处理消息队列
                if self.communication.zmq_client:
                    await asyncio.sleep(0.1)  # 简化处理

                # 短暂休眠避免CPU占用过高
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            self.logger.info("主运行循环被取消")
        except Exception as e:
            self.logger.error(f"主运行循环异常: {e}")
            raise
        finally:
            self.logger.info("退出主运行循环")

    async def _handle_trading_opportunity(self, opportunity: TradingOpportunity):
        """
        处理交易机会

        Args:
            opportunity: 扫描器发布的交易机会
        """
        try:
            self.logger.info(
                f"收到交易机会: {opportunity.symbol} - {opportunity.strategy_type}"
            )

            # 更新统计信息
            self.stats.opportunities_processed += 1
            self.stats.last_activity = datetime.now()

            # 这里可以添加具体的处理逻辑
            # 由于依赖组件可能还需要进一步集成，暂时简化处理

        except Exception as e:
            self.logger.error(f"处理交易机会时发生错误: {e}")

    async def cleanup(self):
        """清理资源"""
        try:
            self.logger.info("开始清理资源...")

            # 停止运行
            if self.state.is_running:
                await self.stop()

            # 清理通信组件
            if self.communication.zmq_client:
                await self.communication.zmq_client.stop()
                self.communication.zmq_client = None

            # 清理核心组件
            if self.components.backtest_engine:
                await self.components.backtest_engine.cleanup()
                self.components.backtest_engine = None

            if self.components.genetic_optimizer:
                await self.components.genetic_optimizer.cleanup()
                self.components.genetic_optimizer = None

            if self.components.decision_engine:
                await self.components.decision_engine.cleanup()
                self.components.decision_engine = None

            if self.components.strategy_manager:
                await self.components.strategy_manager.cleanup()
                self.components.strategy_manager = None

            # 清理外部服务客户端
            if self.components.api_forge_client:
                await self.components.api_forge_client.cleanup()
                self.components.api_forge_client = None

            if self.components.mms_client:
                await self.components.mms_client.cleanup()
                self.components.mms_client = None

            self._initialized = False
            self.logger.info("资源清理完成")

        except Exception as e:
            self.logger.error(f"清理资源时发生错误: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计信息"""
        return {
            "opportunities_processed": self.stats.opportunities_processed,
            "strategies_published": self.stats.strategies_published,
            "last_activity": self.stats.last_activity.isoformat()
            if self.stats.last_activity
            else None,
            "is_running": self.state.is_running,
            "is_initialized": self._initialized,
        }

    @property
    def is_initialized(self):
        return self._initialized

    @property
    def is_running(self):
        return self.state.is_running


async def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)

    # 创建优化器实例
    optimizer = StrategyOptimizationModule()

    try:
        # 启动优化器
        await optimizer.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"运行时发生错误: {e}")
    finally:
        # 清理资源
        await optimizer.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
