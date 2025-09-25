"""Tests for database manager."""

import pytest
import json
from datetime import datetime, timedelta
from tacoreservice.core.database import DatabaseManager


@pytest.mark.unit
class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_initialization(self, test_database):
        """Test database initialization."""
        assert test_database is not None

        # Check if tables exist
        with test_database.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN 
                ('request_logs', 'service_metrics', 'worker_status', 'service_config')
            """
            )
            tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = [
            "request_logs",
            "service_metrics",
            "worker_status",
            "service_config",
        ]
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"

    def test_log_request(self, test_database):
        """Test request logging."""
        request_id = "test_request_123"
        method = "health.check"
        client_id = "test_client"
        worker_id = "worker_1"
        request_data = {"test": "data"}

        test_database.log_request(
            request_id=request_id,
            method=method,
            client_id=client_id,
            worker_id=worker_id,
            request_data=request_data,
        )

        # Verify the request was logged
        with test_database.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM request_logs WHERE request_id = ?", (request_id,)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["request_id"] == request_id
        assert row["method"] == method
        assert row["client_id"] == client_id
        assert row["worker_id"] == worker_id
        assert json.loads(row["request_data"]) == request_data

    def test_log_response(self, test_database):
        """Test response logging."""
        request_id = "test_request_456"

        # First log a request
        test_database.log_request(
            request_id=request_id,
            method="test.method",
            request_data={"test": "data"},
            client_id="test_client",
            worker_id="worker_1",
        )

        # Then log the response
        response_data = {"result": "success"}
        processing_time = 150.5
        status = "success"

        test_database.log_response(
            request_id=request_id,
            response_data=response_data,
            processing_time_ms=processing_time,
            status=status,
        )

        # Verify the response was logged
        with test_database.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM request_logs WHERE request_id = ?", (request_id,)
            )
            row = cursor.fetchone()

        assert row is not None
        assert json.loads(row["response_data"]) == response_data
        assert row["processing_time_ms"] == processing_time
        assert row["status"] == status

    def test_update_worker_status(self, test_database):
        """Test worker status update."""
        worker_id = "worker_test_1"
        status = "idle"
        processed_requests = 10
        cpu_usage = 25.5
        memory_usage = 512.0

        test_database.update_worker_status(
            worker_id=worker_id,
            status=status,
            processed_requests=processed_requests,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
        )

        # Verify worker status was updated
        with test_database.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM worker_status WHERE worker_id = ?", (worker_id,)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["worker_id"] == worker_id
        assert row["status"] == status
        assert row["processed_requests"] == processed_requests
        assert row["cpu_usage"] == cpu_usage
        assert row["memory_usage"] == memory_usage

    def test_record_metric(self, test_database):
        """Test metric recording."""
        metric_name = "test_metric"
        metric_value = 42.5
        metric_data = {"additional": "info"}

        test_database.record_metric(
            metric_name=metric_name, metric_value=metric_value, metric_data=metric_data
        )

        # Verify metric was recorded
        with test_database.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM service_metrics WHERE metric_name = ?", (metric_name,)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["metric_name"] == metric_name
        assert row["metric_value"] == metric_value
        assert json.loads(row["metric_data"]) == metric_data

    def test_get_request_logs(self, test_database):
        """Test getting request logs."""
        # Insert test data
        for i in range(5):
            test_database.log_request(
                request_id=f"test_req_{i}",
                method="test.method",
                request_data={"test": f"data_{i}"},
                client_id="test_client",
                worker_id="worker_1",
            )

        # Get logs
        logs = test_database.get_request_logs(limit=3)

        assert len(logs) == 3
        assert all("request_id" in log for log in logs)

    def test_get_worker_status(self, test_database):
        """Test getting worker status."""
        # Insert test workers
        for i in range(3):
            test_database.update_worker_status(
                worker_id=f"worker_{i}", status="idle", processed_requests=i * 10
            )

        # Get worker status
        workers = test_database.get_worker_status()

        assert len(workers) == 3
        assert all("worker_id" in worker for worker in workers)

    def test_get_service_stats(self, test_database):
        """Test getting service statistics."""
        # Insert test data
        for i in range(10):
            request_id = f"stats_test_{i}"
            test_database.log_request(
                request_id=request_id,
                method="test.method",
                request_data={"test": "data"},
                client_id="test_client",
                worker_id="worker_1",
            )

            status = "success" if i % 2 == 0 else "error"
            test_database.log_response(
                request_id=request_id,
                response_data={"test": "data"},
                processing_time_ms=100.0 + i,
                status=status,
            )

        # Get stats
        stats = test_database.get_service_stats()

        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "avg_response_time" in stats
        assert stats["total_requests"] >= 10

    def test_get_method_statistics(self, test_database):
        """Test getting method statistics."""
        # Insert test data for different methods
        methods = ["health.check", "scan.market", "execute.order"]

        for method in methods:
            for i in range(5):
                request_id = f"{method}_{i}"
                test_database.log_request(
                    request_id=request_id,
                    method=method,
                    request_data={"test": "data"},
                    client_id="test_client",
                    worker_id="worker_1",
                )

                test_database.log_response(
                    request_id=request_id,
                    response_data={"test": "data"},
                    processing_time_ms=100.0 + i,
                    status="success",
                )

        # Get method stats
        method_stats = test_database.get_method_statistics()

        assert len(method_stats) >= 3
        for method in methods:
            assert method in method_stats
            assert "total_calls" in method_stats[method]
            assert "avg_time" in method_stats[method]
            assert "success_rate" in method_stats[method]

    def test_cleanup_old_data(self, test_database):
        """Test cleaning up old data."""
        # Insert old data (simulate by directly inserting with old timestamp)
        with test_database.get_cursor() as cursor:
            old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
            cursor.execute(
                """
                INSERT INTO request_logs 
                (request_id, method, client_id, worker_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                ("old_request", "test.method", "client", "worker", old_timestamp),
            )

        # Insert recent data
        test_database.log_request(
            request_id="recent_request",
            method="test.method",
            request_data={"test": "data"},
            client_id="client",
            worker_id="worker",
        )

        # Cleanup data older than 7 days
        test_database.cleanup_old_data(retention_days=7)

        # Verify old data was removed and recent data remains
        with test_database.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM request_logs")
            count = cursor.fetchone()["count"]

        assert count == 1  # Only recent request should remain
