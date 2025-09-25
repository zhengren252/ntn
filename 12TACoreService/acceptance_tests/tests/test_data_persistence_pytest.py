# pytest兼容的数据持久化测试
import pytest
from .test_data_persistence import DataPersistenceTests


@pytest.fixture(scope="module")
def data_persistence_test_suite():
    """创建数据持久化测试套件实例"""
    suite = DataPersistenceTests()
    yield suite
    suite.cleanup()


def test_sqlite_request_logging(data_persistence_test_suite):
    """测试SQLite请求日志记录"""
    result = data_persistence_test_suite.test_sqlite_request_logging()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_redis_cache_mechanism(data_persistence_test_suite):
    """测试Redis缓存机制"""
    result = data_persistence_test_suite.test_redis_cache_mechanism()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"


def test_database_connectivity(data_persistence_test_suite):
    """测试数据库连接性"""
    result = data_persistence_test_suite.test_database_connectivity()
    assert result["status"] == "PASS", f"测试失败: {result.get('error_message', '未知错误')}"
