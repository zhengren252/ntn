#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试测试环境脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.main import StrategyOptimizationModule
from config.config import Config

async def debug_test_environment():
    """调试测试环境"""
    
    print("=== 调试测试环境 ===")
    
    # 1. 创建测试配置（模拟测试环境）
    config = Config()
    test_config = {
        "environment": "test",
        "database": {
            "url": "sqlite:///test_optimizer.db",
            "echo": False,
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "strategies": {
            "default_strategies": True,
            "custom_strategies_path": "strategies/custom",
        },
        "backtest": {
            "default_capital": 10000.0,
            "commission_rate": 0.001,
            "slippage_rate": 0.0005,
        },
        "optimization": {
            "population_size": 50,
            "generations": 20,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
        },
        "risk": {
            "max_drawdown": 0.2,
            "max_position_size": 0.5,
            "daily_loss_limit": 0.05,
        },
        "zmq": {
            "subscriber_port": 5555,
            "publisher_port": 5556,
            "timeout": 5000,
        },
    }
    
    print(f"测试配置: {test_config}")
    
    # 2. 创建优化模块
    optimizer_module = StrategyOptimizationModule(test_config)
    print(f"优化模块创建成功: {optimizer_module}")
    
    await optimizer_module.initialize()
    print(f"优化模块初始化完成")
    
    try:
        # 3. 测试无效策略参数处理
        print("\n=== 测试无效策略参数处理 ===")
        
        invalid_strategy_config = {
            "name": "invalid_strategy",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 无效参数
                "slow_period": "invalid",  # 无效类型
            },
            "description": "无效策略测试",
        }
        
        print(f"无效策略配置: {invalid_strategy_config}")
        print(f"策略管理器: {optimizer_module.strategy_manager}")
        print(f"策略管理器类型: {type(optimizer_module.strategy_manager)}")
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(
                invalid_strategy_config
            )
            print(f"❌ 问题：没有抛出异常，返回结果: {result}")
            print(f"结果类型: {type(result)}")
        except Exception as e:
            print(f"✅ 正确：抛出异常: {type(e).__name__}: {e}")
        
        # 4. 测试另一种无效配置
        print("\n=== 测试另一种无效配置 ===")
        
        invalid_strategy_config_2 = {
            "name": "invalid_strategy_2",
            "type": "ma_cross",
            "parameters": {
                "fast_period": "not_a_number",  # 无效类型
                "slow_period": 20,
            },
            "description": "无效策略测试2",
        }
        
        print(f"无效策略配置2: {invalid_strategy_config_2}")
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(
                invalid_strategy_config_2
            )
            print(f"❌ 问题：没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"✅ 正确：抛出异常: {type(e).__name__}: {e}")
        
        # 5. 测试缺少必需字段的配置
        print("\n=== 测试缺少必需字段的配置 ===")
        
        invalid_strategy_config_3 = {
            "name": "invalid_strategy_3",
            # 缺少 "type" 字段
            "parameters": {
                "fast_period": 10,
                "slow_period": 20,
            },
            "description": "缺少类型字段的策略",
        }
        
        print(f"无效策略配置3: {invalid_strategy_config_3}")
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(
                invalid_strategy_config_3
            )
            print(f"❌ 问题：没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"✅ 正确：抛出异常: {type(e).__name__}: {e}")
        
    finally:
        await optimizer_module.cleanup()
        print("\n=== 清理完成 ===")

async def debug_test_environment_with_config():
    """使用与测试相同的配置进行调试"""
    print("=== 测试策略验证逻辑（使用测试配置）===")
    
    # 创建与测试相同的配置
    test_config = {
        "environment": "test",
        "database": {
            "sqlite_path": ":memory:",
            "redis_host": "localhost",
            "redis_port": 6379,
            "redis_db": 15,
        },
        "zmq": {
            "subscriber_address": "tcp://localhost:5555",
            "publisher_address": "tcp://localhost:5556",
            "subscribe_topics": ["scanner.pool.preliminary"],
            "publish_topic": "optimizer.pool.trading",
        },
        "backtest": {
            "initial_capital": 10000.0,
            "commission_rate": 0.001,
            "max_concurrent_backtests": 2,
        },
        "optimization": {
            "population_size": 10,
            "max_generations": 5,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
        },
        "risk": {
            "max_position_size": 0.3,
            "max_drawdown_threshold": 0.2,
            "min_sharpe_ratio": 0.5,
        },
    }
    
    # 创建策略优化模组
    optimizer_module = StrategyOptimizationModule(test_config)
    
    # 初始化模组
    await optimizer_module.initialize()
    
    try:
        # 测试与原始测试相同的无效策略配置
        invalid_strategy_config = {
            "name": "invalid_strategy",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 无效参数
                "slow_period": "invalid",  # 无效类型
            },
            "description": "无效策略测试",
        }
        
        print(f"\n=== 测试与原始测试相同的配置 ===")
        print(f"无效策略配置: {invalid_strategy_config}")
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(
                invalid_strategy_config
            )
            print(f"❌ 错误：没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"✅ 正确：抛出异常: {type(e).__name__}: {e}")
            
    finally:
        await optimizer_module.cleanup()
        print("\n=== 清理完成 ===")

if __name__ == "__main__":
    asyncio.run(debug_test_environment_with_config())