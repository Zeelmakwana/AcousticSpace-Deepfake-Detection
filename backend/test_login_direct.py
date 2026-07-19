"""Quick live test — hits the running backend directly and prints the exact response."""
import urllib.request
import urllib.error
import json

payload = json.dumps({
    "email": "test@test.com",
    "password": "testpass1",
    "remember_me": False,
}).encode()

req = urllib.request.Request(
    "http://localhost:8000/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
        print("STATUS:", resp.status)
        print("KEYS:", list(body.keys()))
        print("token_type:", body.get("token_type"))
        print("user:", body.get("user"))
        print("access_token present:", bool(body.get("access_token")))
        print("refresh_token present:", bool(body.get("refresh_token")))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print("HTTP ERROR:", e.code)
    print("BODY:", body)
except Exception as e:
    print("CONNECTION ERROR:", type(e).__name__, e)
