#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略优化模组配置文件
定义系统配置、环境设置和参数

遵循NeuroTrade Nexus核心设计理念：
1. 三环境隔离 (development/staging/production)
2. 数据隔离与环境管理
3. ZeroMQ消息总线配置
4. Docker容器化配置
5. 微服务架构配置
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
LOGS_ROOT = PROJECT_ROOT / "logs"
CONFIG_ROOT = PROJECT_ROOT / "config"

# 环境配置
ENVIRONMENT = os.getenv("NTN_ENVIRONMENT", "development")
VERSION = "1.0.0"


@dataclass
class ZeroMQConfig:
    """ZeroMQ消息总线配置"""

    # 发布者端口
    publisher_port: int
    # 订阅者端口
    subscriber_port: int
    # 请求-响应端口
    req_rep_port: int
    # 推送-拉取端口
    push_pull_port: int
    # 连接超时时间（毫秒）
    connection_timeout: int
    # 消息重试次数
    retry_attempts: int
    # 高水位标记
    high_water_mark: int


@dataclass
class DatabaseConfig:
    """数据库配置"""

    # SQLite数据库路径
    sqlite_path: str
    # Redis配置
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str
    # 连接池配置
    max_connections: int
    connection_timeout: int


@dataclass
class BacktestConfig:
    """回测配置"""

    # 默认回测期间（天）
    default_period_days: int
    # 初始资金
    initial_capital: float
    # 手续费率
    commission_rate: float
    # 滑点
    slippage: float
    # 最大并发回测数量
    max_concurrent_backtests: int
    # VectorBT配置
    vectorbt_config: Dict[str, Any]


@dataclass
class OptimizationConfig:
    """优化配置"""

    # 遗传算法配置
    genetic_algorithm: Dict[str, Any]
    # 网格搜索配置
    grid_search: Dict[str, Any]
    # 贝叶斯优化配置
    bayesian_optimization: Dict[str, Any]
    # 最大优化时间（秒）
    max_optimization_time: int
    # Groq LPU配置
    groq_config: Dict[str, Any]


@dataclass
class RiskConfig:
    """风险控制配置"""

    # 最大仓位大小
    max_position_size: float
    # 最大日损失
    max_daily_loss: float
    # 最大回撤阈值
    max_drawdown_threshold: float
    # 最小置信度阈值
    min_confidence_threshold: float
    # 压力测试场景
    stress_test_scenarios: List[Dict[str, Any]]


@dataclass
class LoggingConfig:
    """日志配置"""

    level: str
    format: str
    file_path: str
    max_file_size: int
    backup_count: int
    console_output: bool


