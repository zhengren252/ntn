# -*- coding: utf-8 -*-
"""
数据格式化器模块

负责数据格式标准化、结构转换和输出格式化
"""

import time
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, urljoin

from ..config import ConfigManager
from ..utils import Logger
from ..utils.serializers import SerializationManager


class OutputFormat(Enum):
    """输出格式"""

    JSON = "json"
    DICT = "dict"
    PROTOBUF = "protobuf"
    AVRO = "avro"


class DateFormat(Enum):
    """日期格式"""

    ISO8601 = "iso8601"  # 2024-01-15T10:30:00Z
    TIMESTAMP = "timestamp"  # 1705315800
    DATETIME = "datetime"  # 2024-01-15 10:30:00
    CUSTOM = "custom"  # 自定义格式


@dataclass
class FormattingRule:
    """格式化规则"""

    field: str
    rule_type: str
    parameters: Dict[str, Any]
    priority: int = 0
    enabled: bool = True


@dataclass
class FormattingResult:
    """格式化结果"""

    success: bool
    formatted_data: Optional[Dict[str, Any]]
    original_data: Dict[str, Any]
    applied_rules: List[str]
    errors: List[str]
    warnings: List[str]
    formatting_time: float
    metadata: Dict[str, Any]


class FieldFormatter:
    """字段格式化器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        # 格式化配置
        format_config = config.get_config("processors.formatting", {})
        self.date_format = DateFormat(format_config.get("date_format", "iso8601"))
        self.custom_date_format = format_config.get(
            "custom_date_format", "%Y-%m-%d %H:%M:%S"
        )
        self.timezone_aware = format_config.get("timezone_aware", True)
        self.url_normalization = format_config.get("url_normalization", True)
        self.text_normalization = format_config.get("text_normalization", True)

        # 字段映射
        self.field_mapping = format_config.get("field_mapping", {})

        # 默认值
        self.default_values = format_config.get("default_values", {})

        self.logger.info("字段格式化器初始化完成")

    def format_timestamp(self, timestamp: Any) -> str:
        """格式化时间戳

        Args:
            timestamp: 时间戳（字符串、数字或datetime对象）

        Returns:
            格式化后的时间戳字符串
        """
        try:
            # 转换为datetime对象
            if isinstance(timestamp, str):
                # 处理ISO格式
                if timestamp.endswith("Z"):
                    dt = datetime.fromisoformat(timestamp[:-1]).replace(
                        tzinfo=timezone.utc
                    )
                elif "+" in timestamp or timestamp.endswith(("00", "30", "45")):
                    dt = datetime.fromisoformat(timestamp)
                else:
                    dt = datetime.fromisoformat(timestamp)
                    if self.timezone_aware and dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
            elif isinstance(timestamp, (int, float)):
                # Unix时间戳
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, datetime):
                dt = timestamp
                if self.timezone_aware and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                raise ValueError(f"不支持的时间戳类型: {type(timestamp)}")

            # 根据配置格式化
            if self.date_format == DateFormat.ISO8601:
                return dt.isoformat()
            elif self.date_format == DateFormat.TIMESTAMP:
                return str(int(dt.timestamp()))
            elif self.date_format == DateFormat.DATETIME:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            elif self.date_format == DateFormat.CUSTOM:
                return dt.strftime(self.custom_date_format)
            else:
                return dt.isoformat()

        except Exception as e:
            self.logger.warning(f"时间戳格式化失败: {timestamp} -> {e}")
            return str(timestamp)

    def format_url(self, url: str) -> str:
        """格式化URL

        Args:
            url: 原始URL

        Returns:
            格式化后的URL
        """
        if not url or not self.url_normalization:
            return url

        try:
            # 解析URL
            parsed = urlparse(url)

            # 标准化协议
            scheme = parsed.scheme.lower() if parsed.scheme else "https"

            # 标准化域名
            netloc = parsed.netloc.lower() if parsed.netloc else ""

            # 移除默认端口
            if ":80" in netloc and scheme == "http":
                netloc = netloc.replace(":80", "")
            elif ":443" in netloc and scheme == "https":
                netloc = netloc.replace(":443", "")

            # 标准化路径
            path = parsed.path.lower() if parsed.path else "/"
            if not path:
                path = "/"

            # 重构URL
            normalized_url = f"{scheme}://{netloc}{path}"
            if parsed.query:
                normalized_url += f"?{parsed.query.lower()}"
            if parsed.fragment:
                normalized_url += f"#{parsed.fragment}"

            return normalized_url

        except Exception as e:
            self.logger.warning(f"URL格式化失败: {url} -> {e}")
            return url

    def format_text(self, text: str) -> str:
        """格式化文本

        Args:
            text: 原始文本

        Returns:
            格式化后的文本
        """
        if not text or not self.text_normalization:
            return text

        try:
            # 清理HTML标签
            text = re.sub(r"<[^>]+>", "", text)

            # 标准化空白字符
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

            # 标准化引号
            text = re.sub(r'[""]', '"', text)
            text = re.sub(r"[" "]", "'", text)

            # 移除多余的标点符号
            text = re.sub(r"[.]{2,}", "...", text)
            text = re.sub(r"[!]{2,}", "!", text)
            text = re.sub(r"[?]{2,}", "?", text)

            return text

        except Exception as e:
            self.logger.warning(f"文本格式化失败: {text[:50]}... -> {e}")
            return text

    def format_keywords(self, keywords: List[str]) -> List[str]:
        """格式化关键词

        Args:
            keywords: 原始关键词列表

        Returns:
            格式化后的关键词列表
        """
        if not isinstance(keywords, list):
            return []

        formatted_keywords = []
        seen = set()

        for keyword in keywords:
            if not isinstance(keyword, str):
                continue

            # 标准化关键词
            keyword = keyword.strip().lower()

            # 移除空关键词和重复关键词
            if keyword and keyword not in seen:
                formatted_keywords.append(keyword)
                seen.add(keyword)

        return formatted_keywords

    def format_category(self, category: str) -> str:
        """格式化分类

        Args:
            category: 原始分类

        Returns:
            格式化后的分类
        """
        if not category:
            return "general"

        # 保持原始格式，只做基本清理
        category = category.strip()

        return category or "general"

    def format_source(self, source: str, url: str = None) -> str:
        """格式化来源

        Args:
            source: 原始来源
            url: URL（用于提取域名）

        Returns:
            格式化后的来源
        """
        if source:
            # 清理HTML标签
            source = re.sub(r"<[^>]+>", "", source)
            return source.strip()

        # 如果没有来源，尝试从URL提取
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                # 移除www前缀
                if domain.startswith("www."):
                    domain = domain[4:]
                return domain
            except Exception:
                pass

        return "unknown"


class DataFormatter:
    """数据格式化器主类

    负责数据格式标准化、结构转换和输出格式化
    """

    def __init__(self, config: ConfigManager, logger: Logger = None):
        """初始化数据格式化器

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or Logger(config)

        # 初始化字段格式化器
        self.field_formatter = FieldFormatter(config, self.logger)

        # 序列化管理器
        self.serialization_manager = SerializationManager(config, self.logger)

        # 格式化配置
        self.format_config = config.get_config("processors.formatting", {})
        self.output_format = OutputFormat(
            self.format_config.get("output_format", "dict")
        )
        self.include_metadata = self.format_config.get("include_metadata", True)
        self.remove_null_fields = self.format_config.get("remove_null_fields", True)

        # 字段映射和规则
        self.field_mapping = self.format_config.get("field_mapping", {})
        self.formatting_rules = self._load_formatting_rules()

        # 输出模板
        self.output_template = self.format_config.get(
            "output_template",
            {
                "id": None,
                "title": None,
                "content": None,
                "url": None,
                "timestamp": None,
                "category": None,
                "keywords": [],
                "source": None,
                "metadata": {},
                # 标准DataItem中的metrics嵌套结构
                "metrics": {
                    "relevance_score": 0.0,
                    "sentiment_score": 0.0,
                    "word_count": 0,
                    "view_count": 0,
                    "share_count": 0,
                },
                # 兼容旧版的扁平字段（向后兼容消费者）
                "relevance_score": 0.0,
                "sentiment_score": 0.0,
                "word_count": 0,
                "view_count": 0,
                "share_count": 0,
            },
        )

        # 统计信息
        self.stats = {
            "items_formatted": 0,
            "items_success": 0,
            "items_failed": 0,
            "total_formatting_time": 0.0,
            "rules_applied": 0,
            "last_formatting_time": None,
        }

        self.logger.info("数据格式化器初始化完成")

    def _load_formatting_rules(self) -> List[FormattingRule]:
        """加载格式化规则

        Returns:
            格式化规则列表
        """
        rules_config = self.format_config.get("rules", [])
        rules = []

        for rule_config in rules_config:
            try:
                rule = FormattingRule(
                    field=rule_config["field"],
                    rule_type=rule_config["type"],
                    parameters=rule_config.get("parameters", {}),
                    priority=rule_config.get("priority", 0),
                    enabled=rule_config.get("enabled", True),
                )
                rules.append(rule)
            except KeyError as e:
                self.logger.warning(f"格式化规则配置错误: {e}")

        # 按优先级排序
        rules.sort(key=lambda x: x.priority, reverse=True)
        return rules

    def format_data(self, data: Dict[str, Any]) -> FormattingResult:
        """格式化数据

        Args:
            data: 原始数据

        Returns:
            格式化结果
        """
        start_time = time.time()

        self.stats["items_formatted"] += 1
        applied_rules = []
        errors = []
        warnings = []

        try:
            # 复制数据以避免修改原始数据
            formatted_data = data.copy()

            # 应用字段映射
            formatted_data = self._apply_field_mapping(formatted_data)

            # 应用格式化规则
            for rule in self.formatting_rules:
                if not rule.enabled:
                    continue

                try:
                    formatted_data = self._apply_formatting_rule(formatted_data, rule)
                    applied_rules.append(f"{rule.field}:{rule.rule_type}")
                    self.stats["rules_applied"] += 1
                except Exception as e:
                    error_msg = f"规则应用失败 {rule.field}:{rule.rule_type} -> {e}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)

            # 标准化核心字段
            formatted_data = self._format_core_fields(formatted_data, warnings)

            # 应用输出模板
            formatted_data = self._apply_output_template(formatted_data)

            # 移除空字段
            if self.remove_null_fields:
                formatted_data = self._remove_null_fields(formatted_data)

            # 添加元数据
            if self.include_metadata:
                formatted_data = self._add_metadata(formatted_data, applied_rules)

            # 转换输出格式
            formatted_data = self._convert_output_format(formatted_data)

            formatting_time = time.time() - start_time
            self.stats["total_formatting_time"] += formatting_time
            self.stats["items_success"] += 1
            self.stats["last_formatting_time"] = datetime.utcnow().isoformat()

            self.logger.debug(
                f"数据格式化完成: 规则数量={len(applied_rules)} | "
                f"错误数量={len(errors)} | 警告数量={len(warnings)} | "
                f"耗时={formatting_time:.3f}s"
            )

            return FormattingResult(
                success=True,
                formatted_data=formatted_data,
                original_data=data,
                applied_rules=applied_rules,
                errors=errors,
                warnings=warnings,
                formatting_time=formatting_time,
                metadata={
                    "rules_applied_count": len(applied_rules),
                    "output_format": self.output_format.value,
                },
            )

        except Exception as e:
            formatting_time = time.time() - start_time
            self.stats["items_failed"] += 1

            error_msg = f"数据格式化异常: {e}"
            self.logger.error(error_msg)

            return FormattingResult(
                success=False,
                formatted_data=None,
                original_data=data,
                applied_rules=applied_rules,
                errors=[error_msg],
                warnings=warnings,
                formatting_time=formatting_time,
                metadata={"error": str(e)},
            )

    def _apply_field_mapping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用字段映射

        Args:
            data: 数据

        Returns:
            映射后的数据
        """
        if not self.field_mapping:
            return data

        mapped_data = {}

        for old_field, new_field in self.field_mapping.items():
            if old_field in data:
                mapped_data[new_field] = data[old_field]
            elif old_field not in self.field_mapping.values():
                # 保留未映射的字段
                if old_field in data:
                    mapped_data[old_field] = data[old_field]

        # 保留未在映射中的字段
        for field, value in data.items():
            if field not in self.field_mapping and field not in mapped_data:
                mapped_data[field] = value

        return mapped_data

    def _apply_formatting_rule(
        self, data: Dict[str, Any], rule: FormattingRule
    ) -> Dict[str, Any]:
        """应用格式化规则

        Args:
            data: 数据
            rule: 格式化规则

        Returns:
            应用规则后的数据
        """
        if rule.field not in data:
            return data

        value = data[rule.field]

        if rule.rule_type == "uppercase":
            if isinstance(value, str):
                data[rule.field] = value.upper()
        elif rule.rule_type == "lowercase":
            if isinstance(value, str):
                data[rule.field] = value.lower()
        elif rule.rule_type == "trim":
            if isinstance(value, str):
                data[rule.field] = value.strip()
        elif rule.rule_type == "replace":
            if isinstance(value, str):
                pattern = rule.parameters.get("pattern", "")
                replacement = rule.parameters.get("replacement", "")
                data[rule.field] = re.sub(pattern, replacement, value)
        elif rule.rule_type == "default":
            if not value:
                data[rule.field] = rule.parameters.get("value", "")
        elif rule.rule_type == "truncate":
            if isinstance(value, str):
                max_length = rule.parameters.get("max_length", 100)
                if len(value) > max_length:
                    data[rule.field] = value[:max_length] + "..."

        return data

    def _format_core_fields(
        self, data: Dict[str, Any], warnings: List[str]
    ) -> Dict[str, Any]:
        """格式化核心字段

        Args:
            data: 数据
            warnings: 警告列表

        Returns:
            格式化后的数据
        """
        # 格式化时间戳
        if "timestamp" in data:
            try:
                data["timestamp"] = self.field_formatter.format_timestamp(
                    data["timestamp"]
                )
            except Exception as e:
                warnings.append(f"时间戳格式化失败: {e}")

        # 格式化URL
        if "url" in data:
            try:
                data["url"] = self.field_formatter.format_url(data["url"])
            except Exception as e:
                warnings.append(f"URL格式化失败: {e}")

        # 格式化文本字段
        for field in ["title", "content", "summary", "author"]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = self.field_formatter.format_text(data[field])
                except Exception as e:
                    warnings.append(f"{field}格式化失败: {e}")

        # 格式化关键词
        if "keywords" in data:
            try:
                data["keywords"] = self.field_formatter.format_keywords(
                    data["keywords"]
                )
            except Exception as e:
                warnings.append(f"关键词格式化失败: {e}")

        # 格式化分类
        if "category" in data:
            try:
                data["category"] = self.field_formatter.format_category(
                    data["category"]
                )
            except Exception as e:
                warnings.append(f"分类格式化失败: {e}")

        # 格式化来源
        if "source" in data:
            try:
                data["source"] = self.field_formatter.format_source(
                    data["source"], data.get("url")
                )
            except Exception as e:
                warnings.append(f"来源格式化失败: {e}")

        # 将可能为字符串的计数字段转为整数
        for field in ["views", "likes", "shares", "comments"]:
            if field in data and isinstance(data[field], str):
                try:
                    numeric_value = data[field].replace(",", "")
                    data[field] = int(float(numeric_value))
                except (ValueError, AttributeError) as e:
                    warnings.append(f"{field}数值格式化失败: {e}")

        # 生成或补齐metrics结构（标准化）
        metrics = data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
        # sentiment 兼容字段映射
        if "sentiment" in data and "sentiment_score" not in metrics:
            try:
                metrics["sentiment_score"] = float(data.get("sentiment", 0.0))
            except Exception:
                metrics["sentiment_score"] = 0.0
        # views -> view_count
        if "views" in data and "view_count" not in metrics:
            try:
                metrics["view_count"] = int(data.get("views", 0) or 0)
            except Exception:
                metrics["view_count"] = 0
        # shares -> share_count
        if "shares" in data and "share_count" not in metrics:
            try:
                metrics["share_count"] = int(data.get("shares", 0) or 0)
            except Exception:
                metrics["share_count"] = 0
        # word_count: 根据content估算
        if "word_count" not in metrics:
            try:
                content = data.get("content") or ""
                # 简单词数估算：按空白切分
                metrics["word_count"] = int(len(str(content).split())) if content else 0
            except Exception:
                metrics["word_count"] = 0
        # relevance_score 默认0.0，留给上游评分器
        if "relevance_score" not in metrics:
            metrics["relevance_score"] = 0.0
        # 补齐缺省字段与类型
        metrics = {
            "relevance_score": float(metrics.get("relevance_score", 0.0)),
            "sentiment_score": float(metrics.get("sentiment_score", 0.0)),
            "word_count": int(metrics.get("word_count", 0)),
            "view_count": int(metrics.get("view_count", 0)),
            "share_count": int(metrics.get("share_count", 0)),
        }
        data["metrics"] = metrics

        # 回填扁平兼容字段
        data["relevance_score"] = metrics["relevance_score"]
        data["sentiment_score"] = metrics["sentiment_score"]
        data["word_count"] = metrics["word_count"]
        data["view_count"] = metrics["view_count"]
        data["share_count"] = metrics["share_count"]

        return data

    def _apply_output_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用输出模板

        Args:
            data: 数据

        Returns:
            应用模板后的数据
        """
        if not self.output_template:
            return data

        template_data = {}

        for field, default_value in self.output_template.items():
            if field in data:
                template_data[field] = data[field]
            else:
                template_data[field] = default_value

        # 保留模板外的字段
        for field, value in data.items():
            if field not in template_data:
                template_data[field] = value

        return template_data

    def _remove_null_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """移除空字段

        Args:
            data: 数据

        Returns:
            移除空字段后的数据
        """
        cleaned_data = {}

        for field, value in data.items():
            # 检查是否为空值
            is_empty = (
                value is None
                or value == ""
                or value == []
                or (isinstance(value, str) and value.strip() == "")
            )

            if not is_empty:
                if isinstance(value, dict):
                    cleaned_value = self._remove_null_fields(value)
                    if cleaned_value:
                        cleaned_data[field] = cleaned_value
                else:
                    cleaned_data[field] = value

        return cleaned_data

    def _add_metadata(
        self, data: Dict[str, Any], applied_rules: List[str]
    ) -> Dict[str, Any]:
        """添加元数据

        Args:
            data: 数据
            applied_rules: 应用的规则列表

        Returns:
            添加元数据后的数据
        """
        if "metadata" not in data:
            data["metadata"] = {}

        data["metadata"].update(
            {
                "formatted_at": datetime.utcnow().isoformat(),
                "formatter_version": "1.0.0",
                "applied_rules": applied_rules,
                "output_format": self.output_format.value,
            }
        )

        return data

    def _convert_output_format(self, data: Dict[str, Any]) -> Union[Dict, str, bytes]:
        """转换输出格式

        Args:
            data: 数据

        Returns:
            转换后的数据
        """
        if self.output_format == OutputFormat.DICT:
            return data
        elif self.output_format == OutputFormat.JSON:
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif self.output_format == OutputFormat.PROTOBUF:
            try:
                if self.serialization_manager.is_format_available("protobuf"):
                    return self.serialization_manager.serialize(data, "protobuf")
                else:
                    self.logger.warning("Protobuf库未安装，返回JSON格式")
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.error(f"Protobuf序列化失败: {e}，返回JSON格式")
                return json.dumps(data, ensure_ascii=False, indent=2)
        elif self.output_format == OutputFormat.AVRO:
            try:
                if self.serialization_manager.is_format_available("avro"):
                    return self.serialization_manager.serialize(data, "avro")
                else:
                    self.logger.warning("Avro库未安装，返回JSON格式")
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.error(f"Avro序列化失败: {e}，返回JSON格式")
                return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return data

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()

        # 计算成功率
        if stats["items_formatted"] > 0:
            stats["success_rate"] = stats["items_success"] / stats["items_formatted"]
            stats["fail_rate"] = stats["items_failed"] / stats["items_formatted"]
            stats["avg_rules_per_item"] = (
                stats["rules_applied"] / stats["items_formatted"]
            )
        else:
            stats["success_rate"] = 0.0
            stats["fail_rate"] = 0.0
            stats["avg_rules_per_item"] = 0.0

        # 计算平均格式化时间
        if stats["items_formatted"] > 0:
            stats["avg_formatting_time"] = (
                stats["total_formatting_time"] / stats["items_formatted"]
            )
        else:
            stats["avg_formatting_time"] = 0.0

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()

        # 判断健康状态
        if stats["success_rate"] >= 0.95:
            status = "healthy"
        elif stats["success_rate"] >= 0.8:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "success_rate": stats["success_rate"],
            "items_formatted": stats["items_formatted"],
            "items_success": stats["items_success"],
            "rules_applied": stats["rules_applied"],
            "avg_formatting_time": stats["avg_formatting_time"],
            "last_formatting_time": stats["last_formatting_time"],
        }


