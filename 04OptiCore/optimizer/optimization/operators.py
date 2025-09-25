import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np

from optimizer.optimization.individual import Individual
from optimizer.optimization.parameter_space import ParameterSpace


class SelectionOperator:
    """
    选择算子类
    """

    def __init__(self, method: str = "tournament", tournament_size: int = 3):
        self.method = method
        self.tournament_size = tournament_size

    def select(
        self, population: List[Individual], num_parents: int
    ) -> List[Individual]:
        """
        从种群中选择父代个体

        Args:
            population: 种群
            num_parents: 需要选择的父代数量

        Returns:
            选择的父代个体列表
        """
        if self.method == "tournament":
            return self._tournament_selection(population, num_parents)
        elif self.method == "roulette_wheel":
            return self._roulette_wheel_selection(population, num_parents)
        else:
            raise ValueError(f"Unknown selection method: {self.method}")

    def _tournament_selection(
        self, population: List[Individual], num_parents: int
    ) -> List[Individual]:
        """
        锦标赛选择
        """
        selected = []
        for _ in range(num_parents):
            # 随机选择锦标赛参与者
            tournament_participants = random.sample(
                population, min(self.tournament_size, len(population))
            )
            # 选择适应度最高的个体
            winner = max(tournament_participants, key=lambda x: x.fitness or 0)
            selected.append(winner.copy())
        return selected

    def _roulette_wheel_selection(
        self, population: List[Individual], num_parents: int
    ) -> List[Individual]:
        """
        轮盘赌选择
        """
        # 计算适应度总和
        fitness_values = [ind.fitness or 0 for ind in population]
        min_fitness = min(fitness_values)

        # 如果有负适应度，进行偏移
        if min_fitness < 0:
            fitness_values = [f - min_fitness + 0.001 for f in fitness_values]

        total_fitness = sum(fitness_values)
        if total_fitness == 0:
            # 如果总适应度为0，随机选择
            return random.choices(population, k=num_parents)

        # 计算选择概率
        probabilities = [f / total_fitness for f in fitness_values]

        # 根据概率选择
        selected = np.random.choice(
            population, size=num_parents, p=probabilities, replace=True
        )
        return [ind.copy() for ind in selected]


class CrossoverOperator:
    """
    交叉算子类
    """

    def __init__(self, method: str = "uniform", crossover_rate: float = 0.8):
        self.method = method
        self.crossover_rate = crossover_rate

    def crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[Individual, Individual]:
        """
        执行交叉操作

        Args:
            parent1: 父代个体1
            parent2: 父代个体2

        Returns:
            两个子代个体
        """
        if random.random() > self.crossover_rate:
            # 不进行交叉，直接返回父代副本
            return parent1.copy(), parent2.copy()

        if self.method == "uniform":
            return self._uniform_crossover(parent1, parent2)
        elif self.method == "single_point":
            return self._single_point_crossover(parent1, parent2)
        else:
            raise ValueError(f"Unknown crossover method: {self.method}")

    def _uniform_crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[Individual, Individual]:
        """
        均匀交叉
        """
        offspring1_params = {}
        offspring2_params = {}

        for param_name in parent1.parameters:
            if random.random() < 0.5:
                offspring1_params[param_name] = parent1.parameters[param_name]
                offspring2_params[param_name] = parent2.parameters[param_name]
            else:
                offspring1_params[param_name] = parent2.parameters[param_name]
                offspring2_params[param_name] = parent1.parameters[param_name]

        # 从父代获取参数范围信息
        param_ranges = getattr(parent1, "_param_ranges", {})
        if (
            not param_ranges
            and hasattr(parent1, "genes")
            and hasattr(parent1, "parameters")
        ):
            # 如果没有存储的参数范围，尝试从参数推断
            param_ranges = {}
            for param_name, value in parent1.parameters.items():
                if isinstance(value, int):
                    param_ranges[param_name] = {"type": "int", "min": 0, "max": 100}
                else:
                    param_ranges[param_name] = {"type": "float", "min": 0.0, "max": 1.0}

        offspring1 = Individual.from_parameters(offspring1_params, param_ranges)
        offspring2 = Individual.from_parameters(offspring2_params, param_ranges)

        return offspring1, offspring2

    def _single_point_crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[Individual, Individual]:
        """
        单点交叉
        """
        param_names = list(parent1.parameters.keys())
        crossover_point = random.randint(1, len(param_names) - 1)

        offspring1_params = {}
        offspring2_params = {}

        for i, param_name in enumerate(param_names):
            if i < crossover_point:
                offspring1_params[param_name] = parent1.parameters[param_name]
                offspring2_params[param_name] = parent2.parameters[param_name]
            else:
                offspring1_params[param_name] = parent2.parameters[param_name]
                offspring2_params[param_name] = parent1.parameters[param_name]

        # 从父代获取参数范围信息
        param_ranges = getattr(parent1, "_param_ranges", {})
        if (
            not param_ranges
            and hasattr(parent1, "genes")
            and hasattr(parent1, "parameters")
        ):
            # 如果没有存储的参数范围，尝试从参数推断
            param_ranges = {}
            for param_name, value in parent1.parameters.items():
                if isinstance(value, int):
                    param_ranges[param_name] = {"type": "int", "min": 0, "max": 100}
                else:
                    param_ranges[param_name] = {"type": "float", "min": 0.0, "max": 1.0}

        offspring1 = Individual.from_parameters(offspring1_params, param_ranges)
        offspring2 = Individual.from_parameters(offspring2_params, param_ranges)

        return offspring1, offspring2


