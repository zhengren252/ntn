#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroHub - 总控模块主入口
NeuroTrade Nexus (NTN) - Module 08
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.app import create_app
from config.settings import get_settings

def main():
    """
    NeuroHub总控模块主入口函数
    """
    try:
        settings = get_settings()
        app = create_app()
        
        print(f"NeuroHub总控模块启动中...")
        print(f"环境: {settings.environment}")
        print(f"端口: {settings.port}")
        
        # 启动应用
        import uvicorn
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower()
        )
        
    except Exception as e:
        print(f"NeuroHub总控模块启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()