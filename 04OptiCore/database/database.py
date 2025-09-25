"""数据库管理模块。

提供数据库连接、会话管理和数据操作功能，包括优化任务、策略、回测报告等数据的存储和查询。
"""
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from database.models import (
    BacktestReport,
    Base,
    OptimizationResult,
    OptimizationTask,
    ParameterPackage,
    Strategy,
    create_tables,
)

settings = get_settings()


class DatabaseManager:
    """
    数据库管理器

    负责：
    1. 数据库连接管理
    2. 会话管理
    3. 数据库初始化
    4. 数据操作封装
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.logger = logging.getLogger(__name__)

        # 创建引擎
        self.engine = create_engine(
            self.database_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
        )

        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    async def initialize(self):
        """
        初始化数据库
        """
        try:
            self.logger.info("正在初始化数据库...")

            # 创建所有表
            create_tables(self.engine)

            # 初始化默认数据
            await self._initialize_default_data()

            self.logger.info("数据库初始化完成")

        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise

    async def _initialize_default_data(self):
        """
        初始化默认数据
        """
        with self.get_session() as session:
            try:
                # 检查是否已有策略数据
                existing_strategies = session.query(Strategy).count()
                if existing_strategies > 0:
                    self.logger.info("数据库已包含策略数据，跳过初始化")
                    return

                # 插入默认策略
                default_strategies = [
                    {
                        "strategy_id": "grid_v1.2",
                        "name": "网格交易策略",
                        "version": "1.2",
                        "description": "基于价格网格的自动交易策略，适用于震荡市场",
                        "parameters_schema": {
                            "grid_num": {
                                "type": "int",
                                "min": 5,
                                "max": 50,
                                "default": 20,
                            },
                            "profit_ratio": {
                                "type": "float",
                                "min": 0.005,
                                "max": 0.1,
                                "default": 0.02,
                            },
                            "stop_loss": {
                                "type": "float",
                                "min": 0.01,
                                "max": 0.2,
                                "default": 0.05,
                            },
                            "grid_spacing": {
                                "type": "float",
                                "min": 0.001,
                                "max": 0.05,
                                "default": 0.01,
                            },
                            "max_position": {
                                "type": "float",
                                "min": 0.1,
                                "max": 1.0,
                                "default": 0.5,
                            },
                        },
                        "risk_limits": {
                            "max_drawdown": 0.15,
                            "max_position_size": 0.3,
                            "daily_loss_limit": 0.05,
                        },
                        "performance_metrics": {
                            "expected_return": 0.12,
                            "sharpe_ratio": 1.2,
                            "max_drawdown": 0.08,
                            "win_rate": 0.65,
                        },
                    },
                    {
                        "strategy_id": "ma_cross_v1.0",
                        "name": "均线交叉策略",
                        "version": "1.0",
                        "description": "基于快慢均线交叉的趋势跟踪策略",
                        "parameters_schema": {
                            "fast_period": {
                                "type": "int",
                                "min": 5,
                                "max": 50,
                                "default": 10,
                            },
                            "slow_period": {
                                "type": "int",
                                "min": 10,
                                "max": 200,
                                "default": 30,
                            },
                            "signal_threshold": {
                                "type": "float",
                                "min": 0.001,
                                "max": 0.05,
                                "default": 0.02,
                            },
                            "stop_loss": {
                                "type": "float",
                                "min": 0.01,
                                "max": 0.2,
                                "default": 0.03,
                            },
                            "take_profit": {
                                "type": "float",
                                "min": 0.02,
                                "max": 0.5,
                                "default": 0.06,
                            },
                        },
                        "risk_limits": {
                            "max_drawdown": 0.12,
                            "max_position_size": 0.4,
                            "daily_loss_limit": 0.04,
                        },
                        "performance_metrics": {
                            "expected_return": 0.15,
                            "sharpe_ratio": 1.5,
                            "max_drawdown": 0.06,
                            "win_rate": 0.58,
                        },
                    },
                    {
                        "strategy_id": "rsi_reversal_v1.1",
                        "name": "RSI反转策略",
                        "version": "1.1",
                        "description": "基于RSI指标的反转交易策略",
                        "parameters_schema": {
                            "rsi_period": {
                                "type": "int",
                                "min": 10,
                                "max": 30,
                                "default": 14,
                            },
                            "oversold_threshold": {
                                "type": "float",
                                "min": 20,
                                "max": 40,
                                "default": 30,
                            },
                            "overbought_threshold": {
                                "type": "float",
                                "min": 60,
                                "max": 80,
                                "default": 70,
                            },
                            "stop_loss": {
                                "type": "float",
                                "min": 0.01,
                                "max": 0.15,
                                "default": 0.04,
                            },
                            "take_profit": {
                                "type": "float",
                                "min": 0.02,
                                "max": 0.3,
                                "default": 0.08,
                            },
                        },
                        "risk_limits": {
                            "max_drawdown": 0.10,
                            "max_position_size": 0.25,
                            "daily_loss_limit": 0.03,
                        },
                        "performance_metrics": {
                            "expected_return": 0.18,
                            "sharpe_ratio": 1.8,
                            "max_drawdown": 0.05,
                            "win_rate": 0.72,
                        },
                    },
                ]

                for strategy_data in default_strategies:
                    strategy = Strategy(
                        strategy_id=strategy_data["strategy_id"],
                        name=strategy_data["name"],
                        version=strategy_data["version"],
                        description=strategy_data["description"],
                        parameters_schema=json.dumps(
                            strategy_data["parameters_schema"]
                        ),
                        risk_limits=json.dumps(strategy_data["risk_limits"]),
                        performance_metrics=json.dumps(
                            strategy_data["performance_metrics"]
                        ),
                        is_active=True,
                    )
                    session.add(strategy)

                session.commit()
                self.logger.info(f"已初始化 {len(default_strategies)} 个默认策略")

            except Exception as e:
                session.rollback()
                self.logger.error(f"初始化默认数据失败: {e}")
                raise

    @contextmanager
    def get_session(self) -> Session:
        """
        获取数据库会话（上下文管理器）

        Yields:
            Session: 数据库会话
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            self.logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    async def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        获取策略信息

        Args:
            strategy_id: 策略ID

        Returns:
            策略信息字典或None
        """
        with self.get_session() as session:
            strategy = (
                session.query(Strategy)
                .filter(Strategy.strategy_id == strategy_id)
                .first()
            )

            return strategy.to_dict() if strategy else None

    async def get_all_strategies(
        self, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取所有策略

        Args:
            active_only: 是否只返回活跃策略

        Returns:
            策略列表
        """
        with self.get_session() as session:
            query = session.query(Strategy)

            if active_only:
                query = query.filter(Strategy.is_active == True)

            strategies = query.all()
            return [strategy.to_dict() for strategy in strategies]

    async def create_backtest_report(self, report_data: Dict[str, Any]) -> str:
        """
        创建回测报告

        Args:
            report_data: 回测报告数据

        Returns:
            报告ID
        """
        with self.get_session() as session:
            report = BacktestReport(
                report_id=report_data["report_id"],
                strategy_id=report_data["strategy_id"],
                symbol=report_data["symbol"],
                start_date=datetime.fromisoformat(report_data["start_date"]),
                end_date=datetime.fromisoformat(report_data["end_date"]),
                initial_capital=report_data["initial_capital"],
                final_capital=report_data["final_capital"],
                total_return=report_data["total_return"],
                annual_return=report_data.get("annual_return"),
                max_drawdown=report_data.get("max_drawdown"),
                sharpe_ratio=report_data.get("sharpe_ratio"),
                win_rate=report_data.get("win_rate"),
                total_trades=report_data.get("total_trades"),
                parameters=json.dumps(report_data.get("parameters", {})),
                detailed_results=json.dumps(report_data.get("detailed_results", {})),
            )

            session.add(report)
            session.commit()

            return report.report_id

    async def create_optimization_task(self, task_data: Dict[str, Any]) -> str:
        """
        创建优化任务

        Args:
            task_data: 任务数据

        Returns:
            任务ID
        """
        with self.get_session() as session:
            task = OptimizationTask(
                task_id=task_data["task_id"],
                strategy_id=task_data["strategy_id"],
                symbol=task_data["symbol"],
                optimization_method=task_data["optimization_method"],
                parameter_space=json.dumps(task_data.get("parameter_space", {})),
                objective_function=task_data.get("objective_function", "return"),
                status="pending",
            )

            session.add(task)
            session.commit()

            return task.task_id

    async def update_optimization_task_status(
        self,
        task_id: str,
        status: str,
        progress: float = None,
        error_message: str = None,
    ):
        """
        更新优化任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-1）
            error_message: 错误信息
        """
        with self.get_session() as session:
            task = (
                session.query(OptimizationTask)
                .filter(OptimizationTask.task_id == task_id)
                .first()
            )

            if task:
                task.status = status
                task.updated_at = datetime.utcnow()

                if progress is not None:
                    task.progress = progress

                if error_message:
                    task.error_message = error_message

                if status == "running" and not task.start_time:
                    task.start_time = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    task.end_time = datetime.utcnow()

                session.commit()

    async def create_optimization_result(self, result_data: Dict[str, Any]) -> str:
        """
        创建优化结果

        Args:
            result_data: 结果数据

        Returns:
            结果ID
        """
        with self.get_session() as session:
            result = OptimizationResult(
                result_id=result_data["result_id"],
                task_id=result_data["task_id"],
                backtest_report_id=result_data["backtest_report_id"],
                generation=result_data.get("generation"),
                individual_id=result_data.get("individual_id"),
                parameters=json.dumps(result_data["parameters"]),
                fitness_score=result_data["fitness_score"],
                objective_values=json.dumps(result_data.get("objective_values", {})),
                constraints_satisfied=result_data.get("constraints_satisfied", True),
                rank=result_data.get("rank"),
            )

            session.add(result)
            session.commit()

            return result.result_id

    async def create_parameter_package(self, package_data: Dict[str, Any]) -> str:
        """
        创建参数包

        Args:
            package_data: 参数包数据

        Returns:
            参数包ID
        """
        with self.get_session() as session:
            package = ParameterPackage(
                package_id=package_data["package_id"],
                optimization_result_id=package_data["optimization_result_id"],
                symbol=package_data["symbol"],
                strategy_id=package_data["strategy_id"],
                action=package_data["action"],
                confidence=package_data["confidence"],
                position_size=package_data["position_size"],
                stop_loss=package_data.get("stop_loss"),
                take_profit=package_data.get("take_profit"),
                parameters=json.dumps(package_data["parameters"]),
                risk_metrics=json.dumps(package_data.get("risk_metrics", {})),
                expected_return=package_data.get("expected_return"),
                max_drawdown=package_data.get("max_drawdown"),
                reasoning=package_data.get("reasoning"),
                expires_at=datetime.utcnow() + timedelta(hours=24),  # 24小时后过期
            )

            session.add(package)
            session.commit()

            return package.package_id

    async def get_optimization_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取优化任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典或None
        """
        with self.get_session() as session:
            task = (
                session.query(OptimizationTask)
                .filter(OptimizationTask.task_id == task_id)
                .first()
            )

            return task.to_dict() if task else None

    async def get_backtest_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        获取回测报告

        Args:
            report_id: 报告ID

        Returns:
            报告信息字典或None
        """
        with self.get_session() as session:
            report = (
                session.query(BacktestReport)
                .filter(BacktestReport.report_id == report_id)
                .first()
            )

            return report.to_dict() if report else None

    async def get_recent_parameter_packages(
        self, symbol: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取最近的参数包

        Args:
            symbol: 交易对（可选）
            limit: 返回数量限制

        Returns:
            参数包列表
        """
        with self.get_session() as session:
            query = session.query(ParameterPackage).filter(
                ParameterPackage.status == "active"
            )

            if symbol:
                query = query.filter(ParameterPackage.symbol == symbol)

            packages = (
                query.order_by(ParameterPackage.published_at.desc()).limit(limit).all()
            )

            return [package.to_dict() for package in packages]

    async def cleanup_expired_packages(self):
        """
        清理过期的参数包
        """
        with self.get_session() as session:
            expired_count = (
                session.query(ParameterPackage)
                .filter(
                    ParameterPackage.expires_at < datetime.utcnow(),
                    ParameterPackage.status == "active",
                )
                .update({"status": "expired"})
            )

            session.commit()

            if expired_count > 0:
                self.logger.info(f"已清理 {expired_count} 个过期参数包")

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        with self.get_session() as session:
            stats = {
                "strategies_count": session.query(Strategy).count(),
                "active_strategies_count": session.query(Strategy)
                .filter(Strategy.is_active == True)
                .count(),
                "backtest_reports_count": session.query(BacktestReport).count(),
                "optimization_tasks_count": session.query(OptimizationTask).count(),
                "optimization_results_count": session.query(OptimizationResult).count(),
                "parameter_packages_count": session.query(ParameterPackage).count(),
                "active_packages_count": session.query(ParameterPackage)
                .filter(ParameterPackage.status == "active")
                .count(),
            }

            return stats

    def close(self):
        """
        关闭数据库连接
        """
        if hasattr(self, "engine"):
            self.engine.dispose()
            self.logger.info("数据库连接已关闭")


# 全局数据库管理器实例
database_manager = DatabaseManager()


# 便捷函数
async def get_database_manager() -> DatabaseManager:
    """
    获取数据库管理器实例

    Returns:
        DatabaseManager: 数据库管理器
    """
    return database_manager
