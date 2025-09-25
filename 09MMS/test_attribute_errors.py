#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证AttributeError修复测试脚本
测试config、MetricsCollector和DatabaseManager类是否存在AttributeError
"""

import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_config():
    """测试配置类"""
    try:
        from src.core.config import settings

        print(f"✅ Config测试通过: REDIS_URL = {settings.REDIS_URL}")
        return True
    except AttributeError as e:
        print(f"❌ Config测试失败: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Config测试异常: {e}")
        return False


async def test_metrics_collector():
    """测试MetricsCollector类"""
    try:
        from src.utils.metrics import MetricsCollector

        collector = MetricsCollector()

        # 测试record_request方法是否存在
        if hasattr(collector, "record_request"):
            print("✅ MetricsCollector测试通过: record_request方法存在")
            return True
        else:
            print("❌ MetricsCollector测试失败: record_request方法不存在")
            return False
    except Exception as e:
        print(f"⚠️ MetricsCollector测试异常: {e}")
        return False


async def test_database_manager():
    """测试DatabaseManager类"""
    try:
        from src.core.database import DatabaseManager

        db_manager = DatabaseManager()

        # 测试initialize方法是否存在
        if hasattr(db_manager, "initialize"):
            print("✅ DatabaseManager测试通过: initialize方法存在")
            return True
        else:
            print("❌ DatabaseManager测试失败: initialize方法不存在")
            return False
    except Exception as e:
        print(f"⚠️ DatabaseManager测试异常: {e}")
        return False


async def main():
    """主测试函数"""
    print("开始验证AttributeError修复...")
    print("=" * 50)

    results = []

    # 测试配置类
    print("1. 测试Config类...")
    results.append(await test_config())

    # 测试MetricsCollector类
    print("\n2. 测试MetricsCollector类...")
    results.append(await test_metrics_collector())

    # 测试DatabaseManager类
    print("\n3. 测试DatabaseManager类...")
    results.append(await test_database_manager())

    print("\n" + "=" * 50)
    print("验证结果汇总:")

    if all(results):
        print("🎉 所有AttributeError已修复，测试全部通过！")
        return True
    else:
        failed_count = len([r for r in results if not r])
        print(f"⚠️ 仍有 {failed_count} 个测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    asyncio.run(main())
