import pytest

from backend.db import engine as db_engine


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Point the ORM at a throwaway per-test SQLite file, never app.db.

    configure() rebinds the shared SessionLocal in place, so repository code
    that imported SessionLocal picks up the test database automatically.
    """
    db_engine.configure(f"sqlite:///{tmp_path / 'test.db'}")
    db_engine.init_db()
    yield
