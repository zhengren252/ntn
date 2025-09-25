# pytest兼容的ZMQ API测试
import pytest
from .test_zmq_business_api import ZMQBusinessAPITests


@pytest.fixture(scope="module")
def zmq_test_suite():
    """创建ZMQ测试套件实例"""
    suite = ZMQBusinessAPITests()
    yield suite
    suite.cleanup()


def test_scan_market_success(zmq_test_suite):
    """测试scan.market成功路径"""
    result = zmq_test_suite.test_scan_market_success()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_execute_order_success(zmq_test_suite):
    """测试execute.order成功路径"""
    result = zmq_test_suite.test_execute_order_success()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_evaluate_risk_success(zmq_test_suite):
    """测试evaluate.risk成功路径"""
    result = zmq_test_suite.test_evaluate_risk_success()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_invalid_method(zmq_test_suite):
    """测试无效方法"""
    result = zmq_test_suite.test_invalid_method()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"
