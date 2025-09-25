# -*- coding: utf-8 -*-
"""
Health API for TACoreService
"""

from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, FastAPI
from typing import Optional


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    module: str
    version: str
    degraded: Optional[bool] = None


class HealthAPI:
    def __init__(self, app: FastAPI):
        self.app = app
        self.router = APIRouter()
        self.register_routes()
        # Ensure routes are mounted on the provided FastAPI app
        self.app.include_router(self.router)

    def _live_payload(self) -> HealthStatus:
        return HealthStatus(
            status="alive",
            timestamp=datetime.utcnow().isoformat(),
            module="模组12: TACoreService",
            version="1.0.0",
        )

    def register_routes(self):
        # 现有健康检查端点（示意，占位）
        @self.router.get("/health")
        async def health():
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "module": "模组12: TACoreService",
                "version": "1.0.0",
            }

        @self.router.get("/health/live", response_model=HealthStatus)
        async def health_live():
            return self._live_payload()

        # 新增 /live 别名，行为等同于 /health/live
        @self.router.get("/live", response_model=HealthStatus)
        async def live_alias():
            return await health_live()  # 直接复用同一逻辑
