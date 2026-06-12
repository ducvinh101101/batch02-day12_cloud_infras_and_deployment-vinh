"""Exercise test for API-key authentication."""
import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("AGENT_API_KEY", "demo-key-change-in-production")


def request(key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key
    req = urllib.request.Request(
        f"{BASE_URL}/ask",
        data=json.dumps({"question": "hello"}).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


assert request() == 401
assert request("wrong-key") == 401
assert request(API_KEY) == 200
print("PASS: missing=401, invalid=401, valid=200")
