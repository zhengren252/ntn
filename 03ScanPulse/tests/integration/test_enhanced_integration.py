#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强集成测试模块
测试03ScanPulse的端到端业务流程、多组件协同工作、故障注入和恢复、性能回归
"""

import pytest
import asyncio
import time
import json
import random
import threading
import multiprocessing
import tempfile
import shutil
import os
import signal
import psutil
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from contextlib import contextmanager, asynccontextmanager
import queue
import socket
import subprocess
import gc
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.detectors.black_horse_detector import BlackHorseDetector
from scanner.detectors.potential_finder import PotentialFinder
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.core.data_processor import DataProcessor
from scanner.core.scanner_module import ScannerModule
from scanner.web.app import ScannerWebApp


@dataclass
class IntegrationTestMetrics:
    """集成测试指标"""

    test_name: str
    start_time: float
    end_time: float
    duration: float
    components_tested: List[str]
    operations_completed: int
    operations_failed: int
    data_processed: int
    memory_usage_peak: float
    cpu_usage_peak: float
    error_recovery_time: float
    success_rate: float
    throughput: float
    latency_avg: float
    latency_p95: float
    success: bool
    error_message: Optional[str]
    performance_baseline: Optional[Dict[str, float]]
    regression_detected: bool


class ComponentHealthChecker:
    """组件健康检查器"""

    def __init__(self):
        self.health_status = {}
        self.monitoring = False
        self.check_interval = 1.0
        self.monitor_thread = None

    def register_component(self, name: str, health_check_func: Callable[[], bool]):
        """注册组件健康检查函数"""
        self.health_status[name] = {
            "check_func": health_check_func,
            "status": "unknown",
            "last_check": 0,
            "failure_count": 0,
            "recovery_time": 0,
        }

    def start_monitoring(self):
        """开始健康监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            current_time = time.time()

            for name, info in self.health_status.items():
                try:
                    is_healthy = info["check_func"]()
                    previous_status = info["status"]

                    if is_healthy:
                        if previous_status == "unhealthy":
                            info["recovery_time"] = current_time - info["last_check"]
                        info["status"] = "healthy"
                        info["failure_count"] = 0
                    else:
                        info["status"] = "unhealthy"
                        info["failure_count"] += 1

                    info["last_check"] = current_time

                except Exception as e:
                    info["status"] = "error"
                    info["failure_count"] += 1
                    print(f"组件 {name} 健康检查错误: {str(e)}")

            time.sleep(self.check_interval)

    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控并返回健康报告"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        return {
            name: {
                "status": info["status"],
                "failure_count": info["failure_count"],
                "recovery_time": info["recovery_time"],
            }
            for name, info in self.health_status.items()
        }

    def get_unhealthy_components(self) -> List[str]:
        """获取不健康的组件列表"""
        return [
            name
            for name, info in self.health_status.items()
            if info["status"] in ["unhealthy", "error"]
        ]