class MutationOperator:
    """
    变异算子类
    """

    def __init__(
        self,
        method: str = "gaussian",
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
    ):
        self.method = method
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength

    def mutate(
        self, individual: Individual, parameter_space: ParameterSpace
    ) -> Individual:
        """
        执行变异操作

        Args:
            individual: 待变异的个体
            parameter_space: 参数空间

        Returns:
            变异后的个体
        """
        if random.random() > self.mutation_rate:
            # 不进行变异，直接返回副本
            return individual.copy()

        if self.method == "gaussian":
            return self._gaussian_mutation(individual, parameter_space)
        elif self.method == "random":
            return self._random_mutation(individual, parameter_space)
        else:
            raise ValueError(f"Unknown mutation method: {self.method}")

    def _gaussian_mutation(
        self, individual: Individual, parameter_space: ParameterSpace
    ) -> Individual:
        """
        高斯变异
        """
        mutated_params = individual.parameters.copy()

        for param_name in mutated_params:
            if random.random() < self.mutation_rate:
                param_range = parameter_space.parameters[param_name]
                current_value = mutated_params[param_name]

                # 计算变异范围
                param_range_size = param_range.max_value - param_range.min_value
                mutation_std = param_range_size * self.mutation_strength

                # 应用高斯变异
                mutation_delta = np.random.normal(0, mutation_std)
                new_value = current_value + mutation_delta

                # 确保在参数范围内
                new_value = max(
                    param_range.min_value, min(param_range.max_value, new_value)
                )

                # 处理步长约束
                if param_range.step is not None:
                    steps = round(
                        (new_value - param_range.min_value) / param_range.step
                    )
                    new_value = param_range.min_value + steps * param_range.step
                    new_value = max(
                        param_range.min_value, min(param_range.max_value, new_value)
                    )

                # 处理整数类型
                if param_range.param_type == "int":
                    new_value = int(round(new_value))

                mutated_params[param_name] = new_value

        # 从ParameterSpace获取参数范围信息
        param_ranges = {}
        for name, param_range in parameter_space.parameters.items():
            param_ranges[name] = {
                "type": param_range.param_type,
                "min": param_range.min_value,
                "max": param_range.max_value,
            }

        return Individual.from_parameters(mutated_params, param_ranges)

    def _random_mutation(
        self, individual: Individual, parameter_space: ParameterSpace
    ) -> Individual:
        """
        随机变异
        """
        mutated_params = individual.parameters.copy()

        for param_name in mutated_params:
            if random.random() < self.mutation_rate:
                # 随机重新生成该参数
                new_value = parameter_space.sample_parameter(param_name)
                mutated_params[param_name] = new_value

        # 从ParameterSpace获取参数范围信息
        param_ranges = {}
        for name, param_range in parameter_space.parameters.items():
            param_ranges[name] = {
                "type": param_range.param_type,
                "min": param_range.min_value,
                "max": param_range.max_value,
            }

        return Individual.from_parameters(mutated_params, param_ranges)
