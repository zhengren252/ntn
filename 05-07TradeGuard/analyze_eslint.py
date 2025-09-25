import os
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESLint报告分析脚本
用于解析eslint_report.json并按规则分类统计问题
"""

import json
from collections import defaultdict, Counter
import sys

def analyze_eslint_report(json_file_path):
    """分析ESLint报告并生成统计信息"""
    try:
        # 尝试不同的编码格式
        encodings = ['utf-8', 'utf-16', 'utf-8-sig', 'latin-1']
        report_data = None
        
        for encoding in encodings:
            try:
                with open(json_file_path, 'r', encoding=encoding) as f:
                    report_data = json.load(f)
                print(f"成功使用 {encoding} 编码读取文件")
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        
        if report_data is None:
            print("无法读取JSON文件，尝试所有编码格式都失败")
            return None
        
        # 统计变量
        total_errors = 0
        total_warnings = 0
        rule_counts = Counter()
        file_issues = defaultdict(list)
        severity_counts = {1: 0, 2: 0}  # 1=warning, 2=error
        
        print("=" * 80)
        print("ESLint 问题分析报告")
        print("=" * 80)
        
        # 遍历所有文件
        for file_info in report_data:
            file_path = file_info['filePath']
            messages = file_info['messages']
            error_count = file_info['errorCount']
            warning_count = file_info['warningCount']
            
            total_errors += error_count
            total_warnings += warning_count
            
            # 如果文件有问题，记录详细信息
            if messages:
                print(f"\n文件: {file_path}")
                print(f"  错误数: {error_count}, 警告数: {warning_count}")
                
                for msg in messages:
                    rule_id = msg.get('ruleId', 'unknown')
                    severity = msg.get('severity', 0)
                    line = msg.get('line', 0)
                    message = msg.get('message', '')
                    
                    rule_counts[rule_id] += 1
                    severity_counts[severity] += 1
                    
                    file_issues[file_path].append({
                        'rule': rule_id,
                        'severity': severity,
                        'line': line,
                        'message': message
                    })
                    
                    print(f"    行 {line}: [{rule_id}] {message}")
        
        # 总体统计
        print("\n" + "=" * 80)
        print("总体统计")
        print("=" * 80)
        print(f"总错误数: {total_errors}")
        print(f"总警告数: {total_warnings}")
        print(f"总问题数: {total_errors + total_warnings}")
        print(f"受影响文件数: {len([f for f in report_data if f['messages']])}")
        
        # 按规则分类统计
        print("\n" + "=" * 80)
        print("按规则分类统计 (Top 10)")
        print("=" * 80)
        for rule, count in rule_counts.most_common(10):
            print(f"{rule}: {count} 个问题")
        
        # 按严重程度统计
        print("\n" + "=" * 80)
        print("按严重程度统计")
        print("=" * 80)
        print(f"错误 (severity=2): {severity_counts[2]}")
        print(f"警告 (severity=1): {severity_counts[1]}")
        
        # 重点关注的规则
        priority_rules = [
            '@typescript-eslint/no-explicit-any',
            'no-unused-vars',
            '@typescript-eslint/no-unused-vars',
            'complexity',
            'no-shadow'
        ]
        
        print("\n" + "=" * 80)
        print("重点修复规则统计")
        print("=" * 80)
        for rule in priority_rules:
            count = rule_counts.get(rule, 0)
            if count > 0:
                print(f"{rule}: {count} 个问题")
        
        # 生成修复建议
        print("\n" + "=" * 80)
        print("修复建议")
        print("=" * 80)
        
        if rule_counts.get('@typescript-eslint/no-explicit-any', 0) > 0:
            print(f"1. 修复 @typescript-eslint/no-explicit-any ({rule_counts['@typescript-eslint/no-explicit-any']} 个)")
            print("   - 从 src/lib/types.ts 中引用具体类型")
            print("   - 避免使用 any 类型")
        
        if rule_counts.get('no-unused-vars', 0) > 0 or rule_counts.get('@typescript-eslint/no-unused-vars', 0) > 0:
            unused_count = rule_counts.get('no-unused-vars', 0) + rule_counts.get('@typescript-eslint/no-unused-vars', 0)
            print(f"\n2. 修复未使用变量 ({unused_count} 个)")
            print("   - 删除未使用的变量和导入")
            print("   - 使用下划线前缀标记故意未使用的参数")
        
        return {
            'total_issues': total_errors + total_warnings,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'rule_counts': dict(rule_counts),
            'affected_files': len([f for f in report_data if f['messages']])
        }
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

if __name__ == "__main__":
    json_file = "eslint_report.json"
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    result = analyze_eslint_report(json_file)
    if result:
        print(f"\n分析完成! 共发现 {result['total_issues']} 个问题")