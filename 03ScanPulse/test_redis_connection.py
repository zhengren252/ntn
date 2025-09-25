#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis连接测试脚本
用于诊断Redis连接问题
"""

import redis
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_redis_connection():
    """测试Redis连接"""
    print("=== Redis连接测试 ===")
    
    # 从环境变量获取配置
    redis_host = os.getenv('REDIS_HOST', 'redis')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_password = os.getenv('REDIS_PASSWORD')
    redis_db = int(os.getenv('REDIS_DB', '0'))
    
    print(f"Redis配置:")
    print(f"  Host: {redis_host}")
    print(f"  Port: {redis_port}")
    print(f"  Database: {redis_db}")
    print(f"  Password: {'***' if redis_password else 'None'}")
    print()
    
    try:
        # 创建Redis客户端
        print("创建Redis客户端...")
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            decode_responses=True
        )
        
        # 测试连接
        print("测试连接...")
        response = client.ping()
        print(f"Ping响应: {response}")
        
        # 测试基本操作
        print("测试基本操作...")
        test_key = "test:connection"
        test_value = "connection_test_value"
        
        # 设置值
        client.set(test_key, test_value, ex=60)  # 60秒过期
        print(f"设置键值: {test_key} = {test_value}")
        
        # 获取值
        retrieved_value = client.get(test_key)
        print(f"获取键值: {test_key} = {retrieved_value}")
        
        # 删除测试键
        client.delete(test_key)
        print(f"删除测试键: {test_key}")
        
        # 获取Redis信息
        print("\n=== Redis服务器信息 ===")
        info = client.info()
        print(f"Redis版本: {info.get('redis_version')}")
        print(f"连接的客户端数: {info.get('connected_clients')}")
        print(f"使用的内存: {info.get('used_memory_human')}")
        print(f"运行时间: {info.get('uptime_in_seconds')}秒")
        
        print("\n✅ Redis连接测试成功!")
        return True
        
    except redis.ConnectionError as e:
        print(f"\n❌ Redis连接错误: {e}")
        print("可能的原因:")
        print("  1. Redis服务器未运行")
        print("  2. 网络连接问题")
        print("  3. 主机名或端口配置错误")
        return False
        
    except redis.AuthenticationError as e:
        print(f"\n❌ Redis认证错误: {e}")
        print("可能的原因:")
        print("  1. 密码错误")
        print("  2. Redis服务器要求认证但未提供密码")
        return False
        
    except Exception as e:
        print(f"\n❌ Redis连接测试失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        return False

def test_network_connectivity():
    """测试网络连通性"""
    print("\n=== 网络连通性测试 ===")
    
    import socket
    
    redis_host = os.getenv('REDIS_HOST', 'redis')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    
    try:
        print(f"测试到 {redis_host}:{redis_port} 的TCP连接...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((redis_host, redis_port))
        sock.close()
        
        if result == 0:
            print("✅ TCP连接成功")
            return True
        else:
            print(f"❌ TCP连接失败，错误代码: {result}")
            return False
            
    except socket.gaierror as e:
        print(f"❌ DNS解析失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 网络测试失败: {e}")
        return False

if __name__ == "__main__":
    print("Redis连接诊断工具")
    print("=" * 50)
    
    # 显示环境变量
    print("\n=== 环境变量 ===")
    redis_vars = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_DB']
    for var in redis_vars:
        value = os.getenv(var, 'Not Set')
        if 'PASSWORD' in var and value != 'Not Set':
            value = '***'
        print(f"{var}: {value}")
    
    # 测试网络连通性
    network_ok = test_network_connectivity()
    
    # 测试Redis连接
    if network_ok:
        redis_ok = test_redis_connection()
    else:
        print("\n⚠️  跳过Redis连接测试，因为网络连通性测试失败")
        redis_ok = False
    
    print("\n" + "=" * 50)
    if network_ok and redis_ok:
        print("🎉 所有测试通过!")
        sys.exit(0)
    else:
        print("💥 测试失败，请检查配置和网络连接")
        sys.exit(1)