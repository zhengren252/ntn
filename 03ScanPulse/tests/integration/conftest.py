#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试配置文件

为扫描器模组V3.5升级后的集成测试提供共享配置和fixture
"""

import pytest
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def integration_config():
    """
    集成测试配置
    """
    return {
        "tacore_service": {
            "url": "tcp://localhost:5555",
            "container_name": "tacore_service",
            "health_check_timeout": 90,
            "startup_timeout": 120,
        },
        "redis": {
            "url": "redis://localhost:6379",
            "container_name": "trading_redis",
            "health_check_timeout": 30,
            "startup_timeout": 60,
        },
        "scanner": {
            "container_name": "scanner",
            "publisher_port": 5556,
            "subscriber_port": 5557,
            "health_check_timeout": 60,
            "startup_timeout": 90,
        },
        "docker_compose": {
            "file": "docker-compose.system.yml",
            "project_name": "neurotrade-integration-test",
        },
        "test_timeouts": {
            "zmq_request": 10000,  # 10秒
            "service_startup": 120,  # 2分钟
            "message_wait": 30000,  # 30秒
            "health_check": 30,  # 30秒
        },
        "test_data": {
            "scan_request": {
                "market_type": "stock",
                "scan_criteria": {
                    "min_volume": 1000000,
                    "price_range": {"min": 10, "max": 500},
                    "technical_indicators": ["RSI", "MACD", "MA"],
                },
            },
            "expected_response_fields": ["status", "data"],
            "expected_data_fields": ["symbol", "price", "volume"],
        },
    }


@pytest.fixture(scope="session")
def project_root():
    """
    项目根目录路径
    """
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def test_environment_info():
    """
    测试环境信息
    """
    return {
        "python_version": os.sys.version,
        "platform": os.name,
        "working_directory": os.getcwd(),
        "test_start_time": time.time(),
    }


@pytest.fixture(autouse=True)
def test_logging(request):
    """
    自动为每个测试添加日志记录
    """
    test_name = request.node.name
    logger.info(f"开始执行测试: {test_name}")

    yield

    logger.info(f"测试完成: {test_name}")


@pytest.fixture(scope="function")
def test_timeout():
    """
    测试超时控制
    """
    start_time = time.time()
    timeout = 300  # 5分钟超时

    def check_timeout():
        if time.time() - start_time > timeout:
            pytest.fail(f"测试超时 ({timeout}秒)")

    yield check_timeout


def pytest_configure(config):
    """
    pytest配置钩子
    """
    # 添加自定义标记
    config.addinivalue_line("markers", "integration: 标记为集成测试")
    config.addinivalue_line("markers", "docker: 需要Docker环境的测试")
    config.addinivalue_line("markers", "slow: 运行时间较长的测试")


def pytest_collection_modifyitems(config, items):
    """
    修改测试收集行为
    """
    # 为所有集成测试添加标记
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.docker)
            item.add_marker(pytest.mark.slow)


def pytest_runtest_setup(item):
    """
    测试运行前的设置
    """
    # 检查Docker环境
    if "docker" in [mark.name for mark in item.iter_markers()]:
        try:
            import docker

            client = docker.from_env()
            client.ping()
        except Exception as e:
            pytest.skip(f"Docker环境不可用: {e}")


def pytest_runtest_teardown(item, nextitem):
    """
    测试运行后的清理
    """
    # 这里可以添加测试后的清理逻辑
    pass


@pytest.fixture(scope="session")
def integration_test_report():
    """
    集成测试报告收集器
    """
    report = {
        "test_results": [],
        "start_time": time.time(),
        "end_time": None,
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
    }

    yield report

    # 测试会话结束时生成报告
    report["end_time"] = time.time()
    report["duration"] = report["end_time"] - report["start_time"]

    logger.info(f"集成测试会话完成:")
    logger.info(f"  总测试数: {report['total_tests']}")
    logger.info(f"  通过: {report['passed_tests']}")
    logger.info(f"  失败: {report['failed_tests']}")
    logger.info(f"  跳过: {report['skipped_tests']}")
    logger.info(f"  耗时: {report['duration']:.2f}秒")
