#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
负载测试模块
测试03ScanPulse在高并发和大数据量场景下的性能表现
包括：高并发扫描测试、大数据量处理测试、内存泄漏检测、网络延迟超时处理
"""

import pytest
import asyncio
import time
import psutil
import gc
import threading
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import weakref
import tracemalloc

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.detectors.black_horse_detector import BlackHorseDetector
from scanner.detectors.potential_finder import PotentialFinder
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.main import ScannerApplication
from scanner.core.data_processor import DataProcessor


class LoadTestMetrics:
    """负载测试指标收集器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_snapshots = []
        self.cpu_snapshots = []
        self.processing_times = []
        self.error_count = 0
        self.success_count = 0
        self.concurrent_tasks = 0
        self.max_concurrent_tasks = 0
        self.network_latencies = []
        self.timeout_count = 0
        self.memory_leaks = []

    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        tracemalloc.start()

    def record_task_start(self):
        """记录任务开始"""
        self.concurrent_tasks += 1
        self.max_concurrent_tasks = max(
            self.max_concurrent_tasks, self.concurrent_tasks
        )

    def record_task_end(self, success: bool, processing_time: float):
        """记录任务结束"""
        self.concurrent_tasks -= 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        self.processing_times.append(processing_time)

    def record_network_latency(self, latency: float):
        """记录网络延迟"""
        self.network_latencies.append(latency)

    def record_timeout(self):
        """记录超时"""
        self.timeout_count += 1

    def record_system_snapshot(self):
        """记录系统快照"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        self.memory_snapshots.append(
            {
                "timestamp": time.time(),
                "memory_mb": memory_mb,
                "memory_percent": process.memory_percent(),
            }
        )

        self.cpu_snapshots.append(
            {"timestamp": time.time(), "cpu_percent": cpu_percent}
        )

    def record_memory_leak_check(self):
        """记录内存泄漏检查"""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.memory_leaks.append(
                {
                    "timestamp": time.time(),
                    "current_mb": current / 1024 / 1024,
                    "peak_mb": peak / 1024 / 1024,
                }
            )

    def stop_monitoring(self):
        """停止监控"""
        self.end_time = time.time()
        if tracemalloc.is_tracing():
            tracemalloc.stop()

    def get_summary(self) -> Dict[str, Any]:
        """获取负载测试摘要"""
        total_time = self.end_time - self.start_time if self.end_time else 0
        total_tasks = self.success_count + self.error_count

        return {
            "total_time": total_time,
            "total_tasks": total_tasks,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / total_tasks if total_tasks > 0 else 0,
            "throughput": total_tasks / total_time if total_time > 0 else 0,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "avg_processing_time": statistics.mean(self.processing_times)
            if self.processing_times
            else 0,
            "p95_processing_time": statistics.quantiles(self.processing_times, n=20)[18]
            if len(self.processing_times) >= 20
            else 0,
            "p99_processing_time": statistics.quantiles(self.processing_times, n=100)[
                98
            ]
            if len(self.processing_times) >= 100
            else 0,
            "avg_memory_mb": statistics.mean(
                [s["memory_mb"] for s in self.memory_snapshots]
            )
            if self.memory_snapshots
            else 0,
            "max_memory_mb": max([s["memory_mb"] for s in self.memory_snapshots])
            if self.memory_snapshots
            else 0,
            "avg_cpu_percent": statistics.mean(
                [s["cpu_percent"] for s in self.cpu_snapshots]
            )
            if self.cpu_snapshots
            else 0,
            "max_cpu_percent": max([s["cpu_percent"] for s in self.cpu_snapshots])
            if self.cpu_snapshots
            else 0,
            "avg_network_latency": statistics.mean(self.network_latencies)
            if self.network_latencies
            else 0,
            "timeout_count": self.timeout_count,
            "memory_leak_detected": len(self.memory_leaks) > 1
            and self.memory_leaks[-1]["current_mb"]
            > self.memory_leaks[0]["current_mb"] * 1.5,
        }


class LoadTestDataGenerator:
    """负载测试数据生成器"""

    @staticmethod
    def generate_market_data_batch(
        count: int, base_timestamp: datetime = None
    ) -> List[Dict[str, Any]]:
        """生成批量市场数据"""
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        data_batch = []
        for i in range(count):
            symbol = f"LOAD{i:06d}USDT"
            price = random.uniform(0.001, 1000.0)
            volume = random.uniform(100000, 10000000)
            change_24h = random.uniform(-0.5, 0.5)

            data_batch.append(
                {
                    "symbol": symbol,
                    "price": price,
                    "volume": volume,
                    "change_24h": change_24h,
                    "high_24h": price * (1 + abs(change_24h) * 0.5),
                    "low_24h": price * (1 - abs(change_24h) * 0.5),
                    "market_cap": price * random.uniform(1000000, 1000000000),
                    "timestamp": (base_timestamp + timedelta(seconds=i)).isoformat(),
                    "technical_indicators": {
                        "rsi": random.uniform(0, 100),
                        "volatility": random.uniform(0.01, 0.5),
                        "volume_sma": volume * random.uniform(0.8, 1.2),
                        "price_sma_20": price * random.uniform(0.95, 1.05),
                        "bollinger_upper": price * 1.1,
                        "bollinger_lower": price * 0.9,
                    },
                    "order_book": {
                        "bids": [[price * 0.999, volume * 0.1] for _ in range(5)],
                        "asks": [[price * 1.001, volume * 0.1] for _ in range(5)],
                    },
                }
            )

        return data_batch

    @staticmethod
    def generate_stress_data(count: int) -> List[Dict[str, Any]]:
        """生成压力测试数据（包含异常情况）"""
        data_batch = LoadTestDataGenerator.generate_market_data_batch(count)

        # 添加一些异常数据
        for i in range(0, count, 100):
            if i < len(data_batch):
                # 极端价格
                data_batch[i]["price"] = random.choice([0.0000001, 999999.99])
                # 极端成交量
                data_batch[i]["volume"] = random.choice([0, 999999999999])
                # 缺失字段
                if random.random() < 0.1:
                    del data_batch[i]["technical_indicators"]

        return data_batch


class TestLoadTests:
    """负载测试类"""

    @pytest.fixture
    def load_test_config(self):
        """负载测试配置"""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "socket_timeout": 5,
                "key_prefix": "load_test",
                "default_ttl": 300,
                "max_connections": 100,
            },
            "zmq": {
                "pub_port": 15559,
                "rep_port": 15560,
                "context_io_threads": 8,
                "socket_linger": 1000,
                "heartbeat_interval": 5,
                "max_sockets": 1000,
            },
            "scanner": {
                "scan_interval": 0.1,
                "batch_size": 100,
                "max_workers": 16,
                "timeout": 30,
                "max_concurrent_scans": 1000,
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

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_high_concurrency_scanning(self, load_test_config):
        """测试高并发扫描（1000+并发）"""
        metrics = LoadTestMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data.return_value = []
        mock_redis.set_scan_result = AsyncMock(return_value=True)

        engine = ThreeHighEngine(
            mock_redis, load_test_config["scanner"]["rules"]["three_high"]
        )

        # 生成大量测试数据
        test_data = LoadTestDataGenerator.generate_market_data_batch(1500)

        metrics.start_monitoring()

        # 创建1000+并发任务
        semaphore = asyncio.Semaphore(1200)  # 限制最大并发数

        async def process_single_item(data):
            async with semaphore:
                metrics.record_task_start()
                start_time = time.time()

                try:
                    # 模拟网络延迟
                    await asyncio.sleep(random.uniform(0.001, 0.01))

                    result = await engine.analyze(data["symbol"], data)
                    await mock_redis.set_scan_result(data["symbol"], result)

                    end_time = time.time()
                    metrics.record_task_end(True, end_time - start_time)

                except asyncio.TimeoutError:
                    metrics.record_timeout()
                    metrics.record_task_end(False, time.time() - start_time)
                except Exception as e:
                    metrics.record_task_end(False, time.time() - start_time)

        # 启动所有并发任务
        tasks = [process_single_item(data) for data in test_data]

        # 监控任务执行
        monitor_task = asyncio.create_task(
            self._monitor_system_during_load(metrics, 30)
        )

        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
        monitor_task.cancel()

        metrics.stop_monitoring()
        summary = metrics.get_summary()

        # 高并发性能断言
        assert summary["success_rate"] > 0.95, f"成功率过低: {summary['success_rate']:.2%}"
        assert (
            summary["max_concurrent_tasks"] >= 1000
        ), f"最大并发数不足: {summary['max_concurrent_tasks']}"
        assert (
            summary["throughput"] > 500
        ), f"吞吐量过低: {summary['throughput']:.2f} tasks/sec"
        assert (
            summary["p95_processing_time"] < 0.1
        ), f"P95处理时间过长: {summary['p95_processing_time']:.3f}s"
        assert (
            summary["max_memory_mb"] < 1000
        ), f"内存使用过高: {summary['max_memory_mb']:.2f}MB"

        print(f"高并发扫描测试结果: {summary}")

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_large_data_volume_processing(self, load_test_config):
        """测试大数据量处理（10000+交易对）"""
        metrics = LoadTestMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data.return_value = []
        mock_redis.set_scan_result = AsyncMock(return_value=True)
        mock_redis.get_scan_result = AsyncMock(return_value={})

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.publish_scan_result = AsyncMock()

        # 创建数据处理器
        data_processor = DataProcessor(mock_redis)

        # 生成大量测试数据（10000+交易对）
        large_dataset = LoadTestDataGenerator.generate_market_data_batch(12000)

        metrics.start_monitoring()

        # 分批处理大数据集
        batch_size = 500
        processed_count = 0

        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i : i + batch_size]

            start_time = time.time()

            try:
                # 并行处理批次
                tasks = []
                for data in batch:
                    metrics.record_task_start()
                    task = data_processor.process_market_data(data)
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 统计结果
                for result in results:
                    if isinstance(result, Exception):
                        metrics.record_task_end(False, 0)
                    else:
                        metrics.record_task_end(True, 0)
                        processed_count += 1

                end_time = time.time()
                metrics.record_processing_time(end_time - start_time)

                # 每1000个项目记录系统状态
                if processed_count % 1000 == 0:
                    metrics.record_system_snapshot()
                    metrics.record_memory_leak_check()

                    # 强制垃圾回收
                    gc.collect()

            except Exception as e:
                print(f"批次处理失败: {e}")
                for _ in batch:
                    metrics.record_task_end(False, 0)

        metrics.stop_monitoring()
        summary = metrics.get_summary()

        # 大数据量处理断言
        assert summary["total_tasks"] >= 10000, f"处理数据量不足: {summary['total_tasks']}"
        assert summary["success_rate"] > 0.98, f"成功率过低: {summary['success_rate']:.2%}"
        assert summary["total_time"] < 120, f"处理时间过长: {summary['total_time']:.2f}s"
        assert (
            summary["throughput"] > 100
        ), f"吞吐量过低: {summary['throughput']:.2f} items/sec"
        assert not summary["memory_leak_detected"], "检测到内存泄漏"

        print(f"大数据量处理测试结果: {summary}")

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, load_test_config):
        """测试内存泄漏检测"""
        metrics = LoadTestMetrics()

        # 创建真实组件进行内存泄漏测试
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data.return_value = []

        engines = {
            "three_high": ThreeHighEngine(
                mock_redis, load_test_config["scanner"]["rules"]["three_high"]
            ),
            "black_horse": BlackHorseDetector(
                mock_redis, load_test_config["scanner"]["rules"]["black_horse"]
            ),
            "potential_finder": PotentialFinder(
                mock_redis, load_test_config["scanner"]["rules"]["potential_finder"]
            ),
        }

        metrics.start_monitoring()

        # 记录初始内存状态
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        metrics.record_memory_leak_check()

        # 运行多轮内存密集型操作
        for round_num in range(20):
            print(f"内存泄漏测试轮次: {round_num + 1}/20")

            # 生成测试数据
            test_data = LoadTestDataGenerator.generate_market_data_batch(200)

            # 处理数据
            for data in test_data:
                for engine_name, engine in engines.items():
                    try:
                        if engine_name == "three_high":
                            await engine.analyze(data["symbol"], data)
                        elif engine_name == "black_horse":
                            await engine.detect(data["symbol"], data)
                        elif engine_name == "potential_finder":
                            await engine.find_potential(data["symbol"], data)
                    except Exception:
                        pass  # 忽略处理错误，专注内存测试

            # 强制垃圾回收
            gc.collect()

            # 记录内存状态
            metrics.record_memory_leak_check()
            metrics.record_system_snapshot()

            # 每5轮检查一次内存趋势
            if (round_num + 1) % 5 == 0:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                print(f"轮次 {round_num + 1}: 内存增长 {memory_growth:.2f}MB")

                # 如果内存增长过快，提前结束测试
                if memory_growth > 500:  # 500MB
                    print("检测到严重内存泄漏，提前结束测试")
                    break

        metrics.stop_monitoring()
        summary = metrics.get_summary()

        # 内存泄漏检测断言
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory

        assert total_memory_growth < 200, f"内存增长过多: {total_memory_growth:.2f}MB"
        assert not summary["memory_leak_detected"], "检测到内存泄漏模式"
        assert (
            summary["max_memory_mb"] < initial_memory + 300
        ), f"峰值内存使用过高: {summary['max_memory_mb']:.2f}MB"

        print(
            f"内存泄漏检测结果: 初始={initial_memory:.2f}MB, 最终={final_memory:.2f}MB, 增长={total_memory_growth:.2f}MB"
        )
        print(f"内存泄漏测试摘要: {summary}")

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_network_latency_timeout_handling(self, load_test_config):
        """测试网络延迟和超时处理"""
        metrics = LoadTestMetrics()

        # 创建模拟组件，模拟网络延迟和超时
        class NetworkSimulatedRedisClient:
            def __init__(self, base_latency=0.01, timeout_rate=0.05):
                self.base_latency = base_latency
                self.timeout_rate = timeout_rate

            async def get_historical_data(self, symbol):
                # 模拟网络延迟
                latency = random.uniform(self.base_latency, self.base_latency * 10)
                metrics.record_network_latency(latency)

                # 模拟超时
                if random.random() < self.timeout_rate:
                    await asyncio.sleep(5)  # 模拟超时
                    raise asyncio.TimeoutError("Network timeout")

                await asyncio.sleep(latency)
                return []

            async def set_scan_result(self, symbol, result):
                latency = random.uniform(self.base_latency, self.base_latency * 5)
                metrics.record_network_latency(latency)

                if random.random() < self.timeout_rate:
                    await asyncio.sleep(5)
                    raise asyncio.TimeoutError("Network timeout")

                await asyncio.sleep(latency)
                return True

        # 创建网络模拟客户端
        network_redis = NetworkSimulatedRedisClient(base_latency=0.02, timeout_rate=0.1)

        engine = ThreeHighEngine(
            network_redis, load_test_config["scanner"]["rules"]["three_high"]
        )

        # 生成测试数据
        test_data = LoadTestDataGenerator.generate_market_data_batch(500)

        metrics.start_monitoring()

        # 测试网络延迟和超时处理
        async def process_with_timeout(data, timeout=3.0):
            metrics.record_task_start()
            start_time = time.time()

            try:
                # 使用超时控制
                result = await asyncio.wait_for(
                    engine.analyze(data["symbol"], data), timeout=timeout
                )

                # 尝试保存结果（也可能超时）
                await asyncio.wait_for(
                    network_redis.set_scan_result(data["symbol"], result),
                    timeout=timeout,
                )

                end_time = time.time()
                metrics.record_task_end(True, end_time - start_time)

            except asyncio.TimeoutError:
                metrics.record_timeout()
                metrics.record_task_end(False, time.time() - start_time)
            except Exception as e:
                metrics.record_task_end(False, time.time() - start_time)

        # 并发执行任务
        tasks = [process_with_timeout(data) for data in test_data]

        # 监控系统状态
        monitor_task = asyncio.create_task(
            self._monitor_system_during_load(metrics, 20)
        )

        await asyncio.gather(*tasks, return_exceptions=True)
        monitor_task.cancel()

        metrics.stop_monitoring()
        summary = metrics.get_summary()

        # 网络延迟和超时处理断言
        assert (
            summary["success_rate"] > 0.85
        ), f"成功率过低（考虑网络问题）: {summary['success_rate']:.2%}"
        assert summary["timeout_count"] > 0, "应该有一些超时发生（测试网络模拟）"
        assert summary["avg_network_latency"] > 0, "应该记录到网络延迟"
        assert summary["total_time"] < 60, f"总处理时间过长: {summary['total_time']:.2f}s"

        timeout_rate = summary["timeout_count"] / summary["total_tasks"]
        assert timeout_rate < 0.2, f"超时率过高: {timeout_rate:.2%}"

        print(f"网络延迟和超时处理测试结果: {summary}")
        print(f"平均网络延迟: {summary['avg_network_latency']:.3f}s")
        print(f"超时率: {timeout_rate:.2%}")

    async def _monitor_system_during_load(
        self, metrics: LoadTestMetrics, duration: int
    ):
        """在负载测试期间监控系统状态"""
        end_time = time.time() + duration

        while time.time() < end_time:
            try:
                metrics.record_system_snapshot()
                await asyncio.sleep(1)  # 每秒记录一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"系统监控错误: {e}")
                break


if __name__ == "__main__":
    # 运行负载测试
    pytest.main([__file__, "-v", "-m", "load", "--tb=short"])
