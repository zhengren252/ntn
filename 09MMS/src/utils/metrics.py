#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 指标监控
提供系统性能监控和指标收集功能

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import asyncio
import psutil
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """指标数据点"""

    timestamp: datetime
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "tags": self.tags,
        }


@dataclass
class MetricSummary:
    """指标摘要"""

    name: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float
    last_value: float
    last_timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "min": self.min_value,
            "max": self.max_value,
            "avg": self.avg_value,
            "sum": self.sum_value,
            "last": self.last_value,
            "last_timestamp": self.last_timestamp.isoformat(),
        }


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_points_per_metric: int = 1000):
        self.max_points_per_metric = max_points_per_metric
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_points_per_metric)
        )
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)

        self._start_time = datetime.now()
        self._lock = asyncio.Lock()

    async def record_counter(
        self, name: str, value: int = 1, tags: Dict[str, str] = None
    ):
        """记录计数器指标"""
        async with self._lock:
            self.counters[name] += value
            await self._add_metric_point(name, value, tags)

    async def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录仪表盘指标"""
        async with self._lock:
            self.gauges[name] = value
            await self._add_metric_point(name, value, tags)

    async def record_histogram(
        self, name: str, value: float, tags: Dict[str, str] = None
    ):
        """记录直方图指标"""
        async with self._lock:
            self.histograms[name].append(value)
            # 保持最近的1000个值
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            await self._add_metric_point(name, value, tags)

    async def record_timer(
        self, name: str, duration: float, tags: Dict[str, str] = None
    ):
        """记录计时器指标"""
        async with self._lock:
            self.timers[name].append(duration)
            # 保持最近的1000个值
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
            await self._add_metric_point(name, duration, tags)

    async def _add_metric_point(
        self, name: str, value: Union[int, float], tags: Dict[str, str] = None
    ):
        """添加指标数据点"""
        point = MetricPoint(timestamp=datetime.now(), value=value, tags=tags or {})
        self.metrics[name].append(point)

    async def get_metric_summary(self, name: str) -> Optional[MetricSummary]:
        """获取指标摘要"""
        async with self._lock:
            if name not in self.metrics or not self.metrics[name]:
                return None

            points = list(self.metrics[name])
            values = [p.value for p in points]

            return MetricSummary(
                name=name,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                avg_value=sum(values) / len(values),
                sum_value=sum(values),
                last_value=values[-1],
                last_timestamp=points[-1].timestamp,
            )

    async def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        async with self._lock:
            result = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {},
                "timers": {},
                "summaries": {},
                "collection_time": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            }

            # 计算直方图统计
            for name, values in self.histograms.items():
                if values:
                    result["histograms"][name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                    }

            # 计算计时器统计
            for name, values in self.timers.items():
                if values:
                    result["timers"][name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                    }

            # 获取指标摘要
            for name in self.metrics.keys():
                summary = await self.get_metric_summary(name)
                if summary:
                    result["summaries"][name] = summary.to_dict()

            return result

    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    async def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        tags: Dict[str, str] = None,
    ):
        """记录HTTP请求指标"""
        request_tags = {"method": method, "path": path, "status_code": str(status_code)}
        if tags:
            request_tags.update(tags)

        # 记录请求计数
        await self.record_counter("http.requests.total", 1, request_tags)

        # 记录请求耗时
        await self.record_timer("http.request.duration", duration, request_tags)

        # 记录状态码计数
        status_tags = {"status_code": str(status_code)}
        await self.record_counter(f"http.responses.{status_code}", 1, status_tags)

    async def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        async with self._lock:
            if (
                "http.request.duration" in self.timers
                and self.timers["http.request.duration"]
            ):
                durations = self.timers["http.request.duration"]
                return sum(durations) / len(durations)
            return 0.0

    async def record_simulation(
        self, duration: float, success: bool, tags: Dict[str, str] = None
    ):
        """记录仿真指标"""
        status = "success" if success else "failure"
        simulation_tags = {"status": status}
        if tags:
            simulation_tags.update(tags)

        # 记录仿真计数
        await self.record_counter("simulation.total", 1, simulation_tags)

        # 记录仿真耗时
        await self.record_timer("simulation.duration", duration, simulation_tags)

    async def get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            return memory.percent
        except Exception:
            return 0.0

    async def get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil

            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    async def reset_metrics(self):
        """重置所有指标"""
        async with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self._start_time = datetime.now()


class SystemMetricsCollector:
    """系统指标收集器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.process = psutil.Process()
        self._collection_interval = 30  # 30秒收集一次
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start_collection(self):
        """开始收集系统指标"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("系统指标收集已启动")

    async def stop_collection(self):
        """停止收集系统指标"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("系统指标收集已停止")

    async def _collection_loop(self):
        """指标收集循环"""
        while self._running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self._collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"收集系统指标时发生错误: {e}")
                await asyncio.sleep(self._collection_interval)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.metrics.record_gauge("system.cpu.usage_percent", cpu_percent)

            # 内存使用情况
            memory = psutil.virtual_memory()
            await self.metrics.record_gauge(
                "system.memory.usage_percent", memory.percent
            )
            await self.metrics.record_gauge(
                "system.memory.available_mb", memory.available / 1024 / 1024
            )
            await self.metrics.record_gauge(
                "system.memory.used_mb", memory.used / 1024 / 1024
            )

            # 磁盘使用情况
            disk = psutil.disk_usage("/")
            await self.metrics.record_gauge("system.disk.usage_percent", disk.percent)
            await self.metrics.record_gauge(
                "system.disk.free_gb", disk.free / 1024 / 1024 / 1024
            )

            # 进程指标
            process_memory = self.process.memory_info()
            await self.metrics.record_gauge(
                "process.memory.rss_mb", process_memory.rss / 1024 / 1024
            )
            await self.metrics.record_gauge(
                "process.memory.vms_mb", process_memory.vms / 1024 / 1024
            )

            process_cpu = self.process.cpu_percent()
            await self.metrics.record_gauge("process.cpu.usage_percent", process_cpu)

            # 文件描述符
            try:
                num_fds = self.process.num_fds()
                await self.metrics.record_gauge("process.file_descriptors", num_fds)
            except (AttributeError, psutil.AccessDenied):
                # Windows系统可能不支持
                pass

            # 线程数
            num_threads = self.process.num_threads()
            await self.metrics.record_gauge("process.threads", num_threads)

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")


