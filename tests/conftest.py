import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from sqlalchemy.engine import make_url

from tsu.db import Base, make_engine, make_sessions
from tsu.models import BudgetGuard


@pytest.fixture
def local_engine(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with make_sessions(engine).begin() as session:
        session.add(BudgetGuard(id=1, frozen=False))
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def postgres_engine():
    url = os.getenv("TSU_TEST_DATABASE_URL")
    if not url:
        pytest.skip("TSU_TEST_DATABASE_URL not configured; requires disposable PostgreSQL")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not parsed.database.endswith("_test"):
        pytest.fail("Use a disposable PostgreSQL database ending in _test")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    engine = make_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_sessions(postgres_engine):
    sessions = make_sessions(postgres_engine)
    # This explicitly configured database is disposable; leave migration version intact.
    with sessions.begin() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.add(BudgetGuard(id=1, frozen=False))
    return sessions
