#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置验证脚本

验证ReviewGuard模组的环境配置文件完整性和一致性：
1. 检查必需的环境变量
2. 验证端口配置一致性
3. 检查ZeroMQ主题名称统一性
4. 验证敏感信息配置
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class EnvConfigValidator:
    """环境配置验证器"""
    
    def __init__(self):
        self.project_root = project_root
        self.env_files = {
            'development': self.project_root / '.env.example',
            'staging': self.project_root / '.env.staging',
            'production': self.project_root / '.env.production'
        }
        
        # 必需的环境变量
        self.required_vars = {
            'APP_ENV', 'API_PORT', 'SERVER_PORT',
            'ZEROMQ_SUB_ENDPOINT', 'ZEROMQ_PUB_ENDPOINT',
            'ZEROMQ_SUB_TOPIC', 'ZEROMQ_PUB_TOPIC',
            'JWT_SECRET_KEY', 'DATABASE_PATH',
            'REDIS_HOST', 'REDIS_PORT'
        }
        
        # 期望的配置值
        self.expected_values = {
            'API_PORT': '8000',
            'SERVER_PORT': '8000',
            'ZEROMQ_SUB_PORT': '5555',
            'ZEROMQ_PUB_PORT': '5556',
            'ZEROMQ_SUB_TOPIC': 'optimizer.pool.trading',
            'ZEROMQ_PUB_TOPIC': 'review.pool.approved'
        }
        
        # 敏感信息变量（不应该有硬编码值）
        self.sensitive_vars = {
            'JWT_SECRET_KEY', 'JWT_SECRET', 'REDIS_PASSWORD',
            'ADMIN_DEFAULT_PASSWORD', 'REVIEWER_DEFAULT_PASSWORD'
        }
    
    def load_env_file(self, file_path: Path) -> Dict[str, str]:
        """加载环境变量文件"""
        env_vars = {}
        
        if not file_path.exists():
            return env_vars
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"❌ 读取文件 {file_path} 失败: {e}")
        
        return env_vars
    
    def validate_required_vars(self, env_name: str, env_vars: Dict[str, str]) -> List[str]:
        """验证必需的环境变量"""
        missing_vars = []
        
        for var in self.required_vars:
            if var not in env_vars or not env_vars[var]:
                missing_vars.append(var)
        
        return missing_vars
    
    def validate_expected_values(self, env_name: str, env_vars: Dict[str, str]) -> List[str]:
        """验证期望的配置值"""
        inconsistent_vars = []
        
        for var, expected_value in self.expected_values.items():
            if var in env_vars and env_vars[var] != expected_value:
                inconsistent_vars.append(f"{var}: 期望 '{expected_value}', 实际 '{env_vars[var]}'")
        
        return inconsistent_vars
    
    def validate_sensitive_vars(self, env_name: str, env_vars: Dict[str, str]) -> List[str]:
        """验证敏感信息配置"""
        insecure_vars = []
        
        # 检查生产环境的敏感信息
        if env_name == 'production':
            for var in self.sensitive_vars:
                if var in env_vars:
                    value = env_vars[var]
                    # 检查是否使用了默认或不安全的值
                    if any(unsafe in value.lower() for unsafe in [
                        'change', 'default', 'test', 'demo', 'password', '123'
                    ]):
                        insecure_vars.append(f"{var}: 使用了不安全的默认值")
        
        return insecure_vars
    
    def validate_zeromq_consistency(self, all_env_vars: Dict[str, Dict[str, str]]) -> List[str]:
        """验证ZeroMQ配置一致性"""
        inconsistencies = []
        
        # 检查主题名称一致性
        for topic_var in ['ZEROMQ_SUB_TOPIC', 'ZEROMQ_PUB_TOPIC']:
            values = set()
            for env_name, env_vars in all_env_vars.items():
                if topic_var in env_vars:
                    values.add(env_vars[topic_var])
            
            if len(values) > 1:
                inconsistencies.append(f"{topic_var} 在不同环境中不一致: {values}")
        
        return inconsistencies
    
    def validate_port_consistency(self, all_env_vars: Dict[str, Dict[str, str]]) -> List[str]:
        """验证端口配置一致性"""
        inconsistencies = []
        
        # 检查端口配置一致性
        for port_var in ['API_PORT', 'SERVER_PORT', 'ZEROMQ_SUB_PORT', 'ZEROMQ_PUB_PORT']:
            values = set()
            for env_name, env_vars in all_env_vars.items():
                if port_var in env_vars:
                    values.add(env_vars[port_var])
            
            if len(values) > 1:
                inconsistencies.append(f"{port_var} 在不同环境中不一致: {values}")
        
        return inconsistencies
    
    def run_validation(self) -> bool:
        """运行完整的验证"""
        print("🔍 开始验证环境配置文件...\n")
        
        all_env_vars = {}
        validation_passed = True
        
        # 加载所有环境文件
        for env_name, file_path in self.env_files.items():
            print(f"📁 验证 {env_name} 环境配置: {file_path}")
            
            if not file_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                validation_passed = False
                continue
            
            env_vars = self.load_env_file(file_path)
            all_env_vars[env_name] = env_vars
            
            # 验证必需变量
            missing_vars = self.validate_required_vars(env_name, env_vars)
            if missing_vars:
                print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
                validation_passed = False
            
            # 验证期望值
            inconsistent_vars = self.validate_expected_values(env_name, env_vars)
            if inconsistent_vars:
                print(f"⚠️  配置值不一致:")
                for var in inconsistent_vars:
                    print(f"   - {var}")
                validation_passed = False
            
            # 验证敏感信息
            insecure_vars = self.validate_sensitive_vars(env_name, env_vars)
            if insecure_vars:
                print(f"🔒 敏感信息配置问题:")
                for var in insecure_vars:
                    print(f"   - {var}")
                if env_name == 'production':
                    validation_passed = False
            
            if not missing_vars and not inconsistent_vars and not insecure_vars:
                print(f"✅ {env_name} 环境配置验证通过")
            
            print()
        
        # 跨环境一致性检查
        print("🔄 检查跨环境配置一致性...")
        
        zeromq_issues = self.validate_zeromq_consistency(all_env_vars)
        if zeromq_issues:
            print("❌ ZeroMQ配置不一致:")
            for issue in zeromq_issues:
                print(f"   - {issue}")
            validation_passed = False
        
        port_issues = self.validate_port_consistency(all_env_vars)
        if port_issues:
            print("❌ 端口配置不一致:")
            for issue in port_issues:
                print(f"   - {issue}")
            validation_passed = False
        
        if not zeromq_issues and not port_issues:
            print("✅ 跨环境配置一致性验证通过")
        
        print("\n" + "="*50)
        if validation_passed:
            print("🎉 所有环境配置验证通过！")
        else:
            print("❌ 环境配置验证失败，请修复上述问题")
        
        return validation_passed

def main():
    """主函数"""
    validator = EnvConfigValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()