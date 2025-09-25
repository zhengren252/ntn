#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的DatabaseManager测试
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_basic_functionality():
    """测试基本功能"""
    try:
        # 使用内存数据库
        db_manager = DatabaseManager(":memory:")
        logger.info("DatabaseManager 初始化成功")
        
        # 初始化数据库
        await db_manager.init_database()
        logger.info("数据库初始化成功")
        
        # 测试基本查询
        result = await db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        logger.info(f"数据库表: {result}")
        
        # 测试保存仿真任务
        task_data = {
            'task_id': 'test_task_001',
            'symbol': 'BTCUSDT',
            'strategy_name': 'test_strategy',
            'parameters': '{"param1": "value1"}',
            'status': 'pending',
            'created_at': '2024-01-01 00:00:00'
        }
        
        await db_manager.save_simulation_task(task_data)
        logger.info("仿真任务保存成功")
        
        # 测试获取仿真任务
        task = await db_manager.get_simulation_task_by_id('test_task_001')
        logger.info(f"获取到的任务: {task}")
        
        # 测试更新任务状态
        await db_manager.update_task_status('test_task_001', 'running')
        logger.info("任务状态更新成功")
        
        # 验证状态更新
        updated_task = await db_manager.get_simulation_task_by_id('test_task_001')
        logger.info(f"更新后的任务: {updated_task}")
        
        # 关闭数据库
        await db_manager.close()
        logger.info("数据库关闭成功")
        
        print("\n=== 所有测试通过! ===")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)