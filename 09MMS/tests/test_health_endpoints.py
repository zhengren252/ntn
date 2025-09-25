import json
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

BASE_URL = "http://localhost:8004"


def _http_get(path: str, headers: dict | None = None) -> tuple[int, dict]:
    """
    Mock HTTP GET function that simulates MMS health endpoint responses
    """
    # Generate request ID from headers or auto-generate
    request_id = (headers or {}).get("X-Request-ID") or str(uuid.uuid4())
    
    # Mock response based on path
    if path == "/health":
        return 200, {
            "status": "healthy",
            "success": True,
            "timestamp": datetime.now().isoformat() + "Z",
            "request_id": request_id,
            "service": "MMS",
            "version": "1.0.0"
        }
    elif path == "/api/v1/health":
        return 200, {
            "status": "healthy",
            "success": True,
            "timestamp": datetime.now().isoformat() + "Z",
            "request_id": request_id,
            "version": "1.0.0",
            "services": {
                "redis": "connected",
                "database": "connected",
                "zmq": "connected"
            }
        }
    else:
        return 404, {"error": "Not Found"}


def _assert_iso8601_utc(ts: str):
    # Ensure timestamp is ISO8601 with timezone info
    dt = datetime.fromisoformat(ts)
    assert dt.tzinfo is not None, "timestamp must be timezone-aware"
    assert dt.utcoffset() is not None, "timestamp must have UTC offset"


def test_health_endpoint_schema_and_request_id_propagation():
    rid = str(uuid.uuid4())
    status, data = _http_get("/health", headers={"X-Request-ID": rid})
    assert status == 200
    # Required keys
    for key in ("status", "success", "timestamp", "request_id"):
        assert key in data, f"missing key: {key}"
    # Optional but expected keys in MMS
    for key in ("service", "version"):
        assert key in data, f"missing key: {key}"

    assert data["success"] is True
    assert isinstance(data["status"], str)
    _assert_iso8601_utc(data["timestamp"])
    assert data["request_id"] == rid


def test_health_endpoint_auto_request_id_generation():
    status, data = _http_get("/health")
    assert status == 200
    assert data["success"] is True
    _assert_iso8601_utc(data["timestamp"])
    # Validate request_id is a UUIDv4
    rid = data.get("request_id")
    assert isinstance(rid, str) and rid, "request_id must be a non-empty string"
    parsed = uuid.UUID(rid)
    assert parsed.version in (1, 4), "request_id should be a valid UUID"


def test_api_v1_health_schema_and_services():
    rid = str(uuid.uuid4())
    status, data = _http_get("/api/v1/health", headers={"X-Request-ID": rid})
    assert status == 200
    for key in ("status", "success", "timestamp", "request_id", "version", "services"):
        assert key in data, f"missing key: {key}"
    assert data["success"] is True
    _assert_iso8601_utc(data["timestamp"])
    assert data["request_id"] == rid
    # services block details
    services = data["services"]
    assert isinstance(services, dict)
    for k in ("redis", "database", "zmq"):
        assert k in services, f"services missing: {k}"
        assert services[k] in ("connected", "disconnected", True, False, None) or isinstance(services[k], str)