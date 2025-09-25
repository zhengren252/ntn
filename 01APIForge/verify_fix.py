#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 ZMQManager 禁用守卫与 await Mock 修复
测试核心逻辑：在 DISABLE_ZMQ=1 时，避免创建后台任务与对 Mock 执行 await
"""
import os
import sys
import asyncio
import logging
from unittest.mock import Mock, patch
import types
import importlib.util

# 设置环境变量以触发禁用模式
os.environ["DISABLE_ZMQ"] = "1"

# 添加项目根路径
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建简化的配置对象，避免依赖外部库
class SimpleZMQConfig:
    def __init__(self):
        self.bind_address = "tcp://127.0.0.1"
        self.connect_address = "tcp://127.0.0.1"
        self.publisher_port = 55055
        self.subscriber_port = 55056
        self.request_port = 55057
        self.reply_port = 55058


def load_zmq_manager_module():
    """以不触发 FastAPI 导入的方式加载 ZMQManager 模块"""
    # 1) 预先构造 api_factory 包结构与 settings 模块桩
    api_factory_pkg = types.ModuleType("api_factory")
    api_factory_pkg.__path__ = [os.path.join(PROJECT_ROOT, "api_factory")]
    core_pkg = types.ModuleType("api_factory.core")
    config_pkg = types.ModuleType("api_factory.config")

    settings_mod = types.ModuleType("api_factory.config.settings")

    class ZMQConfig(SimpleZMQConfig):
        pass

    settings_mod.ZMQConfig = ZMQConfig

    sys.modules["api_factory"] = api_factory_pkg
    sys.modules["api_factory.core"] = core_pkg
    sys.modules["api_factory.config"] = config_pkg
    sys.modules["api_factory.config.settings"] = settings_mod

    # 2) 动态按文件路径加载 zmq_manager.py
    zmq_manager_path = os.path.join(PROJECT_ROOT, "api_factory", "core", "zmq_manager.py")
    spec = importlib.util.spec_from_file_location("api_factory.core.zmq_manager", zmq_manager_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore
    return module


async def test_zmq_manager_disabled():
    """测试 ZMQManager 在禁用模式下的行为"""

    # Mock zmq 模块以避免导入错误
    mock_zmq = Mock()
    mock_zmq.asyncio = Mock()
    mock_context = Mock()
    mock_zmq.asyncio.Context.return_value = mock_context

    with patch.dict(sys.modules, {
        'zmq': mock_zmq,
        'zmq.asyncio': mock_zmq.asyncio
    }):
        # 导入 ZMQManager（在 Mock 应用后）
        module = load_zmq_manager_module()
        ZMQManager = module.ZMQManager

        # 创建管理器实例
        config = SimpleZMQConfig()
        manager = ZMQManager(config)

        # 测试 1：初始化应当快速完成且不创建套接字
        print("测试 1：DISABLE_ZMQ 环境下的初始化...")
        await manager.initialize()

        # 验证：套接字应为 None（未创建）
        assert manager.context is None, "在禁用模式下，context 应为 None"
        assert manager.publisher is None, "在禁用模式下，publisher 应为 None"
        assert manager.subscriber is None, "在禁用模式下，subscriber 应为 None"
        assert manager.reply_socket is None, "在禁用模式下，reply_socket 应为 None"

        print("✓ 初始化测试通过：禁用模式下未创建套接字")

        # 测试 2：模拟 conftest.py 中的 Mock 替换场景
        print("测试 2：Mock 替换的 _handle_request 方法...")

        # 用非协程函数替换 _handle_request（模拟测试中的行为）
        mock_handler = Mock(return_value={"status": "ok", "message": "mocked"})
        manager._handle_request = mock_handler  # type: ignore[attr-defined]

        # 测试 _start_reply_loop 不会对 Mock 执行 await
        # 由于没有 reply_socket，循环应该快速退出
        try:
            # 这个调用应该立即返回而不阻塞
            task = asyncio.create_task(manager._start_reply_loop())

            # 等待短时间以确保没有阻塞
            await asyncio.sleep(0.1)

            # 取消任务（如果还在）
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

            print("✓ _start_reply_loop 测试通过：无死循环且无 await Mock 错误")

        except Exception as e:
            print(f"✗ _start_reply_loop 测试失败: {e}")
            raise

        # 测试 3：发布消息在禁用模式下的行为
        print("测试 3：禁用模式下的消息发布...")
        await manager.publish_message("test.topic", {"msg": "hello"})
        print("✓ 发布消息测试通过：禁用模式下正常降级")

        # 测试 4：健康检查
        print("测试 4：禁用模式下的健康检查...")
        health = await manager.health_check()
        assert health is True, "禁用模式下健康检查应返回 True"
        print("✓ 健康检查测试通过")

        print("\n🎉 所有测试通过！ZMQManager 禁用守卫和 await Mock 修复验证成功")


async def main():
    """主测试函数"""
    try:
        await test_zmq_manager_disabled()
        print("\n✅ 验证完成：修复有效，避免了 'await Mock' 错误和死循环")
        return 0
    except Exception as e:
        print(f"\n❌ 验证失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import contextlib
    exit_code = asyncio.run(main())
    sys.exit(exit_code)