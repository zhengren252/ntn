#!/usr/bin/env python3
"""Check database tables status."""

from tacoreservice.core.database import DatabaseManager
from tacoreservice.config import get_settings


def check_database_tables():
    """Check if database tables exist."""
    try:
        # Initialize database manager
        db = DatabaseManager()
        print("Database manager initialized successfully")

        # Get cursor and check tables
        with db.get_cursor() as cursor:
            # Check if request_logs table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='request_logs'
            """
            )
            request_logs_exists = cursor.fetchone() is not None
            print(f"request_logs table exists: {request_logs_exists}")

            # List all tables
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """
            )
            tables = cursor.fetchall()
            print(f"All tables: {[table[0] for table in tables]}")

            # If request_logs exists, check its structure
            if request_logs_exists:
                cursor.execute("PRAGMA table_info(request_logs)")
                columns = cursor.fetchall()
                print("request_logs table structure:")
                for col in columns:
                    print(f"  {col[1]} {col[2]}")

    except Exception as e:
        print(f"Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_database_tables()
