"""
AcousticSpace — Auth API Routes
=================================
Security hardening (over the original)
---------------------------------------
- Rate limiting via SlowAPI ``@limiter.limit()`` decorators:
    POST /auth/login    → 10/minute per IP (brute-force guard)
    POST /auth/register → 5/minute per IP  (account-farming guard)
    POST /auth/refresh  → 20/minute per IP
    POST /auth/logout   → 30/minute per IP
- The ``limiter`` singleton is imported from ``limiter.py`` (not from
  ``app.py``) to avoid a circular import.  SlowAPI resolves the limiter
  at request time via ``request.app.state.limiter``; the imported object
  and ``app.state.limiter`` are the **same** singleton so limits are
  correctly shared across the process.
- ``request: Request`` is the **first** parameter in every rate-limited
  handler — SlowAPI requires this position to extract the client key.
- Structured audit events emitted for every login attempt (success +
  failure), registration, refresh, logout, and profile updates.
- Consistent RFC 7807 error bodies (handled by app.py global handler).
- request_id propagated to audit records via request.state.

NOTE: ``from __future__ import annotations`` is intentionally absent.
FastAPI + Pydantic v2 resolves route parameter annotations at startup via
``typing.get_type_hints()``.  Enabling PEP 563 deferred evaluation turns
every annotation into a string; Pydantic v2 then cannot locate the
``UserCreate`` / ``UserLogin`` etc. classes and raises
``PydanticUndefinedAnnotation``.  Always use concrete annotations here.
"""

# NO "from __future__ import annotations" — see docstring above.

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.database import get_db
from auth.dependencies import get_current_active_user, _get_ip, _get_request_id
from auth.schemas import Token, TokenData, TokenRefresh, UserCreate, UserLogin, UserOut
from auth.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from limiter import limiter
from models.user import User
from security.audit_log import AuditEvent, emit

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    """
    Create a new user account.

    Rate limited: 5 requests/minute per IP to prevent account farming.

    ``request`` must be the first parameter so SlowAPI can extract the
    client IP address for the rate-limit key.
    """
    ip         = _get_ip(request)
    request_id = _get_request_id(request)

    if db.query(User).filter(User.email == payload.email).first():
        emit(
            AuditEvent.AUTH_REGISTER,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail="Email already registered",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if db.query(User).filter(User.username == payload.username).first():
        emit(
            AuditEvent.AUTH_REGISTER,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail="Username already taken",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        emit(
            AuditEvent.AUTH_REGISTER,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail="IntegrityError on commit",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed due to a conflict. Please try again.",
        )
    db.refresh(user)
    emit(
        AuditEvent.AUTH_REGISTER,
        outcome="success",
        user_id=user.id,
        user_email=user.email,
        ip=ip,
        request_id=request_id,
    )
    return user


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> dict:
    """
    Validate credentials and return an access + refresh JWT pair.

    Rate limited: 10 requests/minute per IP to guard against brute force.
    """
    ip         = _get_ip(request)
    request_id = _get_request_id(request)

    user: Optional[User] = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        emit(
            AuditEvent.AUTH_LOGIN_FAILED,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail=f"Bad credentials for email={payload.email!r}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        emit(
            AuditEvent.AUTH_ACCOUNT_LOCKED,
            outcome="failure",
            user_id=user.id,
            user_email=user.email,
            ip=ip,
            request_id=request_id,
            detail="Login attempt on deactivated account",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    access_token  = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role, remember_me=payload.remember_me)

    emit(
        AuditEvent.AUTH_LOGIN,
        outcome="success",
        user_id=user.id,
        user_email=user.email,
        ip=ip,
        request_id=request_id,
    )
    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user":          user,
    }


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_tokens(
    request: Request,
    payload: TokenRefresh,
    db: Session = Depends(get_db),
) -> dict:
    """
    Accept a valid refresh token and return a fresh JWT pair.

    Rate limited: 20 requests/minute per IP.
    """
    ip         = _get_ip(request)
    request_id = _get_request_id(request)

    token_data: TokenData = decode_token(payload.refresh_token)

    if token_data.type != "refresh":
        emit(
            AuditEvent.AUTH_TOKEN_INVALID,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail="Refresh endpoint received non-refresh token",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected a refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: Optional[User] = db.get(User, int(token_data.sub))
    if user is None or not user.is_active:
        emit(
            AuditEvent.AUTH_TOKEN_INVALID,
            outcome="failure",
            ip=ip,
            request_id=request_id,
            detail=f"Refresh for unknown/inactive user id={token_data.sub}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token      = create_access_token(user.id, user.role)
    new_refresh_token = create_refresh_token(user.id, user.role)

    emit(
        AuditEvent.AUTH_REFRESH,
        outcome="success",
        user_id=user.id,
        user_email=user.email,
        ip=ip,
        request_id=request_id,
    )
    return {
        "access_token":  access_token,
        "refresh_token": new_refresh_token,
        "token_type":    "bearer",
        "user":          user,
    }


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def logout(request: Request) -> None:
    """
    Stateless logout — client discards tokens. Audited for traceability.

    Rate limited: 30 requests/minute per IP (prevents log spam).
    """
    emit(
        AuditEvent.AUTH_LOGOUT,
        outcome="success",
        ip=_get_ip(request),
        request_id=_get_request_id(request),
    )
    return None


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user


# ---------------------------------------------------------------------------
# PATCH /auth/me
# ---------------------------------------------------------------------------
class UpdateUsernamePayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)


@router.patch("/me", response_model=UserOut)
def update_me(
    request: Request,
    payload: UpdateUsernamePayload,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the current user's display username."""
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )
    current_user.username = payload.username
    db.commit()
    db.refresh(current_user)
    return current_user
