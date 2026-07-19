"""
AcousticSpace — Auth FastAPI Dependencies
==========================================
Reusable Depends() helpers for route handlers.

Security additions (over the original)
---------------------------------------
- get_current_user() emits an AUTH_TOKEN_INVALID audit event on any token
  validation failure so failed access attempts are traceable.
- get_current_active_user() emits AUTH_ACCOUNT_LOCKED if a deactivated
  account attempts access.
- Client IP is extracted and included in all audit records.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth.database import get_db
from auth.utils import decode_token
from models.user import User
from security.audit_log import AuditEvent, emit

logger = logging.getLogger("acousticspace.auth")

_bearer = HTTPBearer(auto_error=True)


def _get_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the Bearer token from the Authorization header.
    Returns the corresponding User ORM object, or raises HTTP 401.
    Emits an audit event on validation failure.
    """
    ip         = _get_ip(request)
    request_id = _get_request_id(request)

    try:
        token_data = decode_token(credentials.credentials)
    except HTTPException:
        emit(
            AuditEvent.AUTH_TOKEN_INVALID,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail="Token signature/expiry validation failed",
        )
        raise

    if token_data.type != "access":
        emit(
            AuditEvent.AUTH_TOKEN_INVALID,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail=f"Wrong token type: expected 'access', got '{token_data.type}'",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected an access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User | None = db.get(User, int(token_data.sub))
    if user is None:
        emit(
            AuditEvent.AUTH_TOKEN_INVALID,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail=f"User id={token_data.sub} not found in database",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def get_current_active_user(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    """Raises HTTP 403 if the account has been deactivated; audits the attempt."""
    if not current_user.is_active:
        emit(
            AuditEvent.AUTH_ACCOUNT_LOCKED,
            outcome="failure",
            user_id=current_user.id,
            user_email=current_user.email,
            ip=_get_ip(request),
            request_id=_get_request_id(request),
            detail="Access attempt by deactivated account",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return current_user


def require_admin(
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Raises HTTP 403 if the authenticated user is not an admin."""
    if current_user.role != "admin":
        emit(
            AuditEvent.AUTH_TOKEN_INVALID,
            outcome="failure",
            user_id=current_user.id,
            user_email=current_user.email,
            ip=_get_ip(request),
            request_id=_get_request_id(request),
            detail="Admin access required; user role is not admin",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return current_user
