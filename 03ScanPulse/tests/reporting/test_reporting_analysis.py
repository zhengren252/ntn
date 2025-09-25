#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试报告和分析模块
提供自动化测试报告生成、性能基准对比、测试覆盖率分析和质量门禁设置
"""

import pytest
import json
import os
import time
import subprocess
import tempfile
import shutil
import sqlite3
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from collections import defaultdict, Counter
from contextlib import contextmanager
import statistics
import re
import hashlib
import base64
from jinja2 import Template
import matplotlib

matplotlib.use("Agg")  # 使用非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from io import StringIO, BytesIO


@dataclass
class ResultData:
    """测试结果数据结构"""

    test_name: str
    test_file: str
    test_class: str
    test_method: str
    status: str  # passed, failed, skipped, error
    duration: float
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    markers: List[str] = field(default_factory=list)
    setup_duration: float = 0.0
    teardown_duration: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageResult:
    """代码覆盖率结果"""

    file_path: str
    lines_total: int
    lines_covered: int
    lines_missing: List[int]
    coverage_percentage: float
    branch_total: int = 0
    branch_covered: int = 0
    branch_percentage: float = 0.0
    functions_total: int = 0
    functions_covered: int = 0
    function_percentage: float = 0.0


@dataclass
class PerformanceMetric:
    """性能指标"""

    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    test_name: str
    baseline_value: Optional[float] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    status: str = "unknown"  # pass, fail, warning


@dataclass
class QualityGate:
    """质量门禁"""

    name: str
    description: str
    metric_type: str  # coverage, performance, test_success_rate
    threshold_value: float
    comparison_operator: str  # >=, <=, ==, !=
    is_blocking: bool = True
    weight: float = 1.0


@dataclass
class ReportData:
    """测试报告"""

    report_id: str
    timestamp: datetime
    test_session_info: Dict[str, Any]
    test_results: List[ResultData]
    coverage_results: List[CoverageResult]
    performance_metrics: List[PerformanceMetric]
    quality_gates: List[QualityGate]
    summary: Dict[str, Any]
    recommendations: List[str]
    artifacts: Dict[str, str]  # 文件路径映射


class ResultCollector:
    """测试结果收集器"""

    def __init__(self):
        self.results: List[ResultData] = []
        self.session_info = {}

    def collect_from_pytest_json(self, json_file: str) -> List[ResultData]:
        """从pytest JSON报告收集结果"""
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.session_info = {
                "pytest_version": data.get("pytest_version", "unknown"),
                "python_version": data.get("python_version", "unknown"),
                "platform": data.get("platform", "unknown"),
                "start_time": data.get("created", time.time()),
                "duration": data.get("duration", 0),
            }

            results = []

            for test in data.get("tests", []):
                # 解析测试名称
                nodeid = test.get("nodeid", "")
                parts = nodeid.split("::")
                test_file = parts[0] if parts else "unknown"
                test_class = (
                    parts[1] if len(parts) > 1 and "." not in parts[1] else "unknown"
                )
                test_method = parts[-1] if parts else "unknown"

                # 创建测试结果
                result = ResultData(
                    test_name=test.get("name", test_method),
                    test_file=test_file,
                    test_class=test_class,
                    test_method=test_method,
                    status=test.get("outcome", "unknown"),
                    duration=test.get("duration", 0),
                    error_message=self._extract_error_message(test),
                    error_traceback=self._extract_traceback(test),
                    markers=test.get("markers", []),
                    setup_duration=test.get("setup", {}).get("duration", 0),
                    teardown_duration=test.get("teardown", {}).get("duration", 0),
                    metadata=test.get("metadata", {}),
                )

                results.append(result)

            self.results.extend(results)
            return results

        except Exception as e:
            print(f"收集pytest JSON结果失败: {str(e)}")
            return []

    def _extract_error_message(self, test_data: Dict[str, Any]) -> Optional[str]:
        """提取错误消息"""
        call_info = test_data.get("call", {})
        if "longrepr" in call_info:
            longrepr = call_info["longrepr"]
            if isinstance(longrepr, str):
                # 提取第一行作为错误消息
                lines = longrepr.split("\n")
                for line in lines:
                    if line.strip() and not line.startswith(" "):
                        return line.strip()
        return None

    def _extract_traceback(self, test_data: Dict[str, Any]) -> Optional[str]:
        """提取错误堆栈"""
        call_info = test_data.get("call", {})
        return (
            call_info.get("longrepr")
            if isinstance(call_info.get("longrepr"), str)
            else None
        )

    def collect_from_junit_xml(self, xml_file: str) -> List[ResultData]:
        """从JUnit XML报告收集结果"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            results = []

            for testcase in root.findall(".//testcase"):
                # 解析测试信息
                classname = testcase.get("classname", "unknown")
                name = testcase.get("name", "unknown")
                time_str = testcase.get("time", "0")
                duration = float(time_str) if time_str else 0.0

                # 确定状态
                status = "passed"
                error_message = None
                error_traceback = None

                # 检查失败
                failure = testcase.find("failure")
                if failure is not None:
                    status = "failed"
                    error_message = failure.get("message", "")
                    error_traceback = failure.text

                # 检查错误
                error = testcase.find("error")
                if error is not None:
                    status = "error"
                    error_message = error.get("message", "")
                    error_traceback = error.text

                # 检查跳过
                skipped = testcase.find("skipped")
                if skipped is not None:
                    status = "skipped"
                    error_message = skipped.get("message", "")

                result = ResultData(
                    test_name=name,
                    test_file=classname.replace(".", "/") + ".py",
                    test_class=classname.split(".")[-1]
                    if "." in classname
                    else classname,
                    test_method=name,
                    status=status,
                    duration=duration,
                    error_message=error_message,
                    error_traceback=error_traceback,
                )

                results.append(result)

            self.results.extend(results)
            return results

        except Exception as e:
            print(f"收集JUnit XML结果失败: {str(e)}")
            return []

    def get_summary(self) -> Dict[str, Any]:
        """获取测试结果摘要"""
        if not self.results:
            return {}

        status_counts = Counter(result.status for result in self.results)
        total_tests = len(self.results)
        total_duration = sum(result.duration for result in self.results)

        return {
            "total_tests": total_tests,
            "passed": status_counts.get("passed", 0),
            "failed": status_counts.get("failed", 0),
            "skipped": status_counts.get("skipped", 0),
            "errors": status_counts.get("error", 0),
            "success_rate": status_counts.get("passed", 0) / total_tests
            if total_tests > 0
            else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / total_tests if total_tests > 0 else 0,
            "session_info": self.session_info,
        }


