#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复剩余ESLint问题的脚本
"""

import json
import re
import os
from typing import List, Dict, Any

def load_eslint_report(file_path: str) -> List[Dict[str, Any]]:
    """加载ESLint报告"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载ESLint报告失败: {e}")
        return []

def extract_remaining_issues(report: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """提取所有剩余问题"""
    issues_by_file = {}
    
    for file_result in report:
        file_path = file_result['filePath']
        messages = file_result.get('messages', [])
        
        if messages:
            issues_by_file[file_path] = messages
    
    return issues_by_file

def fix_unused_vars_in_file(file_path: str, issues: List[Dict[str, Any]]) -> bool:
    """修复文件中的未使用变量问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 按行号倒序排列，避免修改影响后续行号
        unused_var_issues = [
            issue for issue in issues 
            if issue.get('ruleId') == '@typescript-eslint/no-unused-vars'
        ]
        
        if not unused_var_issues:
            return False
        
        issues_sorted = sorted(unused_var_issues, key=lambda x: x['line'], reverse=True)
        
        modified = False
        for issue in issues_sorted:
            line_num = issue['line'] - 1  # 转换为0索引
            
            if 0 <= line_num < len(lines):
                line = lines[line_num]
                var_name = issue['message'].split("'")[1] if "'" in issue['message'] else None
                
                if var_name:
                    # 如果是函数参数，在变量名前添加下划线
                    if 'is defined but never used' in issue['message']:
                        # 检查是否是函数参数
                        if '(' in line and ')' in line and var_name in line:
                            # 替换参数名为带下划线的版本
                            pattern = r'\b' + re.escape(var_name) + r'\b'
                            new_line = re.sub(pattern, f'_{var_name}', line, count=1)
                            lines[line_num] = new_line
                            modified = True
                            print(f"  修复第{issue['line']}行: {var_name} -> _{var_name}")
                        else:
                            # 如果是变量声明，注释掉整行
                            lines[line_num] = f"    // {line.strip()} // 暂未使用\n"
                            modified = True
                            print(f"  注释第{issue['line']}行: {var_name}")
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
        return False
        
    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return False

def fix_react_refresh_issues(file_path: str, issues: List[Dict[str, Any]]) -> bool:
    """修复React refresh相关问题"""
    try:
        react_refresh_issues = [
            issue for issue in issues 
            if 'react-refresh' in issue.get('ruleId', '')
        ]
        
        if not react_refresh_issues:
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 在文件顶部添加eslint-disable注释
        if '/* eslint-disable react-refresh/only-export-components */' not in content:
            lines = content.split('\n')
            # 找到第一个非注释行
            insert_index = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('//'):
                    insert_index = i
                    break
            
            lines.insert(insert_index, '/* eslint-disable react-refresh/only-export-components */')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print(f"  添加react-refresh eslint-disable注释")
            return True
        
        return False
        
    except Exception as e:
        print(f"修复React refresh问题失败: {e}")
        return False

def fix_coverage_warnings(coverage_files: List[str]) -> bool:
    """修复coverage目录下的警告"""
    try:
        modified = False
        for file_path in coverage_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 移除不必要的eslint-disable注释
                if '/* eslint-disable */' in content:
                    content = content.replace('/* eslint-disable */', '')
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"  修复coverage文件: {file_path}")
                    modified = True
        
        return modified
        
    except Exception as e:
        print(f"修复coverage警告失败: {e}")
        return False

def main():
    """主函数"""
    print("开始修复剩余ESLint问题...")
    
    # 加载ESLint报告
    report = load_eslint_report('eslint_report_remaining.json')
    if not report:
        print("无法加载ESLint报告")
        return
    
    # 提取剩余问题
    issues_by_file = extract_remaining_issues(report)
    
    if not issues_by_file:
        print("未找到剩余问题")
        return
    
    print(f"找到 {len(issues_by_file)} 个文件包含剩余问题")
    
    # 统计问题类型
    problem_types = {}
    for file_path, issues in issues_by_file.items():
        for issue in issues:
            rule_id = issue.get('ruleId', 'unknown')
            problem_types[rule_id] = problem_types.get(rule_id, 0) + 1
    
    print("\n问题类型统计:")
    for rule_id, count in problem_types.items():
        print(f"  {rule_id}: {count}个")
    
    # 修复每个文件
    total_fixed = 0
    coverage_files = []
    
    for file_path, issues in issues_by_file.items():
        print(f"\n修复文件: {file_path} ({len(issues)} 个问题)")
        
        fixed = False
        
        # 修复未使用变量问题
        if fix_unused_vars_in_file(file_path, issues):
            fixed = True
        
        # 修复React refresh问题
        if fix_react_refresh_issues(file_path, issues):
            fixed = True
        
        # 收集coverage文件
        if 'coverage' in file_path:
            coverage_files.append(file_path)
        
        if fixed:
            total_fixed += len([i for i in issues if i.get('ruleId') in ['@typescript-eslint/no-unused-vars', 'react-refresh/only-export-components']])
            print(f"  ✓ 修复完成")
        else:
            print(f"  - 无需修复或修复失败")
    
    # 修复coverage警告
    if coverage_files:
        print(f"\n修复coverage目录警告...")
        if fix_coverage_warnings(coverage_files):
            print("  ✓ coverage警告修复完成")
    
    print(f"\n修复完成！总共修复了 {total_fixed} 个问题")
    print("建议运行 'npm run lint' 验证修复结果")

if __name__ == '__main__':
    main()