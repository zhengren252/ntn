"""Debug test module for OptiCore strategy optimization.

This module provides debugging functionality for testing the strategy optimization workflow.
"""
import asyncio
import os
import sys
import traceback

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from tests.test_optimizer import TestStrategyOptimizerModule
except ImportError:
    print("Warning: OptiCore.tests.test_optimizer module not found")
    TestStrategyOptimizerModule = None


async def run_test():
    """Run the end-to-end optimization workflow test.

    Returns:
        None
    """
    if TestStrategyOptimizerModule is None:
        print("Cannot run test: TestStrategyOptimizerModule not available")
        return

    try:
        # 先调用类级别的初始化
        TestStrategyOptimizerModule.setUpClass()

        test = TestStrategyOptimizerModule()
        test.setUp()

        # 直接调用测试方法的原始函数，绕过async_test装饰器
        await test.__class__.test_end_to_end_optimization_workflow.__wrapped__(test)
        print("Test passed!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_test())
