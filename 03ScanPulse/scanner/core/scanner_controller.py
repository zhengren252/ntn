# 扫描器控制器
# 负责管理扫描器的生命周期和协调各个组件

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from ..adapters import AdapterManager
from ..communication import CommunicationManager
from ..config import EnvironmentManager
from .scanner_module import ScannerModule, ScannerStatus

# from ..rules import RuleEngine  # 暂时注释，待实现

logger = structlog.get_logger(__name__)


class ScannerController:
    """扫描器控制器 - 统一管理扫描器生命周期"""

    def __init__(
        self, config_path: Optional[str] = None, environment: str = "development"
    ):
        self.environment = environment
        self.config_path = config_path or self._get_default_config_path()

        # 核心组件
        self.config_manager: Optional[EnvironmentManager] = None
        self.adapter_manager: Optional[AdapterManager] = None
        self.communication_manager: Optional[CommunicationManager] = None
        self.scanner_module: Optional[ScannerModule] = None

        # 控制器状态
        self.is_initialized = False
        self.is_running = False
        self.startup_time = None

        # 统计信息
        self.stats = {
            "initialization_time": None,
            "startup_time": None,
            "total_uptime": 0,
            "restart_count": 0,
            "error_count": 0,
        }

        logger.info(
            "ScannerController created",
            environment=environment,
            config_path=self.config_path,
        )

    def _get_default_config_path(self) -> str:
        """获取默认配置路径

        Returns:
            配置文件路径
        """
        # 获取项目根目录
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # 回到项目根目录
        config_dir = project_root / "config"

        return str(config_dir)

    async def initialize(self) -> bool:
        """初始化所有组件

        Returns:
            是否初始化成功
        """
        try:
            if self.is_initialized:
                logger.warning("ScannerController already initialized")
                return True

            start_time = datetime.now()
            logger.info("Initializing ScannerController")

            # 1. 初始化配置管理器
            if not await self._initialize_config_manager():
                return False

            # 2. 初始化适配器管理器
            if not await self._initialize_adapter_manager():
                return False

            # 3. 初始化通信管理器
            if not await self._initialize_communication_manager():
                return False

            # 4. 初始化扫描器模块
            if not await self._initialize_scanner_module():
                return False

            # 5. 设置信号处理
            self._setup_signal_handlers()

            # 6. 注册回调函数
            self._register_callbacks()

            self.is_initialized = True
            initialization_time = (datetime.now() - start_time).total_seconds()
            self.stats["initialization_time"] = initialization_time

            logger.info(
                "ScannerController initialized successfully",
                initialization_time=initialization_time,
            )

            return True

        except Exception as e:
            logger.error("Failed to initialize ScannerController", error=str(e))
            self.stats["error_count"] += 1
            return False

    async def _initialize_config_manager(self) -> bool:
        """初始化配置管理器

        Returns:
            是否初始化成功
        """
        try:
            logger.info("Initializing ConfigManager")

            self.config_manager = EnvironmentManager(
                config_dir=self.config_path, environment=self.environment
            )

            # 加载配置
            if not self.config_manager.load_config():
                logger.error("Failed to load configuration")
                return False

            logger.info("ConfigManager initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize ConfigManager", error=str(e))
            return False

    async def _initialize_adapter_manager(self) -> bool:
        """初始化适配器管理器

        Returns:
            是否初始化成功
        """
        try:
            logger.info("Initializing AdapterManager")

            adapter_config = self.config_manager.get_config("adapters")
            self.adapter_manager = AdapterManager(adapter_config)

            # 初始化适配器
            if not self.adapter_manager.initialize():
                logger.error("Failed to initialize adapters")
                return False

            logger.info("AdapterManager initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize AdapterManager", error=str(e))
            return False

    async def _initialize_communication_manager(self) -> bool:
        """初始化通信管理器

        Returns:
            是否初始化成功
        """
        try:
            logger.info("Initializing CommunicationManager")

            comm_config = {
                "zmq": self.config_manager.get_config("zmq"),
                "redis": self.config_manager.get_config("redis"),
            }

            self.communication_manager = CommunicationManager(comm_config)

            # 启动通信管理器
            if not await asyncio.to_thread(self.communication_manager.start):
                logger.error("Failed to start CommunicationManager")
                return False

            logger.info("CommunicationManager initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize CommunicationManager", error=str(e))
            return False

    async def _initialize_scanner_module(self) -> bool:
        """初始化扫描器模块

        Returns:
            是否初始化成功
        """
        try:
            logger.info("Initializing ScannerModule")

            self.scanner_module = ScannerModule(
                config_manager=self.config_manager,
                adapter_manager=self.adapter_manager,
                communication_manager=self.communication_manager,
            )

            logger.info("ScannerModule initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize ScannerModule", error=str(e))
            return False

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        try:
            # 设置优雅关闭信号处理
            if sys.platform != "win32":
                signal.signal(signal.SIGTERM, self._signal_handler)
                signal.signal(signal.SIGINT, self._signal_handler)
            else:
                # Windows下的信号处理
                signal.signal(signal.SIGINT, self._signal_handler)

            logger.info("Signal handlers setup completed")

        except Exception as e:
            logger.warning("Failed to setup signal handlers", error=str(e))

    def _signal_handler(self, signum, frame):
        """信号处理函数

        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        logger.info("Received shutdown signal", signal=signum)

        # 创建异步任务来处理关闭
        if self.is_running:
            asyncio.create_task(self.shutdown())

    def _register_callbacks(self) -> None:
        """注册回调函数"""
        try:
            if not self.scanner_module:
                return

            # 注册扫描事件回调
            self.scanner_module.add_callback("on_scan_start", self._on_scan_start)
            self.scanner_module.add_callback("on_scan_complete", self._on_scan_complete)
            self.scanner_module.add_callback(
                "on_opportunity_found", self._on_opportunity_found
            )
            self.scanner_module.add_callback("on_error", self._on_scanner_error)

            logger.info("Callbacks registered successfully")

        except Exception as e:
            logger.error("Failed to register callbacks", error=str(e))

    def _on_scan_start(self, data: Dict[str, Any]) -> None:
        """扫描开始回调

        Args:
            data: 扫描开始数据
        """
        logger.debug("Scan started", timestamp=data.get("timestamp"))

    def _on_scan_complete(self, data: Dict[str, Any]) -> None:
        """扫描完成回调

        Args:
            data: 扫描完成数据
        """
        logger.info(
            "Scan completed",
            duration=data.get("duration"),
            symbols_scanned=data.get("symbols_scanned"),
            opportunities_found=data.get("opportunities_found"),
        )

    def _on_opportunity_found(self, data: Dict[str, Any]) -> None:
        """发现机会回调

        Args:
            data: 机会数据
        """
        logger.info(
            "Opportunity found",
            symbol=data.get("symbol"),
            score=data.get("overall_score"),
            confidence=data.get("confidence"),
            recommendation=data.get("recommendation"),
        )

    def _on_scanner_error(self, data: Dict[str, Any]) -> None:
        """扫描器错误回调

        Args:
            data: 错误数据
        """
        logger.error("Scanner error occurred", error=data.get("error"))
        self.stats["error_count"] += 1

    async def start(self) -> bool:
        """启动扫描器

        Returns:
            是否启动成功
        """
        try:
            if not self.is_initialized:
                logger.error("ScannerController not initialized")
                return False

            if self.is_running:
                logger.warning("ScannerController already running")
                return True

            logger.info("Starting ScannerController")
            start_time = datetime.now()

            # 启动扫描器模块
            if not self.scanner_module.start():
                logger.error("Failed to start ScannerModule")
                return False

            self.is_running = True
            self.startup_time = start_time
            self.stats["startup_time"] = start_time.isoformat()

            logger.info("ScannerController started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start ScannerController", error=str(e))
            self.stats["error_count"] += 1
            return False

    async def stop(self) -> None:
        """停止扫描器"""
        try:
            if not self.is_running:
                logger.warning("ScannerController not running")
                return

            logger.info("Stopping ScannerController")

            # 停止扫描器模块
            if self.scanner_module:
                self.scanner_module.stop()

            self.is_running = False

            # 更新运行时间统计
            if self.startup_time:
                uptime = (datetime.now() - self.startup_time).total_seconds()
                self.stats["total_uptime"] += uptime

            logger.info("ScannerController stopped")

        except Exception as e:
            logger.error("Error stopping ScannerController", error=str(e))

    async def restart(self) -> bool:
        """重启扫描器

        Returns:
            是否重启成功
        """
        try:
            logger.info("Restarting ScannerController")

            # 停止
            await self.stop()

            # 等待一段时间
            await asyncio.sleep(2)

            # 重新连接失败的适配器
            if self.adapter_manager:
                reconnected = self.adapter_manager.reconnect_failed_adapters()
                logger.info("Reconnected adapters", count=reconnected)

            # 启动
            success = await self.start()

            if success:
                self.stats["restart_count"] += 1
                logger.info("ScannerController restarted successfully")
            else:
                logger.error("Failed to restart ScannerController")

            return success

        except Exception as e:
            logger.error("Error restarting ScannerController", error=str(e))
            self.stats["error_count"] += 1
            return False

    async def shutdown(self) -> None:
        """关闭扫描器（完全清理）"""
        try:
            logger.info("Shutting down ScannerController")

            # 停止扫描器
            await self.stop()

            # 关闭通信管理器
            if self.communication_manager:
                await asyncio.to_thread(self.communication_manager.stop)
                await asyncio.to_thread(self.communication_manager.close)

            # 关闭适配器管理器
            if self.adapter_manager:
                self.adapter_manager.shutdown()

            # 重置状态
            self.is_initialized = False
            self.is_running = False

            logger.info("ScannerController shutdown completed")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

    def pause(self) -> None:
        """暂停扫描器"""
        if self.scanner_module:
            self.scanner_module.pause()
            logger.info("ScannerController paused")
        else:
            logger.warning("ScannerModule not available")

    def resume(self) -> None:
        """恢复扫描器"""
        if self.scanner_module:
            self.scanner_module.resume()
            logger.info("ScannerController resumed")
        else:
            logger.warning("ScannerModule not available")

    def get_status(self) -> Dict[str, Any]:
        """获取控制器状态

        Returns:
            状态信息字典
        """
        status = {
            "controller": {
                "is_initialized": self.is_initialized,
                "is_running": self.is_running,
                "environment": self.environment,
                "config_path": self.config_path,
                "stats": self.stats.copy(),
            }
        }

        # 添加各组件状态
        if self.scanner_module:
            status["scanner"] = self.scanner_module.get_status()

        if self.adapter_manager:
            status["adapters"] = self.adapter_manager.health_check()

        if self.communication_manager:
            status["communication"] = self.communication_manager.get_stats()

        return status

    def get_health(self) -> Dict[str, Any]:
        """获取健康状态

        Returns:
            健康状态字典
        """
        try:
            health = {
                "overall_status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {},
            }

            # 检查控制器状态
            if not self.is_initialized or not self.is_running:
                health["overall_status"] = "unhealthy"
                health["components"]["controller"] = "not_running"
            else:
                health["components"]["controller"] = "healthy"

            # 检查适配器健康状态
            if self.adapter_manager:
                adapter_health = self.adapter_manager.health_check()
                health["components"]["adapters"] = adapter_health["overall_status"]
                if adapter_health["overall_status"] != "healthy":
                    health["overall_status"] = "degraded"
            else:
                health["components"]["adapters"] = "not_available"
                health["overall_status"] = "unhealthy"

            # 检查扫描器状态
            if self.scanner_module:
                scanner_status = self.scanner_module.get_status()
                if scanner_status["status"] == ScannerStatus.ERROR.value:
                    health["components"]["scanner"] = "error"
                    health["overall_status"] = "unhealthy"
                elif scanner_status["is_running"]:
                    health["components"]["scanner"] = "healthy"
                else:
                    health["components"]["scanner"] = "stopped"
            else:
                health["components"]["scanner"] = "not_available"
                health["overall_status"] = "unhealthy"

            return health

        except Exception as e:
            logger.error("Error getting health status", error=str(e))
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def run_forever(self) -> None:
        """运行扫描器直到收到停止信号"""
        try:
            logger.info("Starting ScannerController run loop")

            # 初始化
            if not await self.initialize():
                logger.error("Initialization failed")
                return

            # 启动
            if not await self.start():
                logger.error("Startup failed")
                return

            # 运行循环
            while self.is_running:
                try:
                    # 定期健康检查
                    health = self.get_health()
                    if health["overall_status"] == "unhealthy":
                        logger.warning("System unhealthy, attempting restart")
                        if not await self.restart():
                            logger.error("Restart failed, shutting down")
                            break

                    # 等待
                    await asyncio.sleep(30)  # 30秒检查一次

                except asyncio.CancelledError:
                    logger.info("Run loop cancelled")
                    break
                except Exception as e:
                    logger.error("Error in run loop", error=str(e))
                    await asyncio.sleep(10)  # 错误后等待10秒

        except Exception as e:
            logger.error("Fatal error in run loop", error=str(e))
        finally:
            # 确保清理
            await self.shutdown()
            logger.info("ScannerController run loop ended")
