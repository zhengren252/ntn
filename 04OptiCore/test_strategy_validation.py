#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略验证测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.strategies.manager import StrategyManager
from config.config import Config

async def test_strategy_validation():
    """测试策略验证逻辑"""
    
    # 创建配置
    config = Config()
    
    # 创建策略管理器
    strategy_manager = StrategyManager(config)
    await strategy_manager.initialize()
    
    print("=== 测试策略验证逻辑 ===")
    
    # 测试1: 无效的负数参数
    print("\n测试1: 负数参数")
    invalid_strategy_1 = {
        "name": "invalid_strategy_1",
        "type": "ma_cross",
        "parameters": {
            "fast_period": -1,  # 负数，应该抛出异常
            "slow_period": 20,
        },
        "description": "测试负数参数",
    }
    
    try:
        result = await strategy_manager.register_strategy(invalid_strategy_1)
        print(f"❌ 测试失败：没有抛出异常，返回结果: {result}")
    except Exception as e:
        print(f"✅ 测试通过：正确抛出异常: {type(e).__name__}: {e}")
    
    # 测试2: 无效的字符串类型参数
    print("\n测试2: 无效字符串类型参数")
    invalid_strategy_2 = {
        "name": "invalid_strategy_2",
        "type": "ma_cross",
        "parameters": {
            "fast_period": 10,
            "slow_period": "invalid",  # 无效字符串，应该抛出异常
        },
        "description": "测试无效字符串参数",
    }
    
    try:
        result = await strategy_manager.register_strategy(invalid_strategy_2)
        print(f"❌ 测试失败：没有抛出异常，返回结果: {result}")
    except Exception as e:
        print(f"✅ 测试通过：正确抛出异常: {type(e).__name__}: {e}")
    
    # 测试3: 有效参数（对照组）
    print("\n测试3: 有效参数")
    valid_strategy = {
        "name": "valid_strategy",
        "type": "ma_cross",
        "parameters": {
            "fast_period": 10,
            "slow_period": 20,
        },
        "description": "测试有效参数",
    }
    
    try:
        result = await strategy_manager.register_strategy(valid_strategy)
        print(f"✅ 测试通过：成功注册策略: {result}")
    except Exception as e:
        print(f"❌ 测试失败：不应该抛出异常: {type(e).__name__}: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_strategy_validation())