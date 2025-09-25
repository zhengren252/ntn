# -*- coding: utf-8 -*-
"""
数据验证器模块

负责数据格式验证、完整性检查和业务规则验证
"""

import re
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass
from urllib.parse import urlparse

from ..config import ConfigManager
from ..utils import Logger


class ValidationLevel(Enum):
    """验证级别"""

    BASIC = "basic"  # 基础验证
    STANDARD = "standard"  # 标准验证
    STRICT = "strict"  # 严格验证


class ValidationSeverity(Enum):
    """验证严重性"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


@dataclass
class ValidationIssue:
    """验证问题"""

    field: str
    message: str
    severity: ValidationSeverity
    rule: str
    value: Any = None
    expected: Any = None


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    issues: List[ValidationIssue]
    validated_data: Optional[Dict[str, Any]]
    validation_time: float
    metadata: Dict[str, Any]


class FieldValidator:
    """字段验证器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        # 验证配置
        validation_config = config.get_config("processors.validation", {})
        self.url_timeout = validation_config.get("url_timeout", 5)
        self.max_title_length = validation_config.get("max_title_length", 200)
        self.max_content_length = validation_config.get("max_content_length", 50000)
        self.min_content_length = validation_config.get("min_content_length", 10)

        # 允许的域名
        self.allowed_domains = set(validation_config.get("allowed_domains", []))
        self.blocked_domains = set(validation_config.get("blocked_domains", []))

        # 关键词验证
        self.max_keywords = validation_config.get("max_keywords", 20)
        self.min_keyword_length = validation_config.get("min_keyword_length", 2)
        self.max_keyword_length = validation_config.get("max_keyword_length", 50)

        self.logger.info("字段验证器初始化完成")

    def validate_title(
        self, title: str, level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[ValidationIssue]:
        """验证标题

        Args:
            title: 标题内容
            level: 验证级别

        Returns:
            验证问题列表
        """
        issues = []

        if not title:
            issues.append(
                ValidationIssue(
                    field="title",
                    message="标题不能为空",
                    severity=ValidationSeverity.ERROR,
                    rule="required",
                    value=title,
                )
            )
            return issues

        # 长度检查
        if len(title) > self.max_title_length:
            issues.append(
                ValidationIssue(
                    field="title",
                    message=f"标题长度超过限制 ({len(title)} > {self.max_title_length})",
                    severity=ValidationSeverity.ERROR,
                    rule="max_length",
                    value=len(title),
                    expected=self.max_title_length,
                )
            )

        # 基础验证
        if level.value in ["basic", "standard", "strict"]:
            # 检查是否包含有效字符
            if not re.search(r"[a-zA-Z\u4e00-\u9fff]", title):
                issues.append(
                    ValidationIssue(
                        field="title",
                        message="标题必须包含有效的字母或中文字符",
                        severity=ValidationSeverity.ERROR,
                        rule="valid_characters",
                        value=title,
                    )
                )

        # 标准验证
        if level.value in ["standard", "strict"]:
            # 检查重复字符
            if re.search(r"(.)\1{4,}", title):
                issues.append(
                    ValidationIssue(
                        field="title",
                        message="标题包含过多重复字符",
                        severity=ValidationSeverity.WARNING,
                        rule="repeated_characters",
                        value=title,
                    )
                )

            # 检查全大写
            if title.isupper() and len(title) > 10:
                issues.append(
                    ValidationIssue(
                        field="title",
                        message="标题不应全部使用大写字母",
                        severity=ValidationSeverity.WARNING,
                        rule="all_uppercase",
                        value=title,
                    )
                )

        # 严格验证
        if level == ValidationLevel.STRICT:
            # 检查特殊字符比例
            special_chars = len(re.findall(r"[^a-zA-Z0-9\u4e00-\u9fff\s]", title))
            if special_chars / len(title) > 0.3:
                issues.append(
                    ValidationIssue(
                        field="title",
                        message="标题包含过多特殊字符",
                        severity=ValidationSeverity.WARNING,
                        rule="special_characters_ratio",
                        value=special_chars / len(title),
                    )
                )

        return issues

    def validate_content(
        self, content: str, level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[ValidationIssue]:
        """验证内容

        Args:
            content: 内容文本
            level: 验证级别

        Returns:
            验证问题列表
        """
        issues = []

        if not content:
            issues.append(
                ValidationIssue(
                    field="content",
                    message="内容不能为空",
                    severity=ValidationSeverity.ERROR,
                    rule="required",
                    value=content,
                )
            )
            return issues

        # 长度检查
        if len(content) < self.min_content_length:
            issues.append(
                ValidationIssue(
                    field="content",
                    message=f"内容长度过短 ({len(content)} < {self.min_content_length})",
                    severity=ValidationSeverity.ERROR,
                    rule="min_length",
                    value=len(content),
                    expected=self.min_content_length,
                )
            )

        if len(content) > self.max_content_length:
            issues.append(
                ValidationIssue(
                    field="content",
                    message=f"内容长度超过限制 ({len(content)} > {self.max_content_length})",
                    severity=ValidationSeverity.ERROR,
                    rule="max_length",
                    value=len(content),
                    expected=self.max_content_length,
                )
            )

        # 基础验证
        if level.value in ["basic", "standard", "strict"]:
            # 检查字符质量
            letter_count = sum(
                1 for c in content if c.isalpha() or "\u4e00" <= c <= "\u9fff"
            )
            if letter_count / len(content) < 0.3:
                issues.append(
                    ValidationIssue(
                        field="content",
                        message="内容包含的有效字符比例过低",
                        severity=ValidationSeverity.WARNING,
                        rule="character_quality",
                        value=letter_count / len(content),
                    )
                )

        # 标准验证
        if level.value in ["standard", "strict"]:
            # 检查句子结构
            sentences = re.split(r"[.!?。！？]", content)
            valid_sentences = [s for s in sentences if len(s.strip()) > 5]
            if len(valid_sentences) < 2:
                issues.append(
                    ValidationIssue(
                        field="content",
                        message="内容缺乏有效的句子结构",
                        severity=ValidationSeverity.WARNING,
                        rule="sentence_structure",
                        value=len(valid_sentences),
                    )
                )

        # 严格验证
        if level == ValidationLevel.STRICT:
            # 检查重复内容
            words = content.lower().split()
            unique_words = set(words)
            if len(words) > 0 and len(unique_words) / len(words) < 0.5:
                issues.append(
                    ValidationIssue(
                        field="content",
                        message="内容包含过多重复词汇",
                        severity=ValidationSeverity.WARNING,
                        rule="word_uniqueness",
                        value=len(unique_words) / len(words),
                    )
                )

        return issues

    def validate_url(
        self, url: str, level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[ValidationIssue]:
        """验证URL

        Args:
            url: URL地址
            level: 验证级别

        Returns:
            验证问题列表
        """
        issues = []

        if not url:
            issues.append(
                ValidationIssue(
                    field="url",
                    message="URL不能为空",
                    severity=ValidationSeverity.ERROR,
                    rule="required",
                    value=url,
                )
            )
            return issues

        # URL格式验证
        try:
            parsed = urlparse(url)

            # 检查协议
            if not parsed.scheme:
                issues.append(
                    ValidationIssue(
                        field="url",
                        message="URL缺少协议 (http/https)",
                        severity=ValidationSeverity.ERROR,
                        rule="missing_scheme",
                        value=url,
                    )
                )
            elif parsed.scheme not in ["http", "https"]:
                issues.append(
                    ValidationIssue(
                        field="url",
                        message=f"不支持的URL协议: {parsed.scheme}",
                        severity=ValidationSeverity.ERROR,
                        rule="invalid_scheme",
                        value=parsed.scheme,
                        expected=["http", "https"],
                    )
                )

            # 检查域名
            if not parsed.netloc:
                issues.append(
                    ValidationIssue(
                        field="url",
                        message="URL缺少域名",
                        severity=ValidationSeverity.ERROR,
                        rule="missing_domain",
                        value=url,
                    )
                )
            else:
                domain_with_port = parsed.netloc.lower()
                # 去掉端口号，只保留域名
                domain = domain_with_port.split(":")[0]

                # 检查被阻止的域名
                if self.blocked_domains and (
                    domain in self.blocked_domains
                    or domain_with_port in self.blocked_domains
                ):
                    issues.append(
                        ValidationIssue(
                            field="url",
                            message=f"域名被阻止: {domain}",
                            severity=ValidationSeverity.ERROR,
                            rule="blocked_domain",
                            value=domain,
                        )
                    )

                # 检查允许的域名（如果配置了）
                if (
                    self.allowed_domains
                    and domain not in self.allowed_domains
                    and domain_with_port not in self.allowed_domains
                ):
                    issues.append(
                        ValidationIssue(
                            field="url",
                            message=f"域名不在允许列表中: {domain}",
                            severity=ValidationSeverity.WARNING,
                            rule="domain_not_allowed",
                            value=domain,
                        )
                    )

        except Exception as e:
            issues.append(
                ValidationIssue(
                    field="url",
                    message=f"URL格式无效: {e}",
                    severity=ValidationSeverity.ERROR,
                    rule="invalid_format",
                    value=url,
                )
            )

        return issues

    def validate_timestamp(
        self, timestamp: str, level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[ValidationIssue]:
        """验证时间戳

        Args:
            timestamp: 时间戳
            level: 验证级别

        Returns:
            验证问题列表
        """
        issues = []

        if not timestamp:
            issues.append(
                ValidationIssue(
                    field="timestamp",
                    message="时间戳不能为空",
                    severity=ValidationSeverity.ERROR,
                    rule="required",
                    value=timestamp,
                )
            )
            return issues

        # 时间戳格式验证
        try:
            if timestamp.endswith("Z"):
                dt = datetime.fromisoformat(timestamp[:-1])
            else:
                dt = datetime.fromisoformat(timestamp)

            # 检查时间范围
            now = datetime.utcnow()

            # 不能是未来时间
            if dt > now:
                issues.append(
                    ValidationIssue(
                        field="timestamp",
                        message="时间戳不能是未来时间",
                        severity=ValidationSeverity.ERROR,
                        rule="future_time",
                        value=timestamp,
                    )
                )

            # 不能太久远（超过10年）
            if level.value in ["standard", "strict"]:
                ten_years_ago = datetime(now.year - 10, now.month, now.day)
                if dt < ten_years_ago:
                    issues.append(
                        ValidationIssue(
                            field="timestamp",
                            message="时间戳过于久远",
                            severity=ValidationSeverity.WARNING,
                            rule="too_old",
                            value=timestamp,
                        )
                    )

        except ValueError as e:
            issues.append(
                ValidationIssue(
                    field="timestamp",
                    message=f"时间戳格式无效: {e}",
                    severity=ValidationSeverity.ERROR,
                    rule="invalid_format",
                    value=timestamp,
                )
            )

        return issues

    def validate_keywords(
        self, keywords: List[str], level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[ValidationIssue]:
        """验证关键词

        Args:
            keywords: 关键词列表
            level: 验证级别

        Returns:
            验证问题列表
        """
        issues = []

        if not isinstance(keywords, list):
            issues.append(
                ValidationIssue(
                    field="keywords",
                    message="关键词必须是列表格式",
                    severity=ValidationSeverity.ERROR,
                    rule="invalid_type",
                    value=type(keywords).__name__,
                    expected="list",
                )
            )
            return issues

        # 数量检查
        if len(keywords) > self.max_keywords:
            issues.append(
                ValidationIssue(
                    field="keywords",
                    message=f"关键词数量超过限制 ({len(keywords)} > {self.max_keywords})",
                    severity=ValidationSeverity.WARNING,
                    rule="max_count",
                    value=len(keywords),
                    expected=self.max_keywords,
                )
            )

        # 验证每个关键词
        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                issues.append(
                    ValidationIssue(
                        field=f"keywords[{i}]",
                        message="关键词必须是字符串",
                        severity=ValidationSeverity.ERROR,
                        rule="invalid_type",
                        value=type(keyword).__name__,
                        expected="str",
                    )
                )
                continue

            # 长度检查
            if len(keyword) < self.min_keyword_length:
                issues.append(
                    ValidationIssue(
                        field=f"keywords[{i}]",
                        message=f"关键词长度过短: '{keyword}'",
                        severity=ValidationSeverity.WARNING,
                        rule="min_length",
                        value=len(keyword),
                        expected=self.min_keyword_length,
                    )
                )

            if len(keyword) > self.max_keyword_length:
                issues.append(
                    ValidationIssue(
                        field=f"keywords[{i}]",
                        message=f"关键词长度过长: '{keyword}'",
                        severity=ValidationSeverity.WARNING,
                        rule="max_length",
                        value=len(keyword),
                        expected=self.max_keyword_length,
                    )
                )

            # 字符检查
            if level.value in ["standard", "strict"]:
                if not re.match(r"^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$", keyword):
                    issues.append(
                        ValidationIssue(
                            field=f"keywords[{i}]",
                            message=f"关键词包含无效字符: '{keyword}'",
                            severity=ValidationSeverity.WARNING,
                            rule="invalid_characters",
                            value=keyword,
                        )
                    )

        # 检查重复
        if level == ValidationLevel.STRICT:
            seen = set()
            for i, keyword in enumerate(keywords):
                if isinstance(keyword, str):
                    keyword_lower = keyword.lower()
                    if keyword_lower in seen:
                        issues.append(
                            ValidationIssue(
                                field=f"keywords[{i}]",
                                message=f"重复的关键词: '{keyword}'",
                                severity=ValidationSeverity.WARNING,
                                rule="duplicate",
                                value=keyword,
                            )
                        )
                    seen.add(keyword_lower)

        return issues


class DataValidator:
    """数据验证器主类

    负责数据格式验证、完整性检查和业务规则验证
    """

    def __init__(self, config: ConfigManager, logger: Logger = None):
        """初始化数据验证器

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or Logger(config)

        # 初始化字段验证器
        self.field_validator = FieldValidator(config, self.logger)

        # 验证配置
        self.validation_config = config.get_config("processors.validation", {})
        self.default_validation_level = ValidationLevel(
            self.validation_config.get("default_level", "standard")
        )
        self.fail_on_error = self.validation_config.get("fail_on_error", True)
        self.fail_on_warning = self.validation_config.get("fail_on_warning", False)

        # 必需字段
        self.required_fields = set(
            self.validation_config.get(
                "required_fields", ["title", "content", "url", "timestamp", "source"]
            )
        )

        # 统计信息
        self.stats = {
            "items_validated": 0,
            "items_passed": 0,
            "items_failed": 0,
            "total_issues": 0,
            "error_count": 0,
            "warning_count": 0,
            "total_validation_time": 0.0,
            "last_validation_time": None,
        }

        self.logger.info("数据验证器初始化完成")

    def validate_data(
        self, data: Dict[str, Any], level: ValidationLevel = None
    ) -> ValidationResult:
        """验证数据

        Args:
            data: 待验证的数据
            level: 验证级别

        Returns:
            验证结果
        """
        start_time = time.time()

        if level is None:
            level = self.default_validation_level

        self.stats["items_validated"] += 1
        all_issues = []

        try:
            # 检查必需字段
            for field in self.required_fields:
                if field not in data or data[field] is None:
                    all_issues.append(
                        ValidationIssue(
                            field=field,
                            message=f"必需字段缺失: {field}",
                            severity=ValidationSeverity.ERROR,
                            rule="required_field",
                            value=data.get(field),
                        )
                    )

            # 验证各个字段
            if "title" in data:
                all_issues.extend(
                    self.field_validator.validate_title(data["title"], level)
                )

            if "content" in data:
                all_issues.extend(
                    self.field_validator.validate_content(data["content"], level)
                )

            if "url" in data:
                all_issues.extend(self.field_validator.validate_url(data["url"], level))

            if "timestamp" in data:
                all_issues.extend(
                    self.field_validator.validate_timestamp(data["timestamp"], level)
                )

            if "keywords" in data:
                all_issues.extend(
                    self.field_validator.validate_keywords(data["keywords"], level)
                )

            # 业务规则验证
            all_issues.extend(self._validate_business_rules(data, level))

            # 统计问题
            error_count = sum(
                1 for issue in all_issues if issue.severity == ValidationSeverity.ERROR
            )
            critical_count = sum(
                1
                for issue in all_issues
                if issue.severity == ValidationSeverity.CRITICAL
            )
            warning_count = sum(
                1
                for issue in all_issues
                if issue.severity == ValidationSeverity.WARNING
            )

            # 更新统计
            self.stats["total_issues"] += len(all_issues)
            self.stats["error_count"] += error_count + critical_count
            self.stats["warning_count"] += warning_count

            # 判断是否通过验证
            is_valid = True
            if critical_count > 0 or error_count > 0:
                is_valid = False
            elif self.fail_on_warning and warning_count > 0:
                is_valid = False

            # 更新通过/失败统计
            if is_valid:
                self.stats["items_passed"] += 1
            else:
                self.stats["items_failed"] += 1

            validation_time = time.time() - start_time
            self.stats["total_validation_time"] += validation_time
            self.stats["last_validation_time"] = datetime.utcnow().isoformat()

            self.logger.debug(
                f"数据验证完成: 有效={is_valid} | "
                f"问题数量: {len(all_issues)} (错误: {error_count + critical_count}, 警告: {warning_count}) | "
                f"耗时: {validation_time:.3f}s"
            )

            return ValidationResult(
                is_valid=is_valid,
                issues=all_issues,
                validated_data=data if is_valid else None,
                validation_time=validation_time,
                metadata={
                    "validation_level": level.value,
                    "error_count": error_count + critical_count,
                    "warning_count": warning_count,
                    "required_fields_checked": len(self.required_fields),
                },
            )

        except Exception as e:
            validation_time = time.time() - start_time
            self.logger.error(f"数据验证异常: {e}")

            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        field="system",
                        message=f"验证过程异常: {e}",
                        severity=ValidationSeverity.CRITICAL,
                        rule="system_error",
                        value=str(e),
                    )
                ],
                validated_data=None,
                validation_time=validation_time,
                metadata={"error": str(e)},
            )

    def _validate_business_rules(
        self, data: Dict[str, Any], level: ValidationLevel
    ) -> List[ValidationIssue]:
        """验证业务规则

        Args:
            data: 数据
            level: 验证级别

        Returns:
            验证问题列表
        """
        issues = []

        # 检查标题和内容的一致性
        if "title" in data and "content" in data:
            title = data["title"].lower()
            content = data["content"].lower()

            # 标题应该与内容相关
            title_words = set(re.findall(r"\w+", title))
            content_words = set(re.findall(r"\w+", content))

            if title_words and content_words:
                common_words = title_words.intersection(content_words)
                if len(common_words) / len(title_words) < 0.3:
                    issues.append(
                        ValidationIssue(
                            field="title_content_consistency",
                            message="标题与内容相关性较低",
                            severity=ValidationSeverity.WARNING,
                            rule="title_content_relevance",
                            value=len(common_words) / len(title_words),
                        )
                    )

        # 检查URL和内容的一致性
        if "url" in data and "source" in data:
            url = data["url"]
            source = data["source"]

            try:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.lower()

                # 检查source是否与URL域名匹配
                if (
                    source
                    and domain
                    and source.lower() not in domain
                    and domain not in source.lower()
                ):
                    issues.append(
                        ValidationIssue(
                            field="url_source_consistency",
                            message="URL域名与source不匹配",
                            severity=ValidationSeverity.WARNING,
                            rule="url_source_match",
                            value={"url_domain": domain, "source": source},
                        )
                    )
            except Exception:
                pass

        # 检查关键词与内容的相关性
        if "keywords" in data and "content" in data and level == ValidationLevel.STRICT:
            keywords = data["keywords"]
            content = data["content"].lower()

            if isinstance(keywords, list) and keywords:
                relevant_keywords = 0
                for keyword in keywords:
                    if isinstance(keyword, str) and keyword.lower() in content:
                        relevant_keywords += 1

                if relevant_keywords / len(keywords) < 0.5:
                    issues.append(
                        ValidationIssue(
                            field="keywords_content_relevance",
                            message="关键词与内容相关性较低",
                            severity=ValidationSeverity.WARNING,
                            rule="keywords_relevance",
                            value=relevant_keywords / len(keywords),
                        )
                    )

        return issues

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()

        # 计算成功率
        if stats["items_validated"] > 0:
            stats["pass_rate"] = stats["items_passed"] / stats["items_validated"]
            stats["fail_rate"] = stats["items_failed"] / stats["items_validated"]
            stats["avg_issues_per_item"] = (
                stats["total_issues"] / stats["items_validated"]
            )
        else:
            stats["pass_rate"] = 0.0
            stats["fail_rate"] = 0.0
            stats["avg_issues_per_item"] = 0.0

        # 计算平均验证时间
        if stats["items_validated"] > 0:
            stats["avg_validation_time"] = (
                stats["total_validation_time"] / stats["items_validated"]
            )
        else:
            stats["avg_validation_time"] = 0.0

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()

        # 判断健康状态
        if stats["pass_rate"] >= 0.9:
            status = "healthy"
        elif stats["pass_rate"] >= 0.7:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "pass_rate": stats["pass_rate"],
            "items_validated": stats["items_validated"],
            "items_passed": stats["items_passed"],
            "total_issues": stats["total_issues"],
            "error_count": stats["error_count"],
            "warning_count": stats["warning_count"],
            "last_validation_time": stats["last_validation_time"],
        }


if __name__ == "__main__":
    # 测试数据验证器
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建数据验证器
    validator = DataValidator(config, logger)

    # 测试数据
    test_data = [
        {
            "title": "Bitcoin价格突破新高",
            "content": "比特币价格今日突破历史新高，达到65000美元，市场情绪非常乐观。分析师认为这是由于机构投资者的大量买入所致。",
            "url": "https://example.com/news/bitcoin-new-high",
            "timestamp": "2024-01-15T10:30:00Z",
            "category": "crypto",
            "keywords": ["bitcoin", "price", "high", "market"],
            "source": "example.com",
        },
        {
            "title": "",  # 空标题
            "content": "短",  # 内容过短
            "url": "invalid-url",  # 无效URL
            "timestamp": "2025-01-15T10:30:00Z",  # 未来时间
            "keywords": "not a list",  # 错误类型
            "source": "test",
        },
        {
            "title": "BITCOIN PRICE GOES TO THE MOON!!!!!!",  # 全大写，重复字符
            "content": "Bitcoin bitcoin bitcoin price price price goes goes goes up up up",  # 重复词汇
            "url": "https://spam.com/fake-news",
            "timestamp": "2024-01-15T10:30:00Z",
            "keywords": [
                "a",
                "very_long_keyword_that_exceeds_the_maximum_length_limit",
                "bitcoin",
                "bitcoin",
            ],  # 重复关键词
            "source": "different-source.com",  # 与URL不匹配
        },
    ]

    # 测试验证
    print("开始测试数据验证器...")

    for i, data in enumerate(test_data):
        print(f"\n测试数据 {i+1}:")
        result = validator.validate_data(data, ValidationLevel.STRICT)

        print(f"验证结果: {result.is_valid}")
        print(f"问题数量: {len(result.issues)}")
        print(f"验证时间: {result.validation_time:.3f}s")

        if result.issues:
            print("发现的问题:")
            for issue in result.issues:
                print(f"  - {issue.field}: {issue.message} ({issue.severity.value})")

    # 显示统计信息
    stats = validator.get_stats()
    print(f"\n验证统计: {stats}")

    # 健康检查
    health = validator.health_check()
    print(f"\n健康状态: {health}")
