#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复测试错误处理问题

问题分析：
1. invalid_strategy_config 被传递给 StrategyOptimizationModule 构造函数
2. StrategyOptimizationModule._validate_config 只验证模块配置，不验证策略参数
3. 策略参数验证应该在 register_strategy 方法中进行
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from optimizer.main import StrategyOptimizationModule
from optimizer.strategies.manager import StrategyConfig

async def test_correct_error_handling():
    """
    测试正确的错误处理流程
    """
    print("=== 测试正确的错误处理流程 ===")
    
    # 1. 创建有效的模块配置
    valid_module_config = {
        "environment": "test",
        "database": {
            "sqlite_path": ":memory:",
        },
    }
    
    print(f"1. 创建StrategyOptimizationModule，配置: {valid_module_config}")
    optimizer_module = StrategyOptimizationModule(valid_module_config)
    
    print("2. 初始化模块")
    await optimizer_module.initialize()
    
    try:
        # 3. 测试无效策略配置 - 这里应该抛出异常
        print("3. 测试无效策略配置")
        
        # 创建包含无效参数的策略配置
        invalid_strategy_config = {
            "strategy_id": "test_invalid_strategy",
            "name": "invalid_strategy", 
            "version": "1.0",
            "description": "无效策略测试",
            "parameters": {
                "fast_period": {
                    "type": "int",
                    "min": 5,
                    "max": 50,
                    "default": -1  # 无效的默认值
                },
                "slow_period": {
                    "type": "int", 
                    "min": 10,
                    "max": 200,
                    "default": "invalid"  # 无效的类型
                }
            },
            "risk_limits": {
                "max_drawdown": 0.10,
                "max_position_size": 0.25,
                "daily_loss_limit": 0.03,
            },
            "performance_metrics": {
                "expected_return": 0.15,
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.06,
                "win_rate": 0.58,
            },
        }
        
        print(f"   无效策略配置: {invalid_strategy_config}")
        
        try:
            # 尝试注册无效策略 - 这里应该抛出异常
            strategy_config = StrategyConfig(**invalid_strategy_config)
            print(f"   StrategyConfig创建成功: {strategy_config}")
            
            result = await optimizer_module.components.strategy_manager.register_strategy(strategy_config)
            print(f"   ERROR: register_strategy没有抛出异常，返回结果: {result}")
            print("   这表明验证逻辑有问题！")
            
        except Exception as e:
            print(f"   SUCCESS: 正确抛出异常: {e}")
            print("   测试通过：register_strategy正确抛出异常")
            
        # 4. 测试另一种无效配置
        print("4. 测试另一种无效配置 - 直接传递字典")
        
        invalid_dict_config = {
            "name": "invalid_strategy",
            "type": "ma_cross", 
            "parameters": {
                "fast_period": -1,  # 无效参数
                "slow_period": "invalid",  # 无效类型
            },
            "description": "无效策略测试",
        }
        
        try:
            result = await optimizer_module.components.strategy_manager.register_strategy(invalid_dict_config)
            print(f"   ERROR: register_strategy没有抛出异常，返回结果: {result}")
            
        except Exception as e:
            print(f"   SUCCESS: 正确抛出异常: {e}")
            
    finally:
        print("5. 清理资源")
        try:
            await optimizer_module.cleanup()
        except Exception as e:
            print(f"   资源清理失败: {e}")
            
    print("=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_correct_error_handling())