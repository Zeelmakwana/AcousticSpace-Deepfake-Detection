"""
AcousticSpace — User SQLAlchemy Model
======================================
Defines the `users` table used for authentication.

Columns
-------
id              : integer primary key, auto-increment
email           : unique, indexed, max 254 chars (RFC 5321)
hashed_password : bcrypt hash stored as a plain string
username        : display name, unique, max 64 chars
role            : "user" | "admin"  — default "user"
is_active       : soft-disable accounts without deletion
created_at      : UTC timestamp of account creation
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email: str = Column(String(254), unique=True, index=True, nullable=False)
    username: str = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password: str = Column(String(255), nullable=False)
    role: str = Column(String(16), nullable=False, default="user")   # "user" | "admin"
    is_active: bool = Column(Boolean, nullable=False, default=True)
    created_at: datetime = Column(
        DateTime,
        nullable=False,
        # Use a lambda so each new row gets the current UTC time at INSERT,
        # not the time the module was first imported.  timezone.utc makes the
        # datetime timezone-aware; SQLite stores it as a naive UTC string
        # which is fine for this application.
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
