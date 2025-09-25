"""Helper functions for TACoreService."""

import re
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Any


def generate_request_id() -> str:
    """Generate a unique request ID.

    Returns:
        A unique request ID string
    """
    timestamp = int(time.time() * 1000)  # milliseconds
    unique_id = uuid.uuid4().hex[:8]
    return f"req_{timestamp}_{unique_id}"


def validate_symbol(symbol: str) -> bool:
    """Validate a trading symbol format.

    Args:
        symbol: Trading symbol to validate

    Returns:
        True if symbol is valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False

    # Remove whitespace and convert to uppercase
    symbol = symbol.strip().upper()

    # Basic symbol validation (alphanumeric, dots, hyphens)
    # Supports formats like: AAPL, BTC-USD, EUR.USD, etc.
    pattern = r"^[A-Z0-9][A-Z0-9.-]*[A-Z0-9]$|^[A-Z0-9]$"

    if not re.match(pattern, symbol):
        return False

    # Length constraints
    if len(symbol) < 1 or len(symbol) > 20:
        return False

    return True


def format_currency(
    amount: Union[int, float], currency: str = "USD", decimal_places: int = 2
) -> str:
    """Format a currency amount.

    Args:
        amount: Amount to format
        currency: Currency code (default: USD)
        decimal_places: Number of decimal places

    Returns:
        Formatted currency string
    """
    try:
        formatted_amount = f"{amount:,.{decimal_places}f}"
        return f"{formatted_amount} {currency}"
    except (ValueError, TypeError):
        return f"0.{'0' * decimal_places} {currency}"


def parse_timeframe(timeframe: str) -> Optional[int]:
    """Parse a timeframe string to seconds.

    Args:
        timeframe: Timeframe string (e.g., '1m', '5m', '1h', '1d')

    Returns:
        Number of seconds or None if invalid
    """
    if not timeframe or not isinstance(timeframe, str):
        return None

    timeframe = timeframe.lower().strip()

    # Extract number and unit
    match = re.match(r"^(\d+)([smhd])$", timeframe)
    if not match:
        return None

    number, unit = match.groups()
    number = int(number)

    # Convert to seconds
    multipliers = {
        "s": 1,  # seconds
        "m": 60,  # minutes
        "h": 3600,  # hours
        "d": 86400,  # days
    }

    return number * multipliers.get(unit, 0)


def get_timestamp(format_type: str = "iso") -> str:
    """Get current timestamp in various formats.

    Args:
        format_type: Format type ('iso', 'unix', 'readable')

    Returns:
        Formatted timestamp string
    """
    now = datetime.now(timezone.utc)

    if format_type == "iso":
        return now.isoformat()
    elif format_type == "unix":
        return str(int(now.timestamp()))
    elif format_type == "readable":
        return now.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        return now.isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to integer.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"

    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Ensure it's not empty
    if not sanitized:
        return "unnamed"

    return sanitized


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values.

    Args:
        old_value: Original value
        new_value: New value

    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float("inf")

    return ((new_value - old_value) / old_value) * 100


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable format.

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., '1.5 MB')
    """
    if bytes_value == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(bytes_value)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def retry_on_exception(
    max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
):
    """Decorator for retrying functions on exception.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Multiplier for delay on each retry

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        raise last_exception

            raise last_exception

        return wrapper

    return decorator


def is_market_hours(timezone_name: str = "US/Eastern") -> bool:
    """Check if current time is within market hours.

    Args:
        timezone_name: Timezone for market hours check

    Returns:
        True if within market hours, False otherwise
    """
    try:
        import pytz

        # Get current time in specified timezone
        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)

        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check if within trading hours (9:30 AM - 4:00 PM ET)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close

    except ImportError:
        # If pytz is not available, assume market is open
        return True
    except Exception:
        # If any error occurs, assume market is open
        return True
