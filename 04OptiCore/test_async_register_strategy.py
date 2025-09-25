#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试异步register_strategy方法
"""

import asyncio
import sys
import os
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.strategies.manager import StrategyManager

async def test_async_register_strategy():
    """
    测试异步register_strategy方法的异常处理
    """
    print("=== 测试异步register_strategy方法 ===")
    
    # 创建临时数据库
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    
    try:
        # 创建StrategyManager
        config = {
            "database": {
                "url": f"sqlite:///{temp_db.name}"
            }
        }
        
        strategy_manager = StrategyManager(config)
        await strategy_manager.initialize()
        
        # 测试1: 负数参数
        print("\n测试1: 负数参数")
        invalid_config_1 = {
            "name": "test_strategy_1",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 负数
                "slow_period": 20
            },
            "description": "测试负数参数"
        }
        
        try:
            result = await strategy_manager.register_strategy(invalid_config_1)
            print(f"   ERROR: 没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"   SUCCESS: 抛出异常: {e}")
        
        # 测试2: 无效字符串参数
        print("\n测试2: 无效字符串参数")
        invalid_config_2 = {
            "name": "test_strategy_2",
            "type": "ma_cross",
            "parameters": {
                "fast_period": 10,
                "slow_period": "invalid"  # 无效字符串
            },
            "description": "测试无效字符串参数"
        }
        
        try:
            result = await strategy_manager.register_strategy(invalid_config_2)
            print(f"   ERROR: 没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"   SUCCESS: 抛出异常: {e}")
        
        # 测试3: 同时包含负数和无效字符串
        print("\n测试3: 同时包含负数和无效字符串")
        invalid_config_3 = {
            "name": "test_strategy_3",
            "type": "ma_cross",
            "parameters": {
                "fast_period": -1,  # 负数
                "slow_period": "invalid"  # 无效字符串
            },
            "description": "测试同时包含负数和无效字符串"
        }
        
        try:
            result = await strategy_manager.register_strategy(invalid_config_3)
            print(f"   ERROR: 没有抛出异常，返回结果: {result}")
        except Exception as e:
            print(f"   SUCCESS: 抛出异常: {e}")
        
        # 测试4: 有效配置
        print("\n测试4: 有效配置")
        valid_config = {
            "name": "test_strategy_4",
            "type": "ma_cross",
            "parameters": {
                "fast_period": 10,
                "slow_period": 20
            },
            "description": "测试有效配置"
        }
        
        try:
            result = await strategy_manager.register_strategy(valid_config)
            print(f"   SUCCESS: 注册成功，策略ID: {result}")
        except Exception as e:
            print(f"   ERROR: 抛出异常: {e}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时文件
        try:
            if hasattr(strategy_manager, 'cleanup'):
                await strategy_manager.cleanup()
        except Exception as e:
            print(f"资源清理失败: {e}")
        
        try:
            os.unlink(temp_db.name)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_async_register_strategy())