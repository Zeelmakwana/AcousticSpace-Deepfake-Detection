"""
Test the exact request path the browser uses:
  Browser → Vite dev server (:5173/api/auth/login) → Backend (:8000/auth/login)
  
We simulate this by calling :5173/api/auth/login directly.
"""
import urllib.request
import urllib.error
import json

BASE_VIA_PROXY = "http://localhost:5173/api"

def post_json(url: str, data: dict) -> tuple[int, dict]:
    raw = json.dumps(data).encode()
    req = urllib.request.Request(
        url,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}

print("=== Testing via Vite proxy (same path browser uses) ===")
print(f"POST {BASE_VIA_PROXY}/auth/login")

status, body = post_json(
    f"{BASE_VIA_PROXY}/auth/login",
    {
        "email": "frontend_debug@example.com",
        "password": "Debugpass123!",
        "remember_me": False,
    }
)

print(f"HTTP {status}")
if status == 200:
    print(f"Keys: {list(body.keys())}")
    print(f"access_token: {'PRESENT' if body.get('access_token') else 'MISSING'}")
    print(f"refresh_token: {'PRESENT' if body.get('refresh_token') else 'MISSING'}")
    print(f"user: {'PRESENT' if body.get('user') else 'MISSING'}")
    print()
    print("SUCCESS: Vite proxy correctly forwarded the request")
else:
    print(f"Body: {json.dumps(body, indent=2)}")

# Also test register via proxy
print()
print("=== Testing register via proxy ===")
status, body = post_json(
    f"{BASE_VIA_PROXY}/auth/register",
    {
        "email": "proxy_test2@example.com",
        "username": "proxytestuser",
        "password": "Proxypass123!",
    }
)
print(f"Register → HTTP {status}: {body}")
