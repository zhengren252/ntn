#!/usr/bin/env python3
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from acceptance_tests.tests.test_zmq_business_api import LazyPirateClient
import json


def test_execute_order():
    client = LazyPirateClient("tcp://localhost:5555")

    request = {
        "method": "execute.order",
        "params": {
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 0.001,
            "price": 50000,
            "order_type": "limit",
        },
        "request_id": "test123",
    }

    print("Sending request:", json.dumps(request, indent=2))
    response = client.send_request(request)
    print("Response:", json.dumps(response, indent=2) if response else "None")

    return response


if __name__ == "__main__":
    test_execute_order()
