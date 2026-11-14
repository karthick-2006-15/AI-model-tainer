"""
Database Connection & Session Manager
Native SQLite storage with zero socket overhead, with seamless support for PostgreSQL.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config.settings import settings
import os

# Ensure local directory exists for SQLite database file
if "sqlite" in settings.DATABASE_URL:
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(os.path.abspath(db_file))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.JARVIS_DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency injector for FastAPI endpoints providing a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates all database tables defined in models.py if they do not exist."""
    from storage.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
