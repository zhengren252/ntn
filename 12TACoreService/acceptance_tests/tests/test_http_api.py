# pytest兼容的HTTP API测试
import pytest
from .test_http_monitoring_api import HTTPMonitoringAPITests


@pytest.fixture(scope="module")
def http_test_suite():
    """创建HTTP测试套件实例"""
    suite = HTTPMonitoringAPITests()
    yield suite
    suite.cleanup()


def test_get_status(http_test_suite):
    """测试GET /status端点"""
    result = http_test_suite.test_get_status()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_get_workers(http_test_suite):
    """测试GET /workers端点"""
    result = http_test_suite.test_get_workers()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_get_logs(http_test_suite):
    """测试GET /logs端点"""
    result = http_test_suite.test_get_logs()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"
