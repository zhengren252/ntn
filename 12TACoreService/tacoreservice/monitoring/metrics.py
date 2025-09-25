"""Metrics collection for TACoreService."""

import time
import threading
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from ..config import get_settings
from ..core.database import DatabaseManager


class MetricsCollector:
    """Collects and manages service metrics."""

    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()

        # In-memory metrics storage
        self._metrics = {
            "requests_total": 0,
            "requests_successful": 0,
            "requests_failed": 0,
            "response_times": deque(maxlen=1000),  # Keep last 1000 response times
            "method_counts": defaultdict(int),
            "error_counts": defaultdict(int),
            "worker_metrics": defaultdict(dict),
        }

        # Thread safety
        self._lock = threading.Lock()

        # Background metrics collection
        self._collection_thread: Optional[threading.Thread] = None
        self._running = False

        self.logger.info("Metrics collector initialized")

    def start_collection(self):
        """Start background metrics collection."""
        if self._running:
            return

        self._running = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop, daemon=True
        )
        self._collection_thread.start()

        self.logger.info("Started background metrics collection")

    def stop_collection(self):
        """Stop background metrics collection."""
        self._running = False

        if self._collection_thread:
            self._collection_thread.join(timeout=5)

        self.logger.info("Stopped background metrics collection")

    def record_request(
        self,
        method: str,
        response_time_ms: int,
        success: bool,
        worker_id: Optional[str] = None,
    ):
        """Record a request metric."""
        with self._lock:
            self._metrics["requests_total"] += 1

            if success:
                self._metrics["requests_successful"] += 1
            else:
                self._metrics["requests_failed"] += 1

            self._metrics["response_times"].append(response_time_ms)
            self._metrics["method_counts"][method] += 1

            if worker_id:
                if worker_id not in self._metrics["worker_metrics"]:
                    self._metrics["worker_metrics"][worker_id] = {
                        "requests_processed": 0,
                        "total_response_time": 0,
                        "last_request_time": time.time(),
                    }

                worker_metrics = self._metrics["worker_metrics"][worker_id]
                worker_metrics["requests_processed"] += 1
                worker_metrics["total_response_time"] += response_time_ms
                worker_metrics["last_request_time"] = time.time()

    def record_error(self, error_type: str, method: Optional[str] = None):
        """Record an error metric."""
        with self._lock:
            self._metrics["error_counts"][error_type] += 1

            if method:
                error_key = f"{method}:{error_type}"
                self._metrics["error_counts"][error_key] += 1

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current in-memory metrics."""
        with self._lock:
            response_times = list(self._metrics["response_times"])

            # Calculate response time statistics
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)

                # Calculate percentiles
                sorted_times = sorted(response_times)
                p50_idx = int(len(sorted_times) * 0.5)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)

                p50_response_time = (
                    sorted_times[p50_idx] if p50_idx < len(sorted_times) else 0
                )
                p95_response_time = (
                    sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0
                )
                p99_response_time = (
                    sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0
                )
            else:
                avg_response_time = 0
                min_response_time = 0
                max_response_time = 0
                p50_response_time = 0
                p95_response_time = 0
                p99_response_time = 0

            # Calculate success rate
            total_requests = self._metrics["requests_total"]
            success_rate = (
                self._metrics["requests_successful"] / total_requests * 100
                if total_requests > 0
                else 0
            )

            # Worker statistics
            worker_stats = {}
            for worker_id, metrics in self._metrics["worker_metrics"].items():
                if metrics["requests_processed"] > 0:
                    avg_worker_response_time = (
                        metrics["total_response_time"] / metrics["requests_processed"]
                    )
                else:
                    avg_worker_response_time = 0

                worker_stats[worker_id] = {
                    "requests_processed": metrics["requests_processed"],
                    "avg_response_time_ms": avg_worker_response_time,
                    "last_request_time": metrics["last_request_time"],
                }

            return {
                "requests": {
                    "total": self._metrics["requests_total"],
                    "successful": self._metrics["requests_successful"],
                    "failed": self._metrics["requests_failed"],
                    "success_rate_percent": success_rate,
                },
                "response_times": {
                    "avg_ms": avg_response_time,
                    "min_ms": min_response_time,
                    "max_ms": max_response_time,
                    "p50_ms": p50_response_time,
                    "p95_ms": p95_response_time,
                    "p99_ms": p99_response_time,
                },
                "methods": dict(self._metrics["method_counts"]),
                "errors": dict(self._metrics["error_counts"]),
                "workers": worker_stats,
                "timestamp": time.time(),
            }

    def get_requests_per_minute(self, minutes: int = 5) -> float:
        """Calculate requests per minute over the specified time window."""
        try:
            # Get recent requests from database
            recent_requests = self.db_manager.get_recent_request_count(minutes)
            return recent_requests / minutes if minutes > 0 else 0

        except Exception as e:
            self.logger.error(f"Error calculating requests per minute: {e}")
            return 0.0

    def get_method_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics by method."""
        try:
            return self.db_manager.get_method_statistics()

        except Exception as e:
            self.logger.error(f"Error getting method statistics: {e}")
            return {}

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        with self._lock:
            total_errors = sum(self._metrics["error_counts"].values())
            total_requests = self._metrics["requests_total"]

            error_rate = (
                (total_errors / total_requests * 100) if total_requests > 0 else 0
            )

            return {
                "total_errors": total_errors,
                "error_rate_percent": error_rate,
                "error_breakdown": dict(self._metrics["error_counts"]),
                "timestamp": time.time(),
            }

    def reset_metrics(self):
        """Reset all in-memory metrics."""
        with self._lock:
            self._metrics = {
                "requests_total": 0,
                "requests_successful": 0,
                "requests_failed": 0,
                "response_times": deque(maxlen=1000),
                "method_counts": defaultdict(int),
                "error_counts": defaultdict(int),
                "worker_metrics": defaultdict(dict),
            }

        self.logger.info("Metrics reset")

    def _collection_loop(self):
        """Background metrics collection loop."""
        while self._running:
            try:
                # Collect and persist metrics periodically
                current_metrics = self.get_current_metrics()

                # Store aggregated metrics in database
                self.db_manager.record_service_metrics(
                    timestamp=int(time.time()),
                    total_requests=current_metrics["requests"]["total"],
                    successful_requests=current_metrics["requests"]["successful"],
                    failed_requests=current_metrics["requests"]["failed"],
                    avg_response_time=current_metrics["response_times"]["avg_ms"],
                    requests_per_minute=self.get_requests_per_minute(),
                )

                # Sleep for collection interval
                time.sleep(self.settings.metrics_collection_interval)

            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(5)  # Wait before retrying

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        try:
            metrics = self.get_current_metrics()

            prometheus_metrics = []

            # Request metrics
            prometheus_metrics.append(
                f"tacoreservice_requests_total {metrics['requests']['total']}"
            )
            prometheus_metrics.append(
                f"tacoreservice_requests_successful {metrics['requests']['successful']}"
            )
            prometheus_metrics.append(
                f"tacoreservice_requests_failed {metrics['requests']['failed']}"
            )
            prometheus_metrics.append(
                f"tacoreservice_success_rate {metrics['requests']['success_rate_percent']}"
            )

            # Response time metrics
            prometheus_metrics.append(
                f"tacoreservice_response_time_avg {metrics['response_times']['avg_ms']}"
            )
            prometheus_metrics.append(
                f"tacoreservice_response_time_p50 {metrics['response_times']['p50_ms']}"
            )
            prometheus_metrics.append(
                f"tacoreservice_response_time_p95 {metrics['response_times']['p95_ms']}"
            )
            prometheus_metrics.append(
                f"tacoreservice_response_time_p99 {metrics['response_times']['p99_ms']}"
            )

            # Method metrics
            for method, count in metrics["methods"].items():
                prometheus_metrics.append(
                    f'tacoreservice_method_requests{{method="{method}"}} {count}'
                )

            # Error metrics
            for error_type, count in metrics["errors"].items():
                prometheus_metrics.append(
                    f'tacoreservice_errors{{type="{error_type}"}} {count}'
                )

            # Worker metrics
            for worker_id, worker_metrics in metrics["workers"].items():
                prometheus_metrics.append(
                    f'tacoreservice_worker_requests{{worker_id="{worker_id}"}} {worker_metrics["requests_processed"]}'
                )
                prometheus_metrics.append(
                    f'tacoreservice_worker_avg_response_time{{worker_id="{worker_id}"}} {worker_metrics["avg_response_time_ms"]}'
                )

            return "\n".join(prometheus_metrics) + "\n"

        except Exception as e:
            self.logger.error(f"Error exporting Prometheus metrics: {e}")
            return "# Error exporting metrics\n"
