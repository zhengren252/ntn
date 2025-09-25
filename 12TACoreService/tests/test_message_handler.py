"""Tests for message handler."""

import pytest
import json
from tacoreservice.core.message_handler import (
    MessageHandler,
    ServiceRequest,
    ServiceResponse,
)


@pytest.mark.unit
class TestMessageHandler:
    """Test MessageHandler functionality."""

    def test_parse_request_valid(self):
        """Test parsing valid request."""
        handler = MessageHandler()
        request_data = {
            "method": "health.check",
            "params": {"detailed": True},
            "request_id": "test_123",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        request_bytes = json.dumps(request_data).encode("utf-8")
        parsed_request = handler.parse_request(request_bytes)

        assert isinstance(parsed_request, ServiceRequest)
        assert parsed_request.method == "health.check"
        assert parsed_request.params == {"detailed": True}
        assert parsed_request.request_id == "test_123"
        assert parsed_request.timestamp is not None  # Auto-generated

    def test_parse_request_minimal(self):
        """Test parsing minimal valid request."""
        handler = MessageHandler()
        request_data = {"method": "health.check"}

        request_bytes = json.dumps(request_data).encode("utf-8")
        parsed_request = handler.parse_request(request_bytes)

        assert isinstance(parsed_request, ServiceRequest)
        assert parsed_request.method == "health.check"
        assert parsed_request.params == {}
        assert parsed_request.request_id is not None  # Should be auto-generated
        assert parsed_request.timestamp is not None  # Should be auto-generated

    def test_parse_request_invalid_json(self):
        """Test parsing invalid JSON."""
        handler = MessageHandler()
        invalid_json = b"invalid json data"

        with pytest.raises(ValueError, match="Invalid JSON"):
            handler.parse_request(invalid_json)

    def test_parse_request_missing_method(self):
        """Test parsing request without method."""
        handler = MessageHandler()
        request_data = {"params": {}, "request_id": "test_123"}

        request_bytes = json.dumps(request_data).encode("utf-8")

        with pytest.raises(ValueError, match="Missing required field: method"):
            handler.parse_request(request_bytes)

    def test_parse_request_invalid_method(self):
        """Test parsing request with invalid method."""
        handler = MessageHandler()
        request_data = {"method": "invalid.method", "params": {}}

        request_bytes = json.dumps(request_data).encode("utf-8")

        with pytest.raises(ValueError, match="Unsupported method"):
            handler.parse_request(request_bytes)

    def test_create_response_success(self):
        """Test creating successful response."""
        handler = MessageHandler()
        request_id = "test_123"
        data = {"status": "healthy"}

        response = handler.create_response(
            request_id=request_id, data=data, status="success"
        )

        assert isinstance(response, ServiceResponse)
        assert response.request_id == request_id
        assert response.data == data
        assert response.status == "success"
        assert response.error is None
        assert response.timestamp is not None
        assert response.processing_time_ms is None  # Not set in this test

    def test_create_response_error(self):
        """Test creating error response."""
        handler = MessageHandler()
        request_id = "test_456"
        error_msg = "Something went wrong"

        response = handler.create_response(
            request_id=request_id, status="error", error=error_msg
        )

        assert isinstance(response, ServiceResponse)
        assert response.request_id == request_id
        assert response.data is None
        assert response.status == "error"
        assert response.error == error_msg

    def test_serialize_response(self):
        """Test serializing response to bytes."""
        handler = MessageHandler()
        response = ServiceResponse(
            request_id="test_789",
            data={"result": "success"},
            status="success",
            error=None,
            timestamp=1704067200.0,  # Unix timestamp for 2024-01-01T00:00:00Z
            processing_time_ms=1,
        )

        serialized = handler.serialize_response(response)

        assert isinstance(serialized, bytes)

        # Verify it can be deserialized back
        deserialized = json.loads(serialized.decode("utf-8"))
        assert deserialized["request_id"] == "test_789"
        assert deserialized["data"] == {"result": "success"}
        assert deserialized["status"] == "success"
        assert deserialized["error"] is None

    def test_create_error_response(self):
        """Test creating error response helper."""
        handler = MessageHandler()
        request_id = "error_test"
        error_msg = "Test error message"

        response = handler.create_error_response(request_id, error_msg)

        assert isinstance(response, ServiceResponse)
        assert response.request_id == request_id
        assert response.status == "error"
        assert response.error == error_msg
        assert response.data is None

    def test_validate_parameters_health_check(self):
        """Test parameter validation for health.check."""
        handler = MessageHandler()
        # Valid parameters
        valid_params = {"detailed": True}
        assert handler.validate_parameters("health.check", valid_params) is True

        # Empty parameters (should be valid)
        assert handler.validate_parameters("health.check", {}) is True

        # Invalid parameter type
        invalid_params = {"detailed": "not_boolean"}
        assert handler.validate_parameters("health.check", invalid_params) is False

    def test_validate_parameters_scan_market(self):
        """Test parameter validation for scan.market."""
        handler = MessageHandler()
        # Valid parameters
        valid_params = {"market_type": "stocks"}
        assert handler.validate_parameters("scan.market", valid_params) is True

        # Missing market_type
        invalid_params = {"limit": 50}
        assert handler.validate_parameters("scan.market", invalid_params) is False

        # Invalid limit type
        invalid_params = {"criteria": {"min_volume": 1000000}, "limit": "not_integer"}
        assert handler.validate_parameters("scan.market", invalid_params) is False

    def test_validate_parameters_execute_order(self):
        """Test parameter validation for execute.order."""
        handler = MessageHandler()
        # Valid parameters
        valid_params = {"symbol": "AAPL", "action": "buy", "quantity": 100}
        assert handler.validate_parameters("execute.order", valid_params) is True

        # Missing required fields
        invalid_params = {
            "symbol": "AAPL",
            "action": "buy"
            # Missing quantity
        }
        assert handler.validate_parameters("execute.order", invalid_params) is False

        # Invalid action
        invalid_params = {"symbol": "AAPL", "action": "invalid_action", "quantity": 100}
        assert handler.validate_parameters("execute.order", invalid_params) is False

    def test_validate_parameters_evaluate_risk(self):
        """Test parameter validation for evaluate.risk."""
        handler = MessageHandler()
        # Valid parameters
        valid_params = {
            "portfolio": {"AAPL": 100, "GOOGL": 50},
            "proposed_trade": {"symbol": "MSFT", "action": "buy", "quantity": 50},
        }
        assert handler.validate_parameters("evaluate.risk", valid_params) is True

        # Missing portfolio
        invalid_params = {
            "proposed_trade": {"symbol": "MSFT", "action": "buy", "quantity": 50}
        }
        assert handler.validate_parameters("evaluate.risk", invalid_params) is False

        # Missing proposed_trade
        invalid_params = {"portfolio": {"AAPL": 100}}
        assert handler.validate_parameters("evaluate.risk", invalid_params) is False

    def test_validate_parameters_analyze_stock(self):
        """Test parameter validation for analyze.stock."""
        handler = MessageHandler()
        # Valid parameters
        valid_params = {"symbol": "AAPL"}
        assert handler.validate_parameters("analyze.stock", valid_params) is True

        # Missing symbol
        invalid_params = {"indicators": ["sma", "rsi"]}
        assert handler.validate_parameters("analyze.stock", invalid_params) is False

        # Valid with additional params
        valid_params_with_indicators = {"symbol": "AAPL", "indicators": ["sma", "rsi"]}
        assert (
            handler.validate_parameters("analyze.stock", valid_params_with_indicators)
            is True
        )

    def test_validate_parameters_get_market_data(self):
        """Test parameter validation for get.market_data."""
        handler = MessageHandler()
        # Valid parameters
        valid_params = {"symbols": ["AAPL", "GOOGL"], "fields": ["price", "volume"]}
        assert handler.validate_parameters("get.market_data", valid_params) is True

        # Missing symbols
        invalid_params = {"fields": ["price", "volume"]}
        assert handler.validate_parameters("get.market_data", invalid_params) is False

        # Empty symbols list
        invalid_params = {"symbols": [], "fields": ["price", "volume"]}
        assert handler.validate_parameters("get.market_data", invalid_params) is False

    def test_supported_methods(self):
        """Test that all expected methods are supported."""
        handler = MessageHandler()
        expected_methods = [
            "health.check",
            "scan.market",
            "execute.order",
            "evaluate.risk",
            "analyze.stock",
            "get.market_data",
        ]

        for method in expected_methods:
            # Should not raise exception for supported methods
            request_data = {"method": method}
            request_bytes = json.dumps(request_data).encode("utf-8")

            try:
                parsed_request = handler.parse_request(request_bytes)
                assert parsed_request.method == method
            except ValueError as e:
                if "Unsupported method" in str(e):
                    pytest.fail(f"Method {method} should be supported")
                else:
                    # Other validation errors are expected for minimal requests
                    pass
