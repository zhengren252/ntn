#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复 @typescript-eslint/no-unused-vars 问题
"""

import json
import re
import os
from typing import List, Dict, Any

def load_eslint_report(json_file_path: str) -> List[Dict[str, Any]]:
    """加载ESLint报告"""
    try:
        encodings = ['utf-8', 'utf-16', 'utf-8-sig', 'latin-1']
        for encoding in encodings:
            try:
                with open(json_file_path, 'r', encoding=encoding) as f:
                    return json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        print("无法读取JSON文件")
        return []
    except Exception as e:
        print(f"加载ESLint报告失败: {e}")
        return []

def get_unused_vars_issues(report_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """提取所有no-unused-vars问题"""
    unused_vars_issues = []
    
    for file_data in report_data:
        file_path = file_data.get('filePath', '')
        messages = file_data.get('messages', [])
        
        for message in messages:
            if message.get('ruleId') == '@typescript-eslint/no-unused-vars':
                unused_vars_issues.append({
                    'filePath': file_path,
                    'line': message.get('line'),
                    'column': message.get('column'),
                    'message': message.get('message'),
                    'severity': message.get('severity')
                })
    
    return unused_vars_issues

def fix_unused_variable(file_path: str, line_number: int, message: str) -> bool:
    """修复单个未使用变量问题"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_number > len(lines):
            print(f"行号 {line_number} 超出文件范围")
            return False
        
        target_line = lines[line_number - 1]  # 转换为0索引
        original_line = target_line
        
        # 分析消息类型并修复
        if "is defined but never used" in message:
            # 提取变量名
            var_match = re.search(r"'([^']+)' is defined but never used", message)
            if var_match:
                var_name = var_match.group(1)
                
                # 检查是否是导入语句
                if 'import' in target_line:
                    # 处理导入语句
                    if f'import {var_name}' in target_line:
                        # 移除整个导入行
                        lines[line_number - 1] = ''
                    elif f', {var_name}' in target_line:
                        # 从导入列表中移除变量
                        target_line = target_line.replace(f', {var_name}', '')
                        lines[line_number - 1] = target_line
                    elif f'{var_name},' in target_line:
                        # 从导入列表中移除变量
                        target_line = target_line.replace(f'{var_name}, ', '')
                        lines[line_number - 1] = target_line
                    elif f'{{ {var_name} }}' in target_line:
                        # 移除整个导入行
                        lines[line_number - 1] = ''
                
                # 检查是否是函数参数
                elif 'function' in target_line or '=>' in target_line or 'const' in target_line:
                    # 对于函数参数，添加下划线前缀
                    if f'{var_name}:' in target_line or f'{var_name},' in target_line or f'{var_name})' in target_line:
                        target_line = target_line.replace(var_name, f'_{var_name}')
                        lines[line_number - 1] = target_line
                
                # 检查是否是变量声明
                elif 'const' in target_line or 'let' in target_line or 'var' in target_line:
                    # 注释掉整行
                    lines[line_number - 1] = f'    // {target_line.strip()}\n'
        
        # 如果行内容发生了变化，写回文件
        if lines[line_number - 1] != original_line:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"修复: {file_path}:{line_number} - {message}")
            return True
        else:
            print(f"跳过: {file_path}:{line_number} - 无法自动修复")
            return False
            
    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("开始修复 @typescript-eslint/no-unused-vars 问题...")
    
    # 加载ESLint报告
    report_data = load_eslint_report('eslint_report.json')
    if not report_data:
        print("无法加载ESLint报告")
        return
    
    # 获取所有未使用变量问题
    unused_vars_issues = get_unused_vars_issues(report_data)
    print(f"发现 {len(unused_vars_issues)} 个未使用变量问题")
    
    if not unused_vars_issues:
        print("没有发现未使用变量问题")
        return
    
    # 按文件分组
    files_to_fix = {}
    for issue in unused_vars_issues:
        file_path = issue['filePath']
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(issue)
    
    # 修复每个文件
    total_fixed = 0
    for file_path, issues in files_to_fix.items():
        print(f"\n修复文件: {file_path}")
        
        # 按行号倒序排序，避免修改影响后续行号
        issues.sort(key=lambda x: x['line'], reverse=True)
        
        for issue in issues:
            if fix_unused_variable(file_path, issue['line'], issue['message']):
                total_fixed += 1
    
    print(f"\n修复完成! 总共修复了 {total_fixed} 个问题")
    print("建议运行 'npm run lint' 验证修复结果")

if __name__ == '__main__':
    main()