#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradeGuard语法错误修复脚本
用于修复Docker化部署测试中发现的语法错误
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

class SyntaxErrorFixer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors_found = []
        self.fixes_applied = []
        
    def check_python_syntax(self) -> List[Dict[str, Any]]:
        """检查Python文件的语法错误"""
        python_files = list(self.project_root.rglob("*.py"))
        syntax_errors = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, str(py_file), 'exec')
            except SyntaxError as e:
                syntax_errors.append({
                    'file': str(py_file),
                    'line': e.lineno,
                    'error': str(e),
                    'type': 'syntax_error'
                })
            except Exception as e:
                syntax_errors.append({
                    'file': str(py_file),
                    'line': 0,
                    'error': str(e),
                    'type': 'other_error'
                })
                
        return syntax_errors
    
    def check_javascript_syntax(self) -> List[Dict[str, Any]]:
        """检查JavaScript/TypeScript文件的语法错误"""
        js_errors = []
        
        # 运行ESLint检查
        try:
            result = subprocess.run(
                ['npm', 'run', 'lint'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                # 解析ESLint输出
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'error' in line.lower() or 'warning' in line.lower():
                        js_errors.append({
                            'file': 'multiple',
                            'line': 0,
                            'error': line.strip(),
                            'type': 'eslint_error'
                        })
                        
        except subprocess.TimeoutExpired:
            js_errors.append({
                'file': 'eslint',
                'line': 0,
                'error': 'ESLint检查超时',
                'type': 'timeout_error'
            })
        except Exception as e:
            js_errors.append({
                'file': 'eslint',
                'line': 0,
                'error': f'ESLint检查失败: {str(e)}',
                'type': 'eslint_failure'
            })
            
        return js_errors
    
    def fix_common_syntax_errors(self) -> List[str]:
        """修复常见的语法错误"""
        fixes = []
        
        # 修复Python文件中的常见问题
        python_files = list(self.project_root.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # 修复缺少的导入
                if 'json' in content and 'import json' not in content:
                    content = 'import json\n' + content
                    fixes.append(f"添加json导入到 {py_file}")
                
                if 'os' in content and 'import os' not in content:
                    content = 'import os\n' + content
                    fixes.append(f"添加os导入到 {py_file}")
                
                # 修复缩进问题
                lines = content.split('\n')
                fixed_lines = []
                for line in lines:
                    # 将制表符转换为空格
                    if '\t' in line:
                        line = line.replace('\t', '    ')
                        fixes.append(f"修复制表符缩进在 {py_file}")
                    fixed_lines.append(line)
                
                content = '\n'.join(fixed_lines)
                
                # 如果内容有变化，写回文件
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                fixes.append(f"修复 {py_file} 时出错: {str(e)}")
        
        return fixes
    
    def run_fix(self) -> Dict[str, Any]:
        """运行完整的语法错误修复流程"""
        print("开始语法错误检查和修复...")
        
        # 检查Python语法错误
        print("检查Python语法错误...")
        python_errors = self.check_python_syntax()
        
        # 检查JavaScript语法错误
        print("检查JavaScript/TypeScript语法错误...")
        js_errors = self.check_javascript_syntax()
        
        # 应用常见修复
        print("应用常见语法错误修复...")
        fixes = self.fix_common_syntax_errors()
        
        # 再次检查Python语法
        print("重新检查Python语法...")
        python_errors_after = self.check_python_syntax()
        
        result = {
            'python_errors_before': len(python_errors),
            'python_errors_after': len(python_errors_after),
            'js_errors': len(js_errors),
            'fixes_applied': len(fixes),
            'details': {
                'python_errors_before': python_errors,
                'python_errors_after': python_errors_after,
                'js_errors': js_errors,
                'fixes': fixes
            }
        }
        
        return result

def main():
    """主函数"""
    project_root = os.getcwd()
    print(f"在项目根目录运行语法错误修复: {project_root}")
    
    fixer = SyntaxErrorFixer(project_root)
    result = fixer.run_fix()
    
    # 输出结果
    print("\n=== 语法错误修复结果 ===")
    print(f"修复前Python语法错误: {result['python_errors_before']}")
    print(f"修复后Python语法错误: {result['python_errors_after']}")
    print(f"JavaScript/TypeScript错误: {result['js_errors']}")
    print(f"应用的修复: {result['fixes_applied']}")
    
    if result['fixes_applied'] > 0:
        print("\n应用的修复:")
        for fix in result['details']['fixes']:
            print(f"  - {fix}")
    
    if result['python_errors_after'] > 0:
        print("\n剩余的Python语法错误:")
        for error in result['details']['python_errors_after']:
            print(f"  - {error['file']}:{error['line']} - {error['error']}")
    
    # 保存详细结果到文件
    with open('syntax_fix_report.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细报告已保存到: syntax_fix_report.json")
    
    # 如果还有语法错误，返回非零退出码
    if result['python_errors_after'] > 0:
        print("\n警告: 仍有Python语法错误需要手动修复")
        return 1
    
    print("\n语法错误修复完成!")
    return 0

if __name__ == '__main__':
    sys.exit(main())