#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIForge Supabase集成测试
测试实际的Supabase客户端和加密管理器集成
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

try:
    from api_factory.config.settings import get_settings
    from api_factory.database.supabase_client import SupabaseClient
    from api_factory.security.encryption import EncryptionManager
    from api_factory.dependencies import get_supabase_client, get_encryption_manager
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    sys.exit(1)


async def test_encryption_manager():
    """测试加密管理器"""
    print("\n🔐 测试加密管理器...")
    
    try:
        encryption_manager = await get_encryption_manager()
        
        # 测试加密解密
        test_data = "sk-1234567890abcdef"
        encrypted = encryption_manager.encrypt(test_data, "api_key")
        decrypted = encryption_manager.decrypt(encrypted, "api_key")
        
        if test_data == decrypted:
            print("   ✅ 加密解密测试通过")
        else:
            print("   ❌ 加密解密测试失败")
            return False
            
        # 测试密钥遮盖
        masked = encryption_manager.mask_key(test_data)
        print(f"   ✅ 密钥遮盖: {masked}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 加密管理器测试失败: {e}")
        return False


async def test_supabase_client():
    """测试Supabase客户端"""
    print("\n🗄️ 测试Supabase客户端...")
    
    try:
        supabase_client = await get_supabase_client()
        
        # 测试健康检查
        health = await supabase_client.health_check()
        if health:
            print("   ✅ Supabase连接健康检查通过")
        else:
            print("   ❌ Supabase连接健康检查失败")
            return False
            
        # 测试创建表（如果不存在）
        table_created = await supabase_client.create_api_keys_table()
        if table_created:
            print("   ✅ api_keys表创建/验证成功")
        else:
            print("   ⚠️ api_keys表创建/验证失败，但可能已存在")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Supabase客户端测试失败: {e}")
        return False


async def test_api_key_operations():
    """测试API密钥CRUD操作"""
    print("\n🔑 测试API密钥CRUD操作...")
    
    try:
        supabase_client = await get_supabase_client()
        
        # 测试数据
        test_key_name = "test_openai_key"
        test_provider = "openai"
        test_api_key = "sk-test1234567890abcdef"
        test_description = "测试用的OpenAI API密钥"
        
        # 1. 创建API密钥
        print("   📝 创建API密钥...")
        created_key = await supabase_client.create_api_key(
            name=test_key_name,
            provider=test_provider,
            api_key=test_api_key,
            description=test_description,
            created_by="test_user"
        )
        
        if created_key and created_key.get('success'):
            print("   ✅ API密钥创建成功")
        else:
            print("   ❌ API密钥创建失败")
            return False
            
        # 2. 查询API密钥
        print("   🔍 查询API密钥...")
        retrieved_key = await supabase_client.get_api_key(test_key_name, decrypt=True)
        
        if retrieved_key:
            print("   ✅ API密钥查询成功")
            print(f"      名称: {retrieved_key.get('name')}")
            print(f"      提供商: {retrieved_key.get('provider')}")
        else:
            print("   ❌ API密钥查询失败")
            return False
            
        # 3. 列出API密钥
        print("   📋 列出API密钥...")
        key_list = await supabase_client.list_api_keys(provider=test_provider)
        
        if key_list and len(key_list) > 0:
            print(f"   ✅ 找到 {len(key_list)} 个API密钥")
        else:
            print("   ⚠️ 未找到API密钥")
            
        # 4. 更新API密钥
        print("   ✏️ 更新API密钥...")
        updated_key = await supabase_client.update_api_key(
            name=test_key_name,
            description="更新后的描述"
        )
        
        if updated_key and updated_key.get('success'):
            print("   ✅ API密钥更新成功")
        else:
            print("   ❌ API密钥更新失败")
            
        # 5. 删除API密钥（软删除）
        print("   🗑️ 删除API密钥...")
        deleted = await supabase_client.delete_api_key(test_key_name, soft_delete=True)
        
        if deleted:
            print("   ✅ API密钥删除成功")
        else:
            print("   ❌ API密钥删除失败")
            
        return True
        
    except Exception as e:
        print(f"   ❌ API密钥操作测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=== APIForge Supabase集成测试 ===")
    
    # 加载环境变量
    try:
        env_file = Path('.env.local')
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
    except Exception as e:
        print(f"⚠️ 加载.env.local失败: {e}")
    
    # 检查环境变量
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    encryption_key = os.getenv('ENCRYPTION_KEY')
    
    print(f"\n📋 配置检查:")
    print(f"   SUPABASE_URL: {'✅ 已配置' if supabase_url else '❌ 未配置'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ 已配置' if supabase_key else '❌ 未配置'}")
    print(f"   ENCRYPTION_KEY: {'✅ 已配置' if encryption_key else '❌ 未配置'}")
    
    if not all([supabase_url, supabase_key, encryption_key]):
        print("\n❌ 请先配置.env.local文件中的相关环境变量")
        print("   运行 python setup_dev_env.py 获取设置指南")
        return
    
    # 运行测试
    tests = [
        ("加密管理器", test_encryption_manager),
        ("Supabase客户端", test_supabase_client),
        ("API密钥操作", test_api_key_operations)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n=== 测试结果汇总 ===")
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 总体结果: {passed}/{len(results)} 测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！APIForge Supabase集成正常工作")
    else:
        print("⚠️ 部分测试失败，请检查配置和依赖")


if __name__ == "__main__":
    asyncio.run(main())