"""Database session management for AI Dungeon Master."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# Global engine and session factory
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key support for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db(db_path: Path | str | None = None) -> Engine:
    """Initialize the database and create all tables.

    Args:
        db_path: Path to the SQLite database file. Defaults to saves/campaign.db

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine, _SessionFactory

    if db_path is None:
        db_path = Path("saves/campaign.db")
    else:
        db_path = Path(db_path)

    # Ensure the directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine
    db_url = f"sqlite:///{db_path}"
    _engine = create_engine(
        db_url,
        echo=False,  # Set to True for SQL debugging
        future=True,
    )

    # Create all tables
    Base.metadata.create_all(_engine)

    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)

    return _engine


def get_engine() -> Engine:
    """Get the database engine, initializing if necessary.

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    if _engine is None:
        init_db()
    return _engine


def get_session() -> Session:
    """Get a new database session.

    Returns:
        SQLAlchemy Session instance
    """
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    return _SessionFactory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as session:
            session.add(some_object)
            session.commit()  # Optional, will auto-commit on exit

    Yields:
        SQLAlchemy Session instance
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_db(db_path: Path | str | None = None) -> None:
    """Reset the database by dropping all tables and recreating them.

    WARNING: This will delete all data!

    Args:
        db_path: Path to the SQLite database file
    """
    global _engine

    if _engine is not None:
        Base.metadata.drop_all(_engine)
        _engine.dispose()
        _engine = None

    init_db(db_path)


def close_db() -> None:
    """Close the database connection and dispose of the engine."""
    global _engine, _SessionFactory

    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionFactory = None