class Config:
    """主配置类"""

    def __init__(self, environment: str = None):
        self.environment = environment or ENVIRONMENT
        self.version = VERSION
        self.project_root = PROJECT_ROOT

        # 根据环境加载配置
        self._load_environment_config()

    def _load_environment_config(self):
        """根据环境加载配置"""
        if self.environment == "development":
            self._load_development_config()
        elif self.environment == "staging":
            self._load_staging_config()
        elif self.environment == "production":
            self._load_production_config()
        elif self.environment == "test":
            self._load_test_config()
        else:
            raise ValueError(f"未知环境: {self.environment}")

    def _load_development_config(self):
        """开发环境配置"""
        # ZeroMQ配置
        self.zeromq = ZeroMQConfig(
            publisher_port=5555,
            subscriber_port=5556,
            req_rep_port=5557,
            push_pull_port=5558,
            connection_timeout=5000,
            retry_attempts=3,
            high_water_mark=1000,
        )

        # 数据库配置
        self.database = DatabaseConfig(
            sqlite_path=str(DATA_ROOT / "dev" / "optimizer.db"),
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password="",
            max_connections=10,
            connection_timeout=30,
        )

        # 回测配置
        self.backtest = BacktestConfig(
            default_period_days=365,
            initial_capital=100000.0,
            commission_rate=0.001,
            slippage=0.0001,
            max_concurrent_backtests=4,
            vectorbt_config={
                "caching": True,
                "silence_warnings": False,
                "chunk_len": 1000,
            },
        )

        # 优化配置
        self.optimization = OptimizationConfig(
            genetic_algorithm={
                "population_size": 50,
                "generations": 20,
                "crossover_rate": 0.8,
                "mutation_rate": 0.1,
                "elite_ratio": 0.1,
            },
            grid_search={"max_combinations": 1000, "parallel_jobs": 4},
            bayesian_optimization={
                "n_calls": 50,
                "n_initial_points": 10,
                "acquisition_function": "EI",
            },
            max_optimization_time=3600,
            groq_config={
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "model": "llama-3.1-70b-versatile",
                "max_tokens": 1000,
                "temperature": 0.1,
            },
        )

        # 风险控制配置
        self.risk = RiskConfig(
            max_position_size=0.1,
            max_daily_loss=0.02,
            max_drawdown_threshold=0.05,
            min_confidence_threshold=0.6,
            stress_test_scenarios=[
                {
                    "name": "2008_financial_crisis",
                    "market_drop": -0.4,
                    "volatility_spike": 3.0,
                    "duration_days": 180,
                },
                {
                    "name": "2020_covid_crash",
                    "market_drop": -0.35,
                    "volatility_spike": 2.5,
                    "duration_days": 60,
                },
                {
                    "name": "2022_crypto_winter",
                    "market_drop": -0.7,
                    "volatility_spike": 4.0,
                    "duration_days": 365,
                },
            ],
        )

        # 日志配置
        self.logging = LoggingConfig(
            level="DEBUG",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file_path=str(LOGS_ROOT / "dev" / "optimizer.log"),
            max_file_size=10 * 1024 * 1024,  # 10MB
            backup_count=5,
            console_output=True,
        )

    def _load_staging_config(self):
        """预发布环境配置"""
        # ZeroMQ配置
        self.zeromq = ZeroMQConfig(
            publisher_port=6555,
            subscriber_port=6556,
            req_rep_port=6557,
            push_pull_port=6558,
            connection_timeout=10000,
            retry_attempts=5,
            high_water_mark=5000,
        )

        # 数据库配置
        self.database = DatabaseConfig(
            sqlite_path=str(DATA_ROOT / "staging" / "optimizer.db"),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=1,
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            max_connections=20,
            connection_timeout=60,
        )

        # 回测配置
        self.backtest = BacktestConfig(
            default_period_days=730,
            initial_capital=500000.0,
            commission_rate=0.0008,
            slippage=0.0001,
            max_concurrent_backtests=8,
            vectorbt_config={
                "caching": True,
                "silence_warnings": True,
                "chunk_len": 2000,
            },
        )

        # 优化配置
        self.optimization = OptimizationConfig(
            genetic_algorithm={
                "population_size": 100,
                "generations": 50,
                "crossover_rate": 0.8,
                "mutation_rate": 0.1,
                "elite_ratio": 0.1,
            },
            grid_search={"max_combinations": 5000, "parallel_jobs": 8},
            bayesian_optimization={
                "n_calls": 100,
                "n_initial_points": 20,
                "acquisition_function": "EI",
            },
            max_optimization_time=7200,
            groq_config={
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "model": "llama-3.1-70b-versatile",
                "max_tokens": 2000,
                "temperature": 0.1,
            },
        )

        # 风险控制配置
        self.risk = RiskConfig(
            max_position_size=0.08,
            max_daily_loss=0.015,
            max_drawdown_threshold=0.04,
            min_confidence_threshold=0.7,
            stress_test_scenarios=[
                {
                    "name": "2008_financial_crisis",
                    "market_drop": -0.4,
                    "volatility_spike": 3.0,
                    "duration_days": 180,
                },
                {
                    "name": "2020_covid_crash",
                    "market_drop": -0.35,
                    "volatility_spike": 2.5,
                    "duration_days": 60,
                },
                {
                    "name": "2022_crypto_winter",
                    "market_drop": -0.7,
                    "volatility_spike": 4.0,
                    "duration_days": 365,
                },
                {
                    "name": "flash_crash",
                    "market_drop": -0.2,
                    "volatility_spike": 5.0,
                    "duration_days": 1,
                },
            ],
        )

        # 日志配置
        self.logging = LoggingConfig(
            level="INFO",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file_path=str(LOGS_ROOT / "staging" / "optimizer.log"),
            max_file_size=50 * 1024 * 1024,  # 50MB
            backup_count=10,
            console_output=False,
        )

    def _load_production_config(self):
        """生产环境配置"""
        # ZeroMQ配置
        self.zeromq = ZeroMQConfig(
            publisher_port=7555,
            subscriber_port=7556,
            req_rep_port=7557,
            push_pull_port=7558,
            connection_timeout=15000,
            retry_attempts=10,
            high_water_mark=10000,
        )

        # 数据库配置
        self.database = DatabaseConfig(
            sqlite_path=str(DATA_ROOT / "production" / "optimizer.db"),
            redis_host=os.getenv("REDIS_HOST", "redis-cluster"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            redis_db=2,
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            max_connections=50,
            connection_timeout=120,
        )

        # 回测配置
        self.backtest = BacktestConfig(
            default_period_days=1095,  # 3年
            initial_capital=1000000.0,
            commission_rate=0.0005,
            slippage=0.0001,
            max_concurrent_backtests=16,
            vectorbt_config={
                "caching": True,
                "silence_warnings": True,
                "chunk_len": 5000,
            },
        )

        # 优化配置
        self.optimization = OptimizationConfig(
            genetic_algorithm={
                "population_size": 200,
                "generations": 100,
                "crossover_rate": 0.8,
                "mutation_rate": 0.1,
                "elite_ratio": 0.1,
            },
            grid_search={"max_combinations": 10000, "parallel_jobs": 16},
            bayesian_optimization={
                "n_calls": 200,
                "n_initial_points": 50,
                "acquisition_function": "EI",
            },
            max_optimization_time=14400,  # 4小时
            groq_config={
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "model": "llama-3.1-70b-versatile",
                "max_tokens": 4000,
                "temperature": 0.05,
            },
        )

        # 风险控制配置
        self.risk = RiskConfig(
            max_position_size=0.05,
            max_daily_loss=0.01,
            max_drawdown_threshold=0.03,
            min_confidence_threshold=0.8,
            stress_test_scenarios=[
                {
                    "name": "2008_financial_crisis",
                    "market_drop": -0.4,
                    "volatility_spike": 3.0,
                    "duration_days": 180,
                },
                {
                    "name": "2020_covid_crash",
                    "market_drop": -0.35,
                    "volatility_spike": 2.5,
                    "duration_days": 60,
                },
                {
                    "name": "2022_crypto_winter",
                    "market_drop": -0.7,
                    "volatility_spike": 4.0,
                    "duration_days": 365,
                },
                {
                    "name": "flash_crash",
                    "market_drop": -0.2,
                    "volatility_spike": 5.0,
                    "duration_days": 1,
                },
                {
                    "name": "liquidity_crisis",
                    "market_drop": -0.3,
                    "volatility_spike": 2.0,
                    "duration_days": 30,
                },
            ],
        )

        # 日志配置
        self.logging = LoggingConfig(
            level="WARNING",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file_path=str(LOGS_ROOT / "production" / "optimizer.log"),
            max_file_size=100 * 1024 * 1024,  # 100MB
            backup_count=20,
            console_output=False,
        )

    def _load_test_config(self):
        """测试环境配置"""
        # ZeroMQ配置
        self.zeromq = ZeroMQConfig(
            publisher_port=8555,
            subscriber_port=8556,
            req_rep_port=8557,
            push_pull_port=8558,
            connection_timeout=5000,
            retry_attempts=3,
            high_water_mark=100,
        )

        # 数据库配置 - 使用内存数据库
        self.database = DatabaseConfig(
            sqlite_path=":memory:",
            redis_host="localhost",
            redis_port=6379,
            redis_db=15,  # 测试专用数据库
            redis_password="",
            max_connections=5,
            connection_timeout=10,
        )

        # 回测配置 - 简化配置用于快速测试
        self.backtest = BacktestConfig(
            default_period_days=30,
            initial_capital=10000.0,
            commission_rate=0.001,
            slippage=0.0001,
            max_concurrent_backtests=2,
            vectorbt_config={
                "caching": False,
                "silence_warnings": True,
                "chunk_len": 100,
            },
        )

        # 优化配置 - 快速测试配置
        self.optimization = OptimizationConfig(
            genetic_algorithm={
                "population_size": 10,
                "generations": 5,
                "crossover_rate": 0.8,
                "mutation_rate": 0.1,
                "elite_ratio": 0.1,
            },
            grid_search={"max_combinations": 100, "parallel_jobs": 2},
            bayesian_optimization={
                "n_calls": 10,
                "n_initial_points": 5,
                "acquisition_function": "EI",
            },
            max_optimization_time=300,  # 5分钟
            groq_config={
                "api_key": "test_key",
                "model": "llama-3.1-70b-versatile",
                "max_tokens": 100,
                "temperature": 0.1,
            },
        )

        # 风险控制配置 - 宽松的测试配置
        self.risk = RiskConfig(
            max_position_size=0.2,
            max_daily_loss=0.05,
            max_drawdown_threshold=0.1,
            min_confidence_threshold=0.5,
            stress_test_scenarios=[
                {
                    "name": "test_scenario",
                    "market_drop": -0.1,
                    "volatility_spike": 1.5,
                    "duration_days": 10,
                }
            ],
        )

        # 日志配置 - 详细的测试日志
        self.logging = LoggingConfig(
            level="DEBUG",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file_path=str(LOGS_ROOT / "test" / "optimizer.log"),
            max_file_size=1 * 1024 * 1024,  # 1MB
            backup_count=2,
            console_output=True,
        )

    def get_data_path(self, filename: str) -> str:
        """获取数据文件路径"""
        return str(DATA_ROOT / self.environment / filename)

    def get_log_path(self, filename: str) -> str:
        """获取日志文件路径"""
        return str(LOGS_ROOT / self.environment / filename)

    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            DATA_ROOT / self.environment,
            LOGS_ROOT / self.environment,
            PROJECT_ROOT / "scripts",
            PROJECT_ROOT / "tests",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "environment": self.environment,
            "version": self.version,
            "project_root": str(self.project_root),
            "zeromq": {
                "publisher_port": self.zeromq.publisher_port,
                "subscriber_port": self.zeromq.subscriber_port,
                "req_rep_port": self.zeromq.req_rep_port,
                "push_pull_port": self.zeromq.push_pull_port,
                "connection_timeout": self.zeromq.connection_timeout,
                "retry_attempts": self.zeromq.retry_attempts,
                "high_water_mark": self.zeromq.high_water_mark,
            },
            "database": {
                "sqlite_path": self.database.sqlite_path,
                "redis_host": self.database.redis_host,
                "redis_port": self.database.redis_port,
                "redis_db": self.database.redis_db,
                "max_connections": self.database.max_connections,
                "connection_timeout": self.database.connection_timeout,
            },
            "backtest": {
                "default_period_days": self.backtest.default_period_days,
                "initial_capital": self.backtest.initial_capital,
                "commission_rate": self.backtest.commission_rate,
                "slippage": self.backtest.slippage,
                "max_concurrent_backtests": self.backtest.max_concurrent_backtests,
                "vectorbt_config": self.backtest.vectorbt_config,
            },
            "optimization": {
                "genetic_algorithm": self.optimization.genetic_algorithm,
                "grid_search": self.optimization.grid_search,
                "bayesian_optimization": self.optimization.bayesian_optimization,
                "max_optimization_time": self.optimization.max_optimization_time,
                "groq_config": self.optimization.groq_config,
            },
            "risk": {
                "max_position_size": self.risk.max_position_size,
                "max_daily_loss": self.risk.max_daily_loss,
                "max_drawdown_threshold": self.risk.max_drawdown_threshold,
                "min_confidence_threshold": self.risk.min_confidence_threshold,
                "stress_test_scenarios": self.risk.stress_test_scenarios,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output,
            },
        }


# 全局配置实例
config = Config()

# 确保目录存在
config.ensure_directories()

# 导出常用配置
ZMQ_CONFIG = config.zeromq
DB_CONFIG = config.database
BACKTEST_CONFIG = config.backtest
OPTIMIZATION_CONFIG = config.optimization
RISK_CONFIG = config.risk
LOGGING_CONFIG = config.logging


def get_config(environment: str = None) -> Config:
    """获取配置实例"""
    if environment:
        return Config(environment)
    return config
