#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试test_error_handling_and_recovery测试
"""

import asyncio
import sys
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.main import StrategyOptimizationModule
from tests.test_optimizer import TestStrategyOptimizerModule

def debug_test():
    """调试测试方法"""
    
    # 创建测试实例
    test_instance = TestStrategyOptimizerModule()
    
    # 调用类级别的初始化
    TestStrategyOptimizerModule.setUpClass()
    
    # 调用实例级别的初始化
    test_instance.setUp()
    
    print("=== 开始调试test_error_handling_and_recovery ===")
    
    try:
        # 直接调用测试方法，让装饰器处理异步
        test_instance.test_error_handling_and_recovery()
        print("✅ 测试通过")
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_instance.tearDown()

if __name__ == "__main__":
    debug_test()