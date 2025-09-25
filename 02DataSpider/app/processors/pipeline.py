# -*- coding: utf-8 -*-
"""
数据处理管道模块

整合数据清洗、验证和格式化功能，提供统一的数据处理接口
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import ConfigManager
from ..utils import Logger
from .data_cleaner import DataCleaner, CleaningLevel
from .data_validator import DataValidator, ValidationLevel
from .data_formatter import DataFormatter, OutputFormat


class ProcessingStage(Enum):
    """处理阶段"""

    CLEANING = "cleaning"
    VALIDATION = "validation"
    FORMATTING = "formatting"
    COMPLETE = "complete"


class ProcessingMode(Enum):
    """处理模式"""

    SEQUENTIAL = "sequential"  # 顺序处理
    PARALLEL = "parallel"  # 并行处理
    ASYNC = "async"  # 异步处理


@dataclass
class ProcessingConfig:
    """处理配置"""

    cleaning_level: CleaningLevel = CleaningLevel.STANDARD
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    output_format: OutputFormat = OutputFormat.DICT
    fail_fast: bool = False
    skip_validation_on_clean_fail: bool = False
    skip_formatting_on_validation_fail: bool = True
    max_workers: int = 4
    processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL


@dataclass
class ProcessingResult:
    """处理结果"""

    success: bool
    data: Optional[Dict[str, Any]]
    original_data: Dict[str, Any]
    stage_results: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    processing_time: float
    stages_completed: List[ProcessingStage]
    metadata: Dict[str, Any]


@dataclass
class BatchProcessingResult:
    """批量处理结果"""

    total_items: int
    successful_items: int
    failed_items: int
    results: List[ProcessingResult]
    processing_time: float
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class DataPipeline:
    """数据处理管道

    整合数据清洗、验证和格式化功能，提供统一的数据处理接口
    """

    def __init__(self, config: ConfigManager, logger: Logger = None):
        """初始化数据处理管道

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or Logger(config)

        # 初始化处理器
        self.cleaner = DataCleaner(config, self.logger)
        self.validator = DataValidator(config, self.logger)
        self.formatter = DataFormatter(config, self.logger)

        # 管道配置
        pipeline_config = config.get_config("processors.pipeline", {})
        self.default_config = ProcessingConfig(
            cleaning_level=CleaningLevel(
                pipeline_config.get("cleaning_level", "standard")
            ),
            validation_level=ValidationLevel(
                pipeline_config.get("validation_level", "standard")
            ),
            output_format=OutputFormat(pipeline_config.get("output_format", "dict")),
            fail_fast=pipeline_config.get("fail_fast", False),
            skip_validation_on_clean_fail=pipeline_config.get(
                "skip_validation_on_clean_fail", False
            ),
            skip_formatting_on_validation_fail=pipeline_config.get(
                "skip_formatting_on_validation_fail", True
            ),
            max_workers=pipeline_config.get("max_workers", 4),
            processing_mode=ProcessingMode(
                pipeline_config.get("processing_mode", "sequential")
            ),
        )

        # 处理钩子
        self.pre_processing_hooks: List[Callable] = []
        self.post_processing_hooks: List[Callable] = []
        self.stage_hooks: Dict[ProcessingStage, List[Callable]] = {
            ProcessingStage.CLEANING: [],
            ProcessingStage.VALIDATION: [],
            ProcessingStage.FORMATTING: [],
        }

        # 统计信息
        self.stats = {
            "items_processed": 0,
            "items_successful": 0,
            "items_failed": 0,
            "total_processing_time": 0.0,
            "stage_stats": {
                "cleaning": {"success": 0, "failed": 0, "time": 0.0},
                "validation": {"success": 0, "failed": 0, "time": 0.0},
                "formatting": {"success": 0, "failed": 0, "time": 0.0},
            },
            "last_processing_time": None,
        }

        self.logger.info("数据处理管道初始化完成")

    def add_pre_processing_hook(self, hook: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """添加预处理钩子

        Args:
            hook: 钩子函数，接收数据并返回处理后的数据
        """
        self.pre_processing_hooks.append(hook)
        self.logger.debug(f"添加预处理钩子: {hook.__name__}")

    def add_post_processing_hook(
        self, hook: Callable[[ProcessingResult], ProcessingResult]
    ):
        """添加后处理钩子

        Args:
            hook: 钩子函数，接收处理结果并返回修改后的结果
        """
        self.post_processing_hooks.append(hook)
        self.logger.debug(f"添加后处理钩子: {hook.__name__}")

    def add_stage_hook(self, stage: ProcessingStage, hook: Callable):
        """添加阶段钩子

        Args:
            stage: 处理阶段
            hook: 钩子函数
        """
        if stage in self.stage_hooks:
            self.stage_hooks[stage].append(hook)
            self.logger.debug(f"添加{stage.value}阶段钩子: {hook.__name__}")

    def process_item(
        self, data: Dict[str, Any], config: ProcessingConfig = None
    ) -> ProcessingResult:
        """处理单个数据项

        Args:
            data: 待处理的数据
            config: 处理配置

        Returns:
            处理结果
        """
        start_time = time.time()

        if config is None:
            config = self.default_config

        self.stats["items_processed"] += 1

        # 初始化结果
        result = ProcessingResult(
            success=False,
            data=None,
            original_data=data.copy(),
            stage_results={},
            errors=[],
            warnings=[],
            processing_time=0.0,
            stages_completed=[],
            metadata={},
        )

        try:
            # 执行预处理钩子
            processed_data = data.copy()
            for hook in self.pre_processing_hooks:
                try:
                    processed_data = hook(processed_data)
                except Exception as e:
                    result.warnings.append(f"预处理钩子失败: {e}")

            # 数据清洗阶段
            cleaning_result = self._execute_cleaning_stage(processed_data, config)
            result.stage_results["cleaning"] = cleaning_result

            if cleaning_result.success:
                processed_data = cleaning_result.cleaned_data
                result.stages_completed.append(ProcessingStage.CLEANING)
                self.stats["stage_stats"]["cleaning"]["success"] += 1
            else:
                self.stats["stage_stats"]["cleaning"]["failed"] += 1
                result.errors.extend(cleaning_result.errors)
                result.warnings.extend(cleaning_result.warnings)

                if config.fail_fast or config.skip_validation_on_clean_fail:
                    result.processing_time = time.time() - start_time
                    self.stats["items_failed"] += 1
                    return result

            # 数据验证阶段
            if not config.skip_validation_on_clean_fail or cleaning_result.success:
                validation_result = self._execute_validation_stage(
                    processed_data, config
                )
                result.stage_results["validation"] = validation_result

                if validation_result.is_valid:
                    result.stages_completed.append(ProcessingStage.VALIDATION)
                    self.stats["stage_stats"]["validation"]["success"] += 1
                else:
                    self.stats["stage_stats"]["validation"]["failed"] += 1
                    result.errors.extend(
                        [issue.message for issue in validation_result.issues]
                    )

                    if config.fail_fast or config.skip_formatting_on_validation_fail:
                        result.processing_time = time.time() - start_time
                        self.stats["items_failed"] += 1
                        return result

            # 数据格式化阶段
            validation_passed = True
            if "validation" in result.stage_results:
                validation_passed = result.stage_results["validation"].is_valid

            if not config.skip_formatting_on_validation_fail or validation_passed:
                formatting_result = self._execute_formatting_stage(
                    processed_data, config
                )
                result.stage_results["formatting"] = formatting_result

                if formatting_result.success:
                    processed_data = formatting_result.formatted_data
                    result.stages_completed.append(ProcessingStage.FORMATTING)
                    self.stats["stage_stats"]["formatting"]["success"] += 1
                else:
                    self.stats["stage_stats"]["formatting"]["failed"] += 1
                    result.errors.extend(formatting_result.errors)
                    result.warnings.extend(formatting_result.warnings)

                    if config.fail_fast:
                        result.processing_time = time.time() - start_time
                        self.stats["items_failed"] += 1
                        return result

            # 设置最终结果
            result.data = processed_data
            result.success = len(result.errors) == 0
            result.stages_completed.append(ProcessingStage.COMPLETE)

            # 添加处理元数据
            if result.data and "metadata" not in result.data:
                result.data["metadata"] = {}
            if result.data:
                result.data["metadata"]["processed_at"] = datetime.utcnow().isoformat()
                result.data["metadata"]["pipeline_version"] = "1.0.0"
                result.data["metadata"]["processing_stages"] = [
                    stage.value for stage in result.stages_completed
                ]

            # 执行后处理钩子
            for hook in self.post_processing_hooks:
                try:
                    result = hook(result)
                except Exception as e:
                    result.warnings.append(f"后处理钩子失败: {e}")

            # 更新统计
            if result.success:
                self.stats["items_successful"] += 1
            else:
                self.stats["items_failed"] += 1

            result.processing_time = time.time() - start_time
            self.stats["total_processing_time"] += result.processing_time
            self.stats["last_processing_time"] = datetime.utcnow().isoformat()

            self.logger.debug(
                f"数据处理完成: 成功={result.success} | "
                f"阶段={len(result.stages_completed)} | "
                f"错误={len(result.errors)} | 警告={len(result.warnings)} | "
                f"耗时={result.processing_time:.3f}s"
            )

            return result

        except Exception as e:
            result.processing_time = time.time() - start_time
            result.errors.append(f"处理异常: {e}")
            self.stats["items_failed"] += 1

            self.logger.error(f"数据处理异常: {e}")
            return result

    def _execute_cleaning_stage(self, data: Dict[str, Any], config: ProcessingConfig):
        """执行清洗阶段"""
        stage_start = time.time()

        # 执行阶段钩子
        for hook in self.stage_hooks[ProcessingStage.CLEANING]:
            try:
                data = hook(data)
            except Exception as e:
                self.logger.warning(f"清洗阶段钩子失败: {e}")

        result = self.cleaner.clean_data(data)

        stage_time = time.time() - stage_start
        self.stats["stage_stats"]["cleaning"]["time"] += stage_time

        return result

    def _execute_validation_stage(self, data: Dict[str, Any], config: ProcessingConfig):
        """执行验证阶段"""
        stage_start = time.time()

        # 执行阶段钩子
        for hook in self.stage_hooks[ProcessingStage.VALIDATION]:
            try:
                data = hook(data)
            except Exception as e:
                self.logger.warning(f"验证阶段钩子失败: {e}")

        result = self.validator.validate_data(data, config.validation_level)

        stage_time = time.time() - stage_start
        self.stats["stage_stats"]["validation"]["time"] += stage_time

        return result

    def _execute_formatting_stage(self, data: Dict[str, Any], config: ProcessingConfig):
        """执行格式化阶段"""
        stage_start = time.time()

        # 执行阶段钩子
        for hook in self.stage_hooks[ProcessingStage.FORMATTING]:
            try:
                data = hook(data)
            except Exception as e:
                self.logger.warning(f"格式化阶段钩子失败: {e}")

        # 临时设置输出格式
        original_format = self.formatter.output_format
        self.formatter.output_format = config.output_format

        result = self.formatter.format_data(data)

        # 恢复原始格式
        self.formatter.output_format = original_format

        stage_time = time.time() - stage_start
        self.stats["stage_stats"]["formatting"]["time"] += stage_time

        return result

    def process_batch(
        self, data_list: List[Dict[str, Any]], config: ProcessingConfig = None
    ) -> BatchProcessingResult:
        """批量处理数据

        Args:
            data_list: 待处理的数据列表
            config: 处理配置

        Returns:
            批量处理结果
        """
        start_time = time.time()

        if config is None:
            config = self.default_config

        results = []
        errors = []
        warnings = []

        try:
            if config.processing_mode == ProcessingMode.SEQUENTIAL:
                # 顺序处理
                for i, data in enumerate(data_list):
                    try:
                        result = self.process_item(data, config)
                        results.append(result)

                        if result.errors:
                            errors.extend(
                                [f"Item {i}: {error}" for error in result.errors]
                            )
                        if result.warnings:
                            warnings.extend(
                                [f"Item {i}: {warning}" for warning in result.warnings]
                            )

                    except Exception as e:
                        error_msg = f"Item {i} 处理异常: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)

            elif config.processing_mode == ProcessingMode.PARALLEL:
                # 并行处理
                with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                    future_to_index = {
                        executor.submit(self.process_item, data, config): i
                        for i, data in enumerate(data_list)
                    }

                    # 按原始顺序收集结果
                    indexed_results = []
                    for future in as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            result = future.result()
                            indexed_results.append((index, result))

                            if result.errors:
                                errors.extend(
                                    [
                                        f"Item {index}: {error}"
                                        for error in result.errors
                                    ]
                                )
                            if result.warnings:
                                warnings.extend(
                                    [
                                        f"Item {index}: {warning}"
                                        for warning in result.warnings
                                    ]
                                )

                        except Exception as e:
                            error_msg = f"Item {index} 处理异常: {e}"
                            errors.append(error_msg)
                            self.logger.error(error_msg)

                    # 按索引排序
                    indexed_results.sort(key=lambda x: x[0])
                    results = [result for _, result in indexed_results]

            elif config.processing_mode == ProcessingMode.ASYNC:
                # 异步处理（在同步上下文中运行）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    results = loop.run_until_complete(
                        self._process_batch_async(data_list, config)
                    )
                finally:
                    loop.close()

            # 计算统计信息
            successful_items = sum(1 for result in results if result.success)
            failed_items = len(results) - successful_items
            processing_time = time.time() - start_time

            self.logger.info(
                f"批量处理完成: 总数={len(data_list)} | "
                f"成功={successful_items} | 失败={failed_items} | "
                f"耗时={processing_time:.3f}s"
            )

            return BatchProcessingResult(
                total_items=len(data_list),
                successful_items=successful_items,
                failed_items=failed_items,
                results=results,
                processing_time=processing_time,
                errors=errors,
                warnings=warnings,
                metadata={
                    "processing_mode": config.processing_mode.value,
                    "max_workers": config.max_workers,
                    "avg_processing_time": processing_time / len(data_list)
                    if data_list
                    else 0,
                },
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"批量处理异常: {e}"
            self.logger.error(error_msg)

            return BatchProcessingResult(
                total_items=len(data_list),
                successful_items=0,
                failed_items=len(data_list),
                results=[],
                processing_time=processing_time,
                errors=[error_msg],
                warnings=warnings,
                metadata={"error": str(e)},
            )

    async def _process_batch_async(
        self, data_list: List[Dict[str, Any]], config: ProcessingConfig
    ) -> List[ProcessingResult]:
        """异步批量处理"""
        semaphore = asyncio.Semaphore(config.max_workers)

        async def process_item_async(data):
            async with semaphore:
                # 在线程池中运行同步处理
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.process_item, data, config)

        tasks = [process_item_async(data) for data in data_list]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()

        # 计算成功率
        if stats["items_processed"] > 0:
            stats["success_rate"] = stats["items_successful"] / stats["items_processed"]
            stats["fail_rate"] = stats["items_failed"] / stats["items_processed"]
            stats["avg_processing_time"] = (
                stats["total_processing_time"] / stats["items_processed"]
            )
        else:
            stats["success_rate"] = 0.0
            stats["fail_rate"] = 0.0
            stats["avg_processing_time"] = 0.0

        # 计算各阶段统计
        for stage, stage_stats in stats["stage_stats"].items():
            total_stage_items = stage_stats["success"] + stage_stats["failed"]
            if total_stage_items > 0:
                stage_stats["success_rate"] = stage_stats["success"] / total_stage_items
                stage_stats["avg_time"] = stage_stats["time"] / total_stage_items
            else:
                stage_stats["success_rate"] = 0.0
                stage_stats["avg_time"] = 0.0

        # 添加子组件统计
        stats["component_stats"] = {
            "cleaner": self.cleaner.get_stats(),
            "validator": self.validator.get_stats(),
            "formatter": self.formatter.get_stats(),
        }

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()

        # 判断整体健康状态
        if stats["success_rate"] >= 0.9:
            status = "healthy"
        elif stats["success_rate"] >= 0.7:
            status = "degraded"
        else:
            status = "unhealthy"

        # 检查各组件健康状态
        component_health = {
            "cleaner": self.cleaner.health_check(),
            "validator": self.validator.health_check(),
            "formatter": self.formatter.health_check(),
        }

        return {
            "status": status,
            "success_rate": stats["success_rate"],
            "items_processed": stats["items_processed"],
            "items_successful": stats["items_successful"],
            "avg_processing_time": stats["avg_processing_time"],
            "last_processing_time": stats["last_processing_time"],
            "component_health": component_health,
        }


