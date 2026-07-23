"""
AcousticSpace — Request / Response Logging Middleware
======================================================
Starlette middleware that emits a structured JSON log record for every HTTP
request and feeds request-duration data into the metrics registry.

Structured log record fields
-----------------------------
    ts          : ISO-8601 UTC timestamp
    level       : "INFO" | "WARNING" | "ERROR"
    logger      : "acousticspace.http"
    request_id  : UUID v4 (injected into request.state + X-Request-ID header)
    method      : HTTP verb
    path        : URL path
    query       : query string (omitted when empty)
    status      : HTTP response status code
    duration_ms : wall-clock time in milliseconds (2 d.p.)
    ip          : best-effort client IP (X-Forwarded-For → client.host)
    ua          : User-Agent header (truncated to 120 chars)

Metrics integration
-------------------
Every completed request calls ``monitoring.metrics.record_request()`` so
counters and the request-duration histogram are updated in-process without
any external system dependency.

Security notes
--------------
- Request / response *bodies* are never logged.
- Authorization header values are never logged.
- Query strings are logged as-is; route handlers must not embed secrets there.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("acousticspace.http")


def _get_client_ip(request: Request) -> str:
    """Return the best-effort client IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every request + response as a structured JSON record and update
    the in-process metrics registry with duration and status data.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        ip     = _get_client_ip(request)
        ua     = (request.headers.get("user-agent") or "")[:120]
        method = request.method
        path   = request.url.path
        query  = request.url.query or None

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            _emit(
                level="ERROR",
                request_id=request_id,
                method=method,
                path=path,
                query=query,
                status=500,
                duration_ms=duration_ms,
                ip=ip,
                ua=ua,
            )
            # Feed into metrics even on unhandled exception
            try:
                from monitoring.metrics import record_request
                record_request(method, path, 500, duration_ms)
            except Exception:
                pass
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        status      = response.status_code

        _emit(
            level="WARNING" if status >= 400 else "INFO",
            request_id=request_id,
            method=method,
            path=path,
            query=query,
            status=status,
            duration_ms=duration_ms,
            ip=ip,
            ua=ua,
        )

        # Feed into metrics registry — never let this crash the response
        try:
            from monitoring.metrics import record_request
            record_request(method, path, status, duration_ms)
        except Exception:
            pass

        response.headers["X-Request-ID"] = request_id
        return response


def _emit(
    *,
    level: str,
    request_id: str,
    method: str,
    path: str,
    query: str | None,
    status: int,
    duration_ms: float,
    ip: str,
    ua: str,
) -> None:
    """Write one structured JSON log record via the standard logging module."""
    record: dict = {
        "ts":         datetime.now(tz=timezone.utc).isoformat(),
        "level":      level,
        "logger":     "acousticspace.http",
        "request_id": request_id,
        "method":     method,
        "path":       path,
        "status":     status,
        "duration_ms": duration_ms,
        "ip":         ip,
        "ua":         ua,
    }
    if query:
        record["query"] = query

    log_fn = logger.warning if status >= 400 else logger.info
    # Log the pre-serialised JSON string so every aggregator (ELK, Loki,
    # CloudWatch, etc.) can parse it without a custom grok pattern.
    log_fn(json.dumps(record, ensure_ascii=False))
