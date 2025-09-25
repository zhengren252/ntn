#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遗传算法个体定义
NeuroTrade Nexus (NTN) - Genetic Algorithm Individual

核心功能：
1. 遗传算法个体表示
2. 个体适应度计算
3. 个体操作（交叉、变异）
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import numpy as np


@dataclass
class Individual:
    """遗传算法个体"""

    genes: List[Union[int, float]] = field(default_factory=list)
    fitness: Optional[float] = None
    parameters: Optional[Dict[str, Union[int, float]]] = None
    generation: int = 0

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

    def copy(self) -> "Individual":
        """创建个体副本"""
        return Individual(
            genes=self.genes.copy(),
            fitness=self.fitness,
            parameters=self.parameters.copy() if self.parameters else {},
            generation=self.generation,
        )

    def set_genes(self, genes: List[Union[int, float]]):
        """设置基因"""
        self.genes = genes.copy()
        self.fitness = None  # 重置适应度

    def get_gene(self, index: int) -> Union[int, float]:
        """获取指定位置的基因"""
        if 0 <= index < len(self.genes):
            return self.genes[index]
        raise IndexError(f"Gene index {index} out of range")

    def set_gene(self, index: int, value: Union[int, float]):
        """设置指定位置的基因"""
        if 0 <= index < len(self.genes):
            self.genes[index] = value
            self.fitness = None  # 重置适应度
        else:
            raise IndexError(f"Gene index {index} out of range")

    def mutate(self, mutation_rate: float, param_ranges: Dict[str, Dict[str, Any]]):
        """变异操作"""
        param_names = list(param_ranges.keys())

        for i, param_name in enumerate(param_names):
            if random.random() < mutation_rate:
                param_info = param_ranges[param_name]

                if param_info["type"] == "int":
                    # 整数变异
                    current_value = int(self.genes[i])
                    mutation_range = max(
                        1, (param_info["max"] - param_info["min"]) // 10
                    )

                    new_value = current_value + random.randint(
                        -mutation_range, mutation_range
                    )
                    new_value = max(
                        param_info["min"], min(param_info["max"], new_value)
                    )

                    self.genes[i] = new_value

                else:  # float
                    # 浮点变异（高斯变异）
                    current_value = self.genes[i]
                    mutation_std = (param_info["max"] - param_info["min"]) * 0.1

                    new_value = current_value + random.gauss(0, mutation_std)
                    new_value = max(
                        param_info["min"], min(param_info["max"], new_value)
                    )

                    self.genes[i] = new_value

        self.fitness = None  # 重置适应度

    def crossover(self, other: "Individual") -> tuple["Individual", "Individual"]:
        """交叉操作"""
        if len(self.genes) != len(other.genes):
            raise ValueError("Cannot crossover individuals with different gene lengths")

        if len(self.genes) <= 1:
            return self.copy(), other.copy()

        # 单点交叉
        crossover_point = random.randint(1, len(self.genes) - 1)

        child1_genes = self.genes[:crossover_point] + other.genes[crossover_point:]
        child2_genes = other.genes[:crossover_point] + self.genes[crossover_point:]

        child1 = Individual(
            genes=child1_genes, generation=max(self.generation, other.generation) + 1
        )
        child2 = Individual(
            genes=child2_genes, generation=max(self.generation, other.generation) + 1
        )

        return child1, child2

    def to_parameters(
        self, param_ranges: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Union[int, float]]:
        """将基因转换为参数字典"""
        params = {}
        param_names = list(param_ranges.keys())

        for i, param_name in enumerate(param_names):
            if i < len(self.genes):
                param_info = param_ranges[param_name]

                if param_info["type"] == "int":
                    params[param_name] = int(self.genes[i])
                else:
                    params[param_name] = float(self.genes[i])

        self.parameters = params
        return params

    def to_params(self, param_ranges: Dict[str, Dict[str, Any]] = None) -> Dict[str, Union[int, float]]:
        """将个体转换为参数字典（别名方法）"""
        if self.parameters:
            return self.parameters
        elif param_ranges:
            return self.to_parameters(param_ranges)
        else:
            # 如果没有参数范围信息，直接返回现有参数
            return self.parameters or {}

    @classmethod
    def from_parameters(
        cls,
        parameters: Dict[str, Union[int, float]],
        param_ranges: Dict[str, Dict[str, Any]],
    ) -> "Individual":
        """从参数字典创建个体"""
        genes = []
        param_names = list(param_ranges.keys())

        for param_name in param_names:
            if param_name in parameters:
                genes.append(parameters[param_name])
            else:
                # 如果参数缺失，使用随机值
                param_info = param_ranges[param_name]
                if param_info["type"] == "int":
                    value = random.randint(param_info["min"], param_info["max"])
                else:
                    value = random.uniform(param_info["min"], param_info["max"])
                genes.append(value)

        individual = cls(genes=genes, parameters=parameters)
        return individual

    @classmethod
    def random(cls, param_ranges: Dict[str, Dict[str, Any]]) -> "Individual":
        """创建随机个体"""
        genes = []
        param_names = list(param_ranges.keys())

        for param_name in param_names:
            param_info = param_ranges[param_name]

            if param_info["type"] == "int":
                value = random.randint(param_info["min"], param_info["max"])
            else:
                value = random.uniform(param_info["min"], param_info["max"])

            genes.append(value)

        individual = cls(genes=genes)
        individual.to_parameters(param_ranges)
        return individual

    @classmethod
    def create_random(cls, parameter_space) -> "Individual":
        """从ParameterSpace创建随机个体"""
        if hasattr(parameter_space, "random_sample"):
            # 如果是ParameterSpace对象
            parameters = parameter_space.random_sample()
            # 从ParameterSpace获取参数范围
            param_ranges = {}
            if hasattr(parameter_space, "parameters"):
                for name, param_range in parameter_space.parameters.items():
                    if hasattr(param_range, "min_value") and hasattr(
                        param_range, "max_value"
                    ):
                        param_ranges[name] = {
                            "type": param_range.param_type,
                            "min": param_range.min_value,
                            "max": param_range.max_value,
                        }
            return cls.from_parameters(parameters, param_ranges)
        else:
            # 如果是字典格式的参数范围
            return cls.random(parameter_space)

    @classmethod
    def random_create(cls, parameter_space) -> "Individual":
        """创建随机个体（别名方法）"""
        return cls.create_random(parameter_space)

    def __str__(self) -> str:
        return f"Individual(genes={self.genes}, fitness={self.fitness}, generation={self.generation})"

    def __repr__(self) -> str:
        return self.__str__()

    def __lt__(self, other: "Individual") -> bool:
        """比较操作符（用于排序）"""
        if self.fitness is None and other.fitness is None:
            return False
        if self.fitness is None:
            return True
        if other.fitness is None:
            return False
        return self.fitness < other.fitness

    def __eq__(self, other: "Individual") -> bool:
        """相等操作符"""
        if not isinstance(other, Individual):
            return False
        return self.genes == other.genes and self.fitness == other.fitness


