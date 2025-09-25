#!/usr/bin/env python3
"""Test ZMQ client for TACoreService."""

import zmq
import json
import uuid
import time


def test_zmq_connection():
    """Test ZMQ connection to TACoreService."""
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)

    try:
        # Connect to LoadBalancer frontend
        socket.connect("tcp://localhost:5555")
        socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout

        # Create test request
        request = {
            "request_id": str(uuid.uuid4()),
            "method": "health.check",
            "params": {},
            "timestamp": time.time(),
        }

        print(f"Sending request: {request}")

        # Send request with proper multipart format for ROUTER
        socket.send_multipart([b"", json.dumps(request).encode("utf-8")])

        # Receive response
        empty, response_data = socket.recv_multipart()
        response = json.loads(response_data.decode("utf-8"))

        print(f"Received response: {response}")

        return response

    except zmq.Again:
        print("Request timed out - no response received")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        socket.close()
        context.term()


def test_multiple_requests():
    """Test multiple requests to verify load balancing."""
    methods = ["health.check", "scan.market", "evaluate.risk"]

    for i, method in enumerate(methods):
        print(f"\n--- Test {i+1}: {method} ---")

        context = zmq.Context()
        socket = context.socket(zmq.DEALER)

        try:
            socket.connect("tcp://localhost:5555")
            socket.setsockopt(zmq.RCVTIMEO, 10000)

            request = {
                "request_id": str(uuid.uuid4()),
                "method": method,
                "params": {
                    "market_type": "stock" if method == "scan.market" else None,
                    "portfolio": {} if method == "evaluate.risk" else None,
                    "proposed_trade": {} if method == "evaluate.risk" else None,
                },
                "timestamp": time.time(),
            }

            # Remove None values
            request["params"] = {
                k: v for k, v in request["params"].items() if v is not None
            }

            print(f"Sending: {request['method']}")
            socket.send_multipart([b"", json.dumps(request).encode("utf-8")])

            empty, response_data = socket.recv_multipart()
            response = json.loads(response_data.decode("utf-8"))

            print(f"Status: {response.get('status', 'unknown')}")
            if response.get("status") == "error":
                print(f"Error: {response.get('error', 'unknown error')}")

        except zmq.Again:
            print("Request timed out")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            socket.close()
            context.term()

        time.sleep(1)  # Brief pause between requests


if __name__ == "__main__":
    print("Testing ZMQ connection to TACoreService...")
    print("=" * 50)

    # Test basic connection
    print("\n1. Testing basic health check...")
    result = test_zmq_connection()

    if result:
        print("\n2. Testing multiple request types...")
        test_multiple_requests()
    else:
        print("\nBasic connection failed. Check if TACoreService is running.")

    print("\nTest completed.")
