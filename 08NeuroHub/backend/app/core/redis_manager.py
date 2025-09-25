#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis数据管理器

负责总控模块的数据存储和缓存：
- 系统状态存储
- 模组状态管理
- 市场数据缓存
- 风险告警存储
- 实时数据推送
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RedisManager:
    """Redis管理器"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.connection_pool = None

    async def init_redis(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self.connection_pool = redis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
                max_connections=20
            )

            # 创建Redis客户端
            self.redis = redis.Redis(connection_pool=self.connection_pool)

            # 测试连接
            await self.redis.ping()
            logger.info(
                f"Redis连接成功: {settings.redis_host}:{settings.redis_port}"
            )

        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis连接已关闭")

    # 系统状态管理
    async def set_system_status(self, status_data: Dict[str, Any]):
        """设置系统状态"""
        key = "system:status:master_control"
        await self.redis.hset(key, mapping=status_data)
        await self.redis.expire(key, 300)  # 5分钟过期

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        key = "system:status:master_control"
        status = await self.redis.hgetall(key)
        return status if status else {}

    async def set_module_status(self, module_name: str,
                                status_data: Dict[str, Any]):
        """设置模组状态"""
        key = f"system:status:{module_name}"
        status_data["last_heartbeat"] = datetime.now().isoformat()
        await self.redis.hset(key, mapping=status_data)
        await self.redis.expire(key, 180)  # 3分钟过期

    async def get_module_status(self, module_name: str) -> Dict[str, Any]:
        """获取模组状态"""
        key = f"system:status:{module_name}"
        status = await self.redis.hgetall(key)
        return status if status else {}

    async def get_all_module_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模组状态"""
        pattern = "system:status:*"
        keys = await self.redis.keys(pattern)

        result = {}
        for key in keys:
            module_name = key.replace("system:status:", "")
            if module_name != "master_control":  # 排除自身
                status = await self.redis.hgetall(key)
                if status:
                    result[module_name] = status

        return result

    # 市场数据管理
    async def set_market_data(self, data_type: str, data: Dict[str, Any]):
        """设置市场数据"""
        key = f"market:{data_type}"
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, 60)  # 1分钟过期

    async def get_market_data(self, data_type: str) -> Dict[str, Any]:
        """获取市场数据"""
        key = f"market:{data_type}"
        data = await self.redis.hgetall(key)
        return data if data else {}

    async def set_bull_bear_index(self, index_value: float,
                                  indicators: Dict[str, Any]):
        """设置牛熊指数"""
        data = {
            "index": str(index_value),
            "timestamp": datetime.now().isoformat(),
            "indicators": json.dumps(indicators)
        }
        await self.set_market_data("bull_bear_index", data)

    async def get_bull_bear_index(self) -> Dict[str, Any]:
        """获取牛熊指数"""
        data = await self.get_market_data("bull_bear_index")
        if data and "indicators" in data:
            data["indicators"] = json.loads(data["indicators"])
        return data

    # 风险管理
    async def set_risk_alert(self, alert_id: str, alert_data: Dict[str, Any]):
        """设置风险告警"""
        key = f"risk:alerts:{alert_id}"
        alert_data["created_at"] = datetime.now().isoformat()
        await self.redis.hset(key, mapping=alert_data)
        await self.redis.expire(key, 3600)  # 1小时过期

        # 添加到告警列表
        await self.redis.lpush("risk:alerts:list", alert_id)
        await self.redis.ltrim("risk:alerts:list", 0, 99)  # 保留最近100条

    async def get_risk_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取风险告警列表"""
        alert_ids = await self.redis.lrange("risk:alerts:list", 0, limit - 1)
        alerts = []

        for alert_id in alert_ids:
            key = f"risk:alerts:{alert_id}"
            alert_data = await self.redis.hgetall(key)
            if alert_data:
                alert_data["alert_id"] = alert_id
                alerts.append(alert_data)

        return alerts

    # 资金管理
    async def set_fund_status(self, fund_data: Dict[str, Any]):
        """设置资金状态"""
        key = "system:fund:status"
        fund_data["last_update"] = datetime.now().isoformat()
        await self.redis.hset(key, mapping=fund_data)
        await self.redis.expire(key, 300)  # 5分钟过期

    async def get_fund_status(self) -> Dict[str, Any]:
        """获取资金状态"""
        key = "system:fund:status"
        status = await self.redis.hgetall(key)
        return status if status else {}

    # 系统信息管理
    async def set_system_info(self, info_key: str, value: str):
        """设置系统信息"""
        key = "system:info"
        await self.redis.hset(key, info_key, value)

    async def get_system_info(self, info_key: str = None) -> Any:
        """获取系统信息"""
        key = "system:info"
        if info_key:
            return await self.redis.hget(key, info_key)
        else:
            return await self.redis.hgetall(key)

    # 实时数据推送
    async def publish_realtime_data(self, channel: str,
                                    data: Dict[str, Any]):
        """发布实时数据"""
        message = json.dumps(data, ensure_ascii=False)
        await self.redis.publish(channel, message)

    async def subscribe_realtime_data(self, channel: str):
        """订阅实时数据"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    # 缓存管理
    async def set_cache(self, key: str, value: Any, expire: int = 3600):
        """设置缓存"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await self.redis.setex(key, expire, value)

    async def get_cache(self, key: str) -> Any:
        """获取缓存"""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def delete_cache(self, key: str):
        """删除缓存"""
        await self.redis.delete(key)

    # 健康检查
    async def health_check(self) -> Dict[str, Any]:
        """Redis健康检查"""
        try:
            start_time = datetime.now()
            await self.redis.ping()
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            info = await self.redis.info()

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# 全局Redis管理器实例
redis_manager = RedisManager()


async def init_redis():
    """初始化Redis"""
    await redis_manager.init_redis()


def get_redis_manager() -> RedisManager:
    """获取Redis管理器实例"""
    return redis_manager