class SimulationMetricsCollector:
    """仿真指标收集器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector

    async def record_simulation_start(self, simulation_id: str, scenario: str):
        """记录仿真开始"""
        await self.metrics.record_counter("simulation.started.total")
        await self.metrics.record_counter(
            "simulation.started.by_scenario", tags={"scenario": scenario}
        )
        logger.info(f"仿真开始: {simulation_id}, 场景: {scenario}")

    async def record_simulation_complete(
        self, simulation_id: str, scenario: str, duration: float, success: bool
    ):
        """记录仿真完成"""
        status = "success" if success else "failure"

        await self.metrics.record_counter("simulation.completed.total")
        await self.metrics.record_counter(
            f"simulation.completed.{status}", tags={"scenario": scenario}
        )

        await self.metrics.record_timer(
            "simulation.duration",
            duration,
            tags={"scenario": scenario, "status": status},
        )

        logger.info(
            f"仿真完成: {simulation_id}, 场景: {scenario}, "
            f"耗时: {duration:.2f}s, 状态: {status}"
        )

    async def record_simulation_error(self, simulation_id: str, error_type: str):
        """记录仿真错误"""
        await self.metrics.record_counter("simulation.errors.total")
        await self.metrics.record_counter(
            "simulation.errors.by_type", tags={"error_type": error_type}
        )
        logger.error(f"仿真错误: {simulation_id}, 错误类型: {error_type}")

    async def record_worker_task_processed(
        self, worker_id: str, processing_time: float
    ):
        """记录工作进程任务处理"""
        await self.metrics.record_counter("worker.tasks.processed")
        await self.metrics.record_timer(
            "worker.task.processing_time",
            processing_time,
            tags={"worker_id": worker_id},
        )

    async def record_cache_operation(self, operation: str, hit: bool, duration: float):
        """记录缓存操作"""
        status = "hit" if hit else "miss"

        await self.metrics.record_counter(
            f"cache.{operation}.total", tags={"status": status}
        )

        await self.metrics.record_timer(
            f"cache.{operation}.duration", duration, tags={"status": status}
        )

    async def record_database_operation(
        self, operation: str, table: str, duration: float, success: bool
    ):
        """记录数据库操作"""
        status = "success" if success else "failure"

        await self.metrics.record_counter(
            f"database.{operation}.total", tags={"table": table, "status": status}
        )

        await self.metrics.record_timer(
            f"database.{operation}.duration",
            duration,
            tags={"table": table, "status": status},
        )

    async def record_api_request(
        self, endpoint: str, method: str, status_code: int, duration: float
    ):
        """记录API请求"""
        await self.metrics.record_counter(
            "api.requests.total",
            tags={
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code),
            },
        )

        await self.metrics.record_timer(
            "api.request.duration",
            duration,
            tags={
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code),
            },
        )

    async def record_queue_size(self, queue_name: str, size: int):
        """记录队列大小"""
        await self.metrics.record_gauge("queue.size", size, tags={"queue": queue_name})

    async def record_active_connections(self, connection_type: str, count: int):
        """记录活跃连接数"""
        await self.metrics.record_gauge(
            "connections.active", count, tags={"type": connection_type}
        )


class PerformanceTimer:
    """性能计时器上下文管理器"""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        metric_name: str,
        tags: Dict[str, str] = None,
    ):
        self.metrics = metrics_collector
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            await self.metrics.record_timer(self.metric_name, duration, self.tags)

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            # 注意：这里是同步版本，需要在异步环境中使用时要小心
            asyncio.create_task(
                self.metrics.record_timer(self.metric_name, duration, self.tags)
            )


class HealthChecker:
    """健康检查器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.checks: Dict[str, callable] = {}
        self.last_check_results: Dict[str, bool] = {}
        self.last_check_time: Optional[datetime] = None

    def register_check(self, name: str, check_func: callable):
        """注册健康检查"""
        self.checks[name] = check_func
        logger.info(f"注册健康检查: {name}")

    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        overall_healthy = True

        for name, check_func in self.checks.items():
            try:
                start_time = time.time()

                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                duration = time.time() - start_time

                is_healthy = bool(result)
                results[name] = {
                    "healthy": is_healthy,
                    "duration": duration,
                    "details": result if isinstance(result, dict) else {},
                }

                self.last_check_results[name] = is_healthy

                if not is_healthy:
                    overall_healthy = False

                # 记录指标
                await self.metrics.record_timer(
                    "health_check.duration", duration, tags={"check": name}
                )

                await self.metrics.record_gauge(
                    "health_check.status", 1 if is_healthy else 0, tags={"check": name}
                )

            except Exception as e:
                logger.error(f"健康检查 {name} 失败: {e}")
                results[name] = {"healthy": False, "error": str(e), "duration": 0}
                self.last_check_results[name] = False
                overall_healthy = False

        self.last_check_time = datetime.now()

        return {
            "healthy": overall_healthy,
            "checks": results,
            "timestamp": self.last_check_time.isoformat(),
        }

    async def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
        return {
            "overall_healthy": all(self.last_check_results.values()),
            "total_checks": len(self.checks),
            "healthy_checks": sum(self.last_check_results.values()),
            "last_check_time": self.last_check_time.isoformat()
            if self.last_check_time
            else None,
            "check_results": self.last_check_results,
        }


