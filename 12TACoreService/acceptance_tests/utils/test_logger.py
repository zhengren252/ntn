# 测试日志记录器
# Test Logger

import logging
import os
from datetime import datetime
from typing import Optional


class TestLogger:
    """验收测试专用日志记录器"""

    def __init__(self, name: str, log_dir: str = "./acceptance_tests/logs"):
        self.name = name
        self.log_dir = log_dir
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)

        # 创建日志记录器
        logger = logging.getLogger(f"acceptance_test_{self.name}")
        logger.setLevel(logging.DEBUG)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        # 创建文件处理器
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"{self.name}_{timestamp}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def info(self, message: str, **kwargs):
        """记录信息日志"""
        self.logger.info(message, **kwargs)

    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        self.logger.debug(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录错误日志"""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        self.logger.critical(message, **kwargs)

    def log_test_start(self, test_name: str, test_id: str):
        """记录测试开始"""
        self.info(f"=== 测试开始: {test_name} (ID: {test_id}) ===")

    def log_test_end(self, test_name: str, test_id: str, result: str, duration: float):
        """记录测试结束"""
        self.info(
            f"=== 测试结束: {test_name} (ID: {test_id}) - 结果: {result} - 耗时: {duration:.2f}s ==="
        )

    def log_test_step(self, step: str, details: Optional[str] = None):
        """记录测试步骤"""
        message = f"步骤: {step}"
        if details:
            message += f" - {details}"
        self.info(message)

    def log_verification(self, point: str, result: bool, details: Optional[str] = None):
        """记录验证点结果"""
        status = "✓ 通过" if result else "✗ 失败"
        message = f"验证点: {point} - {status}"
        if details:
            message += f" - {details}"

        if result:
            self.info(message)
        else:
            self.error(message)

    def log_performance(self, metric: str, value: float, unit: str = ""):
        """记录性能指标"""
        self.info(f"性能指标: {metric} = {value} {unit}")

    def log_error_details(self, error: Exception, context: str = ""):
        """记录详细错误信息"""
        error_msg = f"错误详情: {type(error).__name__}: {str(error)}"
        if context:
            error_msg = f"{context} - {error_msg}"
        self.error(error_msg)

        # 记录堆栈跟踪
        import traceback

        self.debug(f"堆栈跟踪:\n{traceback.format_exc()}")
