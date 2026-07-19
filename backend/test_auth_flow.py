"""
Direct end-to-end test of the auth flow.
Run from: backend/ directory with venv activated.
Usage: python test_auth_flow.py
"""
import json
import sqlite3
import sys
import urllib.request
import urllib.error
import urllib.parse

BASE = "http://localhost:8000"

def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path, token=None):
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


EMAIL    = "kiroflow_test@example.com"
USERNAME = "kiroflowtest"
PASSWORD = "FlowTest99!"

print("=" * 60)
print("AcousticSpace Auth Flow Test")
print("=" * 60)

# ── 1. REGISTER ──────────────────────────────────────────────
print("\n[1] POST /auth/register")
status, body = post("/auth/register", {
    "email": EMAIL,
    "username": USERNAME,
    "password": PASSWORD,
})
print(f"  Status : {status}")
print(f"  Body   : {json.dumps(body, indent=2)}")
if status == 201:
    print("  ✓ Registration succeeded (HTTP 201)")
    user_id = body.get("id")
elif status == 409:
    print("  ℹ User already exists — continuing with login")
    user_id = None
else:
    print(f"  ✗ Unexpected status {status}")
    sys.exit(1)

# ── 2. VERIFY DB ─────────────────────────────────────────────
print("\n[2] Verify user in SQLite database")
try:
    conn = sqlite3.connect("auth.db")
    cur = conn.cursor()
    cur.execute("SELECT id, email, username, role, is_active FROM users WHERE email = ?", (EMAIL,))
    row = cur.fetchone()
    conn.close()
    if row:
        print(f"  ✓ User found in DB: id={row[0]}, email={row[1]}, username={row[2]}, role={row[3]}, is_active={row[4]}")
    else:
        print("  ✗ User NOT found in DB")
        sys.exit(1)
except Exception as exc:
    print(f"  ✗ DB check failed: {exc}")
    sys.exit(1)

# ── 3. LOGIN ─────────────────────────────────────────────────
print("\n[3] POST /auth/login")
status, body = post("/auth/login", {
    "email": EMAIL,
    "password": PASSWORD,
    "remember_me": False,
})
print(f"  Status : {status}")
print(f"  Body   : {json.dumps(body, indent=2)}")
if status == 200:
    print("  ✓ Login succeeded (HTTP 200)")
    access_token  = body.get("access_token")
    refresh_token = body.get("refresh_token")
    token_type    = body.get("token_type")
    user_info     = body.get("user")
    print(f"  ✓ access_token  : {access_token[:30]}...")
    print(f"  ✓ refresh_token : {refresh_token[:30]}...")
    print(f"  ✓ token_type    : {token_type}")
    print(f"  ✓ user          : {user_info}")
else:
    print(f"  ✗ Login failed with status {status}")
    # Print full error detail to understand what went wrong
    print(f"  ✗ Error detail  : {json.dumps(body, indent=2)}")
    sys.exit(1)

# ── 4. GET /auth/me ───────────────────────────────────────────
print("\n[4] GET /auth/me (with access token)")
status, body = get("/auth/me", token=access_token)
print(f"  Status : {status}")
print(f"  Body   : {json.dumps(body, indent=2)}")
if status == 200:
    print("  ✓ /auth/me succeeded")
else:
    print(f"  ✗ /auth/me failed with {status}")
    sys.exit(1)

# ── 5. REFRESH TOKENS ────────────────────────────────────────
print("\n[5] POST /auth/refresh")
status, body = post("/auth/refresh", {"refresh_token": refresh_token})
print(f"  Status : {status}")
if status == 200:
    new_access  = body.get("access_token")
    new_refresh = body.get("refresh_token")
    print(f"  ✓ Refresh succeeded")
    print(f"  ✓ new access_token  : {new_access[:30]}...")
    print(f"  ✓ new refresh_token : {new_refresh[:30]}...")
else:
    print(f"  ✗ Refresh failed: {json.dumps(body, indent=2)}")
    sys.exit(1)

# ── 6. LOGOUT ────────────────────────────────────────────────
print("\n[6] POST /auth/logout")
data = b""
req = urllib.request.Request(
    f"{BASE}/auth/logout",
    data=data,
    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req) as resp:
        logout_status = resp.status
        logout_body = resp.read()
    print(f"  Status : {logout_status}")
    print(f"  ✓ Logout succeeded (HTTP {logout_status})")
except urllib.error.HTTPError as e:
    print(f"  ✗ Logout failed: {e.code} {e.read()}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ COMPLETE AUTH FLOW PASSED: Signup → DB → Login → JWT → /me → Refresh → Logout")
print("=" * 60)
