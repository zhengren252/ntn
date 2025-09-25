#!/usr/bin/env python3
"""
测试SettingsConfigDict的正确用法
"""

import os
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

print("=== 环境变量检查 ===")
print(f"REDIS_HOST: {os.environ.get('REDIS_HOST', 'NOT_SET')}")
print(f"REDIS_PASSWORD: {os.environ.get('REDIS_PASSWORD', 'NOT_SET')}")

# 测试1: 直接在类定义中使用SettingsConfigDict
class TestRedisConfig1(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None

print("\n=== 测试1: 直接SettingsConfigDict ===")
config1 = TestRedisConfig1()
print(f"Test1 - host: {config1.host}")
print(f"Test1 - password: {config1.password}")
print(f"Test1 - model_config: {config1.model_config}")

# 测试2: 使用Config类（旧方式）
class TestRedisConfig2(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    
    class Config:
        env_prefix = "REDIS_"

print("\n=== 测试2: Config类方式 ===")
config2 = TestRedisConfig2()
print(f"Test2 - host: {config2.host}")
print(f"Test2 - password: {config2.password}")

# 测试3: 检查当前settings.py中的导入
print("\n=== 测试3: 检查导入 ===")
try:
    from api_factory.config.settings import RedisConfig
    print("RedisConfig imported successfully")
    print(f"RedisConfig.__bases__: {RedisConfig.__bases__}")
    print(f"RedisConfig.__dict__.keys(): {list(RedisConfig.__dict__.keys())}")
except Exception as e:
    print(f"Import error: {e}")