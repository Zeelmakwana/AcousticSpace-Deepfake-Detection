"""
AcousticSpace — Auth Utilities
================================
Low-level helpers for password hashing and JWT management.

Password hashing
-----------------
Uses the ``bcrypt`` library directly instead of passlib.  passlib 1.7.4 is
incompatible with bcrypt >= 4.0.0 (the API changed in 4.x and again in 5.x);
calling it with bcrypt >= 4 raises ``ValueError: password cannot be longer
than 72 bytes`` even for normal-length passwords because passlib pre-encodes
the secret in a way the new C backend rejects.  Using bcrypt directly avoids
the compatibility shim entirely and is the correct long-term approach.

Passwords are UTF-8 encoded before hashing.  bcrypt hard-truncates at 72
bytes by design; passwords up to 128 chars (enforced by UserCreate schema)
are well within that limit for ASCII/Latin input.  If support for long
Unicode passwords is ever required, add a SHA-256 pre-hash step here.

Security hardening (over the original)
---------------------------------------
- JWT tokens now carry ``iss`` (issuer) and ``aud`` (audience) claims.
  decode_token() validates both, so tokens from a different service or
  environment cannot be replayed here.
- ``_warn_weak_secret()`` is called at startup; it raises RuntimeError in
  production and emits a loud WARNING in development when the key equals the
  insecure default placeholder.
- The minimum acceptable SECRET_KEY length is enforced (32 bytes / 64 hex
  chars) to guard against brute-force attacks on short keys.
- JWTError sub-types (ExpiredSignatureError, JWTClaimsError) are caught
  individually so the error detail is more informative in the audit log,
  while the client always receives the same opaque 401.
- Token type (access/refresh) is validated *inside* decode_token() as an
  additional guard against token confusion.
"""

from __future__ import annotations

import logging
import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from jose.exceptions import JWTClaimsError

from auth.schemas import TokenData

logger = logging.getLogger("acousticspace.auth")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND")
ALGORITHM:  str = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES:  int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS:    int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
REFRESH_TOKEN_REMEMBER_DAYS:  int = int(os.getenv("REFRESH_TOKEN_REMEMBER_DAYS", 30))

# Issuer and audience claims — both must match on decode.
# Override via env to namespace tokens across environments.
JWT_ISSUER:   str = os.getenv("JWT_ISSUER",   "acousticspace-api")
JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "acousticspace-client")

_INSECURE_KEY_PLACEHOLDER = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND"
_MIN_KEY_LENGTH = 32   # bytes — 64 hex chars from `openssl rand -hex 32`

# ---------------------------------------------------------------------------
# Startup key strength check
# ---------------------------------------------------------------------------

def _warn_weak_secret(key: str) -> None:
    """
    Warn loudly if the JWT secret key is weak or unchanged from the default.

    Raises RuntimeError in production to prevent startup with an insecure key.
    Emits a WARNING in all other environments.
    """
    is_default = key.strip() in (_INSECURE_KEY_PLACEHOLDER, "", "CHANGE_ME")
    is_short   = len(key.encode()) < _MIN_KEY_LENGTH
    app_env    = os.getenv("APP_ENV", "development").lower()

    if is_default or is_short:
        msg = (
            "SECURITY WARNING: JWT_SECRET_KEY is weak or set to the insecure "
            "default placeholder. Generate a strong key with: "
            "openssl rand -hex 32"
        )
        if app_env == "production":
            raise RuntimeError(msg)
        warnings.warn(msg, stacklevel=2)
        logger.warning(msg)


# ---------------------------------------------------------------------------
# Password hashing — bcrypt (direct, no passlib)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """
    Return a bcrypt hash of *plain*.

    The password is UTF-8 encoded before hashing.  bcrypt truncates at 72
    bytes internally; the UserCreate schema caps passwords at 128 characters
    which is safe for ASCII/Latin input.  Work factor is 12 (OWASP minimum
    recommendation as of 2024).
    """
    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        # bcrypt raises ValueError for malformed hashes; treat as mismatch.
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_token(
    data: dict[str, Any],
    expires_delta: timedelta,
    token_type: str,
) -> str:
    """
    Build a signed JWT with exp, iss, aud, and type claims.

    ``iss`` and ``aud`` are included so tokens are bound to this service and
    cannot be replayed against a different AcousticSpace deployment.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": token_type,
    })
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Return a short-lived access JWT with iss/aud claims."""
    delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token({"sub": str(user_id), "role": role}, delta, "access")


def create_refresh_token(
    user_id: int,
    role: str,
    remember_me: bool = False,
) -> str:
    """Return a long-lived refresh JWT with iss/aud claims."""
    days = REFRESH_TOKEN_REMEMBER_DAYS if remember_me else REFRESH_TOKEN_EXPIRE_DAYS
    return _create_token({"sub": str(user_id), "role": role}, timedelta(days=days), "refresh")


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT, checking signature, expiry, iss, and aud.

    Raises HTTP 401 for any validation failure.  The error detail distinguishes
    between expired tokens and otherwise invalid ones so the audit log can be
    more precise, but the HTTP response body is always the same opaque message.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
    except ExpiredSignatureError:
        logger.debug("JWT decode failed: token expired")
        raise credentials_exc
    except JWTClaimsError as exc:
        logger.debug("JWT decode failed: claims error — %s", exc)
        raise credentials_exc
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise credentials_exc

    sub:        str | None = payload.get("sub")
    role:       str | None = payload.get("role")
    token_type: str | None = payload.get("type")

    if not sub or not role or token_type not in ("access", "refresh"):
        logger.warning(
            "JWT payload missing required claims: sub=%s role=%s type=%s",
            sub, role, token_type,
        )
        raise credentials_exc

    return TokenData(sub=sub, role=role, type=token_type)  # type: ignore[arg-type]
