# pytest兼容的负载均衡测试
import pytest
from .test_load_balancing import LoadBalancingTests


@pytest.fixture(scope="module")
def load_balancing_test_suite():
    """创建负载均衡测试套件实例"""
    suite = LoadBalancingTests()
    yield suite
    suite.cleanup()


def test_request_distribution(load_balancing_test_suite):
    """测试请求分发"""
    result = load_balancing_test_suite.test_request_distribution()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_horizontal_scaling(load_balancing_test_suite):
    """测试水平扩展"""
    result = load_balancing_test_suite.test_horizontal_scaling()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_performance_under_load(load_balancing_test_suite):
    """测试负载下的性能"""
    result = load_balancing_test_suite.test_performance_under_load()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"
