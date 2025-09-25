#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试特定的验证逻辑
"""

import asyncio
import tempfile
import os
import shutil
from optimizer.main import StrategyOptimizationModule

async def test_specific_validation():
    """测试特定的验证逻辑"""
    print("=== 开始测试特定验证逻辑 ===")
    
    # 创建临时目录和数据库
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_optimizer.db")
    
    # 创建与测试相同的配置
    test_config = {
        "environment": "test",
        "database": {
            "sqlite_path": test_db_path,
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
    await optimizer_module.initialize()
    
    try:
        # 测试1: 只有负数参数
        print("\n=== 测试1: 只有负数参数 ===")
        config1 = {
            "name": "test_negative",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 负数
                "slow_period": 20,  # 正常值
            },
            "description": "测试负数参数",
        }
        
        try:
            result1 = await optimizer_module.strategy_manager.register_strategy(config1)
            print(f"❌ 测试1失败：没有抛出异常，返回结果: {result1}")
        except Exception as e:
            print(f"✅ 测试1通过：抛出异常: {type(e).__name__}: {e}")
        
        # 测试2: 只有无效字符串参数
        print("\n=== 测试2: 只有无效字符串参数 ===")
        config2 = {
            "name": "test_invalid_string",
            "type": "ma_cross",
            "parameters": {
                "fast_period": 10,  # 正常值
                "slow_period": "invalid",  # 无效字符串
            },
            "description": "测试无效字符串参数",
        }
        
        try:
            result2 = await optimizer_module.strategy_manager.register_strategy(config2)
            print(f"❌ 测试2失败：没有抛出异常，返回结果: {result2}")
        except Exception as e:
            print(f"✅ 测试2通过：抛出异常: {type(e).__name__}: {e}")
        
        # 测试3: 同时有负数和无效字符串（原始测试的情况）
        print("\n=== 测试3: 同时有负数和无效字符串 ===")
        config3 = {
            "name": "test_both_invalid",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 负数
                "slow_period": "invalid",  # 无效字符串
            },
            "description": "测试同时有负数和无效字符串",
        }
        
        try:
            result3 = await optimizer_module.strategy_manager.register_strategy(config3)
            print(f"❌ 测试3失败：没有抛出异常，返回结果: {result3}")
        except Exception as e:
            print(f"✅ 测试3通过：抛出异常: {type(e).__name__}: {e}")
        
        # 测试4: 有效的数字字符串
        print("\n=== 测试4: 有效的数字字符串 ===")
        config4 = {
            "name": "test_valid_string",
            "type": "ma_cross",
            "parameters": {
                "fast_period": 10,
                "slow_period": "20",  # 有效的数字字符串
            },
            "description": "测试有效的数字字符串",
        }
        
        try:
            result4 = await optimizer_module.strategy_manager.register_strategy(config4)
            print(f"✅ 测试4通过：成功注册策略: {result4}")
        except Exception as e:
            print(f"❌ 测试4失败：抛出异常: {type(e).__name__}: {e}")
            
    finally:
        await optimizer_module.cleanup()
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print("\n=== 清理完成 ===")

if __name__ == "__main__":
    asyncio.run(test_specific_validation())