#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略优化模组语法检查工具
NeuroTrade Nexus (NTN) - Syntax Checker

功能：
1. 检查所有Python文件的语法错误
2. 验证import语句的正确性
3. 检查函数和类定义的完整性
4. 生成详细的检查报告
"""

import ast
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SyntaxChecker:
    """语法检查器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors = []
        self.warnings = []
        self.checked_files = []

    def find_python_files(self) -> List[Path]:
        """查找所有Python文件"""
        python_files = []

        # 排除的目录
        exclude_dirs = {
            "__pycache__",
            ".pytest_cache",
            ".git",
            ".trae",
            "node_modules",
            ".venv",
            "venv",
            "env",
            ".mypy_cache",
            ".coverage",
        }

        for root, dirs, files in os.walk(self.project_root):
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        return python_files

    def check_syntax(self, file_path: Path) -> Dict[str, Any]:
        """检查单个文件的语法"""
        result = {
            "file": str(file_path.relative_to(self.project_root)),
            "status": "ok",
            "errors": [],
            "warnings": [],
            "imports": [],
            "functions": [],
            "classes": [],
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查语法
            try:
                tree = ast.parse(content, filename=str(file_path))
                result["status"] = "ok"

                # 分析AST
                self._analyze_ast(tree, result)

            except SyntaxError as e:
                result["status"] = "syntax_error"
                result["errors"].append(
                    {
                        "type": "SyntaxError",
                        "message": str(e),
                        "line": e.lineno,
                        "column": e.offset,
                        "text": e.text.strip() if e.text else "",
                    }
                )

            except Exception as e:
                result["status"] = "parse_error"
                result["errors"].append(
                    {
                        "type": type(e).__name__,
                        "message": str(e),
                        "line": None,
                        "column": None,
                        "text": "",
                    }
                )

        except Exception as e:
            result["status"] = "file_error"
            result["errors"].append(
                {
                    "type": "FileError",
                    "message": f"无法读取文件: {e}",
                    "line": None,
                    "column": None,
                    "text": "",
                }
            )

        return result

    def _analyze_ast(self, tree: ast.AST, result: Dict[str, Any]):
        """分析AST树"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(
                        {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )

            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    result["imports"].append(
                        {
                            "type": "from_import",
                            "module": node.module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )

            elif isinstance(node, ast.FunctionDef):
                result["functions"].append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "is_async": False,
                    }
                )

            elif isinstance(node, ast.AsyncFunctionDef):
                result["functions"].append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "is_async": True,
                    }
                )

            elif isinstance(node, ast.ClassDef):
                result["classes"].append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [self._get_name(base) for base in node.bases],
                        "methods": [],
                    }
                )

                # 获取类方法
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        result["classes"][-1]["methods"].append(
                            {
                                "name": item.name,
                                "line": item.lineno,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                            }
                        )

    def _get_name(self, node: ast.AST) -> str:
        """获取AST节点的名称"""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)

    def check_imports(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查import语句"""
        import_errors = []

        for imp in result["imports"]:
            try:
                if imp["type"] == "import":
                    # 尝试导入模块
                    __import__(imp["module"])
                elif imp["type"] == "from_import":
                    if imp["module"]:
                        module = __import__(imp["module"], fromlist=[imp["name"]])
                        if not hasattr(module, imp["name"]):
                            import_errors.append(
                                {
                                    "type": "ImportError",
                                    "message": f"模块 {imp['module']} 中没有 {imp['name']}",
                                    "line": imp["line"],
                                    "module": imp["module"],
                                    "name": imp["name"],
                                }
                            )
            except ImportError as e:
                import_errors.append(
                    {
                        "type": "ImportError",
                        "message": str(e),
                        "line": imp["line"],
                        "module": imp.get("module", ""),
                        "name": imp.get("name", ""),
                    }
                )
            except Exception as e:
                import_errors.append(
                    {
                        "type": "UnknownImportError",
                        "message": str(e),
                        "line": imp["line"],
                        "module": imp.get("module", ""),
                        "name": imp.get("name", ""),
                    }
                )

        return import_errors

    def run_check(self) -> Dict[str, Any]:
        """运行完整检查"""
        print("开始语法检查...")

        python_files = self.find_python_files()
        print(f"找到 {len(python_files)} 个Python文件")

        results = []
        total_errors = 0
        total_warnings = 0

        for file_path in python_files:
            print(f"检查: {file_path.relative_to(self.project_root)}")

            result = self.check_syntax(file_path)

            # 检查import语句（仅对语法正确的文件）
            if result["status"] == "ok":
                import_errors = self.check_imports(result)
                result["import_errors"] = import_errors
                result["errors"].extend(import_errors)

            results.append(result)
            total_errors += len(result["errors"])
            total_warnings += len(result["warnings"])

            if result["errors"]:
                print(f"  ❌ {len(result['errors'])} 个错误")
            else:
                print(f"  ✅ 语法正确")

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "summary": {
                "total_files": len(python_files),
                "files_with_errors": len([r for r in results if r["errors"]]),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
            },
            "files": results,
        }

        return report

    def save_report(
        self, report: Dict[str, Any], output_file: str = "syntax_check_report.json"
    ):
        """保存检查报告"""
        output_path = self.project_root / output_file

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存到: {output_path}")

    def print_summary(self, report: Dict[str, Any]):
        """打印检查摘要"""
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("语法检查报告摘要")
        print("=" * 60)
        print(f"检查时间: {report['timestamp']}")
        print(f"项目路径: {report['project_root']}")
        print(f"总文件数: {summary['total_files']}")
        print(f"有错误的文件: {summary['files_with_errors']}")
        print(f"总错误数: {summary['total_errors']}")
        print(f"总警告数: {summary['total_warnings']}")

        if summary["total_errors"] == 0:
            print("\n🎉 所有文件语法检查通过！")
        else:
            print("\n❌ 发现语法错误，请查看详细报告")

            # 显示错误文件
            print("\n错误文件列表:")
            for file_result in report["files"]:
                if file_result["errors"]:
                    print(f"  📄 {file_result['file']}:")
                    for error in file_result["errors"]:
                        line_info = f"第{error['line']}行" if error["line"] else "未知位置"
                        print(
                            f"    ❌ {error['type']}: {error['message']} ({line_info})"
                        )


def main():
    """主函数"""
    project_root = os.getcwd()

    checker = SyntaxChecker(project_root)
    report = checker.run_check()

    checker.print_summary(report)
    checker.save_report(report)

    # 返回错误代码
    return 1 if report["summary"]["total_errors"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
