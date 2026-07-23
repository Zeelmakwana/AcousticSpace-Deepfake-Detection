"""List all users in auth.db and run a full login test."""
import sqlite3
import urllib.request
import urllib.error
import json

# --- Show schema first ---
conn = sqlite3.connect("auth.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", tables)
if tables:
    for (t,) in tables:
        print(f"\n  Schema for {t!r}:")
        for row in conn.execute(f"PRAGMA table_info({t})"):
            print(f"    {row}")
        rows = conn.execute(f"SELECT * FROM {t}").fetchall()
        print(f"  Rows in {t!r}: {len(rows)}")
        for r in rows[:5]:
            print(f"    {r}")
conn.close()

print()
print("=== Attempting register + login cycle ===")

TEST_EMAIL = "frontend_debug@example.com"
TEST_USER  = "frontenddbg"
TEST_PASS  = "Debugpass123!"

def post_json(url: str, data: dict) -> tuple[int, dict]:
    raw = json.dumps(data).encode()
    req = urllib.request.Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# Register
status, body = post_json("http://localhost:8000/auth/register", {
    "email": TEST_EMAIL, "username": TEST_USER, "password": TEST_PASS
})
print(f"Register → HTTP {status}: {body}")

# Login
status, body = post_json("http://localhost:8000/auth/login", {
    "email": TEST_EMAIL, "password": TEST_PASS, "remember_me": False
})
print(f"Login    → HTTP {status}")
if status == 200:
    print(f"  Keys in response: {list(body.keys())}")
    print(f"  token_type:       {body.get('token_type')}")
    print(f"  access_token:     {'PRESENT' if body.get('access_token') else 'MISSING'}")
    print(f"  refresh_token:    {'PRESENT' if body.get('refresh_token') else 'MISSING'}")
    u = body.get("user")
    if u:
        print(f"  user.id:          {u.get('id')}")
        print(f"  user.email:       {u.get('email')}")
        print(f"  user.username:    {u.get('username')}")
        print(f"  user.role:        {u.get('role')}")
        print(f"  user.is_active:   {u.get('is_active')}")
        print(f"  user.created_at:  {u.get('created_at')}")
    else:
        print("  user: MISSING FROM RESPONSE  *** BUG ***")
else:
    print(f"  Error body: {body}")
