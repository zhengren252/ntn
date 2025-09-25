#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语法检查脚本
检查项目中所有Python文件的语法错误
"""

import ast
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List


def check_syntax(file_path: str) -> Dict[str, Any]:
    """
    检查单个文件的语法

    Args:
        file_path: 文件路径

    Returns:
        检查结果字典
    """
    result = {"file": file_path, "valid": True, "errors": []}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 尝试编译代码
        ast.parse(content, filename=file_path)

    except SyntaxError as e:
        result["valid"] = False
        result["errors"].append(
            {
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "column": e.offset,
            }
        )
    except Exception as e:
        result["valid"] = False
        result["errors"].append(
            {"type": type(e).__name__, "message": str(e), "line": None, "column": None}
        )

    return result


def check_imports(file_path: str) -> Dict[str, Any]:
    """
    检查导入语句

    Args:
        file_path: 文件路径

    Returns:
        检查结果字典
    """
    result = {"file": file_path, "valid": True, "errors": []}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析AST
        tree = ast.parse(content, filename=file_path)

        # 检查导入语句
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    try:
                        __import__(alias.name)
                    except ImportError as e:
                        result["valid"] = False
                        result["errors"].append(
                            {
                                "type": "ImportError",
                                "message": f"Cannot import '{alias.name}': {str(e)}",
                                "line": node.lineno,
                                "module": alias.name,
                            }
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    try:
                        module = __import__(
                            node.module, fromlist=[alias.name for alias in node.names]
                        )
                        for alias in node.names:
                            if alias.name != "*" and not hasattr(module, alias.name):
                                result["valid"] = False
                                result["errors"].append(
                                    {
                                        "type": "ImportError",
                                        "message": f"Cannot import '{alias.name}' from '{node.module}'",
                                        "line": node.lineno,
                                        "module": node.module,
                                    }
                                )
                    except ImportError as e:
                        result["valid"] = False
                        result["errors"].append(
                            {
                                "type": "ImportError",
                                "message": f"Cannot import from '{node.module}': {str(e)}",
                                "line": node.lineno,
                                "module": node.module,
                            }
                        )

    except Exception as e:
        result["valid"] = False
        result["errors"].append(
            {"type": type(e).__name__, "message": str(e), "line": None, "module": None}
        )

    return result


def find_python_files(directory: str) -> List[str]:
    """
    查找目录下所有Python文件

    Args:
        directory: 目录路径

    Returns:
        Python文件路径列表
    """
    python_files = []

    for root, dirs, files in os.walk(directory):
        # 跳过特定目录
        dirs[:] = [
            d
            for d in dirs
            if d not in [".git", "__pycache__", ".pytest_cache", "node_modules"]
        ]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    return python_files


def main():
    """
    主函数
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent

    # 将项目根目录添加到Python路径
    sys.path.insert(0, str(project_root))

    print("NeuroTrade Nexus - 策略优化模组语法检查")
    print("=" * 50)
    print(f"项目路径: {project_root}")
    print()

    # 查找所有Python文件
    python_files = find_python_files(str(project_root))
    print(f"找到 {len(python_files)} 个Python文件")
    print()

    # 语法检查
    syntax_errors = []
    import_errors = []

    for file_path in python_files:
        rel_path = os.path.relpath(file_path, project_root)

        # 检查语法
        syntax_result = check_syntax(file_path)
        if not syntax_result["valid"]:
            syntax_errors.append(syntax_result)

        # 检查导入（只有语法正确的文件才检查导入）
        if syntax_result["valid"]:
            import_result = check_imports(file_path)
            if not import_result["valid"]:
                import_errors.append(import_result)

    # 输出结果
    total_errors = len(syntax_errors) + len(import_errors)

    if total_errors == 0:
        print("✅ 所有文件语法检查通过！")
        return 0

    print(f"❌ 发现 {total_errors} 个错误")
    print()

    # 输出语法错误
    if syntax_errors:
        print("语法错误:")
        print("-" * 30)
        for error in syntax_errors:
            rel_path = os.path.relpath(error["file"], project_root)
            print(f"文件: {rel_path}")
            for err in error["errors"]:
                if err["line"]:
                    print(f"  第{err['line']}行: {err['type']} - {err['message']}")
                else:
                    print(f"  {err['type']} - {err['message']}")
            print()

    # 输出导入错误
    if import_errors:
        print("导入错误:")
        print("-" * 30)
        for error in import_errors:
            rel_path = os.path.relpath(error["file"], project_root)
            print(f"文件: {rel_path}")
            for err in error["errors"]:
                if err["line"]:
                    print(f"  第{err['line']}行: {err['type']} - {err['message']}")
                else:
                    print(f"  {err['type']} - {err['message']}")
            print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
