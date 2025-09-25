#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复代码中的语法错误和格式问题
"""

import os
import re


def fix_f_string_errors(content):
    """修复f-string语法错误"""
    # 修复被错误分割的f-string
    # 模式1: f"...{variable_name}" + "continuation"
    pattern1 = r'(f"[^"]*\{[^}]*)"\n\s*"([^"]*\}[^"]*")'
    content = re.sub(pattern1, r"\1\2", content, flags=re.MULTILINE)

    # 模式2: logger.info(f"...{var}" + "continuation")
    pattern2 = r'(logger\.\w+\(f"[^"]*\{[^}]*)"\n\s*"([^"]*\}[^"]*")'
    content = re.sub(pattern2, r"\1\2", content, flags=re.MULTILINE)

    return content


def fix_blank_lines(content):
    """修复空行问题"""
    lines = content.split("\n")
    fixed_lines = []

    for i, line in enumerate(lines):
        # 检查是否是类或函数定义
        if re.match(r"^(class |def |async def )", line.strip()):
            # 确保前面有两个空行（除非是文件开头）
            if i > 0 and fixed_lines:
                # 移除末尾的空行
                while fixed_lines and fixed_lines[-1].strip() == "":
                    fixed_lines.pop()
                # 添加两个空行
                fixed_lines.extend(["", ""])

        fixed_lines.append(line)

    # 移除连续的多个空行（超过2个）
    result_lines = []
    empty_count = 0

    for line in fixed_lines:
        if line.strip() == "":
            empty_count += 1
            if empty_count <= 2:
                result_lines.append(line)
        else:
            empty_count = 0
            result_lines.append(line)

    return "\n".join(result_lines)


def fix_undefined_names(content):
    """修复未定义的名称"""
    # 添加RedisManager导入
    if (
        "RedisManager" in content
        and "from ..core.redis_manager import RedisManager" not in content
    ):
        # 找到导入部分
        lines = content.split("\n")
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("from ") or line.strip().startswith("import "):
                import_end = i

        # 在导入部分添加RedisManager
        lines.insert(import_end + 1, "from ..core.redis_manager import RedisManager")
        content = "\n".join(lines)

    return content


def fix_line_continuation(content):
    """修复行继续缩进问题"""
    lines = content.split("\n")
    fixed_lines = []

    for i, line in enumerate(lines):
        # 检查是否是续行
        if (
            i > 0
            and line.strip()
            and not line[0].isspace()
            and lines[i - 1].rstrip().endswith((",", "(", "[", "{"))
        ):
            # 添加适当的缩进
            prev_line = lines[i - 1]
            indent = len(prev_line) - len(prev_line.lstrip())
            line = " " * (indent + 4) + line.strip()

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_file(file_path):
    """修复单个文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 应用各种修复
        content = fix_f_string_errors(content)
        content = fix_undefined_names(content)
        content = fix_blank_lines(content)
        content = fix_line_continuation(content)

        # 确保文件以换行符结尾
        if not content.endswith("\n"):
            content += "\n"

        # 只有在内容发生变化时才写入
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"已修复: {file_path}")
            return True
        else:
            print(f"无需修复: {file_path}")
            return False

    except Exception as e:
        print(f"修复文件失败 {file_path}: {e}")
        return False


def main():
    """主函数"""
    api_factory_dir = "api_factory"

    if not os.path.exists(api_factory_dir):
        print(f"目录不存在: {api_factory_dir}")
        return

    fixed_count = 0

    # 遍历所有Python文件
    for root, dirs, files in os.walk(api_factory_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if fix_file(file_path):
                    fixed_count += 1

    print(f"\n修复完成! 共修复了 {fixed_count} 个文件")
    print("请重新运行flake8检查验证修复结果")


if __name__ == "__main__":
    main()