# 全局指标收集器实例
_metrics_collector: Optional[MetricsCollector] = None
_system_metrics_collector: Optional[SystemMetricsCollector] = None
_simulation_metrics_collector: Optional[SimulationMetricsCollector] = None
_health_checker: Optional[HealthChecker] = None


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()

    return _metrics_collector


def get_system_metrics_collector() -> SystemMetricsCollector:
    """获取系统指标收集器实例"""
    global _system_metrics_collector

    if _system_metrics_collector is None:
        _system_metrics_collector = SystemMetricsCollector(get_metrics_collector())

    return _system_metrics_collector


def get_simulation_metrics_collector() -> SimulationMetricsCollector:
    """获取仿真指标收集器实例"""
    global _simulation_metrics_collector

    if _simulation_metrics_collector is None:
        _simulation_metrics_collector = SimulationMetricsCollector(
            get_metrics_collector()
        )

    return _simulation_metrics_collector


def get_health_checker() -> HealthChecker:
    """获取健康检查器实例"""
    global _health_checker

    if _health_checker is None:
        _health_checker = HealthChecker(get_metrics_collector())

    return _health_checker


async def cleanup_metrics():
    """清理指标收集器资源"""
    global _system_metrics_collector

    if _system_metrics_collector:
        await _system_metrics_collector.stop_collection()


# 装饰器函数
def measure_time(metric_name: str, tags: Dict[str, str] = None):
    """测量执行时间的装饰器"""

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            async with PerformanceTimer(metrics, metric_name, tags):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            with PerformanceTimer(metrics, metric_name, tags):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def count_calls(metric_name: str, tags: Dict[str, str] = None):
    """计数函数调用的装饰器"""

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            await metrics.record_counter(metric_name, tags=tags)
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            asyncio.create_task(metrics.record_counter(metric_name, tags=tags))
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def initialize_metrics():
    """初始化指标收集器"""
    # 初始化全局指标收集器实例
    get_metrics_collector()
    get_system_metrics_collector()
    get_simulation_metrics_collector()
    get_health_checker()

    logger.info("指标收集器已初始化")
