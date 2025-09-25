#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03ScanPulse 测试运行脚本
提供便捷的测试执行和报告生成功能
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def install_dependencies():
    """安装测试依赖"""
    print("📦 安装测试依赖...")

    dependencies = [
        "pytest>=7.0.0",
        "pytest-html>=3.1.0",
        "pytest-cov>=4.0.0",
        "pytest-xdist>=3.0.0",
        "pytest-benchmark>=4.0.0",
        "pytest-mock>=3.10.0",
        "psutil>=5.9.0",
        "redis>=4.5.0",
        "pyzmq>=25.0.0",
        "requests>=2.28.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
    ]

    for dep in dependencies:
        print(f"  安装 {dep}...")
        success, stdout, stderr = run_command(f"pip install {dep}")
        if not success:
            print(f"  ❌ 安装失败: {stderr}")
            return False
        else:
            print(f"  ✅ 安装成功")

    return True


def run_unit_tests(verbose=False, coverage=False):
    """运行单元测试"""
    print("🧪 运行单元测试...")

    cmd = "pytest tests/unit"

    if verbose:
        cmd += " -v"

    if coverage:
        cmd += " --cov=scanner --cov-report=html --cov-report=term"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 单元测试通过")
    else:
        print("❌ 单元测试失败")
        print(stderr)

    return success


def run_integration_tests(verbose=False):
    """运行集成测试"""
    print("🔗 运行集成测试...")

    cmd = "pytest tests/integration -m integration"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 集成测试通过")
    else:
        print("❌ 集成测试失败")
        print(stderr)

    return success


def run_performance_tests(verbose=False, quick=False):
    """运行性能测试"""
    print("⚡ 运行性能测试...")

    if quick:
        # 快速性能测试，跳过长时间运行的测试
        cmd = "pytest tests/performance -m 'performance and not slow'"
    else:
        cmd = "pytest tests/performance -m performance"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short --benchmark-only"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 性能测试通过")
    else:
        print("❌ 性能测试失败")
        print(stderr)

    return success


def run_load_tests(verbose=False):
    """运行负载测试"""
    print("🚀 运行负载测试...")

    cmd = "pytest tests/performance/test_load_tests.py -m load"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 负载测试通过")
    else:
        print("❌ 负载测试失败")
        print(stderr)

    return success


def run_stability_tests(verbose=False):
    """运行稳定性测试"""
    print("🏗️ 运行稳定性测试...")

    cmd = "pytest tests/performance/test_stability_tests.py -m stability"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 稳定性测试通过")
    else:
        print("❌ 稳定性测试失败")
        print(stderr)

    return success


def run_stress_tests(verbose=False):
    """运行压力测试"""
    print("💪 运行压力测试...")

    cmd = "pytest tests/performance/test_stress_tests.py -m stress"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 压力测试通过")
    else:
        print("❌ 压力测试失败")
        print(stderr)

    return success


def run_production_tests(verbose=False):
    """运行生产环境验证测试"""
    print("🏭 运行生产环境验证测试...")

    cmd = "pytest tests/performance/test_production_validation.py -m production"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 生产环境验证测试通过")
    else:
        print("❌ 生产环境验证测试失败")
        print(stderr)

    return success


def run_e2e_tests(verbose=False):
    """运行端到端测试"""
    print("🎯 运行端到端测试...")

    cmd = "pytest tests/e2e -m e2e"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 端到端测试通过")
    else:
        print("❌ 端到端测试失败")
        print(stderr)

    return success


def run_reporting_tests(verbose=False):
    """运行测试报告分析"""
    print("📊 运行测试报告分析...")

    cmd = "pytest tests/reporting -m reporting"

    if verbose:
        cmd += " -v"

    cmd += " --tb=short"

    success, stdout, stderr = run_command(cmd)

    if success:
        print("✅ 测试报告分析通过")
    else:
        print("❌ 测试报告分析失败")
        print(stderr)

    return success


def generate_full_report(output_dir="test_reports"):
    """生成完整测试报告"""
    print("📋 生成完整测试报告...")

    # 创建报告目录
    report_dir = Path(output_dir)
    report_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 运行所有测试并生成报告
