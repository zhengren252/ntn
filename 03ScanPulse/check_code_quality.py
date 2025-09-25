#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码质量检查脚本
"""

import subprocess
import sys
import os


def run_flake8():
    """运行flake8代码质量检查"""
    print("运行flake8代码质量检查...")
    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "flake8",
                "scanner/",
                "--max-line-length=120",
                "--ignore=E501,W503,F401",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"运行flake8失败: {e}")
        return False


def run_mypy():
    """运行mypy类型检查"""
    print("\n运行mypy类型检查...")
    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "mypy",
                "scanner/",
                "--ignore-missing-imports",
                "--no-strict-optional",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"运行mypy失败: {e}")
        return False


def main():
    """主函数"""
    print("ScanPulse 代码质量检查")
    print("=" * 50)

    # 运行flake8
    flake8_ok = run_flake8()

    # 运行mypy（可选）
    # mypy_ok = run_mypy()

    print("\n" + "=" * 50)
    if flake8_ok:
        print("✓ 代码质量检查通过！")
        return 0
    else:
        print("✗ 代码质量检查失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
