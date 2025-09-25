#!/usr/bin/env python3
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class TestRedisConfig(BaseSettings):
    host: str = Field(default="localhost", env="REDIS_HOST")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

print("Environment variables:")
print(f"REDIS_HOST: {os.environ.get('REDIS_HOST')}")
print(f"REDIS_PASSWORD: {os.environ.get('REDIS_PASSWORD')}")

print("\nConfig values:")
config = TestRedisConfig()
print(f"host: {config.host}")
print(f"password: {config.password}")

print("\nForced config values:")
config2 = TestRedisConfig(host=os.environ.get('REDIS_HOST', 'localhost'), 
                         password=os.environ.get('REDIS_PASSWORD'))
print(f"host: {config2.host}")
print(f"password: {config2.password}")