#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息源爬虫模组健康检查脚本
用于监控系统各组件的健康状态
"""

import os
import sys
import json
import time
import argparse
import requests
import redis
import sqlite3
import zmq
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class HealthStatus(Enum):
    """健康状态枚举"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """组件健康状态"""

    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = None
    response_time: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if self.details is None:
            self.details = {}


class HealthChecker:
    """健康检查器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results: List[ComponentHealth] = []

    def check_api_service(self) -> ComponentHealth:
        """检查API服务健康状态"""
        start_time = time.time()

        try:
            api_url = self.config.get("api_url", "http://localhost:5000")
            health_endpoint = f"{api_url}/health"

            response = requests.get(
                health_endpoint, timeout=self.config.get("api_timeout", 10)
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return ComponentHealth(
                        name="API Service",
                        status=HealthStatus.HEALTHY,
                        message="API服务运行正常",
                        details=data,
                        response_time=response_time,
                    )
                else:
                    return ComponentHealth(
                        name="API Service",
                        status=HealthStatus.UNHEALTHY,
                        message=f"API服务状态异常: {data.get('status')}",
                        details=data,
                        response_time=response_time,
                    )
            else:
                return ComponentHealth(
                    name="API Service",
                    status=HealthStatus.UNHEALTHY,
                    message=f"API服务响应异常: HTTP {response.status_code}",
                    response_time=response_time,
                )

        except requests.exceptions.ConnectionError:
            return ComponentHealth(
                name="API Service",
                status=HealthStatus.UNHEALTHY,
                message="无法连接到API服务",
                response_time=time.time() - start_time,
            )
        except requests.exceptions.Timeout:
            return ComponentHealth(
                name="API Service",
                status=HealthStatus.UNHEALTHY,
                message="API服务响应超时",
                response_time=time.time() - start_time,
            )
        except Exception as e:
            return ComponentHealth(
                name="API Service",
                status=HealthStatus.UNKNOWN,
                message=f"API服务检查失败: {str(e)}",
                response_time=time.time() - start_time,
            )

    def check_redis_service(self) -> ComponentHealth:
        """检查Redis服务健康状态"""
        start_time = time.time()

        try:
            redis_url = self.config.get("redis_url", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)

            # 测试连接
            r.ping()

            # 获取Redis信息
            info = r.info()
            memory_usage = info.get("used_memory_human", "N/A")
            connected_clients = info.get("connected_clients", 0)
            uptime = info.get("uptime_in_seconds", 0)

            response_time = time.time() - start_time

            # 检查内存使用率
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)

            status = HealthStatus.HEALTHY
            message = "Redis服务运行正常"

            if max_memory > 0:
                memory_ratio = used_memory / max_memory
                if memory_ratio > 0.9:
                    status = HealthStatus.WARNING
                    message = f"Redis内存使用率过高: {memory_ratio:.1%}"
                elif memory_ratio > 0.95:
                    status = HealthStatus.UNHEALTHY
                    message = f"Redis内存使用率危险: {memory_ratio:.1%}"

            return ComponentHealth(
                name="Redis Service",
                status=status,
                message=message,
                details={
                    "memory_usage": memory_usage,
                    "connected_clients": connected_clients,
                    "uptime_seconds": uptime,
                    "version": info.get("redis_version", "unknown"),
                },
                response_time=response_time,
            )

        except redis.ConnectionError:
            return ComponentHealth(
                name="Redis Service",
                status=HealthStatus.UNHEALTHY,
                message="无法连接到Redis服务",
                response_time=time.time() - start_time,
            )
        except Exception as e:
            return ComponentHealth(
                name="Redis Service",
                status=HealthStatus.UNKNOWN,
                message=f"Redis服务检查失败: {str(e)}",
                response_time=time.time() - start_time,
            )

    def check_database(self) -> ComponentHealth:
        """检查SQLite数据库健康状态"""
        start_time = time.time()

        try:
            db_path = self.config.get("database_path", "data/dev.db")

            if not os.path.exists(db_path):
                return ComponentHealth(
                    name="Database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"数据库文件不存在: {db_path}",
                    response_time=time.time() - start_time,
                )

            # 检查数据库连接
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()

            # 执行简单查询
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            # 检查数据库大小
            db_size = os.path.getsize(db_path)

            # 检查表数量
            table_count = len(tables)

            conn.close()
            response_time = time.time() - start_time

            status = HealthStatus.HEALTHY
            message = "数据库运行正常"

            # 检查数据库大小（警告阈值：1GB）
            if db_size > 1024 * 1024 * 1024:
                status = HealthStatus.WARNING
                message = f"数据库文件较大: {db_size / (1024*1024):.1f}MB"

            return ComponentHealth(
                name="Database",
                status=status,
                message=message,
                details={
                    "database_path": db_path,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2),
                    "table_count": table_count,
                    "tables": [table[0] for table in tables],
                },
                response_time=response_time,
            )

        except sqlite3.OperationalError as e:
            return ComponentHealth(
                name="Database",
                status=HealthStatus.UNHEALTHY,
                message=f"数据库操作失败: {str(e)}",
                response_time=time.time() - start_time,
            )
        except Exception as e:
            return ComponentHealth(
                name="Database",
                status=HealthStatus.UNKNOWN,
                message=f"数据库检查失败: {str(e)}",
                response_time=time.time() - start_time,
            )

    def check_zmq_service(self) -> ComponentHealth:
        """检查ZeroMQ服务健康状态"""
        start_time = time.time()

        try:
            context = zmq.Context()

            # 检查发布端口
            pub_port = self.config.get("zmq_pub_port", 5555)
            socket = context.socket(zmq.PUB)

            try:
                socket.bind(f"tcp://*:{pub_port}")
                socket.close()
                pub_available = True
            except zmq.ZMQError:
                pub_available = False

            # 检查订阅端口
            sub_port = self.config.get("zmq_sub_port", 5556)
            socket = context.socket(zmq.SUB)

            try:
                socket.bind(f"tcp://*:{sub_port}")
                socket.close()
                sub_available = True
            except zmq.ZMQError:
                sub_available = False

            context.term()
            response_time = time.time() - start_time

            if pub_available and sub_available:
                status = HealthStatus.HEALTHY
                message = "ZeroMQ服务端口可用"
            elif pub_available or sub_available:
                status = HealthStatus.WARNING
                message = "部分ZeroMQ端口不可用"
            else:
                status = HealthStatus.UNHEALTHY
                message = "ZeroMQ端口均不可用"

            return ComponentHealth(
                name="ZeroMQ Service",
                status=status,
                message=message,
                details={
                    "publisher_port": pub_port,
                    "subscriber_port": sub_port,
                    "publisher_available": pub_available,
                    "subscriber_available": sub_available,
                },
                response_time=response_time,
            )

        except Exception as e:
            return ComponentHealth(
                name="ZeroMQ Service",
                status=HealthStatus.UNKNOWN,
                message=f"ZeroMQ服务检查失败: {str(e)}",
                response_time=time.time() - start_time,
            )

    def check_disk_space(self) -> ComponentHealth:
        """检查磁盘空间"""
        start_time = time.time()

        try:
            import shutil

            # 检查当前目录磁盘空间
            total, used, free = shutil.disk_usage(".")

            free_percent = (free / total) * 100
            used_percent = (used / total) * 100

            response_time = time.time() - start_time

            if free_percent < 5:
                status = HealthStatus.UNHEALTHY
                message = f"磁盘空间严重不足: {free_percent:.1f}%可用"
            elif free_percent < 10:
                status = HealthStatus.WARNING
                message = f"磁盘空间不足: {free_percent:.1f}%可用"
            else:
                status = HealthStatus.HEALTHY
                message = f"磁盘空间充足: {free_percent:.1f}%可用"

            return ComponentHealth(
                name="Disk Space",
                status=status,
                message=message,
                details={
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "used_percent": round(used_percent, 1),
                    "free_percent": round(free_percent, 1),
                },
                response_time=response_time,
            )

        except Exception as e:
            return ComponentHealth(
                name="Disk Space",
                status=HealthStatus.UNKNOWN,
                message=f"磁盘空间检查失败: {str(e)}",
                response_time=time.time() - start_time,
            )

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        print("开始健康检查...")

        # 执行各项检查
        checks = [
            self.check_api_service,
            self.check_redis_service,
            self.check_database,
            self.check_zmq_service,
            self.check_disk_space,
        ]

        for check_func in checks:
            try:
                result = check_func()
                self.results.append(result)
                print(f"✓ {result.name}: {result.status.value} - {result.message}")
            except Exception as e:
                error_result = ComponentHealth(
                    name=check_func.__name__,
                    status=HealthStatus.UNKNOWN,
                    message=f"检查执行失败: {str(e)}",
                )
                self.results.append(error_result)
                print(f"✗ {check_func.__name__}: 检查失败 - {str(e)}")

        # 计算总体健康状态
        overall_status = self._calculate_overall_status()

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": [
                {
                    "name": result.name,
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details,
                    "response_time": result.response_time,
                    "timestamp": result.timestamp,
                }
                for result in self.results
            ],
            "summary": self._generate_summary(),
        }

    def _calculate_overall_status(self) -> HealthStatus:
        """计算总体健康状态"""
        if not self.results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in self.results]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    def _generate_summary(self) -> Dict[str, Any]:
        """生成检查摘要"""
        total = len(self.results)
        healthy = sum(1 for r in self.results if r.status == HealthStatus.HEALTHY)
        warning = sum(1 for r in self.results if r.status == HealthStatus.WARNING)
        unhealthy = sum(1 for r in self.results if r.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for r in self.results if r.status == HealthStatus.UNKNOWN)

        avg_response_time = (
            sum(r.response_time for r in self.results) / total if total > 0 else 0
        )

        return {
            "total_components": total,
            "healthy_count": healthy,
            "warning_count": warning,
            "unhealthy_count": unhealthy,
            "unknown_count": unknown,
            "average_response_time": round(avg_response_time, 3),
        }


