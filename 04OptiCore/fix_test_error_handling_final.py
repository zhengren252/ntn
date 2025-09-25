#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复test_error_handling_and_recovery测试
"""

import asyncio
import sys
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.main import StrategyOptimizationModule
from optimizer.strategies.manager import StrategyManager
from config.config import Config

async def test_strategy_manager_directly():
    """直接测试StrategyManager的异常处理"""
    
    # 创建临时数据库
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_fix.db")
    
    test_config = {
        'environment': 'test',
        'database': {
            'sqlite_path': db_path,
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1
        },
        'optimization': {
            'max_concurrent_tasks': 2,
            'timeout': 300,
            'result_cache_size': 100
        },
        'genetic_algorithm': {
            'population_size': 20,
            'max_generations': 50,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'elite_ratio': 0.1
        }
    }
    
    # 创建StrategyManager实例
    strategy_manager = StrategyManager(test_config)
    await strategy_manager.initialize()
    
    try:
        # 测试无效策略参数
        invalid_strategy_config = {
            "name": "invalid_strategy",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 无效参数
                "slow_period": "invalid",  # 无效类型
            },
            "description": "无效策略测试",
        }
        
        print(f"测试无效策略配置: {invalid_strategy_config}")
        
        try:
            result = await strategy_manager.register_strategy(invalid_strategy_config)
            print(f"ERROR: 没有抛出异常，返回结果: {result}")
            return False
        except Exception as e:
            print(f"SUCCESS: 正确抛出异常: {type(e).__name__}: {e}")
            return True
            
    finally:
        # 清理临时文件
        try:
            os.remove(db_path)
            os.rmdir(temp_dir)
        except:
            pass

async def test_optimization_module():
    """测试StrategyOptimizationModule的异常处理"""
    
    # 创建临时数据库
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_module.db")
    
    test_config = {
        'environment': 'test',
        'database': {
            'sqlite_path': db_path,
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 1
        },
        'optimization': {
            'max_concurrent_tasks': 2,
            'timeout': 300,
            'result_cache_size': 100
        },
        'genetic_algorithm': {
            'population_size': 20,
            'max_generations': 50,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'elite_ratio': 0.1
        }
    }
    
    # 创建StrategyOptimizationModule实例
    optimizer_module = StrategyOptimizationModule(test_config)
    await optimizer_module.initialize()
    
    try:
        # 测试无效策略参数
        invalid_strategy_config = {
            "name": "invalid_strategy",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 无效参数
                "slow_period": "invalid",  # 无效类型
            },
            "description": "无效策略测试",
        }
        
        print(f"测试StrategyOptimizationModule无效策略配置: {invalid_strategy_config}")
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(invalid_strategy_config)
            print(f"ERROR: StrategyOptimizationModule没有抛出异常，返回结果: {result}")
            return False
        except Exception as e:
            print(f"SUCCESS: StrategyOptimizationModule正确抛出异常: {type(e).__name__}: {e}")
            return True
            
    finally:
        # 清理临时文件
        try:
            os.remove(db_path)
            os.rmdir(temp_dir)
        except:
            pass

async def main():
    """主函数"""
    print("=== 测试StrategyManager异常处理 ===")
    result1 = await test_strategy_manager_directly()
    
    print("\n=== 测试StrategyOptimizationModule异常处理 ===")
    result2 = await test_optimization_module()
    
    if result1 and result2:
        print("\n✅ 所有测试通过！异常处理工作正常。")
    else:
        print("\n❌ 测试失败！需要修复异常处理。")
        
    return result1 and result2

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)