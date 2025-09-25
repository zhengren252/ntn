#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan Pulse 启动调试脚本
用于诊断启动过程中的问题
"""

import sys
import asyncio
import traceback
from pathlib import Path

def test_imports():
    """测试模块导入"""
    print("=== 测试模块导入 ===")
    
    try:
        print("1. 导入基础模块...")
        import scanner
        print("   ✅ scanner模块导入成功")
        
        print("2. 导入配置管理器...")
        from scanner.config.env_manager import get_env_manager
        print("   ✅ 环境管理器导入成功")
        
        print("3. 导入日志系统...")
        from scanner.utils.logger import get_logger, setup_logging
        print("   ✅ 日志系统导入成功")
        
        print("4. 导入Redis客户端...")
        from scanner.communication.redis_client import RedisClient
        print("   ✅ Redis客户端导入成功")
        
        print("5. 导入ZeroMQ客户端...")
        from scanner.communication.zmq_client import ScannerZMQClient
        print("   ✅ ZeroMQ客户端导入成功")
        
        print("6. 导入TACoreService适配器...")
        from scanner.adapters.trading_agents_cn_adapter import TACoreServiceClient, TACoreServiceAgent
        print("   ✅ TACoreService适配器导入成功")
        
        print("7. 导入扫描引擎...")
        from scanner.engines.three_high_engine import ThreeHighEngine
        from scanner.detectors.black_horse_detector import BlackHorseDetector
        from scanner.detectors.potential_finder import PotentialFinder
        print("   ✅ 扫描引擎导入成功")
        
        print("8. 导入健康检查...")
        from scanner.health_check import get_health_checker
        print("   ✅ 健康检查导入成功")
        
        print("9. 导入Web应用...")
        from scanner.web.app import create_app, run_web_app
        print("   ✅ Web应用导入成功")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        print(f"   错误详情: {traceback.format_exc()}")
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n=== 测试配置加载 ===")
    
    try:
        from scanner.config.env_manager import get_env_manager
        
        env_manager = get_env_manager()
        print(f"1. 环境管理器创建成功: {env_manager}")
        
        environment = env_manager.get_environment()
        print(f"2. 当前环境: {environment}")
        
        redis_config = env_manager.get_redis_config()
        print(f"3. Redis配置: {redis_config}")
        
        zmq_config = env_manager.get_zmq_config()
        print(f"4. ZeroMQ配置: {zmq_config}")
        
        scanner_config = env_manager.get_scanner_config()
        print(f"5. 扫描器配置: {scanner_config}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
        print(f"   错误详情: {traceback.format_exc()}")
        return False

def test_redis_connection():
    """测试Redis连接"""
    print("\n=== 测试Redis连接 ===")
    
    try:
        from scanner.config.env_manager import get_env_manager
        from scanner.communication.redis_client import RedisClient
        
        env_manager = get_env_manager()
        redis_config = env_manager.get_redis_config()
        
        print(f"1. Redis配置: {redis_config}")
        
        redis_client = RedisClient(redis_config)
        print("2. Redis客户端创建成功")
        
        connected = redis_client.connect()
        print(f"3. Redis连接结果: {connected}")
        
        if connected:
            redis_client.disconnect()
            print("4. Redis连接已断开")
        
        return connected
        
    except Exception as e:
        print(f"   ❌ Redis连接失败: {e}")
        print(f"   错误详情: {traceback.format_exc()}")
        return False

async def test_application_startup():
    """测试应用程序启动"""
    print("\n=== 测试应用程序启动 ===")
    
    try:
        from scanner.main import ScannerApplication
        
        print("1. 创建ScannerApplication实例...")
        app = ScannerApplication()
        print("   ✅ ScannerApplication创建成功")
        
        print("2. 初始化组件...")
        success = await app.initialize_components()
        print(f"   组件初始化结果: {success}")
        
        if success:
            print("3. 验证配置...")
            validation_result = app.env_manager.validate_config()
            print(f"   配置验证结果: {validation_result}")
        
        return success
        
    except Exception as e:
        print(f"   ❌ 应用程序启动失败: {e}")
        print(f"   错误详情: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    print("Scan Pulse 启动调试脚本")
    print("=" * 50)
    
    # 测试模块导入
    if not test_imports():
        print("\n❌ 模块导入测试失败，停止后续测试")
        return False
    
    # 测试配置加载
    if not test_config_loading():
        print("\n❌ 配置加载测试失败，停止后续测试")
        return False
    
    # 测试Redis连接
    if not test_redis_connection():
        print("\n⚠️  Redis连接测试失败，但继续后续测试")
    
    # 测试应用程序启动
    try:
        success = asyncio.run(test_application_startup())
        if success:
            print("\n✅ 所有测试通过！Scan Pulse应该可以正常启动")
        else:
            print("\n❌ 应用程序启动测试失败")
        return success
    except Exception as e:
        print(f"\n❌ 异步测试失败: {e}")
        print(f"错误详情: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

