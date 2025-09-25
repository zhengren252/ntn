#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试register_strategy方法
"""

import asyncio
import sys
import os
import tempfile

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.main import StrategyOptimizationModule

async def test_register_strategy():
    """
    直接测试register_strategy方法
    """
    # 创建临时数据库文件
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_direct.db")
    
    test_config = {
        'environment': 'test',
        'database': {
            'sqlite_path': db_path,
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 15
        },
        'zmq': {
            'subscriber_address': 'tcp://localhost:5555',
            'publisher_address': 'tcp://localhost:5556',
            'subscribe_topics': ['scanner.pool.preliminary'],
            'publish_topic': 'optimizer.pool.trading'
        },
        'backtest': {
            'initial_capital': 10000.0,
            'commission_rate': 0.001,
            'max_concurrent_backtests': 2
        },
        'optimization': {
            'population_size': 10,
            'max_generations': 5,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8
        }
    }
    
    print("创建StrategyOptimizationModule...")
    optimizer_module = StrategyOptimizationModule(test_config)
    
    print("初始化模块...")
    await optimizer_module.initialize()
    
    try:
        # 测试无效策略参数处理
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
        print(f"strategy_manager类型: {type(optimizer_module.strategy_manager)}")
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(
                invalid_strategy_config
            )
            print(f"ERROR: 没有抛出异常！返回结果: {result}")
            return False
        except Exception as e:
            print(f"SUCCESS: 正确抛出异常: {e}")
            return True
            
    finally:
        await optimizer_module.cleanup()
        # 清理临时文件
        try:
            os.remove(db_path)
            os.rmdir(temp_dir)
        except:
            pass

if __name__ == "__main__":
    result = asyncio.run(test_register_strategy())
    if result:
        print("测试通过：register_strategy正确抛出异常")
    else:
        print("测试失败：register_strategy没有抛出异常")
        sys.exit(1)