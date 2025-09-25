#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 @typescript-eslint/no-explicit-any 问题的脚本
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

def extract_explicit_any_issues(report: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """提取所有 @typescript-eslint/no-explicit-any 问题"""
    issues_by_file = {}
    
    for file_result in report:
        file_path = file_result['filePath']
        messages = file_result.get('messages', [])
        
        explicit_any_issues = [
            msg for msg in messages 
            if msg.get('ruleId') == '@typescript-eslint/no-explicit-any'
        ]
        
        if explicit_any_issues:
            issues_by_file[file_path] = explicit_any_issues
    
    return issues_by_file

def get_type_replacement(context: str, line_content: str) -> str:
    """根据上下文确定合适的类型替换"""
    line_lower = line_content.lower()
    
    # 常见的类型替换模式
    if 'error' in line_lower or 'exception' in line_lower:
        return 'Error'
    elif 'message' in line_lower or 'msg' in line_lower:
        return 'string'
    elif 'data' in line_lower or 'payload' in line_lower:
        return 'Record<string, unknown>'
    elif 'config' in line_lower or 'setting' in line_lower:
        return 'Record<string, unknown>'
    elif 'result' in line_lower or 'response' in line_lower:
        return 'Record<string, unknown>'
    elif 'request' in line_lower or 'req' in line_lower:
        return 'Record<string, unknown>'
    elif 'params' in line_lower or 'parameter' in line_lower:
        return 'Record<string, unknown>'
    elif 'event' in line_lower:
        return 'Event'
    elif 'callback' in line_lower or 'handler' in line_lower:
        return 'Function'
    elif 'array' in line_lower or '[]' in line_content:
        return 'unknown[]'
    else:
        return 'unknown'

def fix_explicit_any_in_file(file_path: str, issues: List[Dict[str, Any]]) -> bool:
    """修复文件中的 @typescript-eslint/no-explicit-any 问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 按行号倒序排列，避免修改影响后续行号
        issues_sorted = sorted(issues, key=lambda x: x['line'], reverse=True)
        
        modified = False
        for issue in issues_sorted:
            line_num = issue['line'] - 1  # 转换为0索引
            column = issue['column'] - 1  # 转换为0索引
            
            if 0 <= line_num < len(lines):
                line = lines[line_num]
                
                # 检查是否是 'any' 关键字
                if column < len(line) and line[column:column+3] == 'any':
                    # 获取合适的类型替换
                    replacement_type = get_type_replacement(file_path, line)
                    
                    # 替换 'any' 为合适的类型
                    new_line = line[:column] + replacement_type + line[column+3:]
                    lines[line_num] = new_line
                    modified = True
                    
                    print(f"  修复第{issue['line']}行: any -> {replacement_type}")
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
        return False
        
    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("开始修复 @typescript-eslint/no-explicit-any 问题...")
    
    # 加载ESLint报告
    report = load_eslint_report('eslint_report.json')
    if not report:
        print("无法加载ESLint报告")
        return
    
    # 提取 @typescript-eslint/no-explicit-any 问题
    issues_by_file = extract_explicit_any_issues(report)
    
    if not issues_by_file:
        print("未找到 @typescript-eslint/no-explicit-any 问题")
        return
    
    print(f"找到 {len(issues_by_file)} 个文件包含 @typescript-eslint/no-explicit-any 问题")
    
    # 修复每个文件
    total_fixed = 0
    for file_path, issues in issues_by_file.items():
        print(f"\n修复文件: {file_path} ({len(issues)} 个问题)")
        
        if fix_explicit_any_in_file(file_path, issues):
            total_fixed += len(issues)
            print(f"  ✓ 修复完成")
        else:
            print(f"  ✗ 修复失败")
    
    print(f"\n修复完成！总共修复了 {total_fixed} 个 @typescript-eslint/no-explicit-any 问题")
    print("建议运行 'npm run lint' 验证修复结果")

if __name__ == '__main__':
    main()