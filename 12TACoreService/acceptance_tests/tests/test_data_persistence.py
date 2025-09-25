# 数据持久化验证测试
# Data Persistence Validation Tests

import sqlite3
import redis
import time
import json
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.test_logger import TestLogger
from utils.test_helpers import TestHelpers
from config import AcceptanceTestConfig as TestConfig
from tests.test_zmq_business_api import LazyPirateClient


class DataPersistenceTests:
    """数据持久化验证测试套件"""

    def __init__(self):
        self.config = TestConfig()
        self.logger = TestLogger("data_persistence_tests")
        self.helpers = TestHelpers()

    def _connect_sqlite(self) -> Optional[sqlite3.Connection]:
        """连接SQLite数据库"""
        try:
            conn = sqlite3.connect(self.config.SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            return conn
        except Exception as e:
            self.logger.error(f"连接SQLite数据库失败: {e}")
            return None

    def _connect_redis(self) -> Optional[redis.Redis]:
        """连接Redis缓存"""
        try:
            r = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
            )
            # 测试连接
            r.ping()
            return r
        except Exception as e:
            self.logger.error(f"连接Redis失败: {e}")
            return None

    def _query_request_logs(
        self, conn: sqlite3.Connection, request_id: str
    ) -> Optional[Dict[str, Any]]:
        """查询请求日志"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM request_logs WHERE request_id = ? ORDER BY created_at DESC LIMIT 1",
                (request_id,),
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None
        except Exception as e:
            self.logger.error(f"查询请求日志失败: {e}")
            return None

    def test_sqlite_request_logging(self) -> Dict[str, Any]:
        """测试用例: DATA-01 - SQLite 请求日志持久化"""
        test_case = {
            "case_id": "DATA-01",
            "title": "SQLite 请求日志持久化",
            "suite_id": "DATA-PERSISTENCE",
            "suite_name": "数据层集成测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("DATA-01", "SQLite 请求日志持久化")

            # 1. 连接SQLite数据库
            conn = self._connect_sqlite()
            if not conn:
                test_case["error_message"] = "无法连接SQLite数据库"
                return test_case

            # 2. 发送一个execute.order请求
            client = LazyPirateClient(
                self.config.ZMQ_ENDPOINT, timeout=self.config.ZMQ_TIMEOUT, retries=2
            )

            request_id = self.helpers.generate_request_id()
            request = {
                "request_id": request_id,
                "method": "execute.order",
                "params": {
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "amount": 0.001,
                    "price": 50000,
                    "order_type": "limit",
                },
            }

            self.logger.log_test_step(f"发送execute.order请求，request_id: {request_id}")
            response = client.send_request(request)
            client.close()

            # 验证点1: 验证请求成功
            request_successful = (
                response is not None and response.get("status") == "success"
            )
            vp1 = {
                "description": "验证execute.order请求成功",
                "passed": request_successful,
                "details": f"响应状态: {response.get('status') if response else 'None'}",
            }
            test_case["verification_results"].append(vp1)

            if not request_successful:
                conn.close()
                test_case["error_message"] = "execute.order请求失败，无法验证日志持久化"
                return test_case

            # 3. 等待一段时间确保日志写入
            time.sleep(2)

            # 4. 查询SQLite数据库中的请求日志
            log_record = self._query_request_logs(conn, request_id)

            # 验证点2: 验证日志记录存在
            vp2 = {
                "description": "验证SQLite中存在对应的日志记录",
                "passed": log_record is not None,
                "details": f"找到日志记录: {log_record is not None}",
            }
            test_case["verification_results"].append(vp2)

            if log_record:
                # 验证点3: 验证request_id匹配
                vp3 = {
                    "description": "验证日志记录中的request_id匹配",
                    "passed": log_record.get("request_id") == request_id,
                    "details": f"期望: {request_id}, 实际: {log_record.get('request_id')}",
                }
                test_case["verification_results"].append(vp3)

                # 验证点4: 验证status字段为'success'
                vp4 = {
                    "description": "验证日志记录中的status字段为'success'",
                    "passed": log_record.get("status") == "success",
                    "details": f"日志状态: {log_record.get('status')}",
                }
                test_case["verification_results"].append(vp4)

                # 验证点5: 验证其他关键字段存在
                required_fields = ["method", "created_at", "processing_time_ms"]
                missing_fields = []
                for field in required_fields:
                    if field not in log_record or log_record[field] is None:
                        missing_fields.append(field)

                vp5 = {
                    "description": "验证日志记录包含所有必需字段",
                    "passed": len(missing_fields) == 0,
                    "details": f"缺失字段: {missing_fields}"
                    if missing_fields
                    else "所有字段都存在",
                }
                test_case["verification_results"].append(vp5)
            else:
                # 如果没有找到日志记录，添加失败的验证点
                vp3 = {
                    "description": "验证日志记录中的request_id匹配",
                    "passed": False,
                    "details": "未找到日志记录",
                }
                test_case["verification_results"].append(vp3)

            conn.close()

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"SQLite请求日志持久化", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"SQLite请求日志持久化测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "SQLite请求日志持久化", "DATA-01", test_case["status"], test_case["duration"]
            )

        return test_case

    def test_redis_cache_mechanism(self) -> Dict[str, Any]:
        """测试用例: DATA-02 - Redis 缓存机制验证"""
        test_case = {
            "case_id": "DATA-02",
            "title": "Redis 缓存机制验证",
            "suite_id": "DATA-PERSISTENCE",
            "suite_name": "数据层集成测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("DATA-02", "Redis 缓存机制验证")

            # 1. 连接Redis
            redis_client = self._connect_redis()
            if not redis_client:
                test_case["error_message"] = "无法连接Redis缓存"
                return test_case

            # 2. 连接SQLite（用于检查处理时间）
            sqlite_conn = self._connect_sqlite()
            if not sqlite_conn:
                test_case["error_message"] = "无法连接SQLite数据库"
                return test_case

            # 3. 创建ZMQ客户端
            client = LazyPirateClient(
                self.config.ZMQ_ENDPOINT, timeout=self.config.ZMQ_TIMEOUT, retries=2
            )

            # 4. 发送第一个evaluate.risk请求
            request_id_1 = self.helpers.generate_request_id()
            request_template = {
                "method": "evaluate.risk",
                "params": {
                    "portfolio": {"BTC": 0.5, "ETH": 2.0, "USDT": 10000},
                    "market_conditions": "volatile",
                    "risk_tolerance": "medium",
                },
            }

            request_1 = request_template.copy()
            request_1["request_id"] = request_id_1

            self.logger.log_test_step(
                f"发送第一个evaluate.risk请求，request_id: {request_id_1}"
            )

            first_start_time = time.time()
            response_1 = client.send_request(request_1)
            first_duration = time.time() - first_start_time

            # 验证点1: 验证第一个请求成功
            first_successful = (
                response_1 is not None and response_1.get("status") == "success"
            )
            vp1 = {
                "description": "验证第一个evaluate.risk请求成功",
                "passed": first_successful,
                "details": f"响应状态: {response_1.get('status') if response_1 else 'None'}, 耗时: {first_duration:.3f}s",
            }
            test_case["verification_results"].append(vp1)

            if not first_successful:
                client.close()
                sqlite_conn.close()
                test_case["error_message"] = "第一个evaluate.risk请求失败"
                return test_case

            # 5. 等待一段时间确保日志写入
            time.sleep(1)

            # 6. 立即发送完全相同的第二个请求
            request_id_2 = self.helpers.generate_request_id()
            request_2 = request_template.copy()
            request_2["request_id"] = request_id_2

            self.logger.log_test_step(
                f"发送第二个相同的evaluate.risk请求，request_id: {request_id_2}"
            )

            second_start_time = time.time()
            response_2 = client.send_request(request_2)
            second_duration = time.time() - second_start_time

            client.close()

            # 验证点2: 验证第二个请求成功
            second_successful = (
                response_2 is not None and response_2.get("status") == "success"
            )
            vp2 = {
                "description": "验证第二个evaluate.risk请求成功",
                "passed": second_successful,
                "details": f"响应状态: {response_2.get('status') if response_2 else 'None'}, 耗时: {second_duration:.3f}s",
            }
            test_case["verification_results"].append(vp2)

            if not second_successful:
                sqlite_conn.close()
                test_case["error_message"] = "第二个evaluate.risk请求失败"
                return test_case

            # 7. 等待日志写入
            time.sleep(2)

            # 8. 查询两个请求的处理时间
            log_1 = self._query_request_logs(sqlite_conn, request_id_1)
            log_2 = self._query_request_logs(sqlite_conn, request_id_2)

            sqlite_conn.close()

            # 验证点3: 验证两个请求的日志都存在
            both_logs_exist = log_1 is not None and log_2 is not None
            vp3 = {
                "description": "验证两个请求的日志记录都存在",
                "passed": both_logs_exist,
                "details": f"第一个日志: {log_1 is not None}, 第二个日志: {log_2 is not None}",
            }
            test_case["verification_results"].append(vp3)

            if both_logs_exist:
                # 验证点4: 比较处理时间（如果有缓存，第二个请求应该更快）
                processing_time_1 = log_1.get("processing_time_ms", 0)
                processing_time_2 = log_2.get("processing_time_ms", 0)

                # 如果第二个请求的处理时间明显更短，说明可能命中了缓存
                cache_hit_likely = (
                    processing_time_2 < processing_time_1 * 0.5
                )  # 第二次处理时间少于第一次的50%

                vp4 = {
                    "description": "验证可能的缓存命中 (第二次请求处理更快)",
                    "passed": cache_hit_likely
                    or (processing_time_2 < 100),  # 或者处理时间很短（<100ms）
                    "details": f"第一次: {processing_time_1}ms, 第二次: {processing_time_2}ms",
                }
                test_case["verification_results"].append(vp4)

                # 验证点5: 验证响应内容一致性
                response_1_data = response_1.get("data", {})
                response_2_data = response_2.get("data", {})

                # 比较关键字段
                risk_score_1 = response_1_data.get("risk_score")
                risk_score_2 = response_2_data.get("risk_score")
                risk_level_1 = response_1_data.get("risk_level")
                risk_level_2 = response_2_data.get("risk_level")

                content_consistent = (
                    risk_score_1 == risk_score_2 and risk_level_1 == risk_level_2
                )

                vp5 = {
                    "description": "验证两次请求的响应内容一致",
                    "passed": content_consistent,
                    "details": f"风险评分: {risk_score_1} vs {risk_score_2}, 风险等级: {risk_level_1} vs {risk_level_2}",
                }
                test_case["verification_results"].append(vp5)
            else:
                # 如果日志不存在，添加失败的验证点
                vp4 = {
                    "description": "验证可能的缓存命中 (第二次请求处理更快)",
                    "passed": False,
                    "details": "无法获取处理时间数据",
                }
                test_case["verification_results"].append(vp4)

            # 9. 检查Redis中是否有相关缓存数据
            try:
                # 尝试查找可能的缓存键
                cache_keys = (
                    redis_client.keys("*risk*")
                    or redis_client.keys("*cache*")
                    or redis_client.keys("*evaluate*")
                )

                vp6 = {
                    "description": "验证Redis中存在缓存相关数据",
                    "passed": len(cache_keys) > 0,
                    "details": f"找到 {len(cache_keys)} 个可能的缓存键",
                }
                test_case["verification_results"].append(vp6)

            except Exception as e:
                vp6 = {
                    "description": "验证Redis中存在缓存相关数据",
                    "passed": False,
                    "details": f"Redis查询异常: {e}",
                }
                test_case["verification_results"].append(vp6)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"Redis缓存机制验证", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"Redis缓存机制验证测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "Redis缓存机制验证", "DATA-02", test_case["status"], test_case["duration"]
            )

        return test_case

    def test_database_connectivity(self) -> Dict[str, Any]:
        """额外测试: 数据库连接性验证"""
        test_case = {
            "case_id": "DATA-03",
            "title": "数据库连接性验证",
            "suite_id": "DATA-PERSISTENCE",
            "suite_name": "数据层集成测试",
            "status": "FAIL",
            "duration": 0,
            "verification_results": [],
            "error_message": None,
        }

        start_time = time.time()

        try:
            self.logger.log_test_start("DATA-03", "数据库连接性验证")

            # 1. 测试SQLite连接
            sqlite_conn = self._connect_sqlite()
            sqlite_connected = sqlite_conn is not None

            if sqlite_connected:
                # 测试基本查询
                try:
                    cursor = sqlite_conn.cursor()
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='request_logs'"
                    )
                    table_exists = cursor.fetchone() is not None
                    sqlite_conn.close()
                except Exception:
                    table_exists = False
                    if sqlite_conn:
                        sqlite_conn.close()
            else:
                table_exists = False

            vp1 = {
                "description": "验证SQLite数据库连接和表结构",
                "passed": sqlite_connected and table_exists,
                "details": f"连接: {sqlite_connected}, request_logs表存在: {table_exists}",
            }
            test_case["verification_results"].append(vp1)

            # 2. 测试Redis连接
            redis_client = self._connect_redis()
            redis_connected = redis_client is not None

            if redis_connected:
                # 测试基本操作
                try:
                    test_key = f"test_key_{int(time.time())}"
                    redis_client.set(test_key, "test_value", ex=10)  # 10秒过期
                    retrieved_value = redis_client.get(test_key)
                    redis_operations_work = retrieved_value == "test_value"
                    redis_client.delete(test_key)  # 清理测试数据
                except Exception:
                    redis_operations_work = False
            else:
                redis_operations_work = False

            vp2 = {
                "description": "验证Redis缓存连接和基本操作",
                "passed": redis_connected and redis_operations_work,
                "details": f"连接: {redis_connected}, 基本操作: {redis_operations_work}",
            }
            test_case["verification_results"].append(vp2)

            # 判断测试是否通过
            all_passed = all(vp["passed"] for vp in test_case["verification_results"])
            test_case["status"] = "PASS" if all_passed else "FAIL"

            self.logger.log_verification(f"数据库连接性验证", all_passed)

        except Exception as e:
            test_case["error_message"] = str(e)
            self.logger.error(f"数据库连接性验证测试异常: {e}")

        finally:
            test_case["duration"] = time.time() - start_time
            self.logger.log_test_end(
                "数据库连接性验证", "DATA-03", test_case["status"], test_case["duration"]
            )

        return test_case

    def run_all_tests(self) -> List[Dict[str, Any]]:
        """运行所有数据持久化测试"""
        self.logger.info("开始运行数据持久化验证测试套件")

        test_results = []

        # 运行所有测试用例
        test_results.append(self.test_database_connectivity())  # 先测试连接性
        test_results.append(self.test_sqlite_request_logging())
        test_results.append(self.test_redis_cache_mechanism())

        self.logger.info(f"数据持久化验证测试套件完成，共运行 {len(test_results)} 个测试用例")

        return test_results

    def cleanup(self):
        """清理测试资源"""
        try:
            self.logger.info("开始清理数据持久化测试资源")

            # 清理SQLite测试数据
            try:
                sqlite_conn = self._connect_sqlite()
                if sqlite_conn:
                    cursor = sqlite_conn.cursor()
                    # 删除测试期间创建的测试数据
                    cursor.execute(
                        "DELETE FROM request_logs WHERE request_id LIKE 'test_%'"
                    )
                    sqlite_conn.commit()
                    sqlite_conn.close()
                    self.logger.info("SQLite测试数据清理完成")
            except Exception as e:
                self.logger.warning(f"SQLite清理异常: {e}")

            # 清理Redis测试数据
            try:
                redis_client = self._connect_redis()
                if redis_client:
                    # 删除测试期间可能创建的缓存键
                    test_keys = redis_client.keys("test_*")
                    if test_keys:
                        redis_client.delete(*test_keys)
                    self.logger.info("Redis测试数据清理完成")
            except Exception as e:
                self.logger.warning(f"Redis清理异常: {e}")

            self.logger.info("数据持久化测试资源清理完成")

        except Exception as e:
            self.logger.error(f"清理测试资源时发生异常: {e}")
