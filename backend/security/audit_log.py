"""
AcousticSpace — Structured Audit Logger
=========================================
Provides a structured, append-only audit trail for all security-sensitive
operations: authentication events, file uploads, analysis runs, deletions.

Design
------
- Every audit event is a single JSON-Lines record written to ``audit.log``
  (path configurable via AUDIT_LOG_PATH env var).
- Events are also forwarded to the standard ``acousticspace.audit`` logger
  at INFO level so they appear in the uvicorn console during development.
- The writer is thread-safe (Python's logging module handles locking).
- No PII beyond user ID and email prefix is ever written to the audit log.
- The module exposes a single public function: ``emit()``.

Audit event schema (all fields)
--------------------------------
    ts        : ISO-8601 UTC timestamp
    event     : snake_case event type (see AuditEvent enum)
    user_id   : int | None   — authenticated user id when available
    user_email: str | None   — first 3 chars + "@…" masked email
    ip        : str | None   — client IP from X-Forwarded-For or Request
    request_id: str | None   — UUID injected by RequestLoggingMiddleware
    resource  : str | None   — e.g. filename, analysis_id
    outcome   : "success" | "failure"
    detail    : str | None   — safe, operator-facing supplementary info

Public API
----------
    emit(event, *, outcome, user_id, user_email, ip, request_id, resource, detail)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

# ---------------------------------------------------------------------------
# Audit event catalogue
# ---------------------------------------------------------------------------

class AuditEvent(str, Enum):
    # Auth
    AUTH_REGISTER       = "auth.register"
    AUTH_LOGIN          = "auth.login"
    AUTH_LOGIN_FAILED   = "auth.login_failed"
    AUTH_LOGOUT         = "auth.logout"
    AUTH_REFRESH        = "auth.token_refresh"
    AUTH_TOKEN_INVALID  = "auth.token_invalid"
    AUTH_ACCOUNT_LOCKED = "auth.account_locked"

    # Upload & Analysis
    UPLOAD_RECEIVED     = "upload.received"
    UPLOAD_REJECTED     = "upload.rejected"
    ANALYSIS_STARTED    = "analysis.started"
    ANALYSIS_COMPLETED  = "analysis.completed"
    ANALYSIS_FAILED     = "analysis.failed"

    # History
    HISTORY_DELETE_ONE  = "history.delete_one"
    HISTORY_DELETE_ALL  = "history.delete_all"

    # Reports
    REPORT_GENERATED    = "report.generated"

    # Rate limiting
    RATE_LIMIT_HIT      = "security.rate_limit_hit"


# ---------------------------------------------------------------------------
# Logger setup — rotate daily, keep 30 days
# ---------------------------------------------------------------------------
_AUDIT_LOG_PATH: str = os.getenv("AUDIT_LOG_PATH", "audit.log")

_file_handler = logging.handlers.TimedRotatingFileHandler(
    _AUDIT_LOG_PATH,
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8",
    utc=True,
)
_file_handler.setFormatter(logging.Formatter("%(message)s"))

_audit_logger = logging.getLogger("acousticspace.audit")
_audit_logger.setLevel(logging.INFO)
_audit_logger.addHandler(_file_handler)
_audit_logger.propagate = False   # don't double-emit to uvicorn console handler

# Console mirror — shows audit events in dev without needing to tail the file
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(
    logging.Formatter("[AUDIT] %(message)s")
)
_audit_logger.addHandler(_console_handler)


# ---------------------------------------------------------------------------
# Email masking helper
# ---------------------------------------------------------------------------

def _mask_email(email: str | None) -> str | None:
    if not email:
        return None
    try:
        local, domain = email.split("@", 1)
        masked_local = local[:3] + ("*" * max(0, len(local) - 3))
        return f"{masked_local}@{domain}"
    except ValueError:
        return "***"


# ---------------------------------------------------------------------------
# Public emit function
# ---------------------------------------------------------------------------

def emit(
    event: AuditEvent | str,
    *,
    outcome: Literal["success", "failure"] = "success",
    user_id: int | None = None,
    user_email: str | None = None,
    ip: str | None = None,
    request_id: str | None = None,
    resource: str | None = None,
    detail: str | None = None,
) -> None:
    """
    Write one audit record to the audit log (JSON Lines format).

    All parameters are keyword-only to prevent accidental positional misuse.
    """
    record: dict = {
        "ts":          datetime.now(tz=timezone.utc).isoformat(),
        "event":       event.value if isinstance(event, AuditEvent) else event,
        "outcome":     outcome,
        "user_id":     user_id,
        "user_email":  _mask_email(user_email),
        "ip":          ip,
        "request_id":  request_id,
        "resource":    resource,
        "detail":      detail,
    }
    # Omit None fields to keep records compact
    compact = {k: v for k, v in record.items() if v is not None}
    _audit_logger.info(json.dumps(compact, ensure_ascii=False))
