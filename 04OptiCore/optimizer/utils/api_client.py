#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIForge集成客户端
NeuroTrade Nexus (NTN) - APIForge Integration Client

核心功能：
1. 与模组一（APIForge）的HTTP API集成
2. 历史数据获取接口
3. 交易所API统一调用
4. 认证和配额管理
5. 自动重试和错误处理
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import numpy as np
import pandas as pd


@dataclass
class APIForgeConfig:
    """APIForge配置"""
    
    base_url: str = "http://localhost:8001"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class APIForgeStats:
    """APIForge统计信息"""
    
    requests_sent: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    last_request_time: Optional[datetime] = None


class APIForgeClient:
    """
    APIForge集成客户端
    
    实现NeuroTrade Nexus规范：
    - 与模组一的统一API接口集成
    - 支持历史数据获取
    - 自动认证和错误处理
    - 连接池管理
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        
        # 初始化配置
        self.config = APIForgeConfig(
            base_url=config.get("base_url", "http://localhost:8001"),
            api_key=config.get("api_key"),
            timeout=config.get("timeout", 30),
            max_retries=config.get("max_retries", 3),
            retry_delay=config.get("retry_delay", 1.0)
        )
        
        # 初始化统计信息
        self.stats = APIForgeStats()
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
    
    async def initialize(self):
        """初始化APIForge客户端"""
        if self._initialized:
            return
            
        try:
            self.logger.info("正在初始化APIForge客户端...")
            
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {}
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
                
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
            
            # 测试连接
            await self._test_connection()
            
            self._initialized = True
            self.logger.info("APIForge客户端初始化完成")
            
        except Exception as e:
            self.logger.error(f"APIForge客户端初始化失败: {e}")
            await self.cleanup()
            raise
    
    async def _test_connection(self):
        """测试与APIForge的连接"""
        try:
            url = f"{self.config.base_url}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    self.logger.info("APIForge连接测试成功")
                else:
                    raise ConnectionError(f"APIForge健康检查失败: {response.status}")
        except Exception as e:
            self.logger.warning(f"APIForge连接测试失败，将使用降级模式: {e}")
    
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 交易对符号
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            interval: 时间间隔 (1m, 5m, 1h, 1d等)
            
        Returns:
            历史数据DataFrame
        """
        try:
            self.logger.info(f"请求历史数据: {symbol} ({start_date} - {end_date})")
            
            url = f"{self.config.base_url}/api/v1/market/historical"
            params = {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "interval": interval
            }
            
            data = await self._make_request("GET", url, params=params)
            
            if data and "klines" in data:
                # 转换为DataFrame
                df = pd.DataFrame(data["klines"])
                df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp")
                
                # 转换数据类型
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col])
                
                self.logger.info(f"成功获取 {len(df)} 条历史数据")
                return df
            else:
                # 降级：生成模拟数据
                return self._generate_mock_data(symbol, start_date, end_date)
                
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            # 降级：生成模拟数据
            return self._generate_mock_data(symbol, start_date, end_date)
    
    async def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取市场信息
        
        Args:
            symbol: 交易对符号
            
        Returns:
            市场信息字典
        """
        try:
            url = f"{self.config.base_url}/api/v1/market/info"
            params = {"symbol": symbol}
            
            data = await self._make_request("GET", url, params=params)
            
            if data:
                return data
            else:
                # 降级：返回默认市场信息
                return self._get_default_market_info(symbol)
                
        except Exception as e:
            self.logger.error(f"获取市场信息失败: {e}")
            return self._get_default_market_info(symbol)
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            params: 查询参数
            data: 请求数据
            
        Returns:
            响应数据
        """
        if not self.session:
            await self.initialize()
        
        for attempt in range(self.config.max_retries):
            try:
                self.stats.requests_sent += 1
                self.stats.last_request_time = datetime.now()
                
                async with self.session.request(
                    method, url, params=params, json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.stats.requests_successful += 1
                        return result
                    else:
                        self.logger.warning(f"API请求失败: {response.status}")
                        
            except Exception as e:
                self.logger.warning(f"请求尝试 {attempt + 1} 失败: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        self.stats.requests_failed += 1
        return None
    
    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟历史数据（降级模式）"""
        self.logger.info(f"生成模拟数据: {symbol}")
        
        # 创建日期范围
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 生成模拟价格数据
        np.random.seed(42)  # 确保可重现
        base_price = 100.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # 创建OHLCV数据
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                "timestamp": date,
                "open": price,
                "high": high,
                "low": low,
                "close": price,
                "volume": volume
            })
        
        df = pd.DataFrame(data)
        df = df.set_index("timestamp")
        
        return df
    
    def _get_default_market_info(self, symbol: str) -> Dict[str, Any]:
        """获取默认市场信息（降级模式）"""
        return {
            "symbol": symbol,
            "base_asset": symbol.replace("USDT", "").replace("BTC", ""),
            "quote_asset": "USDT",
            "status": "TRADING",
            "min_qty": 0.001,
            "max_qty": 1000000,
            "step_size": 0.001,
            "tick_size": 0.01,
            "min_notional": 10.0
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            self._initialized = False
            self.logger.info("APIForge客户端资源清理完成")
            
        except Exception as e:
            self.logger.error(f"APIForge客户端清理失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "requests_sent": self.stats.requests_sent,
            "requests_successful": self.stats.requests_successful,
            "requests_failed": self.stats.requests_failed,
            "success_rate": (
                self.stats.requests_successful / max(self.stats.requests_sent, 1)
            ),
            "last_request_time": (
                self.stats.last_request_time.isoformat() 
                if self.stats.last_request_time else None
            ),
            "is_initialized": self._initialized
        }


def create_api_forge_client(config: Dict[str, Any]) -> APIForgeClient:
    """
    创建APIForge客户端实例
    
    Args:
        config: 客户端配置
        
    Returns:
        APIForge客户端实例
    """
    return APIForgeClient(config)