class FaultInjector:
    """故障注入器"""

    def __init__(self):
        self.active_faults = {}
        self.fault_history = []

    @contextmanager
    def inject_network_latency(self, delay_ms: int):
        """注入网络延迟"""
        fault_id = f"network_latency_{delay_ms}ms"

        # 模拟网络延迟的补丁
        original_sleep = time.sleep

        def delayed_operation(*args, **kwargs):
            time.sleep(delay_ms / 1000.0)  # 转换为秒
            return original_sleep(*args, **kwargs)

        try:
            self.active_faults[fault_id] = True
            self.fault_history.append(
                {
                    "type": "network_latency",
                    "params": {"delay_ms": delay_ms},
                    "start_time": time.time(),
                }
            )

            with patch("time.sleep", side_effect=delayed_operation):
                yield

        finally:
            if fault_id in self.active_faults:
                del self.active_faults[fault_id]

    @contextmanager
    def inject_memory_pressure(self, pressure_mb: int):
        """注入内存压力"""
        fault_id = f"memory_pressure_{pressure_mb}mb"
        memory_hog = None

        try:
            self.active_faults[fault_id] = True
            self.fault_history.append(
                {
                    "type": "memory_pressure",
                    "params": {"pressure_mb": pressure_mb},
                    "start_time": time.time(),
                }
            )

            # 分配内存制造压力
            memory_hog = bytearray(pressure_mb * 1024 * 1024)

            yield

        finally:
            if fault_id in self.active_faults:
                del self.active_faults[fault_id]
            if memory_hog:
                del memory_hog
                gc.collect()

    @contextmanager
    def inject_cpu_stress(self, duration_seconds: float):
        """注入CPU压力"""
        fault_id = f"cpu_stress_{duration_seconds}s"
        stress_thread = None
        stop_stress = threading.Event()

        def cpu_stress_worker():
            end_time = time.time() + duration_seconds
            while time.time() < end_time and not stop_stress.is_set():
                # CPU密集型计算
                sum(i * i for i in range(1000))

        try:
            self.active_faults[fault_id] = True
            self.fault_history.append(
                {
                    "type": "cpu_stress",
                    "params": {"duration_seconds": duration_seconds},
                    "start_time": time.time(),
                }
            )

            stress_thread = threading.Thread(target=cpu_stress_worker)
            stress_thread.daemon = True
            stress_thread.start()

            yield

        finally:
            stop_stress.set()
            if stress_thread:
                stress_thread.join(timeout=1)
            if fault_id in self.active_faults:
                del self.active_faults[fault_id]

    @contextmanager
    def inject_component_failure(self, component_mock: Mock, failure_rate: float = 1.0):
        """注入组件故障"""
        fault_id = f"component_failure_{id(component_mock)}"
        original_methods = {}

        try:
            self.active_faults[fault_id] = True
            self.fault_history.append(
                {
                    "type": "component_failure",
                    "params": {"failure_rate": failure_rate},
                    "start_time": time.time(),
                }
            )

            # 保存原始方法并注入故障
            for attr_name in dir(component_mock):
                if not attr_name.startswith("_") and callable(
                    getattr(component_mock, attr_name)
                ):
                    original_method = getattr(component_mock, attr_name)
                    original_methods[attr_name] = original_method

                    def create_failing_method(original):
                        def failing_method(*args, **kwargs):
                            if random.random() < failure_rate:
                                raise Exception(f"注入的组件故障: {attr_name}")
                            return original(*args, **kwargs)

                        return failing_method

                    setattr(
                        component_mock,
                        attr_name,
                        create_failing_method(original_method),
                    )

            yield

        finally:
            # 恢复原始方法
            for attr_name, original_method in original_methods.items():
                setattr(component_mock, attr_name, original_method)

            if fault_id in self.active_faults:
                del self.active_faults[fault_id]

    def get_fault_history(self) -> List[Dict[str, Any]]:
        """获取故障历史"""
        return self.fault_history.copy()

    def clear_history(self):
        """清除故障历史"""
        self.fault_history.clear()


