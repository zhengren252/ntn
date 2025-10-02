#!/usr/bin/env python3
"""
系统性Dockerfile审计脚本
用于识别需要PATH配置修复的Python/uvicorn服务
"""

import os
import re
import json
from pathlib import Path

def find_all_dockerfiles(root_dir):
    """查找所有Dockerfile文件"""
    dockerfiles = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file == 'Dockerfile':
                dockerfiles.append(os.path.join(root, file))
    return dockerfiles

def is_python_service_dockerfile(dockerfile_path):
    """检查Dockerfile是否是需要虚拟环境的Python服务"""
    try:
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 查找是否使用了虚拟环境 /opt/venv
        has_venv = bool(re.search(r'/opt/venv', content, re.IGNORECASE))
        
        # 查找是否是Python服务（有requirements.txt或使用python命令）
        has_python_requirements = bool(re.search(r'requirements\.txt', content, re.IGNORECASE))
        has_python_cmd = bool(re.search(r'(?:CMD|ENTRYPOINT)\s+.*python', content, re.IGNORECASE | re.MULTILINE))
        has_uvicorn_cmd = bool(re.search(r'(?:CMD|ENTRYPOINT)\s+.*uvicorn', content, re.IGNORECASE | re.MULTILINE))
        
        return (has_venv or has_python_requirements) and (has_python_cmd or has_uvicorn_cmd)
    except Exception as e:
        print(f"错误读取文件 {dockerfile_path}: {e}")
        return False

def has_correct_path_env(dockerfile_path):
    """检查Dockerfile是否已经包含正确的PATH环境变量配置"""
    try:
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否包含PATH配置
        path_pattern = r'ENV\s+PATH\s*=\s*["\']?/opt/venv/bin:\$PATH["\']?'
        return bool(re.search(path_pattern, content, re.IGNORECASE))
    except Exception as e:
        print(f"错误读取文件 {dockerfile_path}: {e}")
        return False

def audit_dockerfiles(root_dir):
    """执行完整的Dockerfile审计"""
    print("=== 开始系统性Dockerfile审计 ===")
    
    # 1. 找到所有Dockerfile
    all_dockerfiles = find_all_dockerfiles(root_dir)
    print(f"发现 {len(all_dockerfiles)} 个Dockerfile文件:")
    for df in all_dockerfiles:
        print(f"  - {df}")
    
    print("\n=== 筛选Python服务Dockerfile ===")
    
    # 2. 筛选Python服务的Dockerfile
    python_dockerfiles = []
    for df in all_dockerfiles:
        if is_python_service_dockerfile(df):
            python_dockerfiles.append(df)
            print(f"  ✓ {df}")
    
    print(f"\n发现 {len(python_dockerfiles)} 个Python服务的Dockerfile")
    
    print("\n=== 检查PATH配置状态 ===")
    
    # 3. 检查PATH配置
    needs_fix = []
    already_configured = []
    
    for df in python_dockerfiles:
        if has_correct_path_env(df):
            already_configured.append(df)
            print(f"  ✓ 已配置: {df}")
        else:
            needs_fix.append(df)
            print(f"  ✗ 需修复: {df}")
    
    # 4. 生成修复列表
    print(f"\n=== 审计结果 ===")
    print(f"总计Dockerfile: {len(all_dockerfiles)}")
    print(f"Python服务: {len(python_dockerfiles)}")
    print(f"已正确配置: {len(already_configured)}")
    print(f"需要修复: {len(needs_fix)}")
    
    # 保存修复列表到文件
    fix_list_file = os.path.join(root_dir, 'dockerfile_fix_list.txt')
    with open(fix_list_file, 'w', encoding='utf-8') as f:
        for df in needs_fix:
            f.write(df + '\n')
    
    print(f"\n需要修复的文件列表已保存到: {fix_list_file}")
    
    # 保存详细审计结果
    audit_results = {
        'total_dockerfiles': len(all_dockerfiles),
        'python_dockerfiles': len(python_dockerfiles),
        'already_configured': already_configured,
        'needs_fix': needs_fix,
        'timestamp': str(os.path.getctime(fix_list_file))
    }
    
    audit_file = os.path.join(root_dir, 'audit_results.json')
    with open(audit_file, 'w', encoding='utf-8') as f:
        json.dump(audit_results, f, indent=2, ensure_ascii=False)
    
    print(f"详细审计结果已保存到: {audit_file}")
    
    return needs_fix

if __name__ == "__main__":
    root_directory = r"e:\NTN_Clean"
    fix_list = audit_dockerfiles(root_directory)
    
    if fix_list:
        print(f"\n🚨 发现 {len(fix_list)} 个需要修复的Dockerfile:")
        for i, df in enumerate(fix_list, 1):
            print(f"  {i}. {df}")
    else:
        print("\n✅ 所有Dockerfile都已正确配置!")