#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复剩余的no-unused-vars问题
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
    except UnicodeDecodeError:
        # 尝试其他编码
        for encoding in ['utf-16', 'utf-8-sig', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        raise Exception(f"无法读取文件 {file_path}")

def fix_unused_imports(file_path: str, unused_vars: List[str]) -> bool:
    """修复未使用的导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for var_name in unused_vars:
            # 处理导入语句中的未使用变量
            # 匹配 import { var1, var2, ... } from '...';
            import_pattern = r'import\s*\{([^}]+)\}\s*from\s*[\'"][^\'"]+[\'"];'
            
            def replace_import(match):
                imports = match.group(1)
                import_list = [imp.strip() for imp in imports.split(',')]
                
                # 移除未使用的变量
                filtered_imports = [imp for imp in import_list if imp != var_name]
                
                if not filtered_imports:
                    # 如果所有导入都被移除，注释整行
                    return f"// {match.group(0)} // 所有导入都未使用"
                elif len(filtered_imports) < len(import_list):
                    # 重新构建导入语句
                    new_imports = ', '.join(filtered_imports)
                    return match.group(0).replace(imports, new_imports)
                
                return match.group(0)
            
            content = re.sub(import_pattern, replace_import, content)
            
            # 处理单独的导入语句
            single_import_pattern = f'import\s+{re.escape(var_name)}\s+from\s+[\'"][^\'"]+[\'"];'
            content = re.sub(single_import_pattern, f'// import {var_name} from ...; // 未使用', content)
            
            # 处理函数参数中的未使用变量（添加下划线前缀）
            if not var_name.startswith('_'):
                # 匹配函数参数
                param_pattern = f'\b{re.escape(var_name)}\b(?=\s*[,)])'  
                content = re.sub(param_pattern, f'_{var_name}', content)
        
        # 只有内容发生变化时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    eslint_report_path = 'eslint_report.json'
    
    if not os.path.exists(eslint_report_path):
        print(f"ESLint报告文件不存在: {eslint_report_path}")
        return
    
    # 加载ESLint报告
    report = load_eslint_report(eslint_report_path)
    
    # 收集no-unused-vars问题
    unused_vars_by_file = {}
    
    for file_result in report:
        file_path = file_result['filePath']
        messages = file_result['messages']
        
        for message in messages:
            if message['ruleId'] == '@typescript-eslint/no-unused-vars':
                if file_path not in unused_vars_by_file:
                    unused_vars_by_file[file_path] = []
                
                # 提取变量名
                text = message['message']
                # 匹配 "'variableName' is defined but never used"
                match = re.search(r"'([^']+)' is defined but never used", text)
                if match:
                    var_name = match.group(1)
                    unused_vars_by_file[file_path].append(var_name)
    
    print(f"发现 {len(unused_vars_by_file)} 个文件包含未使用变量问题")
    
    # 修复每个文件
    fixed_files = 0
    total_fixes = 0
    
    for file_path, unused_vars in unused_vars_by_file.items():
        print(f"\n修复文件: {file_path}")
        print(f"未使用变量: {', '.join(unused_vars)}")
        
        if fix_unused_imports(file_path, unused_vars):
            fixed_files += 1
            total_fixes += len(unused_vars)
            print(f"✓ 已修复 {len(unused_vars)} 个问题")
        else:
            print("× 修复失败或无需修复")
    
    print(f"\n修复完成:")
    print(f"- 修复文件数: {fixed_files}")
    print(f"- 修复问题数: {total_fixes}")
    print(f"\n请运行 'npm run lint' 验证修复结果")

if __name__ == '__main__':
    main()