#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的数据库功能测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import DatabaseManager
from src.core.config import DatabaseConfig

async def test_basic_functionality():
    """测试基本功能"""
    print("开始测试DatabaseManager基本功能...")
    
    # 使用内存数据库进行测试
    config = DatabaseConfig(
        database_url=":memory:",
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600
    )
    
    db_manager = DatabaseManager(config)
    
    try:
        # 测试数据库初始化
        print("1. 测试数据库初始化...")
        await db_manager.init_database()
        print("   ✓ 数据库初始化成功")
        
        # 测试简单查询
        print("2. 测试简单查询...")
        result = await db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        print(f"   ✓ 查询成功，找到 {len(result)} 个表")
        
        # 测试事务
        print("3. 测试事务...")
        queries = [
            "INSERT INTO calibration_params (param_id, symbol, scenario, base_slippage, volatility_factor, liquidity_factor) VALUES ('test1', 'TEST', 'normal', 0.001, 1.0, 1.0)"
        ]
        await db_manager.execute_transaction(queries)
        print("   ✓ 事务执行成功")
        
        # 验证插入的数据
        print("4. 验证插入的数据...")
        result = await db_manager.execute_query("SELECT COUNT(*) FROM calibration_params WHERE param_id='test1'")
        count = result[0][0] if result else 0
        print(f"   ✓ 找到 {count} 条测试数据")
        
        print("\n所有测试通过！")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await db_manager.close()

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)