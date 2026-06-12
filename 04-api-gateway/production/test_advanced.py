"""End-to-end exercise tests for JWT, roles, rate limiting, and cost guard."""
import argparse
import json
import os
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def call(path, method="GET", body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else {}


def token(username, password):
    status, payload = call(
        "/auth/token", "POST", {"username": username, "password": password}
    )
    assert status == 200
    return payload["access_token"]


def test_all():
    assert call("/ask", "POST", {"question": "hello"})[0] == 401
    student = token("student", "demo123")
    assert call("/ask", "POST", {"question": "docker"}, student)[0] == 200
    assert call("/admin/stats", token=student)[0] == 403
    teacher = token("teacher", "teach456")
    assert call("/admin/stats", token=teacher)[0] == 200
    print("PASS: JWT auth, protected endpoint, and admin role")


def test_rate_limit():
    student = token("student", "demo123")
    statuses = [
        call("/ask", "POST", {"question": f"test {i}"}, student)[0]
        for i in range(11)
    ]
    assert statuses[-1] == 429, statuses
    print(f"PASS: rate-limit statuses={statuses}")


parser = argparse.ArgumentParser()
parser.add_argument("--test", choices=["all", "rate-limit"], default="all")
args = parser.parse_args()
test_rate_limit() if args.test == "rate-limit" else test_all()
