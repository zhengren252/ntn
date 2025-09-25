#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的测试调试脚本
直接模拟测试环境中的行为
"""

import asyncio
import tempfile
import os
import shutil
from optimizer.main import StrategyOptimizationModule

async def test_error_handling_debug():
    """调试错误处理测试"""
    print("=== 开始调试错误处理测试 ===")
    
    # 创建临时目录和数据库
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_optimizer.db")
    
    # 创建与测试相同的配置
    test_config = {
        "environment": "test",
        "database": {
            "sqlite_path": test_db_path,  # 使用真实的数据库文件
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
    
    print(f"DEBUG: test_config = {test_config}")
    
    # 创建策略优化模组
    optimizer_module = StrategyOptimizationModule(test_config)
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
        
        # 直接调用register_strategy方法
        try:
            result = await optimizer_module.strategy_manager.register_strategy(
                invalid_strategy_config
            )
            print(f"❌ 错误：没有抛出异常，返回结果: {result}")
            print(f"DEBUG: register_strategy返回结果: {result}")
            print(f"DEBUG: 没有抛出异常，这是问题所在！")
            return False
        except Exception as e:
            print(f"✅ 正确：抛出异常: {type(e).__name__}: {e}")
            return True
            
    finally:
        await optimizer_module.cleanup()
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print("\n=== 清理完成 ===")

if __name__ == "__main__":
    result = asyncio.run(test_error_handling_debug())
    print(f"\n测试结果: {'通过' if result else '失败'}")