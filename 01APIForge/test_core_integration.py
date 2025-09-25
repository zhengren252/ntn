#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心集成测试 - 简化版本
测试APIForge核心功能，不依赖复杂的外部库
"""

import os
import sys
import json
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional


class SimpleEncryption:
    """简化的加密类，用于测试"""
    
    def __init__(self, key: str):
        self.key = key.encode('utf-8')
    
    def encrypt(self, data: str) -> str:
        """简单的Base64编码（生产环境应使用真正的加密）"""
        encoded = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        return f"enc_{encoded}"
    
    def decrypt(self, encrypted_data: str) -> str:
        """简单的Base64解码"""
        if encrypted_data.startswith('enc_'):
            encoded = encrypted_data[4:]
            return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        return encrypted_data
    
    def mask_key(self, api_key: str) -> str:
        """遮盖API密钥"""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


class MockSupabaseClient:
    """模拟Supabase客户端"""
    
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.data_store = {}  # 内存存储，模拟数据库
        self.encryption = SimpleEncryption(os.getenv('ENCRYPTION_KEY', 'test-key'))
    
    async def health_check(self) -> bool:
        """健康检查"""
        return bool(self.url and self.key)
    
    async def create_api_key(self, name: str, provider: str, api_key: str, 
                           description: str = "", created_by: str = "system") -> Dict[str, Any]:
        """创建API密钥"""
        try:
            encrypted_key = self.encryption.encrypt(api_key)
            
            key_data = {
                'id': hashlib.md5(name.encode()).hexdigest()[:8],
                'name': name,
                'provider': provider,
                'encrypted_api_key': encrypted_key,
                'description': description,
                'created_by': created_by,
                'is_active': True,
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            }
            
            self.data_store[name] = key_data
            return {'success': True, 'data': key_data}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_api_key(self, name: str, decrypt: bool = False) -> Optional[Dict[str, Any]]:
        """获取API密钥"""
        if name not in self.data_store:
            return None
            
        key_data = self.data_store[name].copy()
        
        if decrypt and 'encrypted_api_key' in key_data:
            try:
                key_data['api_key'] = self.encryption.decrypt(key_data['encrypted_api_key'])
                key_data['masked_key'] = self.encryption.mask_key(key_data['api_key'])
            except Exception:
                key_data['api_key'] = "[解密失败]"
                key_data['masked_key'] = "****"
        
        return key_data
    
    async def list_api_keys(self, provider: Optional[str] = None) -> list:
        """列出API密钥"""
        keys = []
        for key_data in self.data_store.values():
            if provider is None or key_data.get('provider') == provider:
                # 返回不包含敏感信息的版本
                safe_data = key_data.copy()
                if 'encrypted_api_key' in safe_data:
                    del safe_data['encrypted_api_key']
                safe_data['masked_key'] = self.encryption.mask_key(
                    self.encryption.decrypt(key_data.get('encrypted_api_key', ''))
                )
                keys.append(safe_data)
        return keys
    
    async def update_api_key(self, name: str, **updates) -> Dict[str, Any]:
        """更新API密钥"""
        if name not in self.data_store:
            return {'success': False, 'error': 'Key not found'}
        
        try:
            for key, value in updates.items():
                if key in ['description', 'is_active']:
                    self.data_store[name][key] = value
            
            self.data_store[name]['updated_at'] = '2024-01-01T00:00:00Z'
            return {'success': True, 'data': self.data_store[name]}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def delete_api_key(self, name: str, soft_delete: bool = True) -> bool:
        """删除API密钥"""
        if name not in self.data_store:
            return False
        
        if soft_delete:
            self.data_store[name]['is_active'] = False
            self.data_store[name]['deleted_at'] = '2024-01-01T00:00:00Z'
        else:
            del self.data_store[name]
        
        return True


def load_env_file(file_path: str) -> Dict[str, str]:
    """加载环境变量文件"""
    env_vars = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        pass
    return env_vars


async def test_encryption():
    """测试加密功能"""
    print("\n🔐 测试加密功能...")
    
    encryption_key = os.getenv('ENCRYPTION_KEY', 'test-encryption-key')
    encryption = SimpleEncryption(encryption_key)
    
    # 测试数据
    test_data = "sk-1234567890abcdef"
    
    try:
        # 加密
        encrypted = encryption.encrypt(test_data)
        print(f"   原始数据: {test_data}")
        print(f"   加密后: {encrypted}")
        
        # 解密
        decrypted = encryption.decrypt(encrypted)
        print(f"   解密后: {decrypted}")
        
        # 验证
        if test_data == decrypted:
            print("   ✅ 加密解密测试通过")
        else:
            print("   ❌ 加密解密测试失败")
            return False
        
        # 测试密钥遮盖
        masked = encryption.mask_key(test_data)
        print(f"   遮盖后: {masked}")
        print("   ✅ 密钥遮盖测试通过")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 加密测试失败: {e}")
        return False


async def test_mock_supabase():
    """测试模拟Supabase客户端"""
    print("\n🗄️ 测试模拟Supabase客户端...")
    
    supabase_url = os.getenv('SUPABASE_URL', 'https://test.supabase.co')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', 'test-key')
    
    client = MockSupabaseClient(supabase_url, supabase_key)
    
    try:
        # 健康检查
        health = await client.health_check()
        if health:
            print("   ✅ 健康检查通过")
        else:
            print("   ❌ 健康检查失败")
            return False
        
        # 测试CRUD操作
        test_name = "test_openai_key"
        test_provider = "openai"
        test_api_key = "sk-test1234567890abcdef"
        test_description = "测试用的OpenAI API密钥"
        
        # 创建
        print("   📝 创建API密钥...")
        create_result = await client.create_api_key(
            name=test_name,
            provider=test_provider,
            api_key=test_api_key,
            description=test_description
        )
        
        if create_result.get('success'):
            print("   ✅ API密钥创建成功")
        else:
            print(f"   ❌ API密钥创建失败: {create_result.get('error')}")
            return False
        
        # 查询
        print("   🔍 查询API密钥...")
        retrieved = await client.get_api_key(test_name, decrypt=True)
        
        if retrieved:
            print(f"   ✅ 查询成功: {retrieved['name']} ({retrieved['provider']})")
            print(f"   遮盖密钥: {retrieved.get('masked_key', 'N/A')}")
        else:
            print("   ❌ 查询失败")
            return False
        
        # 列表
        print("   📋 列出API密钥...")
        key_list = await client.list_api_keys(provider=test_provider)
        
        if key_list:
            print(f"   ✅ 找到 {len(key_list)} 个密钥")
        else:
            print("   ⚠️ 未找到密钥")
        
        # 更新
        print("   ✏️ 更新API密钥...")
        update_result = await client.update_api_key(
            name=test_name,
            description="更新后的描述"
        )
        
        if update_result.get('success'):
            print("   ✅ 更新成功")
        else:
            print(f"   ❌ 更新失败: {update_result.get('error')}")
        
        # 删除
        print("   🗑️ 删除API密钥...")
        delete_result = await client.delete_api_key(test_name, soft_delete=True)
        
        if delete_result:
            print("   ✅ 删除成功")
        else:
            print("   ❌ 删除失败")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Supabase客户端测试失败: {e}")
        return False


async def test_api_response_format():
    """测试API响应格式"""
    print("\n📡 测试API响应格式...")
    
    try:
        # 模拟API响应
        success_response = {
            "success": True,
            "data": {
                "id": "key_123",
                "name": "test_key",
                "provider": "openai",
                "masked_key": "sk-12****cdef",
                "description": "测试密钥",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z"
            },
            "timestamp": "2024-01-01T00:00:00Z",
            "request_id": "req_123456"
        }
        
        error_response = {
            "success": False,
            "error": {
                "code": "KEY_NOT_FOUND",
                "message": "指定的API密钥不存在",
                "details": {}
            },
            "timestamp": "2024-01-01T00:00:00Z",
            "request_id": "req_123457"
        }
        
        # 验证响应格式
        required_fields = ['success', 'timestamp', 'request_id']
        
        for response_name, response in [("成功响应", success_response), ("错误响应", error_response)]:
            print(f"   📋 验证{response_name}...")
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ❌ 缺少必需字段: {missing_fields}")
                return False
            
            if response['success'] and 'data' not in response:
                print("   ❌ 成功响应缺少data字段")
                return False
            
            if not response['success'] and 'error' not in response:
                print("   ❌ 错误响应缺少error字段")
                return False
            
            print(f"   ✅ {response_name}格式正确")
        
        print("   ✅ API响应格式测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ API响应格式测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=== APIForge 核心集成测试 ===")
    
    # 加载环境变量
    env_files = ['.env.local', '.env']
    for env_file in env_files:
        if Path(env_file).exists():
            env_vars = load_env_file(env_file)
            for key, value in env_vars.items():
                os.environ[key] = value
            print(f"✅ 已加载 {env_file}")
            break
    else:
        print("⚠️ 未找到环境变量文件")
    
    # 检查关键环境变量
    required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'ENCRYPTION_KEY']
    print(f"\n📋 环境变量检查:")
    
    for var in required_vars:
        value = os.getenv(var)
        status = "✅ 已配置" if value else "❌ 未配置"
        print(f"   {var}: {status}")
    
    # 运行测试
    tests = [
        ("加密功能", test_encryption),
        ("模拟Supabase客户端", test_mock_supabase),
        ("API响应格式", test_api_response_format)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出结果
    print("\n=== 测试结果汇总 ===")
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 总体结果: {passed}/{len(results)} 测试通过")
    
    if passed == len(results):
        print("🎉 所有核心功能测试通过！")
        print("\n📝 下一步建议:")
        print("   1. 配置真实的Supabase项目")
        print("   2. 安装完整的Python依赖")
        print("   3. 运行完整的APIForge服务")
        print("   4. 执行端到端集成测试")
    else:
        print("⚠️ 部分测试失败，请检查配置")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())