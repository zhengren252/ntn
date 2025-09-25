# 环境配置管理器
# 实现development/staging/production三环境隔离
# 严格遵循数据隔离与环境管理规范

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
import yaml
from dotenv import load_dotenv
import threading
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)


class Environment(Enum):
    """环境类型枚举"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentManager:
    """环境配置管理器 - 实现三环境隔离"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.current_env = self._detect_environment()
        self.config = {}
        # 环境变量别名映射（优先级高于标准键）
        # 允许通过更直观的变量名覆盖配置，如 SCAN_WEB_PORT 覆盖 web.port
        self.env_alias_map: Dict[str, list[str]] = {
            "web.port": ["SCAN_WEB_PORT", "WEB_PORT", "PORT"],
            # ZeroMQ 端口别名（仅对绑定端口生效）
            "zmq.publisher.port": ["ZMQ_PUBLISHER_PORT"],
            "zmq.reply.port": ["ZMQ_REPLY_PORT"],
            # Redis 常见别名
            "redis.url": ["REDIS_URL"],
            "redis.host": ["REDIS_HOST"],
            "redis.port": ["REDIS_PORT"],
            "redis.password": ["REDIS_PASSWORD"],
            # Logging 常见别名
            "logging.level": ["LOG_LEVEL", "SCANNER_LOG_LEVEL"],
            "logging.format": ["LOG_FORMAT", "SCANNER_LOG_FORMAT"],
            "logging.console.enabled": ["LOG_CONSOLE", "LOG_TO_CONSOLE"],
            "logging.console.colorize": ["LOG_COLOR", "LOG_COLORIZE"],
            "logging.file.enabled": ["LOG_FILE_ENABLED", "LOG_TO_FILE"],
            "logging.file.path": ["LOG_FILE_PATH"],
            "logging.file.max_size": ["LOG_MAX_SIZE", "LOG_FILE_MAX_SIZE"],
            "logging.file.backup_count": ["LOG_BACKUP_COUNT"],
        }

        # 加载环境变量
        self._load_env_files()

        # 加载配置文件
        self._load_config_files()

        logger.info(
            "EnvironmentManager initialized",
            environment=self.current_env.value,
            config_dir=str(self.config_dir),
        )

    def _detect_environment(self) -> Environment:
        """检测当前环境"""
        env_name = os.getenv("SCANNER_ENV", "development").lower()

        try:
            return Environment(env_name)
        except ValueError:
            logger.warning(
                "Invalid environment name, defaulting to development", env_name=env_name
            )
            return Environment.DEVELOPMENT

    def _load_env_files(self) -> None:
        """加载环境变量文件"""
        # 按优先级加载.env文件
        env_files = [
            self.config_dir / ".env",  # 通用配置
            self.config_dir / f".env.{self.current_env.value}",  # 环境特定配置
            self.config_dir / ".env.local",  # 本地覆盖配置
        ]

        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file, override=True)
                logger.debug("Loaded env file", file=str(env_file))

    def _load_config_files(self) -> None:
        """加载YAML配置文件"""
        # 按优先级加载配置文件
        config_files = [
            self.config_dir / "config.yaml",  # 基础配置
            self.config_dir / f"config.{self.current_env.value}.yaml",  # 环境特定配置
            self.config_dir / "config.local.yaml",  # 本地覆盖配置
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        file_config = yaml.safe_load(f) or {}

                    # 深度合并配置
                    self._deep_merge(self.config, file_config)
                    logger.debug("Loaded config file", file=str(config_file))

                except Exception as e:
                    logger.error(
                        "Failed to load config file",
                        file=str(config_file),
                        error=str(e),
                    )

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """深度合并字典"""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            key: 配置键，支持点分隔的嵌套键（如 'redis.host'）
            default: 默认值

        Returns:
            配置值
        """
        # 1) 环境变量别名优先
        for alias in self.env_alias_map.get(key, []):
            alias_value = os.getenv(alias)
            if alias_value is not None and alias_value != "":
                return self._convert_env_value(alias_value)

        # 2) 标准环境变量名（点->下划线 + 大写）
        env_key = key.upper().replace(".", "_")
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._convert_env_value(env_value)

        # 3) 配置文件
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def _convert_env_value(self, value: str) -> Any:
        """转换环境变量值类型"""
        # 布尔值转换
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        elif value.lower() in ("false", "no", "0", "off"):
            return False

        # 数字转换
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # 列表转换（逗号分隔）
        if "," in value:
            return [item.strip() for item in value.split(",")]

        return value

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        # 优先支持统一的 REDIS_URL/redis.url，允许形如：
        # redis://[:password@]host:port[/db] 或 rediss://
        url_value = self.get_config("redis.url")
        parsed_host = None
        parsed_port = None
        parsed_db = None
        parsed_password = None
        parsed_ssl = False

        if isinstance(url_value, str) and url_value.strip():
            try:
                parsed = urlparse(url_value)
                if parsed.scheme in ("redis", "rediss"):
                    parsed_host = parsed.hostname or "localhost"
                    parsed_port = parsed.port or 6379
                    # 处理路径中的数据库索引，例如 "/0"
                    if parsed.path and parsed.path.strip("/").isdigit():
                        parsed_db = int(parsed.path.strip("/"))
                    else:
                        parsed_db = 0
                    # 优先使用URL中的密码（若存在）
                    parsed_password = parsed.password
                    parsed_ssl = parsed.scheme == "rediss"
                else:
                    logger.warning("Unsupported Redis URL scheme, fallback to host/port", scheme=parsed.scheme)
            except Exception as e:
                logger.warning("Failed to parse REDIS_URL, fallback to host/port", error=str(e))

        # 组装基础配置（若URL可用则使用解析结果，否则读取分散配置）
        host = parsed_host if parsed_host is not None else self.get_config("redis.host", "localhost")
        port = int(parsed_port if parsed_port is not None else self.get_config("redis.port", 6379))
        database = int(parsed_db if parsed_db is not None else self.get_config("redis.database", 0))
        # 若显式提供 redis.password/REDIS_PASSWORD，则覆盖 URL 中的密码
        password = self.get_config("redis.password", parsed_password)

        base_config = {
            "host": host,
            "port": port,
            "database": database,
            "password": password,
            "ssl": bool(parsed_ssl),
            "socket_timeout": int(self.get_config("redis.socket_timeout", 5)),
            "socket_connect_timeout": int(
                self.get_config("redis.socket_connect_timeout", 5)
            ),
            "retry_on_timeout": self.get_config("redis.retry_on_timeout", True),
            "health_check_interval": int(
                self.get_config("redis.health_check_interval", 30)
            ),
            "key_prefix": f"scanner_{self.current_env.value}",  # 环境隔离
            "default_ttl": int(self.get_config("redis.default_ttl", 3600)),
            "ttl": {
                "scan_result": int(self.get_config("redis.ttl.scan_result", 3600)),
                "market_data": int(self.get_config("redis.ttl.market_data", 300)),
                "news_events": int(self.get_config("redis.ttl.news_events", 1800)),
            },
        }

        return base_config

    def get_zmq_config(self) -> Dict[str, Any]:
        """获取ZeroMQ配置"""
        base_config = {
            "publisher": {
                "host": self.get_config("zmq.publisher.host", "localhost"),
                "port": self.get_config("zmq.publisher.port", 5555),
                "bind": self.get_config("zmq.publisher.bind", True),
            },
            "subscriber": {
                "host": self.get_config("zmq.subscriber.host", "localhost"),
                "port": self.get_config("zmq.subscriber.port", 5556),
                "topics": self.get_config(
                    "zmq.subscriber.topics", ["market_data", "news_events"]
                ),
            },
            "request": {
                "host": self.get_config("zmq.request.host", "localhost"),
                "port": self.get_config("zmq.request.port", 5557),
                "timeout": self.get_config("zmq.request.timeout", 5000),
            },
            "reply": {
                "host": self.get_config("zmq.reply.host", "localhost"),
                "port": self.get_config("zmq.reply.port", 5558),
                "bind": self.get_config("zmq.reply.bind", True),
            },
            "heartbeat_interval": self.get_config("zmq.heartbeat_interval", 30),
            "max_retries": self.get_config("zmq.max_retries", 3),
        }

        return base_config

    def get_scanner_config(self) -> Dict[str, Any]:
        """获取扫描器配置"""
        base_config = {
            "rules": {
                "three_high": {
                    "volatility_threshold": self.get_config(
                        "scanner.rules.three_high.volatility_threshold", 0.05
                    ),
                    "volume_threshold": self.get_config(
                        "scanner.rules.three_high.volume_threshold", 1000000
                    ),
                    "correlation_threshold": self.get_config(
                        "scanner.rules.three_high.correlation_threshold", 0.7
                    ),
                    "enabled": self.get_config(
                        "scanner.rules.three_high.enabled", True
                    ),
                },
                "black_horse": {
                    "price_change_threshold": self.get_config(
                        "scanner.rules.black_horse.price_change_threshold", 0.15
                    ),
                    "volume_spike_threshold": self.get_config(
                        "scanner.rules.black_horse.volume_spike_threshold", 3.0
                    ),
                    "news_sentiment_threshold": self.get_config(
                        "scanner.rules.black_horse.news_sentiment_threshold", 0.6
                    ),
                    "enabled": self.get_config(
                        "scanner.rules.black_horse.enabled", True
                    ),
                },
                "potential_finder": {
                    "market_cap_threshold": self.get_config(
                        "scanner.rules.potential_finder.market_cap_threshold", 5e8
                    ),
                    "momentum_window": self.get_config(
                        "scanner.rules.potential_finder.momentum_window", 14
                    ),
                    "enabled": self.get_config(
                        "scanner.rules.potential_finder.enabled", True
                    ),
                },
            },
            "performance": {
                "concurrency": self.get_config("scanner.performance.concurrency", 4),
                "batch_size": self.get_config("scanner.performance.batch_size", 100),
                "rate_limit": self.get_config("scanner.performance.rate_limit", 50),
            },
            "features": {
                "enable_news_sentiment": self.get_config(
                    "scanner.features.enable_news_sentiment", True
                ),
                "enable_market_correlation": self.get_config(
                    "scanner.features.enable_market_correlation", True
                ),
            },
        }

        return base_config

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置

        返回结构需与 scanner.utils.logger.StructuredLogger 期望保持一致：
        {
            "name": str,
            "level": "DEBUG"|"INFO"|...,
            "format": "json"|"text",
            "console": {"enabled": bool, "colorize": bool},
            "file": {"enabled": bool, "path": str, "max_size": str, "backup_count": int}
        }
        """
        level = str(self.get_config("logging.level", "INFO")).upper()
        log_format = self.get_config("logging.format", "json")

        config: Dict[str, Any] = {
            "name": self.get_config("logging.name", "scanner"),
            "level": level,
            "format": log_format,
            "console": {
                "enabled": self.get_config("logging.console.enabled", True),
                "colorize": self.get_config("logging.console.colorize", False),
            },
            "file": {
                "enabled": self.get_config("logging.file.enabled", True),
                "path": self.get_config("logging.file.path", "logs/scanner.log"),
                "max_size": self.get_config("logging.file.max_size", "10MB"),
                "backup_count": int(self.get_config("logging.file.backup_count", 5)),
            },
        }

        # 兜底：不允许未知格式，自动回退到 json
        if config["format"] not in ("json", "text"):
            config["format"] = "json"

        return config

    # 新增：提供统一获取当前环境的方法，供外部调用（例如 main.py 中的日志）
    def get_environment(self) -> Environment:
        return self.current_env

    # 新增：配置完整性校验，返回结构需包含 valid/warnings/errors
    def validate_config(self) -> Dict[str, Any]:
        warnings: list[str] = []
        errors: list[str] = []
        details: Dict[str, Any] = {}

        try:
            # 基础分组配置获取（使用转换后的访问以规避文件结构差异）
            logging_cfg = self.get_logging_config()
            zmq_cfg = self.get_zmq_config()
            redis_cfg = self.get_redis_config()
            scanner_cfg = self.get_scanner_config()

            details["environment"] = self.current_env.value

            # 1) Logging 校验
            if logging_cfg["format"] not in ("json", "text"):
                errors.append("logging.format must be 'json' or 'text'")
            if not isinstance(logging_cfg.get("level"), str):
                errors.append("logging.level must be a string")
            # 文件日志目录存在性（仅警告，不阻断）
            if logging_cfg.get("file", {}).get("enabled"):
                log_path = logging_cfg["file"].get("path", "logs/scanner.log")
                log_dir = str(Path(log_path).parent)
                if not Path(log_dir).exists():
                    warnings.append(f"Log directory does not exist: {log_dir}")

            # 2) Redis 校验
            if not redis_cfg.get("host"):
                errors.append("redis.host is required")
            try:
                port = int(redis_cfg.get("port", 6379))
                if port <= 0 or port > 65535:
                    errors.append("redis.port must be in range 1-65535")
            except Exception:
                errors.append("redis.port must be an integer")
            # 生产环境下，缺少密码给出警告（允许无密码，视部署而定）
            if self.current_env == Environment.PRODUCTION and not redis_cfg.get("password"):
                warnings.append("Production environment without redis.password configured")

            # 3) ZMQ 校验（检查常用端口字段与范围）
            def _check_port(name: str, value: Any):
                try:
                    p = int(value)
                    if p < 1 or p > 65535:
                        errors.append(f"{name} must be in range 1-65535")
                except Exception:
                    errors.append(f"{name} must be an integer")

            _check_port("zmq.publisher.port", zmq_cfg.get("publisher", {}).get("port", 5555))
            _check_port("zmq.subscriber.port", zmq_cfg.get("subscriber", {}).get("port", 5556))
            _check_port("zmq.request.port", zmq_cfg.get("request", {}).get("port", 5557))
            _check_port("zmq.reply.port", zmq_cfg.get("reply", {}).get("port", 5558))

            # 4) 扫描器规则校验
            rules = scanner_cfg.get("rules", {})
            for rule_key in ("three_high", "black_horse", "potential_finder"):
                if rule_key not in rules:
                    errors.append(f"Missing scanner.rules.{rule_key} configuration")
                    continue
                if not isinstance(rules[rule_key].get("enabled", True), bool):
                    errors.append(f"scanner.rules.{rule_key}.enabled must be a boolean")
            # 若所有规则均禁用，发出警告（允许降级运行）
            if all(not rules.get(k, {}).get("enabled", True) for k in rules.keys() or []):
                warnings.append("All scanner rules are disabled; service will run with no active detectors")

            # 5) 生产环境额外约束（尽量只给警告，避免阻断启动）
            if self.current_env == Environment.PRODUCTION:
                if not logging_cfg.get("file", {}).get("enabled", True):
                    warnings.append("Production environment with file logging disabled")

            valid = len(errors) == 0
            result = {"valid": valid, "warnings": warnings, "errors": errors, "details": details}

            # 记录日志（结构化）
            if valid:
                logger.info("Configuration validation passed", warnings_count=len(warnings))
            else:
                logger.error("Configuration validation failed", errors=errors, warnings=warnings)

            return result

        except Exception as e:
            logger.error("Configuration validation encountered exception", error=str(e))
            return {"valid": False, "warnings": warnings, "errors": [str(e)], "details": {}}

# -----------------------------
# 工厂方法与单例（线程安全）
# -----------------------------
_ENV_MANAGER_SINGLETON: Optional[EnvironmentManager] = None
_ENV_MANAGER_LOCK = threading.Lock()


def get_env_manager(config_dir: Optional[str] = None) -> EnvironmentManager:
    """获取 EnvironmentManager 的线程安全单例。

    优先使用首次创建时的 config_dir，后续传入不同的目录将被忽略并记录告警。
    """
    global _ENV_MANAGER_SINGLETON

    if _ENV_MANAGER_SINGLETON is not None:
        if config_dir is not None and Path(config_dir) != _ENV_MANAGER_SINGLETON.config_dir:
            logger.warning(
                "get_env_manager called with a different config_dir; ignoring and using existing singleton",
                requested=str(config_dir),
                current=str(_ENV_MANAGER_SINGLETON.config_dir),
            )
        return _ENV_MANAGER_SINGLETON

    with _ENV_MANAGER_LOCK:
        if _ENV_MANAGER_SINGLETON is None:
            _ENV_MANAGER_SINGLETON = EnvironmentManager(config_dir=config_dir)
            logger.info(
                "EnvironmentManager singleton created",
                config_dir=str(_ENV_MANAGER_SINGLETON.config_dir),
                environment=_ENV_MANAGER_SINGLETON.current_env.value,
            )
        return _ENV_MANAGER_SINGLETON
