# 扫描器模组主程序入口
# 整合所有模块，提供统一的启动接口
# 严格遵循微服务架构和核心设计理念

import asyncio
import signal
import sys
from typing import Any, Dict, Optional

from scanner.adapters.trading_agents_cn_adapter import (
    TACoreServiceAgent,
    TACoreServiceClient,
)
from scanner.adapters.adapter_manager import AdapterManager
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.config.env_manager import get_env_manager
from scanner.detectors.black_horse_detector import BlackHorseDetector
from scanner.detectors.potential_finder import PotentialFinder
from scanner.engines.three_high_engine import ThreeHighEngine
from scanner.health_check import get_health_checker
from scanner.utils.logger import (
    get_error_handler,
    get_logger,
    setup_logging,
)
from scanner.web.app import create_app, run_web_app

# 项目根目录路径管理 - 避免sys.modules警告
# 使用相对导入替代sys.path操作


class ScannerApplication:
    """扫描器应用程序主类"""

    def __init__(self):
        # 环境管理器
        self.env_manager = get_env_manager()

        # 初始化日志系统
        logging_config = self.env_manager.get_logging_config()
        setup_logging(logging_config)

        self.logger = get_logger(__name__)
        self.error_handler = get_error_handler()

        self.logger.info("ScannerApplication constructor started")

        # 组件实例
        self.redis_client: Optional[RedisClient] = None
        self.zmq_client: Optional[ScannerZMQClient] = None
        self.trading_adapter: Optional[TACoreServiceAgent] = None
        self.adapter_manager: Optional[AdapterManager] = None
        self.health_checker = get_health_checker()

        # 扫描引擎
        self.three_high_engine: Optional[ThreeHighEngine] = None
        self.black_horse_detector: Optional[BlackHorseDetector] = None
        self.potential_finder: Optional[PotentialFinder] = None

        # Web应用
        self.web_app = None
        self.web_server_task = None

        # 运行状态
        self.is_running = False
        self.shutdown_event = asyncio.Event()

        self.logger.info(
            "Scanner application initialized",
            environment=self.env_manager.get_environment().value,
        )

    async def initialize_components(self) -> bool:
        """初始化所有组件

        Returns:
            是否初始化成功
        """
        try:
            self.logger.info("Initializing components")

            # 初始化Redis客户端（失败不阻断启动，允许降级模式）
            redis_config = self.env_manager.get_redis_config()
            self.redis_client = RedisClient(redis_config)
            try:
                if not self.redis_client.connect():
                    self.logger.warning(
                        "Redis connect() returned False, starting in degraded mode (no Redis)"
                    )
                    self.redis_client = None
                else:
                    self.logger.info("Redis client initialized")
            except Exception as e:
                self.logger.warning(
                    f"Redis connection error during init: {e}, starting in degraded mode (no Redis)"
                )
                self.redis_client = None

            # 初始化ZeroMQ客户端（独立于Redis）
            zmq_config = self.env_manager.get_zmq_config()
            self.zmq_client = ScannerZMQClient(
                req_host=zmq_config.get("request", {}).get("host", "localhost"),
                req_port=zmq_config.get("request", {}).get("port", 5555),
                pub_host=zmq_config.get("publisher", {}).get("host", "localhost"),
                pub_port=zmq_config.get("publisher", {}).get("port", 5556)
            )
            self.zmq_client.connect()
            self.logger.info("ZeroMQ client initialized")

            # 初始化TACoreService适配器
            tacore_config = self.env_manager.get_config("tacore_service", {})
            tacore_client = TACoreServiceClient(
                server_address=tacore_config.get(
                    "server_address", "tcp://localhost:5555"
                ),
                timeout=tacore_config.get("timeout", 15000),
            )
            try:
                if tacore_client.connect():
                    self.logger.info("TACoreService connected successfully")
                else:
                    self.logger.warning(
                        "TACoreService connection failed, will retry later"
                    )
            except Exception as e:
                self.logger.warning(
                    f"TACoreService connection error: {e}, will retry later"
                )

            self.trading_adapter = TACoreServiceAgent(tacore_client)
            self.logger.info("TACoreService adapter initialized")

            # 初始化适配器管理器
            adapters_config = self.env_manager.get_config("adapters", {})
            self.adapter_manager = AdapterManager(adapters_config)
            if self.adapter_manager.initialize():
                self.logger.info("Adapter manager initialized successfully")
            else:
                self.logger.warning(
                    "Adapter manager initialization failed, continuing without some adapters"
                )

            # 初始化扫描引擎（需要Redis，若无则跳过并记录）
            scanner_config = self.env_manager.get_scanner_config()

            # 三高规则引擎
            if self.redis_client and scanner_config["rules"]["three_high"]["enabled"]:
                self.three_high_engine = ThreeHighEngine(
                    self.redis_client, scanner_config["rules"]["three_high"]
                )
                self.logger.info("Three-high engine initialized")
            elif scanner_config["rules"]["three_high"]["enabled"]:
                self.logger.warning(
                    "Three-high engine skipped due to degraded mode (no Redis)"
                )

            # 黑马监测器
            if self.redis_client and scanner_config["rules"]["black_horse"]["enabled"]:
                self.black_horse_detector = BlackHorseDetector(
                    self.redis_client, scanner_config["rules"]["black_horse"]
                )
                self.logger.info("Black horse detector initialized")
            elif scanner_config["rules"]["black_horse"]["enabled"]:
                self.logger.warning(
                    "Black horse detector skipped due to degraded mode (no Redis)"
                )

            # 潜力挖掘器
            if self.redis_client and scanner_config["rules"]["potential_finder"]["enabled"]:
                self.potential_finder = PotentialFinder(
                    self.redis_client, scanner_config["rules"]["potential_finder"]
                )
                self.logger.info("Potential finder initialized")
            elif scanner_config["rules"]["potential_finder"]["enabled"]:
                self.logger.warning(
                    "Potential finder skipped due to degraded mode (no Redis)"
                )

            # 设置新闻事件订阅（用于黑马监测器）
            await self._setup_news_subscription()

            self.logger.info("All components initialized (degraded mode: %s)", str(self.redis_client is None))
            return True

        except Exception as e:
            self.error_handler.handle_exception(
                e, context={"operation": "initialize_components"}, reraise=True
            )
            return False

    async def _handle_scan_result(self, results: list) -> None:
        """处理扫描结果回调"""
        try:
            self.logger.info("Processing scan results", count=len(results))

            for result in results:
                symbol = result.get("symbol")
                if not symbol:
                    continue

                # 存储扫描结果到Redis
            if self.redis_client:
                self.redis_client.set_scan_result(symbol, result)

            # 通过ZeroMQ发布结果
            if self.zmq_client:
                await self.zmq_client.publish_scan_result(result)

            # 应用扫描引擎
            await self._apply_scan_engines(symbol, result)

            self.logger.info(
                f"Scan result handled: {result['symbol']} - " f"{result['type']}"
            )

            self.logger.debug("Scan results processed successfully")

        except Exception as e:
            self.error_handler.handle_exception(
                e,
                context={
                    "operation": "handle_scan_result",
                    "result_count": len(results),
                },
            )

    async def _handle_adapter_error(self, error_type: str, error_message: str) -> None:
        """处理适配器错误回调"""
        self.logger.error(
            "TACoreService adapter error",
            error_type=error_type,
            error_message=error_message,
        )

        # 通过ZeroMQ发布错误状态
        if self.zmq_client:
            await self.zmq_client.publish_status_update(
                {
                    "type": "error",
                    "component": "trading_adapter",
                    "error_type": error_type,
                    "error_message": error_message,
                }
            )

    async def _apply_scan_engines(
        self, symbol: str, market_data: Dict[str, Any]
    ) -> None:
        """应用扫描引擎"""
        try:
            # 三高规则引擎
            if self.three_high_engine:
                three_high_result = await self.three_high_engine.analyze(
                    symbol, market_data
                )
                if three_high_result.get("triggered"):
                    self.logger.info(
                        "Three-high rule triggered",
                        symbol=symbol,
                        score=three_high_result.get("score"),
                    )

                    # 发布三高信号
                    if self.zmq_client:
                        await self.zmq_client.publish_scan_result(
                            {
                                "type": "three_high_signal",
                                "symbol": symbol,
                                "result": three_high_result,
                            }
                        )

            # 黑马监测器
            if self.black_horse_detector:
                black_horse_result = await self.black_horse_detector.detect(
                    symbol, market_data
                )
                if black_horse_result.get("detected"):
                    self.logger.info(
                        "Black horse detected",
                        symbol=symbol,
                        confidence=black_horse_result.get("confidence"),
                    )

                    # 发布黑马信号
                    if self.zmq_client:
                        await self.zmq_client.publish_scan_result(
                            {
                                "type": "black_horse_signal",
                                "symbol": symbol,
                                "result": black_horse_result,
                            }
                        )

            # 潜力挖掘器
            if self.potential_finder:
                potential_result = await self.potential_finder.find_potential(
                    symbol, market_data
                )
                if potential_result.get("has_potential"):
                    self.logger.info(
                        "Potential found",
                        symbol=symbol,
                        potential_score=potential_result.get("potential_score"),
                    )

                    # 发布潜力信号
                    if self.zmq_client:
                        await self.zmq_client.publish_scan_result(
                            {
                                "type": "potential_signal",
                                "symbol": symbol,
                                "result": potential_result,
                            }
                        )

        except Exception as e:
            self.error_handler.handle_exception(
                e, context={"operation": "apply_scan_engines", "symbol": symbol}
            )

    async def start_scanning(self) -> None:
        """开始扫描循环"""
        scanner_config = self.env_manager.get_scanner_config()
        scan_interval = scanner_config.get("scan_interval", 60)

        self.logger.info("Starting scan loop", interval=scan_interval)

        while self.is_running and not self.shutdown_event.is_set():
            try:
                # 获取要扫描的交易对列表
                symbols = await self._get_scan_symbols()

                if symbols:
                    # 优先使用APIForge获取市场数据，然后使用TACoreService进行分析
                    await self._scan_with_integrated_adapters(symbols)

                # 等待下次扫描
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=scan_interval
                    )
                    break  # 收到关闭信号
                except asyncio.TimeoutError:
                    continue  # 超时，继续下次扫描

            except Exception as e:
                self.error_handler.handle_exception(
                    e, context={"operation": "scan_loop"}
                )
                await asyncio.sleep(5)  # 错误时短暂等待

    async def _setup_news_subscription(self) -> None:
        """设置新闻事件订阅，用于黑马监测器"""
        try:
            # 这里应该设置对crawler.news主题的订阅
            # 由于当前ZMQ客户端主要用于请求-响应，新闻订阅通过Redis实现
            # 黑马监测器会从Redis中获取由DataSpider缓存的新闻事件
            self.logger.info("News subscription setup completed (via Redis cache)")
        except Exception as e:
            self.logger.error(f"Failed to setup news subscription: {e}")

    async def _scan_with_integrated_adapters(self, symbols: list) -> None:
        """使用集成适配器进行扫描
        
        Args:
            symbols: 要扫描的交易对列表
        """
        try:
            results = []
            
            # 优先使用APIForge获取市场数据
            if self.adapter_manager:
                api_factory = self.adapter_manager.get_api_factory_adapter()
                if api_factory and api_factory.is_connected():
                    self.logger.debug("Using APIForge for market data")
                    for symbol in symbols:
                        try:
                            market_data = api_factory.get_market_data(symbol)
                            if market_data:
                                # 使用TACoreService进行分析
                                if self.trading_adapter:
                                    analysis = await self.trading_adapter.analyze_symbol(
                                        symbol, market_data
                                    )
                                    if analysis:
                                        result = {
                                            **market_data, **analysis, "symbol": symbol
                                        }
                                        results.append(result)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to get data for {symbol} from APIForge: {e}"
                            )
                
            # 如果APIForge不可用，回退到TACoreService
            if not results and self.trading_adapter:
                self.logger.debug("Falling back to TACoreService for market scanning")
                results = await self.trading_adapter.scan_symbols(symbols)
            
            # 处理扫描结果
            if results:
                await self._handle_scan_result(results)
                
        except Exception as e:
            self.logger.error(f"Error in integrated scanning: {e}")

    async def _get_scan_symbols(self) -> list:
        """获取要扫描的交易对列表"""
        # 这里可以从配置、API或其他数据源获取交易对列表
        # 目前使用默认列表
        return [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "ADAUSDT",
            "DOTUSDT",
            "LINKUSDT",
            "LTCUSDT",
            "BCHUSDT",
            "XLMUSDT",
            "EOSUSDT",
        ]

    async def _start_web_server(self) -> None:
        """启动Web服务器"""
        try:
            # 通过环境管理器分别获取 host/port，确保环境变量覆盖（WEB_HOST/WEB_PORT）生效
            host = self.env_manager.get_config("web.host", "0.0.0.0")
            port = int(self.env_manager.get_config("web.port", 8000))

            self.web_app = create_app(
                redis_client=self.redis_client,
                zmq_client=self.zmq_client,
                health_checker=self.health_checker,
            )

            self.logger.info(f"Starting web server on {host}:{port}")

            await run_web_app(self.web_app, host=host, port=port)

        except Exception as e:
            self.error_handler.handle_exception(
                e, context={"operation": "start_web_server"}
            )

    async def run(self) -> None:
        """运行应用程序"""
        try:
            self.logger.info("Starting scanner application")

            # 初始化组件
            if not await self.initialize_components():
                raise RuntimeError("Failed to initialize components")

            # 验证配置
            validation_result = self.env_manager.validate_config()
            if not validation_result["valid"]:
                self.logger.error(
                    "Configuration validation failed",
                    errors=validation_result["errors"],
                )
                return

            if validation_result["warnings"]:
                self.logger.warning(
                    "Configuration warnings", warnings=validation_result["warnings"]
                )

            self.is_running = True

            # 启动健康监控
            health_task = asyncio.create_task(self.health_checker.start_monitoring())

            # 启动扫描循环
            scan_task = asyncio.create_task(self.start_scanning())

            # 启动Web服务器
            web_task = asyncio.create_task(self._start_web_server())

            self.logger.info("Scanner application started successfully")

            # 等待任务完成或关闭信号
            await asyncio.gather(
                health_task, scan_task, web_task, return_exceptions=True
            )

        except Exception as e:
            self.error_handler.handle_exception(
                e, context={"operation": "run_application"}
            )
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """关闭应用程序"""
        try:
            self.logger.info("Shutting down scanner application")

            self.is_running = False
            self.shutdown_event.set()

            # 停止健康监控
            self.health_checker.stop_monitoring()

            # 关闭TradingAgents-CN适配器
            if self.trading_adapter:
                await self.trading_adapter.disconnect()

            # 关闭ZeroMQ客户端
            if self.zmq_client:
                self.zmq_client.stop()

            # 关闭Redis客户端
            if self.redis_client:
                self.redis_client.disconnect()

            # 停止Web服务器
            if self.web_server_task:
                self.web_server_task.cancel()
                try:
                    await self.web_server_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Scanner application shutdown completed")

        except Exception as e:
            self.error_handler.handle_exception(e, context={"operation": "shutdown"})


def setup_signal_handlers(app: ScannerApplication) -> None:
    """设置信号处理器"""

    def signal_handler(signum, frame):
        logger = get_logger(__name__)
        logger.info(f"Received signal {signum}, initiating shutdown")

        # 获取当前事件循环并安排关闭任务
        try:
            loop = asyncio.get_running_loop()
            # 创建关闭任务
            loop.create_task(app.shutdown())
        except RuntimeError:
            # 如果没有运行的事件循环，直接退出
            logger.warning("No running event loop found, exiting immediately")
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """主函数"""
    app = ScannerApplication()

    try:
        # 设置信号处理器（在应用启动后）
        setup_signal_handlers(app)

        await app.run()
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger = get_logger(__name__)
        error_handler = get_error_handler()
        error_handler.handle_exception(e, context={"operation": "main"}, reraise=True)
    finally:
        await app.shutdown()


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
