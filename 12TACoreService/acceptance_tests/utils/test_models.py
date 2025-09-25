# 测试结果数据模型
# Test Result Data Models

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class TestStatus(Enum):
    """测试状态枚举"""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


class TestSeverity(Enum):
    """测试严重性级别"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class VerificationPoint:
    """验证点数据结构"""

    description: str
    passed: bool
    details: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestCase:
    """测试用例数据结构"""

    case_id: str
    title: str
    suite_id: str
    suite_name: str
    status: TestStatus
    duration: float
    start_time: datetime
    end_time: datetime
    severity: TestSeverity = TestSeverity.MEDIUM
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    verification_results: List[VerificationPoint] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.verification_results is None:
            self.verification_results = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # 转换枚举值为字符串
        data["status"] = self.status.value
        data["severity"] = self.severity.value
        # 转换时间为ISO格式字符串
        data["start_time"] = self.start_time.isoformat()
        data["end_time"] = self.end_time.isoformat()
        return data


@dataclass
class TestSuite:
    """测试套件数据结构"""

    suite_id: str
    suite_name: str
    description: str
    test_cases: List[TestCase]
    start_time: datetime
    end_time: datetime

    @property
    def duration(self) -> float:
        """计算套件总耗时"""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def total_tests(self) -> int:
        """总测试数"""
        return len(self.test_cases)

    @property
    def passed_tests(self) -> int:
        """通过测试数"""
        return len([tc for tc in self.test_cases if tc.status == TestStatus.PASS])

    @property
    def failed_tests(self) -> int:
        """失败测试数"""
        return len([tc for tc in self.test_cases if tc.status == TestStatus.FAIL])

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "suite_name": self.suite_name,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": self.success_rate,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
        }


@dataclass
class TestReport:
    """测试报告数据结构"""

    report_id: str
    title: str
    version: str
    plan_id: str
    generated_at: datetime
    test_suites: List[TestSuite]
    environment: Dict[str, Any] = None
    configuration: Dict[str, Any] = None

    def __post_init__(self):
        if self.environment is None:
            self.environment = {}
        if self.configuration is None:
            self.configuration = {}

    @property
    def total_tests(self) -> int:
        """总测试数"""
        return sum(suite.total_tests for suite in self.test_suites)

    @property
    def passed_tests(self) -> int:
        """通过测试数"""
        return sum(suite.passed_tests for suite in self.test_suites)

    @property
    def failed_tests(self) -> int:
        """失败测试数"""
        return sum(suite.failed_tests for suite in self.test_suites)

    @property
    def success_rate(self) -> float:
        """总成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    @property
    def total_duration(self) -> float:
        """总耗时"""
        return sum(suite.duration for suite in self.test_suites)

    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        return {
            "report_id": self.report_id,
            "title": self.title,
            "version": self.version,
            "plan_id": self.plan_id,
            "generated_at": self.generated_at.isoformat(),
            "timestamp": self.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": self.success_rate,
            "total_duration": self.total_duration,
            "suite_count": len(self.test_suites),
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "report_info": {
                "report_id": self.report_id,
                "title": self.title,
                "version": self.version,
                "plan_id": self.plan_id,
                "generated_at": self.generated_at.isoformat(),
            },
            "summary": self.get_summary(),
            "environment": self.environment,
            "configuration": self.configuration,
            "test_suites": [suite.to_dict() for suite in self.test_suites],
        }

    def get_flat_test_cases(self) -> List[Dict[str, Any]]:
        """获取扁平化的测试用例列表（用于兼容现有格式）"""
        flat_cases = []
        for suite in self.test_suites:
            for test_case in suite.test_cases:
                flat_cases.append(test_case.to_dict())
        return flat_cases
