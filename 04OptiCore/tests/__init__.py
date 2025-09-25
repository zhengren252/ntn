# NeuroTrade Nexus - 策略优化模组测试包
# 遵循核心设计理念：高质量代码和全面测试覆盖

"""
策略优化模组测试包

本包包含策略优化模组的所有测试用例，确保系统的可靠性和稳定性。
测试覆盖以下核心功能：

1. 策略优化测试
2. 回测引擎测试
3. 决策引擎测试
4. 策略模板测试
5. 配置管理测试
6. 集成测试
7. 性能测试

测试环境配置：
- 使用pytest作为测试框架
- 支持异步测试
- 模拟数据和外部依赖
- 测试覆盖率要求90%+
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试环境配置
os.environ["NTN_ENVIRONMENT"] = "test"
os.environ["TESTING"] = "true"


# 异步测试支持
def pytest_configure(config):
    """Pytest配置钩子"""
    # 设置异步事件循环策略
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# 测试常量
TEST_DATA_DIR = project_root / "tests" / "data"
TEST_CONFIG_DIR = project_root / "tests" / "config"
TEST_LOGS_DIR = project_root / "tests" / "logs"

# 确保测试目录存在
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_CONFIG_DIR.mkdir(exist_ok=True)
TEST_LOGS_DIR.mkdir(exist_ok=True)

__version__ = "1.0.0"
__author__ = "NeuroTrade Nexus Team"
__email__ = "support@neurotrade-nexus.com"
