import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


# Where the persistent SQLite file lives. Overridable via env so tests can
# point at a throwaway tmp file instead of the real app.db.
DEFAULT_DATABASE_URL = "sqlite:///app.db"


def _make_engine(url: str):
    # check_same_thread=False: FastAPI/uvicorn may touch a session from a
    # different thread than the one that opened the connection. Safe here
    # because each request uses its own short-lived session.
    return create_engine(url, echo=False, connect_args={"check_same_thread": False})


engine = _make_engine(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

# A single sessionmaker reused everywhere. configure() rebinds it in place so
# repository code that imported SessionLocal keeps working after reconfigure.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def configure(database_url: str) -> None:
    """Repoint the engine at a different database (used by tests)."""
    global engine
    engine = _make_engine(database_url)
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    """Create all tables if they don't already exist. Idempotent."""
    # Import models so they register on Base.metadata before create_all.
    from backend.db import models  # noqa: F401

    Base.metadata.create_all(engine)
