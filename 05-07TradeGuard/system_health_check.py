import os
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体驱动交易系统 V3.5 系统健康检查
生成升级完成报告
"""

import zmq
import json
import time
import psutil
import platform
from datetime import datetime
from typing import Dict, Any, List


class SystemHealthChecker:
    def __init__(self, service_endpoint: str = "tcp://localhost:5555"):
        self.service_endpoint = service_endpoint
        self.health_data = {}
        self.start_time = datetime.now()

    def create_connection(self) -> zmq.Socket:
        """创建ZMQ连接"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        socket.setsockopt(zmq.SNDTIMEO, 5000)
        socket.connect(self.service_endpoint)
        return socket

    def send_request(
        self, socket: zmq.Socket, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送请求"""
        request_id = int(time.time() * 1000000)
        request = {"id": request_id, "method": method, "params": params or {}}

        try:
            socket.send_json(request)
            response = socket.recv_json()
            return response
        except Exception as e:
            return {"error": str(e)}

    def check_system_info(self) -> Dict[str, Any]:
        """检查系统基本信息"""
        print("🖥️ 检查系统基本信息...")

        try:
            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total_gb": round(
                    psutil.virtual_memory().total / (1024**3), 2
                ),
                "disk_usage": {
                    "total_gb": round(psutil.disk_usage("/").total / (1024**3), 2)
                    if platform.system() != "Windows"
                    else round(psutil.disk_usage("C:").total / (1024**3), 2),
                    "used_gb": round(psutil.disk_usage("/").used / (1024**3), 2)
                    if platform.system() != "Windows"
                    else round(psutil.disk_usage("C:").used / (1024**3), 2),
                    "free_gb": round(psutil.disk_usage("/").free / (1024**3), 2)
                    if platform.system() != "Windows"
                    else round(psutil.disk_usage("C:").free / (1024**3), 2),
                },
            }

            print(f"  操作系统: {system_info['platform']}")
            print(
                f"  CPU核心数: {system_info['cpu_count']} 物理 / {system_info['cpu_count_logical']} 逻辑"
            )
            print(f"  内存总量: {system_info['memory_total_gb']} GB")
            print(f"  磁盘空间: {system_info['disk_usage']['free_gb']} GB 可用")

            return {"status": "healthy", "data": system_info}

        except Exception as e:
            print(f"  ❌ 系统信息检查失败: {e}")
            return {"status": "error", "error": str(e)}

    def check_resource_usage(self) -> Dict[str, Any]:
        """检查系统资源使用情况"""
        print("📊 检查系统资源使用情况...")

        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = round(memory.used / (1024**3), 2)
            memory_available_gb = round(memory.available / (1024**3), 2)

            # 磁盘使用情况
            disk_path = "/" if platform.system() != "Windows" else "C:"
            disk = psutil.disk_usage(disk_path)
            disk_percent = (disk.used / disk.total) * 100

            # 网络统计
            network = psutil.net_io_counters()

            resource_usage = {
                "cpu_percent": cpu_percent,
                "memory": {
                    "percent": memory_percent,
                    "used_gb": memory_used_gb,
                    "available_gb": memory_available_gb,
                    "total_gb": round(memory.total / (1024**3), 2),
                },
                "disk": {
                    "percent": round(disk_percent, 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
            }

            print(f"  CPU使用率: {cpu_percent}%")
            print(
                f"  内存使用率: {memory_percent}% ({memory_used_gb}/{memory_used_gb + memory_available_gb} GB)"
            )
            print(f"  磁盘使用率: {disk_percent:.1f}%")

            # 健康状态评估
            status = "healthy"
            warnings = []

            if cpu_percent > 80:
                status = "warning"
                warnings.append(f"CPU使用率过高: {cpu_percent}%")

            if memory_percent > 85:
                status = "warning"
                warnings.append(f"内存使用率过高: {memory_percent}%")

            if disk_percent > 90:
                status = "warning"
                warnings.append(f"磁盘使用率过高: {disk_percent:.1f}%")

            return {"status": status, "data": resource_usage, "warnings": warnings}

        except Exception as e:
            print(f"  ❌ 资源使用检查失败: {e}")
            return {"status": "error", "error": str(e)}

    def check_tacore_service(self) -> Dict[str, Any]:
        """检查TACoreService状态"""
        print("🔧 检查TACoreService状态...")

        socket = self.create_connection()

        try:
            # 健康检查
            health_response = self.send_request(socket, "system.health")

            if "result" in health_response:
                service_info = health_response["result"]
                print(f"  服务状态: {service_info.get('status', 'unknown')}")
                print(f"  服务名称: {service_info.get('service', 'unknown')}")
                print(f"  响应时间戳: {service_info.get('timestamp', 'unknown')}")

                return {
                    "status": "healthy"
                    if service_info.get("status") == "healthy"
                    else "unhealthy",
                    "data": service_info,
                }
            else:
                error_msg = health_response.get("error", "Unknown error")
                print(f"  ❌ 服务健康检查失败: {error_msg}")
                return {"status": "unhealthy", "error": error_msg}

        except Exception as e:
            print(f"  ❌ 无法连接到TACoreService: {e}")
            return {"status": "unreachable", "error": str(e)}
        finally:
            socket.close()

    def check_module_functionality(self) -> Dict[str, Any]:
        """检查各模组功能"""
        print("🧩 检查各模组功能...")

        socket = self.create_connection()
        module_results = {}

        try:
            # 测试各个模组的核心功能
            modules = [
                ("scan.market", {"symbol": "BTCUSDT", "timeframe": "1h"}, "市场扫描"),
                (
                    "trade.execute",
                    {"symbol": "BTCUSDT", "side": "buy", "amount": 0.001},
                    "交易执行",
                ),
                (
                    "risk.assess",
                    {"portfolio": {"BTCUSDT": {"amount": 0.1, "value": 4500}}},
                    "风险评估",
                ),
                (
                    "fund.allocate",
                    {"total_capital": 100000, "risk_tolerance": "medium"},
                    "资金分配",
                ),
            ]

            for method, params, description in modules:
                print(f"  检查{description}模组...")

                start_time = time.time()
                response = self.send_request(socket, method, params)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000

                if "result" in response:
                    print(f"    ✅ {description}功能正常 (响应时间: {response_time:.2f}ms)")
                    module_results[method] = {
                        "status": "healthy",
                        "response_time_ms": response_time,
                        "description": description,
                    }
                else:
                    error_msg = response.get("error", "Unknown error")
                    print(f"    ❌ {description}功能异常: {error_msg}")
                    module_results[method] = {
                        "status": "unhealthy",
                        "error": error_msg,
                        "description": description,
                    }

            # 统计健康模组数量
            healthy_count = sum(
                1 for result in module_results.values() if result["status"] == "healthy"
            )
            total_count = len(module_results)

            overall_status = (
                "healthy"
                if healthy_count == total_count
                else "partial"
                if healthy_count > 0
                else "unhealthy"
            )

            print(f"  模组健康状况: {healthy_count}/{total_count} 正常")

            return {
                "status": overall_status,
                "healthy_count": healthy_count,
                "total_count": total_count,
                "modules": module_results,
            }

        except Exception as e:
            print(f"  ❌ 模组功能检查失败: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            socket.close()

    def generate_upgrade_report(self) -> Dict[str, Any]:
        """生成升级完成报告"""
        print("\n📋 生成升级完成报告...")

        # 执行所有健康检查
        self.health_data = {
            "system_info": self.check_system_info(),
            "resource_usage": self.check_resource_usage(),
            "tacore_service": self.check_tacore_service(),
            "module_functionality": self.check_module_functionality(),
        }

        # 评估整体健康状况
        overall_status = "healthy"
        issues = []
        warnings = []

        for check_name, check_result in self.health_data.items():
            if (
                check_result.get("status") == "error"
                or check_result.get("status") == "unhealthy"
            ):
                overall_status = "unhealthy"
                issues.append(
                    f"{check_name}: {check_result.get('error', 'Unknown issue')}"
                )
            elif (
                check_result.get("status") == "warning"
                or check_result.get("status") == "partial"
            ):
                if overall_status == "healthy":
                    overall_status = "warning"
                warnings.extend(check_result.get("warnings", []))

        # 生成报告
        report = {
            "report_info": {
                "title": "AI智能体驱动交易系统 V3.5 升级完成报告",
                "version": "V3.5",
                "generated_at": datetime.now().isoformat(),
                "check_duration_seconds": (
                    datetime.now() - self.start_time
                ).total_seconds(),
            },
            "upgrade_summary": {
                "status": overall_status,
                "upgrade_successful": overall_status in ["healthy", "warning"],
                "issues_count": len(issues),
                "warnings_count": len(warnings),
            },
            "health_checks": self.health_data,
            "issues": issues,
            "warnings": warnings,
            "recommendations": self.generate_recommendations(
                overall_status, issues, warnings
            ),
        }

        return report

    def generate_recommendations(
        self, status: str, issues: List[str], warnings: List[str]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if status == "healthy":
            recommendations.extend(
                [
                    "✅ 系统升级成功，所有组件运行正常",
                    "✅ 建议投入生产环境使用",
                    "📊 建议定期监控系统性能指标",
                    "🔄 建议建立定期健康检查机制",
                ]
            )
        elif status == "warning":
            recommendations.extend(
                ["⚠️ 系统基本功能正常，但存在一些警告", "🔍 建议解决警告问题后投入生产", "📈 建议优化资源使用情况", "🔄 建议增加监控频率"]
            )
        else:
            recommendations.extend(
                ["❌ 系统存在严重问题，不建议投入生产", "🔧 建议立即修复所有严重问题", "🧪 建议重新执行完整测试", "👥 建议联系技术支持团队"]
            )

        # 根据具体问题添加建议
        if any("CPU" in warning for warning in warnings):
            recommendations.append("💻 建议优化CPU密集型操作或增加计算资源")

        if any("内存" in warning for warning in warnings):
            recommendations.append("🧠 建议优化内存使用或增加内存容量")

        if any("磁盘" in warning for warning in warnings):
            recommendations.append("💾 建议清理磁盘空间或扩展存储容量")

        return recommendations

    def print_report_summary(self, report: Dict[str, Any]):
        """打印报告摘要"""
        print("\n" + "=" * 60)
        print("📊 AI智能体驱动交易系统 V3.5 升级完成报告")
        print("=" * 60)

        # 基本信息
        print(f"报告生成时间: {report['report_info']['generated_at']}")
        print(f"检查耗时: {report['report_info']['check_duration_seconds']:.2f}秒")

        # 升级状态
        status = report["upgrade_summary"]["status"]
        success = report["upgrade_summary"]["upgrade_successful"]

        print(f"\n升级状态: ", end="")
        if status == "healthy":
            print("🟢 健康")
        elif status == "warning":
            print("🟡 警告")
        else:
            print("🔴 异常")

        print(f"升级成功: {'✅ 是' if success else '❌ 否'}")
        print(f"问题数量: {report['upgrade_summary']['issues_count']}")
        print(f"警告数量: {report['upgrade_summary']['warnings_count']}")

        # 健康检查详情
        print("\n健康检查详情:")
        for check_name, check_result in report["health_checks"].items():
            status_icon = {
                "healthy": "✅",
                "warning": "⚠️",
                "partial": "⚠️",
                "unhealthy": "❌",
                "error": "❌",
                "unreachable": "❌",
            }.get(check_result.get("status"), "❓")

            print(
                f"  {status_icon} {check_name}: {check_result.get('status', 'unknown')}"
            )

        # 问题和警告
        if report["issues"]:
            print("\n❌ 发现的问题:")
            for issue in report["issues"]:
                print(f"  • {issue}")

        if report["warnings"]:
            print("\n⚠️ 警告信息:")
            for warning in report["warnings"]:
                print(f"  • {warning}")

        # 建议
        print("\n💡 建议:")
        for recommendation in report["recommendations"]:
            print(f"  • {recommendation}")

        print("\n" + "=" * 60)

    def run_health_check(self) -> Dict[str, Any]:
        """运行完整的系统健康检查"""
        print("🏥 开始系统健康检查...")
        print("=" * 50)

        try:
            # 生成报告
            report = self.generate_upgrade_report()

            # 打印摘要
            self.print_report_summary(report)

            # 保存报告
            report_filename = f"upgrade_completion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print(f"\n📄 完整报告已保存到: {report_filename}")

            return report

        except Exception as e:
            print(f"\n❌ 健康检查过程中出现异常: {e}")
            return {
                "report_info": {
                    "title": "AI智能体驱动交易系统 V3.5 升级完成报告",
                    "version": "V3.5",
                    "generated_at": datetime.now().isoformat(),
                    "error": str(e),
                },
                "upgrade_summary": {
                    "status": "error",
                    "upgrade_successful": False,
                    "error": str(e),
                },
            }


def main():
    """主函数"""
    checker = SystemHealthChecker()

    try:
        report = checker.run_health_check()

        # 根据报告状态返回退出码
        if report.get("upgrade_summary", {}).get("upgrade_successful", False):
            print("\n🎉 系统健康检查完成，升级成功！")
            return True
        else:
            print("\n⚠️ 系统健康检查发现问题，请查看报告详情")
            return False

    except KeyboardInterrupt:
        print("\n用户中断健康检查")
        return False
    except Exception as e:
        print(f"\n健康检查过程中出现异常: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
