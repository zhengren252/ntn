#!/usr/bin/env python3
import zmq
import json
import time


def test_zmq_connection():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    try:
        print("Connecting to LoadBalancer...")
        socket.connect("tcp://localhost:5555")

        request = {"method": "scan.market", "params": {"symbol": "AAPL"}}

        print(f"Sending request: {request}")
        socket.send_string(json.dumps(request))
        print("Request sent, waiting for response...")

        # Set timeout to 30 seconds
        socket.setsockopt(zmq.RCVTIMEO, 30000)

        try:
            response = socket.recv_string()
            print(f"Response received: {response}")
        except zmq.Again:
            print("Timeout - no response received")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    test_zmq_connection()
