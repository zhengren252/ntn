"""Validation utilities for TACoreService."""

import re
from typing import Any, Dict, List, Optional, Union
from .helpers import validate_symbol, safe_float, safe_int


class ValidationError(Exception):
    """Custom validation error."""

    pass


class RequestValidator:
    """Validates service requests and parameters."""

    # Supported methods and their required parameters
    METHOD_SCHEMAS = {
        "health.check": {"required": [], "optional": []},
        "scan.market": {
            "required": [],
            "optional": ["market_type", "symbols", "filters"],
        },
        "execute.order": {
            "required": ["symbol", "action", "quantity"],
            "optional": ["price", "order_type", "time_in_force"],
        },
        "evaluate.risk": {
            "required": ["portfolio", "proposed_trade"],
            "optional": ["risk_tolerance", "time_horizon"],
        },
        "analyze.stock": {
            "required": ["symbol"],
            "optional": ["analysis_type", "time_period"],
        },
        "get.market_data": {
            "required": ["symbols"],
            "optional": ["data_type", "time_range"],
        },
    }

    @classmethod
    def validate_method(cls, method: str) -> bool:
        """Validate if method is supported.

        Args:
            method: Method name to validate

        Returns:
            True if method is supported

        Raises:
            ValidationError: If method is not supported
        """
        if not method or not isinstance(method, str):
            raise ValidationError("Method must be a non-empty string")

        if method not in cls.METHOD_SCHEMAS:
            raise ValidationError(f"Unsupported method: {method}")

        return True

    @classmethod
    def validate_request_params(cls, method: str, params: Dict[str, Any]) -> bool:
        """Validate request parameters for a given method.

        Args:
            method: Method name
            params: Parameters to validate

        Returns:
            True if parameters are valid

        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate method first
        cls.validate_method(method)

        if not isinstance(params, dict):
            raise ValidationError("Parameters must be a dictionary")

        schema = cls.METHOD_SCHEMAS[method]

        # Check required parameters
        for required_param in schema["required"]:
            if required_param not in params:
                raise ValidationError(f"Missing required parameter: {required_param}")

            if params[required_param] is None:
                raise ValidationError(
                    f"Required parameter cannot be None: {required_param}"
                )

        # Validate specific parameter types and values
        cls._validate_specific_params(method, params)

        return True

    @classmethod
    def _validate_specific_params(cls, method: str, params: Dict[str, Any]):
        """Validate specific parameters based on method."""
        if method == "execute.order":
            cls._validate_order_params(params)
        elif method == "scan.market":
            cls._validate_scan_params(params)
        elif method == "evaluate.risk":
            cls._validate_risk_params(params)
        elif method == "analyze.stock":
            cls._validate_analysis_params(params)
        elif method == "get.market_data":
            cls._validate_market_data_params(params)

    @classmethod
    def _validate_order_params(cls, params: Dict[str, Any]):
        """Validate order execution parameters."""
        # Validate symbol
        symbol = params.get("symbol")
        if not validate_symbol(symbol):
            raise ValidationError(f"Invalid symbol format: {symbol}")

        # Validate action
        action = params.get("action", "").lower()
        if action not in ["buy", "sell"]:
            raise ValidationError(f"Invalid action: {action}. Must be 'buy' or 'sell'")

        # Validate quantity
        quantity = params.get("quantity")
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            raise ValidationError("Quantity must be a positive number")

        # Validate price (if provided)
        price = params.get("price")
        if price is not None:
            if not isinstance(price, (int, float)) or price <= 0:
                raise ValidationError("Price must be a positive number")

        # Validate order type (if provided)
        order_type = params.get("order_type", "market").lower()
        if order_type not in ["market", "limit", "stop", "stop_limit"]:
            raise ValidationError(f"Invalid order type: {order_type}")

        # Validate time in force (if provided)
        time_in_force = params.get("time_in_force", "day").lower()
        if time_in_force not in ["day", "gtc", "ioc", "fok"]:
            raise ValidationError(f"Invalid time in force: {time_in_force}")

    @classmethod
    def _validate_scan_params(cls, params: Dict[str, Any]):
        """Validate market scan parameters."""
        # Validate market type
        market_type = params.get("market_type", "stock").lower()
        if market_type not in ["stock", "crypto", "forex", "commodity"]:
            raise ValidationError(f"Invalid market type: {market_type}")

        # Validate symbols (if provided)
        symbols = params.get("symbols")
        if symbols is not None:
            if not isinstance(symbols, list):
                raise ValidationError("Symbols must be a list")

            for symbol in symbols:
                if not validate_symbol(symbol):
                    raise ValidationError(f"Invalid symbol in list: {symbol}")

        # Validate filters (if provided)
        filters = params.get("filters")
        if filters is not None and not isinstance(filters, dict):
            raise ValidationError("Filters must be a dictionary")

    @classmethod
    def _validate_risk_params(cls, params: Dict[str, Any]):
        """Validate risk evaluation parameters."""
        # Validate portfolio
        portfolio = params.get("portfolio")
        if not isinstance(portfolio, dict):
            raise ValidationError("Portfolio must be a dictionary")

        # Validate proposed trade
        proposed_trade = params.get("proposed_trade")
        if not isinstance(proposed_trade, dict):
            raise ValidationError("Proposed trade must be a dictionary")

        # Validate risk tolerance (if provided)
        risk_tolerance = params.get("risk_tolerance")
        if risk_tolerance is not None:
            if risk_tolerance not in ["low", "medium", "high"]:
                raise ValidationError(f"Invalid risk tolerance: {risk_tolerance}")

    @classmethod
    def _validate_analysis_params(cls, params: Dict[str, Any]):
        """Validate stock analysis parameters."""
        # Validate symbol
        symbol = params.get("symbol")
        if not validate_symbol(symbol):
            raise ValidationError(f"Invalid symbol format: {symbol}")

        # Validate analysis type (if provided)
        analysis_type = params.get("analysis_type", "comprehensive").lower()
        if analysis_type not in ["technical", "fundamental", "comprehensive"]:
            raise ValidationError(f"Invalid analysis type: {analysis_type}")

    @classmethod
    def _validate_market_data_params(cls, params: Dict[str, Any]):
        """Validate market data parameters."""
        # Validate symbols
        symbols = params.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            raise ValidationError("Symbols must be a non-empty list")

        for symbol in symbols:
            if not validate_symbol(symbol):
                raise ValidationError(f"Invalid symbol in list: {symbol}")

        # Validate data type (if provided)
        data_type = params.get("data_type", "realtime").lower()
        if data_type not in ["realtime", "historical", "intraday"]:
            raise ValidationError(f"Invalid data type: {data_type}")


class ParameterValidator:
    """Validates individual parameters and data types."""

    @staticmethod
    def validate_string(
        value: Any,
        name: str,
        min_length: int = 1,
        max_length: int = 255,
        pattern: Optional[str] = None,
    ) -> str:
        """Validate string parameter.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern to match

        Returns:
            Validated string

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(f"{name} must be a string")

        if len(value) < min_length:
            raise ValidationError(
                f"{name} must be at least {min_length} characters long"
            )

        if len(value) > max_length:
            raise ValidationError(
                f"{name} must be at most {max_length} characters long"
            )

        if pattern and not re.match(pattern, value):
            raise ValidationError(f"{name} does not match required pattern")

        return value

    @staticmethod
    def validate_number(
        value: Any,
        name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allow_zero: bool = True,
    ) -> Union[int, float]:
        """Validate numeric parameter.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            allow_zero: Whether zero is allowed

        Returns:
            Validated number

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{name} must be a number")

        if not allow_zero and value == 0:
            raise ValidationError(f"{name} cannot be zero")

        if min_value is not None and value < min_value:
            raise ValidationError(f"{name} must be at least {min_value}")

        if max_value is not None and value > max_value:
            raise ValidationError(f"{name} must be at most {max_value}")

        return value

    @staticmethod
    def validate_list(
        value: Any,
        name: str,
        min_length: int = 0,
        max_length: Optional[int] = None,
        item_validator: Optional[callable] = None,
    ) -> List[Any]:
        """Validate list parameter.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            min_length: Minimum list length
            max_length: Maximum list length
            item_validator: Function to validate each item

        Returns:
            Validated list

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, list):
            raise ValidationError(f"{name} must be a list")

        if len(value) < min_length:
            raise ValidationError(f"{name} must have at least {min_length} items")

        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"{name} must have at most {max_length} items")

        if item_validator:
            for i, item in enumerate(value):
                try:
                    item_validator(item)
                except ValidationError as e:
                    raise ValidationError(f"{name}[{i}]: {str(e)}")

        return value

    @staticmethod
    def validate_dict(
        value: Any,
        name: str,
        required_keys: Optional[List[str]] = None,
        optional_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate dictionary parameter.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            required_keys: List of required keys
            optional_keys: List of optional keys

        Returns:
            Validated dictionary

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, dict):
            raise ValidationError(f"{name} must be a dictionary")

        if required_keys:
            for key in required_keys:
                if key not in value:
                    raise ValidationError(f"{name} missing required key: {key}")

        if optional_keys is not None:
            allowed_keys = set(required_keys or []) | set(optional_keys)
            for key in value.keys():
                if key not in allowed_keys:
                    raise ValidationError(f"{name} contains unexpected key: {key}")

        return value

    @staticmethod
    def validate_enum(
        value: Any, name: str, allowed_values: List[Any], case_sensitive: bool = True
    ) -> Any:
        """Validate enum parameter.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            allowed_values: List of allowed values
            case_sensitive: Whether comparison is case sensitive

        Returns:
            Validated value

        Raises:
            ValidationError: If validation fails
        """
        if not case_sensitive and isinstance(value, str):
            value = value.lower()
            allowed_values = [
                v.lower() if isinstance(v, str) else v for v in allowed_values
            ]

        if value not in allowed_values:
            raise ValidationError(f"{name} must be one of: {allowed_values}")

        return value
