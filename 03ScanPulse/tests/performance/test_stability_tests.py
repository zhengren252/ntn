#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长期稳定性测试模块
测试03ScanPulse在长期运行场景下的稳定性表现
包括：24小时连续运行测试、内存使用趋势监控、错误恢复能力测试、资源清理验证测试
"""

import pytest
import asyncio
import time
import psutil
import gc
import threading
import random
import statistics
import json
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import weakref
import tracemalloc
from dataclasses import dataclass, asdict
from pathlib import Path

import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.detectors.black_horse_detector import BlackHorseDetector
from scanner.detectors.potential_finder import PotentialFinder
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.main import ScannerApplication
from scanner.core.data_processor import DataProcessor


@dataclass
class StabilitySnapshot:
    """稳定性测试快照"""

    timestamp: float
    memory_mb: float
    memory_percent: float
    cpu_percent: float
    open_files: int
    threads_count: int
    connections_count: int
    processed_items: int
    error_count: int
    gc_collections: Dict[str, int]


class StabilityTestMetrics:
    """稳定性测试指标收集器"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.snapshots: List[StabilitySnapshot] = []
        self.error_events: List[Dict[str, Any]] = []
        self.recovery_events: List[Dict[str, Any]] = []
        self.resource_leaks: List[Dict[str, Any]] = []
        self.performance_degradation: List[Dict[str, Any]] = []
        self.total_processed = 0
        self.total_errors = 0
        self.max_memory_mb = 0
        self.memory_growth_rate = 0
        self.is_monitoring = False
        self.monitor_task = None

    def start_monitoring(self, interval: float = 10.0):
        """开始监控"""
        self.start_time = time.time()
        self.is_monitoring = True
        tracemalloc.start()

        # 启动后台监控任务
        self.monitor_task = asyncio.create_task(self._background_monitor(interval))

    async def _background_monitor(self, interval: float):
        """后台监控任务"""
        while self.is_monitoring:
            try:
                self.record_snapshot()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.record_error("monitor", str(e))

    def record_snapshot(self):
        """记录系统快照"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            # 获取GC统计信息
            gc_stats = {f"gen_{i}": gc.get_count()[i] for i in range(3)}

            snapshot = StabilitySnapshot(
                timestamp=time.time(),
                memory_mb=memory_info.rss / 1024 / 1024,
                memory_percent=process.memory_percent(),
                cpu_percent=process.cpu_percent(),
                open_files=len(process.open_files()),
                threads_count=process.num_threads(),
                connections_count=len(process.connections()),
                processed_items=self.total_processed,
                error_count=self.total_errors,
                gc_collections=gc_stats,
            )

            self.snapshots.append(snapshot)

            # 更新最大内存使用
            self.max_memory_mb = max(self.max_memory_mb, snapshot.memory_mb)

            # 检测内存增长趋势
            if len(self.snapshots) >= 10:
                recent_memory = [s.memory_mb for s in self.snapshots[-10:]]
                self.memory_growth_rate = (recent_memory[-1] - recent_memory[0]) / 10

                # 检测内存泄漏
                if self.memory_growth_rate > 5:  # 每次快照增长超过5MB
                    self.resource_leaks.append(
                        {
                            "type": "memory_leak",
                            "timestamp": snapshot.timestamp,
                            "growth_rate": self.memory_growth_rate,
                            "current_memory": snapshot.memory_mb,
                        }
                    )

        except Exception as e:
            self.record_error("snapshot", str(e))

    def record_error(self, component: str, error_msg: str, recoverable: bool = True):
        """记录错误事件"""
        self.total_errors += 1
        error_event = {
            "timestamp": time.time(),
            "component": component,
            "error": error_msg,
            "recoverable": recoverable,
            "total_errors": self.total_errors,
        }
        self.error_events.append(error_event)

    def record_recovery(self, component: str, recovery_time: float, success: bool):
        """记录恢复事件"""
        recovery_event = {
            "timestamp": time.time(),
            "component": component,
            "recovery_time": recovery_time,
            "success": success,
        }
        self.recovery_events.append(recovery_event)

    def record_processed_items(self, count: int):
        """记录处理项目数"""
        self.total_processed += count

    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.end_time = time.time()

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        if tracemalloc.is_tracing():
            tracemalloc.stop()

    def get_stability_summary(self) -> Dict[str, Any]:
        """获取稳定性测试摘要"""
        total_time = self.end_time - self.start_time if self.end_time else 0

        # 计算内存统计
        memory_values = [s.memory_mb for s in self.snapshots]
        cpu_values = [s.cpu_percent for s in self.snapshots]

        # 计算错误率
        error_rate = (
            self.total_errors / self.total_processed if self.total_processed > 0 else 0
        )

        # 计算恢复成功率
        recovery_success_rate = 0
        if self.recovery_events:
            successful_recoveries = sum(1 for r in self.recovery_events if r["success"])
            recovery_success_rate = successful_recoveries / len(self.recovery_events)

        return {
            "test_name": self.test_name,
            "total_time_hours": total_time / 3600,
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "error_rate": error_rate,
            "snapshots_count": len(self.snapshots),
            "memory_stats": {
                "initial_mb": memory_values[0] if memory_values else 0,
                "final_mb": memory_values[-1] if memory_values else 0,
                "max_mb": max(memory_values) if memory_values else 0,
                "avg_mb": statistics.mean(memory_values) if memory_values else 0,
                "growth_rate_mb_per_snapshot": self.memory_growth_rate,
            },
            "cpu_stats": {
                "avg_percent": statistics.mean(cpu_values) if cpu_values else 0,
                "max_percent": max(cpu_values) if cpu_values else 0,
            },
            "resource_leaks_count": len(self.resource_leaks),
            "recovery_success_rate": recovery_success_rate,
            "stability_score": self._calculate_stability_score(),
        }

    def _calculate_stability_score(self) -> float:
        """计算稳定性评分（0-100）"""
        score = 100.0

        # 错误率影响
        if self.total_processed > 0:
            error_rate = self.total_errors / self.total_processed
            score -= error_rate * 50  # 错误率每1%扣0.5分

        # 内存泄漏影响
        score -= len(self.resource_leaks) * 10  # 每个内存泄漏扣10分

        # 恢复能力影响
        if self.recovery_events:
            failed_recoveries = sum(1 for r in self.recovery_events if not r["success"])
            score -= failed_recoveries * 5  # 每个恢复失败扣5分

        return max(0, score)

    def save_report(self, output_dir: str):
        """保存稳定性测试报告"""
        os.makedirs(output_dir, exist_ok=True)

        # 保存摘要报告
        summary = self.get_stability_summary()
        with open(f"{output_dir}/stability_summary_{self.test_name}.json", "w") as f:
            json.dump(summary, f, indent=2)

        # 保存详细快照数据
        snapshots_data = [asdict(s) for s in self.snapshots]
        with open(f"{output_dir}/stability_snapshots_{self.test_name}.json", "w") as f:
            json.dump(snapshots_data, f, indent=2)

        # 保存错误事件
        with open(f"{output_dir}/stability_errors_{self.test_name}.json", "w") as f:
            json.dump(self.error_events, f, indent=2)


class StabilityTestRunner:
    """稳定性测试运行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.components = {}
        self.is_running = False

    async def setup_components(self):
        """设置测试组件"""
        # 创建模拟Redis客户端
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data = AsyncMock(return_value=[])
        mock_redis.set_scan_result = AsyncMock(return_value=True)
        mock_redis.get_scan_result = AsyncMock(return_value={})

        # 创建模拟ZMQ客户端
        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.publish_scan_result = AsyncMock()
        mock_zmq.publish_status_update = AsyncMock()

        # 创建扫描引擎
        self.components = {
            "redis": mock_redis,
            "zmq": mock_zmq,
            "three_high_engine": ThreeHighEngine(
                mock_redis, self.config["scanner"]["rules"]["three_high"]
            ),
            "black_horse_detector": BlackHorseDetector(
                mock_redis, self.config["scanner"]["rules"]["black_horse"]
            ),
            "potential_finder": PotentialFinder(
                mock_redis, self.config["scanner"]["rules"]["potential_finder"]
            ),
            "data_processor": DataProcessor(mock_redis),
        }

    def generate_continuous_data_stream(self, duration_hours: float):
        """生成连续数据流"""
        end_time = time.time() + (duration_hours * 3600)

        while time.time() < end_time and self.is_running:
            # 生成一批市场数据
            batch_size = random.randint(10, 50)
            data_batch = []

            for i in range(batch_size):
                symbol = f"STAB{random.randint(1, 1000):04d}USDT"
                data_batch.append(
                    {
                        "symbol": symbol,
                        "price": random.uniform(0.01, 1000.0),
                        "volume": random.uniform(100000, 10000000),
                        "change_24h": random.uniform(-0.3, 0.3),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "technical_indicators": {
                            "rsi": random.uniform(0, 100),
                            "volatility": random.uniform(0.01, 0.5),
                        },
                    }
                )

            yield data_batch

            # 随机间隔
            time.sleep(random.uniform(0.1, 2.0))

    async def simulate_error_scenarios(self, metrics: StabilityTestMetrics):
        """模拟错误场景"""
        error_scenarios = [
            ("redis_connection_lost", 0.02),
            ("zmq_publish_failed", 0.03),
            ("data_processing_error", 0.05),
            ("memory_pressure", 0.01),
            ("network_timeout", 0.04),
        ]

        while self.is_running:
            await asyncio.sleep(random.uniform(30, 120))  # 30-120秒间隔

            # 随机选择错误场景
            scenario, probability = random.choice(error_scenarios)

            if random.random() < probability:
                await self._inject_error(scenario, metrics)

    async def _inject_error(self, scenario: str, metrics: StabilityTestMetrics):
        """注入错误"""
        recovery_start = time.time()

        try:
            if scenario == "redis_connection_lost":
                # 模拟Redis连接丢失
                self.components[
                    "redis"
                ].get_historical_data.side_effect = ConnectionError(
                    "Redis connection lost"
                )
                metrics.record_error("redis", "Connection lost", True)

                # 模拟恢复
                await asyncio.sleep(random.uniform(1, 5))
                self.components["redis"].get_historical_data.side_effect = None

            elif scenario == "zmq_publish_failed":
                # 模拟ZMQ发布失败
                self.components["zmq"].publish_scan_result.side_effect = Exception(
                    "ZMQ publish failed"
                )
                metrics.record_error("zmq", "Publish failed", True)

                # 模拟恢复
                await asyncio.sleep(random.uniform(0.5, 2))
                self.components["zmq"].publish_scan_result.side_effect = None

            elif scenario == "memory_pressure":
                # 模拟内存压力
                large_data = [random.random() for _ in range(1000000)]  # 创建大量数据
                metrics.record_error("system", "Memory pressure", True)

                # 清理内存
                del large_data
                gc.collect()

            recovery_time = time.time() - recovery_start
            metrics.record_recovery(scenario, recovery_time, True)

        except Exception as e:
            recovery_time = time.time() - recovery_start
            metrics.record_recovery(scenario, recovery_time, False)
            metrics.record_error(scenario, f"Recovery failed: {str(e)}", False)