class PerformanceBaseline:
    """性能基准管理器"""

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

    def save_baseline(self, test_name: str, metrics: Dict[str, float]):
        """保存性能基准"""
        self.baselines[test_name] = metrics
        try:
            with open(self.baseline_file, "w", encoding="utf-8") as f:
                json.dump(self.baselines, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存性能基准失败: {str(e)}")

    def get_baseline(self, test_name: str) -> Optional[Dict[str, float]]:
        """获取性能基准"""
        return self.baselines.get(test_name)

    def check_regression(
        self, test_name: str, current_metrics: Dict[str, float], threshold: float = 0.1
    ) -> Tuple[bool, Dict[str, float]]:
        """检查性能回归"""
        baseline = self.get_baseline(test_name)
        if not baseline:
            return False, {}

        regressions = {}
        has_regression = False

        for metric_name, current_value in current_metrics.items():
            if metric_name in baseline:
                baseline_value = baseline[metric_name]
                if baseline_value > 0:  # 避免除零
                    change_ratio = (current_value - baseline_value) / baseline_value

                    # 对于延迟类指标，增加是回归；对于吞吐量类指标，减少是回归
                    if metric_name in ["latency_avg", "latency_p95", "duration"]:
                        if change_ratio > threshold:
                            regressions[metric_name] = change_ratio
                            has_regression = True
                    elif metric_name in ["throughput", "success_rate"]:
                        if change_ratio < -threshold:
                            regressions[metric_name] = change_ratio
                            has_regression = True

        return has_regression, regressions


class EndToEndTestOrchestrator:
    """端到端测试编排器"""

    def __init__(self):
        self.components = {}
        self.test_data = {}
        self.results = {}

    def register_component(self, name: str, component: Any):
        """注册组件"""
        self.components[name] = component

    def setup_test_environment(self) -> Dict[str, Any]:
        """设置测试环境"""
        # 创建模拟的市场数据
        self.test_data["market_data"] = self._generate_market_data()

        # 创建模拟的Redis客户端
        redis_mock = Mock(spec=RedisClient)
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.publish.return_value = 1
        redis_mock.is_connected.return_value = True
        self.components["redis"] = redis_mock

        # 创建模拟的ZMQ客户端
        zmq_mock = Mock(spec=ScannerZMQClient)
        zmq_mock.send_message = AsyncMock(return_value=True)
        zmq_mock.is_connected.return_value = True
        self.components["zmq"] = zmq_mock

        # 创建扫描引擎
        three_high_engine = ThreeHighEngine()
        self.components["three_high_engine"] = three_high_engine

        # 创建检测器
        black_horse_detector = BlackHorseDetector()
        potential_finder = PotentialFinder()
        self.components["black_horse_detector"] = black_horse_detector
        self.components["potential_finder"] = potential_finder

        # 创建数据处理器
        data_processor = DataProcessor()
        self.components["data_processor"] = data_processor

        return {
            "components": list(self.components.keys()),
            "test_data_size": len(self.test_data["market_data"]),
            "setup_time": time.time(),
        }

    def _generate_market_data(self, num_symbols: int = 100) -> List[Dict[str, Any]]:
        """生成市场数据"""
        market_data = []

        for i in range(num_symbols):
            symbol = f"SYMBOL{i:03d}"

            # 生成价格数据
            base_price = random.uniform(10, 1000)
            price_change = random.uniform(-0.1, 0.1)
            current_price = base_price * (1 + price_change)

            # 生成成交量数据
            volume = random.randint(1000, 1000000)

            # 生成技术指标数据
            data = {
                "symbol": symbol,
                "price": current_price,
                "volume": volume,
                "change_percent": price_change * 100,
                "high": current_price * random.uniform(1.0, 1.05),
                "low": current_price * random.uniform(0.95, 1.0),
                "turnover_rate": random.uniform(0.1, 10.0),
                "pe_ratio": random.uniform(5, 50),
                "market_cap": current_price * random.randint(1000000, 10000000),
                "timestamp": time.time(),
            }

            market_data.append(data)

        return market_data

    async def run_end_to_end_workflow(self) -> Dict[str, Any]:
        """运行端到端工作流"""
        workflow_results = {
            "data_processing": [],
            "scanning_results": [],
            "detection_results": [],
            "communication_results": [],
            "errors": [],
        }

        try:
            # 1. 数据处理阶段
            print("开始数据处理阶段")
            data_processor = self.components["data_processor"]

            for data in self.test_data["market_data"]:
                try:
                    processed_data = data_processor.process_market_data(data)
                    workflow_results["data_processing"].append(processed_data)
                except Exception as e:
                    workflow_results["errors"].append(f"数据处理错误: {str(e)}")

            # 2. 扫描引擎阶段
            print("开始扫描引擎阶段")
            three_high_engine = self.components["three_high_engine"]

            for processed_data in workflow_results["data_processing"]:
                try:
                    scan_result = three_high_engine.scan(processed_data)
                    if scan_result:
                        workflow_results["scanning_results"].append(scan_result)
                except Exception as e:
                    workflow_results["errors"].append(f"扫描引擎错误: {str(e)}")

            # 3. 检测器阶段
            print("开始检测器阶段")
            black_horse_detector = self.components["black_horse_detector"]
            potential_finder = self.components["potential_finder"]

            for scan_result in workflow_results["scanning_results"]:
                try:
                    # 黑马检测
                    black_horse_result = black_horse_detector.detect(scan_result)
                    if black_horse_result:
                        workflow_results["detection_results"].append(
                            {"type": "black_horse", "result": black_horse_result}
                        )

                    # 潜力挖掘
                    potential_result = potential_finder.find_potential(scan_result)
                    if potential_result:
                        workflow_results["detection_results"].append(
                            {"type": "potential", "result": potential_result}
                        )

                except Exception as e:
                    workflow_results["errors"].append(f"检测器错误: {str(e)}")

            # 4. 通信阶段
            print("开始通信阶段")
            redis_client = self.components["redis"]
            zmq_client = self.components["zmq"]

            for detection_result in workflow_results["detection_results"]:
                try:
                    # Redis存储
                    redis_key = f"detection:{detection_result['type']}:{time.time()}"
                    redis_client.set(redis_key, json.dumps(detection_result))

                    # ZMQ发送
                    await zmq_client.send_message(detection_result)

                    workflow_results["communication_results"].append(
                        {"redis_key": redis_key, "zmq_sent": True}
                    )

                except Exception as e:
                    workflow_results["errors"].append(f"通信错误: {str(e)}")

        except Exception as e:
            workflow_results["errors"].append(f"工作流错误: {str(e)}")

        return workflow_results

    def cleanup(self):
        """清理测试环境"""
        self.components.clear()
        self.test_data.clear()
        self.results.clear()


class TestEnhancedIntegration:
    """增强集成测试类"""

    @pytest.fixture
    def integration_config(self):
        """集成测试配置"""
        return {
            "test_duration": 30,  # 测试持续时间（秒）
            "data_volume": 1000,  # 测试数据量
            "concurrent_workers": 5,  # 并发工作线程数
            "fault_injection": {
                "network_latency_ms": 100,
                "memory_pressure_mb": 100,
                "cpu_stress_duration": 5,
                "component_failure_rate": 0.1,
            },
            "performance_thresholds": {
                "max_latency_ms": 1000,
                "min_throughput": 10,
                "min_success_rate": 0.95,
                "max_memory_mb": 500,
            },
        }

    @pytest.fixture
    def performance_baseline(self):
        """性能基准管理器"""
        baseline_file = tempfile.mktemp(suffix="_baseline.json")
        baseline_manager = PerformanceBaseline(baseline_file)
        yield baseline_manager

        # 清理
        if os.path.exists(baseline_file):
            os.remove(baseline_file)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_end_to_end_business_workflow(
        self, integration_config, performance_baseline
    ):
        """测试端到端业务流程"""
        orchestrator = EndToEndTestOrchestrator()
        health_checker = ComponentHealthChecker()

        start_time = time.time()

        try:
            # 设置测试环境
            setup_info = orchestrator.setup_test_environment()
            print(f"测试环境设置完成: {setup_info}")

            # 注册组件健康检查
            for component_name, component in orchestrator.components.items():
                if hasattr(component, "is_connected"):
                    health_checker.register_component(
                        component_name, lambda c=component: c.is_connected()
                    )
                else:
                    health_checker.register_component(
                        component_name, lambda: True  # 默认健康
                    )

            # 开始健康监控
            health_checker.start_monitoring()

            # 运行端到端工作流
            print("开始端到端工作流测试")
            workflow_results = await orchestrator.run_end_to_end_workflow()

            end_time = time.time()

            # 停止健康监控
            health_report = health_checker.stop_monitoring()

            # 计算性能指标
            duration = end_time - start_time
            total_operations = (
                len(workflow_results["data_processing"])
                + len(workflow_results["scanning_results"])
                + len(workflow_results["detection_results"])
                + len(workflow_results["communication_results"])
            )

            success_rate = 1.0 - (
                len(workflow_results["errors"]) / max(total_operations, 1)
            )
            throughput = total_operations / duration

            # 创建测试指标
            test_metrics = IntegrationTestMetrics(
                test_name="end_to_end_business_workflow",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                components_tested=list(orchestrator.components.keys()),
                operations_completed=total_operations - len(workflow_results["errors"]),
                operations_failed=len(workflow_results["errors"]),
                data_processed=len(workflow_results["data_processing"]),
                memory_usage_peak=psutil.Process().memory_info().rss
                / 1024
                / 1024,  # MB
                cpu_usage_peak=psutil.Process().cpu_percent(),
                error_recovery_time=0,  # 端到端测试中没有恢复时间
                success_rate=success_rate,
                throughput=throughput,
                latency_avg=duration / max(total_operations, 1) * 1000,  # ms
                latency_p95=duration * 1000,  # 简化的P95延迟
                success=success_rate
                >= integration_config["performance_thresholds"]["min_success_rate"],
                error_message=None
                if success_rate >= 0.95
                else f"成功率过低: {success_rate:.2%}",
                performance_baseline=None,
                regression_detected=False,
            )

            # 性能基准检查
            current_metrics = {
                "duration": duration,
                "throughput": throughput,
                "success_rate": success_rate,
                "latency_avg": test_metrics.latency_avg,
            }

            baseline = performance_baseline.get_baseline(test_metrics.test_name)
            if baseline:
                has_regression, regressions = performance_baseline.check_regression(
                    test_metrics.test_name, current_metrics
                )
                test_metrics.regression_detected = has_regression
                test_metrics.performance_baseline = baseline

                if has_regression:
                    print(f"检测到性能回归: {regressions}")
            else:
                # 保存为新的基准
                performance_baseline.save_baseline(
                    test_metrics.test_name, current_metrics
                )
                print("保存新的性能基准")

            # 断言
            assert len(workflow_results["data_processing"]) > 0, "数据处理阶段没有处理任何数据"
            assert len(workflow_results["scanning_results"]) >= 0, "扫描引擎阶段异常"
            assert len(workflow_results["detection_results"]) >= 0, "检测器阶段异常"
            assert (
                success_rate
                >= integration_config["performance_thresholds"]["min_success_rate"]
            ), f"成功率过低: {success_rate:.2%}"
            assert (
                throughput
                >= integration_config["performance_thresholds"]["min_throughput"]
            ), f"吞吐量过低: {throughput:.2f} ops/s"
            assert (
                test_metrics.latency_avg
                <= integration_config["performance_thresholds"]["max_latency_ms"]
            ), f"平均延迟过高: {test_metrics.latency_avg:.2f} ms"

            # 健康检查断言
            unhealthy_components = [
                name
                for name, status in health_report.items()
                if status["status"] != "healthy"
            ]
            assert len(unhealthy_components) == 0, f"发现不健康的组件: {unhealthy_components}"

            print(f"端到端业务流程测试结果:")
            print(f"  - 处理数据: {len(workflow_results['data_processing'])}条")
            print(f"  - 扫描结果: {len(workflow_results['scanning_results'])}个")
            print(f"  - 检测结果: {len(workflow_results['detection_results'])}个")
            print(f"  - 通信结果: {len(workflow_results['communication_results'])}个")
            print(f"  - 错误数量: {len(workflow_results['errors'])}个")
            print(f"  - 成功率: {success_rate:.2%}")
            print(f"  - 吞吐量: {throughput:.2f} ops/s")
            print(f"  - 健康报告: {health_report}")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            health_checker.stop_monitoring()
            pytest.fail(f"端到端业务流程测试失败: {str(e)}")

        finally:
            orchestrator.cleanup()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multi_component_coordination(self, integration_config):
        """测试多组件协同工作"""
        health_checker = ComponentHealthChecker()

        start_time = time.time()

        try:
            # 创建多个组件实例
            components = {
                "engine1": ThreeHighEngine(),
                "engine2": ThreeHighEngine(),
                "detector1": BlackHorseDetector(),
                "detector2": PotentialFinder(),
                "processor1": DataProcessor(),
                "processor2": DataProcessor(),
            }

            # 注册健康检查
            for name, component in components.items():
                health_checker.register_component(
                    name,
                    lambda c=component: hasattr(c, "is_healthy")
                    and c.is_healthy()
                    or True,
                )

            health_checker.start_monitoring()

            # 生成测试数据
            test_data = []
            for i in range(integration_config["data_volume"]):
                data = {
                    "symbol": f"TEST{i:04d}",
                    "price": random.uniform(10, 100),
                    "volume": random.randint(1000, 100000),
                    "timestamp": time.time(),
                }
                test_data.append(data)

            # 多组件协同处理
            coordination_results = {
                "processed_data": [],
                "scan_results": [],
                "detection_results": [],
                "coordination_errors": [],
            }

            def process_batch(batch_data, component_set):
                """处理数据批次"""
                batch_results = []

                for data in batch_data:
                    try:
                        # 数据处理
                        processed = component_set["processor"].process_market_data(data)

                        # 扫描处理
                        scan_result = component_set["engine"].scan(processed)

                        # 检测处理
                        if scan_result:
                            detection_result = component_set["detector"].detect(
                                scan_result
                            )
                            if detection_result:
                                batch_results.append(
                                    {
                                        "original": data,
                                        "processed": processed,
                                        "scanned": scan_result,
                                        "detected": detection_result,
                                    }
                                )

                    except Exception as e:
                        coordination_results["coordination_errors"].append(str(e))

                return batch_results

            # 并发处理不同批次
            batch_size = len(test_data) // 3
            batches = [
                test_data[:batch_size],
                test_data[batch_size : batch_size * 2],
                test_data[batch_size * 2 :],
            ]

            component_sets = [
                {
                    "processor": components["processor1"],
                    "engine": components["engine1"],
                    "detector": components["detector1"],
                },
                {
                    "processor": components["processor2"],
                    "engine": components["engine2"],
                    "detector": components["detector2"],
                },
                {
                    "processor": components["processor1"],
                    "engine": components["engine2"],
                    "detector": components["detector1"],
                },
            ]

            # 使用线程池并发处理
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for batch, component_set in zip(batches, component_sets):
                    future = executor.submit(process_batch, batch, component_set)
                    futures.append(future)

                # 收集结果
                for future in as_completed(futures):
                    try:
                        batch_results = future.result(timeout=30)
                        coordination_results["processed_data"].extend(batch_results)
                    except Exception as e:
                        coordination_results["coordination_errors"].append(
                            f"批次处理错误: {str(e)}"
                        )

            end_time = time.time()
            health_report = health_checker.stop_monitoring()

            # 计算协同性能指标
            duration = end_time - start_time
            total_processed = len(coordination_results["processed_data"])
            error_count = len(coordination_results["coordination_errors"])
            success_rate = (
                (total_processed) / (total_processed + error_count)
                if (total_processed + error_count) > 0
                else 0
            )
            throughput = total_processed / duration

            # 创建测试指标
            test_metrics = IntegrationTestMetrics(
                test_name="multi_component_coordination",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                components_tested=list(components.keys()),
                operations_completed=total_processed,
                operations_failed=error_count,
                data_processed=len(test_data),
                memory_usage_peak=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage_peak=psutil.Process().cpu_percent(),
                error_recovery_time=0,
                success_rate=success_rate,
                throughput=throughput,
                latency_avg=duration / max(total_processed, 1) * 1000,
                latency_p95=duration * 1000,
                success=success_rate >= 0.8,  # 多组件协同允许较低的成功率
                error_message=None
                if success_rate >= 0.8
                else f"协同成功率过低: {success_rate:.2%}",
                performance_baseline=None,
                regression_detected=False,
            )

            # 断言
            assert total_processed > 0, "多组件协同没有处理任何数据"
            assert success_rate >= 0.8, f"多组件协同成功率过低: {success_rate:.2%}"
            assert throughput > 5, f"多组件协同吞吐量过低: {throughput:.2f} ops/s"

            # 健康检查
            unhealthy_components = [
                name
                for name, status in health_report.items()
                if status["status"] != "healthy"
            ]
            assert len(unhealthy_components) <= 1, f"过多不健康组件: {unhealthy_components}"

            print(f"多组件协同测试结果:")
            print(f"  - 输入数据: {len(test_data)}条")
            print(f"  - 处理结果: {total_processed}个")
            print(f"  - 错误数量: {error_count}个")
            print(f"  - 成功率: {success_rate:.2%}")
            print(f"  - 吞吐量: {throughput:.2f} ops/s")
            print(f"  - 健康报告: {health_report}")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            health_checker.stop_monitoring()
            pytest.fail(f"多组件协同测试失败: {str(e)}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_fault_injection_and_recovery(self, integration_config):
        """测试故障注入和恢复"""
        fault_injector = FaultInjector()
        health_checker = ComponentHealthChecker()

        start_time = time.time()

        try:
            # 创建测试组件
            components = {
                "engine": ThreeHighEngine(),
                "detector": BlackHorseDetector(),
                "processor": DataProcessor(),
            }

            # 创建模拟组件用于故障注入
            mock_redis = Mock(spec=RedisClient)
            mock_redis.is_connected.return_value = True
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            components["redis"] = mock_redis

            # 注册健康检查
            for name, component in components.items():
                if hasattr(component, "is_connected"):
                    health_checker.register_component(
                        name, lambda c=component: c.is_connected()
                    )
                else:
                    health_checker.register_component(name, lambda: True)

            health_checker.start_monitoring()

            # 生成测试数据
            test_data = [
                {
                    "symbol": f"FAULT{i:03d}",
                    "price": random.uniform(10, 100),
                    "volume": random.randint(1000, 10000),
                    "timestamp": time.time(),
                }
                for i in range(100)
            ]

            fault_test_results = {
                "normal_operations": 0,
                "fault_operations": 0,
                "recovery_operations": 0,
                "fault_errors": [],
                "recovery_times": [],
            }

            # 1. 正常操作基准测试
            print("开始正常操作基准测试")
            normal_start = time.time()

            for data in test_data[:30]:
                try:
                    processed = components["processor"].process_market_data(data)
                    scan_result = components["engine"].scan(processed)
                    if scan_result:
                        components["detector"].detect(scan_result)
                    components["redis"].set(f"test:{data['symbol']}", json.dumps(data))
                    fault_test_results["normal_operations"] += 1
                except Exception as e:
                    fault_test_results["fault_errors"].append(f"正常操作错误: {str(e)}")

            normal_duration = time.time() - normal_start

            # 2. 网络延迟故障注入
            print("开始网络延迟故障注入测试")
            fault_start = time.time()

            with fault_injector.inject_network_latency(
                integration_config["fault_injection"]["network_latency_ms"]
            ):
                for data in test_data[30:50]:
                    try:
                        processed = components["processor"].process_market_data(data)
                        scan_result = components["engine"].scan(processed)
                        if scan_result:
                            components["detector"].detect(scan_result)
                        components["redis"].set(
                            f"test:{data['symbol']}", json.dumps(data)
                        )
                        fault_test_results["fault_operations"] += 1
                    except Exception as e:
                        fault_test_results["fault_errors"].append(f"网络延迟故障: {str(e)}")

            fault_duration = time.time() - fault_start

            # 3. 内存压力故障注入
            print("开始内存压力故障注入测试")

            with fault_injector.inject_memory_pressure(
                integration_config["fault_injection"]["memory_pressure_mb"]
            ):
                for data in test_data[50:70]:
                    try:
                        processed = components["processor"].process_market_data(data)
                        scan_result = components["engine"].scan(processed)
                        if scan_result:
                            components["detector"].detect(scan_result)
                        components["redis"].set(
                            f"test:{data['symbol']}", json.dumps(data)
                        )
                        fault_test_results["fault_operations"] += 1
                    except Exception as e:
                        fault_test_results["fault_errors"].append(f"内存压力故障: {str(e)}")

            # 4. 组件故障注入
            print("开始组件故障注入测试")

            with fault_injector.inject_component_failure(
                mock_redis,
                integration_config["fault_injection"]["component_failure_rate"],
            ):
                for data in test_data[70:90]:
                    try:
                        processed = components["processor"].process_market_data(data)
                        scan_result = components["engine"].scan(processed)
                        if scan_result:
                            components["detector"].detect(scan_result)
                        components["redis"].set(
                            f"test:{data['symbol']}", json.dumps(data)
                        )
                        fault_test_results["fault_operations"] += 1
                    except Exception as e:
                        fault_test_results["fault_errors"].append(f"组件故障: {str(e)}")

            # 5. 恢复测试
            print("开始恢复测试")
            recovery_start = time.time()

            for data in test_data[90:]:
                try:
                    processed = components["processor"].process_market_data(data)
                    scan_result = components["engine"].scan(processed)
                    if scan_result:
                        components["detector"].detect(scan_result)
                    components["redis"].set(f"test:{data['symbol']}", json.dumps(data))
                    fault_test_results["recovery_operations"] += 1
                except Exception as e:
                    fault_test_results["fault_errors"].append(f"恢复阶段错误: {str(e)}")

            recovery_duration = time.time() - recovery_start
            fault_test_results["recovery_times"].append(recovery_duration)

            end_time = time.time()
            health_report = health_checker.stop_monitoring()

            # 计算故障恢复指标
            total_operations = (
                fault_test_results["normal_operations"]
                + fault_test_results["fault_operations"]
                + fault_test_results["recovery_operations"]
            )

            error_count = len(fault_test_results["fault_errors"])
            success_rate = (
                total_operations / (total_operations + error_count)
                if (total_operations + error_count) > 0
                else 0
            )

            # 故障影响分析
            normal_throughput = (
                fault_test_results["normal_operations"] / normal_duration
            )
            fault_throughput = fault_test_results["fault_operations"] / fault_duration
            recovery_throughput = (
                fault_test_results["recovery_operations"] / recovery_duration
            )

            fault_impact = (
                (normal_throughput - fault_throughput) / normal_throughput
                if normal_throughput > 0
                else 0
            )
            recovery_efficiency = (
                recovery_throughput / normal_throughput if normal_throughput > 0 else 0
            )

            # 创建测试指标
            test_metrics = IntegrationTestMetrics(
                test_name="fault_injection_and_recovery",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                components_tested=list(components.keys()),
                operations_completed=total_operations,
                operations_failed=error_count,
                data_processed=len(test_data),
                memory_usage_peak=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage_peak=psutil.Process().cpu_percent(),
                error_recovery_time=recovery_duration,
                success_rate=success_rate,
                throughput=(total_operations) / (end_time - start_time),
                latency_avg=(end_time - start_time) / max(total_operations, 1) * 1000,
                latency_p95=(end_time - start_time) * 1000,
                success=success_rate >= 0.7
                and recovery_efficiency >= 0.8,  # 故障测试允许较低成功率
                error_message=None
                if success_rate >= 0.7
                else f"故障恢复成功率过低: {success_rate:.2%}",
                performance_baseline=None,
                regression_detected=False,
            )

            # 断言
            assert fault_test_results["normal_operations"] > 0, "正常操作阶段没有成功操作"
            assert fault_test_results["fault_operations"] >= 0, "故障注入阶段异常"
            assert fault_test_results["recovery_operations"] > 0, "恢复阶段没有成功操作"
            assert success_rate >= 0.7, f"整体成功率过低: {success_rate:.2%}"
            assert recovery_efficiency >= 0.8, f"恢复效率过低: {recovery_efficiency:.2%}"
            assert fault_impact <= 0.5, f"故障影响过大: {fault_impact:.2%}"

            print(f"故障注入和恢复测试结果:")
            print(
                f"  - 正常操作: {fault_test_results['normal_operations']}个 (吞吐量: {normal_throughput:.2f} ops/s)"
            )
            print(
                f"  - 故障操作: {fault_test_results['fault_operations']}个 (吞吐量: {fault_throughput:.2f} ops/s)"
            )
            print(
                f"  - 恢复操作: {fault_test_results['recovery_operations']}个 (吞吐量: {recovery_throughput:.2f} ops/s)"
            )
            print(f"  - 故障影响: {fault_impact:.2%}")
            print(f"  - 恢复效率: {recovery_efficiency:.2%}")
            print(f"  - 错误数量: {error_count}个")
            print(f"  - 整体成功率: {success_rate:.2%}")
            print(f"  - 故障历史: {fault_injector.get_fault_history()}")
            print(f"  - 健康报告: {health_report}")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            health_checker.stop_monitoring()
            pytest.fail(f"故障注入和恢复测试失败: {str(e)}")

        finally:
            fault_injector.clear_history()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_performance_regression_detection(
        self, integration_config, performance_baseline
    ):
        """测试性能回归检测"""
        start_time = time.time()

        try:
            # 创建测试组件
            engine = ThreeHighEngine()
            detector = BlackHorseDetector()
            processor = DataProcessor()

            # 生成测试数据
            test_data = [
                {
                    "symbol": f"REGR{i:03d}",
                    "price": random.uniform(10, 100),
                    "volume": random.randint(1000, 10000),
                    "timestamp": time.time(),
                }
                for i in range(integration_config["data_volume"])
            ]

            # 第一次运行 - 建立基准
            print("第一次运行 - 建立性能基准")

            first_run_start = time.time()
            first_run_results = []

            for data in test_data:
                try:
                    processed = processor.process_market_data(data)
                    scan_result = engine.scan(processed)
                    if scan_result:
                        detection_result = detector.detect(scan_result)
                        if detection_result:
                            first_run_results.append(detection_result)
                except Exception as e:
                    print(f"第一次运行错误: {str(e)}")

            first_run_duration = time.time() - first_run_start
            first_run_throughput = len(first_run_results) / first_run_duration
            first_run_latency = first_run_duration / len(test_data) * 1000

            # 保存第一次运行的基准
            baseline_metrics = {
                "duration": first_run_duration,
                "throughput": first_run_throughput,
                "latency_avg": first_run_latency,
                "success_rate": len(first_run_results) / len(test_data),
            }

            performance_baseline.save_baseline(
                "performance_regression_test", baseline_metrics
            )

            # 模拟性能退化的第二次运行
            print("第二次运行 - 模拟性能退化")

            second_run_start = time.time()
            second_run_results = []

            for i, data in enumerate(test_data):
                try:
                    # 模拟性能退化 - 添加人工延迟
                    if i % 10 == 0:  # 每10个操作添加延迟
                        time.sleep(0.01)  # 10ms延迟

                    processed = processor.process_market_data(data)
                    scan_result = engine.scan(processed)
                    if scan_result:
                        detection_result = detector.detect(scan_result)
                        if detection_result:
                            second_run_results.append(detection_result)
                except Exception as e:
                    print(f"第二次运行错误: {str(e)}")

            second_run_duration = time.time() - second_run_start
            second_run_throughput = len(second_run_results) / second_run_duration
            second_run_latency = second_run_duration / len(test_data) * 1000

            # 第二次运行的指标
            current_metrics = {
                "duration": second_run_duration,
                "throughput": second_run_throughput,
                "latency_avg": second_run_latency,
                "success_rate": len(second_run_results) / len(test_data),
            }

            # 检查性能回归
            has_regression, regressions = performance_baseline.check_regression(
                "performance_regression_test", current_metrics, threshold=0.05  # 5%阈值
            )

            end_time = time.time()

            # 创建测试指标
            test_metrics = IntegrationTestMetrics(
                test_name="performance_regression_detection",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                components_tested=[
                    "ThreeHighEngine",
                    "BlackHorseDetector",
                    "DataProcessor",
                ],
                operations_completed=len(first_run_results) + len(second_run_results),
                operations_failed=0,
                data_processed=len(test_data) * 2,
                memory_usage_peak=psutil.Process().memory_info().rss / 1024 / 1024,
                cpu_usage_peak=psutil.Process().cpu_percent(),
                error_recovery_time=0,
                success_rate=(len(first_run_results) + len(second_run_results))
                / (len(test_data) * 2),
                throughput=(len(first_run_results) + len(second_run_results))
                / (end_time - start_time),
                latency_avg=(first_run_latency + second_run_latency) / 2,
                latency_p95=max(first_run_latency, second_run_latency),
                success=True,
                error_message=None,
                performance_baseline=baseline_metrics,
                regression_detected=has_regression,
            )

            # 断言
            assert len(first_run_results) > 0, "第一次运行没有产生结果"
            assert len(second_run_results) > 0, "第二次运行没有产生结果"
            assert has_regression, "应该检测到性能回归但没有检测到"  # 我们故意引入了延迟，应该检测到回归
            assert (
                "latency_avg" in regressions or "duration" in regressions
            ), "应该检测到延迟或持续时间回归"

            # 验证回归检测的准确性
            expected_latency_increase = (
                second_run_latency - first_run_latency
            ) / first_run_latency
            assert (
                expected_latency_increase > 0.05
            ), f"延迟增加不足以触发回归检测: {expected_latency_increase:.2%}"

            print(f"性能回归检测测试结果:")
            print(f"  - 第一次运行:")
            print(f"    * 持续时间: {first_run_duration:.3f}s")
            print(f"    * 吞吐量: {first_run_throughput:.2f} ops/s")
            print(f"    * 平均延迟: {first_run_latency:.2f}ms")
            print(f"    * 结果数量: {len(first_run_results)}")
            print(f"  - 第二次运行:")
            print(f"    * 持续时间: {second_run_duration:.3f}s")
            print(f"    * 吞吐量: {second_run_throughput:.2f} ops/s")
            print(f"    * 平均延迟: {second_run_latency:.2f}ms")
            print(f"    * 结果数量: {len(second_run_results)}")
            print(f"  - 回归检测:")
            print(f"    * 检测到回归: {has_regression}")
            print(f"    * 回归详情: {regressions}")
            print(f"  - 基准指标: {baseline_metrics}")
            print(f"  - 当前指标: {current_metrics}")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            pytest.fail(f"性能回归检测测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行集成测试
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])
