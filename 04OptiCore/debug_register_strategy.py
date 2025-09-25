#!/usr/bin/env python3
"""
调试register_strategy方法的异常处理
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.main import StrategyOptimizationModule

async def test_register_strategy_exceptions():
    """测试register_strategy方法的异常处理"""
    print("=== 开始调试register_strategy异常处理 ===")
    
    # 获取测试配置
    test_config = {
        "environment": "test",
        "debug": True,
        "testing": True,
        "database": {"path": ":memory:", "echo": False},
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 15,
            "decode_responses": True,
        },
        "zmq": {
            "frontend_port": 5555,
            "backend_port": 5556,
            "bind_address": "127.0.0.1",
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "backtest": {
            "default_initial_capital": 10000.0,
            "default_commission": 0.001,
            "default_slippage": 0.0001,
        },
        "optimization": {
            "max_workers": 2,
            "timeout": 300,
            "memory_limit": "1GB",
        },
    }
    print(f"测试配置: {test_config}")
    
    # 创建优化模块
    optimizer_module = StrategyOptimizationModule(test_config)
    await optimizer_module.initialize()
    
    try:
        # 测试1: 负数参数
        print("\n--- 测试1: 负数参数 ---")
        invalid_config_1 = {
            "name": "test_negative",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 负数
                "slow_period": 20,
            },
            "description": "负数参数测试",
        }
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(invalid_config_1)
            print(f"❌ 没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"✅ 抛出异常: {type(e).__name__}: {e}")
        
        # 测试2: 无效字符串参数
        print("\n--- 测试2: 无效字符串参数 ---")
        invalid_config_2 = {
            "name": "test_invalid_string",
            "type": "ma_cross",
            "parameters": {
                "fast_period": 10,
                "slow_period": "invalid",  # 无效字符串
            },
            "description": "无效字符串参数测试",
        }
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(invalid_config_2)
            print(f"❌ 没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"✅ 抛出异常: {type(e).__name__}: {e}")
        
        # 测试3: 同时包含负数和无效字符串
        print("\n--- 测试3: 同时包含负数和无效字符串 ---")
        invalid_config_3 = {
            "name": "test_both_invalid",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 负数
                "slow_period": "invalid",  # 无效字符串
            },
            "description": "同时包含负数和无效字符串测试",
        }
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(invalid_config_3)
            print(f"❌ 没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"✅ 抛出异常: {type(e).__name__}: {e}")
        
        # 测试4: 有效配置
        print("\n--- 测试4: 有效配置 ---")
        valid_config = {
            "name": "test_valid",
            "type": "ma_cross",
            "parameters": {
                "fast_period": 10,
                "slow_period": 20,
            },
            "description": "有效配置测试",
        }
        
        try:
            result = await optimizer_module.strategy_manager.register_strategy(valid_config)
            print(f"✅ 成功注册策略: {result}")
        except Exception as e:
            print(f"❌ 意外异常: {type(e).__name__}: {e}")
        
    finally:
        try:
            await optimizer_module.cleanup()
        except Exception as e:
            print(f"清理时出错: {e}")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_register_strategy_exceptions())