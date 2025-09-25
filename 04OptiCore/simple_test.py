#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.strategies.manager import StrategyManager

async def simple_test():
    """
    简单测试
    """
    print("开始简单测试...")
    
    # 创建配置
    config = {
        'environment': 'test',
        'database': {
            'sqlite_path': ':memory:',
            'redis_host': 'localhost',
            'redis_port': 6379,
            'redis_db': 15
        }
    }
    
    # 创建策略管理器
    strategy_manager = StrategyManager(config)
    await strategy_manager.initialize()
    
    # 测试无效策略配置
    invalid_strategy_config = {
        "name": "invalid_strategy",
        "type": "ma_cross",
        "parameters": {
            "fast_period": -1,  # 无效参数
        },
        "description": "无效策略测试",
    }
    
    print(f"测试无效策略配置: {invalid_strategy_config}")
    
    # 使用assertRaises的逻辑
    exception_raised = False
    try:
        result = await strategy_manager.register_strategy(invalid_strategy_config)
        print(f"ERROR: 没有抛出异常！返回结果: {result}")
    except Exception as e:
        print(f"SUCCESS: 正确抛出异常: {e}")
        exception_raised = True
    
    if not exception_raised:
        print("FAIL: 测试失败 - 没有抛出异常")
        return False
    else:
        print("PASS: 测试通过 - 正确抛出异常")
        return True

if __name__ == "__main__":
    result = asyncio.run(simple_test())
    if not result:
        sys.exit(1)