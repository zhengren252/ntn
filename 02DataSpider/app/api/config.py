# -*- coding: utf-8 -*-
"""
配置管理模块

提供配置管理、环境隔离、动态配置更新和配置验证功能
"""

import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, NotFound

from .middleware import require_auth, require_admin, handle_errors, validate_json
from ..config.config_manager import ConfigManager

# 创建蓝图
config_bp = Blueprint("config", __name__)


class ConfigScope(Enum):
    """配置作用域"""

    GLOBAL = "global"
    CRAWLER = "crawler"
    PROCESSOR = "processor"
    API = "api"
    MONITORING = "monitoring"


class ConfigType(Enum):
    """配置类型"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    JSON = "json"


@dataclass
class ConfigSchema:
    """配置模式定义"""

    key: str
    type: ConfigType
    description: str
    default: Any
    required: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    pattern: Optional[str] = None
    scope: ConfigScope = ConfigScope.GLOBAL


@dataclass
class ConfigChange:
    """配置变更记录"""

    key: str
    old_value: Any
    new_value: Any
    user: str
    timestamp: datetime
    reason: str
    environment: str


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        """初始化配置验证器"""
        self.schemas: Dict[str, ConfigSchema] = {}
        self._load_default_schemas()

    def _load_default_schemas(self):
        """加载默认配置模式"""
        default_schemas = [
            # 全局配置
            ConfigSchema(
                key="app.name",
                type=ConfigType.STRING,
                description="应用名称",
                default="NeuroTrade DataSpider",
                required=True,
                scope=ConfigScope.GLOBAL,
            ),
            ConfigSchema(
                key="app.version",
                type=ConfigType.STRING,
                description="应用版本",
                default="1.0.0",
                required=True,
                scope=ConfigScope.GLOBAL,
            ),
            ConfigSchema(
                key="app.environment",
                type=ConfigType.STRING,
                description="运行环境",
                default="development",
                required=True,
                choices=["development", "staging", "production"],
                scope=ConfigScope.GLOBAL,
            ),
            ConfigSchema(
                key="app.debug",
                type=ConfigType.BOOLEAN,
                description="调试模式",
                default=False,
                scope=ConfigScope.GLOBAL,
            ),
            ConfigSchema(
                key="app.log_level",
                type=ConfigType.STRING,
                description="日志级别",
                default="INFO",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                scope=ConfigScope.GLOBAL,
            ),
            # API配置
            ConfigSchema(
                key="api.host",
                type=ConfigType.STRING,
                description="API服务器地址",
                default="0.0.0.0",
                scope=ConfigScope.API,
            ),
            ConfigSchema(
                key="api.port",
                type=ConfigType.INTEGER,
                description="API服务器端口",
                default=5000,
                min_value=1,
                max_value=65535,
                scope=ConfigScope.API,
            ),
            ConfigSchema(
                key="api.workers",
                type=ConfigType.INTEGER,
                description="API工作进程数",
                default=1,
                min_value=1,
                max_value=32,
                scope=ConfigScope.API,
            ),
            ConfigSchema(
                key="api.rate_limit.requests_per_minute",
                type=ConfigType.INTEGER,
                description="每分钟请求限制",
                default=60,
                min_value=1,
                scope=ConfigScope.API,
            ),
            ConfigSchema(
                key="api.cors.enabled",
                type=ConfigType.BOOLEAN,
                description="启用CORS",
                default=True,
                scope=ConfigScope.API,
            ),
            # 爬虫配置
            ConfigSchema(
                key="crawler.concurrent_requests",
                type=ConfigType.INTEGER,
                description="并发请求数",
                default=16,
                min_value=1,
                max_value=100,
                scope=ConfigScope.CRAWLER,
            ),
            ConfigSchema(
                key="crawler.download_delay",
                type=ConfigType.FLOAT,
                description="下载延迟（秒）",
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                scope=ConfigScope.CRAWLER,
            ),
            ConfigSchema(
                key="crawler.retry_times",
                type=ConfigType.INTEGER,
                description="重试次数",
                default=3,
                min_value=0,
                max_value=10,
                scope=ConfigScope.CRAWLER,
            ),
            ConfigSchema(
                key="crawler.timeout",
                type=ConfigType.INTEGER,
                description="请求超时（秒）",
                default=30,
                min_value=5,
                max_value=300,
                scope=ConfigScope.CRAWLER,
            ),
            ConfigSchema(
                key="crawler.user_agents",
                type=ConfigType.LIST,
                description="用户代理列表",
                default=[
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                ],
                scope=ConfigScope.CRAWLER,
            ),
            # 数据处理配置
            ConfigSchema(
                key="processor.batch_size",
                type=ConfigType.INTEGER,
                description="批处理大小",
                default=100,
                min_value=1,
                max_value=1000,
                scope=ConfigScope.PROCESSOR,
            ),
            ConfigSchema(
                key="processor.max_workers",
                type=ConfigType.INTEGER,
                description="最大工作线程数",
                default=4,
                min_value=1,
                max_value=16,
                scope=ConfigScope.PROCESSOR,
            ),
            ConfigSchema(
                key="processor.cleaning_level",
                type=ConfigType.STRING,
                description="数据清洗级别",
                default="standard",
                choices=["basic", "standard", "aggressive"],
                scope=ConfigScope.PROCESSOR,
            ),
            ConfigSchema(
                key="processor.validation_level",
                type=ConfigType.STRING,
                description="数据验证级别",
                default="standard",
                choices=["basic", "standard", "strict"],
                scope=ConfigScope.PROCESSOR,
            ),
            # 监控配置
            ConfigSchema(
                key="monitoring.metrics_retention_days",
                type=ConfigType.INTEGER,
                description="指标保留天数",
                default=7,
                min_value=1,
                max_value=365,
                scope=ConfigScope.MONITORING,
            ),
            ConfigSchema(
                key="monitoring.health_check_interval",
                type=ConfigType.INTEGER,
                description="健康检查间隔（秒）",
                default=60,
                min_value=10,
                max_value=3600,
                scope=ConfigScope.MONITORING,
            ),
            ConfigSchema(
                key="monitoring.alert_thresholds.cpu_percent",
                type=ConfigType.FLOAT,
                description="CPU使用率告警阈值",
                default=80.0,
                min_value=50.0,
                max_value=95.0,
                scope=ConfigScope.MONITORING,
            ),
            ConfigSchema(
                key="monitoring.alert_thresholds.memory_percent",
                type=ConfigType.FLOAT,
                description="内存使用率告警阈值",
                default=85.0,
                min_value=50.0,
                max_value=95.0,
                scope=ConfigScope.MONITORING,
            ),
            # ZeroMQ配置
            ConfigSchema(
                key="zmq.publisher_port",
                type=ConfigType.INTEGER,
                description="ZMQ发布端口",
                default=5555,
                min_value=1024,
                max_value=65535,
                scope=ConfigScope.GLOBAL,
            ),
            ConfigSchema(
                key="zmq.high_water_mark",
                type=ConfigType.INTEGER,
                description="ZMQ高水位标记",
                default=1000,
                min_value=100,
                max_value=10000,
                scope=ConfigScope.GLOBAL,
            ),
        ]

        for schema in default_schemas:
            self.schemas[schema.key] = schema

    def validate_value(self, key: str, value: Any) -> tuple[bool, str]:
        """验证配置值

        Args:
            key: 配置键
            value: 配置值

        Returns:
            (是否有效, 错误信息)
        """
        if key not in self.schemas:
            return False, f"Unknown configuration key: {key}"

        schema = self.schemas[key]

        # 类型验证
        if not self._validate_type(value, schema.type):
            return False, f"Invalid type for {key}, expected {schema.type.value}"

        # 范围验证
        if schema.min_value is not None and isinstance(value, (int, float)):
            if value < schema.min_value:
                return False, f"Value for {key} must be >= {schema.min_value}"

        if schema.max_value is not None and isinstance(value, (int, float)):
            if value > schema.max_value:
                return False, f"Value for {key} must be <= {schema.max_value}"

        # 选择验证
        if schema.choices and value not in schema.choices:
            return False, f"Value for {key} must be one of {schema.choices}"

        # 模式验证（正则表达式）
        if schema.pattern and isinstance(value, str):
            import re

            if not re.match(schema.pattern, value):
                return False, f"Value for {key} does not match pattern {schema.pattern}"

        return True, ""

    def _validate_type(self, value: Any, expected_type: ConfigType) -> bool:
        """验证值类型"""
        if expected_type == ConfigType.STRING:
            return isinstance(value, str)
        elif expected_type == ConfigType.INTEGER:
            return isinstance(value, int)
        elif expected_type == ConfigType.FLOAT:
            return isinstance(value, (int, float))
        elif expected_type == ConfigType.BOOLEAN:
            return isinstance(value, bool)
        elif expected_type == ConfigType.LIST:
            return isinstance(value, list)
        elif expected_type == ConfigType.DICT:
            return isinstance(value, dict)
        elif expected_type == ConfigType.JSON:
            try:
                json.dumps(value)
                return True
            except (TypeError, ValueError):
                return False

        return False

    def get_schema(self, key: str) -> Optional[ConfigSchema]:
        """获取配置模式"""
        return self.schemas.get(key)

    def get_schemas_by_scope(self, scope: ConfigScope) -> List[ConfigSchema]:
        """按作用域获取配置模式"""
        return [schema for schema in self.schemas.values() if schema.scope == scope]

    def add_schema(self, schema: ConfigSchema):
        """添加配置模式"""
        self.schemas[schema.key] = schema


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "config"):
        """初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.validator = ConfigValidator()
        self.change_history: List[ConfigChange] = []
        self.configs: Dict[str, Dict[str, Any]] = {}

        # 加载所有环境配置
        self._load_all_configs()

    def _load_all_configs(self):
        """加载所有环境配置"""
        environments = ["development", "staging", "production"]

        for env in environments:
            self.configs[env] = self._load_config(env)

    def _load_config(self, environment: str) -> Dict[str, Any]:
        """加载指定环境配置

        Args:
            environment: 环境名称

        Returns:
            配置字典
        """
        config_file = self.config_dir / f"{environment}.yaml"

        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                current_app.logger_instance.error(f"加载配置文件失败 {config_file}: {e}")
                return {}
        else:
            # 创建默认配置文件
            default_config = self._get_default_config()
            self._save_config(environment, default_config)
            return default_config

    def _save_config(self, environment: str, config: Dict[str, Any]):
        """保存配置到文件

        Args:
            environment: 环境名称
            config: 配置字典
        """
        config_file = self.config_dir / f"{environment}.yaml"

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            current_app.logger_instance.error(f"保存配置文件失败 {config_file}: {e}")
            raise

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        config = {}

        for schema in self.validator.schemas.values():
            # 使用点号分隔的键创建嵌套字典
            keys = schema.key.split(".")
            current = config

            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            current[keys[-1]] = schema.default

        return config

    def get_config(self, environment: str, key: str = None) -> Any:
        """获取配置值

        Args:
            environment: 环境名称
            key: 配置键，如果为None则返回所有配置

        Returns:
            配置值
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]

        if key is None:
            return config

        # 支持点号分隔的键
        keys = key.split(".")
        current = config

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            # 如果键不存在，返回默认值
            schema = self.validator.get_schema(key)
            if schema:
                return schema.default
            raise KeyError(f"Configuration key not found: {key}")

    def set_config(
        self,
        environment: str,
        key: str,
        value: Any,
        user: str = "system",
        reason: str = "",
    ):
        """设置配置值

        Args:
            environment: 环境名称
            key: 配置键
            value: 配置值
            user: 操作用户
            reason: 变更原因
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        # 验证配置值
        is_valid, error_msg = self.validator.validate_value(key, value)
        if not is_valid:
            raise ValueError(error_msg)

        # 获取旧值
        try:
            old_value = self.get_config(environment, key)
        except KeyError:
            old_value = None

        # 设置新值
        config = self.configs[environment]
        keys = key.split(".")
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

        # 保存到文件
        self._save_config(environment, config)

        # 记录变更历史
        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=value,
            user=user,
            timestamp=datetime.utcnow(),
            reason=reason,
            environment=environment,
        )
        self.change_history.append(change)

        current_app.logger_instance.info(
            f"配置变更: {environment}.{key} = {value} (用户: {user}, 原因: {reason})"
        )

    def delete_config(
        self, environment: str, key: str, user: str = "system", reason: str = ""
    ):
        """删除配置项

        Args:
            environment: 环境名称
            key: 配置键
            user: 操作用户
            reason: 删除原因
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        # 获取旧值
        try:
            old_value = self.get_config(environment, key)
        except KeyError:
            return  # 键不存在，无需删除

        # 删除配置项
        config = self.configs[environment]
        keys = key.split(".")
        current = config

        try:
            for k in keys[:-1]:
                current = current[k]
            del current[keys[-1]]
        except (KeyError, TypeError):
            return  # 键不存在

        # 保存到文件
        self._save_config(environment, config)

        # 记录变更历史
        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=None,
            user=user,
            timestamp=datetime.utcnow(),
            reason=reason,
            environment=environment,
        )
        self.change_history.append(change)

        current_app.logger_instance.info(
            f"配置删除: {environment}.{key} (用户: {user}, 原因: {reason})"
        )

    def get_change_history(
        self, environment: str = None, key: str = None, limit: int = 100
    ) -> List[ConfigChange]:
        """获取配置变更历史

        Args:
            environment: 环境名称过滤
            key: 配置键过滤
            limit: 返回数量限制

        Returns:
            变更历史列表
        """
        history = self.change_history

        # 过滤
        if environment:
            history = [
                change for change in history if change.environment == environment
            ]

        if key:
            history = [change for change in history if change.key == key]

        # 按时间倒序排列
        history.sort(key=lambda x: x.timestamp, reverse=True)

        return history[:limit]

    def export_config(self, environment: str, format: str = "yaml") -> str:
        """导出配置

        Args:
            environment: 环境名称
            format: 导出格式 (yaml, json)

        Returns:
            配置字符串
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]

        if format.lower() == "json":
            return json.dumps(config, indent=2, ensure_ascii=False)
        elif format.lower() == "yaml":
            return yaml.dump(config, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def import_config(
        self,
        environment: str,
        config_data: str,
        format: str = "yaml",
        user: str = "system",
        reason: str = "批量导入",
    ):
        """导入配置

        Args:
            environment: 环境名称
            config_data: 配置数据
            format: 数据格式 (yaml, json)
            user: 操作用户
            reason: 导入原因
        """
        try:
            if format.lower() == "json":
                new_config = json.loads(config_data)
            elif format.lower() == "yaml":
                new_config = yaml.safe_load(config_data)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            raise ValueError(f"Failed to parse config data: {e}")

        # 验证所有配置项
        def validate_nested_config(config_dict, prefix=""):
            for key, value in config_dict.items():
                full_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    validate_nested_config(value, full_key)
                else:
                    is_valid, error_msg = self.validator.validate_value(full_key, value)
                    if not is_valid:
                        raise ValueError(f"Invalid config {full_key}: {error_msg}")

        validate_nested_config(new_config)

        # 备份当前配置
        old_config = self.configs[environment].copy()

        # 应用新配置
        self.configs[environment] = new_config

        # 保存到文件
        self._save_config(environment, new_config)

        # 记录变更历史
        change = ConfigChange(
            key="*",
            old_value=old_config,
            new_value=new_config,
            user=user,
            timestamp=datetime.utcnow(),
            reason=reason,
            environment=environment,
        )
        self.change_history.append(change)

        current_app.logger_instance.info(
            f"配置批量导入: {environment} (用户: {user}, 原因: {reason})"
        )


# 全局配置管理器实例
config_manager = ConfigManager()


@config_bp.route("/environments", methods=["GET"])
@require_auth
@handle_errors
def get_environments():
    """获取所有环境列表"""
    environments = list(config_manager.configs.keys())

    return jsonify({"environments": environments, "total": len(environments)})


@config_bp.route("/environments/<environment>", methods=["GET"])
@require_auth
@handle_errors
def get_environment_config(environment: str):
    """获取指定环境的配置"""
    try:
        config = config_manager.get_config(environment)

        return jsonify(
            {
                "environment": environment,
                "config": config,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except ValueError as e:
        raise NotFound(str(e))


@config_bp.route("/environments/<environment>/keys/<path:key>", methods=["GET"])
@require_auth
@handle_errors
def get_config_value(environment: str, key: str):
    """获取指定配置项的值"""
    try:
        value = config_manager.get_config(environment, key)
        schema = config_manager.validator.get_schema(key)

        return jsonify(
            {
                "environment": environment,
                "key": key,
                "value": value,
                "schema": asdict(schema) if schema else None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except (ValueError, KeyError) as e:
        raise NotFound(str(e))


@config_bp.route("/environments/<environment>/keys/<path:key>", methods=["PUT"])
@require_admin
@validate_json
@handle_errors
def set_config_value(environment: str, key: str):
    """设置指定配置项的值"""
    data = request.get_json()
    value = data.get("value")
    user = data.get("user", "api")
    reason = data.get("reason", "通过API更新")

    if value is None:
        raise BadRequest("Missing 'value' field")

    try:
        config_manager.set_config(environment, key, value, user, reason)

        return jsonify(
            {
                "environment": environment,
                "key": key,
                "value": value,
                "user": user,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except ValueError as e:
        raise BadRequest(str(e))


@config_bp.route("/environments/<environment>/keys/<path:key>", methods=["DELETE"])
@require_admin
@handle_errors
def delete_config_value(environment: str, key: str):
    """删除指定配置项"""
    user = request.args.get("user", "api")
    reason = request.args.get("reason", "通过API删除")

    try:
        config_manager.delete_config(environment, key, user, reason)

        return jsonify(
            {
                "environment": environment,
                "key": key,
                "user": user,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except ValueError as e:
        raise BadRequest(str(e))


@config_bp.route("/environments/<environment>/export", methods=["GET"])
@require_auth
@handle_errors
def export_config(environment: str):
    """导出环境配置"""
    format = request.args.get("format", "yaml").lower()

    if format not in ["yaml", "json"]:
        raise BadRequest("Format must be 'yaml' or 'json'")

    try:
        config_data = config_manager.export_config(environment, format)

        return jsonify(
            {
                "environment": environment,
                "format": format,
                "data": config_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except ValueError as e:
        raise NotFound(str(e))


@config_bp.route("/environments/<environment>/import", methods=["POST"])
@require_admin
@validate_json
@handle_errors
def import_config(environment: str):
    """导入环境配置"""
    data = request.get_json()
    config_data = data.get("data")
    format = data.get("format", "yaml").lower()
    user = data.get("user", "api")
    reason = data.get("reason", "通过API导入")

    if not config_data:
        raise BadRequest("Missing 'data' field")

    if format not in ["yaml", "json"]:
        raise BadRequest("Format must be 'yaml' or 'json'")

    try:
        config_manager.import_config(environment, config_data, format, user, reason)

        return jsonify(
            {
                "environment": environment,
                "format": format,
                "user": user,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except ValueError as e:
        raise BadRequest(str(e))


@config_bp.route("/schemas", methods=["GET"])
@require_auth
@handle_errors
def get_config_schemas():
    """获取配置模式"""
    scope = request.args.get("scope")

    if scope:
        try:
            scope_enum = ConfigScope(scope)
            schemas = config_manager.validator.get_schemas_by_scope(scope_enum)
        except ValueError:
            raise BadRequest(f"Invalid scope: {scope}")
    else:
        schemas = list(config_manager.validator.schemas.values())

    schemas_data = [asdict(schema) for schema in schemas]

    return jsonify(
        {"schemas": schemas_data, "total": len(schemas_data), "scope": scope}
    )


@config_bp.route("/schemas/<path:key>", methods=["GET"])
@require_auth
@handle_errors
def get_config_schema(key: str):
    """获取指定配置项的模式"""
    schema = config_manager.validator.get_schema(key)

    if not schema:
        raise NotFound(f"Schema not found for key: {key}")

    return jsonify({"key": key, "schema": asdict(schema)})


@config_bp.route("/history", methods=["GET"])
@require_auth
@handle_errors
def get_change_history():
    """获取配置变更历史"""
    environment = request.args.get("environment")
    key = request.args.get("key")
    limit = min(int(request.args.get("limit", 100)), 1000)

    history = config_manager.get_change_history(environment, key, limit)

    history_data = []
    for change in history:
        history_data.append(
            {
                "key": change.key,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "user": change.user,
                "timestamp": change.timestamp.isoformat(),
                "reason": change.reason,
                "environment": change.environment,
            }
        )

    return jsonify(
        {
            "history": history_data,
            "total": len(history_data),
            "filters": {"environment": environment, "key": key, "limit": limit},
        }
    )


@config_bp.route("/validate", methods=["POST"])
@require_auth
@validate_json
@handle_errors
def validate_config():
    """验证配置值"""
    data = request.get_json()
    key = data.get("key")
    value = data.get("value")

    if not key:
        raise BadRequest("Missing 'key' field")

    if value is None:
        raise BadRequest("Missing 'value' field")

    is_valid, error_msg = config_manager.validator.validate_value(key, value)
    schema = config_manager.validator.get_schema(key)

    return jsonify(
        {
            "key": key,
            "value": value,
            "valid": is_valid,
            "error": error_msg if not is_valid else None,
            "schema": asdict(schema) if schema else None,
        }
    )


if __name__ == "__main__":
    # 测试配置管理功能
    print("测试配置管理模块...")

    # 创建配置管理器
    manager = ConfigManager("test_config")

    print("\n测试配置获取...")
    try:
        app_name = manager.get_config("development", "app.name")
        print(f"应用名称: {app_name}")

        api_port = manager.get_config("development", "api.port")
        print(f"API端口: {api_port}")
    except Exception as e:
        print(f"获取配置失败: {e}")

    print("\n测试配置设置...")
    try:
        manager.set_config("development", "test.key", "test_value", "test_user", "测试设置")
        print("配置设置成功")
    except Exception as e:
        print(f"设置配置失败: {e}")
