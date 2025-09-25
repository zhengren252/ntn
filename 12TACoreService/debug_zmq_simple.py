#!/usr/bin/env python3
import zmq
import json
import time


def test_simple_zmq():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

    # Set timeout
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds

    request = {
        "request_id": f"debug_test_{int(time.time())}",
        "method": "scan.market",
        "params": {
            "market_type": "crypto",
            "symbols": ["BTC/USDT"],
            "scan_type": "opportunities",
        },
    }

    print(f"Sending request: {request}")
    socket.send_string(json.dumps(request))

    try:
        response = socket.recv_string()
        print(f"Received response: {response}")
        response_data = json.loads(response)
        print(f"Response status: {response_data.get('status')}")
    except zmq.Again:
        print("Request timed out")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    test_simple_zmq()
