#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控系统初始化脚本
用于设置Prometheus、Grafana、Alertmanager等监控组件
"""

import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.config_manager import ConfigManager
from app.utils.logger import setup_logger


class MonitoringInitializer:
    """监控系统初始化器"""

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config = ConfigManager(environment)
        self.logger = setup_logger(
            "monitoring_init", self.config.get("logging.level", "INFO")
        )

        # 服务配置
        self.services = {
            "prometheus": {
                "url": f"http://localhost:{self.config.get('monitoring.prometheus.port', 9090)}",
                "health_endpoint": "/api/v1/query?query=up",
                "config_reload_endpoint": "/-/reload",
            },
            "grafana": {
                "url": f"http://localhost:{self.config.get('monitoring.grafana.port', 3001)}",
                "health_endpoint": "/api/health",
                "admin_user": self.config.get("monitoring.grafana.admin_user", "admin"),
                "admin_password": self.config.get(
                    "monitoring.grafana.admin_password", "admin"
                ),
            },
            "alertmanager": {
                "url": f"http://localhost:{self.config.get('monitoring.alertmanager.port', 9093)}",
                "health_endpoint": "/api/v1/status",
                "config_reload_endpoint": "/-/reload",
            },
        }

    def wait_for_service(self, service_name: str, timeout: int = 300) -> bool:
        """等待服务启动"""
        service_config = self.services.get(service_name)
        if not service_config:
            self.logger.error(f"未知服务: {service_name}")
            return False

        url = service_config["url"] + service_config["health_endpoint"]
        start_time = time.time()

        self.logger.info(f"等待 {service_name} 服务启动...")

        while time.time() - start_time < timeout:
            try:
                if service_name == "grafana":
                    response = requests.get(url, timeout=5)
                else:
                    response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    self.logger.info(f"{service_name} 服务已启动")
                    return True

            except requests.exceptions.RequestException:
                pass

            time.sleep(5)

        self.logger.error(f"{service_name} 服务启动超时")
        return False

    def setup_grafana(self) -> bool:
        """设置Grafana"""
        self.logger.info("配置Grafana...")

        grafana_config = self.services["grafana"]
        base_url = grafana_config["url"]
        auth = (grafana_config["admin_user"], grafana_config["admin_password"])

        try:
            # 1. 添加Prometheus数据源
            datasource_config = {
                "name": "Prometheus",
                "type": "prometheus",
                "url": self.services["prometheus"]["url"],
                "access": "proxy",
                "isDefault": True,
                "basicAuth": False,
                "jsonData": {"httpMethod": "POST", "timeInterval": "15s"},
            }

            response = requests.post(
                f"{base_url}/api/datasources",
                json=datasource_config,
                auth=auth,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in [200, 409]:  # 200: 创建成功, 409: 已存在
                self.logger.info("Prometheus数据源配置成功")
            else:
                self.logger.error(f"Prometheus数据源配置失败: {response.text}")
                return False

            # 2. 导入仪表板
            dashboard_file = project_root / "config" / "grafana-dashboard.json"
            if dashboard_file.exists():
                with open(dashboard_file, "r", encoding="utf-8") as f:
                    dashboard_config = json.load(f)

                import_config = {
                    "dashboard": dashboard_config["dashboard"],
                    "overwrite": True,
                    "inputs": [
                        {
                            "name": "DS_PROMETHEUS",
                            "type": "datasource",
                            "pluginId": "prometheus",
                            "value": "Prometheus",
                        }
                    ],
                }

                response = requests.post(
                    f"{base_url}/api/dashboards/import",
                    json=import_config,
                    auth=auth,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    self.logger.info("仪表板导入成功")
                else:
                    self.logger.error(f"仪表板导入失败: {response.text}")
                    return False

            # 3. 配置告警通知渠道
            notification_config = {
                "name": "email-alerts",
                "type": "email",
                "settings": {
                    "addresses": self.config.get(
                        "monitoring.email.recipients", "admin@example.com"
                    ),
                    "singleEmail": True,
                    "subject": "[Grafana Alert] {{ .GroupLabels.alertname }}",
                    "message": "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}",
                },
            }

            response = requests.post(
                f"{base_url}/api/alert-notifications",
                json=notification_config,
                auth=auth,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in [200, 409]:
                self.logger.info("告警通知渠道配置成功")
            else:
                self.logger.warning(f"告警通知渠道配置失败: {response.text}")

            return True

        except Exception as e:
            self.logger.error(f"Grafana配置失败: {e}")
            return False

    def setup_prometheus(self) -> bool:
        """设置Prometheus"""
        self.logger.info("配置Prometheus...")

        try:
            # 检查配置文件
            config_file = project_root / "config" / f"prometheus-{self.environment}.yml"
            if not config_file.exists():
                config_file = project_root / "config" / "prometheus-prod.yml"

            if not config_file.exists():
                self.logger.error("Prometheus配置文件不存在")
                return False

            # 重载配置
            prometheus_config = self.services["prometheus"]
            reload_url = (
                prometheus_config["url"] + prometheus_config["config_reload_endpoint"]
            )

            response = requests.post(reload_url, timeout=10)

            if response.status_code == 200:
                self.logger.info("Prometheus配置重载成功")
                return True
            else:
                self.logger.error(f"Prometheus配置重载失败: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Prometheus配置失败: {e}")
            return False

    def setup_alertmanager(self) -> bool:
        """设置Alertmanager"""
        self.logger.info("配置Alertmanager...")

        try:
            # 检查配置文件
            config_file = project_root / "config" / "alertmanager.yml"
            if not config_file.exists():
                self.logger.error("Alertmanager配置文件不存在")
                return False

            # 重载配置
            alertmanager_config = self.services["alertmanager"]
            reload_url = (
                alertmanager_config["url"]
                + alertmanager_config["config_reload_endpoint"]
            )

            response = requests.post(reload_url, timeout=10)

            if response.status_code == 200:
                self.logger.info("Alertmanager配置重载成功")
                return True
            else:
                self.logger.error(f"Alertmanager配置重载失败: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Alertmanager配置失败: {e}")
            return False

    def create_monitoring_directories(self) -> None:
        """创建监控相关目录"""
        self.logger.info("创建监控目录...")

        directories = [
            "data/prometheus",
            "data/grafana",
            "data/alertmanager",
            "data/monitoring/logs",
            "data/monitoring/backups",
        ]

        for directory in directories:
            dir_path = project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"创建目录: {dir_path}")

    def verify_monitoring_stack(self) -> bool:
        """验证监控栈"""
        self.logger.info("验证监控栈...")

        all_healthy = True

        for service_name in ["prometheus", "grafana", "alertmanager"]:
            if not self.wait_for_service(service_name, timeout=60):
                all_healthy = False

        if all_healthy:
            self.logger.info("监控栈验证成功")
            self.print_access_info()
        else:
            self.logger.error("监控栈验证失败")

        return all_healthy

    def print_access_info(self) -> None:
        """打印访问信息"""
        print("\n" + "=" * 60)
        print("监控系统访问信息")
        print("=" * 60)

        for service_name, config in self.services.items():
            print(f"{service_name.capitalize():15}: {config['url']}")

        print("\nGrafana登录信息:")
        grafana_config = self.services["grafana"]
        print(f"用户名: {grafana_config['admin_user']}")
        print(f"密码: {grafana_config['admin_password']}")

        print("\n默认仪表板:")
        print(f"信息源爬虫监控: {grafana_config['url']}/d/info-crawler")

        print("=" * 60)

    def initialize(self) -> bool:
        """初始化监控系统"""
        self.logger.info(f"开始初始化 {self.environment} 环境监控系统")

        try:
            # 1. 创建必要目录
            self.create_monitoring_directories()

            # 2. 等待服务启动
            if not self.verify_monitoring_stack():
                return False

            # 3. 配置Prometheus
            if not self.setup_prometheus():
                return False

            # 4. 配置Grafana
            if not self.setup_grafana():
                return False

            # 5. 配置Alertmanager
            if not self.setup_alertmanager():
                return False

            self.logger.info("监控系统初始化完成")
            return True

        except Exception as e:
            self.logger.error(f"监控系统初始化失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="监控系统初始化脚本")
    parser.add_argument(
        "--env",
        "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="部署环境",
    )
    parser.add_argument("--verify-only", action="store_true", help="仅验证监控栈状态")
    parser.add_argument("--setup-grafana", action="store_true", help="仅设置Grafana")
    parser.add_argument("--setup-prometheus", action="store_true", help="仅设置Prometheus")
    parser.add_argument(
        "--setup-alertmanager", action="store_true", help="仅设置Alertmanager"
    )

    args = parser.parse_args()

    # 初始化监控系统
    initializer = MonitoringInitializer(args.env)

    try:
        if args.verify_only:
            success = initializer.verify_monitoring_stack()
        elif args.setup_grafana:
            success = initializer.setup_grafana()
        elif args.setup_prometheus:
            success = initializer.setup_prometheus()
        elif args.setup_alertmanager:
            success = initializer.setup_alertmanager()
        else:
            success = initializer.initialize()

        if success:
            print("\n✅ 监控系统初始化成功")
            sys.exit(0)
        else:
            print("\n❌ 监控系统初始化失败")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
