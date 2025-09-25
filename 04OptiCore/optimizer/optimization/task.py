from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OptimizationGoal(Enum):
    """优化目标枚举"""

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class OptimizationStatus(Enum):
    """优化状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class OptimizationTask:
    """
    优化任务类
    """

    task_id: str
    strategy_id: str
    strategy_type: str
    parameter_space: Dict[str, Any]
    fitness_function: Callable[[Dict[str, Any]], float]
    target_metric: str
    optimization_goal: str = "maximize"
    max_generations: Optional[int] = None
    population_size: Optional[int] = None
    timeout_seconds: Optional[float] = None
    constraints: Optional[List[Callable[[Dict[str, Any]], bool]]] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: OptimizationStatus = OptimizationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """后初始化处理"""
        if isinstance(self.optimization_goal, str):
            try:
                self.optimization_goal = OptimizationGoal(self.optimization_goal)
            except ValueError:
                self.optimization_goal = OptimizationGoal.MAXIMIZE

        if isinstance(self.status, str):
            try:
                self.status = OptimizationStatus(self.status)
            except ValueError:
                self.status = OptimizationStatus.PENDING

    def is_maximization(self) -> bool:
        """判断是否为最大化优化"""
        return self.optimization_goal == OptimizationGoal.MAXIMIZE

    def is_minimization(self) -> bool:
        """判断是否为最小化优化"""
        return self.optimization_goal == OptimizationGoal.MINIMIZE

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        验证参数是否满足约束条件

        Args:
            parameters: 待验证的参数

        Returns:
            是否满足所有约束条件
        """
        if not self.constraints:
            return True

        return all(constraint(parameters) for constraint in self.constraints)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "parameter_space": self.parameter_space,
            "target_metric": self.target_metric,
            "optimization_goal": self.optimization_goal.value
            if isinstance(self.optimization_goal, OptimizationGoal)
            else self.optimization_goal,
            "max_generations": self.max_generations,
            "population_size": self.population_size,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value
            if isinstance(self.status, OptimizationStatus)
            else self.status,
            "metadata": self.metadata,
        }


@dataclass
class OptimizationResult:
    """
    优化结果类
    """

    task_id: str
    strategy_id: str
    best_parameters: Dict[str, Any]
    best_fitness: float
    generations_completed: int
    total_evaluations: int
    optimization_time: float
    convergence_generation: Optional[int] = None
    fitness_history: List[float] = field(default_factory=list)
    diversity_history: List[float] = field(default_factory=list)
    parameter_history: List[Dict[str, Any]] = field(default_factory=list)
    timeout_occurred: bool = False
    error_message: Optional[str] = None
    status: OptimizationStatus = OptimizationStatus.COMPLETED
    completed_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """后初始化处理"""
        if isinstance(self.status, str):
            try:
                self.status = OptimizationStatus(self.status)
            except ValueError:
                self.status = OptimizationStatus.COMPLETED

    def get_improvement_rate(self) -> float:
        """
        计算适应度改进率

        Returns:
            从初始到最终的适应度改进率
        """
        if len(self.fitness_history) < 2:
            return 0.0

        initial_fitness = self.fitness_history[0]
        final_fitness = self.fitness_history[-1]

        if initial_fitness == 0:
            return float("inf") if final_fitness > 0 else 0.0

        return (final_fitness - initial_fitness) / abs(initial_fitness)

    def get_convergence_rate(self) -> float:
        """
        计算收敛速度

        Returns:
            收敛速度（代数/总代数）
        """
        if self.convergence_generation is None or self.generations_completed == 0:
            return 1.0

        return self.convergence_generation / self.generations_completed

    def get_average_diversity(self) -> float:
        """
        计算平均种群多样性

        Returns:
            平均多样性值
        """
        if not self.diversity_history:
            return 0.0

        return sum(self.diversity_history) / len(self.diversity_history)

    def is_successful(self) -> bool:
        """
        判断优化是否成功

        Returns:
            优化是否成功完成
        """
        return (
            self.status == OptimizationStatus.COMPLETED and self.error_message is None
        )

    def get_final_statistics(self) -> Dict[str, Any]:
        """
        获取最终统计信息

        Returns:
            包含各种统计指标的字典
        """
        return {
            "best_fitness": self.best_fitness,
            "generations_completed": self.generations_completed,
            "total_evaluations": self.total_evaluations,
            "optimization_time": self.optimization_time,
            "improvement_rate": self.get_improvement_rate(),
            "convergence_rate": self.get_convergence_rate(),
            "average_diversity": self.get_average_diversity(),
            "timeout_occurred": self.timeout_occurred,
            "successful": self.is_successful(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "strategy_id": self.strategy_id,
            "best_parameters": self.best_parameters,
            "best_fitness": self.best_fitness,
            "generations_completed": self.generations_completed,
            "total_evaluations": self.total_evaluations,
            "optimization_time": self.optimization_time,
            "convergence_generation": self.convergence_generation,
            "fitness_history": self.fitness_history,
            "diversity_history": self.diversity_history,
            "parameter_history": self.parameter_history,
            "timeout_occurred": self.timeout_occurred,
            "error_message": self.error_message,
            "status": self.status.value
            if isinstance(self.status, OptimizationStatus)
            else self.status,
            "completed_at": self.completed_at.isoformat(),
            "metadata": self.metadata,
            "statistics": self.get_final_statistics(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationResult":
        """从字典创建优化结果"""
        # 处理日期时间字段
        if "completed_at" in data and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        # 移除统计信息字段（这是计算得出的）
        data.pop("statistics", None)

        return cls(**data)
