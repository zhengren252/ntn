#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置测试脚本
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ["NTN_ENV"] = "development"
os.environ["REDIS_PASSWORD"] = ""
os.environ["TELEGRAM_API_ID"] = ""
os.environ["TELEGRAM_API_HASH"] = ""
os.environ["TELEGRAM_PHONE"] = ""

try:
    from app.config import ConfigManager

    print("正在初始化ConfigManager...")
    config = ConfigManager("development")

    print("配置加载成功！")
    print(f"环境: {config.environment}")

    # 测试API配置
    api_config = config.get_api_config()
    print(f"API配置: {api_config}")

    # 测试secret_key
    secret_key = config.get("api.auth.secret_key")
    print(f"Secret Key: {secret_key}")

except Exception as e:
    print(f"配置加载失败: {e}")
    import traceback

    traceback.print_exc()
