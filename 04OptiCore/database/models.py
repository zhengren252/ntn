"""数据库模型定义模块。

定义了优化系统中使用的所有数据库表模型，包括策略、优化任务、参数包、优化结果和回测报告等。
"""
import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Strategy(Base):
    """
    策略表 - 存储策略基本信息
    """

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    description = Column(Text)
    parameters_schema = Column(Text)  # JSON格式的参数模式
    risk_limits = Column(Text)  # JSON格式的风险限制
    performance_metrics = Column(Text)  # JSON格式的性能指标
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    backtest_reports = relationship("BacktestReport", back_populates="strategy")
    optimization_tasks = relationship("OptimizationTask", back_populates="strategy")

    # 索引
    __table_args__ = (
        Index("idx_strategy_active", "is_active"),
        Index("idx_strategy_created", "created_at"),
    )

    def to_dict(self):
        """将回测报告对象转换为字典格式。

        Returns:
            dict: 包含回测报告所有字段的字典
        """
        """将策略对象转换为字典格式。
        
        Returns:
            dict: 包含策略所有字段的字典
        """
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "parameters_schema": json.loads(self.parameters_schema)
            if self.parameters_schema
            else {},
            "risk_limits": json.loads(self.risk_limits) if self.risk_limits else {},
            "performance_metrics": json.loads(self.performance_metrics)
            if self.performance_metrics
            else {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BacktestReport(Base):
    """
    回测报告表 - 存储回测结果
    """

    __tablename__ = "backtest_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(50), unique=True, nullable=False, index=True)
    strategy_id = Column(
        String(50), ForeignKey("strategies.strategy_id"), nullable=False
    )
    symbol = Column(String(20), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    annual_return = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)
    parameters = Column(Text)  # JSON格式的策略参数
    detailed_results = Column(Text)  # JSON格式的详细结果
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    strategy = relationship("Strategy", back_populates="backtest_reports")
    optimization_results = relationship(
        "OptimizationResult", back_populates="backtest_report"
    )

    # 索引
    __table_args__ = (
        Index("idx_backtest_symbol", "symbol"),
        Index("idx_backtest_strategy", "strategy_id"),
        Index("idx_backtest_return", "total_return"),
        Index("idx_backtest_created", "created_at"),
    )

    def to_dict(self):
        """将回测报告对象转换为字典格式。

        Returns:
            dict: 包含回测报告所有字段的字典
        """
        return {
            "id": self.id,
            "report_id": self.report_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "parameters": json.loads(self.parameters) if self.parameters else {},
            "detailed_results": json.loads(self.detailed_results)
            if self.detailed_results
            else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OptimizationTask(Base):
    """
    优化任务表 - 存储参数优化任务信息
    """

    __tablename__ = "optimization_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), unique=True, nullable=False, index=True)
    strategy_id = Column(
        String(50), ForeignKey("strategies.strategy_id"), nullable=False
    )
    symbol = Column(String(20), nullable=False)
    optimization_method = Column(
        String(50), nullable=False
    )  # 'genetic', 'grid', 'bayesian'
    parameter_space = Column(Text)  # JSON格式的参数空间
    objective_function = Column(String(50))  # 'return', 'sharpe', 'profit_factor'
    status = Column(
        String(20), default="pending"
    )  # 'pending', 'running', 'completed', 'failed'
    progress = Column(Float, default=0.0)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    strategy = relationship("Strategy", back_populates="optimization_tasks")
    optimization_results = relationship(
        "OptimizationResult", back_populates="optimization_task"
    )

    # 索引
    __table_args__ = (
        Index("idx_optimization_status", "status"),
        Index("idx_optimization_symbol", "symbol"),
        Index("idx_optimization_strategy", "strategy_id"),
        Index("idx_optimization_created", "created_at"),
    )

    def to_dict(self):
        """将优化任务对象转换为字典格式。

        Returns:
            dict: 包含优化任务所有字段的字典
        """
        return {
            "id": self.id,
            "task_id": self.task_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "optimization_method": self.optimization_method,
            "parameter_space": json.loads(self.parameter_space)
            if self.parameter_space
            else {},
            "objective_function": self.objective_function,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OptimizationResult(Base):
    """
    优化结果表 - 存储参数优化结果
    """

    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(50), unique=True, nullable=False, index=True)
    task_id = Column(
        String(50), ForeignKey("optimization_tasks.task_id"), nullable=False
    )
    backtest_report_id = Column(
        String(50), ForeignKey("backtest_reports.report_id"), nullable=False
    )
    generation = Column(Integer)  # 遗传算法代数
    individual_id = Column(Integer)  # 个体ID
    parameters = Column(Text, nullable=False)  # JSON格式的优化参数
    fitness_score = Column(Float, nullable=False)
    objective_values = Column(Text)  # JSON格式的目标函数值
    constraints_satisfied = Column(Boolean, default=True)
    rank = Column(Integer)  # 在该代中的排名
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    optimization_task = relationship(
        "OptimizationTask", back_populates="optimization_results"
    )
    backtest_report = relationship(
        "BacktestReport", back_populates="optimization_results"
    )
    parameter_packages = relationship(
        "ParameterPackage", back_populates="optimization_result"
    )

    # 索引
    __table_args__ = (
        Index("idx_optimization_result_task", "task_id"),
        Index("idx_optimization_result_fitness", "fitness_score"),
        Index("idx_optimization_result_generation", "generation"),
        Index("idx_optimization_result_rank", "rank"),
    )

    def to_dict(self):
        """将优化结果对象转换为字典格式。

        Returns:
            dict: 包含优化结果所有字段的字典
        """
        return {
            "id": self.id,
            "result_id": self.result_id,
            "task_id": self.task_id,
            "backtest_report_id": self.backtest_report_id,
            "generation": self.generation,
            "individual_id": self.individual_id,
            "parameters": json.loads(self.parameters) if self.parameters else {},
            "fitness_score": self.fitness_score,
            "objective_values": json.loads(self.objective_values)
            if self.objective_values
            else {},
            "constraints_satisfied": self.constraints_satisfied,
            "rank": self.rank,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ParameterPackage(Base):
    """
    参数包表 - 存储最终发布的策略参数包
    """

    __tablename__ = "parameter_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(String(50), unique=True, nullable=False, index=True)
    optimization_result_id = Column(
        String(50), ForeignKey("optimization_results.result_id"), nullable=False
    )
    symbol = Column(String(20), nullable=False)
    strategy_id = Column(String(50), nullable=False)
    action = Column(String(10), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    confidence = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    parameters = Column(Text, nullable=False)  # JSON格式的策略参数
    risk_metrics = Column(Text)  # JSON格式的风险指标
    expected_return = Column(Float)
    max_drawdown = Column(Float)
    reasoning = Column(Text)  # 决策理由
    status = Column(
        String(20), default="active"
    )  # 'active', 'executed', 'cancelled', 'expired'
    published_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    executed_at = Column(DateTime)

    # 关系
    optimization_result = relationship(
        "OptimizationResult", back_populates="parameter_packages"
    )

    # 索引
    __table_args__ = (
        Index("idx_parameter_package_symbol", "symbol"),
        Index("idx_parameter_package_strategy", "strategy_id"),
        Index("idx_parameter_package_status", "status"),
        Index("idx_parameter_package_confidence", "confidence"),
        Index("idx_parameter_package_published", "published_at"),
    )

    def to_dict(self):
        """将参数包对象转换为字典格式。

        Returns:
            dict: 包含参数包所有字段的字典
        """
        return {
            "id": self.id,
            "package_id": self.package_id,
            "optimization_result_id": self.optimization_result_id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "action": self.action,
            "confidence": self.confidence,
            "position_size": self.position_size,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "parameters": json.loads(self.parameters) if self.parameters else {},
            "risk_metrics": json.loads(self.risk_metrics) if self.risk_metrics else {},
            "expected_return": self.expected_return,
            "max_drawdown": self.max_drawdown,
            "reasoning": self.reasoning,
            "status": self.status,
            "published_at": self.published_at.isoformat()
            if self.published_at
            else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


# 创建所有表的函数
def create_tables(engine):
    """
    创建所有数据库表

    Args:
        engine: SQLAlchemy引擎
    """
    Base.metadata.create_all(engine)


# 删除所有表的函数
def drop_tables(engine):
    """
    删除所有数据库表

    Args:
        engine: SQLAlchemy引擎
    """
    Base.metadata.drop_all(engine)
