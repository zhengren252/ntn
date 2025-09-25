#!/usr/bin/env python3
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from acceptance_tests.tests.test_zmq_business_api import LazyPirateClient
import json


def test_invalid_method():
    client = LazyPirateClient("tcp://localhost:5555")

    request = {"method": "invalid.method", "params": {}, "request_id": "test123"}

    print("Sending request:", json.dumps(request, indent=2))
    response = client.send_request(request)
    print("Response:", json.dumps(response, indent=2) if response else "None")
    print("Response type:", type(response))

    if response:
        print("Error field:", response.get("error"))
        print("Error type:", type(response.get("error")))

    return response


if __name__ == "__main__":
    test_invalid_method()
