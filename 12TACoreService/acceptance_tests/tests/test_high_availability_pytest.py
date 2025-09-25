# pytest兼容的高可用性测试
import pytest
from .test_high_availability import HighAvailabilityTests


@pytest.fixture(scope="module")
def high_availability_test_suite():
    """创建高可用性测试套件实例"""
    suite = HighAvailabilityTests()
    yield suite
    suite.cleanup()


def test_worker_failover(high_availability_test_suite):
    """测试工作进程故障转移"""
    result = high_availability_test_suite.test_worker_failover()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_lazy_pirate_retry(high_availability_test_suite):
    """测试Lazy Pirate重试机制"""
    result = high_availability_test_suite.test_lazy_pirate_retry()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_service_recovery(high_availability_test_suite):
    """测试服务恢复"""
    result = high_availability_test_suite.test_service_recovery()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"
