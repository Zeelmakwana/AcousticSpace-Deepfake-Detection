"""
AcousticSpace — Auth Database Setup
=====================================
Creates the SQLAlchemy engine, session factory, and a dependency that
yields a per-request DB session to FastAPI route handlers.

The database file is stored at the path given by the DATABASE_URL
environment variable.  The default is a SQLite file at ./auth.db
(relative to the directory where uvicorn is started, i.e. backend/).

SQLite is used for development.  For production swap DATABASE_URL to a
PostgreSQL DSN — no other code needs to change.

Usage in route handlers
-----------------------
    from auth.database import get_db
    from sqlalchemy.orm import Session
    from fastapi import Depends

    @router.get("/me")
    def me(db: Session = Depends(get_db)):
        ...

Table creation
--------------
Call `create_all_tables()` once at application startup (in app.py) so
the `users` table exists before the first request arrives.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import ALL models before create_all_tables() is called so that every
# table definition is registered on Base.metadata.  The models package
# __init__.py guarantees correct import order (Base → User → AnalysisHistory).
import models  # noqa: F401  — side-effect import; registers all ORM classes
from models.user import Base

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./auth.db")

# connect_args is only needed for SQLite (thread-safety for FastAPI's
# async request handling where multiple threads may share one connection).
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all_tables() -> None:
    """Create every table declared under Base (User, …) if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency — yield a SQLAlchemy Session, close it when done.

    Use with Depends(get_db) in route signatures.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
