#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遗传算法优化器测试
NeuroTrade Nexus (NTN) - Genetic Algorithm Optimizer Tests

测试覆盖：
1. 遗传算法核心功能测试
2. 参数优化流程测试
3. 种群进化测试
4. 适应度函数测试
5. 交叉和变异操作测试
6. 收敛性测试

遵循NeuroTrade Nexus测试规范：
- 独立测试：每个测试用例相互独立
- 确定性测试：使用固定随机种子确保结果可重现
- 性能测试：验证优化效率和收敛性
- 边界测试：测试极端参数和异常情况
"""

import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import get_config
from optimizer.optimization.genetic_optimizer import GeneticOptimizer
from optimizer.optimization.individual import Individual, Population
from optimizer.optimization.operators import (
    CrossoverOperator,
    MutationOperator,
    SelectionOperator,
)
from optimizer.optimization.parameter_space import ParameterSpace
from optimizer.optimization.task import (
    OptimizationResult,
    OptimizationStatus,
    OptimizationTask,
)


class TestGeneticOptimizer(unittest.TestCase):
    """
    遗传算法优化器测试类
    """

    def setUp(self):
        """
        测试初始化
        """
        # 创建测试配置
        self.test_config = {
            "genetic_algorithm": {
                "population_size": 20,
                "max_generations": 50,
                "mutation_rate": 0.1,
                "crossover_rate": 0.8,
                "elite_ratio": 0.1,
                "convergence_threshold": 0.001,
                "stagnation_limit": 10,
            },
            "optimization": {
                "timeout": 300,
                "max_concurrent": 2,
                "min_improvement": 0.01,
            },
            "database": {"path": ":memory:"},
        }

        # 创建优化器实例
        self.optimizer = GeneticOptimizer(self.test_config)

        # 设置固定随机种子确保测试结果可重现
        np.random.seed(42)

        # 创建测试参数空间
        self.test_parameter_spaces = {
            "grid_trading": {
                "grid_num": {"type": "int", "min": 5, "max": 20, "step": 1},
                "profit_ratio": {
                    "type": "float",
                    "min": 0.01,
                    "max": 0.05,
                    "step": 0.001,
                },
                "stop_loss": {"type": "float", "min": 0.05, "max": 0.2, "step": 0.01},
                "position_size": {
                    "type": "float",
                    "min": 0.1,
                    "max": 0.5,
                    "step": 0.05,
                },
            },
            "ma_crossover": {
                "fast_period": {"type": "int", "min": 3, "max": 15, "step": 1},
                "slow_period": {"type": "int", "min": 10, "max": 50, "step": 1},
                "signal_threshold": {
                    "type": "float",
                    "min": 0.005,
                    "max": 0.02,
                    "step": 0.001,
                },
                "position_size": {"type": "float", "min": 0.1, "max": 0.8, "step": 0.1},
            },
            "rsi_strategy": {
                "rsi_period": {"type": "int", "min": 10, "max": 25, "step": 1},
                "oversold_threshold": {"type": "int", "min": 20, "max": 40, "step": 5},
                "overbought_threshold": {
                    "type": "int",
                    "min": 60,
                    "max": 80,
                    "step": 5,
                },
                "position_size": {"type": "float", "min": 0.1, "max": 0.6, "step": 0.1},
            },
        }

        # 创建模拟适应度函数
        self.mock_fitness_function = self._create_mock_fitness_function()

    def tearDown(self):
        """
        测试清理
        """
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(self.optimizer.cleanup())
        except (RuntimeError, AttributeError):
            pass

    def _create_mock_fitness_function(self):
        """
        创建模拟适应度函数

        模拟一个有明确最优解的函数，用于测试优化器收敛性
        """

        def fitness_function(parameters):
            """
            模拟适应度函数：基于参数与目标值的距离计算适应度

            目标参数（最优解）：
            - grid_num: 10
            - profit_ratio: 0.02
            - stop_loss: 0.1
            - position_size: 0.3
            """
            target_params = {
                "grid_num": 10,
                "profit_ratio": 0.02,
                "stop_loss": 0.1,
                "position_size": 0.3,
            }

            # 计算参数与目标值的归一化距离
            total_distance = 0
            param_count = 0

            for param_name, target_value in target_params.items():
                if param_name in parameters:
                    actual_value = parameters[param_name]

                    # 归一化距离计算
                    if param_name == "grid_num":
                        normalized_distance = (
                            abs(actual_value - target_value) / 15
                        )  # 范围5-20
                    elif param_name == "profit_ratio":
                        normalized_distance = (
                            abs(actual_value - target_value) / 0.04
                        )  # 范围0.01-0.05
                    elif param_name == "stop_loss":
                        normalized_distance = (
                            abs(actual_value - target_value) / 0.15
                        )  # 范围0.05-0.2
                    elif param_name == "position_size":
                        normalized_distance = (
                            abs(actual_value - target_value) / 0.4
                        )  # 范围0.1-0.5
                    else:
                        normalized_distance = 0

                    total_distance += normalized_distance
                    param_count += 1

            # 适应度 = 1 - 平均归一化距离（越接近目标，适应度越高）
            if param_count > 0:
                avg_distance = total_distance / param_count
                fitness = max(0, 1 - avg_distance)
            else:
                fitness = 0

            # 添加一些随机噪声模拟真实环境
            noise = np.random.normal(0, 0.01)
            fitness = max(0, min(1, fitness + noise))

            return fitness

        return fitness_function

    def test_optimizer_initialization(self):
        """
        测试优化器初始化
        """
        self.assertIsNotNone(self.optimizer)
        self.assertEqual(self.optimizer.population_size, 20)
        self.assertEqual(self.optimizer.max_generations, 50)
        self.assertEqual(self.optimizer.mutation_rate, 0.1)
        self.assertEqual(self.optimizer.crossover_rate, 0.8)
        self.assertEqual(self.optimizer.elite_ratio, 0.1)

    def test_parameter_space_creation(self):
        """
        测试参数空间创建
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        self.assertIsNotNone(param_space)
        self.assertEqual(len(param_space.parameters), 4)

        # 测试参数范围
        self.assertIn("grid_num", param_space.parameters)
        self.assertIn("profit_ratio", param_space.parameters)
        self.assertIn("stop_loss", param_space.parameters)
        self.assertIn("position_size", param_space.parameters)

    def test_individual_creation(self):
        """
        测试个体创建
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        individual = Individual.create_random(param_space)

        self.assertIsNotNone(individual)
        self.assertIsNotNone(individual.parameters)
        self.assertEqual(len(individual.parameters), 4)

        # 验证参数在合理范围内
        self.assertGreaterEqual(individual.parameters["grid_num"], 5)
        self.assertLessEqual(individual.parameters["grid_num"], 20)
        self.assertGreaterEqual(individual.parameters["profit_ratio"], 0.01)
        self.assertLessEqual(individual.parameters["profit_ratio"], 0.05)

    def test_individual_fitness_evaluation(self):
        """
        测试个体适应度评估
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        individual = Individual.create_random(param_space)
        fitness = self.mock_fitness_function(individual.parameters)
        individual.fitness = fitness

        self.assertIsNotNone(individual.fitness)
        self.assertGreaterEqual(individual.fitness, 0)
        self.assertLessEqual(individual.fitness, 1)

    def test_population_initialization(self):
        """
        测试种群初始化
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        population = self.optimizer._initialize_population(param_space)

        self.assertEqual(len(population), self.optimizer.population_size)

        # 验证每个个体都有有效参数
        for individual in population:
            self.assertIsNotNone(individual.parameters)
            self.assertEqual(len(individual.parameters), 4)

    def test_fitness_evaluation(self):
        """
        测试适应度评估
        """

        async def run_test():
            param_space_config = self.test_parameter_spaces["grid_trading"]
            param_space = ParameterSpace(param_space_config)

            population = self.optimizer._initialize_population(param_space)

            # 模拟适应度评估
            await self.optimizer._evaluate_population(
                population, self.mock_fitness_function
            )

            # 验证所有个体都有适应度值
            for individual in population:
                self.assertIsNotNone(individual.fitness)
                self.assertGreaterEqual(individual.fitness, 0)
                self.assertLessEqual(individual.fitness, 1)

        asyncio.run(run_test())

    def test_selection_operator(self):
        """
        测试选择算子
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        population_obj = self.optimizer._initialize_population(param_space)
        
        # 从Population对象中获取individuals列表
        if hasattr(population_obj, 'individuals'):
            population = population_obj.individuals
        else:
            population = population_obj

        # 设置随机适应度值
        for individual in population:
            individual.fitness = np.random.random()

        selection_op = SelectionOperator("tournament", tournament_size=3)
        selected = selection_op.select(population, self.optimizer.population_size // 2)

        self.assertEqual(len(selected), self.optimizer.population_size // 2)

        # 验证选择的个体有适应度值
        for individual in selected:
            self.assertIsNotNone(individual.fitness)

    def test_crossover_operator(self):
        """
        测试交叉算子
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        parent1 = Individual.create_random(param_space)
        parent2 = Individual.create_random(param_space)

        crossover_op = CrossoverOperator("uniform")
        offspring1, offspring2 = crossover_op.crossover(parent1, parent2)

        self.assertIsNotNone(offspring1)
        self.assertIsNotNone(offspring2)
        self.assertEqual(len(offspring1.parameters), len(parent1.parameters))
        self.assertEqual(len(offspring2.parameters), len(parent2.parameters))

        # 验证后代参数在合理范围内
        for param_name, value in offspring1.parameters.items():
            param_config = param_space_config[param_name]
            self.assertGreaterEqual(value, param_config["min"])
            self.assertLessEqual(value, param_config["max"])

    def test_mutation_operator(self):
        """
        测试变异算子
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        individual = Individual.create_random(param_space)
        original_params = individual.parameters.copy()

        mutation_op = MutationOperator("gaussian", mutation_strength=0.1)
        mutated = mutation_op.mutate(individual, param_space)

        self.assertIsNotNone(mutated)
        self.assertEqual(len(mutated.parameters), len(original_params))

        # 验证变异后参数在合理范围内
        for param_name, value in mutated.parameters.items():
            param_config = param_space_config[param_name]
            self.assertGreaterEqual(value, param_config["min"])
            self.assertLessEqual(value, param_config["max"])

    def test_elite_preservation(self):
        """
        测试精英保留
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        population_obj = self.optimizer._initialize_population(param_space)
        
        # 从Population对象中获取individuals列表
        if hasattr(population_obj, 'individuals'):
            population = population_obj.individuals
        else:
            population = population_obj

        # 设置适应度值（递减）
        for i, individual in enumerate(population):
            individual.fitness = 1.0 - (i * 0.05)

        elite_count = int(self.optimizer.population_size * self.optimizer.elite_ratio)
        elites = self.optimizer._select_elites(population)

        self.assertEqual(len(elites), elite_count)

        # 验证精英是适应度最高的个体
        elite_fitness = [individual.fitness for individual in elites]
        self.assertEqual(elite_fitness, sorted(elite_fitness, reverse=True))

    def test_convergence_detection(self):
        """
        测试收敛检测
        """
        # 模拟收敛的适应度历史（变化范围小于convergence_threshold=0.001）
        converged_history = [0.5, 0.5001, 0.5002, 0.5003, 0.5004]
        self.assertTrue(self.optimizer._check_convergence(converged_history))

        # 模拟未收敛的适应度历史
        not_converged_history = [0.3, 0.4, 0.6, 0.5, 0.7]
        self.assertFalse(self.optimizer._check_convergence(not_converged_history))

    def test_stagnation_detection(self):
        """
        测试停滞检测
        """
        # 模拟停滞的适应度历史
        stagnant_history = [0.5] * 15  # 15代没有改进
        self.assertTrue(self.optimizer._check_stagnation(stagnant_history))

        # 模拟有改进的适应度历史
        improving_history = [0.1, 0.2, 0.3, 0.4, 0.5]
        self.assertFalse(self.optimizer._check_stagnation(improving_history))

    @patch(
        "optimizer.optimization.genetic_optimizer.GeneticOptimizer._save_optimization_result"
    )
    def test_optimization_task_execution(self, mock_save):
        """
        测试优化任务执行
        """
        mock_save.return_value = AsyncMock()

        async def run_test():
            # 创建ParameterSpace对象
            param_space_config = self.test_parameter_spaces["grid_trading"]
            param_space = ParameterSpace(param_space_config)
            
            task = OptimizationTask(
                task_id="test_optimization_001",
                strategy_id="grid_001",
                strategy_type="grid_trading",
                parameter_space=param_space,
                fitness_function=self.mock_fitness_function,
                target_metric="sharpe_ratio",
                optimization_goal="maximize",
            )

            result = await self.optimizer.optimize(task)

            # 验证优化结果
            self.assertIsInstance(result, OptimizationResult)
            self.assertEqual(result.task_id, "test_optimization_001")
            self.assertEqual(result.strategy_id, "grid_001")
            self.assertIsNotNone(result.best_parameters)
            self.assertIsNotNone(result.best_fitness)
            self.assertGreater(result.generations_completed, 0)

            # 验证最优参数在合理范围内
            param_space_config = self.test_parameter_spaces["grid_trading"]
            for param_name, value in result.best_parameters.items():
                if param_name in param_space_config:
                    param_config = param_space_config[param_name]
                    self.assertGreaterEqual(value, param_config["min"])
                    self.assertLessEqual(value, param_config["max"])

        asyncio.run(run_test())

    @patch(
        "optimizer.optimization.genetic_optimizer.GeneticOptimizer._save_optimization_result"
    )
    def test_multi_objective_optimization(self, mock_save):
        """
        测试多目标优化
        """
        mock_save.return_value = AsyncMock()

        def multi_objective_fitness(parameters):
            """
            多目标适应度函数：同时优化收益和风险
            """
            # 模拟收益指标（基于profit_ratio）
            profit_ratio = parameters.get("profit_ratio", 0.02)
            return_score = min(1.0, profit_ratio / 0.05)  # 归一化到0-1

            # 模拟风险指标（基于stop_loss）
            stop_loss = parameters.get("stop_loss", 0.1)
            risk_score = 1.0 - min(1.0, stop_loss / 0.2)  # 止损越小，风险控制越好

            # 综合评分（权重：收益70%，风险30%）
            combined_score = 0.7 * return_score + 0.3 * risk_score

            return combined_score

        async def run_test():
            # 创建ParameterSpace对象
            param_space_config = self.test_parameter_spaces["grid_trading"]
            param_space = ParameterSpace(param_space_config)
            
            task = OptimizationTask(
                task_id="multi_obj_test_001",
                strategy_id="grid_002",
                strategy_type="grid_trading",
                parameter_space=param_space,
                fitness_function=multi_objective_fitness,
                target_metric="combined_score",
                optimization_goal="maximize",
            )

            result = await self.optimizer.optimize(task)

            # 验证多目标优化结果
            self.assertIsInstance(result, OptimizationResult)
            self.assertIsNotNone(result.best_parameters)
            self.assertGreater(result.best_fitness, 0)

        asyncio.run(run_test())

    def test_parameter_constraints(self):
        """
        测试参数约束
        """
        # 测试均线策略的约束：快线周期必须小于慢线周期
        param_space_config = self.test_parameter_spaces["ma_crossover"]
        param_space = ParameterSpace(param_space_config)

        # 添加约束检查
        def constraint_check(parameters):
            fast_period = parameters.get("fast_period", 5)
            slow_period = parameters.get("slow_period", 20)
            return fast_period < slow_period

        # 生成多个个体并检查约束
        valid_individuals = 0
        total_attempts = 100

        for _ in range(total_attempts):
            individual = Individual.create_random(param_space)
            if constraint_check(individual.parameters):
                valid_individuals += 1

        # 验证大部分个体满足约束（由于随机生成，不是100%）
        constraint_satisfaction_rate = valid_individuals / total_attempts
        self.assertGreater(constraint_satisfaction_rate, 0.5)  # 至少50%满足约束

    @patch(
        "optimizer.optimization.genetic_optimizer.GeneticOptimizer._save_optimization_result"
    )
    def test_optimization_timeout(self, mock_save):
        """
        测试优化超时处理
        """
        mock_save.return_value = AsyncMock()

        # 临时修改超时时间为很短的时间
        original_timeout = self.optimizer.optimization_timeout
        self.optimizer.optimization_timeout = 0.01  # 10毫秒

        async def run_test():
            # 创建ParameterSpace对象
            param_space_config = self.test_parameter_spaces["grid_trading"]
            param_space = ParameterSpace(param_space_config)
            
            task = OptimizationTask(
                task_id="timeout_test_001",
                strategy_id="grid_003",
                strategy_type="grid_trading",
                parameter_space=param_space,
                fitness_function=self.mock_fitness_function,
                target_metric="sharpe_ratio",
                optimization_goal="maximize",
            )

            result = await self.optimizer.optimize(task)

            # 验证超时后仍有结果（部分优化）
            self.assertIsInstance(result, OptimizationResult)
            self.assertIsNotNone(result.best_parameters)
            self.assertTrue(result.timeout_occurred)

        try:
            asyncio.run(run_test())
        finally:
            # 恢复原始超时时间
            self.optimizer.optimization_timeout = original_timeout

    def test_optimization_statistics(self):
        """
        测试优化统计信息
        """

        async def run_test():
            # 获取初始统计信息
            initial_stats = await self.optimizer.get_optimization_statistics()

            self.assertIn("total_optimizations", initial_stats)
            self.assertIn("successful_optimizations", initial_stats)
            self.assertIn("average_generations", initial_stats)
            self.assertIn("average_fitness_improvement", initial_stats)

            # 验证统计信息格式
            self.assertIsInstance(initial_stats["total_optimizations"], int)
            self.assertIsInstance(initial_stats["successful_optimizations"], int)

        asyncio.run(run_test())

    def test_parameter_sensitivity_analysis(self):
        """
        测试参数敏感性分析
        """
        # 测试不同参数值对适应度的影响
        base_params = {
            "grid_num": 10,
            "profit_ratio": 0.02,
            "stop_loss": 0.1,
            "position_size": 0.3,
        }

        base_fitness = self.mock_fitness_function(base_params)

        # 测试grid_num的敏感性
        grid_sensitivities = []
        for grid_num in range(5, 21, 2):
            test_params = base_params.copy()
            test_params["grid_num"] = grid_num
            fitness = self.mock_fitness_function(test_params)
            sensitivity = abs(fitness - base_fitness)
            grid_sensitivities.append(sensitivity)

        # 验证敏感性分析结果
        self.assertEqual(len(grid_sensitivities), 8)
        self.assertTrue(all(s >= 0 for s in grid_sensitivities))

    def test_diversity_maintenance(self):
        """
        测试种群多样性维护
        """
        param_space_config = self.test_parameter_spaces["grid_trading"]
        param_space = ParameterSpace(param_space_config)

        population = self.optimizer._initialize_population(param_space)

        # 计算种群多样性
        diversity = self.optimizer._calculate_population_diversity(population)

        self.assertIsInstance(diversity, float)
        self.assertGreaterEqual(diversity, 0)
        self.assertLessEqual(diversity, 1)

        # 验证初始种群有一定多样性
        self.assertGreater(diversity, 0.1)  # 至少10%的多样性

    def test_adaptive_parameters(self):
        """
        测试自适应参数调整
        """
        # 测试变异率自适应调整
        initial_mutation_rate = self.optimizer.mutation_rate

        # 模拟停滞情况
        stagnant_history = [0.5] * 10
        self.optimizer._adapt_parameters(10, stagnant_history)

        # 验证变异率增加
        self.assertGreaterEqual(self.optimizer.mutation_rate, initial_mutation_rate)

        # 模拟改进情况
        improving_history = [0.1, 0.2, 0.3, 0.4, 0.5]
        self.optimizer._adapt_parameters(5, improving_history)

        # 验证变异率可能降低
        self.assertLessEqual(self.optimizer.mutation_rate, initial_mutation_rate * 1.5)

    def test_memory_efficiency(self):
        """
        测试内存使用效率
        """
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 运行多次优化
        async def run_test():
            for i in range(5):
                # 创建ParameterSpace对象
                param_space_config = self.test_parameter_spaces["grid_trading"]
                param_space = ParameterSpace(param_space_config)
                
                task = OptimizationTask(
                    task_id=f"memory_test_{i:03d}",
                    strategy_id=f"grid_{i:03d}",
                    strategy_type="grid_trading",
                    parameter_space=param_space,
                    fitness_function=self.mock_fitness_function,
                    target_metric="sharpe_ratio",
                    optimization_goal="maximize",
                )

                # 使用较小的种群和代数以节省时间
                original_pop_size = self.optimizer.population_size
                original_max_gen = self.optimizer.max_generations

                self.optimizer.population_size = 10
                self.optimizer.max_generations = 10

                try:
                    await self.optimizer.optimize(task)
                finally:
                    self.optimizer.population_size = original_pop_size
                    self.optimizer.max_generations = original_max_gen

        with patch(
            "optimizer.optimization.genetic_optimizer.GeneticOptimizer._save_optimization_result"
        ):
            asyncio.run(run_test())

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 验证内存增长在合理范围内（小于100MB）
        self.assertLess(memory_increase, 100)

    def test_cleanup(self):
        """
        测试资源清理
        """

        async def run_test():
            # 确保优化器正常运行
            self.assertIsNotNone(self.optimizer)

            # 执行清理
            await self.optimizer.cleanup()

            # 验证清理后状态
            # 注意：具体的清理验证取决于实现细节

        asyncio.run(run_test())


class TestGeneticOperators(unittest.TestCase):
    """
    遗传算子测试类
    """

    def setUp(self):
        """
        测试初始化
        """
        np.random.seed(42)

        self.param_space_config = {
            "param1": {"type": "int", "min": 1, "max": 10, "step": 1},
            "param2": {"type": "float", "min": 0.1, "max": 1.0, "step": 0.1},
            "param3": {"type": "float", "min": 0.01, "max": 0.1, "step": 0.01},
        }

        self.param_space = ParameterSpace(self.param_space_config)

    def test_tournament_selection(self):
        """
        测试锦标赛选择
        """
        # 创建测试种群
        population = []
        for i in range(10):
            individual = Individual.create_random(self.param_space)
            individual.fitness = i * 0.1  # 递增的适应度
            population.append(individual)

        selection_op = SelectionOperator("tournament", tournament_size=3)
        selected = selection_op.select(population, 5)

        self.assertEqual(len(selected), 5)

        # 验证选择倾向于高适应度个体
        selected_fitness = [ind.fitness for ind in selected]
        avg_selected_fitness = sum(selected_fitness) / len(selected_fitness)
        avg_population_fitness = sum(ind.fitness for ind in population) / len(
            population
        )

        self.assertGreaterEqual(avg_selected_fitness, avg_population_fitness)

    def test_roulette_wheel_selection(self):
        """
        测试轮盘赌选择
        """
        # 创建测试种群
        population = []
        for i in range(10):
            individual = Individual.create_random(self.param_space)
            individual.fitness = (i + 1) * 0.1  # 递增的适应度（避免0）
            population.append(individual)

        selection_op = SelectionOperator("roulette_wheel")
        selected = selection_op.select(population, 5)

        self.assertEqual(len(selected), 5)

        # 验证所有选择的个体都有有效适应度
        for individual in selected:
            self.assertIsNotNone(individual.fitness)
            self.assertGreater(individual.fitness, 0)

    def test_uniform_crossover(self):
        """
        测试均匀交叉
        """
        parent1 = Individual.create_random(self.param_space)
        parent2 = Individual.create_random(self.param_space)

        crossover_op = CrossoverOperator("uniform")
        offspring1, offspring2 = crossover_op.crossover(parent1, parent2)

        # 验证后代结构
        self.assertEqual(len(offspring1.parameters), len(parent1.parameters))
        self.assertEqual(len(offspring2.parameters), len(parent2.parameters))

        # 验证参数来源于父代
        for param_name in offspring1.parameters:
            self.assertIn(
                offspring1.parameters[param_name],
                [parent1.parameters[param_name], parent2.parameters[param_name]],
            )

    def test_single_point_crossover(self):
        """
        测试单点交叉
        """
        parent1 = Individual.create_random(self.param_space)
        parent2 = Individual.create_random(self.param_space)

        crossover_op = CrossoverOperator("single_point")
        offspring1, offspring2 = crossover_op.crossover(parent1, parent2)

        # 验证后代结构
        self.assertEqual(len(offspring1.parameters), len(parent1.parameters))
        self.assertEqual(len(offspring2.parameters), len(parent2.parameters))

    def test_gaussian_mutation(self):
        """
        测试高斯变异
        """
        individual = Individual.create_random(self.param_space)

        mutation_op = MutationOperator("gaussian", mutation_strength=0.1)
        mutated = mutation_op.mutate(individual, self.param_space)

        # 验证变异后参数在合理范围内
        for param_name, value in mutated.parameters.items():
            param_config = self.param_space_config[param_name]
            self.assertGreaterEqual(value, param_config["min"])
            self.assertLessEqual(value, param_config["max"])

    def test_random_mutation(self):
        """
        测试随机变异
        """
        individual = Individual.create_random(self.param_space)

        mutation_op = MutationOperator("random")
        mutated = mutation_op.mutate(individual, self.param_space)

        # 验证变异后参数在合理范围内
        for param_name, value in mutated.parameters.items():
            param_config = self.param_space_config[param_name]
            self.assertGreaterEqual(value, param_config["min"])
            self.assertLessEqual(value, param_config["max"])


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
