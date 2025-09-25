#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试策略验证脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.strategies.manager import StrategyManager

async def test_strategy_validation():
    """
    测试策略验证功能
    """
    print("开始测试策略验证...")
    
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
            "slow_period": "invalid",  # 无效类型
        },
        "description": "无效策略测试",
    }
    
    print(f"测试无效策略配置: {invalid_strategy_config}")
    
    try:
        result = await strategy_manager.register_strategy(invalid_strategy_config)
        print(f"ERROR: 没有抛出异常！返回结果: {result}")
        return False
    except Exception as e:
        print(f"SUCCESS: 正确抛出异常: {e}")
        return True
    finally:
        # 清理资源（如果有cleanup方法的话）
        if hasattr(strategy_manager, 'cleanup'):
            await strategy_manager.cleanup()

if __name__ == "__main__":
    result = asyncio.run(test_strategy_validation())
    if result:
        print("\n测试通过：策略验证正常工作")
    else:
        print("\n测试失败：策略验证没有正常工作")
        sys.exit(1)