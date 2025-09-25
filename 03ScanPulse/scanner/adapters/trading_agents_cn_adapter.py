#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TACoreService适配器
用于将扫描器模组与TACoreService核心服务集成
"""

import asyncio

# import json  # Unused
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import structlog
import zmq

from .base_adapter import AdapterConfig, AdapterStatus, BaseAdapter

logger = structlog.get_logger(__name__)


class TradingAgentInterface(ABC):
    """交易代理接口"""

    @abstractmethod
    async def scan_market(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """扫描市场数据"""
        pass

    @abstractmethod
    async def analyze_symbol(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个交易对"""
        pass

    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据"""
        pass

    @abstractmethod
    async def get_news_events(self, symbol: str = None) -> List[Dict[str, Any]]:
        """获取新闻事件"""
        pass


class TACoreServiceClient:
    """TACoreService客户端"""

    def __init__(
        self, server_address: str = "tcp://localhost:5555", timeout: int = 30000
    ):
        self.server_address = server_address
        self.timeout = timeout
        self.context = None
        self.socket = None
        self._connected = False

    def connect(self) -> bool:
        """连接到TACoreService"""
        try:
            if self._connected:
                return True

            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
            self.socket.setsockopt(zmq.SNDTIMEO, self.timeout)
            self.socket.connect(self.server_address)

            # 测试连接（设置较短的超时时间避免阻塞）
            original_timeout = self.timeout
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            
            try:
                test_response = self.send_request("health.check")
                if test_response and test_response.get("status") == "success":
                    self._connected = True
                    logger.info("Connected to TACoreService", server=self.server_address)
                    # 恢复原始超时设置
                    self.socket.setsockopt(zmq.RCVTIMEO, original_timeout)
                    return True
                else:
                    self.disconnect()
                    return False
            except zmq.Again:
                logger.warning("TACoreService health check timeout")
                self.disconnect()
                return False

        except Exception as e:
            logger.error("Failed to connect to TACoreService", error=str(e))
            self.disconnect()
            return False

    def disconnect(self):
        """断开连接"""
        try:
            if self.socket:
                self.socket.close()
            if self.context:
                self.context.term()
        except Exception as e:
            logger.warning("Error during disconnect", error=str(e))
        finally:
            self._connected = False
            self.socket = None
            self.context = None

    def send_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """发送请求到TACoreService"""
        if not self._connected or not self.socket:
            logger.error("Not connected to TACoreService")
            return None

        try:
            request = {
                "method": method,
                "params": params or {},
                "request_id": str(uuid.uuid4()),
            }

            self.socket.send_json(request)
            response = self.socket.recv_json()

            return response

        except zmq.Again:
            logger.error("Request timeout", method=method)
            return None
        except Exception as e:
            logger.error("Request failed", method=method, error=str(e))
            return None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected


class TACoreServiceAgent(TradingAgentInterface):
    """TACoreService代理实现"""

    def __init__(self, client: TACoreServiceClient):
        self.client = client

    async def scan_market(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """扫描市场数据"""
        try:
            params = {"symbols": symbols, "scan_type": "comprehensive"}

            response = self.client.send_request("scan.market", params)

            if response and response.get("status") == "success":
                result = response.get("result", {})
                return result.get("scan_results", [])
            else:
                logger.error("Market scan failed", response=response)
                return []

        except Exception as e:
            logger.error("Market scan error", error=str(e))
            return []

    async def analyze_symbol(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个交易对"""
        try:
            params = {
                "symbol": symbol,
                "analysis_type": "comprehensive",
                "market_data": data,
            }

            response = self.client.send_request("analyze.symbol", params)

            if response and response.get("status") == "success":
                result = response.get("result", {})
                return result.get("analysis", {})
            else:
                logger.error("Symbol analysis failed", symbol=symbol, response=response)
                return {}

        except Exception as e:
            logger.error("Symbol analysis error", symbol=symbol, error=str(e))
            return {}

    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据"""
        try:
            params = {"symbol": symbol, "timeframe": "1h"}

            response = self.client.send_request("get.market_data", params)

            if response and response.get("status") == "success":
                result = response.get("result", {})
                return result.get("data", {})
            else:
                logger.error("Get market data failed", symbol=symbol, response=response)
                return None

        except Exception as e:
            logger.error("Get market data error", symbol=symbol, error=str(e))
            return None

    async def get_news_events(self, symbol: str = None) -> List[Dict[str, Any]]:
        """获取新闻事件"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol

            response = self.client.send_request("get.news_events", params)

            if response and response.get("status") == "success":
                result = response.get("result", {})
                return result.get("events", [])
            else:
                logger.warning(
                    "Get news events failed", symbol=symbol, response=response
                )
                return []

        except Exception as e:
            logger.error("Get news events error", symbol=symbol, error=str(e))
            return []

    def get_market_data_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """同步获取市场数据"""
        try:
            params = {"symbol": symbol, "timeframe": "1h"}

            response = self.client.send_request("get.market_data", params)

            if response and response.get("status") == "success":
                result = response.get("result", {})
                return result.get("data", {})
            else:
                logger.error("Get market data failed", symbol=symbol, response=response)
                return None

        except Exception as e:
            logger.error("Get market data error", symbol=symbol, error=str(e))
            return None


