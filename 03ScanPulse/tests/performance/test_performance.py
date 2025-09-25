# 性能测试
# 测试扫描器在高负载和压力条件下的性能表现

import pytest
import asyncio
import time
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import statistics

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


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
        self.processing_times = []
        self.throughput_data = []

    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        self.memory_usage = []
        self.cpu_usage = []
        self.processing_times = []
        self.throughput_data = []

    def record_processing_time(self, processing_time):
        """记录处理时间"""
        self.processing_times.append(processing_time)

    def record_system_metrics(self):
        """记录系统指标"""
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())

    def stop_monitoring(self):
        """停止监控"""
        self.end_time = time.time()

    def get_summary(self):
        """获取性能摘要"""
        total_time = self.end_time - self.start_time if self.end_time else 0

        return {
            "total_time": total_time,
            "avg_processing_time": statistics.mean(self.processing_times)
            if self.processing_times
            else 0,
            "max_processing_time": max(self.processing_times)
            if self.processing_times
            else 0,
            "min_processing_time": min(self.processing_times)
            if self.processing_times
            else 0,
            "avg_memory_usage": statistics.mean(self.memory_usage)
            if self.memory_usage
            else 0,
            "max_memory_usage": max(self.memory_usage) if self.memory_usage else 0,
            "avg_cpu_usage": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
            "max_cpu_usage": max(self.cpu_usage) if self.cpu_usage else 0,
            "throughput": len(self.processing_times) / total_time
            if total_time > 0
            else 0,
        }