class TestStabilityTests:
    """稳定性测试类"""

    @pytest.fixture
    def stability_config(self):
        """稳定性测试配置"""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "socket_timeout": 10,
                "key_prefix": "stability_test",
                "default_ttl": 3600,
            },
            "zmq": {
                "pub_port": 15561,
                "rep_port": 15562,
                "context_io_threads": 4,
                "socket_linger": 5000,
                "heartbeat_interval": 10,
            },
            "scanner": {
                "scan_interval": 1,
                "batch_size": 20,
                "max_workers": 4,
                "timeout": 30,
                "rules": {
                    "three_high": {
                        "price_threshold": 100,
                        "volume_threshold": 1000000,
                        "market_cap_threshold": 100000000,
                    },
                    "black_horse": {
                        "volume_spike_threshold": 5.0,
                        "price_change_threshold": 0.2,
                    },
                    "potential_finder": {
                        "market_cap_threshold": 50000000,
                        "volume_threshold": 500000,
                    },
                },
            },
        }

    @pytest.mark.stability
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_24_hour_continuous_operation(self, stability_config):
        """测试24小时连续运行（实际运行1小时作为演示）"""
        # 注意：实际24小时测试应该在专门的测试环境中运行
        # 这里使用1小时作为演示
        test_duration_hours = 1.0  # 实际应该是24.0

        metrics = StabilityTestMetrics("24h_continuous")
        runner = StabilityTestRunner(stability_config)

        await runner.setup_components()
        runner.is_running = True

        metrics.start_monitoring(interval=30.0)  # 每30秒记录一次

        try:
            # 启动错误注入任务
            error_task = asyncio.create_task(runner.simulate_error_scenarios(metrics))

            # 连续处理数据流
            data_stream = runner.generate_continuous_data_stream(test_duration_hours)

            for batch in data_stream:
                try:
                    # 处理数据批次
                    tasks = []
                    for data in batch:
                        # 随机选择处理引擎
                        engine_choice = random.choice(
                            ["three_high", "black_horse", "potential_finder"]
                        )

                        if engine_choice == "three_high":
                            task = runner.components["three_high_engine"].analyze(
                                data["symbol"], data
                            )
                        elif engine_choice == "black_horse":
                            task = runner.components["black_horse_detector"].detect(
                                data["symbol"], data
                            )
                        else:
                            task = runner.components["potential_finder"].find_potential(
                                data["symbol"], data
                            )

                        tasks.append(task)

                    # 等待批次完成
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # 统计结果
                    success_count = sum(
                        1 for r in results if not isinstance(r, Exception)
                    )
                    error_count = len(results) - success_count

                    metrics.record_processed_items(success_count)

                    if error_count > 0:
                        metrics.record_error(
                            "batch_processing", f"{error_count} items failed", True
                        )

                    # 定期垃圾回收
                    if metrics.total_processed % 1000 == 0:
                        gc.collect()

                except Exception as e:
                    metrics.record_error("data_stream", str(e), True)

            error_task.cancel()

        finally:
            runner.is_running = False
            await metrics.stop_monitoring()

        summary = metrics.get_stability_summary()

        # 24小时连续运行断言
        assert (
            summary["total_processed"] > 1000
        ), f"处理数据量不足: {summary['total_processed']}"
        assert summary["error_rate"] < 0.05, f"错误率过高: {summary['error_rate']:.2%}"
        assert (
            summary["stability_score"] > 80
        ), f"稳定性评分过低: {summary['stability_score']:.1f}"
        assert summary["memory_stats"]["growth_rate_mb_per_snapshot"] < 10, "内存增长率过高"
        assert summary["resource_leaks_count"] == 0, "检测到资源泄漏"

        # 保存测试报告
        metrics.save_report("stability_test_reports")

        print(f"24小时连续运行测试结果: {summary}")

    @pytest.mark.stability
    @pytest.mark.asyncio
    async def test_memory_usage_trend_monitoring(self, stability_config):
        """测试内存使用趋势监控"""
        metrics = StabilityTestMetrics("memory_trend")
        runner = StabilityTestRunner(stability_config)

        await runner.setup_components()
        runner.is_running = True

        metrics.start_monitoring(interval=5.0)  # 每5秒记录一次

        try:
            # 运行内存密集型操作
            for cycle in range(60):  # 5分钟测试
                print(f"内存趋势监控周期: {cycle + 1}/60")

                # 创建一些数据处理任务
                data_batch = [
                    {
                        "symbol": f"MEM{i:04d}USDT",
                        "price": random.uniform(1, 100),
                        "volume": random.uniform(100000, 1000000),
                        "change_24h": random.uniform(-0.1, 0.1),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    for i in range(100)
                ]

                # 处理数据
                tasks = []
                for data in data_batch:
                    task = runner.components["three_high_engine"].analyze(
                        data["symbol"], data
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)
                metrics.record_processed_items(
                    len([r for r in results if not isinstance(r, Exception)])
                )

                # 每10个周期强制垃圾回收
                if cycle % 10 == 0:
                    gc.collect()

                await asyncio.sleep(5)  # 等待5秒

        finally:
            runner.is_running = False
            await metrics.stop_monitoring()

        summary = metrics.get_stability_summary()

        # 内存趋势监控断言
        assert len(metrics.snapshots) >= 50, "快照数量不足"
        assert summary["memory_stats"]["growth_rate_mb_per_snapshot"] < 5, "内存增长率过高"

        # 检查内存使用模式
        memory_values = [s.memory_mb for s in metrics.snapshots]
        memory_variance = (
            statistics.variance(memory_values) if len(memory_values) > 1 else 0
        )
        assert memory_variance < 10000, "内存使用波动过大"

        print(f"内存使用趋势监控结果: {summary}")
        print(f"内存方差: {memory_variance:.2f}")

    @pytest.mark.stability
    @pytest.mark.asyncio
    async def test_error_recovery_capability(self, stability_config):
        """测试错误恢复能力"""
        metrics = StabilityTestMetrics("error_recovery")
        runner = StabilityTestRunner(stability_config)

        await runner.setup_components()
        runner.is_running = True

        metrics.start_monitoring(interval=10.0)

        try:
            # 主动注入各种错误并测试恢复
            error_scenarios = [
                "redis_connection_lost",
                "zmq_publish_failed",
                "data_processing_error",
                "memory_pressure",
                "network_timeout",
            ]

            for scenario in error_scenarios:
                print(f"测试错误恢复场景: {scenario}")

                # 注入错误
                await runner._inject_error(scenario, metrics)

                # 继续正常处理以测试恢复
                for i in range(10):
                    data = {
                        "symbol": f"REC{i:04d}USDT",
                        "price": random.uniform(1, 100),
                        "volume": random.uniform(100000, 1000000),
                        "change_24h": random.uniform(-0.1, 0.1),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    try:
                        result = await runner.components["three_high_engine"].analyze(
                            data["symbol"], data
                        )
                        metrics.record_processed_items(1)
                    except Exception as e:
                        metrics.record_error("recovery_test", str(e), True)

                await asyncio.sleep(2)

        finally:
            runner.is_running = False
            await metrics.stop_monitoring()

        summary = metrics.get_stability_summary()

        # 错误恢复能力断言
        assert len(metrics.recovery_events) >= 5, "恢复事件数量不足"
        assert (
            summary["recovery_success_rate"] > 0.8
        ), f"恢复成功率过低: {summary['recovery_success_rate']:.2%}"
        assert summary["total_processed"] > 0, "恢复后未能正常处理数据"

        print(f"错误恢复能力测试结果: {summary}")
        print(f"恢复事件: {len(metrics.recovery_events)}")

    @pytest.mark.stability
    @pytest.mark.asyncio
    async def test_resource_cleanup_verification(self, stability_config):
        """测试资源清理验证"""
        metrics = StabilityTestMetrics("resource_cleanup")
        runner = StabilityTestRunner(stability_config)

        # 记录初始资源状态
        initial_process = psutil.Process()
        initial_memory = initial_process.memory_info().rss / 1024 / 1024
        initial_threads = initial_process.num_threads()
        initial_files = len(initial_process.open_files())

        await runner.setup_components()
        runner.is_running = True

        metrics.start_monitoring(interval=5.0)

        try:
            # 运行多轮资源密集型操作
            for round_num in range(20):
                print(f"资源清理验证轮次: {round_num + 1}/20")

                # 创建大量临时对象
                temp_objects = []
                for i in range(1000):
                    data = {
                        "symbol": f"CLEAN{i:04d}USDT",
                        "price": random.uniform(1, 100),
                        "volume": random.uniform(100000, 1000000),
                        "large_data": [random.random() for _ in range(1000)],  # 大量数据
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    temp_objects.append(data)

                # 处理数据
                tasks = []
                for data in temp_objects[:100]:  # 只处理前100个
                    task = runner.components["data_processor"].process_market_data(data)
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                metrics.record_processed_items(success_count)

                # 清理临时对象
                del temp_objects

                # 强制垃圾回收
                collected = gc.collect()
                print(f"轮次 {round_num + 1}: 垃圾回收清理了 {collected} 个对象")

                # 记录资源状态
                current_process = psutil.Process()
                current_memory = current_process.memory_info().rss / 1024 / 1024
                current_threads = current_process.num_threads()
                current_files = len(current_process.open_files())

                print(
                    f"内存: {current_memory:.2f}MB (+{current_memory - initial_memory:.2f}MB)"
                )
                print(f"线程: {current_threads} (+{current_threads - initial_threads})")
                print(f"文件: {current_files} (+{current_files - initial_files})")

                await asyncio.sleep(1)

        finally:
            runner.is_running = False
            await metrics.stop_monitoring()

        # 最终资源状态检查
        final_process = psutil.Process()
        final_memory = final_process.memory_info().rss / 1024 / 1024
        final_threads = final_process.num_threads()
        final_files = len(final_process.open_files())

        summary = metrics.get_stability_summary()

        # 资源清理验证断言
        memory_growth = final_memory - initial_memory
        thread_growth = final_threads - initial_threads
        file_growth = final_files - initial_files

        assert memory_growth < 100, f"内存增长过多: {memory_growth:.2f}MB"
        assert thread_growth <= 5, f"线程增长过多: {thread_growth}"
        assert file_growth <= 10, f"文件句柄增长过多: {file_growth}"
        assert summary["resource_leaks_count"] == 0, "检测到资源泄漏"

        print(f"资源清理验证结果: {summary}")
        print(
            f"资源变化 - 内存: +{memory_growth:.2f}MB, 线程: +{thread_growth}, 文件: +{file_growth}"
        )


if __name__ == "__main__":
    # 运行稳定性测试
    pytest.main([__file__, "-v", "-m", "stability", "--tb=short"])
