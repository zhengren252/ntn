#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Web服务器启动脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner.web.app import create_app, run_web_app
from scanner.utils.logger import get_logger


async def main():
    """主函数"""
    logger = get_logger(__name__)

    try:
        # 创建Web应用
        logger.info("创建Web应用...")
        app = create_app()

        # 启动Web服务器
        logger.info("启动Web服务器在 http://localhost:8080")
        await run_web_app(app=app, host="0.0.0.0", port=8080, debug=True)

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭Web服务器...")
    except Exception as e:
        logger.error(f"Web服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    print("启动ScanPulse Web界面...")
    print("访问地址: http://localhost:8080")
    print("按 Ctrl+C 停止服务器")
    print("-" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)
