"""
AcousticSpace — Auth Pydantic Schemas
=======================================
These schemas define the request/response shapes for every auth endpoint.
They are intentionally separate from the SQLAlchemy model so that the
database representation and the API contract can evolve independently.

Schemas
-------
UserCreate          POST /auth/register  — incoming registration payload
UserLogin           POST /auth/login     — incoming login payload
UserOut             responses            — safe user representation (no hash)
Token               POST /auth/login response body
TokenRefresh        POST /auth/refresh   — incoming refresh token payload
TokenData           internal             — decoded JWT claim payload
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, digits, hyphens, and underscores.")
        return v


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False   # if True, extend refresh token TTL


# ---------------------------------------------------------------------------
# Safe user representation (never includes hashed_password)
# ---------------------------------------------------------------------------
class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: Literal["user", "admin"]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Token response
# ---------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Refresh request
# ---------------------------------------------------------------------------
class TokenRefresh(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Internal — decoded JWT payload
# ---------------------------------------------------------------------------
class TokenData(BaseModel):
    sub: str              # user id as string
    role: str
    type: Literal["access", "refresh"]
