#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Web界面启动脚本
用于验证Web应用是否能正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from scanner.web.app import create_app

    print("✓ 成功导入Web应用模块")
except ImportError as e:
    print(f"✗ 导入Web应用模块失败: {e}")
    sys.exit(1)

try:
    # 创建Flask应用实例
    app = create_app()
    print("✓ 成功创建Flask应用实例")

    # 检查路由
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.rule} [{', '.join(rule.methods)}]")

    print(f"✓ 注册的路由数量: {len(routes)}")
    for route in routes[:10]:  # 显示前10个路由
        print(f"  - {route}")

    if len(routes) > 10:
        print(f"  ... 还有 {len(routes) - 10} 个路由")

    print("\n✓ Web应用测试通过！")

except Exception as e:
    print(f"✗ Web应用测试失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
