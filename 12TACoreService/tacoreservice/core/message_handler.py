"""Message handling and serialization for TACoreService."""

import json
import uuid
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ServiceRequest:
    """Standard service request format."""

    method: str
    params: Dict[str, Any]
    request_id: str
    timestamp: float
    client_id: Optional[str] = None


@dataclass
class ServiceResponse:
    """Standard service response format."""

    status: str  # success, error
    request_id: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ServiceResponse to dictionary."""
        return {
            'status': self.status,
            'request_id': self.request_id,
            'data': self.data,
            'error': self.error,
            'processing_time_ms': self.processing_time_ms,
            'timestamp': self.timestamp
        }


class MessageHandler:
    """Handles message serialization, validation, and routing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Supported service methods
        self.supported_methods = {
            "scan.market",
            "execute.order",
            "evaluate.risk",
            "analyze.stock",
            "get.market_data",
            "health.check",
        }

    def parse_request(self, raw_message: bytes) -> ServiceRequest:
        """Parse raw message into ServiceRequest."""
        try:
            data = json.loads(raw_message.decode("utf-8"))

            # Validate required fields
            if "method" not in data:
                raise ValueError("Missing required field: method")

            if "params" not in data:
                data["params"] = {}

            # Generate request ID if not provided
            if "request_id" not in data:
                data["request_id"] = str(uuid.uuid4())

            # Validate method
            if data["method"] not in self.supported_methods:
                raise ValueError(f"Unsupported method: {data['method']}")

            return ServiceRequest(
                method=data["method"],
                params=data["params"],
                request_id=data["request_id"],
                timestamp=time.time(),
                client_id=data.get("client_id"),
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Request parsing error: {e}")

    def create_response(
        self,
        request_id: str,
        status: str = "success",
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
    ) -> ServiceResponse:
        """Create a standardized service response."""
        return ServiceResponse(
            status=status,
            request_id=request_id,
            data=data,
            error=error,
            processing_time_ms=processing_time_ms,
        )

    def serialize_response(self, response: ServiceResponse) -> bytes:
        """Serialize ServiceResponse to bytes."""
        try:
            response_dict = asdict(response)
            return json.dumps(response_dict, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            self.logger.error(f"Response serialization error: {e}")
            # Create error response
            error_response = {
                "status": "error",
                "request_id": response.request_id,
                "error": "Response serialization failed",
                "timestamp": time.time(),
            }
            return json.dumps(error_response).encode("utf-8")

    def create_error_response(
        self,
        request_id: str,
        error_message: str,
        processing_time_ms: Optional[int] = None,
    ) -> ServiceResponse:
        """Create an error response."""
        return self.create_response(
            request_id=request_id,
            status="error",
            error=error_message,
            processing_time_ms=processing_time_ms,
        )

    def validate_request_params(self, method: str, params: Dict[str, Any]) -> bool:
        """Validate request parameters based on method."""
        try:
            if method == "scan.market":
                return self._validate_scan_market_params(params)
            elif method == "execute.order":
                return self._validate_execute_order_params(params)
            elif method == "evaluate.risk":
                return self._validate_evaluate_risk_params(params)
            elif method == "analyze.stock":
                return self._validate_analyze_stock_params(params)
            elif method == "get.market_data":
                return self._validate_get_market_data_params(params)
            elif method == "health.check":
                return self._validate_health_check_params(params)
            else:
                return False
        except Exception as e:
            self.logger.error(f"Parameter validation error for {method}: {e}")
            return False

    @classmethod
    def validate_parameters(cls, method: str, params: Dict[str, Any]) -> bool:
        """Class method for parameter validation (backward compatibility)."""
        handler = cls()
        return handler.validate_request_params(method, params)

    def _validate_scan_market_params(self, params: Dict[str, Any]) -> bool:
        """Validate scan.market parameters."""
        required_fields = ["market_type"]
        return all(field in params for field in required_fields)

    def _validate_execute_order_params(self, params: Dict[str, Any]) -> bool:
        """Validate execute.order parameters."""
        # Support both formats: (action, quantity) and (side, amount)
        has_action_quantity = (
            "symbol" in params and "action" in params and "quantity" in params
        )
        has_side_amount = "symbol" in params and "side" in params and "amount" in params

        if not (has_action_quantity or has_side_amount):
            return False

        # Validate action/side
        action_field = "action" if "action" in params else "side"
        if params[action_field] not in ["buy", "sell"]:
            return False

        # Validate quantity/amount
        quantity_field = "quantity" if "quantity" in params else "amount"
        try:
            quantity = float(params[quantity_field])
            if quantity <= 0:
                return False
        except (ValueError, TypeError):
            return False

        return True

    def _validate_evaluate_risk_params(self, params: Dict[str, Any]) -> bool:
        """Validate evaluate.risk parameters."""
        # Accept either the new format (portfolio + proposed_trade) or legacy format (portfolio + market_conditions)
        has_new_format = "portfolio" in params and "proposed_trade" in params
        has_legacy_format = "portfolio" in params and (
            "market_conditions" in params or "risk_tolerance" in params
        )
        return has_new_format or has_legacy_format

    def _validate_analyze_stock_params(self, params: Dict[str, Any]) -> bool:
        """Validate analyze.stock parameters."""
        required_fields = ["symbol"]
        return all(field in params for field in required_fields)

    def _validate_get_market_data_params(self, params: Dict[str, Any]) -> bool:
        """Validate get.market_data parameters."""
        required_fields = ["symbols"]
        if not all(field in params for field in required_fields):
            return False

        # Validate symbols is a list and not empty
        if not isinstance(params["symbols"], list) or len(params["symbols"]) == 0:
            return False

        return True

    def _validate_health_check_params(self, params: Dict[str, Any]) -> bool:
        """Validate health.check parameters."""
        # Health check accepts optional 'detailed' boolean parameter
        if "detailed" in params:
            return isinstance(params["detailed"], bool)
        return True  # No params required, or valid detailed param

    def log_request(self, request: ServiceRequest, client_info: Optional[str] = None):
        """Log incoming request."""
        self.logger.info(
            f"Request {request.request_id}: {request.method} "
            f"from {client_info or 'unknown'} "
            f"with params: {request.params}"
        )

    def log_response(
        self, response: ServiceResponse, processing_time_ms: Optional[int] = None
    ):
        """Log outgoing response."""
        status_msg = "SUCCESS" if response.status == "success" else "ERROR"
        time_msg = f" ({processing_time_ms}ms)" if processing_time_ms else ""

        self.logger.info(f"Response {response.request_id}: {status_msg}{time_msg}")

        if response.error:
            self.logger.error(f"Error in {response.request_id}: {response.error}")
