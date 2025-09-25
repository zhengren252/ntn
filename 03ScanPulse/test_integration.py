#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试脚本
测试扫描器模组与TACoreService的集成功能
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
import structlog
import yaml

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from scanner.adapters.adapter_manager import AdapterManager
from scanner.adapters.trading_agents_cn_adapter import TACoreServiceAdapter
from scanner.config.manager import ConfigManager
from scanner.utils.enhanced_logger import setup_logger

logger = structlog.get_logger(__name__)


class IntegrationTester:
    """集成测试器"""

    def __init__(self):
        self.config_manager = None
        self.adapter_manager = None
        self.tacore_adapter = None

    def setup(self) -> bool:
        """设置测试环境"""
        try:
            # 设置日志
            setup_logger(level="INFO", format_type="json")

            # 加载配置
            self.config_manager = ConfigManager()
            if not self.config_manager.load_config():
                logger.error("Failed to load configuration")
                return False

            # 初始化适配器管理器
            config = self.config_manager.get_config()
            self.adapter_manager = AdapterManager(config)

            if not self.adapter_manager.initialize():
                logger.error("Failed to initialize adapter manager")
                return False

            # 获取TACoreService适配器
            self.tacore_adapter = self.adapter_manager.get_tacore_service_adapter()
            if not self.tacore_adapter:
                logger.error("TACoreService adapter not found")
                return False

            logger.info("Integration test setup completed")
            return True

        except Exception as e:
            logger.error("Setup failed", error=str(e))
            return False

    async def test_tacore_service_connection(self) -> bool:
        """测试TACoreService连接"""
        try:
            logger.info("Testing TACoreService connection...")

            # 检查连接状态
            if not self.tacore_adapter.is_connected():
                logger.error("TACoreService adapter not connected")
                return False

            # 执行健康检查
            health_result = await self.tacore_adapter.health_check_detailed()

            if health_result.get("healthy"):
                logger.info(
                    "TACoreService connection test passed", health=health_result
                )
                return True
            else:
                logger.error("TACoreService health check failed", health=health_result)
                return False

        except Exception as e:
            logger.error("TACoreService connection test failed", error=str(e))
            return False

    async def test_market_scan(self) -> bool:
        """测试市场扫描功能"""
        try:
            logger.info("Testing market scan functionality...")

            # 测试交易对列表
            test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

            # 执行扫描
            scan_results = await self.tacore_adapter.scan_symbols(test_symbols)

            if scan_results:
                logger.info(
                    "Market scan test passed",
                    symbol_count=len(test_symbols),
                    result_count=len(scan_results),
                )

                # 显示扫描结果
                for result in scan_results:
                    logger.info(
                        "Scan result",
                        symbol=result.get("symbol"),
                        price=result.get("price"),
                        score=result.get("score"),
                    )

                return True
            else:
                logger.error("Market scan returned no results")
                return False

        except Exception as e:
            logger.error("Market scan test failed", error=str(e))
            return False

    async def test_symbol_analysis(self) -> bool:
        """测试交易对分析功能"""
        try:
            logger.info("Testing symbol analysis functionality...")

            # 测试交易对
            test_symbol = "BTCUSDT"

            # 执行详细分析
            analysis_result = await self.tacore_adapter.analyze_symbol_detailed(
                test_symbol
            )

            if analysis_result:
                logger.info(
                    "Symbol analysis test passed",
                    symbol=test_symbol,
                    analysis_keys=list(analysis_result.keys()),
                )

                # 显示分析结果
                market_data = analysis_result.get("market_data", {})
                analysis = analysis_result.get("analysis", {})

                logger.info(
                    "Analysis details",
                    price=market_data.get("price"),
                    volume=market_data.get("volume"),
                    analysis_summary=analysis,
                )

                return True
            else:
                logger.error("Symbol analysis returned no results")
                return False

        except Exception as e:
            logger.error("Symbol analysis test failed", error=str(e))
            return False

    async def test_market_data_retrieval(self) -> bool:
        """测试市场数据获取功能"""
        try:
            logger.info("Testing market data retrieval...")

            # 测试交易对
            test_symbol = "BTCUSDT"

            # 获取市场数据
            market_data = self.tacore_adapter.get_market_data(test_symbol)

            if market_data:
                logger.info(
                    "Market data retrieval test passed",
                    symbol=test_symbol,
                    data_keys=list(market_data.keys()),
                )

                # 显示市场数据
                logger.info(
                    "Market data details",
                    price=market_data.get("price"),
                    volume=market_data.get("volume"),
                    change_24h=market_data.get("change_24h"),
                )

                return True
            else:
                logger.error("Market data retrieval returned no results")
                return False

        except Exception as e:
            logger.error("Market data retrieval test failed", error=str(e))
            return False

    async def test_market_overview(self) -> bool:
        """测试市场概览功能"""
        try:
            logger.info("Testing market overview functionality...")

            # 获取市场概览
            overview = await self.tacore_adapter.get_market_overview()

            if overview:
                logger.info(
                    "Market overview test passed", overview_keys=list(overview.keys())
                )

                # 显示概览信息
                summary = overview.get("summary", {})
                logger.info(
                    "Market overview summary",
                    total_symbols=summary.get("total_symbols"),
                    active_symbols=summary.get("active_symbols"),
                    news_count=summary.get("news_count"),
                )

                return True
            else:
                logger.error("Market overview returned no results")
                return False

        except Exception as e:
            logger.error("Market overview test failed", error=str(e))
            return False

    def test_adapter_manager_integration(self) -> bool:
        """测试适配器管理器集成"""
        try:
            logger.info("Testing adapter manager integration...")

            # 检查适配器管理器状态
            stats = self.adapter_manager.get_stats()
            logger.info("Adapter manager stats", stats=stats)

            # 执行健康检查
            health = self.adapter_manager.health_check()
            logger.info("Adapter manager health", health=health)

            # 测试通过适配器管理器获取市场数据
            market_data = self.adapter_manager.get_market_data(
                "BTCUSDT", "tacore_service"
            )

            if market_data:
                logger.info(
                    "Adapter manager integration test passed",
                    data_keys=list(market_data.keys()),
                )
                return True
            else:
                logger.error("Adapter manager market data retrieval failed")
                return False

        except Exception as e:
            logger.error("Adapter manager integration test failed", error=str(e))
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("Starting integration tests...")

        test_results = {}

        # 测试列表
        tests = [
            ("tacore_service_connection", self.test_tacore_service_connection),
            ("market_scan", self.test_market_scan),
            ("symbol_analysis", self.test_symbol_analysis),
            ("market_data_retrieval", self.test_market_data_retrieval),
            ("market_overview", self.test_market_overview),
            ("adapter_manager_integration", self.test_adapter_manager_integration),
        ]

        for test_name, test_func in tests:
            try:
                logger.info(f"Running test: {test_name}")

                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()

                test_results[test_name] = result

                if result:
                    logger.info(f"✓ Test {test_name} PASSED")
                else:
                    logger.error(f"✗ Test {test_name} FAILED")

            except Exception as e:
                logger.error(f"✗ Test {test_name} ERROR", error=str(e))
                test_results[test_name] = False

            # 短暂延迟
            await asyncio.sleep(1)

        return test_results

    def cleanup(self):
        """清理资源"""
        try:
            if self.adapter_manager:
                self.adapter_manager.shutdown()
            logger.info("Integration test cleanup completed")
        except Exception as e:
            logger.error("Cleanup failed", error=str(e))


async def main():
    """主函数"""
    tester = IntegrationTester()

    try:
        # 设置测试环境
        if not tester.setup():
            logger.error("Failed to setup test environment")
            return False

        # 运行所有测试
        test_results = await tester.run_all_tests()

        # 统计结果
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        failed_tests = total_tests - passed_tests

        logger.info(
            "Integration test summary",
            total=total_tests,
            passed=passed_tests,
            failed=failed_tests,
            success_rate=f"{(passed_tests/total_tests)*100:.1f}%",
        )

        # 显示详细结果
        for test_name, result in test_results.items():
            status = "PASSED" if result else "FAILED"
            logger.info(f"  {test_name}: {status}")

        return failed_tests == 0

    except Exception as e:
        logger.error("Integration test failed", error=str(e))
        return False

    finally:
        tester.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Integration Test for TACoreService")
    parser.add_argument(
        "--config", default="scanner/config/config.yaml", help="Configuration file path"
    )

    args = parser.parse_args()

    # 运行测试
    success = asyncio.run(main())

    if success:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed")
        sys.exit(1)