if __name__ == "__main__":
    # 测试数据处理管道
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建数据处理管道
    pipeline = DataPipeline(config, logger)

    # 添加测试钩子
    def pre_hook(data):
        data["processed_by"] = "pipeline"
        return data

    def post_hook(result):
        if result.data:
            result.data["pipeline_version"] = "1.0.0"
        return result

    pipeline.add_pre_processing_hook(pre_hook)
    pipeline.add_post_processing_hook(post_hook)

    # 测试数据
    test_data = [
        {
            "title": "Bitcoin价格分析",
            "content": "比特币价格今日表现强劲，突破了重要阻力位。",
            "url": "https://example.com/bitcoin-analysis",
            "timestamp": "2024-01-15T10:30:00Z",
            "category": "crypto",
            "keywords": ["bitcoin", "price", "analysis"],
            "source": "example.com",
        },
        {
            "title": "",  # 空标题
            "content": "短",  # 内容过短
            "url": "invalid-url",
            "timestamp": "invalid-time",
            "keywords": "not a list",
            "source": "test",
        },
        {
            "title": "股市更新",
            "content": "股票市场今日收盘上涨，投资者情绪乐观。",
            "url": "https://finance.com/stock-update",
            "timestamp": "2024-01-15T15:30:00Z",
            "category": "stocks",
            "keywords": ["stocks", "market", "update"],
            "source": "finance.com",
        },
    ]

    # 测试单项处理
    print("开始测试数据处理管道...")
    print("\n=== 单项处理测试 ===")

    for i, data in enumerate(test_data):
        print(f"\n处理数据项 {i+1}:")
        result = pipeline.process_item(data)

        print(f"处理结果: {result.success}")
        print(f"完成阶段: {[stage.value for stage in result.stages_completed]}")
        print(f"处理时间: {result.processing_time:.3f}s")

        if result.errors:
            print(f"错误: {result.errors}")

        if result.warnings:
            print(f"警告: {result.warnings}")

        if result.data:
            print(f"处理后数据: {result.data}")

    # 测试批量处理
    print("\n=== 批量处理测试 ===")

    # 测试不同处理模式
    for mode in [ProcessingMode.SEQUENTIAL, ProcessingMode.PARALLEL]:
        print(f"\n测试{mode.value}模式:")

        batch_config = ProcessingConfig(processing_mode=mode, max_workers=2)

        batch_result = pipeline.process_batch(test_data, batch_config)

        print(
            f"批量处理结果: 总数={batch_result.total_items} | "
            f"成功={batch_result.successful_items} | "
            f"失败={batch_result.failed_items} | "
            f"耗时={batch_result.processing_time:.3f}s"
        )

        if batch_result.errors:
            print(f"批量错误: {batch_result.errors[:3]}...")  # 只显示前3个错误

    # 显示统计信息
    stats = pipeline.get_stats()
    print(f"\n=== 管道统计 ===")
    print(f"处理统计: {stats}")

    # 健康检查
    health = pipeline.health_check()
    print(f"\n=== 健康状态 ===")
    print(f"健康检查: {health}")
