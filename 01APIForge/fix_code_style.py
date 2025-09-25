#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码风格修复脚本 - 第二轮修复
修复剩余的flake8问题
"""

import os
import re
from pathlib import Path


def fix_specific_issues(file_path):
    """修复特定的代码风格问题"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    lines = content.split("\n")
    fixed_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # 修复E303: 过多空行 (超过2个连续空行)
        if line.strip() == "":
            blank_count = 1
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                blank_count += 1
                j += 1

            # 限制连续空行不超过2个
            if blank_count > 2:
                fixed_lines.extend(["", ""])
                i = j
                continue

        # 修复E302: 类/函数定义前需要2个空行
        if line.strip().startswith("class ") or (
            line.strip().startswith("def ") and not line.strip().startswith("def _")
        ):
            # 检查前面的空行数量
            blank_lines = 0
            k = len(fixed_lines) - 1
            while k >= 0 and fixed_lines[k].strip() == "":
                blank_lines += 1
                k -= 1

            # 如果不是文件开头且前面不是装饰器，需要确保有2个空行
            if k >= 0 and not fixed_lines[k].strip().startswith("@"):
                # 移除现有的空行
                while fixed_lines and fixed_lines[-1].strip() == "":
                    fixed_lines.pop()
                # 添加2个空行
                fixed_lines.extend(["", ""])

        # 修复E304: 函数装饰器后不应有空行
        if line.strip().startswith("@"):
            fixed_lines.append(line)
            # 跳过装饰器后的空行
            i += 1
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            continue

        fixed_lines.append(line)
        i += 1

    content = "\n".join(fixed_lines)

    # 修复长行问题 (E501) - 简单的字符串分割
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        if len(line) > 120 and '"' in line:
            # 尝试分割长字符串
            if "logger." in line and '"' in line:
                # 分割日志字符串
                indent = len(line) - len(line.lstrip())
                prefix = line[: line.find('"')]
                suffix = line[line.rfind('"') + 1 :]
                string_part = line[line.find('"') : line.rfind('"') + 1]

                if len(string_part) > 60:
                    # 分割字符串
                    mid = len(string_part) // 2
                    part1 = string_part[:mid] + '"'
                    part2 = '"' + string_part[mid + 1 :]

                    fixed_lines.append(prefix + part1)
                    fixed_lines.append(" " * (indent + 4) + part2 + suffix)
                    continue

        fixed_lines.append(line)

    content = "\n".join(fixed_lines)

    # 修复未使用的导入
    content = remove_unused_imports_from_content(content, file_path)

    # 修复参数等号周围的空格 (E251)
    content = re.sub(r"(\w+)\s*=\s*(\w+)\s*=", r"\1=\2=", content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"已修复: {file_path}")
        return True

    return False


def remove_unused_imports_from_content(content, file_path):
    """从内容中移除未使用的导入"""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        # 检查特定的未使用导入
        if "import asyncio" in line and "asyncio." not in content.replace(line, ""):
            print(f"移除未使用的导入: asyncio from {file_path}")
            continue
        elif "RedisKeys" in line and "RedisKeys." not in content.replace(line, ""):
            print(f"移除未使用的导入: RedisKeys from {file_path}")
            continue

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_bare_except(file_path):
    """修复裸露的except语句"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 将 except: 替换为 except Exception:
    content = re.sub(r"except:\s*$", "except Exception:", content, flags=re.MULTILINE)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"修复裸露except: {file_path}")
        return True

    return False


def main():
    """主函数"""
    api_factory_dir = Path("api_factory")

    if not api_factory_dir.exists():
        print("错误: api_factory目录不存在")
        return

    # 获取所有Python文件
    python_files = list(api_factory_dir.rglob("*.py"))

    print(f"找到 {len(python_files)} 个Python文件")

    fixed_count = 0

    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue

        print(f"\n处理文件: {file_path}")

        # 修复特定问题
        if fix_specific_issues(file_path):
            fixed_count += 1

        # 修复裸露except
        if fix_bare_except(file_path):
            fixed_count += 1

    print(f"\n修复完成! 共修复了 {fixed_count} 个文件")
    print("请重新运行flake8检查验证修复结果")


if __name__ == "__main__":
    main()
