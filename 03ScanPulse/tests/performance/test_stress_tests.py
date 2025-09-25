#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力测试模块
测试03ScanPulse在极限负载下的性能表现
包括：CPU密集型操作测试、磁盘I/O压力测试、网络带宽压力测试、数据库连接池压力测试
"""

import pytest
import asyncio
import time
import os
import tempfile
import shutil
import threading
import multiprocessing
import psutil
import json
import random
import string
import hashlib
import gzip
import pickle
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import queue
import socket
import select
from contextlib import contextmanager
import gc
import signal

# Windows兼容性处理
try:
    import resource
except ImportError:
    # Windows上resource模块不可用，创建一个模拟版本
    class MockResource:
        RLIMIT_NOFILE = 7
        RLIMIT_AS = 9

        @staticmethod
        def getrlimit(resource_type):
            return (1024, 1024)  # 返回默认值

        @staticmethod
        def setrlimit(resource_type, limits):
            pass  # 在Windows上不执行任何操作

    resource = MockResource()

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


@dataclass
class StressTestMetrics:
    """压力测试指标"""

    test_name: str
    start_time: float
    end_time: float
    duration: float
    cpu_usage_max: float
    cpu_usage_avg: float
    memory_usage_max: float
    memory_usage_avg: float
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int
    operations_completed: int
    operations_failed: int
    throughput: float
    error_rate: float
    success: bool
    error_message: Optional[str]


class SystemResourceMonitor:
    """系统资源监控器"""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.monitoring = False
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_io": [],
            "network_io": [],
            "timestamps": [],
        }
        self.monitor_thread = None

    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_io": [],
            "network_io": [],
            "timestamps": [],
        }
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()

    def _monitor_loop(self):
        """监控循环"""
        process = psutil.Process()

        while self.monitoring:
            try:
                timestamp = time.time()

                # CPU使用率
                cpu_percent = process.cpu_percent()

                # 内存使用率
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()

                # 磁盘I/O
                disk_io = (
                    process.io_counters() if hasattr(process, "io_counters") else None
                )

                # 网络I/O（系统级别）
                net_io = psutil.net_io_counters()

                self.metrics["timestamps"].append(timestamp)
                self.metrics["cpu_usage"].append(cpu_percent)
                self.metrics["memory_usage"].append(memory_percent)

                if disk_io:
                    self.metrics["disk_io"].append(
                        {
                            "read_bytes": disk_io.read_bytes,
                            "write_bytes": disk_io.write_bytes,
                            "read_count": disk_io.read_count,
                            "write_count": disk_io.write_count,
                        }
                    )

                if net_io:
                    self.metrics["network_io"].append(
                        {
                            "bytes_sent": net_io.bytes_sent,
                            "bytes_recv": net_io.bytes_recv,
                            "packets_sent": net_io.packets_sent,
                            "packets_recv": net_io.packets_recv,
                        }
                    )

                time.sleep(self.interval)

            except Exception as e:
                print(f"监控错误: {str(e)}")
                time.sleep(self.interval)

    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控并返回统计信息"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        return self._calculate_statistics()

    def _calculate_statistics(self) -> Dict[str, Any]:
        """计算统计信息"""
        stats = {
            "duration": 0,
            "cpu_max": 0,
            "cpu_avg": 0,
            "memory_max": 0,
            "memory_avg": 0,
            "disk_read_total": 0,
            "disk_write_total": 0,
            "network_sent_total": 0,
            "network_recv_total": 0,
        }

        if self.metrics["timestamps"]:
            stats["duration"] = (
                self.metrics["timestamps"][-1] - self.metrics["timestamps"][0]
            )

        if self.metrics["cpu_usage"]:
            stats["cpu_max"] = max(self.metrics["cpu_usage"])
            stats["cpu_avg"] = sum(self.metrics["cpu_usage"]) / len(
                self.metrics["cpu_usage"]
            )

        if self.metrics["memory_usage"]:
            stats["memory_max"] = max(self.metrics["memory_usage"])
            stats["memory_avg"] = sum(self.metrics["memory_usage"]) / len(
                self.metrics["memory_usage"]
            )

        if self.metrics["disk_io"]:
            first_disk = self.metrics["disk_io"][0]
            last_disk = self.metrics["disk_io"][-1]
            stats["disk_read_total"] = (
                last_disk["read_bytes"] - first_disk["read_bytes"]
            )
            stats["disk_write_total"] = (
                last_disk["write_bytes"] - first_disk["write_bytes"]
            )

        if self.metrics["network_io"]:
            first_net = self.metrics["network_io"][0]
            last_net = self.metrics["network_io"][-1]
            stats["network_sent_total"] = (
                last_net["bytes_sent"] - first_net["bytes_sent"]
            )
            stats["network_recv_total"] = (
                last_net["bytes_recv"] - first_net["bytes_recv"]
            )

        return stats


class CPUStressGenerator:
    """CPU压力生成器"""

    @staticmethod
    def cpu_intensive_calculation(iterations: int = 1000000) -> float:
        """CPU密集型计算"""
        result = 0.0
        for i in range(iterations):
            result += (i**0.5) * (i**0.3) / (i + 1)
            if i % 10000 == 0:
                # 模拟复杂计算
                temp = hashlib.sha256(str(result).encode()).hexdigest()
                result += len(temp)
        return result

    @staticmethod
    def parallel_cpu_stress(
        num_processes: int, iterations_per_process: int
    ) -> List[float]:
        """并行CPU压力测试"""
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = []
            for _ in range(num_processes):
                future = executor.submit(
                    CPUStressGenerator.cpu_intensive_calculation, iterations_per_process
                )
                futures.append(future)

            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    print(f"CPU压力测试进程错误: {str(e)}")
                    results.append(0.0)

            return results

    @staticmethod
    def memory_intensive_operation(size_mb: int = 100) -> bool:
        """内存密集型操作"""
        try:
            # 创建大量数据
            data_size = size_mb * 1024 * 1024  # 转换为字节
            large_data = bytearray(data_size)

            # 填充随机数据
            for i in range(0, data_size, 1024):
                chunk = os.urandom(min(1024, data_size - i))
                large_data[i : i + len(chunk)] = chunk

            # 数据处理
            compressed = gzip.compress(large_data)
            decompressed = gzip.decompress(compressed)

            # 验证数据完整性
            return len(decompressed) == len(large_data)

        except Exception as e:
            print(f"内存密集型操作错误: {str(e)}")
            return False
        finally:
            # 强制垃圾回收
            gc.collect()


class DiskIOStressGenerator:
    """磁盘I/O压力生成器"""

    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.test_files = []

    def create_test_files(self, num_files: int, file_size_mb: int) -> List[str]:
        """创建测试文件"""
        file_paths = []

        for i in range(num_files):
            file_path = os.path.join(self.temp_dir, f"test_file_{i}.dat")

            # 创建指定大小的文件
            with open(file_path, "wb") as f:
                chunk_size = 1024 * 1024  # 1MB chunks
                remaining = file_size_mb * chunk_size

                while remaining > 0:
                    chunk = os.urandom(min(chunk_size, remaining))
                    f.write(chunk)
                    remaining -= len(chunk)

            file_paths.append(file_path)
            self.test_files.append(file_path)

        return file_paths

    def sequential_read_test(self, file_paths: List[str]) -> Tuple[float, int]:
        """顺序读取测试"""
        start_time = time.time()
        total_bytes = 0

        for file_path in file_paths:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    total_bytes += len(chunk)

        duration = time.time() - start_time
        return duration, total_bytes

    def random_read_test(
        self, file_paths: List[str], num_operations: int
    ) -> Tuple[float, int]:
        """随机读取测试"""
        start_time = time.time()
        total_bytes = 0

        for _ in range(num_operations):
            file_path = random.choice(file_paths)
            file_size = os.path.getsize(file_path)

            if file_size > 0:
                # 随机位置读取
                position = random.randint(0, max(0, file_size - 1024))
                read_size = min(1024, file_size - position)

                with open(file_path, "rb") as f:
                    f.seek(position)
                    chunk = f.read(read_size)
                    total_bytes += len(chunk)

        duration = time.time() - start_time
        return duration, total_bytes

    def write_stress_test(
        self, num_files: int, operations_per_file: int
    ) -> Tuple[float, int]:
        """写入压力测试"""
        start_time = time.time()
        total_bytes = 0

        for i in range(num_files):
            file_path = os.path.join(self.temp_dir, f"write_test_{i}.dat")
            self.test_files.append(file_path)

            with open(file_path, "wb") as f:
                for j in range(operations_per_file):
                    # 写入随机数据
                    data_size = random.randint(1024, 10240)  # 1KB to 10KB
                    data = os.urandom(data_size)
                    f.write(data)
                    total_bytes += len(data)

                    # 偶尔同步到磁盘
                    if j % 100 == 0:
                        f.flush()
                        os.fsync(f.fileno())

        duration = time.time() - start_time
        return duration, total_bytes

    def cleanup(self):
        """清理测试文件"""
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"清理文件失败 {file_path}: {str(e)}")
        self.test_files.clear()


class NetworkStressGenerator:
    """网络压力生成器"""

    def __init__(self):
        self.servers = []
        self.clients = []

    def create_echo_server(self, port: int) -> threading.Thread:
        """创建回显服务器"""

        def server_loop():
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                server_socket.bind(("localhost", port))
                server_socket.listen(10)
                server_socket.settimeout(1.0)

                self.servers.append(server_socket)

                while True:
                    try:
                        client_socket, addr = server_socket.accept()
                        client_thread = threading.Thread(
                            target=self._handle_client, args=(client_socket,)
                        )
                        client_thread.daemon = True
                        client_thread.start()

                    except socket.timeout:
                        continue
                    except Exception:
                        break

            except Exception as e:
                print(f"服务器错误: {str(e)}")
            finally:
                server_socket.close()

        server_thread = threading.Thread(target=server_loop)
        server_thread.daemon = True
        server_thread.start()

        # 等待服务器启动
        time.sleep(0.1)
        return server_thread

    def _handle_client(self, client_socket: socket.socket):
        """处理客户端连接"""
        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                client_socket.send(data)  # 回显数据
        except Exception:
            pass
        finally:
            client_socket.close()

    def network_throughput_test(
        self, host: str, port: int, num_connections: int, data_size: int
    ) -> Tuple[float, int, int]:
        """网络吞吐量测试"""
        start_time = time.time()
        total_sent = 0
        total_received = 0
        successful_connections = 0

        def client_worker():
            nonlocal total_sent, total_received, successful_connections

            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(10.0)
                client_socket.connect((host, port))

                # 发送数据
                test_data = os.urandom(data_size)
                client_socket.send(test_data)
                total_sent += len(test_data)

                # 接收回显数据
                received_data = b""
                while len(received_data) < data_size:
                    chunk = client_socket.recv(
                        min(1024, data_size - len(received_data))
                    )
                    if not chunk:
                        break
                    received_data += chunk

                total_received += len(received_data)
                successful_connections += 1

                client_socket.close()

            except Exception as e:
                print(f"客户端连接错误: {str(e)}")

        # 并发客户端连接
        threads = []
        for _ in range(num_connections):
            thread = threading.Thread(target=client_worker)
            thread.start()
            threads.append(thread)

        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)

        duration = time.time() - start_time
        return duration, total_sent, total_received

    def cleanup(self):
        """清理网络资源"""
        for server in self.servers:
            try:
                server.close()
            except Exception:
                pass
        self.servers.clear()


class DatabaseConnectionPoolStress:
    """数据库连接池压力测试"""

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections = []
        self.connection_pool = queue.Queue(maxsize=max_connections)
        self.connection_stats = {"created": 0, "destroyed": 0, "active": 0, "errors": 0}

    def create_mock_connection(self) -> Mock:
        """创建模拟数据库连接"""
        connection = Mock()
        connection.execute = Mock(return_value=True)
        connection.fetchall = Mock(return_value=[])
        connection.commit = Mock()
        connection.rollback = Mock()
        connection.close = Mock()
        connection.is_connected = True

        self.connection_stats["created"] += 1
        return connection

    def get_connection(self) -> Optional[Mock]:
        """获取连接"""
        try:
            if not self.connection_pool.empty():
                connection = self.connection_pool.get_nowait()
                self.connection_stats["active"] += 1
                return connection
            elif len(self.active_connections) < self.max_connections:
                connection = self.create_mock_connection()
                self.active_connections.append(connection)
                self.connection_stats["active"] += 1
                return connection
            else:
                return None  # 连接池已满

        except Exception as e:
            self.connection_stats["errors"] += 1
            print(f"获取连接错误: {str(e)}")
            return None

    def return_connection(self, connection: Mock):
        """归还连接"""
        try:
            if connection and connection.is_connected:
                self.connection_pool.put_nowait(connection)
                self.connection_stats["active"] -= 1
            else:
                self._destroy_connection(connection)

        except queue.Full:
            self._destroy_connection(connection)
        except Exception as e:
            self.connection_stats["errors"] += 1
            print(f"归还连接错误: {str(e)}")

    def _destroy_connection(self, connection: Mock):
        """销毁连接"""
        try:
            if connection in self.active_connections:
                self.active_connections.remove(connection)
            connection.close()
            connection.is_connected = False
            self.connection_stats["destroyed"] += 1
            self.connection_stats["active"] -= 1
        except Exception as e:
            print(f"销毁连接错误: {str(e)}")

    def stress_test(
        self, num_workers: int, operations_per_worker: int
    ) -> Dict[str, Any]:
        """连接池压力测试"""
        start_time = time.time()
        results = {
            "successful_operations": 0,
            "failed_operations": 0,
            "connection_timeouts": 0,
            "total_operations": num_workers * operations_per_worker,
        }

        def worker():
            for _ in range(operations_per_worker):
                connection = None
                try:
                    # 获取连接
                    connection = self.get_connection()
                    if connection is None:
                        results["connection_timeouts"] += 1
                        continue

                    # 模拟数据库操作
                    connection.execute("SELECT * FROM test_table")
                    connection.fetchall()
                    connection.commit()

                    # 模拟处理时间
                    time.sleep(random.uniform(0.001, 0.01))

                    results["successful_operations"] += 1

                except Exception as e:
                    results["failed_operations"] += 1
                    print(f"数据库操作错误: {str(e)}")

                finally:
                    if connection:
                        self.return_connection(connection)

        # 启动工作线程
        threads = []
        for _ in range(num_workers):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        results["duration"] = time.time() - start_time
        results["connection_stats"] = self.connection_stats.copy()

        return results

    def cleanup(self):
        """清理连接池"""
        # 清空连接池
        while not self.connection_pool.empty():
            try:
                connection = self.connection_pool.get_nowait()
                self._destroy_connection(connection)
            except queue.Empty:
                break

        # 销毁活跃连接
        for connection in self.active_connections.copy():
            self._destroy_connection(connection)


class TestStressTests:
    """压力测试类"""

    @pytest.fixture
    def stress_config(self):
        """压力测试配置"""
        return {
            "cpu_stress": {
                "num_processes": multiprocessing.cpu_count(),
                "iterations_per_process": 500000,
                "memory_size_mb": 50,
            },
            "disk_stress": {
                "num_files": 10,
                "file_size_mb": 10,
                "num_operations": 1000,
            },
            "network_stress": {
                "num_connections": 50,
                "data_size": 1024 * 10,  # 10KB
                "server_port": 9999,
            },
            "database_stress": {
                "max_connections": 50,
                "num_workers": 20,
                "operations_per_worker": 100,
            },
        }

    @pytest.mark.stress
    @pytest.mark.slow
    def test_cpu_intensive_operations(self, stress_config):
        """测试CPU密集型操作"""
        monitor = SystemResourceMonitor()
        monitor.start_monitoring()

        start_time = time.time()

        try:
            config = stress_config["cpu_stress"]

            # CPU密集型计算测试
            print(f"开始CPU密集型计算测试: {config['num_processes']}进程")

            results = CPUStressGenerator.parallel_cpu_stress(
                config["num_processes"], config["iterations_per_process"]
            )

            # 内存密集型操作测试
            print(f"开始内存密集型操作测试: {config['memory_size_mb']}MB")

            memory_results = []
            for i in range(5):  # 5次内存操作
                result = CPUStressGenerator.memory_intensive_operation(
                    config["memory_size_mb"]
                )
                memory_results.append(result)

            end_time = time.time()

            # 停止监控
            stats = monitor.stop_monitoring()

            # 创建测试指标
            test_metrics = StressTestMetrics(
                test_name="cpu_intensive_operations",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                cpu_usage_max=stats["cpu_max"],
                cpu_usage_avg=stats["cpu_avg"],
                memory_usage_max=stats["memory_max"],
                memory_usage_avg=stats["memory_avg"],
                disk_io_read=stats["disk_read_total"],
                disk_io_write=stats["disk_write_total"],
                network_bytes_sent=stats["network_sent_total"],
                network_bytes_recv=stats["network_recv_total"],
                operations_completed=len([r for r in results if r > 0])
                + sum(memory_results),
                operations_failed=len([r for r in results if r == 0])
                + (5 - sum(memory_results)),
                throughput=len(results) / (end_time - start_time),
                error_rate=(len([r for r in results if r == 0])) / len(results),
                success=True,
                error_message=None,
            )

            # 断言
            assert (
                len(results) == config["num_processes"]
            ), f"CPU测试进程数不匹配: {len(results)} != {config['num_processes']}"
            assert all(r > 0 for r in results), "CPU密集型计算失败"
            assert all(memory_results), "内存密集型操作失败"
            assert (
                test_metrics.cpu_usage_max > 50
            ), f"CPU使用率过低: {test_metrics.cpu_usage_max}%"
            assert (
                test_metrics.memory_usage_max > 30
            ), f"内存使用率过低: {test_metrics.memory_usage_max}%"
            assert (
                test_metrics.error_rate < 0.1
            ), f"错误率过高: {test_metrics.error_rate:.2%}"

            print(f"CPU压力测试结果: {asdict(test_metrics)}")

        except Exception as e:
            monitor.stop_monitoring()
            pytest.fail(f"CPU压力测试失败: {str(e)}")

    @pytest.mark.stress
    @pytest.mark.slow
    def test_disk_io_pressure(self, stress_config):
        """测试磁盘I/O压力"""
        monitor = SystemResourceMonitor()
        temp_dir = tempfile.mkdtemp(prefix="scanpulse_disk_stress_")
        disk_stress = DiskIOStressGenerator(temp_dir)

        monitor.start_monitoring()
        start_time = time.time()

        try:
            config = stress_config["disk_stress"]

            # 创建测试文件
            print(f"创建测试文件: {config['num_files']}个文件，每个{config['file_size_mb']}MB")
            test_files = disk_stress.create_test_files(
                config["num_files"], config["file_size_mb"]
            )

            # 顺序读取测试
            print("开始顺序读取测试")
            seq_duration, seq_bytes = disk_stress.sequential_read_test(test_files)

            # 随机读取测试
            print(f"开始随机读取测试: {config['num_operations']}次操作")
            rand_duration, rand_bytes = disk_stress.random_read_test(
                test_files, config["num_operations"]
            )

            # 写入压力测试
            print("开始写入压力测试")
            write_duration, write_bytes = disk_stress.write_stress_test(
                config["num_files"], 100
            )

            end_time = time.time()
            stats = monitor.stop_monitoring()

            # 计算性能指标
            seq_throughput = seq_bytes / (1024 * 1024) / seq_duration  # MB/s
            rand_throughput = rand_bytes / (1024 * 1024) / rand_duration  # MB/s
            write_throughput = write_bytes / (1024 * 1024) / write_duration  # MB/s

            test_metrics = StressTestMetrics(
                test_name="disk_io_pressure",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                cpu_usage_max=stats["cpu_max"],
                cpu_usage_avg=stats["cpu_avg"],
                memory_usage_max=stats["memory_max"],
                memory_usage_avg=stats["memory_avg"],
                disk_io_read=stats["disk_read_total"],
                disk_io_write=stats["disk_write_total"],
                network_bytes_sent=stats["network_sent_total"],
                network_bytes_recv=stats["network_recv_total"],
                operations_completed=len(test_files)
                + config["num_operations"]
                + config["num_files"] * 100,
                operations_failed=0,
                throughput=(seq_throughput + rand_throughput + write_throughput) / 3,
                error_rate=0.0,
                success=True,
                error_message=None,
            )

            # 断言
            assert len(test_files) == config["num_files"], "测试文件创建数量不匹配"
            assert seq_bytes > 0, "顺序读取未读取到数据"
            assert rand_bytes > 0, "随机读取未读取到数据"
            assert write_bytes > 0, "写入测试未写入数据"
            assert seq_throughput > 1.0, f"顺序读取吞吐量过低: {seq_throughput:.2f} MB/s"
            assert write_throughput > 1.0, f"写入吞吐量过低: {write_throughput:.2f} MB/s"
            assert (
                stats["disk_read_total"] > 0 or stats["disk_write_total"] > 0
            ), "未检测到磁盘I/O活动"

            print(f"磁盘I/O压力测试结果:")
            print(f"  - 顺序读取吞吐量: {seq_throughput:.2f} MB/s")
            print(f"  - 随机读取吞吐量: {rand_throughput:.2f} MB/s")
            print(f"  - 写入吞吐量: {write_throughput:.2f} MB/s")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            monitor.stop_monitoring()
            pytest.fail(f"磁盘I/O压力测试失败: {str(e)}")

        finally:
            disk_stress.cleanup()
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.stress
    @pytest.mark.slow
    def test_network_bandwidth_pressure(self, stress_config):
        """测试网络带宽压力"""
        monitor = SystemResourceMonitor()
        network_stress = NetworkStressGenerator()

        monitor.start_monitoring()
        start_time = time.time()

        try:
            config = stress_config["network_stress"]

            # 启动回显服务器
            print(f"启动回显服务器，端口: {config['server_port']}")
            server_thread = network_stress.create_echo_server(config["server_port"])

            # 等待服务器完全启动
            time.sleep(0.5)

            # 网络吞吐量测试
            print(
                f"开始网络吞吐量测试: {config['num_connections']}个连接，每个{config['data_size']}字节"
            )

            (
                duration,
                total_sent,
                total_received,
            ) = network_stress.network_throughput_test(
                "localhost",
                config["server_port"],
                config["num_connections"],
                config["data_size"],
            )

            end_time = time.time()
            stats = monitor.stop_monitoring()

            # 计算网络性能指标
            sent_throughput = total_sent / (1024 * 1024) / duration  # MB/s
            recv_throughput = total_received / (1024 * 1024) / duration  # MB/s
            connection_rate = config["num_connections"] / duration  # connections/s

            test_metrics = StressTestMetrics(
                test_name="network_bandwidth_pressure",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                cpu_usage_max=stats["cpu_max"],
                cpu_usage_avg=stats["cpu_avg"],
                memory_usage_max=stats["memory_max"],
                memory_usage_avg=stats["memory_avg"],
                disk_io_read=stats["disk_read_total"],
                disk_io_write=stats["disk_write_total"],
                network_bytes_sent=total_sent,
                network_bytes_recv=total_received,
                operations_completed=config["num_connections"],
                operations_failed=0,
                throughput=(sent_throughput + recv_throughput) / 2,
                error_rate=0.0,
                success=True,
                error_message=None,
            )

            # 断言
            assert total_sent > 0, "未发送任何数据"
            assert total_received > 0, "未接收任何数据"
            assert (
                total_sent == total_received
            ), f"发送和接收数据量不匹配: {total_sent} != {total_received}"
            assert sent_throughput > 0.1, f"发送吞吐量过低: {sent_throughput:.2f} MB/s"
            assert recv_throughput > 0.1, f"接收吞吐量过低: {recv_throughput:.2f} MB/s"
            assert connection_rate > 1.0, f"连接建立速率过低: {connection_rate:.2f} conn/s"

            print(f"网络带宽压力测试结果:")
            print(f"  - 发送吞吐量: {sent_throughput:.2f} MB/s")
            print(f"  - 接收吞吐量: {recv_throughput:.2f} MB/s")
            print(f"  - 连接建立速率: {connection_rate:.2f} conn/s")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            monitor.stop_monitoring()
            pytest.fail(f"网络带宽压力测试失败: {str(e)}")

        finally:
            network_stress.cleanup()

    @pytest.mark.stress
    @pytest.mark.slow
    def test_database_connection_pool_pressure(self, stress_config):
        """测试数据库连接池压力"""
        monitor = SystemResourceMonitor()

        monitor.start_monitoring()
        start_time = time.time()

        try:
            config = stress_config["database_stress"]

            # 创建连接池
            db_pool = DatabaseConnectionPoolStress(config["max_connections"])

            print(
                f"开始数据库连接池压力测试: {config['max_connections']}最大连接，{config['num_workers']}工作线程"
            )

            # 执行压力测试
            results = db_pool.stress_test(
                config["num_workers"], config["operations_per_worker"]
            )

            end_time = time.time()
            stats = monitor.stop_monitoring()

            # 计算性能指标
            success_rate = (
                results["successful_operations"] / results["total_operations"]
            )
            operations_per_second = (
                results["successful_operations"] / results["duration"]
            )

            test_metrics = StressTestMetrics(
                test_name="database_connection_pool_pressure",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                cpu_usage_max=stats["cpu_max"],
                cpu_usage_avg=stats["cpu_avg"],
                memory_usage_max=stats["memory_max"],
                memory_usage_avg=stats["memory_avg"],
                disk_io_read=stats["disk_read_total"],
                disk_io_write=stats["disk_write_total"],
                network_bytes_sent=stats["network_sent_total"],
                network_bytes_recv=stats["network_recv_total"],
                operations_completed=results["successful_operations"],
                operations_failed=results["failed_operations"],
                throughput=operations_per_second,
                error_rate=1.0 - success_rate,
                success=success_rate > 0.95,
                error_message=None
                if success_rate > 0.95
                else f"成功率过低: {success_rate:.2%}",
            )

            # 断言
            assert results["successful_operations"] > 0, "没有成功的数据库操作"
            assert success_rate > 0.95, f"数据库操作成功率过低: {success_rate:.2%}"
            assert (
                operations_per_second > 10
            ), f"数据库操作吞吐量过低: {operations_per_second:.2f} ops/s"
            assert (
                results["connection_timeouts"] < results["total_operations"] * 0.1
            ), "连接超时过多"
            assert (
                results["connection_stats"]["created"] <= config["max_connections"]
            ), "创建连接数超过限制"

            print(f"数据库连接池压力测试结果:")
            print(f"  - 成功率: {success_rate:.2%}")
            print(f"  - 操作吞吐量: {operations_per_second:.2f} ops/s")
            print(f"  - 连接统计: {results['connection_stats']}")
            print(f"  - 测试指标: {asdict(test_metrics)}")

        except Exception as e:
            monitor.stop_monitoring()
            pytest.fail(f"数据库连接池压力测试失败: {str(e)}")

        finally:
            if "db_pool" in locals():
                db_pool.cleanup()

    @pytest.mark.stress
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_comprehensive_stress_scenario(self, stress_config):
        """测试综合压力场景"""
        """同时进行CPU、磁盘、网络和数据库压力测试"""
        monitor = SystemResourceMonitor()
        temp_dir = tempfile.mkdtemp(prefix="scanpulse_comprehensive_stress_")

        monitor.start_monitoring()
        start_time = time.time()

        try:
            print("开始综合压力测试场景")

            # 创建所有压力生成器
            disk_stress = DiskIOStressGenerator(temp_dir)
            network_stress = NetworkStressGenerator()
            db_pool = DatabaseConnectionPoolStress(25)  # 减少连接数避免资源冲突

            # 启动网络服务器
            server_thread = network_stress.create_echo_server(9998)
            time.sleep(0.5)

            # 并发执行所有压力测试
            async def cpu_stress_task():
                return CPUStressGenerator.parallel_cpu_stress(2, 100000)  # 减少负载

            async def disk_stress_task():
                test_files = disk_stress.create_test_files(5, 5)  # 减少文件大小
                duration, bytes_read = disk_stress.sequential_read_test(test_files)
                return duration, bytes_read

            async def network_stress_task():
                duration, sent, recv = network_stress.network_throughput_test(
                    "localhost", 9998, 20, 1024  # 减少连接数和数据量
                )
                return duration, sent, recv

            async def db_stress_task():
                return db_pool.stress_test(10, 50)  # 减少工作线程和操作数

            # 并发执行所有任务
            tasks = [
                asyncio.create_task(cpu_stress_task()),
                asyncio.create_task(disk_stress_task()),
                asyncio.create_task(network_stress_task()),
                asyncio.create_task(db_stress_task()),
            ]

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            stats = monitor.stop_monitoring()

            # 分析结果
            cpu_results, disk_results, network_results, db_results = results

            # 验证所有测试都成功完成
            assert not isinstance(cpu_results, Exception), f"CPU压力测试失败: {cpu_results}"
            assert not isinstance(disk_results, Exception), f"磁盘压力测试失败: {disk_results}"
            assert not isinstance(
                network_results, Exception
            ), f"网络压力测试失败: {network_results}"
            assert not isinstance(db_results, Exception), f"数据库压力测试失败: {db_results}"

            # 创建综合测试指标
            test_metrics = StressTestMetrics(
                test_name="comprehensive_stress_scenario",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                cpu_usage_max=stats["cpu_max"],
                cpu_usage_avg=stats["cpu_avg"],
                memory_usage_max=stats["memory_max"],
                memory_usage_avg=stats["memory_avg"],
                disk_io_read=stats["disk_read_total"],
                disk_io_write=stats["disk_write_total"],
                network_bytes_sent=network_results[1]
                if len(network_results) > 1
                else 0,
                network_bytes_recv=network_results[2]
                if len(network_results) > 2
                else 0,
                operations_completed=len(cpu_results)
                + 1
                + 1
                + db_results["successful_operations"],
                operations_failed=db_results["failed_operations"],
                throughput=0,  # 综合吞吐量难以计算
                error_rate=db_results["failed_operations"]
                / (
                    db_results["successful_operations"]
                    + db_results["failed_operations"]
                ),
                success=True,
                error_message=None,
            )

            # 综合压力测试断言
            assert (
                test_metrics.cpu_usage_max > 30
            ), f"综合测试CPU使用率过低: {test_metrics.cpu_usage_max}%"
            assert (
                test_metrics.memory_usage_max > 20
            ), f"综合测试内存使用率过低: {test_metrics.memory_usage_max}%"
            assert (
                test_metrics.operations_completed > 50
            ), f"综合测试完成操作数过少: {test_metrics.operations_completed}"
            assert (
                test_metrics.error_rate < 0.1
            ), f"综合测试错误率过高: {test_metrics.error_rate:.2%}"

            print(f"综合压力测试结果:")
            print(f"  - CPU测试: {len(cpu_results)}个进程完成")
            print(f"  - 磁盘测试: {disk_results[1]}字节读取")
            print(f"  - 网络测试: {network_results[1]}字节发送")
            print(f"  - 数据库测试: {db_results['successful_operations']}个成功操作")
            print(f"  - 综合指标: {asdict(test_metrics)}")

        except Exception as e:
            monitor.stop_monitoring()
            pytest.fail(f"综合压力测试失败: {str(e)}")

        finally:
            # 清理所有资源
            if "disk_stress" in locals():
                disk_stress.cleanup()
            if "network_stress" in locals():
                network_stress.cleanup()
            if "db_pool" in locals():
                db_pool.cleanup()
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # 运行压力测试
    pytest.main([__file__, "-v", "-m", "stress", "--tb=short"])
