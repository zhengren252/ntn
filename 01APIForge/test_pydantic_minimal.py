#!/usr/bin/env python3
"""
最小化pydantic_settings测试脚本
用于诊断Redis配置问题
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

print("=== 环境变量检查 ===")
print(f"REDIS_HOST: {os.environ.get('REDIS_HOST', 'NOT_SET')}")
print(f"REDIS_PASSWORD: {os.environ.get('REDIS_PASSWORD', 'NOT_SET')}")
print(f"REDIS_PORT: {os.environ.get('REDIS_PORT', 'NOT_SET')}")

print("\n=== 方法1: 基础BaseSettings ===")
class BasicRedisConfig(BaseSettings):
    host: str = "localhost"
    password: Optional[str] = None
    port: int = 6379

basic_config = BasicRedisConfig()
print(f"Basic - host: {basic_config.host}")
print(f"Basic - password: {basic_config.password}")
print(f"Basic - port: {basic_config.port}")

print("\n=== 方法2: 使用Field(env=...) ===")
class FieldRedisConfig(BaseSettings):
    host: str = Field(default="localhost", env="REDIS_HOST")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    port: int = Field(default=6379, env="REDIS_PORT")

field_config = FieldRedisConfig()
print(f"Field - host: {field_config.host}")
print(f"Field - password: {field_config.password}")
print(f"Field - port: {field_config.port}")

print("\n=== 方法3: 使用SettingsConfigDict ===")
class ConfigDictRedisConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
    
    host: str = Field(default="localhost", env="REDIS_HOST")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    port: int = Field(default=6379, env="REDIS_PORT")

config_dict_config = ConfigDictRedisConfig()
print(f"ConfigDict - host: {config_dict_config.host}")
print(f"ConfigDict - password: {config_dict_config.password}")
print(f"ConfigDict - port: {config_dict_config.port}")

print("\n=== 方法4: 显式传递环境变量 ===")
class ExplicitRedisConfig(BaseSettings):
    host: str = Field(default="localhost", env="REDIS_HOST")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    port: int = Field(default=6379, env="REDIS_PORT")

explicit_config = ExplicitRedisConfig(
    host=os.environ.get("REDIS_HOST", "localhost"),
    password=os.environ.get("REDIS_PASSWORD"),
    port=int(os.environ.get("REDIS_PORT", "6379"))
)
print(f"Explicit - host: {explicit_config.host}")
print(f"Explicit - password: {explicit_config.password}")
print(f"Explicit - port: {explicit_config.port}")

print("\n=== 方法5: 测试env_prefix ===")
class PrefixRedisConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = "localhost"
    password: Optional[str] = None
    port: int = 6379

prefix_config = PrefixRedisConfig()
print(f"Prefix - host: {prefix_config.host}")
print(f"Prefix - password: {prefix_config.password}")
print(f"Prefix - port: {prefix_config.port}")

print("\n=== 调试信息 ===")
import pydantic_settings
print(f"pydantic_settings version: {pydantic_settings.__version__}")

# 尝试手动设置环境变量
os.environ["TEST_VAR"] = "test_value"
class TestConfig(BaseSettings):
    test_var: str = Field(default="default", env="TEST_VAR")

test_config = TestConfig()
print(f"Manual env test - test_var: {test_config.test_var}")