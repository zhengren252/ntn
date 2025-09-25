# -*- coding: utf-8 -*-
"""
数据清洗器模块

负责数据清洗、去重、标准化和质量控制
"""

import re
import time
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from ..config import ConfigManager
from ..utils import Logger


class CleaningLevel(Enum):
    """清洗级别"""

    BASIC = "basic"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


class DataQuality(Enum):
    """数据质量等级"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INVALID = "invalid"


@dataclass
class CleaningResult:
    """清洗结果"""

    success: bool
    original_data: Dict[str, Any]
    cleaned_data: Optional[Dict[str, Any]]
    quality_score: float
    quality_level: DataQuality
    issues_found: List[str]
    cleaning_time: float
    metadata: Dict[str, Any]


class TextCleaner:
    """文本清洗器"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger

        text_config = config.get_config("processors.text_cleaning", {})
        self.min_content_length = text_config.get("min_content_length", 50)
        self.max_content_length = text_config.get("max_content_length", 10000)
        self.remove_html = text_config.get("remove_html", True)
        self.normalize_whitespace = text_config.get("normalize_whitespace", True)

        self.logger.info("文本清洗器初始化完成")

    def clean_text(
        self, text: str, level: CleaningLevel = CleaningLevel.STANDARD
    ) -> str:
        """清洗文本"""
        if not text:
            return ""

        cleaned_text = self._basic_cleaning(text)

        if level == CleaningLevel.BASIC:
            return cleaned_text

        cleaned_text = self._standard_cleaning(cleaned_text)

        if level == CleaningLevel.STANDARD:
            return cleaned_text

        cleaned_text = self._aggressive_cleaning(cleaned_text)
        return cleaned_text

    def _basic_cleaning(self, text: str) -> str:
        """基础清洗"""
        if self.remove_html:
            text = self._remove_html_tags(text)

        if self.normalize_whitespace:
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

        return text

    def _standard_cleaning(self, text: str) -> str:
        """标准清洗"""
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        text = re.sub(r"[.,;:!?]{2,}", lambda m: m.group()[0], text)
        return text

    def _aggressive_cleaning(self, text: str) -> str:
        """激进清洗"""
        return text

    def _remove_html_tags(self, text: str) -> str:
        """移除HTML标签"""
        if BeautifulSoup:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text()
        else:
            return re.sub(r"<[^>]+>", "", text)


class DataCleaner:
    """数据清洗器主类"""

    def __init__(self, config: ConfigManager, logger: Logger):
        self.config = config
        self.logger = logger
        self.text_cleaner = TextCleaner(config, logger)

    def clean_data(self, data: Dict[str, Any]) -> CleaningResult:
        """清洗数据"""
        start_time = time.time()

        try:
            cleaned_data = data.copy()
            issues = []

            # 清理包含危险内容的字段（清理而不是删除）
            dangerous_patterns = [
                r"<script[^>]*>.*?</script>",
                r"onerror\s*=[^\s>]*",
                r"onclick\s*=[^\s>]*",
                r"onload\s*=[^\s>]*",
                r'javascript:[^\s"\'>]*',
                r'vbscript:[^\s"\'>]*',
            ]

            # 对于重要字段（如title, content），清理危险内容而不是删除字段
            important_fields = {"title", "content", "url", "source", "author"}
            fields_to_remove = []

            for field, value in cleaned_data.items():
                if isinstance(value, str):
                    original_value = value
                    # 清理危险内容
                    for pattern in dangerous_patterns:
                        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

                    if value != original_value:
                        if field in important_fields:
                            # 重要字段：清理后保留
                            cleaned_data[field] = value.strip()
                            issues.append(f"清理字段中的危险内容: {field}")
                        else:
                            # 非重要字段：如果包含危险内容则删除
                            fields_to_remove.append(field)
                            issues.append(f"移除包含危险内容的字段: {field}")

            for field in fields_to_remove:
                del cleaned_data[field]

            if "title" in cleaned_data:
                cleaned_data["title"] = self.text_cleaner.clean_text(
                    cleaned_data["title"]
                )

            if "content" in cleaned_data:
                cleaned_data["content"] = self.text_cleaner.clean_text(
                    cleaned_data["content"]
                )

            processing_time = time.time() - start_time

            return CleaningResult(
                success=True,
                original_data=data,
                cleaned_data=cleaned_data,
                quality_score=0.8,
                quality_level=DataQuality.HIGH,
                issues_found=issues,
                cleaning_time=processing_time,
                metadata={},
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"数据清洗失败: {e}")

            return CleaningResult(
                success=False,
                original_data=data,
                cleaned_data=None,
                quality_score=0.0,
                quality_level=DataQuality.INVALID,
                issues_found=[str(e)],
                cleaning_time=processing_time,
                metadata={"error": str(e)},
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {"processed": 0}

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {"status": "healthy"}
