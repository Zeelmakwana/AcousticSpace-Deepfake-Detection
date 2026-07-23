"""
Test CORS preflight — does the backend properly respond to OPTIONS requests
from http://localhost:5173 (the Vite dev server origin)?
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"

def options_request(path, origin, request_method="POST", request_headers="Content-Type, Authorization"):
    req = urllib.request.Request(f"{BASE}{path}", method="OPTIONS")
    req.add_header("Origin", origin)
    req.add_header("Access-Control-Request-Method", request_method)
    req.add_header("Access-Control-Request-Headers", request_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            headers = dict(resp.headers)
            return resp.status, headers
    except urllib.error.HTTPError as e:
        headers = dict(e.headers)
        return e.code, headers

print("=" * 70)
print("CORS Preflight Tests")
print("=" * 70)

# Test 1: Preflight from Vite dev server origin
print("\n[1] OPTIONS /auth/login from http://localhost:5173")
status, headers = options_request("/auth/login", "http://localhost:5173")
print(f"  Status: {status}")
for k, v in headers.items():
    if "access-control" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")

# Test 2: Preflight from http://localhost:3000
print("\n[2] OPTIONS /auth/login from http://localhost:3000")
status, headers = options_request("/auth/login", "http://localhost:3000")
print(f"  Status: {status}")
for k, v in headers.items():
    if "access-control" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")

# Test 3: Preflight from unknown origin
print("\n[3] OPTIONS /auth/login from http://evil.com (should be rejected)")
status, headers = options_request("/auth/login", "http://evil.com")
print(f"  Status: {status}")
for k, v in headers.items():
    if "access-control" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")

# Test 4: Check if X-Request-ID is also allowed (used by logging middleware)
print("\n[4] OPTIONS with X-Request-ID header from http://localhost:5173")
status, headers = options_request(
    "/auth/login",
    "http://localhost:5173",
    request_headers="Content-Type, Authorization, X-Request-ID"
)
print(f"  Status: {status}")
acao = headers.get("access-control-allow-origin", "MISSING")
acah = headers.get("access-control-allow-headers", "MISSING")
print(f"  Access-Control-Allow-Origin:  {acao}")
print(f"  Access-Control-Allow-Headers: {acah}")

print("\n" + "=" * 70)
print("CORS Summary:")
print("  If Access-Control-Allow-Origin is 'http://localhost:5173' → browser will proceed")
print("  If it's MISSING or different → browser blocks the request (no JSON body sent)")
print("  When blocked, the actual POST may be sent as form-encoded → 422 validation error")
print("=" * 70)
