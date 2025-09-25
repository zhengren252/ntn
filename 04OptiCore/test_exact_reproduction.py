#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确复现原始测试的问题
"""

import asyncio
import tempfile
import os
import shutil
import unittest
from optimizer.main import StrategyOptimizationModule

class TestExactReproduction(unittest.TestCase):
    """精确复现原始测试"""
    
    @classmethod
    def setUpClass(cls):
        """类级别的初始化"""
        cls.test_config = {
            "environment": "test",
            "database": {
                "sqlite_path": "",  # 将在setUp中设置
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
    
    def setUp(self):
        """每个测试用例的初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_optimizer.db")
        
        # 更新测试配置
        self.__class__.test_config["database"]["sqlite_path"] = self.test_db_path
    
    def tearDown(self):
        """每个测试用例的清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_error_handling_exact_reproduction(self):
        """精确复现原始测试的错误处理"""
        print("=== 开始精确复现原始测试 ===")
        
        async def run_test():
            print("DEBUG: 开始测试错误处理和恢复")
            print(f"DEBUG: test_config = {self.test_config}")
            
            optimizer_module = StrategyOptimizationModule(self.test_config)
            print(f"DEBUG: optimizer_module创建成功: {optimizer_module}")
            
            await optimizer_module.initialize()
            print(f"DEBUG: optimizer_module初始化完成")
            print(f"DEBUG: optimizer_module.strategy_manager = {optimizer_module.strategy_manager}")
            print(f"DEBUG: type(optimizer_module.strategy_manager) = {type(optimizer_module.strategy_manager)}")

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

                print(f"DEBUG: 测试开始，invalid_strategy_config = {invalid_strategy_config}")
                print(f"DEBUG: optimizer_module.strategy_manager = {optimizer_module.strategy_manager}")
                
                # 这里是关键：我们直接调用register_strategy，看看是否抛出异常
                print("DEBUG: 即将调用register_strategy...")
                try:
                    result = await optimizer_module.strategy_manager.register_strategy(
                        invalid_strategy_config
                    )
                    print(f"❌ ERROR: register_strategy没有抛出异常，返回结果: {result}")
                    print(f"❌ 这就是测试失败的原因！")
                    return False
                except Exception as e:
                    print(f"✅ SUCCESS: register_strategy正确抛出异常: {type(e).__name__}: {e}")
                    return True

            finally:
                await optimizer_module.cleanup()
        
        # 运行异步测试
        result = asyncio.run(run_test())
        
        if not result:
            print("\n=== 测试结论 ===")
            print("原始测试失败的原因：register_strategy方法没有抛出预期的异常")
            print("这意味着验证逻辑可能存在问题，或者异常被内部捕获了")
        else:
            print("\n=== 测试结论 ===")
            print("register_strategy方法正确抛出了异常，原始测试应该通过")

if __name__ == "__main__":
    unittest.main(verbosity=2)