#!/usr/bin/env python3
"""
最终清扫：Python服务PATH配置全面审计脚本
目标：找出所有使用虚拟环境但缺少正确PATH配置的Dockerfile
"""

import os
import re
import json
from pathlib import Path

def find_all_dockerfiles(root_path):
    """找到项目中的所有Dockerfile文件"""
    dockerfiles = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file == 'Dockerfile':
                dockerfile_path = os.path.join(root, file)
                dockerfiles.append(dockerfile_path)
    return dockerfiles

def analyze_dockerfile(dockerfile_path):
    """分析Dockerfile，检查是否使用虚拟环境且缺少PATH配置"""
    try:
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(dockerfile_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except Exception as e:
            print(f"ERROR: 无法读取文件 {dockerfile_path}: {e}")
            return False, "读取错误"
    
    # 检查是否使用虚拟环境
    uses_venv = '/opt/venv' in content
    
    if not uses_venv:
        return False, "不使用虚拟环境"
    
    # 检查是否已有正确的PATH配置
    # 匹配各种可能的PATH配置格式
    path_patterns = [
        r'ENV\s+PATH[=\s]+["\']?/opt/venv/bin:\$PATH["\']?',
        r'ENV\s+PATH[=\s]+["\']?\$PATH:/opt/venv/bin["\']?',
        r'ENV\s+PATH\s*=\s*["\']?/opt/venv/bin:\$PATH["\']?',
        r'ENV\s+PATH\s*=\s*["\']?\$PATH:/opt/venv/bin["\']?'
    ]
    
    has_path_config = any(re.search(pattern, content, re.IGNORECASE) for pattern in path_patterns)
    
    if has_path_config:
        return False, "已有PATH配置"
    
    # 检查是否是多阶段构建，并确认最终阶段缺少PATH
    stages = re.findall(r'FROM\s+[^\s]+\s+AS\s+(\w+)', content, re.IGNORECASE)
    
    if stages:
        # 多阶段构建，检查最后阶段
        last_stage = stages[-1]
        # 找到最后阶段的内容
        stage_pattern = rf'FROM\s+[^\s]+\s+AS\s+{last_stage}(.*?)(?=FROM\s+|$)'
        stage_match = re.search(stage_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if stage_match:
            stage_content = stage_match.group(1)
            stage_has_path = any(re.search(pattern, stage_content, re.IGNORECASE) for pattern in path_patterns)
            if stage_has_path:
                return False, f"最终阶段 {last_stage} 已有PATH配置"
    
    return True, "缺少PATH配置"

def main():
    """主函数：执行全面审计"""
    print("🔍 开始执行最终PATH配置审计...")
    
    root_path = '.'  # 当前工作目录
    
    # 1. 找到所有Dockerfile文件
    print("📁 正在搜索所有Dockerfile文件...")
    all_dockerfiles = find_all_dockerfiles(root_path)
    print(f"   找到 {len(all_dockerfiles)} 个Dockerfile文件")
    
    # 2. 分析每个Dockerfile
    print("🔬 正在分析每个Dockerfile...")
    needs_fix = []
    analysis_results = {}
    
    for dockerfile in all_dockerfiles:
        relative_path = os.path.relpath(dockerfile, root_path)
        print(f"   分析: {relative_path}")
        
        needs_fix_flag, reason = analyze_dockerfile(dockerfile)
        analysis_results[relative_path] = {
            'needs_fix': needs_fix_flag,
            'reason': reason,
            'absolute_path': dockerfile
        }
        
        if needs_fix_flag:
            needs_fix.append(dockerfile)
            print(f"   ❌ 需要修复: {reason}")
        else:
            print(f"   ✅ 无需修复: {reason}")
    
    # 3. 生成审计报告
    print(f"\n📊 审计完成！")
    print(f"   总计检查: {len(all_dockerfiles)} 个文件")
    print(f"   需要修复: {len(needs_fix)} 个文件")
    
    if needs_fix:
        print(f"\n🚨 需要修复的文件列表:")
        for i, dockerfile in enumerate(needs_fix, 1):
            relative_path = os.path.relpath(dockerfile, root_path)
            print(f"   {i}. {relative_path}")
    else:
        print(f"\n🎉 所有文件都已正确配置PATH！")
    
    # 4. 保存详细结果到JSON文件
    with open('final_audit_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_files': len(all_dockerfiles),
            'needs_fix_count': len(needs_fix),
            'needs_fix_files': [os.path.relpath(f, root_path) for f in needs_fix],
            'detailed_results': analysis_results
        }, f, indent=2, ensure_ascii=False)
    
    # 5. 保存需要修复的文件列表
    with open('final_fix_list.txt', 'w', encoding='utf-8') as f:
        for dockerfile in needs_fix:
            f.write(f"{dockerfile}\n")
    
    print(f"\n📄 详细报告已保存到: final_audit_results.json")
    print(f"📄 修复列表已保存到: final_fix_list.txt")
    
    return len(needs_fix)

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)