class CoverageAnalyzer:
    """代码覆盖率分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def analyze_coverage_xml(self, xml_file: str) -> List[CoverageResult]:
        """分析coverage XML报告"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            results = []

            for package in root.findall(".//package"):
                for class_elem in package.findall("classes/class"):
                    filename = class_elem.get("filename", "")

                    # 解析行覆盖率
                    lines = class_elem.findall("lines/line")
                    lines_total = len(lines)
                    lines_covered = sum(
                        1 for line in lines if line.get("hits", "0") != "0"
                    )
                    lines_missing = [
                        int(line.get("number", 0))
                        for line in lines
                        if line.get("hits", "0") == "0"
                    ]

                    coverage_percentage = (
                        (lines_covered / lines_total * 100) if lines_total > 0 else 0
                    )

                    result = CoverageResult(
                        file_path=filename,
                        lines_total=lines_total,
                        lines_covered=lines_covered,
                        lines_missing=lines_missing,
                        coverage_percentage=coverage_percentage,
                    )

                    results.append(result)

            return results

        except Exception as e:
            print(f"分析coverage XML失败: {str(e)}")
            return []

    def analyze_coverage_json(self, json_file: str) -> List[CoverageResult]:
        """分析coverage JSON报告"""
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            results = []

            files_data = data.get("files", {})

            for file_path, file_info in files_data.items():
                summary = file_info.get("summary", {})

                # 行覆盖率
                lines_total = summary.get("num_statements", 0)
                lines_covered = summary.get("covered_lines", 0)
                lines_missing = file_info.get("missing_lines", [])
                coverage_percentage = summary.get("percent_covered", 0)

                # 分支覆盖率
                branch_total = summary.get("num_branches", 0)
                branch_covered = summary.get("covered_branches", 0)
                branch_percentage = (
                    (branch_covered / branch_total * 100) if branch_total > 0 else 0
                )

                result = CoverageResult(
                    file_path=file_path,
                    lines_total=lines_total,
                    lines_covered=lines_covered,
                    lines_missing=lines_missing,
                    coverage_percentage=coverage_percentage,
                    branch_total=branch_total,
                    branch_covered=branch_covered,
                    branch_percentage=branch_percentage,
                )

                results.append(result)

            return results

        except Exception as e:
            print(f"分析coverage JSON失败: {str(e)}")
            return []

    def generate_coverage_summary(
        self, coverage_results: List[CoverageResult]
    ) -> Dict[str, Any]:
        """生成覆盖率摘要"""
        if not coverage_results:
            return {}

        total_lines = sum(result.lines_total for result in coverage_results)
        covered_lines = sum(result.lines_covered for result in coverage_results)
        total_branches = sum(result.branch_total for result in coverage_results)
        covered_branches = sum(result.branch_covered for result in coverage_results)

        line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0
        branch_coverage = (
            (covered_branches / total_branches * 100) if total_branches > 0 else 0
        )

        # 按文件类型分组
        by_extension = defaultdict(list)
        for result in coverage_results:
            ext = Path(result.file_path).suffix
            by_extension[ext].append(result)

        extension_summary = {}
        for ext, results in by_extension.items():
            ext_total_lines = sum(r.lines_total for r in results)
            ext_covered_lines = sum(r.lines_covered for r in results)
            ext_coverage = (
                (ext_covered_lines / ext_total_lines * 100)
                if ext_total_lines > 0
                else 0
            )

            extension_summary[ext] = {
                "files": len(results),
                "lines_total": ext_total_lines,
                "lines_covered": ext_covered_lines,
                "coverage_percentage": ext_coverage,
            }

        # 低覆盖率文件
        low_coverage_files = [
            {"file": result.file_path, "coverage": result.coverage_percentage}
            for result in coverage_results
            if result.coverage_percentage < 80
        ]
        low_coverage_files.sort(key=lambda x: x["coverage"])

        return {
            "total_files": len(coverage_results),
            "total_lines": total_lines,
            "covered_lines": covered_lines,
            "line_coverage_percentage": line_coverage,
            "total_branches": total_branches,
            "covered_branches": covered_branches,
            "branch_coverage_percentage": branch_coverage,
            "by_extension": extension_summary,
            "low_coverage_files": low_coverage_files[:10],  # 前10个最低覆盖率文件
        }


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self, baseline_file: str = "performance_baseline.json"):
        self.baseline_file = baseline_file
        self.baselines = self._load_baselines()

    def _load_baselines(self) -> Dict[str, Dict[str, float]]:
        """加载性能基准"""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载性能基准失败: {str(e)}")
        return {}

    def analyze_performance_metrics(
        self, test_results: List[ResultData]
    ) -> List[PerformanceMetric]:
        """分析性能指标"""
        metrics = []

        for result in test_results:
            # 测试持续时间指标
            duration_metric = PerformanceMetric(
                metric_name="test_duration",
                value=result.duration,
                unit="seconds",
                timestamp=result.timestamp,
                test_name=result.test_name,
            )

            # 检查基准
            baseline_key = f"{result.test_name}_duration"
            if baseline_key in self.baselines:
                duration_metric.baseline_value = self.baselines[baseline_key]

            metrics.append(duration_metric)

            # 内存使用指标
            if result.memory_usage > 0:
                memory_metric = PerformanceMetric(
                    metric_name="memory_usage",
                    value=result.memory_usage,
                    unit="MB",
                    timestamp=result.timestamp,
                    test_name=result.test_name,
                )

                baseline_key = f"{result.test_name}_memory"
                if baseline_key in self.baselines:
                    memory_metric.baseline_value = self.baselines[baseline_key]

                metrics.append(memory_metric)

            # CPU使用指标
            if result.cpu_usage > 0:
                cpu_metric = PerformanceMetric(
                    metric_name="cpu_usage",
                    value=result.cpu_usage,
                    unit="percent",
                    timestamp=result.timestamp,
                    test_name=result.test_name,
                )

                baseline_key = f"{result.test_name}_cpu"
                if baseline_key in self.baselines:
                    cpu_metric.baseline_value = self.baselines[baseline_key]

                metrics.append(cpu_metric)

        return metrics

    def compare_with_baseline(
        self, metrics: List[PerformanceMetric], threshold: float = 0.1
    ) -> Dict[str, Any]:
        """与基准进行比较"""
        comparisons = []
        regressions = []
        improvements = []

        for metric in metrics:
            if metric.baseline_value is not None:
                change_ratio = (
                    metric.value - metric.baseline_value
                ) / metric.baseline_value

                comparison = {
                    "metric_name": metric.metric_name,
                    "test_name": metric.test_name,
                    "current_value": metric.value,
                    "baseline_value": metric.baseline_value,
                    "change_ratio": change_ratio,
                    "change_percentage": change_ratio * 100,
                    "unit": metric.unit,
                }

                # 判断回归或改进
                if metric.metric_name in ["test_duration", "memory_usage", "cpu_usage"]:
                    # 对于这些指标，增加是回归
                    if change_ratio > threshold:
                        comparison["status"] = "regression"
                        regressions.append(comparison)
                    elif change_ratio < -threshold:
                        comparison["status"] = "improvement"
                        improvements.append(comparison)
                    else:
                        comparison["status"] = "stable"
                else:
                    # 对于吞吐量等指标，减少是回归
                    if change_ratio < -threshold:
                        comparison["status"] = "regression"
                        regressions.append(comparison)
                    elif change_ratio > threshold:
                        comparison["status"] = "improvement"
                        improvements.append(comparison)
                    else:
                        comparison["status"] = "stable"

                comparisons.append(comparison)

        return {
            "total_comparisons": len(comparisons),
            "regressions": regressions,
            "improvements": improvements,
            "stable_metrics": len(comparisons) - len(regressions) - len(improvements),
            "all_comparisons": comparisons,
        }

    def generate_performance_trends(
        self, metrics: List[PerformanceMetric]
    ) -> Dict[str, Any]:
        """生成性能趋势分析"""
        # 按指标名称分组
        by_metric = defaultdict(list)
        for metric in metrics:
            by_metric[metric.metric_name].append(metric)

        trends = {}

        for metric_name, metric_list in by_metric.items():
            if len(metric_list) < 2:
                continue

            # 按时间排序
            metric_list.sort(key=lambda x: x.timestamp)

            values = [m.value for m in metric_list]

            # 计算趋势统计
            trend_stats = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "trend_direction": "stable",
            }

            # 简单趋势分析
            if len(values) >= 3:
                first_third = values[: len(values) // 3]
                last_third = values[-len(values) // 3 :]

                first_avg = statistics.mean(first_third)
                last_avg = statistics.mean(last_third)

                change_ratio = (
                    (last_avg - first_avg) / first_avg if first_avg != 0 else 0
                )

                if change_ratio > 0.1:
                    trend_stats["trend_direction"] = "increasing"
                elif change_ratio < -0.1:
                    trend_stats["trend_direction"] = "decreasing"

                trend_stats["trend_change_ratio"] = change_ratio

            trends[metric_name] = trend_stats

        return trends


class QualityGateEvaluator:
    """质量门禁评估器"""

    def __init__(self):
        self.default_gates = [
            QualityGate(
                name="测试成功率",
                description="测试用例成功率必须达到95%以上",
                metric_type="test_success_rate",
                threshold_value=0.95,
                comparison_operator=">=",
                is_blocking=True,
                weight=1.0,
            ),
            QualityGate(
                name="代码覆盖率",
                description="代码行覆盖率必须达到80%以上",
                metric_type="line_coverage",
                threshold_value=80.0,
                comparison_operator=">=",
                is_blocking=True,
                weight=0.8,
            ),
            QualityGate(
                name="分支覆盖率",
                description="代码分支覆盖率必须达到70%以上",
                metric_type="branch_coverage",
                threshold_value=70.0,
                comparison_operator=">=",
                is_blocking=False,
                weight=0.6,
            ),
            QualityGate(
                name="性能回归",
                description="不允许超过10%的性能回归",
                metric_type="performance_regression",
                threshold_value=0.1,
                comparison_operator="<=",
                is_blocking=True,
                weight=0.9,
            ),
        ]

    def evaluate_gates(
        self,
        test_summary: Dict[str, Any],
        coverage_summary: Dict[str, Any],
        performance_comparison: Dict[str, Any],
        custom_gates: List[QualityGate] = None,
    ) -> Dict[str, Any]:
        """评估质量门禁"""
        gates = custom_gates if custom_gates else self.default_gates

        gate_results = []
        blocking_failures = []
        warnings = []

        for gate in gates:
            result = self._evaluate_single_gate(
                gate, test_summary, coverage_summary, performance_comparison
            )
            gate_results.append(result)

            if not result["passed"]:
                if gate.is_blocking:
                    blocking_failures.append(result)
                else:
                    warnings.append(result)

        # 计算总体质量分数
        total_weight = sum(gate.weight for gate in gates)
        passed_weight = sum(
            gate.weight for gate, result in zip(gates, gate_results) if result["passed"]
        )
        quality_score = (passed_weight / total_weight * 100) if total_weight > 0 else 0

        overall_passed = len(blocking_failures) == 0

        return {
            "overall_passed": overall_passed,
            "quality_score": quality_score,
            "total_gates": len(gates),
            "passed_gates": sum(1 for result in gate_results if result["passed"]),
            "failed_gates": sum(1 for result in gate_results if not result["passed"]),
            "blocking_failures": blocking_failures,
            "warnings": warnings,
            "gate_results": gate_results,
        }

    def _evaluate_single_gate(
        self,
        gate: QualityGate,
        test_summary: Dict[str, Any],
        coverage_summary: Dict[str, Any],
        performance_comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        """评估单个质量门禁"""
        actual_value = None
        passed = False

        try:
            # 获取实际值
            if gate.metric_type == "test_success_rate":
                actual_value = test_summary.get("success_rate", 0)
            elif gate.metric_type == "line_coverage":
                actual_value = coverage_summary.get("line_coverage_percentage", 0)
            elif gate.metric_type == "branch_coverage":
                actual_value = coverage_summary.get("branch_coverage_percentage", 0)
            elif gate.metric_type == "performance_regression":
                regressions = performance_comparison.get("regressions", [])
                if regressions:
                    max_regression = max(abs(r["change_ratio"]) for r in regressions)
                    actual_value = max_regression
                else:
                    actual_value = 0.0

            # 评估是否通过
            if actual_value is not None:
                if gate.comparison_operator == ">=":
                    passed = actual_value >= gate.threshold_value
                elif gate.comparison_operator == "<=":
                    passed = actual_value <= gate.threshold_value
                elif gate.comparison_operator == "==":
                    passed = actual_value == gate.threshold_value
                elif gate.comparison_operator == "!=":
                    passed = actual_value != gate.threshold_value

        except Exception as e:
            print(f"评估质量门禁 {gate.name} 失败: {str(e)}")

        return {
            "gate_name": gate.name,
            "description": gate.description,
            "metric_type": gate.metric_type,
            "threshold_value": gate.threshold_value,
            "actual_value": actual_value,
            "comparison_operator": gate.comparison_operator,
            "passed": passed,
            "is_blocking": gate.is_blocking,
            "weight": gate.weight,
        }


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html_report(self, report: ReportData) -> str:
        """生成HTML报告"""
        template_str = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {{ report.report_id }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .metric-label { color: #666; margin-top: 5px; }
        .section { margin-bottom: 30px; }
        .section h2 { border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .test-result { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .passed { background-color: #d4edda; border-left: 4px solid #28a745; }
        .failed { background-color: #f8d7da; border-left: 4px solid #dc3545; }
        .skipped { background-color: #fff3cd; border-left: 4px solid #ffc107; }
        .error { background-color: #f8d7da; border-left: 4px solid #dc3545; }
        .coverage-bar { width: 100%; height: 20px; background-color: #e9ecef; border-radius: 10px; overflow: hidden; }
        .coverage-fill { height: 100%; background-color: #28a745; transition: width 0.3s ease; }
        .quality-gate { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .gate-passed { background-color: #d4edda; }
        .gate-failed { background-color: #f8d7da; }
        .recommendations { background-color: #e7f3ff; padding: 15px; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .chart-container { margin: 20px 0; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>测试报告</h1>
            <p>报告ID: {{ report.report_id }}</p>
            <p>生成时间: {{ report.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </div>
        
        <div class="section">
            <h2>测试摘要</h2>
            <div class="summary">
                <div class="metric-card">
                    <div class="metric-value">{{ report.summary.total_tests }}</div>
                    <div class="metric-label">总测试数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ report.summary.passed }}</div>
                    <div class="metric-label">通过</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ report.summary.failed }}</div>
                    <div class="metric-label">失败</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f" | format(report.summary.success_rate * 100) }}%</div>
                    <div class="metric-label">成功率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.2f" | format(report.summary.total_duration) }}s</div>
                    <div class="metric-label">总耗时</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>代码覆盖率</h2>
            {% if report.summary.coverage %}
            <div class="summary">
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f" | format(report.summary.coverage.line_coverage_percentage) }}%</div>
                    <div class="metric-label">行覆盖率</div>
                    <div class="coverage-bar">
                        <div class="coverage-fill" style="width: {{ report.summary.coverage.line_coverage_percentage }}%"></div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f" | format(report.summary.coverage.branch_coverage_percentage) }}%</div>
                    <div class="metric-label">分支覆盖率</div>
                    <div class="coverage-bar">
                        <div class="coverage-fill" style="width: {{ report.summary.coverage.branch_coverage_percentage }}%"></div>
                    </div>
                </div>
            </div>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>质量门禁</h2>
            {% if report.summary.quality_gates %}
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f" | format(report.summary.quality_gates.quality_score) }}</div>
                <div class="metric-label">质量分数</div>
            </div>
            
            {% for gate in report.summary.quality_gates.gate_results %}
            <div class="quality-gate {{ 'gate-passed' if gate.passed else 'gate-failed' }}">
                <strong>{{ gate.gate_name }}</strong>
                <span style="float: right;">{{ '✓' if gate.passed else '✗' }}</span>
                <br>
                <small>{{ gate.description }}</small>
                <br>
                <small>期望: {{ gate.comparison_operator }} {{ gate.threshold_value }}, 实际: {{ gate.actual_value }}</small>
            </div>
            {% endfor %}
            {% endif %}
        </div>
        
        <div class="section">
            <h2>测试结果详情</h2>
            {% for result in report.test_results[:20] %}
            <div class="test-result {{ result.status }}">
                <strong>{{ result.test_name }}</strong>
                <span style="float: right;">{{ "%.3f" | format(result.duration) }}s</span>
                <br>
                <small>{{ result.test_file }}::{{ result.test_class }}::{{ result.test_method }}</small>
                {% if result.error_message %}
                <br>
                <small style="color: #dc3545;">{{ result.error_message }}</small>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        {% if report.recommendations %}
        <div class="section">
            <h2>改进建议</h2>
            <div class="recommendations">
                <ul>
                {% for recommendation in report.recommendations %}
                    <li>{{ recommendation }}</li>
                {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
        
        <div class="section">
            <h2>环境信息</h2>
            <table>
                {% for key, value in report.test_session_info.items() %}
                <tr>
                    <td><strong>{{ key }}</strong></td>
                    <td>{{ value }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
        """

        template = Template(template_str)
        html_content = template.render(report=report)

        # 保存HTML文件
        html_file = self.output_dir / f"test_report_{report.report_id}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_file)

    def generate_json_report(self, report: ReportData) -> str:
        """生成JSON报告"""
        # 转换为可序列化的字典
        report_dict = {
            "report_id": report.report_id,
            "timestamp": report.timestamp.isoformat(),
            "test_session_info": report.test_session_info,
            "test_results": [asdict(result) for result in report.test_results],
            "coverage_results": [asdict(result) for result in report.coverage_results],
            "performance_metrics": [
                asdict(metric) for metric in report.performance_metrics
            ],
            "quality_gates": [asdict(gate) for gate in report.quality_gates],
            "summary": report.summary,
            "recommendations": report.recommendations,
            "artifacts": report.artifacts,
        }

        # 处理datetime对象
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        json_file = self.output_dir / f"test_report_{report.report_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                report_dict, f, indent=2, ensure_ascii=False, default=datetime_handler
            )

        return str(json_file)

    def generate_csv_report(self, report: ReportData) -> str:
        """生成CSV报告"""
        csv_file = self.output_dir / f"test_results_{report.report_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow(
                [
                    "Test Name",
                    "Test File",
                    "Test Class",
                    "Test Method",
                    "Status",
                    "Duration",
                    "Error Message",
                    "Timestamp",
                ]
            )

            # 写入测试结果
            for result in report.test_results:
                writer.writerow(
                    [
                        result.test_name,
                        result.test_file,
                        result.test_class,
                        result.test_method,
                        result.status,
                        result.duration,
                        result.error_message or "",
                        result.timestamp.isoformat(),
                    ]
                )

        return str(csv_file)

    def generate_charts(self, report: ReportData) -> Dict[str, str]:
        """生成图表"""
        charts = {}

        try:
            # 设置中文字体
            plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            # 1. 测试结果饼图
            fig, ax = plt.subplots(figsize=(8, 6))

            status_counts = Counter(result.status for result in report.test_results)
            labels = list(status_counts.keys())
            sizes = list(status_counts.values())
            colors = {
                "passed": "#28a745",
                "failed": "#dc3545",
                "skipped": "#ffc107",
                "error": "#fd7e14",
            }
            chart_colors = [colors.get(label, "#6c757d") for label in labels]

            ax.pie(
                sizes,
                labels=labels,
                colors=chart_colors,
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.set_title("测试结果分布")

            chart_file = self.output_dir / f"test_results_pie_{report.report_id}.png"
            plt.savefig(chart_file, dpi=150, bbox_inches="tight")
            plt.close()
            charts["test_results_pie"] = str(chart_file)

            # 2. 测试持续时间柱状图
            if report.test_results:
                fig, ax = plt.subplots(figsize=(12, 6))

                # 选择前20个最慢的测试
                sorted_results = sorted(
                    report.test_results, key=lambda x: x.duration, reverse=True
                )[:20]
                test_names = [
                    r.test_name[:30] + "..." if len(r.test_name) > 30 else r.test_name
                    for r in sorted_results
                ]
                durations = [r.duration for r in sorted_results]

                bars = ax.bar(range(len(test_names)), durations)
                ax.set_xlabel("测试用例")
                ax.set_ylabel("持续时间 (秒)")
                ax.set_title("测试持续时间 (前20个最慢的测试)")
                ax.set_xticks(range(len(test_names)))
                ax.set_xticklabels(test_names, rotation=45, ha="right")

                # 为失败的测试着色
                for i, result in enumerate(sorted_results):
                    if result.status == "failed":
                        bars[i].set_color("#dc3545")
                    elif result.status == "passed":
                        bars[i].set_color("#28a745")

                chart_file = (
                    self.output_dir / f"test_duration_bar_{report.report_id}.png"
                )
                plt.savefig(chart_file, dpi=150, bbox_inches="tight")
                plt.close()
                charts["test_duration_bar"] = str(chart_file)

            # 3. 覆盖率图表
            if report.coverage_results:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

                # 覆盖率分布直方图
                coverage_percentages = [
                    r.coverage_percentage for r in report.coverage_results
                ]
                ax1.hist(
                    coverage_percentages,
                    bins=20,
                    color="#007bff",
                    alpha=0.7,
                    edgecolor="black",
                )
                ax1.set_xlabel("覆盖率 (%)")
                ax1.set_ylabel("文件数量")
                ax1.set_title("代码覆盖率分布")
                ax1.axvline(x=80, color="red", linestyle="--", label="80%阈值")
                ax1.legend()

                # 低覆盖率文件
                low_coverage = [
                    r for r in report.coverage_results if r.coverage_percentage < 80
                ][:10]
                if low_coverage:
                    file_names = [Path(r.file_path).name for r in low_coverage]
                    coverages = [r.coverage_percentage for r in low_coverage]

                    bars = ax2.bar(
                        range(len(file_names)), coverages, color="#dc3545", alpha=0.7
                    )
                    ax2.set_xlabel("文件")
                    ax2.set_ylabel("覆盖率 (%)")
                    ax2.set_title("低覆盖率文件 (< 80%)")
                    ax2.set_xticks(range(len(file_names)))
                    ax2.set_xticklabels(file_names, rotation=45, ha="right")
                    ax2.axhline(y=80, color="red", linestyle="--", alpha=0.5)

                chart_file = (
                    self.output_dir / f"coverage_analysis_{report.report_id}.png"
                )
                plt.savefig(chart_file, dpi=150, bbox_inches="tight")
                plt.close()
                charts["coverage_analysis"] = str(chart_file)

        except Exception as e:
            print(f"生成图表失败: {str(e)}")

        return charts


class ReportingFramework:
    """测试报告框架"""

    def __init__(self, project_root: str, output_dir: str = "test_reports"):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.result_collector = ResultCollector()
        self.coverage_analyzer = CoverageAnalyzer(str(project_root))
        self.performance_analyzer = PerformanceAnalyzer()
        self.quality_gate_evaluator = QualityGateEvaluator()
        self.report_generator = ReportGenerator(str(output_dir))

    def generate_comprehensive_report(
        self,
        pytest_json_file: Optional[str] = None,
        junit_xml_file: Optional[str] = None,
        coverage_xml_file: Optional[str] = None,
        coverage_json_file: Optional[str] = None,
        custom_quality_gates: Optional[List[QualityGate]] = None,
    ) -> ReportData:
        """生成综合测试报告"""

        report_id = f"report_{int(time.time())}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        timestamp = datetime.now(timezone.utc)

        # 收集测试结果
        test_results = []
        if pytest_json_file and os.path.exists(pytest_json_file):
            test_results.extend(
                self.result_collector.collect_from_pytest_json(pytest_json_file)
            )
        if junit_xml_file and os.path.exists(junit_xml_file):
            test_results.extend(
                self.result_collector.collect_from_junit_xml(junit_xml_file)
            )

        # 收集覆盖率结果
        coverage_results = []
        if coverage_xml_file and os.path.exists(coverage_xml_file):
            coverage_results.extend(
                self.coverage_analyzer.analyze_coverage_xml(coverage_xml_file)
            )
        if coverage_json_file and os.path.exists(coverage_json_file):
            coverage_results.extend(
                self.coverage_analyzer.analyze_coverage_json(coverage_json_file)
            )

        # 分析性能指标
        performance_metrics = self.performance_analyzer.analyze_performance_metrics(
            test_results
        )

        # 生成摘要
        test_summary = self.result_collector.get_summary()
        coverage_summary = self.coverage_analyzer.generate_coverage_summary(
            coverage_results
        )
        performance_comparison = self.performance_analyzer.compare_with_baseline(
            performance_metrics
        )

        # 评估质量门禁
        quality_gate_result = self.quality_gate_evaluator.evaluate_gates(
            test_summary, coverage_summary, performance_comparison, custom_quality_gates
        )

        # 生成建议
        recommendations = self._generate_recommendations(
            test_summary, coverage_summary, performance_comparison, quality_gate_result
        )

        # 创建报告对象
        report = ReportData(
            report_id=report_id,
            timestamp=timestamp,
            test_session_info=test_summary.get("session_info", {}),
            test_results=test_results,
            coverage_results=coverage_results,
            performance_metrics=performance_metrics,
            quality_gates=custom_quality_gates
            or self.quality_gate_evaluator.default_gates,
            summary={
                **test_summary,
                "coverage": coverage_summary,
                "performance": performance_comparison,
                "quality_gates": quality_gate_result,
            },
            recommendations=recommendations,
            artifacts={},
        )

        # 生成报告文件
        html_file = self.report_generator.generate_html_report(report)
        json_file = self.report_generator.generate_json_report(report)
        csv_file = self.report_generator.generate_csv_report(report)
        charts = self.report_generator.generate_charts(report)

        report.artifacts = {
            "html_report": html_file,
            "json_report": json_file,
            "csv_report": csv_file,
            **charts,
        }

        return report

    def _generate_recommendations(
        self,
        test_summary: Dict[str, Any],
        coverage_summary: Dict[str, Any],
        performance_comparison: Dict[str, Any],
        quality_gate_result: Dict[str, Any],
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 测试相关建议
        success_rate = test_summary.get("success_rate", 0)
        if success_rate < 0.95:
            recommendations.append(f"测试成功率为 {success_rate:.1%}，建议修复失败的测试用例以提高稳定性")

        failed_count = test_summary.get("failed", 0)
        if failed_count > 0:
            recommendations.append(f"有 {failed_count} 个测试用例失败，建议优先修复这些问题")

        # 覆盖率相关建议
        line_coverage = coverage_summary.get("line_coverage_percentage", 0)
        if line_coverage < 80:
            recommendations.append(f"代码行覆盖率为 {line_coverage:.1f}%，建议增加测试用例以达到80%以上")

        branch_coverage = coverage_summary.get("branch_coverage_percentage", 0)
        if branch_coverage < 70:
            recommendations.append(f"分支覆盖率为 {branch_coverage:.1f}%，建议增加边界条件和异常情况的测试")

        low_coverage_files = coverage_summary.get("low_coverage_files", [])
        if low_coverage_files:
            recommendations.append(
                f"发现 {len(low_coverage_files)} 个低覆盖率文件，建议重点关注这些文件的测试"
            )

        # 性能相关建议
        regressions = performance_comparison.get("regressions", [])
        if regressions:
            recommendations.append(f"检测到 {len(regressions)} 个性能回归，建议分析并优化相关代码")

        # 质量门禁相关建议
        blocking_failures = quality_gate_result.get("blocking_failures", [])
        if blocking_failures:
            recommendations.append(f"有 {len(blocking_failures)} 个阻塞性质量门禁失败，必须修复后才能发布")

        warnings = quality_gate_result.get("warnings", [])
        if warnings:
            recommendations.append(f"有 {len(warnings)} 个质量警告，建议在下次迭代中改进")

        quality_score = quality_gate_result.get("quality_score", 0)
        if quality_score < 80:
            recommendations.append(f"质量分数为 {quality_score:.1f}，建议全面提升代码质量")

        return recommendations


class TestReportingAnalysis:
    """测试报告分析类"""

    @pytest.fixture
    def reporting_framework(self):
        """报告框架fixture"""
        project_root = Path(__file__).parent.parent.parent
        output_dir = tempfile.mkdtemp(prefix="test_reports_")

        framework = ReportingFramework(str(project_root), output_dir)
        yield framework

        # 清理
        shutil.rmtree(output_dir, ignore_errors=True)

    @pytest.mark.reporting
    def test_generate_comprehensive_report(self, reporting_framework):
        """测试生成综合报告"""
        # 创建模拟的测试结果文件
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # 创建模拟的pytest JSON报告
            pytest_json = {
                "pytest_version": "7.0.0",
                "python_version": "3.9.0",
                "platform": "Windows-10",
                "created": time.time(),
                "duration": 30.5,
                "tests": [
                    {
                        "nodeid": "test_example.py::TestClass::test_method1",
                        "name": "test_method1",
                        "outcome": "passed",
                        "duration": 0.5,
                        "markers": ["unit"],
                    },
                    {
                        "nodeid": "test_example.py::TestClass::test_method2",
                        "name": "test_method2",
                        "outcome": "failed",
                        "duration": 1.2,
                        "call": {"longrepr": "AssertionError: Test failed"},
                    },
                ],
            }

            pytest_json_file = temp_dir / "pytest_report.json"
            with open(pytest_json_file, "w") as f:
                json.dump(pytest_json, f)

            # 创建模拟的覆盖率JSON报告
            coverage_json = {
                "files": {
                    "scanner/core/engine.py": {
                        "summary": {
                            "num_statements": 100,
                            "covered_lines": 85,
                            "percent_covered": 85.0,
                            "num_branches": 20,
                            "covered_branches": 15,
                        },
                        "missing_lines": [10, 15, 20, 25, 30],
                    },
                    "scanner/detectors/detector.py": {
                        "summary": {
                            "num_statements": 50,
                            "covered_lines": 30,
                            "percent_covered": 60.0,
                            "num_branches": 10,
                            "covered_branches": 6,
                        },
                        "missing_lines": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                    },
                }
            }

            coverage_json_file = temp_dir / "coverage.json"
            with open(coverage_json_file, "w") as f:
                json.dump(coverage_json, f)

            # 生成综合报告
            report = reporting_framework.generate_comprehensive_report(
                pytest_json_file=str(pytest_json_file),
                coverage_json_file=str(coverage_json_file),
            )

            # 验证报告内容
            assert report.report_id is not None
            assert len(report.test_results) == 2
            assert len(report.coverage_results) == 2
            assert report.summary["total_tests"] == 2
            assert report.summary["passed"] == 1
            assert report.summary["failed"] == 1
            assert report.summary["success_rate"] == 0.5

            # 验证覆盖率摘要
            coverage_summary = report.summary["coverage"]
            assert coverage_summary["total_files"] == 2
            assert coverage_summary["line_coverage_percentage"] > 0

            # 验证质量门禁
            quality_gates = report.summary["quality_gates"]
            assert "overall_passed" in quality_gates
            assert "quality_score" in quality_gates

            # 验证生成的文件
            assert "html_report" in report.artifacts
            assert "json_report" in report.artifacts
            assert "csv_report" in report.artifacts

            # 验证文件存在
            assert os.path.exists(report.artifacts["html_report"])
            assert os.path.exists(report.artifacts["json_report"])
            assert os.path.exists(report.artifacts["csv_report"])

            # 验证建议
            assert len(report.recommendations) > 0

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.reporting
    def test_quality_gate_evaluation(self, reporting_framework):
        """测试质量门禁评估"""
        # 创建测试数据
        test_summary = {
            "total_tests": 100,
            "passed": 95,
            "failed": 5,
            "success_rate": 0.95,
        }

        coverage_summary = {
            "line_coverage_percentage": 85.0,
            "branch_coverage_percentage": 75.0,
        }

        performance_comparison = {
            "regressions": [
                {"change_ratio": 0.05},  # 5%回归
                {"change_ratio": 0.15},  # 15%回归
            ]
        }

        # 评估质量门禁
        result = reporting_framework.quality_gate_evaluator.evaluate_gates(
            test_summary, coverage_summary, performance_comparison
        )

        # 验证结果
        assert "overall_passed" in result
        assert "quality_score" in result
        assert "gate_results" in result
        assert len(result["gate_results"]) > 0

        # 验证具体门禁
        gate_names = [gate["gate_name"] for gate in result["gate_results"]]
        assert "测试成功率" in gate_names
        assert "代码覆盖率" in gate_names

    @pytest.mark.reporting
    def test_performance_analysis(self, reporting_framework):
        """测试性能分析"""
        # 创建测试结果
        test_results = [
            ResultData(
                test_name="test_performance_1",
                test_file="test_perf.py",
                test_class="TestPerf",
                test_method="test_performance_1",
                status="passed",
                duration=1.5,
                memory_usage=100.0,
                cpu_usage=50.0,
            ),
            ResultData(
                test_name="test_performance_2",
                test_file="test_perf.py",
                test_class="TestPerf",
                test_method="test_performance_2",
                status="passed",
                duration=2.0,
                memory_usage=150.0,
                cpu_usage=75.0,
            ),
        ]

        # 分析性能指标
        metrics = reporting_framework.performance_analyzer.analyze_performance_metrics(
            test_results
        )

        # 验证指标
        assert len(metrics) > 0

        metric_names = [m.metric_name for m in metrics]
        assert "test_duration" in metric_names
        assert "memory_usage" in metric_names
        assert "cpu_usage" in metric_names

        # 测试趋势分析
        trends = reporting_framework.performance_analyzer.generate_performance_trends(
            metrics
        )
        assert isinstance(trends, dict)

    @pytest.mark.reporting
    def test_coverage_analysis(self, reporting_framework):
        """测试覆盖率分析"""
        # 创建覆盖率结果
        coverage_results = [
            CoverageResult(
                file_path="scanner/core/engine.py",
                lines_total=100,
                lines_covered=85,
                lines_missing=[10, 15, 20],
                coverage_percentage=85.0,
                branch_total=20,
                branch_covered=15,
                branch_percentage=75.0,
            ),
            CoverageResult(
                file_path="scanner/detectors/detector.py",
                lines_total=50,
                lines_covered=30,
                lines_missing=[5, 10, 15],
                coverage_percentage=60.0,
                branch_total=10,
                branch_covered=6,
                branch_percentage=60.0,
            ),
        ]

        # 生成覆盖率摘要
        summary = reporting_framework.coverage_analyzer.generate_coverage_summary(
            coverage_results
        )

        # 验证摘要
        assert summary["total_files"] == 2
        assert summary["total_lines"] == 150
        assert summary["covered_lines"] == 115
        assert summary["line_coverage_percentage"] > 0
        assert "by_extension" in summary
        assert "low_coverage_files" in summary

    @pytest.mark.reporting
    def test_test_result_collection(self, reporting_framework):
        """测试结果收集"""
        # 创建临时JUnit XML文件
        temp_dir = Path(tempfile.mkdtemp())

        try:
            junit_xml = """
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite name="TestSuite" tests="3" failures="1" errors="0" skipped="1" time="5.5">
        <testcase classname="test.TestClass" name="test_pass" time="1.0"/>
        <testcase classname="test.TestClass" name="test_fail" time="2.0">
            <failure message="Test failed">AssertionError: Expected True</failure>
        </testcase>
        <testcase classname="test.TestClass" name="test_skip" time="0.5">
            <skipped message="Test skipped"/>
        </testcase>
    </testsuite>
</testsuites>
            """

            junit_file = temp_dir / "junit.xml"
            with open(junit_file, "w") as f:
                f.write(junit_xml)

            # 收集结果
            results = reporting_framework.result_collector.collect_from_junit_xml(
                str(junit_file)
            )

            # 验证结果
            assert len(results) == 3

            statuses = [r.status for r in results]
            assert "passed" in statuses
            assert "failed" in statuses
            assert "skipped" in statuses

            # 验证摘要
            summary = reporting_framework.result_collector.get_summary()
            assert summary["total_tests"] == 3
            assert summary["passed"] == 1
            assert summary["failed"] == 1
            assert summary["skipped"] == 1

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.reporting
    def test_report_generation_formats(self, reporting_framework):
        """测试报告生成格式"""
        # 创建简单的测试报告
        report = ReportData(
            report_id="test_report_123",
            timestamp=datetime.now(timezone.utc),
            test_session_info={"python_version": "3.9.0"},
            test_results=[
                ResultData(
                    test_name="test_example",
                    test_file="test_file.py",
                    test_class="TestClass",
                    test_method="test_example",
                    status="passed",
                    duration=1.0,
                )
            ],
            coverage_results=[],
            performance_metrics=[],
            quality_gates=[],
            summary={"total_tests": 1, "passed": 1, "success_rate": 1.0},
            recommendations=["示例建议"],
            artifacts={},
        )

        # 生成HTML报告
        html_file = reporting_framework.report_generator.generate_html_report(report)
        assert os.path.exists(html_file)
        assert html_file.endswith(".html")

        # 验证HTML内容
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
            assert "test_report_123" in html_content
            assert "test_example" in html_content

        # 生成JSON报告
        json_file = reporting_framework.report_generator.generate_json_report(report)
        assert os.path.exists(json_file)
        assert json_file.endswith(".json")

        # 验证JSON内容
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            assert json_data["report_id"] == "test_report_123"
            assert len(json_data["test_results"]) == 1

        # 生成CSV报告
        csv_file = reporting_framework.report_generator.generate_csv_report(report)
        assert os.path.exists(csv_file)
        assert csv_file.endswith(".csv")

        # 验证CSV内容
        with open(csv_file, "r", encoding="utf-8") as f:
            csv_content = f.read()
            assert "test_example" in csv_content
            assert "passed" in csv_content

    @pytest.mark.reporting
    def test_custom_quality_gates(self, reporting_framework):
        """测试自定义质量门禁"""
        # 创建自定义质量门禁
        custom_gates = [
            QualityGate(
                name="自定义成功率",
                description="测试成功率必须达到99%",
                metric_type="test_success_rate",
                threshold_value=0.99,
                comparison_operator=">=",
                is_blocking=True,
                weight=1.0,
            ),
            QualityGate(
                name="自定义覆盖率",
                description="代码覆盖率必须达到90%",
                metric_type="line_coverage",
                threshold_value=90.0,
                comparison_operator=">=",
                is_blocking=False,
                weight=0.8,
            ),
        ]

        # 测试数据
        test_summary = {"success_rate": 0.95}
        coverage_summary = {"line_coverage_percentage": 85.0}
        performance_comparison = {"regressions": []}

        # 评估自定义门禁
        result = reporting_framework.quality_gate_evaluator.evaluate_gates(
            test_summary, coverage_summary, performance_comparison, custom_gates
        )

        # 验证结果
        assert len(result["gate_results"]) == 2
        assert not result["overall_passed"]  # 应该失败，因为成功率不足99%

        # 验证具体门禁结果
        gate_results = {r["gate_name"]: r for r in result["gate_results"]}
        assert not gate_results["自定义成功率"]["passed"]
        assert not gate_results["自定义覆盖率"]["passed"]

    @pytest.mark.reporting
    def test_baseline_comparison(self, reporting_framework):
        """测试基准比较"""
        # 创建基准数据
        baseline_file = Path(tempfile.mkdtemp()) / "baseline.json"
        baseline_data = {
            "test_performance_1_duration": 1.0,
            "test_performance_1_memory": 80.0,
            "test_performance_2_duration": 1.5,
        }

        with open(baseline_file, "w") as f:
            json.dump(baseline_data, f)

        # 创建新的性能分析器
        analyzer = PerformanceAnalyzer(str(baseline_file))

        # 创建性能指标
        metrics = [
            PerformanceMetric(
                metric_name="test_duration",
                value=1.2,  # 比基准慢20%
                unit="seconds",
                timestamp=datetime.now(timezone.utc),
                test_name="test_performance_1",
                baseline_value=1.0,
            ),
            PerformanceMetric(
                metric_name="memory_usage",
                value=100.0,  # 比基准高25%
                unit="MB",
                timestamp=datetime.now(timezone.utc),
                test_name="test_performance_1",
                baseline_value=80.0,
            ),
        ]

        # 比较基准
        comparison = analyzer.compare_with_baseline(metrics, threshold=0.1)

        # 验证比较结果
        assert "regressions" in comparison
        assert "improvements" in comparison
        assert len(comparison["regressions"]) > 0  # 应该检测到回归

        # 清理
        baseline_file.unlink()
        baseline_file.parent.rmdir()


if __name__ == "__main__":
    # 运行测试报告分析
    pytest.main([__file__, "-v", "-m", "reporting", "--tb=short"])
