#!/usr/bin/env python3
"""
Debug script for requests API
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from tacoreservice.core.database import DatabaseManager
    from tacoreservice.core.config import get_settings
except ImportError:
    # Try direct import
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tacoreservice"))
    from core.database import DatabaseManager
    from core.config import get_settings

import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test database connection and request logs."""
    try:
        settings = get_settings()
        db_manager = DatabaseManager()

        logger.info("Testing database connection...")

        # Test get_request_logs method
        logs = db_manager.get_request_logs(limit=5)
        logger.info(f"Retrieved {len(logs)} logs")

        for log in logs:
            logger.info(f"Log: {log}")

        return True

    except Exception as e:
        logger.error(f"Database test failed: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    test_database_connection()
