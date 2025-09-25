#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock
from app.processors.pipeline import DataPipeline, ProcessingConfig, ProcessingMode

# 模拟配置
mock_config = Mock()

# 设置配置数据
config_data = {
    "data_processing": {
        "cleaning_level": "standard",
        "validation_enabled": True,
        "output_format": "json",
        "max_workers": 4,
    },
    "processors": {
        "validation": {
            "url_timeout": 5,
            "max_title_length": 200,
            "max_content_length": 50000,
            "min_content_length": 10,
            "allowed_domains": ["example.com", "test.com"],
        }
    },
}


# 配置mock方法
def mock_get_config(key, default=None):
    keys = key.split(".")
    value = config_data
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default


mock_config.get_config = mock_get_config
mock_config.get.return_value = config_data

# 模拟日志
mock_logger = Mock()

# 初始化
pipeline = DataPipeline(mock_config, mock_logger)

# 测试数据
test_batch = [
    {
        "title": "Bitcoin News 1",
        "content": "Content 1",
        "url": "https://example.com/1",
        "timestamp": "2024-01-15T10:30:00Z",
        "source": "example.com",
    },
    {
        "title": "Ethereum News 2",
        "content": "Content 2",
        "url": "https://example.com/2",
        "timestamp": "2024-01-15T10:31:00Z",
        "source": "example.com",
    },
]

# 配置
config = ProcessingConfig(processing_mode=ProcessingMode.SEQUENTIAL, max_workers=1)

print("开始批量处理测试...")
batch_result = pipeline.process_batch(test_batch, config)

print(f"批量处理结果:")
print(f"  总项目数: {batch_result.total_items}")
print(f"  成功项目数: {batch_result.successful_items}")
print(f"  失败项目数: {batch_result.failed_items}")
print(f"  处理时间: {batch_result.processing_time:.3f}s")
print(f"  错误: {batch_result.errors}")
print(f"  警告: {batch_result.warnings}")

print("\n单个结果详情:")
for i, result in enumerate(batch_result.results):
    print(f"  结果 {i+1}:")
    print(f"    成功: {result.success}")
    print(f"    错误: {result.errors}")
    print(f"    警告: {result.warnings}")
    if result.data:
        print(f"    数据字段: {list(result.data.keys())}")
    print()
