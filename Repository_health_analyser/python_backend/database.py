"""
database.py — SQLite database setup using SQLAlchemy ORM.

This module initializes the SQLite database and provides:
  - `engine`   : SQLAlchemy engine connected to repo_health.db
  - `SessionLocal` : sessionmaker factory for creating DB sessions
  - `Base`     : declarative base class for ORM models
  - `get_db()` : FastAPI dependency that yields a DB session and
                 closes it automatically after each request.

Libraries:
  - sqlalchemy  : Python ORM / database toolkit
  - sqlite3     : embedded DB (zero config, ships with Python)

How it works:
  SQLAlchemy uses a connection pool. Each request gets a session from
  `SessionLocal()`, performs its queries, and the `get_db` dependency
  closes the session in the `finally` block — even if the request raises.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# -------------------------------------------------------------------
# Database location
# -------------------------------------------------------------------
# Stored in the python_backend directory so the file is predictable.
# Change DATABASE_URL env var to point at a different SQLite path or
# even a PostgreSQL URL (e.g. "postgresql://...") without code changes.
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# RepoHealth always uses SQLite. The DATABASE_URL env var in the workspace
# may point at the shared Postgres instance for other services — we ignore it.
# SQLite requires zero configuration and is ideal for a per-repo analysis tool.
SQLITE_PATH = os.environ.get(
    "REPO_HEALTH_DB",
    os.path.join(BASE_DIR, "repo_health.db")
)
DATABASE_URL = f"sqlite:///{SQLITE_PATH}"

# `check_same_thread=False` is required for SQLite when multiple
# threads (FastAPI's async workers + background ingestion) share the connection.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a database session.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            return db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
