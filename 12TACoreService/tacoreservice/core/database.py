"""Database management for TACoreService."""

import sqlite3
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import contextmanager
from ..config import get_settings


class DatabaseManager:
    """SQLite database manager for TACoreService.

    Handles request logging, metrics storage, and configuration persistence.
    Thread-safe implementation with connection pooling.
    """

    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.db_path = self.settings.sqlite_db_path
        self._local = threading.local()

        # Initialize database
        self._init_database()

        self.logger.info(f"DatabaseManager initialized with database: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                self.db_path, check_same_thread=False, timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()

    def _init_database(self):
        """Initialize database tables."""
        try:
            with self.get_cursor() as cursor:
                # Request logs table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS request_logs (
                        request_id VARCHAR(100) PRIMARY KEY,
                        method VARCHAR(50) NOT NULL,
                        worker_id VARCHAR(50),
                        client_id VARCHAR(100),
                        request_data TEXT,
                        response_data TEXT,
                        processing_time_ms INTEGER,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """
                )

                # Service metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS service_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name VARCHAR(50) NOT NULL,
                        metric_value REAL NOT NULL,
                        metric_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Worker status table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS worker_status (
                        worker_id VARCHAR(50) PRIMARY KEY,
                        status VARCHAR(20) NOT NULL,
                        last_heartbeat TIMESTAMP,
                        processed_requests INTEGER DEFAULT 0,
                        cpu_usage REAL,
                        memory_usage REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Configuration table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS service_config (
                        key VARCHAR(100) PRIMARY KEY,
                        value TEXT NOT NULL,
                        description TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for better performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_request_logs_created_at 
                    ON request_logs(created_at)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_request_logs_method 
                    ON request_logs(method)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_service_metrics_timestamp 
                    ON service_metrics(timestamp)
                """
                )

                self.logger.info("Database tables initialized successfully")

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def log_request(
        self,
        request_id: str,
        method: str,
        request_data: Dict[str, Any],
        client_id: Optional[str] = None,
        worker_id: Optional[str] = None,
    ):
        """Log incoming request."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO request_logs 
                    (request_id, method, worker_id, client_id, request_data, status)
                    VALUES (?, ?, ?, ?, ?, 'processing')
                """,
                    (
                        request_id,
                        method,
                        worker_id,
                        client_id,
                        json.dumps(request_data),
                    ),
                )

        except Exception as e:
            self.logger.error(f"Failed to log request {request_id}: {e}")

    def log_response(
        self,
        request_id: str,
        response_data: Dict[str, Any],
        processing_time_ms: int,
        status: str = "success",
    ):
        """Log request completion."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE request_logs 
                    SET response_data = ?, processing_time_ms = ?, 
                        status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE request_id = ?
                """,
                    (json.dumps(response_data), processing_time_ms, status, request_id),
                )

        except Exception as e:
            self.logger.error(f"Failed to log response for {request_id}: {e}")

    def update_worker_status(
        self,
        worker_id: str,
        status: str,
        processed_requests: Optional[int] = None,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
    ):
        """Update worker status."""
        try:
            # Normalize values to avoid NULLs where not desired
            normalized_processed = 0 if processed_requests is None else int(processed_requests)
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO worker_status 
                    (worker_id, status, last_heartbeat, processed_requests, 
                     cpu_usage, memory_usage, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (worker_id, status, normalized_processed, cpu_usage, memory_usage),
                )

        except Exception as e:
            self.logger.error(f"Failed to update worker status for {worker_id}: {e}")

    def record_metric(
        self, metric_name: str, metric_value: float, metric_data: Optional[Dict] = None
    ):
        """Record service metric."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO service_metrics (metric_name, metric_value, metric_data)
                    VALUES (?, ?, ?)
                """,
                    (
                        metric_name,
                        metric_value,
                        json.dumps(metric_data) if metric_data else None,
                    ),
                )

        except Exception as e:
            self.logger.error(f"Failed to record metric {metric_name}: {e}")

    def record_service_metrics(
        self,
        timestamp: int = None,
        total_requests: int = 0,
        successful_requests: int = 0,
        failed_requests: int = 0,
        avg_response_time: float = 0.0,
        requests_per_minute: float = 0.0,
        metrics_data: Dict[str, Any] = None,
    ):
        """Record service metrics data."""
        try:
            import time

            if timestamp is None:
                timestamp = int(time.time())

            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO service_metrics 
                    (metric_name, metric_value, metric_data)
                    VALUES (?, ?, ?)
                """,
                    (
                        "service_summary",
                        total_requests,
                        json.dumps(
                            {
                                "total_requests": total_requests,
                                "successful_requests": successful_requests,
                                "failed_requests": failed_requests,
                                "avg_response_time": avg_response_time,
                                "requests_per_minute": requests_per_minute,
                                "additional_data": metrics_data or {},
                            }
                        ),
                    ),
                )

            self.logger.debug(
                f"Recorded service metrics: total_requests={total_requests}, success_rate={successful_requests/total_requests*100 if total_requests > 0 else 0:.1f}%"
            )
        except Exception as e:
            self.logger.error(f"Failed to record service metrics: {e}")

    def get_request_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        method_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        hours_back: int = 24,
    ) -> List[Dict]:
        """Get request logs with filtering."""
        try:
            with self.get_cursor() as cursor:
                # First check if table exists and has data
                cursor.execute("SELECT COUNT(*) FROM request_logs")
                count = cursor.fetchone()[0]
                self.logger.info(f"Total request logs in database: {count}")

                query = """
                    SELECT request_id, method, worker_id, client_id, 
                           processing_time_ms, status, created_at
                    FROM request_logs 
                    WHERE created_at > datetime('now', '-{} hours')
                """.format(
                    hours_back
                )

                params = []

                if method_filter:
                    query += " AND method = ?"
                    params.append(method_filter)

                if status_filter:
                    query += " AND status = ?"
                    params.append(status_filter)

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                self.logger.info(f"Executing query: {query} with params: {params}")
                cursor.execute(query, params)
                rows = cursor.fetchall()

                result = [dict(row) for row in rows]
                self.logger.info(f"Retrieved {len(result)} request logs")
                return result

        except Exception as e:
            self.logger.error(f"Failed to get request logs: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def get_recent_request_count(self, minutes: int = 5) -> int:
        """Get count of requests in the last N minutes."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM request_logs 
                    WHERE created_at > datetime('now', '-{} minutes')
                """.format(
                        minutes
                    )
                )

                result = cursor.fetchone()
                return result[0] if result else 0

        except Exception as e:
            self.logger.error(f"Failed to get recent request count: {e}")
            return 0

    def get_service_metrics(
        self, metric_name: Optional[str] = None, hours_back: int = 24
    ) -> List[Dict]:
        """Get service metrics."""
        try:
            with self.get_cursor() as cursor:
                query = """
                    SELECT * FROM service_metrics 
                    WHERE timestamp > datetime('now', '-{} hours')
                """.format(
                    hours_back
                )

                params = []

                if metric_name:
                    query += " AND metric_name = ?"
                    params.append(metric_name)

                query += " ORDER BY timestamp DESC"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to get service metrics: {e}")
            return []

    def get_worker_status(self) -> List[Dict]:
        """Get all worker status."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        worker_id,
                        status,
                        last_heartbeat,
                        COALESCE(processed_requests, 0) AS processed_requests,
                        cpu_usage,
                        memory_usage,
                        updated_at
                    FROM worker_status 
                    ORDER BY updated_at DESC
                """
                )
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to get worker status: {e}")
            return []

    def cleanup_old_data(self, retention_days: int = None):
        """Clean up old data based on retention policy."""
        if retention_days is None:
            retention_days = self.settings.metrics_retention_days

        try:
            with self.get_cursor() as cursor:
                # Clean up old request logs
                cursor.execute(
                    """
                    DELETE FROM request_logs 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(
                        retention_days
                    )
                )

                # Clean up old metrics
                cursor.execute(
                    """
                    DELETE FROM service_metrics 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(
                        retention_days
                    )
                )

                self.logger.info(f"Cleaned up data older than {retention_days} days")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        try:
            with self.get_cursor() as cursor:
                stats = {}

                # Total requests
                cursor.execute("SELECT COUNT(*) as total FROM request_logs")
                stats["total_requests"] = cursor.fetchone()["total"]

                # Requests by status
                cursor.execute(
                    """
                    SELECT status, COUNT(*) as count 
                    FROM request_logs 
                    GROUP BY status
                """
                )
                stats["requests_by_status"] = {
                    row["status"]: row["count"] for row in cursor.fetchall()
                }

                # Average processing time
                cursor.execute(
                    """
                    SELECT AVG(processing_time_ms) as avg_time 
                    FROM request_logs 
                    WHERE processing_time_ms IS NOT NULL
                """
                )
                result = cursor.fetchone()
                stats["avg_processing_time_ms"] = (
                    result["avg_time"] if result["avg_time"] else 0
                )

                # Active workers
                cursor.execute(
                    """
                    SELECT COUNT(*) as active_workers 
                    FROM worker_status 
                    WHERE status = 'idle' OR status = 'busy'
                """
                )
                stats["active_workers"] = cursor.fetchone()["active_workers"]

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}

    def get_request_details(self, request_id: str) -> Optional[Dict]:
        """Get detailed information for a specific request."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM request_logs 
                    WHERE request_id = ?
                """,
                    (request_id,),
                )

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            self.logger.error(f"Failed to get request details for {request_id}: {e}")
            return None

    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        try:
            with self.get_cursor() as cursor:
                stats = {}

                # Total requests in last 24 hours
                cursor.execute(
                    """
                    SELECT COUNT(*) as total 
                    FROM request_logs 
                    WHERE created_at > datetime('now', '-24 hours')
                """
                )
                stats["total_requests"] = cursor.fetchone()["total"]

                # Successful requests
                cursor.execute(
                    """
                    SELECT COUNT(*) as successful 
                    FROM request_logs 
                    WHERE status = 'success' AND created_at > datetime('now', '-24 hours')
                """
                )
                stats["successful_requests"] = cursor.fetchone()["successful"]

                # Failed requests
                cursor.execute(
                    """
                    SELECT COUNT(*) as failed 
                    FROM request_logs 
                    WHERE status = 'error' AND created_at > datetime('now', '-24 hours')
                """
                )
                stats["failed_requests"] = cursor.fetchone()["failed"]

                # Average response time
                cursor.execute(
                    """
                    SELECT AVG(processing_time_ms) as avg_time 
                    FROM request_logs 
                    WHERE processing_time_ms IS NOT NULL 
                    AND created_at > datetime('now', '-24 hours')
                """
                )
                result = cursor.fetchone()
                stats["avg_response_time"] = (
                    result["avg_time"] if result["avg_time"] else 0.0
                )

                # Requests per minute (last hour)
                cursor.execute(
                    """
                    SELECT COUNT(*) as count 
                    FROM request_logs 
                    WHERE created_at > datetime('now', '-1 hour')
                """
                )
                hourly_requests = cursor.fetchone()["count"]
                stats["requests_per_minute"] = hourly_requests / 60.0

                # Active workers
                cursor.execute(
                    """
                    SELECT COUNT(*) as active 
                    FROM worker_status 
                    WHERE (status = 'idle' OR status = 'busy') 
                    AND last_heartbeat > datetime('now', '-5 minutes')
                """
                )
                stats["active_workers"] = cursor.fetchone()["active"]

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get service stats: {e}")
            return {}

    def get_method_statistics(self) -> Dict[str, Any]:
        """Get statistics by method type."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        method,
                        COUNT(*) as total_calls,
                        AVG(processing_time_ms) as avg_time,
                        MIN(processing_time_ms) as min_time,
                        MAX(processing_time_ms) as max_time,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                    FROM request_logs 
                    WHERE created_at > datetime('now', '-24 hours')
                    GROUP BY method
                    ORDER BY total_calls DESC
                """
                )

                methods = {}
                for row in cursor.fetchall():
                    methods[row["method"]] = {
                        "total_calls": row["total_calls"],
                        "avg_time": row["avg_time"] or 0.0,
                        "min_time": row["min_time"] or 0.0,
                        "max_time": row["max_time"] or 0.0,
                        "success_count": row["success_count"],
                        "error_count": row["error_count"],
                        "success_rate": (
                            row["success_count"] / row["total_calls"] * 100
                        )
                        if row["total_calls"] > 0
                        else 0.0,
                    }

                return methods

        except Exception as e:
            self.logger.error(f"Failed to get method statistics: {e}")
            return {}

    def get_hourly_request_stats(self, hours_back: int = 24) -> List[Dict]:
        """Get hourly request distribution."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT 
                        strftime('%Y-%m-%d %H:00:00', created_at) as hour,
                        COUNT(*) as request_count,
                        AVG(processing_time_ms) as avg_time,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                    FROM request_logs 
                    WHERE created_at > datetime('now', '-{hours_back} hours')
                    GROUP BY strftime('%Y-%m-%d %H:00:00', created_at)
                    ORDER BY hour DESC
                """
                )

                hourly_stats = []
                for row in cursor.fetchall():
                    hourly_stats.append(
                        {
                            "hour": row["hour"],
                            "request_count": row["request_count"],
                            "avg_time": row["avg_time"] or 0.0,
                            "success_count": row["success_count"],
                            "error_count": row["error_count"],
                        }
                    )

                return hourly_stats

        except Exception as e:
            self.logger.error(f"Failed to get hourly request stats: {e}")
            return []

    def close(self):
        """Close database connections."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            delattr(self._local, "connection")

        self.logger.info("Database connections closed")
