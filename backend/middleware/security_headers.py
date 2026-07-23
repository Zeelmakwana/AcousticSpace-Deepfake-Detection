"""
AcousticSpace — Security Headers Middleware
============================================
Injects a standard set of security-oriented HTTP response headers on every
outgoing response.

Headers applied
---------------
    Strict-Transport-Security
        Force HTTPS for 1 year including subdomains (HSTS).  Only sent when
        APP_ENV=production to avoid breaking local HTTP development.

    X-Content-Type-Options: nosniff
        Prevent browsers from MIME-sniffing the response away from the
        declared Content-Type.

    X-Frame-Options: DENY
        Block the response from being embedded in an iframe (clickjacking).

    X-XSS-Protection: 0
        Explicitly disable the legacy IE/Chrome XSS auditor, which can itself
        introduce vulnerabilities.  Modern browsers ignore it; CSP is the
        correct mechanism.

    Referrer-Policy: strict-origin-when-cross-origin
        Limits referrer information sent with cross-origin requests.

    Permissions-Policy
        Opt out of browser features the API never uses.

    Content-Security-Policy
        Restrictive CSP for API responses (no HTML rendered by the backend).
        Allows only same-origin frames; blocks all inline scripts and eval.

    Cache-Control: no-store
        Applied only to /auth/* routes so credential responses are never
        cached by intermediary proxies.

Design
------
- Applied unconditionally to every response.
- HSTS is gated on APP_ENV=production.
- Never overrides headers already set by the route handler.
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_APP_ENV = os.getenv("APP_ENV", "development").lower()
_IS_PROD = _APP_ENV == "production"

# Content-Security-Policy for a pure JSON API — no HTML, no scripts served.
_CSP = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'none';"
)

# Permissions-Policy — opt-out everything the API doesn't need
_PERMISSIONS = (
    "accelerometer=(), "
    "camera=(), "
    "geolocation=(), "
    "gyroscope=(), "
    "magnetometer=(), "
    "microphone=(), "
    "payment=(), "
    "usb=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response: Response = await call_next(request)

        h = response.headers

        # HSTS — production only (HTTPS required)
        if _IS_PROD:
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload",
            )

        h.setdefault("X-Content-Type-Options",  "nosniff")
        h.setdefault("X-Frame-Options",          "DENY")
        h.setdefault("X-XSS-Protection",         "0")
        h.setdefault("Referrer-Policy",          "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy",        _PERMISSIONS)
        h.setdefault("Content-Security-Policy",   _CSP)

        # No caching for auth endpoints
        if request.url.path.startswith("/auth"):
            h["Cache-Control"] = "no-store"
            h["Pragma"]        = "no-cache"

        return response