class Population:
    """种群管理器"""

    def __init__(self, individuals: List[Individual] = None):
        self.individuals = individuals or []

    def add_individual(self, individual: Individual):
        """添加个体"""
        self.individuals.append(individual)

    def size(self) -> int:
        """获取种群大小"""
        return len(self.individuals)

    def get_best(self) -> Optional[Individual]:
        """获取最优个体"""
        if not self.individuals:
            return None

        valid_individuals = [ind for ind in self.individuals if ind.fitness is not None]
        if not valid_individuals:
            return None

        return max(valid_individuals, key=lambda x: x.fitness)

    def get_worst(self) -> Optional[Individual]:
        """获取最差个体"""
        if not self.individuals:
            return None

        valid_individuals = [ind for ind in self.individuals if ind.fitness is not None]
        if not valid_individuals:
            return None

        return min(valid_individuals, key=lambda x: x.fitness)

    def calculate_diversity(self) -> float:
        """计算种群多样性"""
        if len(self.individuals) < 2:
            return 0.0

        total_distance = 0.0
        count = 0

        for i in range(len(self.individuals)):
            for j in range(i + 1, len(self.individuals)):
                # 计算两个个体之间的欧几里得距离
                ind1 = self.individuals[i]
                ind2 = self.individuals[j]

                if len(ind1.genes) == len(ind2.genes):
                    distance = (
                        sum((g1 - g2) ** 2 for g1, g2 in zip(ind1.genes, ind2.genes))
                        ** 0.5
                    )
                    total_distance += distance
                    count += 1

        return total_distance / count if count > 0 else 0.0

    def get_average_fitness(self) -> float:
        """获取平均适应度"""
        valid_individuals = [ind for ind in self.individuals if ind.fitness is not None]
        if not valid_individuals:
            return 0.0
        return sum(ind.fitness for ind in valid_individuals) / len(valid_individuals)

    def sort_by_fitness(self, reverse: bool = True):
        """按适应度排序"""
        self.individuals.sort(
            key=lambda x: x.fitness if x.fitness is not None else -float("inf"),
            reverse=reverse,
        )

    def tournament_selection(self, tournament_size: int = 3) -> Individual:
        """锦标赛选择"""
        if tournament_size > len(self.individuals):
            tournament_size = len(self.individuals)

        tournament = random.sample(self.individuals, tournament_size)
        return max(
            tournament,
            key=lambda x: x.fitness if x.fitness is not None else -float("inf"),
        )

    def __len__(self) -> int:
        return len(self.individuals)

    def __iter__(self):
        return iter(self.individuals)

    def __getitem__(self, index) -> Individual:
        return self.individuals[index]
