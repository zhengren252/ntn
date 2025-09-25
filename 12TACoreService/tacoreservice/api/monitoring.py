"""Monitoring API for TACoreService."""

import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..config import get_settings
from ..core.database import DatabaseManager


class ServiceStatus(BaseModel):
    """Service status model."""

    service_name: str
    status: str
    uptime: float
    version: str
    timestamp: str


class WorkerStatus(BaseModel):
    """Worker status model."""

    worker_id: str
    status: str
    processed_requests: int
    last_seen: str


class ServiceMetrics(BaseModel):
    """Service metrics model."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    requests_per_minute: float
    active_workers: int


class RequestLog(BaseModel):
    """Request log model."""

    request_id: str
    method: str
    client_id: str
    worker_id: str
    processing_time_ms: int
    status: str
    timestamp: str


class MonitoringAPI:
    """HTTP API for monitoring TACoreService."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()
        self.start_time = time.time()

        # Register routes
        self._register_routes()

        self.logger.info("Monitoring API initialized")

    def _register_routes(self):
        """Register monitoring API routes."""

        @self.app.get("/api/status", response_model=ServiceStatus)
        async def get_service_status():
            """Get overall service status."""
            return await self._get_service_status()

        @self.app.get("/api/workers", response_model=List[WorkerStatus])
        async def get_workers_status():
            """Get status of all workers."""
            return await self._get_workers_status()

        @self.app.get("/api/metrics", response_model=ServiceMetrics)
        async def get_service_metrics():
            """Get service metrics."""
            return await self._get_service_metrics()

        @self.app.get("/api/requests", response_model=List[RequestLog])
        async def get_request_logs(
            limit: int = Query(100, ge=1, le=1000),
            offset: int = Query(0, ge=0),
            method: Optional[str] = Query(None),
            status: Optional[str] = Query(None),
        ):
            """Get request logs with optional filtering."""
            return await self._get_request_logs(limit, offset, method, status)

        @self.app.get("/api/requests/{request_id}")
        async def get_request_details(request_id: str):
            """Get details for a specific request."""
            return await self._get_request_details(request_id)

        @self.app.get("/api/stats")
        async def get_service_stats():
            """Get detailed service statistics."""
            return await self._get_service_stats()

        @self.app.post("/api/cleanup")
        async def cleanup_old_data(days: int = Query(7, ge=1, le=365)):
            """Clean up old data from database."""
            return await self._cleanup_old_data(days)

    async def _get_service_status(self) -> ServiceStatus:
        """Get current service status."""
        try:
            uptime = time.time() - self.start_time

            return ServiceStatus(
                service_name=self.settings.service_name,
                status="running",
                uptime=uptime,
                version="1.0.0",
                timestamp=self._get_timestamp(),
            )

        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _get_workers_status(self) -> List[WorkerStatus]:
        """Get status of all workers."""
        try:
            workers_data = self.db_manager.get_worker_status()

            workers = []
            for worker in workers_data:
                workers.append(
                    WorkerStatus(
                        worker_id=worker["worker_id"],
                        status=worker["status"],
                        processed_requests=worker.get("processed_requests", 0),
                        last_seen=worker.get("last_heartbeat", ""),
                    )
                )

            return workers

        except Exception as e:
            self.logger.error(f"Error getting workers status: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _get_service_metrics(self) -> ServiceMetrics:
        """Get service metrics."""
        try:
            stats = self.db_manager.get_service_stats()

            return ServiceMetrics(
                total_requests=stats.get("total_requests", 0),
                successful_requests=stats.get("successful_requests", 0),
                failed_requests=stats.get("failed_requests", 0),
                average_response_time=stats.get("avg_response_time", 0.0),
                requests_per_minute=stats.get("requests_per_minute", 0.0),
                active_workers=stats.get("active_workers", 0),
            )

        except Exception as e:
            self.logger.error(f"Error getting service metrics: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _get_request_logs(
        self, limit: int, offset: int, method: Optional[str], status: Optional[str]
    ) -> List[RequestLog]:
        """Get request logs with filtering."""
        try:
            logs_data = self.db_manager.get_request_logs(
                limit=limit, offset=offset, method_filter=method, status_filter=status
            )

            logs = []
            for log in logs_data:
                logs.append(
                    RequestLog(
                        request_id=log["request_id"],
                        method=log["method"],
                        client_id=log.get("client_id", ""),
                        worker_id=log.get("worker_id", ""),
                        processing_time_ms=log.get("processing_time_ms", 0),
                        status=log["status"],
                        timestamp=log["created_at"],  # Map created_at to timestamp
                    )
                )

            return logs

        except Exception as e:
            self.logger.error(f"Error getting request logs: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _get_request_details(self, request_id: str) -> Dict[str, Any]:
        """Get details for a specific request."""
        try:
            request_data = self.db_manager.get_request_details(request_id)

            if not request_data:
                raise HTTPException(status_code=404, detail="Request not found")

            return request_data

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting request details: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _get_service_stats(self) -> Dict[str, Any]:
        """Get detailed service statistics."""
        try:
            stats = self.db_manager.get_service_stats()

            # Add additional computed statistics
            uptime = time.time() - self.start_time
            stats["uptime_seconds"] = uptime
            stats["uptime_formatted"] = self._format_uptime(uptime)

            # Get method-specific statistics
            method_stats = self.db_manager.get_method_statistics()
            stats["method_statistics"] = method_stats

            # Get hourly request distribution
            hourly_stats = self.db_manager.get_hourly_request_stats()
            stats["hourly_distribution"] = hourly_stats

            return stats

        except Exception as e:
            self.logger.error(f"Error getting service stats: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _cleanup_old_data(self, days: int) -> Dict[str, Any]:
        """Clean up old data from database."""
        try:
            deleted_count = self.db_manager.cleanup_old_data(days)

            return {
                "status": "success",
                "message": f"Cleaned up data older than {days} days",
                "deleted_records": deleted_count,
                "timestamp": self._get_timestamp(),
            }

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()

    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
