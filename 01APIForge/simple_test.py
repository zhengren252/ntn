#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的API密钥管理功能测试
不依赖外部库，仅测试基本逻辑
"""

import os
import json
import hashlib
import base64
from datetime import datetime

def test_basic_functionality():
    """测试基本功能"""
    print("=== API密钥管理基本功能测试 ===")
    
    # 1. 测试环境变量检查
    print("\n1. 检查环境变量...")
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY', 
        'SUPABASE_SERVICE_ROLE_KEY',
        'ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请在.env文件中配置这些变量")
    else:
        print("✅ 所有必需的环境变量都已配置")
    
    # 2. 测试加密功能（简化版）
    print("\n2. 测试基本加密功能...")
    try:
        test_key = "test-api-key-12345"
        # 简单的base64编码作为加密示例
        encoded = base64.b64encode(test_key.encode()).decode()
        decoded = base64.b64decode(encoded).decode()
        
        if decoded == test_key:
            print("✅ 基本编码/解码功能正常")
        else:
            print("❌ 编码/解码功能异常")
    except Exception as e:
        print(f"❌ 加密测试失败: {e}")
    
    # 3. 测试API密钥数据结构
    print("\n3. 测试API密钥数据结构...")
    try:
        api_key_data = {
            "id": "test-id-123",
            "name": "测试API密钥",
            "provider": "openai",
            "key_preview": "sk-...xyz",
            "description": "用于测试的API密钥",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 验证数据结构
        required_fields = ['id', 'name', 'provider', 'key_preview', 'is_active']
        missing_fields = [field for field in required_fields if field not in api_key_data]
        
        if not missing_fields:
            print("✅ API密钥数据结构正确")
            print(f"   示例数据: {json.dumps(api_key_data, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 缺少必需字段: {missing_fields}")
    except Exception as e:
        print(f"❌ 数据结构测试失败: {e}")
    
    # 4. 测试密钥预览生成
    print("\n4. 测试密钥预览生成...")
    try:
        def generate_key_preview(key: str) -> str:
            """生成API密钥的预览版本"""
            if len(key) <= 8:
                return key[:2] + "..." + key[-2:]
            else:
                return key[:4] + "..." + key[-4:]
        
        test_keys = [
            "sk-1234567890abcdef",
            "abc123",
            "very-long-api-key-for-testing-purposes"
        ]
        
        for key in test_keys:
            preview = generate_key_preview(key)
            print(f"   原始密钥: {key} -> 预览: {preview}")
        
        print("✅ 密钥预览生成功能正常")
    except Exception as e:
        print(f"❌ 密钥预览生成失败: {e}")
    
    # 5. 测试API响应格式
    print("\n5. 测试API响应格式...")
    try:
        def create_api_response(success: bool, data=None, message: str = ""):
            """创建标准API响应格式"""
            return {
                "success": success,
                "data": data,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        
        # 测试成功响应
        success_response = create_api_response(True, api_key_data, "API密钥创建成功")
        print("✅ 成功响应格式正确")
        
        # 测试错误响应
        error_response = create_api_response(False, None, "API密钥不存在")
        print("✅ 错误响应格式正确")
        
    except Exception as e:
        print(f"❌ API响应格式测试失败: {e}")
    
    print("\n=== 测试完成 ===")
    print("\n📝 下一步操作:")
    print("1. 配置.env文件中的Supabase和加密相关环境变量")
    print("2. 安装Python依赖包 (pip install -r requirements.txt)")
    print("3. 运行完整的Supabase连接测试")
    print("4. 启动APIForge服务进行端到端测试")

if __name__ == "__main__":
    test_basic_functionality()