class TestPerformance:
    """性能测试类"""

    @pytest.fixture
    def performance_config(self):
        """性能测试配置"""
        return {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "socket_timeout": 1,
                "key_prefix": "perf_test",
                "default_ttl": 60,
            },
            "zmq": {
                "pub_port": 15557,
                "rep_port": 15558,
                "context_io_threads": 4,
                "socket_linger": 0,
                "heartbeat_interval": 1,
            },
            "scanner": {
                "scan_interval": 1,
                "batch_size": 50,
                "max_workers": 8,
                "timeout": 10,
            },
        }

    def generate_market_data(self, count=1000):
        """生成测试市场数据"""
        data = []
        for i in range(count):
            data.append(
                {
                    "symbol": f"TEST{i:04d}USDT",
                    "price": 100.0 + (i % 100),
                    "volume": 1000000 + i * 1000,
                    "change_24h": (i % 20 - 10) / 100,
                    "high_24h": 105.0 + (i % 100),
                    "low_24h": 95.0 + (i % 100),
                    "market_cap": 1000000000 + i * 1000000,
                    "timestamp": "2024-01-01T12:00:00Z",
                    "technical_indicators": {
                        "rsi": 50 + (i % 50),
                        "volatility": 0.01 + (i % 10) / 100,
                        "volume_sma": 800000 + i * 800,
                    },
                }
            )
        return data

    @pytest.mark.performance
    async def test_three_high_engine_performance(self, performance_config):
        """测试三高引擎性能"""
        metrics = PerformanceMetrics()

        # 创建模拟Redis客户端
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data.return_value = []

        engine = ThreeHighEngine(
            mock_redis, performance_config["scanner"]["rules"]["three_high"]
        )

        # 生成测试数据
        test_data = self.generate_market_data(1000)

        metrics.start_monitoring()

        # 批量处理测试
        for i, data in enumerate(test_data):
            start_time = time.time()

            result = await engine.analyze(data["symbol"], data)

            end_time = time.time()
            metrics.record_processing_time(end_time - start_time)

            # 每100次记录系统指标
            if i % 100 == 0:
                metrics.record_system_metrics()

        metrics.stop_monitoring()
        summary = metrics.get_summary()

        # 性能断言
        assert summary["avg_processing_time"] < 0.01  # 平均处理时间小于10ms
        assert summary["throughput"] > 100  # 每秒处理超过100个项目
        assert summary["max_memory_usage"] < 500  # 最大内存使用小于500MB

        print(f"三高引擎性能测试结果: {summary}")

    @pytest.mark.performance
    async def test_black_horse_detector_performance(self, performance_config):
        """测试黑马检测器性能"""
        metrics = PerformanceMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_news_events.return_value = []

        detector = BlackHorseDetector(
            mock_redis, performance_config["scanner"]["rules"]["black_horse"]
        )

        # 生成测试数据
        test_data = self.generate_market_data(500)

        metrics.start_monitoring()

        # 并发处理测试
        tasks = []
        for data in test_data:
            task = detector.detect(data["symbol"], data)
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        metrics.record_processing_time(end_time - start_time)
        metrics.record_system_metrics()
        metrics.stop_monitoring()

        summary = metrics.get_summary()

        # 性能断言
        assert summary["total_time"] < 5.0  # 总处理时间小于5秒
        assert len(results) == 500  # 所有项目都被处理

        print(f"黑马检测器性能测试结果: {summary}")

    @pytest.mark.performance
    async def test_potential_finder_performance(self, performance_config):
        """测试潜力挖掘器性能"""
        metrics = PerformanceMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_market_overview.return_value = {
            "total_market_cap": 2000000000000
        }

        finder = PotentialFinder(
            mock_redis, performance_config["scanner"]["rules"]["potential_finder"]
        )

        # 生成测试数据（包含一些低市值币种）
        test_data = self.generate_market_data(300)
        for i in range(0, 100, 10):
            test_data[i]["market_cap"] = 50000000  # 低市值
            test_data[i]["price"] = 0.5  # 低价格

        metrics.start_monitoring()

        # 顺序处理测试
        for data in test_data:
            start_time = time.time()

            result = await finder.find_potential(data["symbol"], data)

            end_time = time.time()
            metrics.record_processing_time(end_time - start_time)

        metrics.record_system_metrics()
        metrics.stop_monitoring()

        summary = metrics.get_summary()

        # 性能断言
        assert summary["avg_processing_time"] < 0.005  # 平均处理时间小于5ms
        assert summary["throughput"] > 200  # 每秒处理超过200个项目

        print(f"潜力挖掘器性能测试结果: {summary}")

    @pytest.mark.performance
    async def test_redis_client_performance(self, performance_config):
        """测试Redis客户端性能"""
        metrics = PerformanceMetrics()

        # 创建真实Redis客户端（如果可用）或模拟客户端
        try:
            redis_client = RedisClient(performance_config["redis"])
            await redis_client.connect()
            use_real_redis = True
        except:
            redis_client = Mock(spec=RedisClient)
            redis_client.set_scan_result.return_value = True
            redis_client.get_scan_result.return_value = {}
            use_real_redis = False

        # 生成测试数据
        test_data = self.generate_market_data(200)

        metrics.start_monitoring()

        # 写入性能测试
        for data in test_data:
            start_time = time.time()

            if use_real_redis:
                await redis_client.set_scan_result(data["symbol"], data)
            else:
                redis_client.set_scan_result(data["symbol"], data)

            end_time = time.time()
            metrics.record_processing_time(end_time - start_time)

        # 读取性能测试
        for data in test_data[:50]:  # 测试部分读取
            start_time = time.time()

            if use_real_redis:
                await redis_client.get_scan_result(data["symbol"])
            else:
                redis_client.get_scan_result(data["symbol"])

            end_time = time.time()
            metrics.record_processing_time(end_time - start_time)

        metrics.record_system_metrics()
        metrics.stop_monitoring()

        if use_real_redis:
            await redis_client.disconnect()

        summary = metrics.get_summary()

        # 性能断言
        if use_real_redis:
            assert summary["avg_processing_time"] < 0.01  # 平均操作时间小于10ms
            assert summary["throughput"] > 100  # 每秒操作超过100次

        print(f"Redis客户端性能测试结果 (real={use_real_redis}): {summary}")

    @pytest.mark.performance
    async def test_zmq_client_performance(self, performance_config):
        """测试ZMQ客户端性能"""
        metrics = PerformanceMetrics()

        # 创建模拟ZMQ客户端
        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.publish_scan_result = AsyncMock()
        mock_zmq.publish_status_update = AsyncMock()

        # 生成测试数据
        test_data = self.generate_market_data(500)

        metrics.start_monitoring()

        # 发布性能测试
        for data in test_data:
            start_time = time.time()

            await mock_zmq.publish_scan_result(data)

            end_time = time.time()
            metrics.record_processing_time(end_time - start_time)

        metrics.record_system_metrics()
        metrics.stop_monitoring()

        summary = metrics.get_summary()

        # 验证调用次数
        assert mock_zmq.publish_scan_result.call_count == 500

        print(f"ZMQ客户端性能测试结果: {summary}")

    @pytest.mark.performance
    @pytest.mark.slow
    async def test_full_pipeline_performance(self, performance_config):
        """测试完整管道性能"""
        metrics = PerformanceMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.set_scan_result.return_value = True
        mock_redis.get_historical_data.return_value = []
        mock_redis.get_news_events.return_value = []
        mock_redis.get_market_overview.return_value = {
            "total_market_cap": 2000000000000
        }

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        # 创建扫描器应用
        with patch("scanner.main.get_env_manager") as mock_env_manager:
            mock_env_manager.return_value.get_redis_config.return_value = (
                performance_config["redis"]
            )
            mock_env_manager.return_value.get_zmq_config.return_value = (
                performance_config["zmq"]
            )
            mock_env_manager.return_value.get_scanner_config.return_value = (
                performance_config["scanner"]
            )

            app = ScannerApplication()
            app.redis_client = mock_redis
            app.zmq_client = mock_zmq

            # 初始化引擎
            app.three_high_engine = ThreeHighEngine(
                mock_redis, performance_config["scanner"]["rules"]["three_high"]
            )
            app.black_horse_detector = BlackHorseDetector(
                mock_redis, performance_config["scanner"]["rules"]["black_horse"]
            )
            app.potential_finder = PotentialFinder(
                mock_redis, performance_config["scanner"]["rules"]["potential_finder"]
            )

            # 生成大量测试数据
            test_data = self.generate_market_data(1000)

            metrics.start_monitoring()

            # 分批处理
            batch_size = 50
            for i in range(0, len(test_data), batch_size):
                batch = test_data[i : i + batch_size]

                start_time = time.time()

                # 处理批次
                tasks = []
                for data in batch:
                    task = app._apply_scan_engines(data["symbol"], data)
                    tasks.append(task)

                await asyncio.gather(*tasks)

                end_time = time.time()
                metrics.record_processing_time(end_time - start_time)

                # 记录系统指标
                metrics.record_system_metrics()

                # 强制垃圾回收
                gc.collect()

            metrics.stop_monitoring()

            summary = metrics.get_summary()

            # 性能断言
            assert summary["total_time"] < 30.0  # 总处理时间小于30秒
            assert summary["throughput"] > 30  # 每秒处理超过30个项目
            assert summary["max_memory_usage"] < 1000  # 最大内存使用小于1GB

            print(f"完整管道性能测试结果: {summary}")

    @pytest.mark.performance
    async def test_memory_leak_detection(self, performance_config):
        """测试内存泄漏检测"""
        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data.return_value = []

        engine = ThreeHighEngine(
            mock_redis, performance_config["scanner"]["rules"]["three_high"]
        )

        # 记录初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_samples = [initial_memory]

        # 运行多轮处理
        for round_num in range(10):
            test_data = self.generate_market_data(100)

            for data in test_data:
                await engine.analyze(data["symbol"], data)

            # 强制垃圾回收
            gc.collect()

            # 记录内存使用
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)

        # 分析内存趋势
        memory_growth = memory_samples[-1] - memory_samples[0]
        avg_growth_per_round = memory_growth / 10

        # 内存泄漏检测
        assert memory_growth < 100  # 总内存增长小于100MB
        assert avg_growth_per_round < 10  # 每轮平均增长小于10MB

        print(
            f"内存使用情况: 初始={initial_memory:.2f}MB, 最终={memory_samples[-1]:.2f}MB, 增长={memory_growth:.2f}MB"
        )

    @pytest.mark.performance
    async def test_concurrent_load_handling(self, performance_config):
        """测试并发负载处理"""
        metrics = PerformanceMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.get_historical_data.return_value = []

        engine = ThreeHighEngine(
            mock_redis, performance_config["scanner"]["rules"]["three_high"]
        )

        # 生成测试数据
        test_data = self.generate_market_data(200)

        metrics.start_monitoring()

        # 创建多个并发任务组
        task_groups = []
        for i in range(4):  # 4个并发组
            group_data = test_data[i * 50 : (i + 1) * 50]
            group_tasks = []

            for data in group_data:
                task = engine.analyze(data["symbol"], data)
                group_tasks.append(task)

            task_groups.append(group_tasks)

        # 并发执行所有任务组
        start_time = time.time()

        all_results = await asyncio.gather(
            *[asyncio.gather(*group) for group in task_groups]
        )

        end_time = time.time()

        metrics.record_processing_time(end_time - start_time)
        metrics.record_system_metrics()
        metrics.stop_monitoring()

        summary = metrics.get_summary()

        # 验证结果
        total_results = sum(len(group_results) for group_results in all_results)
        assert total_results == 200

        # 性能断言
        assert summary["total_time"] < 5.0  # 并发处理时间小于5秒

        print(f"并发负载处理性能测试结果: {summary}")

    @pytest.mark.performance
    async def test_stress_test(self, performance_config):
        """压力测试"""
        metrics = PerformanceMetrics()

        # 创建模拟组件
        mock_redis = Mock(spec=RedisClient)
        mock_redis.connect.return_value = True
        mock_redis.set_scan_result.return_value = True
        mock_redis.get_historical_data.return_value = []

        mock_zmq = Mock(spec=ScannerZMQClient)
        mock_zmq.start.return_value = None
        mock_zmq.publish_scan_result = AsyncMock()

        # 生成大量测试数据
        test_data = self.generate_market_data(2000)

        metrics.start_monitoring()

        # 高强度处理
        batch_size = 100
        successful_batches = 0
        failed_batches = 0

        for i in range(0, len(test_data), batch_size):
            batch = test_data[i : i + batch_size]

            try:
                start_time = time.time()

                # 模拟处理批次
                for data in batch:
                    mock_redis.set_scan_result(data["symbol"], data)
                    await mock_zmq.publish_scan_result(data)

                end_time = time.time()
                metrics.record_processing_time(end_time - start_time)
                successful_batches += 1

            except Exception as e:
                failed_batches += 1
                print(f"批次处理失败: {e}")

            # 每5个批次记录系统指标
            if i % (batch_size * 5) == 0:
                metrics.record_system_metrics()

        metrics.stop_monitoring()

        summary = metrics.get_summary()

        # 压力测试断言
        success_rate = successful_batches / (successful_batches + failed_batches)
        assert success_rate > 0.95  # 成功率超过95%
        assert summary["max_memory_usage"] < 2000  # 最大内存使用小于2GB

        print(f"压力测试结果: 成功率={success_rate:.2%}, 性能={summary}")
