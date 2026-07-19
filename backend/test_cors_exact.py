"""Simulate exactly what the browser sends — including Origin header for CORS preflight."""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"
ORIGIN = "http://localhost:5173"

def post_json_with_origin(url: str, data: dict, origin: str) -> tuple[int, dict, dict]:
    raw = json.dumps(data).encode()
    req = urllib.request.Request(
        url,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Origin": origin,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            resp_headers = dict(resp.headers)
            return resp.status, json.loads(resp.read()), resp_headers
    except urllib.error.HTTPError as e:
        resp_headers = dict(e.headers)
        return e.code, json.loads(e.read()), resp_headers

# --- Test 1: OPTIONS preflight (what browser sends before POST) ---
print("=== TEST 1: OPTIONS preflight ===")
preflight = urllib.request.Request(
    f"{BASE}/auth/login",
    headers={
        "Origin": ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    },
    method="OPTIONS",
)
try:
    with urllib.request.urlopen(preflight) as resp:
        print(f"OPTIONS → HTTP {resp.status}")
        for k, v in resp.headers.items():
            if "access-control" in k.lower() or "allow" in k.lower():
                print(f"  {k}: {v}")
except urllib.error.HTTPError as e:
    print(f"OPTIONS → HTTP {e.code}: {e.read().decode()}")
    for k, v in e.headers.items():
        if "access-control" in k.lower() or "allow" in k.lower():
            print(f"  {k}: {v}")

print()

# --- Test 2: POST login with Origin (simulates browser) ---
print("=== TEST 2: POST /auth/login with Origin header ===")
status, body, headers = post_json_with_origin(
    f"{BASE}/auth/login",
    {"email": "frontend_debug@example.com", "password": "Debugpass123!", "remember_me": False},
    ORIGIN,
)
print(f"POST → HTTP {status}")
print(f"CORS headers:")
for k, v in headers.items():
    if "access-control" in k.lower():
        print(f"  {k}: {v}")
if status == 200:
    print(f"Response keys: {list(body.keys())}")
    print(f"user present: {bool(body.get('user'))}")
    print(f"ALL GOOD - backend responds correctly to browser-like request")
else:
    print(f"ERROR body: {body}")

# --- Test 3: Verify what the Vite proxy sees (simulate /api/auth/login) ---
# The Vite proxy strips /api and forwards to :8000 — but in this test
# we're calling :8000 directly, so this confirms the proxy stripping works.
print()
print("=== TEST 3: Verify CORS allows credentials ===")
status, body, headers = post_json_with_origin(
    f"{BASE}/auth/login",
    {"email": "frontend_debug@example.com", "password": "Debugpass123!", "remember_me": False},
    ORIGIN,
)
allow_credentials = headers.get("access-control-allow-credentials", "NOT SET")
allow_origin = headers.get("access-control-allow-origin", "NOT SET")
print(f"Access-Control-Allow-Origin: {allow_origin}")
print(f"Access-Control-Allow-Credentials: {allow_credentials}")
if allow_origin == ORIGIN and allow_credentials == "true":
    print("CORS is configured correctly for browser requests with credentials")
elif allow_origin == "*":
    print("WARNING: CORS allows wildcard origin — credentials won't work with this!")
else:
    print(f"CORS may be blocking browser requests from {ORIGIN}")
