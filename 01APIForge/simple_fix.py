#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单修复脚本
"""

import os
import re


def fix_file_issues(file_path):
    """修复文件中的问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 移除未使用的导入
        content = re.sub(
            r"^from typing import.*Union.*\n", "", content, flags=re.MULTILINE
        )
        content = re.sub(r"^import.*Union.*\n", "", content, flags=re.MULTILINE)

        # 修复空行问题 - 移除多余的空行
        lines = content.split("\n")
        fixed_lines = []
        empty_count = 0

        for line in lines:
            if line.strip() == "":
                empty_count += 1
                if empty_count <= 2:
                    fixed_lines.append(line)
            else:
                empty_count = 0
                fixed_lines.append(line)

        content = "\n".join(fixed_lines)

        # 确保函数和类定义前有适当的空行
        lines = content.split("\n")
        result_lines = []

        for i, line in enumerate(lines):
            if re.match(r"^\s*(def |class |async def )", line) and i > 0:
                # 检查前面的空行数量
                empty_before = 0
                j = i - 1
                while j >= 0 and lines[j].strip() == "":
                    empty_before += 1
                    j -= 1

                # 如果空行不足2个，添加空行
                if empty_before < 2 and j >= 0:
                    # 移除现有的空行
                    while result_lines and result_lines[-1].strip() == "":
                        result_lines.pop()
                    # 添加两个空行
                    result_lines.extend(["", ""])

            result_lines.append(line)

        content = "\n".join(result_lines)

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
                if fix_file_issues(file_path):
                    fixed_count += 1

    print(f"\n修复完成! 共修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
