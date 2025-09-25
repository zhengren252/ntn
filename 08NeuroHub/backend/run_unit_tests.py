#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试运行脚本

直接运行单元测试，避免pytest的导入问题
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# 添加当前目录到Python路径
sys.path.insert(0, os.getcwd())

def run_decision_engine_tests():
    """运行决策引擎测试"""
    print("=== 运行决策引擎单元测试 ===")
    
    try:
        from tests.unit.test_decision_engine import TestDecisionEngine
        
        test_instance = TestDecisionEngine()
        
        # 运行异步测试
        async def run_async_tests():
            # 创建mock对象
            from unittest.mock import AsyncMock
            mock_redis_manager = AsyncMock()
            mock_zmq_manager = AsyncMock()
            
            # 创建决策引擎实例
            from app.core.decision_engine import DecisionEngine
            decision_engine = DecisionEngine()
            decision_engine.redis_manager = mock_redis_manager
            decision_engine.zmq_manager = mock_zmq_manager
            
            await test_instance.test_unit_decision_01_switch_aggressive_mode(decision_engine, mock_redis_manager, mock_zmq_manager)
            print("✅ UNIT-DECISION-01: 决策引擎切换进攻模式测试通过")
            
            # 重置mock对象
            mock_redis_manager.reset_mock()
            mock_zmq_manager.reset_mock()
            
            await test_instance.test_unit_decision_02_emergency_shutdown(decision_engine, mock_redis_manager, mock_zmq_manager)
            print("✅ UNIT-DECISION-02: 决策引擎紧急熔断测试通过")
            
            # 重置mock对象
            mock_redis_manager.reset_mock()
            mock_zmq_manager.reset_mock()
            
            await test_instance.test_market_analysis_strong_bull(decision_engine, mock_redis_manager)
            await test_instance.test_market_analysis_strong_bear(decision_engine, mock_redis_manager)
            await test_instance.test_market_analysis_no_data(decision_engine, mock_redis_manager)
            
            # 重置mock对象
            mock_redis_manager.reset_mock()
            mock_zmq_manager.reset_mock()
            
            await test_instance.test_risk_alert_high_level(decision_engine, mock_redis_manager, mock_zmq_manager)
            
            # 重置mock对象
            mock_redis_manager.reset_mock()
            mock_zmq_manager.reset_mock()
            
            await test_instance.test_risk_alert_low_level(decision_engine, mock_redis_manager, mock_zmq_manager)
        
        # 运行异步测试
        asyncio.run(run_async_tests())
        
        print("✅ 决策引擎单元测试全部通过！")
        return True
        
    except Exception as e:
        print(f"❌ 决策引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_api_tests():
    """运行API测试"""
    print("\n=== 运行API单元测试 ===")
    
    try:
        from tests.unit.test_api import TestAPIEndpoints
        
        test_instance = TestAPIEndpoints()
        
        # Mock get_zmq_manager
        with patch('app.api.routes.get_zmq_manager') as mock_get_zmq_manager:
            mock_zmq_manager = AsyncMock()
            mock_get_zmq_manager.return_value = mock_zmq_manager
            
            test_instance.test_unit_api_01_invalid_command_type()
            test_instance.test_valid_command_execution()
            test_instance.test_command_validation_edge_cases()
        
        print("✅ API单元测试全部通过！")
        return True
        
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 开始运行总控模块单元测试")
    print("=" * 50)
    
    # 运行测试
    decision_success = run_decision_engine_tests()
    api_success = run_api_tests()
    
    print("\n" + "=" * 50)
    
    if decision_success and api_success:
        print("🎉 所有单元测试通过！")
        print("\n测试覆盖范围：")
        print("✅ UNIT-DECISION-01: 决策引擎切换进攻模式")
        print("✅ UNIT-DECISION-02: 决策引擎紧急熔断")
        print("✅ UNIT-API-01: API无效控制指令")
        print("✅ 额外的边界情况和错误处理测试")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)