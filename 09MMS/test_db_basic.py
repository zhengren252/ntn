#!/usr/bin/env python3
"""
基础数据库测试
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.database import DatabaseManager
from src.models.simulation import SimulationTask, TaskStatus, ScenarioType
from datetime import datetime, timedelta

async def test_basic_functionality():
    """测试基本功能"""
    print("开始基础数据库测试...")
    
    # 使用内存数据库
    db_manager = DatabaseManager(":memory:")
    
    try:
        # 初始化数据库
        print("1. 初始化数据库...")
        await db_manager.init_database()
        print("✓ 数据库初始化成功")
        
        # 测试基本查询
        print("2. 测试基本查询...")
        result = await db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        print(f"✓ 查询成功，找到 {len(result)} 个表")
        
        # 创建测试任务
        print("3. 创建测试任务...")
        task = SimulationTask(
            task_id="test_001",
            symbol="AAPL",
            period="1d",
            scenario=ScenarioType.NORMAL,
            strategy_params={
                "entry_threshold": 0.02,
                "exit_threshold": 0.01,
                "position_size": 0.1,
            },
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
            status=TaskStatus.PENDING,
        )
        
        # 保存任务
        print("4. 保存仿真任务...")
        await db_manager.save_simulation_task(task)
        print("✓ 任务保存成功")
        
        # 获取任务
        print("5. 获取仿真任务...")
        saved_task = await db_manager.get_simulation_task_by_id("test_001")
        if saved_task:
            print(f"✓ 任务获取成功: {saved_task.task_id}")
        else:
            print("✗ 任务获取失败")
            return False
        
        # 更新任务状态
        print("6. 更新任务状态...")
        await db_manager.update_simulation_task_status("test_001", TaskStatus.RUNNING)
        updated_task = await db_manager.get_simulation_task_by_id("test_001")
        if updated_task and updated_task.status == TaskStatus.RUNNING:
            print("✓ 任务状态更新成功")
        else:
            print("✗ 任务状态更新失败")
            return False
        
        print("\n🎉 所有基础测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理资源
        try:
            await db_manager.close_connections()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)