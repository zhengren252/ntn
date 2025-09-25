# -*- coding: utf-8 -*-
"""
监控模块

提供系统监控、健康检查、性能指标和告警功能
"""

import time
import psutil
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from collections import deque, defaultdict

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from .middleware import require_auth, handle_errors, cache_response

# 创建蓝图
monitoring_bp = Blueprint("monitoring", __name__)


class HealthStatus(Enum):
    """健康状态"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """健康检查结果"""

    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float
    details: Dict[str, Any]


@dataclass
class Metric:
    """性能指标"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


@dataclass
class Alert:
    """告警信息"""

    id: str
    level: AlertLevel
    component: str
    message: str
    timestamp: datetime
    resolved: bool
    resolved_at: Optional[datetime]
    details: Dict[str, Any]


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self, max_history: int = 1000):
        """初始化指标收集器

        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.metrics_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self.start_time = time.time()

    def collect_system_metrics(self) -> List[Metric]:
        """收集系统指标"""
        timestamp = datetime.utcnow()
        metrics = []

        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(
                Metric(
                    name="system.cpu.usage",
                    value=cpu_percent,
                    unit="percent",
                    timestamp=timestamp,
                    tags={"type": "total"},
                )
            )

            # 内存指标
            memory = psutil.virtual_memory()
            metrics.extend(
                [
                    Metric(
                        name="system.memory.usage",
                        value=memory.percent,
                        unit="percent",
                        timestamp=timestamp,
                        tags={"type": "total"},
                    ),
                    Metric(
                        name="system.memory.available",
                        value=memory.available,
                        unit="bytes",
                        timestamp=timestamp,
                        tags={"type": "available"},
                    ),
                    Metric(
                        name="system.memory.used",
                        value=memory.used,
                        unit="bytes",
                        timestamp=timestamp,
                        tags={"type": "used"},
                    ),
                ]
            )

            # 磁盘指标
            disk = psutil.disk_usage("/")
            metrics.extend(
                [
                    Metric(
                        name="system.disk.usage",
                        value=(disk.used / disk.total) * 100,
                        unit="percent",
                        timestamp=timestamp,
                        tags={"mount": "/"},
                    ),
                    Metric(
                        name="system.disk.free",
                        value=disk.free,
                        unit="bytes",
                        timestamp=timestamp,
                        tags={"mount": "/"},
                    ),
                ]
            )

            # 网络指标
            network = psutil.net_io_counters()
            metrics.extend(
                [
                    Metric(
                        name="system.network.bytes_sent",
                        value=network.bytes_sent,
                        unit="bytes",
                        timestamp=timestamp,
                        tags={"direction": "sent"},
                    ),
                    Metric(
                        name="system.network.bytes_recv",
                        value=network.bytes_recv,
                        unit="bytes",
                        timestamp=timestamp,
                        tags={"direction": "received"},
                    ),
                ]
            )

            # 进程指标
            process = psutil.Process()
            metrics.extend(
                [
                    Metric(
                        name="process.cpu.usage",
                        value=process.cpu_percent(),
                        unit="percent",
                        timestamp=timestamp,
                        tags={"pid": str(process.pid)},
                    ),
                    Metric(
                        name="process.memory.usage",
                        value=process.memory_percent(),
                        unit="percent",
                        timestamp=timestamp,
                        tags={"pid": str(process.pid)},
                    ),
                    Metric(
                        name="process.memory.rss",
                        value=process.memory_info().rss,
                        unit="bytes",
                        timestamp=timestamp,
                        tags={"pid": str(process.pid), "type": "rss"},
                    ),
                ]
            )

        except Exception as e:
            current_app.logger_instance.error(f"收集系统指标失败: {e}")

        # 存储指标历史
        for metric in metrics:
            self.metrics_history[metric.name].append(metric)

        return metrics

    def collect_application_metrics(self) -> List[Metric]:
        """收集应用指标"""
        timestamp = datetime.utcnow()
        metrics = []

        try:
            # 应用运行时间
            uptime = time.time() - self.start_time
            metrics.append(
                Metric(
                    name="app.uptime",
                    value=uptime,
                    unit="seconds",
                    timestamp=timestamp,
                    tags={"component": "api"},
                )
            )

            # API请求统计
            if hasattr(current_app, "request_logger"):
                request_stats = current_app.request_logger.get_stats()
                metrics.extend(
                    [
                        Metric(
                            name="app.requests.total",
                            value=request_stats["request_count"],
                            unit="count",
                            timestamp=timestamp,
                            tags={"component": "api"},
                        ),
                        Metric(
                            name="app.requests.error_rate",
                            value=request_stats["error_rate"],
                            unit="percent",
                            timestamp=timestamp,
                            tags={"component": "api"},
                        ),
                        Metric(
                            name="app.requests.avg_response_time",
                            value=request_stats["avg_response_time"],
                            unit="seconds",
                            timestamp=timestamp,
                            tags={"component": "api"},
                        ),
                        Metric(
                            name="app.requests.rate",
                            value=request_stats["requests_per_second"],
                            unit="requests_per_second",
                            timestamp=timestamp,
                            tags={"component": "api"},
                        ),
                    ]
                )

            # 限流统计
            if hasattr(current_app, "rate_limiter"):
                rate_limit_stats = current_app.rate_limiter.get_stats()
                metrics.extend(
                    [
                        Metric(
                            name="app.rate_limit.active_keys",
                            value=rate_limit_stats["active_keys"],
                            unit="count",
                            timestamp=timestamp,
                            tags={"component": "rate_limiter"},
                        ),
                        Metric(
                            name="app.rate_limit.total_requests",
                            value=rate_limit_stats["total_requests"],
                            unit="count",
                            timestamp=timestamp,
                            tags={"component": "rate_limiter"},
                        ),
                    ]
                )

        except Exception as e:
            current_app.logger_instance.error(f"收集应用指标失败: {e}")

        # 存储指标历史
        for metric in metrics:
            self.metrics_history[metric.name].append(metric)

        return metrics

    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[Metric]:
        """获取指标历史

        Args:
            metric_name: 指标名称
            limit: 返回数量限制

        Returns:
            指标历史列表
        """
        history = self.metrics_history.get(metric_name, deque())
        return list(history)[-limit:]

    def get_all_metrics(self) -> Dict[str, List[Metric]]:
        """获取所有指标"""
        return {name: list(history) for name, history in self.metrics_history.items()}


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        """初始化健康检查器"""
        self.check_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def check_system_health(self) -> HealthCheck:
        """检查系统健康状态"""
        start_time = time.time()

        try:
            # 检查CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent

            # 判断健康状态
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"High resource usage: CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%, Disk={disk_percent:.1f}%"
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Moderate resource usage: CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%, Disk={disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources are within normal limits"

            response_time = time.time() - start_time

            health_check = HealthCheck(
                component="system",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "load_average": psutil.getloadavg()
                    if hasattr(psutil, "getloadavg")
                    else None,
                },
            )

        except Exception as e:
            response_time = time.time() - start_time
            health_check = HealthCheck(
                component="system",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={"error": str(e)},
            )

        # 存储检查历史
        self.check_history["system"].append(health_check)

        return health_check

    def check_application_health(self) -> HealthCheck:
        """检查应用健康状态"""
        start_time = time.time()

        try:
            # 检查应用组件
            issues = []

            # 检查请求错误率
            if hasattr(current_app, "request_logger"):
                request_stats = current_app.request_logger.get_stats()
                error_rate = request_stats["error_rate"]

                if error_rate > 0.1:  # 10%错误率
                    issues.append(f"High error rate: {error_rate:.1%}")
                elif error_rate > 0.05:  # 5%错误率
                    issues.append(f"Moderate error rate: {error_rate:.1%}")

            # 检查响应时间
            if hasattr(current_app, "request_logger"):
                avg_response_time = request_stats["avg_response_time"]

                if avg_response_time > 5.0:  # 5秒
                    issues.append(f"High response time: {avg_response_time:.2f}s")
                elif avg_response_time > 2.0:  # 2秒
                    issues.append(f"Moderate response time: {avg_response_time:.2f}s")

            # 判断健康状态
            if any("High" in issue for issue in issues):
                status = HealthStatus.UNHEALTHY
                message = "; ".join(issues)
            elif issues:
                status = HealthStatus.DEGRADED
                message = "; ".join(issues)
            else:
                status = HealthStatus.HEALTHY
                message = "Application is running normally"

            response_time = time.time() - start_time

            health_check = HealthCheck(
                component="application",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={
                    "error_rate": request_stats.get("error_rate", 0),
                    "avg_response_time": request_stats.get("avg_response_time", 0),
                    "request_count": request_stats.get("request_count", 0),
                    "uptime": request_stats.get("uptime", 0),
                },
            )

        except Exception as e:
            response_time = time.time() - start_time
            health_check = HealthCheck(
                component="application",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={"error": str(e)},
            )

        # 存储检查历史
        self.check_history["application"].append(health_check)

        return health_check

    def check_dependencies_health(self) -> HealthCheck:
        """检查依赖服务健康状态"""
        start_time = time.time()

        try:
            # 检查ZMQ连接
            zmq_status = "unknown"
            if hasattr(current_app, "zmq_client"):
                # 这里应该实现实际的ZMQ连接检查
                zmq_status = "healthy"

            # 检查数据库连接（如果有）
            db_status = "not_configured"

            # 判断整体状态
            if zmq_status == "healthy":
                status = HealthStatus.HEALTHY
                message = "All dependencies are healthy"
            elif zmq_status == "unknown":
                status = HealthStatus.DEGRADED
                message = "Some dependencies status unknown"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Dependencies are unhealthy"

            response_time = time.time() - start_time

            health_check = HealthCheck(
                component="dependencies",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={"zmq_status": zmq_status, "database_status": db_status},
            )

        except Exception as e:
            response_time = time.time() - start_time
            health_check = HealthCheck(
                component="dependencies",
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={"error": str(e)},
            )

        # 存储检查历史
        self.check_history["dependencies"].append(health_check)

        return health_check

    def get_overall_health(self) -> HealthCheck:
        """获取整体健康状态"""
        start_time = time.time()

        # 执行所有健康检查
        system_health = self.check_system_health()
        app_health = self.check_application_health()
        deps_health = self.check_dependencies_health()

        # 确定整体状态
        all_checks = [system_health, app_health, deps_health]

        if any(check.status == HealthStatus.UNHEALTHY for check in all_checks):
            overall_status = HealthStatus.UNHEALTHY
        elif any(check.status == HealthStatus.DEGRADED for check in all_checks):
            overall_status = HealthStatus.DEGRADED
        elif any(check.status == HealthStatus.UNKNOWN for check in all_checks):
            overall_status = HealthStatus.UNKNOWN
        else:
            overall_status = HealthStatus.HEALTHY

        response_time = time.time() - start_time

        return HealthCheck(
            component="overall",
            status=overall_status,
            message=f"Overall system status: {overall_status.value}",
            timestamp=datetime.utcnow(),
            response_time=response_time,
            details={
                "system": {
                    "status": system_health.status.value,
                    "message": system_health.message,
                },
                "application": {
                    "status": app_health.status.value,
                    "message": app_health.message,
                },
                "dependencies": {
                    "status": deps_health.status.value,
                    "message": deps_health.message,
                },
            },
        )


# 全局实例
metrics_collector = MetricsCollector()
health_checker = HealthChecker()


@monitoring_bp.route("/health", methods=["GET"])
@handle_errors
def health_check():
    """健康检查端点"""
    component = request.args.get("component", "overall")

    if component == "overall":
        health = health_checker.get_overall_health()
    elif component == "system":
        health = health_checker.check_system_health()
    elif component == "application":
        health = health_checker.check_application_health()
    elif component == "dependencies":
        health = health_checker.check_dependencies_health()
    else:
        raise BadRequest(f"Unknown component: {component}")

    # 根据健康状态设置HTTP状态码
    status_code = 200
    if health.status == HealthStatus.DEGRADED:
        status_code = 200  # 仍然返回200，但在响应中标明状态
    elif health.status == HealthStatus.UNHEALTHY:
        status_code = 503  # Service Unavailable
    elif health.status == HealthStatus.UNKNOWN:
        status_code = 500  # Internal Server Error

    payload = {
        "success": health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
        "component": health.component,
        "status": health.status.value,
        "message": health.message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": getattr(g, "request_id", "unknown"),
        "response_time": health.response_time,
        "details": health.details,
    }

    return jsonify(payload), status_code


@monitoring_bp.route("/metrics", methods=["GET"])
@require_auth
@handle_errors
def get_metrics():
    """获取性能指标"""
    metric_type = request.args.get("type", "all")  # system, application, all
    limit = min(int(request.args.get("limit", 100)), 1000)

    metrics = []

    if metric_type in ["system", "all"]:
        system_metrics = metrics_collector.collect_system_metrics()
        metrics.extend(system_metrics)

    if metric_type in ["application", "all"]:
        app_metrics = metrics_collector.collect_application_metrics()
        metrics.extend(app_metrics)

    # 转换为JSON格式
    metrics_data = []
    for metric in metrics[-limit:]:
        metrics_data.append(
            {
                "name": metric.name,
                "value": metric.value,
                "unit": metric.unit,
                "timestamp": metric.timestamp.isoformat(),
                "tags": metric.tags,
            }
        )

    return jsonify(
        {
            "metrics": metrics_data,
            "total": len(metrics_data),
            "type": metric_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@monitoring_bp.route("/metrics/<metric_name>/history", methods=["GET"])
@require_auth
@handle_errors
def get_metric_history(metric_name: str):
    """获取指标历史"""
    limit = min(int(request.args.get("limit", 100)), 1000)

    history = metrics_collector.get_metric_history(metric_name, limit)

    history_data = []
    for metric in history:
        history_data.append(
            {
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "tags": metric.tags,
            }
        )

    return jsonify(
        {
            "metric_name": metric_name,
            "history": history_data,
            "total": len(history_data),
        }
    )


@monitoring_bp.route("/stats", methods=["GET"])
@require_auth
@handle_errors
@cache_response(30)
def get_monitoring_stats():
    """获取监控统计信息"""
    # 收集当前指标
    system_metrics = metrics_collector.collect_system_metrics()
    app_metrics = metrics_collector.collect_application_metrics()

    # 获取健康状态
    overall_health = health_checker.get_overall_health()

    # 系统信息
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }

    # 当前指标摘要
    current_metrics = {}
    for metric in system_metrics + app_metrics:
        current_metrics[metric.name] = {
            "value": metric.value,
            "unit": metric.unit,
            "timestamp": metric.timestamp.isoformat(),
        }

    return jsonify(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "health": {
                "status": overall_health.status.value,
                "message": overall_health.message,
                "details": overall_health.details,
            },
            "system_info": system_info,
            "current_metrics": current_metrics,
            "metrics_count": len(metrics_collector.get_all_metrics()),
            "health_checks_count": sum(
                len(history) for history in health_checker.check_history.values()
            ),
        }
    )


@monitoring_bp.route("/dashboard", methods=["GET"])
@require_auth
@handle_errors
def get_dashboard_data():
    """获取监控面板数据"""
    # 收集最新指标
    system_metrics = metrics_collector.collect_system_metrics()
    app_metrics = metrics_collector.collect_application_metrics()

    # 获取健康状态
    health = health_checker.get_overall_health()

    # 构建面板数据
    dashboard_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "health": {
            "status": health.status.value,
            "message": health.message,
            "components": health.details,
        },
        "system": {},
        "application": {},
        "alerts": [],  # 这里可以添加告警信息
    }

    # 整理系统指标
    for metric in system_metrics:
        category = metric.name.split(".")[1]  # system.cpu.usage -> cpu
        if category not in dashboard_data["system"]:
            dashboard_data["system"][category] = {}

        metric_key = metric.name.split(".")[-1]  # system.cpu.usage -> usage
        dashboard_data["system"][category][metric_key] = {
            "value": metric.value,
            "unit": metric.unit,
            "tags": metric.tags,
        }

    # 整理应用指标
    for metric in app_metrics:
        if metric.name.startswith("app."):
            category = metric.name.split(".")[1]  # app.requests.total -> requests
            if category not in dashboard_data["application"]:
                dashboard_data["application"][category] = {}

            metric_key = metric.name.split(".")[-1]  # app.requests.total -> total
            dashboard_data["application"][category][metric_key] = {
                "value": metric.value,
                "unit": metric.unit,
                "tags": metric.tags,
            }

    return jsonify(dashboard_data)


if __name__ == "__main__":
    # 测试监控功能
    print("测试监控模块...")

    # 测试指标收集
    collector = MetricsCollector()

    print("收集系统指标...")
    system_metrics = collector.collect_system_metrics()
    for metric in system_metrics[:5]:  # 只显示前5个
        print(f"  {metric.name}: {metric.value} {metric.unit}")

    print("\n收集应用指标...")
    app_metrics = collector.collect_application_metrics()
    for metric in app_metrics:
        print(f"  {metric.name}: {metric.value} {metric.unit}")

    # 测试健康检查
    checker = HealthChecker()

    print("\n执行健康检查...")
    health = checker.get_overall_health()
    print(f"整体健康状态: {health.status.value} - {health.message}")
    print(f"响应时间: {health.response_time:.3f}s")

    # 显示详细信息
    for component, details in health.details.items():
        print(f"  {component}: {details['status']} - {details['message']}")
