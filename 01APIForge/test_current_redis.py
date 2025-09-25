#!/usr/bin/env python3
"""
测试当前RedisConfig类的行为
"""

import os
from api_factory.config.settings import RedisConfig

print("=== 环境变量检查 ===")
print(f"REDIS_HOST: {os.environ.get('REDIS_HOST', 'NOT_SET')}")
print(f"REDIS_PASSWORD: {os.environ.get('REDIS_PASSWORD', 'NOT_SET')}")
print(f"REDIS_PORT: {os.environ.get('REDIS_PORT', 'NOT_SET')}")

print("\n=== 当前RedisConfig类测试 ===")
redis_config = RedisConfig()
print(f"Current RedisConfig - host: {redis_config.host}")
print(f"Current RedisConfig - password: {redis_config.password}")
print(f"Current RedisConfig - port: {redis_config.port}")

print("\n=== 测试不同的case ===")
# 测试小写环境变量
os.environ["redis_host"] = "test_lowercase"
os.environ["redis_password"] = "test_lowercase_pass"

redis_config2 = RedisConfig()
print(f"Lowercase test - host: {redis_config2.host}")
print(f"Lowercase test - password: {redis_config2.password}")

# 清理测试环境变量
del os.environ["redis_host"]
del os.environ["redis_password"]

print("\n=== 测试手动设置REDIS_PORT ===")
os.environ["REDIS_PORT"] = "6380"
redis_config3 = RedisConfig()
print(f"With REDIS_PORT - host: {redis_config3.host}")
print(f"With REDIS_PORT - password: {redis_config3.password}")
print(f"With REDIS_PORT - port: {redis_config3.port}")

print("\n=== 调试model_config ===")
print(f"RedisConfig model_config: {redis_config.model_config}")