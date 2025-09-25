#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ScannerApplication初始化
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/scanner')

from scanner.main import ScannerApplication

async def test_scanner_initialization():
    """测试扫描器初始化"""
    try:
        print("开始测试ScannerApplication初始化...")
        
        # 创建应用实例
        app = ScannerApplication()
        
        # 测试初始化组件
        await app.initialize_components()
        
        print("✅ ScannerApplication初始化成功！")
        return True
        
    except Exception as e:
        print(f"❌ ScannerApplication初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_scanner_initialization())
    sys.exit(0 if success else 1)