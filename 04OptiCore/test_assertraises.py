#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试assertRaises行为
"""

import asyncio
import sys
import os
import unittest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.main import StrategyOptimizationModule

class TestAssertRaises(unittest.TestCase):
    def setUp(self):
        self.test_config = {
            'environment': 'test',
            'database': {
                'sqlite_path': ':memory:',
                'redis_host': 'localhost',
                'redis_port': 6379,
                'redis_db': 15
            },
            'zmq': {
                'subscriber_port': 5555,
                'publisher_port': 5556,
                'timeout': 5000
            },
            'backtest': {
                'initial_capital': 10000.0,
                'commission': 0.001,
                'slippage': 0.0001
            },
            'optimization': {
                'population_size': 20,
                'generations': 10,
                'mutation_rate': 0.1,
                'crossover_rate': 0.8
            }
        }
    
    async def async_test_method(self):
        """
        异步测试方法
        """
        print("开始异步测试...")
        
        optimizer_module = StrategyOptimizationModule(self.test_config)
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
            
            # 使用assertRaises
            with self.assertRaises(Exception):
                result = await optimizer_module.strategy_manager.register_strategy(
                    invalid_strategy_config
                )
                print(f"ERROR: 没有抛出异常！返回结果: {result}")
                
            print("SUCCESS: assertRaises正确捕获了异常")
            
        finally:
            await optimizer_module.cleanup()
    
    def test_async_assertraises(self):
        """
        测试异步assertRaises
        """
        asyncio.run(self.async_test_method())

if __name__ == "__main__":
    unittest.main(verbosity=2)