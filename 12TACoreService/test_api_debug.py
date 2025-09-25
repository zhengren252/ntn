#!/usr/bin/env python3
"""
Quick debug script for API endpoint issue
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from tacoreservice.core.database import DatabaseManager
    import requests
    import traceback

    print("=== API Debug Test ===")

    # Test database connection
    print("\n1. Testing database connection...")
    db = DatabaseManager()

    # Check if request_logs table exists and has data
    print("\n2. Checking request_logs table...")
    with db.get_cursor() as cursor:
        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='request_logs'"
            )
            table_exists = cursor.fetchone()
            print(f"request_logs table exists: {table_exists is not None}")

            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM request_logs")
                count = cursor.fetchone()[0]
                print(f"Total records in request_logs: {count}")

                # Show table schema
                cursor.execute("PRAGMA table_info(request_logs)")
                columns = cursor.fetchall()
                print("Table schema:")
                for col in columns:
                    print(f"  {col[1]} ({col[2]})")

                # Show sample data if any
                if count > 0:
                    cursor.execute("SELECT * FROM request_logs LIMIT 3")
                    rows = cursor.fetchall()
                    print("\nSample data:")
                    for row in rows:
                        print(f"  {dict(row)}")

        except Exception as e:
            print(f"Database error: {e}")
            traceback.print_exc()

    # Test API endpoint directly
    print("\n3. Testing API endpoint...")
    try:
        response = requests.get("http://localhost:8080/api/requests?limit=5", timeout=5)
        print(f"API Response Status: {response.status_code}")
        print(f"API Response Headers: {dict(response.headers)}")
        if response.status_code == 200:
            print(f"API Response Data: {response.json()}")
        else:
            print(f"API Response Error: {response.text}")
    except Exception as e:
        print(f"API request error: {e}")
        traceback.print_exc()

    print("\n=== Debug Complete ===")

except Exception as e:
    print(f"Script error: {e}")
    traceback.print_exc()
