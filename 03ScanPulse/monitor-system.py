#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体驱动交易系统V3.5 - 系统监控脚本
实时监控所有模组的运行状态、性能指标和错误日志
"""

import os
import sys
import time
import json
import psutil
import requests
import zmq
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading
import logging
from collections import defaultdict, deque

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from config.system_logging import get_service_logger


class SystemMonitor:
    """系统监控器"""

    def __init__(self):
        self.logger = get_service_logger("system_monitor").get_logger()
        self.running = False
        self.monitor_interval = 30  # 监控间隔（秒）

        # 服务配置
        self.services = {
            "tacore_service": {
                "type": "zmq",
                "endpoint": "tcp://localhost:5555",
                "health_method": "health.check",
            },
            "redis": {"type": "redis", "host": "localhost", "port": 6379, "db": 0},
            "api_factory": {
                "type": "http",
                "url": "http://localhost:8001/health",
                "timeout": 5,
            },
            "crawler": {
                "type": "http",
                "url": "http://localhost:8002/health",
                "timeout": 5,
            },
            "scanner": {
                "type": "http",
                "url": "http://localhost:8003/health",
                "timeout": 5,
            },
            "trader": {
                "type": "http",
                "url": "http://localhost:8004/health",
                "timeout": 5,
            },
            "risk_manager": {
                "type": "http",
                "url": "http://localhost:8005/health",
                "timeout": 5,
            },
            "portfolio": {
                "type": "http",
                "url": "http://localhost:8006/health",
                "timeout": 5,
            },
            "notifier": {
                "type": "http",
                "url": "http://localhost:8007/health",
                "timeout": 5,
            },
            "analytics": {
                "type": "http",
                "url": "http://localhost:8008/health",
                "timeout": 5,
            },
            "backtester": {
                "type": "http",
                "url": "http://localhost:8009/health",
                "timeout": 5,
            },
            "web_ui": {
                "type": "http",
                "url": "http://localhost:3000/health",
                "timeout": 5,
            },
            "monitor": {
                "type": "http",
                "url": "http://localhost:8010/health",
                "timeout": 5,
            },
        }

        # 监控数据存储
        self.status_history = defaultdict(lambda: deque(maxlen=100))
        self.performance_metrics = defaultdict(dict)
        self.error_counts = defaultdict(int)
        self.alert_thresholds = {
            "response_time": 5.0,  # 响应时间阈值（秒）
            "error_rate": 0.1,  # 错误率阈值
            "memory_usage": 0.8,  # 内存使用率阈值
            "cpu_usage": 0.8,  # CPU使用率阈值
        }

        # 初始化连接
        self.zmq_context = None
        self.redis_client = None
        self._init_connections()

    def _init_connections(self):
        """初始化连接"""
        try:
            # 初始化ZMQ上下文
            self.zmq_context = zmq.Context()

            # 初始化Redis连接
            redis_config = self.services["redis"]
            self.redis_client = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                db=redis_config["db"],
                decode_responses=True,
            )

            self.logger.info("Monitor connections initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")

    def check_service_health(
        self, service_name: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查服务健康状态"""
        start_time = time.time()

        try:
            if config["type"] == "http":
                response = requests.get(config["url"], timeout=config.get("timeout", 5))
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "details": response.json() if response.content else {},
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "error": f"HTTP {response.status_code}",
                    }

            elif config["type"] == "zmq":
                socket = self.zmq_context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时

                try:
                    socket.connect(config["endpoint"])

                    # 发送健康检查请求
                    request = {
                        "method": config["health_method"],
                        "params": {},
                        "id": f"monitor_{int(time.time())}",
                    }

                    socket.send_string(json.dumps(request))
                    response_str = socket.recv_string()
                    response = json.loads(response_str)

                    response_time = time.time() - start_time

                    if response.get("status") == "success":
                        return {
                            "status": "healthy",
                            "response_time": response_time,
                            "details": response.get("result", {}),
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "response_time": response_time,
                            "error": response.get("message", "Unknown error"),
                        }

                finally:
                    socket.close()

            elif config["type"] == "redis":
                self.redis_client.ping()
                response_time = time.time() - start_time

                # 获取Redis信息
                info = self.redis_client.info()

                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "details": {
                        "version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human"),
                        "keyspace_hits": info.get("keyspace_hits"),
                        "keyspace_misses": info.get("keyspace_misses"),
                    },
                }

            else:
                return {
                    "status": "unknown",
                    "response_time": 0,
                    "error": f'Unknown service type: {config["type"]}',
                }

        except Exception as e:
            response_time = time.time() - start_time
            return {"status": "error", "response_time": response_time, "error": str(e)}

    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()

            # 磁盘使用情况
            disk = psutil.disk_usage("/")

            # 网络统计
            network = psutil.net_io_counters()

            return {
                "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return {}

    def check_log_errors(self, service_name: str, minutes: int = 5) -> Dict[str, Any]:
        """检查日志中的错误"""
        try:
            log_dir = Path("logs") / service_name
            error_log_file = log_dir / f"{service_name}_error.log"

            if not error_log_file.exists():
                return {"error_count": 0, "recent_errors": []}

            # 读取最近的错误日志
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            recent_errors = []
            error_count = 0

            with open(error_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = datetime.fromisoformat(log_entry["timestamp"])

                        if log_time >= cutoff_time:
                            error_count += 1
                            recent_errors.append(
                                {
                                    "timestamp": log_entry["timestamp"],
                                    "message": log_entry["message"],
                                    "level": log_entry["level"],
                                }
                            )

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            return {
                "error_count": error_count,
                "recent_errors": recent_errors[-10:],  # 最近10个错误
            }

        except Exception as e:
            self.logger.error(f"Failed to check log errors for {service_name}: {e}")
            return {"error_count": 0, "recent_errors": []}

    def generate_alert(
        self,
        service_name: str,
        alert_type: str,
        message: str,
        severity: str = "warning",
    ):
        """生成告警"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "type": alert_type,
            "severity": severity,
            "message": message,
        }

        # 记录告警日志
        if severity == "critical":
            self.logger.critical(f"ALERT: {message}", extra=alert)
        elif severity == "error":
            self.logger.error(f"ALERT: {message}", extra=alert)
        else:
            self.logger.warning(f"ALERT: {message}", extra=alert)

        # 可以在这里添加其他告警通知方式（邮件、短信等）
        return alert

    def monitor_cycle(self):
        """执行一次监控循环"""
        cycle_start = time.time()

        # 获取系统指标
        system_metrics = self.get_system_metrics()

        # 检查系统资源告警
        if system_metrics:
            cpu_usage = system_metrics["cpu"]["percent"] / 100
            memory_usage = system_metrics["memory"]["percent"] / 100

            if cpu_usage > self.alert_thresholds["cpu_usage"]:
                self.generate_alert(
                    "system",
                    "high_cpu_usage",
                    f"High CPU usage: {cpu_usage:.1%}",
                    "warning",
                )

            if memory_usage > self.alert_thresholds["memory_usage"]:
                self.generate_alert(
                    "system",
                    "high_memory_usage",
                    f"High memory usage: {memory_usage:.1%}",
                    "warning",
                )

        # 检查所有服务
        service_statuses = {}

        for service_name, config in self.services.items():
            # 检查服务健康状态
            health_status = self.check_service_health(service_name, config)

            # 检查日志错误
            log_errors = self.check_log_errors(service_name)

            # 合并状态信息
            status = {
                "health": health_status,
                "errors": log_errors,
                "timestamp": datetime.now().isoformat(),
            }

            service_statuses[service_name] = status

            # 存储历史状态
            self.status_history[service_name].append(status)

            # 检查告警条件
            if health_status["status"] != "healthy":
                self.generate_alert(
                    service_name,
                    "service_unhealthy",
                    f"Service {service_name} is {health_status['status']}: {health_status.get('error', 'Unknown error')}",
                    "error",
                )

            elif (
                health_status["response_time"] > self.alert_thresholds["response_time"]
            ):
                self.generate_alert(
                    service_name,
                    "slow_response",
                    f"Slow response from {service_name}: {health_status['response_time']:.2f}s",
                    "warning",
                )

            if log_errors["error_count"] > 0:
                self.generate_alert(
                    service_name,
                    "log_errors",
                    f"Found {log_errors['error_count']} errors in {service_name} logs",
                    "warning",
                )

        # 生成监控报告
        cycle_duration = time.time() - cycle_start

        report = {
            "timestamp": datetime.now().isoformat(),
            "cycle_duration": cycle_duration,
            "system_metrics": system_metrics,
            "service_statuses": service_statuses,
            "summary": {
                "total_services": len(self.services),
                "healthy_services": sum(
                    1
                    for s in service_statuses.values()
                    if s["health"]["status"] == "healthy"
                ),
                "unhealthy_services": sum(
                    1
                    for s in service_statuses.values()
                    if s["health"]["status"] != "healthy"
                ),
                "total_errors": sum(
                    s["errors"]["error_count"] for s in service_statuses.values()
                ),
            },
        }

        self.logger.info(
            f"Monitor cycle completed in {cycle_duration:.2f}s",
            extra={
                "cycle_duration": cycle_duration,
                "healthy_services": report["summary"]["healthy_services"],
                "total_services": report["summary"]["total_services"],
            },
        )

        return report

    def start_monitoring(self):
        """开始监控"""
        self.running = True
        self.logger.info("System monitoring started")

        try:
            while self.running:
                try:
                    report = self.monitor_cycle()

                    # 等待下一个监控周期
                    time.sleep(self.monitor_interval)

                except KeyboardInterrupt:
                    self.logger.info("Monitoring interrupted by user")
                    break

                except Exception as e:
                    self.logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
                    time.sleep(5)  # 错误后短暂等待

        finally:
            self.stop_monitoring()

    def stop_monitoring(self):
        """停止监控"""
        self.running = False

        if self.zmq_context:
            self.zmq_context.term()

        self.logger.info("System monitoring stopped")

    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "monitor_status": "running" if self.running else "stopped",
            "services": list(self.services.keys()),
            "recent_status": {
                name: list(history)[-1] if history else None
                for name, history in self.status_history.items()
            },
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AI智能体驱动交易系统V3.5 - 系统监控")
    parser.add_argument("--interval", type=int, default=30, help="监控间隔（秒）")
    parser.add_argument("--once", action="store_true", help="只执行一次监控检查")
    parser.add_argument("--report", action="store_true", help="生成状态报告")

    args = parser.parse_args()

    monitor = SystemMonitor()
    monitor.monitor_interval = args.interval

    if args.once:
        # 执行一次监控检查
        report = monitor.monitor_cycle()
        print(json.dumps(report, indent=2, ensure_ascii=False))

    elif args.report:
        # 生成状态报告
        report = monitor.get_status_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))

    else:
        # 持续监控
        try:
            monitor.start_monitoring()
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        except Exception as e:
            print(f"Monitoring failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