if __name__ == "__main__":
    # 测试数据格式化器
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建数据格式化器
    formatter = DataFormatter(config, logger)

    # 测试数据
    test_data = [
        {
            "title": "  Bitcoin Price Analysis  ",
            "content": "Bitcoin price has been volatile...   Multiple spaces   and\n\nnewlines.",
            "url": "HTTP://EXAMPLE.COM:443/news/bitcoin",
            "timestamp": "2024-01-15T10:30:00Z",
            "category": "Crypto Currency",
            "keywords": ["Bitcoin", "PRICE", "analysis", "bitcoin", ""],
            "source": "  Example News  ",
            "extra_field": "should be preserved",
        },
        {
            "headline": "Stock Market Update",  # 需要映射到title
            "body": "Market analysis...",  # 需要映射到content
            "link": "https://finance.com/stocks",
            "published": 1705315800,  # Unix时间戳
            "tags": ["stocks", "market", "finance"],
            "publisher": "finance.com",
        },
    ]

    # 测试格式化
    print("开始测试数据格式化器...")

    for i, data in enumerate(test_data):
        print(f"\n测试数据 {i+1}:")
        print(f"原始数据: {data}")

        result = formatter.format_data(data)

        print(f"格式化结果: {result.success}")
        print(f"应用规则: {result.applied_rules}")
        print(f"格式化时间: {result.formatting_time:.3f}s")

        if result.errors:
            print(f"错误: {result.errors}")

        if result.warnings:
            print(f"警告: {result.warnings}")

        if result.formatted_data:
            print(f"格式化后数据: {result.formatted_data}")

    # 显示统计信息
    stats = formatter.get_stats()
    print(f"\n格式化统计: {stats}")

    # 健康检查
    health = formatter.health_check()
    print(f"\n健康状态: {health}")
