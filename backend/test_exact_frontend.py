"""
Simulate exactly what the frontend Axios client sends.
Axios sends JSON with Content-Type: application/json.
The login payload from LoginPage.tsx is:
  { email: loginEmail, password: loginPassword, remember_me: rememberMe }
The register payload is:
  { email: signupEmail, username: signupUsername, password: signupPassword }
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"

def post_raw(path, payload, extra_headers=None):
    """Post with exact same headers Axios uses."""
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",  # Axios default Accept
        "Origin": "http://localhost:5173",
        "Referer": "http://localhost:5173/login",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body.decode()

EMAIL    = "kiroflow_test@example.com"
PASSWORD = "FlowTest99!"

print("=" * 70)
print("Simulating exact Axios frontend requests")
print("=" * 70)

# Test 1: Login with remember_me=false (default checkbox state)
print("\n[TEST 1] Login — remember_me=false (Axios payload)")
status, body = post_raw("/auth/login", {
    "email": EMAIL,
    "password": PASSWORD,
    "remember_me": False,
})
print(f"  Status: {status}")
if status == 200:
    print("  ✓ OK")
else:
    print(f"  ✗ FAILED: {json.dumps(body, indent=2)}")

# Test 2: Login WITHOUT remember_me field (in case it's omitted)
print("\n[TEST 2] Login — no remember_me field")
status, body = post_raw("/auth/login", {
    "email": EMAIL,
    "password": PASSWORD,
})
print(f"  Status: {status}")
if status == 200:
    print("  ✓ OK")
else:
    print(f"  ✗ FAILED: {json.dumps(body, indent=2)}")

# Test 3: Login with wrong field name (username instead of email)
print("\n[TEST 3] Login — wrong field 'username' instead of 'email'")
status, body = post_raw("/auth/login", {
    "username": EMAIL,
    "password": PASSWORD,
})
print(f"  Status: {status}")
if status == 422:
    print(f"  (Expected 422) Errors: {json.dumps(body.get('errors', body), indent=2)}")
else:
    print(f"  Unexpected: {body}")

# Test 4: Login with wrong field name (identifier)
print("\n[TEST 4] Login — wrong field 'identifier' instead of 'email'")
status, body = post_raw("/auth/login", {
    "identifier": EMAIL,
    "password": PASSWORD,
})
print(f"  Status: {status}")
if status == 422:
    print(f"  (Expected 422) Errors: {json.dumps(body.get('errors', body), indent=2)}")
else:
    print(f"  Unexpected: {body}")

# Test 5: Test if CORS preflight is the issue (simulate OPTIONS)
print("\n[TEST 5] Test form-encoded body (wrong Content-Type)")
data = f"email={EMAIL}&password={PASSWORD}".encode("utf-8")
req = urllib.request.Request(
    f"{BASE}/auth/login",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
try:
    with urllib.request.urlopen(req) as resp:
        status = resp.status
        body = json.loads(resp.read())
    print(f"  Status: {status}")
except urllib.error.HTTPError as e:
    body = json.loads(e.read())
    print(f"  Status: {e.code}")
    print(f"  Body: {json.dumps(body, indent=2)}")

# Test 6: Empty body
print("\n[TEST 6] Empty JSON body {}")
status, body = post_raw("/auth/login", {})
print(f"  Status: {status}")
if status == 422:
    print(f"  Errors: {json.dumps(body.get('errors', body), indent=2)}")

print("\n" + "=" * 70)
print("Done. Review above to find which test matches the browser error.")
print("=" * 70)