class TACoreServiceAdapter(BaseAdapter):
    """TACoreService适配器 - 集成TACoreService核心服务"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.client: Optional[TACoreServiceClient] = None
        self.agent: Optional[TACoreServiceAgent] = None
        self._is_connected = False

        # 适配器配置
        self.adapter_config = self.config.config.get("adapter", {})
        self.server_config = self.config.config.get("tacore_service", {})

        # 服务器地址和超时配置
        self.server_address = self.server_config.get("address", "tcp://localhost:5555")
        self.timeout = self.server_config.get("timeout", 30000)

        # 回调函数
        self.scan_result_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None

        logger.info(
            "TACoreService adapter initialized",
            server_address=self.server_address,
            timeout=self.timeout,
        )

    def set_callbacks(
        self,
        scan_result_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self.scan_result_callback = scan_result_callback
        self.error_callback = error_callback
        logger.debug("Callbacks configured")

    def connect(self) -> bool:
        """连接到TACoreService"""
        try:
            if not self.config.enabled:
                logger.info("TACoreServiceAdapter disabled")
                self._set_status(AdapterStatus.DISABLED)
                return False

            if self.config.mock_mode:
                self._set_status(AdapterStatus.MOCK)
                self._is_connected = True
                logger.info("TACoreServiceAdapter connected in mock mode")
                return True

            # 创建客户端
            self.client = TACoreServiceClient(self.server_address, self.timeout)

            # 连接到服务
            if self.client.connect():
                self.agent = TACoreServiceAgent(self.client)
                self._is_connected = True
                self._set_status(AdapterStatus.CONNECTED)
                logger.info("Connected to TACoreService", server=self.server_address)
                return True
            else:
                self._set_status(AdapterStatus.ERROR)
                logger.error("Failed to connect to TACoreService")
                return False

        except Exception as e:
            logger.error("Failed to connect to TACoreService", error=str(e))
            self._is_connected = False
            self._set_status(AdapterStatus.ERROR)
            if self.error_callback:
                asyncio.create_task(self.error_callback("connection_error", str(e)))
            return False

    def disconnect(self) -> None:
        """断开连接"""
        try:
            if self.client:
                self.client.disconnect()

            self._is_connected = False
            self.client = None
            self.agent = None
            self._set_status(AdapterStatus.DISCONNECTED)
            logger.info("Disconnected from TACoreService")

        except Exception as e:
            logger.error("Error during disconnect", error=str(e))
            self._set_status(AdapterStatus.ERROR)

    async def scan_symbols(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """扫描交易对列表"""
        if not self._is_connected or not self.agent:
            logger.error("Adapter not connected")
            return []

        try:
            logger.info(
                "Starting symbol scan via TACoreService", symbol_count=len(symbols)
            )

            # 使用TACoreService代理扫描市场
            scan_results = await self.agent.scan_market(symbols)

            # 处理扫描结果
            processed_results = []
            for result in scan_results:
                processed_result = await self._process_scan_result(result)
                if processed_result:
                    processed_results.append(processed_result)

            logger.info(
                "Symbol scan completed via TACoreService",
                scanned_count=len(symbols),
                result_count=len(processed_results),
            )

            # 调用回调函数
            if self.scan_result_callback:
                await self.scan_result_callback(processed_results)

            return processed_results

        except Exception as e:
            logger.error("Error during symbol scan", error=str(e))
            if self.error_callback:
                await self.error_callback("scan_error", str(e))
            return []

    async def analyze_symbol_detailed(self, symbol: str) -> Optional[Dict[str, Any]]:
        """详细分析单个交易对"""
        if not self._is_connected or not self.agent:
            return None

        try:
            # 获取市场数据
            market_data = await self.agent.get_market_data(symbol)
            if not market_data:
                logger.warning("No market data available", symbol=symbol)
                return None

            # 执行分析
            analysis_result = await self.agent.analyze_symbol(symbol, market_data)

            # 获取相关新闻事件
            news_events = await self.agent.get_news_events(symbol)

            # 组合详细结果
            detailed_result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "market_data": market_data,
                "analysis": analysis_result,
                "news_events": news_events,
                "adapter_metadata": {
                    "source": "TACoreService",
                    "version": self.adapter_config.get("version", "1.0.0"),
                },
            }

            logger.debug("Detailed analysis completed via TACoreService", symbol=symbol)
            return detailed_result

        except Exception as e:
            logger.error("Error during detailed analysis", symbol=symbol, error=str(e))
            if self.error_callback:
                await self.error_callback("analysis_error", str(e))
            return None

    async def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览"""
        if not self._is_connected or not self.agent:
            return {}

        try:
            # 获取热门交易对
            popular_symbols = self.adapter_config.get("popular_symbols", [])
            if not popular_symbols:
                popular_symbols = [
                    "BTCUSDT",
                    "ETHUSDT",
                    "BNBUSDT",
                    "ADAUSDT",
                    "DOTUSDT",
                ]

            # 扫描热门交易对
            overview_data = await self.agent.scan_market(popular_symbols)

            # 获取市场新闻
            market_news = await self.agent.get_news_events()

            market_overview = {
                "timestamp": datetime.now().isoformat(),
                "popular_symbols": overview_data,
                "market_news": market_news[:10],  # 最新10条新闻
                "summary": {
                    "total_symbols": len(overview_data),
                    "active_symbols": len(
                        [d for d in overview_data if d.get("volume", 0) > 0]
                    ),
                    "news_count": len(market_news),
                },
                "source": "TACoreService",
            }

            logger.info("Market overview generated via TACoreService")
            return market_overview

        except Exception as e:
            logger.error("Error generating market overview", error=str(e))
            return {}

    async def _process_scan_result(
        self, raw_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """处理原始扫描结果"""
        try:
            # 标准化结果格式
            processed_result = {
                "symbol": raw_result.get("symbol"),
                "timestamp": datetime.now().isoformat(),
                "price": raw_result.get("price", 0),
                "volume": raw_result.get("volume", 0),
                "change_24h": raw_result.get("change_24h", 0),
                "market_cap": raw_result.get("market_cap", 0),
                "score": raw_result.get("score", 0),
                "signals": raw_result.get("signals", []),
                "metadata": {
                    "source": "TACoreService",
                    "adapter_version": self.adapter_config.get("version", "1.0.0"),
                    "processed_at": datetime.now().isoformat(),
                },
            }

            # 验证必需字段
            if not processed_result["symbol"]:
                logger.warning("Invalid scan result: missing symbol")
                return None

            return processed_result

        except Exception as e:
            logger.error("Error processing scan result", error=str(e))
            return None

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected and self.client and self.client.is_connected()

    def health_check(self) -> bool:
        """健康检查（同步版本）"""
        try:
            if not self._is_connected or not self.client:
                return False

            # 发送健康检查请求
            response = self.client.send_request("health.check")
            return response and response.get("status") == "success"

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False

    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场数据（同步接口）"""
        if not self._is_connected or not self.agent:
            return None

        try:
            return self.agent.get_market_data_sync(symbol)
        except Exception as e:
            logger.error("Failed to get market data", symbol=symbol, error=str(e))
            return None

    def get_adapter_status(self) -> Dict[str, Any]:
        """获取适配器状态"""
        return {
            "connected": self._is_connected,
            "client_connected": self.client.is_connected() if self.client else False,
            "agent_available": self.agent is not None,
            "server_address": self.server_address,
            "callbacks_configured": {
                "scan_result": self.scan_result_callback is not None,
                "error": self.error_callback is not None,
            },
            "config": self.adapter_config,
            "timestamp": datetime.now().isoformat(),
        }

    async def health_check_detailed(self) -> Dict[str, Any]:
        """详细健康检查（异步版本）"""
        health_status = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # 检查连接状态
            health_status["checks"]["connection"] = self._is_connected

            # 检查客户端状态
            health_status["checks"]["client"] = (
                self.client and self.client.is_connected()
            )

            # 检查代理状态
            health_status["checks"]["agent"] = self.agent is not None

            # 如果连接正常，尝试获取市场数据
            if self._is_connected and self.agent:
                try:
                    test_data = await self.agent.get_market_data("BTCUSDT")
                    health_status["checks"]["data_access"] = test_data is not None
                except Exception:
                    health_status["checks"]["data_access"] = False
            else:
                health_status["checks"]["data_access"] = False

            # 综合健康状态
            health_status["healthy"] = all(health_status["checks"].values())

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            health_status["healthy"] = False
            health_status["error"] = str(e)

        return health_status

    async def __aenter__(self):
        self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