def load_config(env: str) -> Dict[str, Any]:
    """加载配置"""
    config = {
        "api_url": f'http://localhost:{5000 + (0 if env == "development" else 1 if env == "staging" else 2)}',
        "redis_url": f'redis://localhost:{6379 + (0 if env == "development" else 1 if env == "staging" else 2)}/{0 if env == "development" else 1 if env == "staging" else 2}',
        "database_path": f"data/{env}.db",
        "zmq_pub_port": 5555
        + (0 if env == "development" else 2 if env == "staging" else 4),
        "zmq_sub_port": 5556
        + (0 if env == "development" else 2 if env == "staging" else 4),
        "api_timeout": 10,
    }

    return config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="信息源爬虫模组健康检查")
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="development",
        help="环境名称",
    )
    parser.add_argument(
        "--output", choices=["json", "text"], default="text", help="输出格式"
    )
    parser.add_argument("--file", help="输出到文件")
    parser.add_argument("--exit-code", action="store_true", help="根据健康状态设置退出码")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.env)

    # 执行健康检查
    checker = HealthChecker(config)
    results = checker.run_all_checks()

    # 输出结果
    if args.output == "json":
        output = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        output = f"""
=== 信息源爬虫模组健康检查报告 ===
环境: {args.env}
时间: {results['timestamp']}
总体状态: {results['overall_status']}

组件状态:
"""
        for component in results["components"]:
            status_icon = {
                "healthy": "✓",
                "warning": "⚠",
                "unhealthy": "✗",
                "unknown": "?",
            }.get(component["status"], "?")

            output += f"{status_icon} {component['name']}: {component['status']} - {component['message']}\n"
            if component["details"]:
                for key, value in component["details"].items():
                    output += f"  {key}: {value}\n"
            output += "\n"

        summary = results["summary"]
        output += f"""
摘要:
- 总组件数: {summary['total_components']}
- 健康: {summary['healthy_count']}
- 警告: {summary['warning_count']}
- 异常: {summary['unhealthy_count']}
- 未知: {summary['unknown_count']}
- 平均响应时间: {summary['average_response_time']}s
"""

    # 输出到文件或控制台
    if args.file:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"健康检查报告已保存到: {args.file}")
    else:
        print(output)

    # 设置退出码
    if args.exit_code:
        status_map = {"healthy": 0, "warning": 1, "unhealthy": 2, "unknown": 3}
        sys.exit(status_map.get(results["overall_status"], 3))


if __name__ == "__main__":
    main()
