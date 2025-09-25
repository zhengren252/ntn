# 测试辅助工具
# Test Helper Utilities

import time
import json
import uuid
import sqlite3
import redis
from typing import Dict, Any, Optional, List
from datetime import datetime


class TestHelpers:
    """测试辅助工具类"""

    @staticmethod
    def generate_request_id(prefix: str = "test") -> str:
        """生成唯一的请求ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}_{timestamp}_{unique_id}"

    @staticmethod
    def measure_time(func):
        """装饰器：测量函数执行时间"""

        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            return result, duration

        return wrapper

    @staticmethod
    def validate_json_structure(
        data: Dict[str, Any], required_fields: List[str]
    ) -> tuple[bool, List[str]]:
        """验证JSON结构是否包含必需字段"""
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)

        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields

    @staticmethod
    def validate_response_format(
        response: Dict[str, Any], expected_status: str = "success"
    ) -> tuple[bool, str]:
        """验证响应格式"""
        try:
            # 检查基本字段
            if "status" not in response:
                return False, "缺少 'status' 字段"

            if response["status"] != expected_status:
                return False, f"状态不匹配，期望: {expected_status}, 实际: {response['status']}"

            if "request_id" not in response:
                return False, "缺少 'request_id' 字段"

            return True, "响应格式正确"

        except Exception as e:
            return False, f"验证响应格式时出错: {str(e)}"

    @staticmethod
    def check_sqlite_record(
        db_path: str, table: str, conditions: Dict[str, Any]
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """检查SQLite数据库中的记录"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            cursor = conn.cursor()

            # 构建查询条件
            where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
            query = f"SELECT * FROM {table} WHERE {where_clause}"

            cursor.execute(query, list(conditions.values()))
            result = cursor.fetchone()

            conn.close()

            if result:
                # 转换为字典
                record = dict(result)
                return True, record
            else:
                return False, None

        except Exception as e:
            return False, None

    @staticmethod
    def check_redis_cache(
        host: str, port: int, db: int, key: str
    ) -> tuple[bool, Optional[str]]:
        """检查Redis缓存"""
        try:
            r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            value = r.get(key)

            if value:
                return True, value
            else:
                return False, None

        except Exception as e:
            return False, None

    @staticmethod
    def wait_for_condition(
        condition_func, timeout: int = 30, interval: float = 1.0
    ) -> bool:
        """等待条件满足"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)

        return False

    @staticmethod
    def format_test_data(data: Dict[str, Any]) -> str:
        """格式化测试数据为可读字符串"""
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def calculate_statistics(values: List[float]) -> Dict[str, float]:
        """计算统计数据"""
        if not values:
            return {}

        values_sorted = sorted(values)
        n = len(values)

        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / n,
            "median": values_sorted[n // 2]
            if n % 2 == 1
            else (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2,
            "p95": values_sorted[int(n * 0.95)] if n > 0 else 0,
            "p99": values_sorted[int(n * 0.99)] if n > 0 else 0,
        }

    @staticmethod
    def create_test_summary(test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建测试摘要"""
        total_tests = len(test_results)
        passed_tests = sum(
            1 for result in test_results if result.get("status") == "PASS"
        )
        failed_tests = total_tests - passed_tests

        # 计算执行时间统计
        durations = [result.get("duration", 0) for result in test_results]
        duration_stats = TestHelpers.calculate_statistics(durations)

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests * 100)
            if total_tests > 0
            else 0,
            "total_duration": sum(durations),
            "duration_statistics": duration_stats,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def save_test_data(data: Dict[str, Any], file_path: str):
        """保存测试数据到文件"""
        import os

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_test_data(file_path: str) -> Optional[Dict[str, Any]]:
        """从文件加载测试数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
